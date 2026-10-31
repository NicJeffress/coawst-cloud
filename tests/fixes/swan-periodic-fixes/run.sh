#!/bin/bash
# Test of 1-fixes/swan-periodic-fixes.patch: SWAN with periodic lateral
# boundaries (COORDINATES ... REPEATING), items 11, 12 and 15.
#
#   tests/fixes/swan-periodic-fixes/run.sh SOURCE OUTDIR
#
# SOURCE: a COAWST tree or tarball at the pinned commit (for the source check).
#   1. Source check (check_source.py), before and after the patch:
#      item 12 every test that cuts the grid into x-strips excludes periodic grids
#      item 15 the coupler takes the spectral Stokes fields through the same
#              index map as the other wave fields
#   2. Standalone SWAN (tests/cases/Swan_Periodic_Test), an A15-like reef with
#      a pass, periodic in x, waves from 20 deg east of north, 1 h
#      (make_inputs.py): grids 'wide' (200 x 121 points: x-strips) and 'tall'
#      (100 x 121: y-strips), each with 1 and 4 SWAN processes (check_runs.py):
#        item 12 wide, 4 processes = 1 process (before: crash or garbage)
#        item 11 COMPGRID output = output on the grid points, none missing
#   Item 15 needs a coupled periodic run; it is run with the periodic
#   curvilinear grids of A15 (2-improvements/swan-periodic-curvilinear).
# Needs Docker and Python with numpy and netCDF4 (PYTHON). About 20 min.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
SRC=$1 OUT=$(realpath -m "$2")
PY=${PYTHON:-python3}
P=1-fixes/swan-periodic-fixes.patch
mkdir -p "$OUT"
status=0
echo "== 1. source check"
for side in before after; do
    if [ $side = before ]; then "$tools/series_upto.sh" $P --before > "$OUT/series-$side"
    else "$tools/series_upto.sh" $P > "$OUT/series-$side"; fi
    s=$OUT/series-$side; [ "$(cat "$s")" = none ] && s=none
    rm -rf "$OUT/src-$side"
    "$tools/patched_tree.sh" "$SRC" "$s" "$OUT/src-$side"
    echo "-- $side the patch"
    "$PY" -I "$here/check_source.py" "$OUT/src-$side/SWAN/src" | tee "$OUT/source-$side.txt" | sed 's/^/   /' || true
    rm -rf "$OUT/src-$side"
done
grep -q INCONSISTENT "$OUT/source-before.txt" || { echo "FAIL: stock source not flagged"; status=1; }
grep -qx CONSISTENT "$OUT/source-after.txt" || { echo "FAIL: patched source inconsistent"; status=1; }

echo "== 2. standalone periodic SWAN"
"$tools/build_pair.sh" $P coawst-test:swanper --case "$here/../../cases/Swan_Periodic_Test" \
    --app SWAN_PERIODIC_TEST
for side in before after; do
    rm -rf "$OUT/$side" && mkdir -p "$OUT/$side"
    "$PY" -I "$here/make_inputs.py" "$OUT/$side/inputs" > /dev/null
    # DISSIP as NetCDF needs 2-improvements/swan-netcdf-output (SWAN would
    # reject the input): not used here
    sed -i "/'output\/dissip.nc'/d" "$OUT/$side/inputs"/*/swan.in
    for case in wide-rep-mid tall-rep-mid; do
        for np in 1 4; do
            d=$OUT/$side/$case-np$np
            cp -r "$OUT/$side/inputs/$case" "$d"
            docker run --rm --user "$(id -u):$(id -g)" -v "$d:/run" -w /run coawst-test:swanper-$side \
                mpirun --use-hwthread-cpus --bind-to none -np $np coawstM swan.in > "$d/log.txt" 2>&1 \
                && echo "   $side $case np$np: done" || echo "   $side $case np$np: FAILED (exit $?)"
        done
    done
    echo "-- $side the patch"
    "$PY" -I "$here/check_runs.py" "$OUT/$side" | tee "$OUT/check-$side.txt" | sed 's/^/   /' || true
done
grep -q "SOME CHECKS BAD" "$OUT/check-before.txt" || { echo "FAIL: no bug shown before the patch"; status=1; }
grep -q "ALL OK" "$OUT/check-after.txt" || { echo "FAIL: checks bad after the patch"; status=1; }
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
