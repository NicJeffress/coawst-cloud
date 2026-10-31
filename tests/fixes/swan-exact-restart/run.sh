#!/bin/bash
# Test of 1-fixes/swan-exact-restart.patch: a run restarted from SWAN's periodic
# restart files must reproduce the uninterrupted run (item 19).
#
#   tests/fixes/swan-exact-restart/run.sh OUTDIR
#
# Standalone SWAN (tests/cases/Swan_Periodic_Test build), the periodic reef of
# swan-periodic-fixes ('tall-rep-mid', its make_inputs.py), 2 SWAN processes,
# Hs every 10 min:
#   straight  40 min
#   part1     20 min, RESTART 'output/swan_rst.dat' <FORMAT> 20 MIN
#   part2     INIT HOTSTART MULTIPLE (part1's files) <FORMAT>, then 20 -> 40 min
# for FORMAT = UNFORMATTED (binary) and FREE (text), before and after the patch.
# Compared: Hs at 40 min, part2 vs straight.
#   before, UNFORMATTED: SWAN writes its periodic restart files as text
#           whatever the keyword, so the binary restart does not reproduce
#           the run (it fails to read, or differs)
#   after,  UNFORMATTED: bit-identical
#   FREE (text, about 5 significant digits): differs before and after
#           (shown for reference; not part of PASS)
# Needs Docker and Python with numpy and netCDF4 (PYTHON). About 15 min.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
OUT=$(realpath -m "$1")
PY=${PYTHON:-python3}
mkdir -p "$OUT"
"$tools/build_pair.sh" 1-fixes/swan-exact-restart.patch coawst-test:swanrst \
    --case "$here/../../cases/Swan_Periodic_Test" --app SWAN_PERIODIC_TEST
"$PY" -I "$here/../swan-periodic-fixes/make_inputs.py" "$OUT/inputs" > /dev/null
base=$OUT/inputs/tall-rep-mid
sed -i -E 's/OUTPUT 20000101.000000 30 MIN/OUTPUT 20000101.000000 10 MIN/' "$base/swan.in"
sed -i "/'output\/dissip.nc'/d" "$base/swan.in"     # needs 2-improvements/swan-netcdf-output
swan() { # dir side
    docker run --rm --user "$(id -u):$(id -g)" -v "$1:/run" -w /run coawst-test:swanrst-$2 \
        mpirun --use-hwthread-cpus --bind-to none -np 2 coawstM swan.in > "$1/log.txt" 2>&1
}
for side in before after; do
    d=$OUT/$side-straight; rm -rf "$d"; cp -r "$base" "$d"
    sed -i -E 's/^(COMPUTE NONSTATIONARY 20000101.000000 60 SEC) [0-9.]+/\1 20000101.004000/' "$d/swan.in"
    swan "$d" $side && echo "   $side straight 40 min: done" || echo "   $side straight: FAILED"
    for fmt in UNFORMATTED FREE; do
        p1=$OUT/$side-$fmt-part1 p2=$OUT/$side-$fmt-part2
        rm -rf "$p1" "$p2"; cp -r "$base" "$p1"; cp -r "$base" "$p2"
        sed -i -E "s/^(COMPUTE NONSTATIONARY 20000101.000000 60 SEC) [0-9.]+/RESTART 'output\/swan_rst.dat' $fmt 20 MIN\n\1 20000101.002000/" "$p1/swan.in"
        swan "$p1" $side && echo "   $side $fmt part1 0-20 min: done" || echo "   $side $fmt part1: FAILED"
        cp "$p1"/output/swan_rst.dat* "$p2/" 2>/dev/null || true
        sed -i -E "s/^COMPUTE NONSTATIONARY 20000101.000000 60 SEC [0-9.]+/INIT HOTSTART MULTIPLE 'swan_rst.dat' $fmt\nCOMPUTE NONSTATIONARY 20000101.002000 60 SEC 20000101.004000/" "$p2/swan.in"
        if swan "$p2" $side; then
            echo "   $side $fmt part2 20-40 min: done"
            "$PY" -I "$tools/compare_nc.py" "$OUT/$side-straight/output/hsign.nc" \
                "$p2/output/hsign.nc" --last > "$OUT/compare-$side-$fmt.txt" 2>&1 || true
        else
            echo "   $side $fmt part2: FAILED"; tail -5 "$p2/log.txt" > "$OUT/compare-$side-$fmt.txt"
            echo "RESTART FAILED" >> "$OUT/compare-$side-$fmt.txt"
        fi
    done
done
echo "== Hs at 40 min, restarted vs straight"
for side in before after; do for fmt in UNFORMATTED FREE; do
    printf '   %-6s %-11s %s\n' $side $fmt "$(grep -E '^hs|RESTART FAILED|BIT|DIFF' "$OUT/compare-$side-$fmt.txt" | head -2 | paste -sd' ')"
done; done
status=0
grep -q "ALL BIT-IDENTICAL" "$OUT/compare-before-UNFORMATTED.txt" && { echo "FAIL: stock restart already exact"; status=1; }
grep -q "ALL BIT-IDENTICAL" "$OUT/compare-after-UNFORMATTED.txt" || { echo "FAIL: patched restart not exact"; status=1; }
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
