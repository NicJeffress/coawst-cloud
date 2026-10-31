#!/bin/bash
# Test of 1-fixes/roms-restart-wec.patch: a coupled run stopped and restarted
# from its restart files must continue exactly as the uninterrupted run.
#
#   tests/fixes/roms-restart-wec/run.sh OUTDIR [TOTAL RST]
#
# Two variants of the idealized reef (tests/cases), both with waves (WEC_VF),
# GLS turbulence and PERFECT_RESTART:
#   veg    Reef_Ideal_A15_veg (canopy everywhere)
#   river  Reef_Ideal_A15 with a river: 3 face sources (LuvSrc) on the land wall
#          of the lagoon, 5 m3/s each, in the top layers (make_river.py)
# Builds (all with the fixes, including swan-exact-restart for SWAN's side, and
# the borrowed swan-netcdf-output and swan-periodic-curvilinear):
#   before: without this patch      after: with it
# Runs (tests/tools/restart_inside.sh, ROMS 1x2 + 2 SWAN here; TI TJ NWAV):
#   straight 0 -> TOTAL (default 60 min); part1 0 -> RST (30), writing restart
#   files; part2 RST -> TOTAL from them. History and SWAN output every 10 min.
# Baseline: the river image without the river (noriver-after).
# Check (check_runs.py): part2 vs straight at TOTAL. Before the patch the
# restarted run drifts away; after it, veg must agree to round-off and river
# no worse than its no-river baseline.
# STAGES (default "build run check"): with STAGES=build the four runs can be
# made elsewhere (OUTDIR/<variant>-<side>/ as restart_inside.sh writes them),
# then STAGES=check. Needs Docker and Python with numpy and netCDF4 (PYTHON).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
root=$here/../../..
OUT=$(realpath -m "$1") TOTAL=${2:-60} RST=${3:-30}
PY=${PYTHON:-python3}
STAGES=${STAGES:-build run check}
TI=${TI:-1} TJ=${TJ:-2} NWAV=${NWAV:-2}
P=1-fixes/roms-restart-wec.patch
mkdir -p "$OUT"
has() { [[ " $STAGES " == *" $1 "* ]]; }
river_sed="s/^( *LuvSrc *== *)F/\1T/"
status=0
if has build; then
    echo "== build"
    { grep -vE '^[[:space:]]*(#|$)' "$root/build/coawst/patches/series" | grep '^1-fixes/'
      echo 2-improvements/swan-netcdf-output.patch
      echo 2-improvements/swan-periodic-curvilinear.patch; } > "$OUT/series-after"
    grep -vxF "$P" "$OUT/series-after" > "$OUT/series-before"
    for side in before after; do
        for c in Reef_Ideal_A15_veg Reef_Ideal_A15; do
            [ $c = Reef_Ideal_A15 ] && v=river || v=veg
            "$root/build/coawst/build.sh" --case "$root/tests/cases/$c" --app REEF_IDEAL_A15 \
                --series "$OUT/series-$side" --tag coawst-test:rst-$v-$side > "$OUT/build-$v-$side.log" 2>&1
        done
    done
    "$PY" -I "$here/make_river.py" "$root/tests/cases/Reef_Ideal_A15" "$OUT/ocean_rivers.nc"
fi
if has run; then
    echo "== runs"
    for side in before after; do
        for v in veg river; do
            [ $v = river ] && c=Reef_Ideal_A15 || c=Reef_Ideal_A15_veg
            d=$OUT/$v-$side; rm -rf "$d"; mkdir -p "$d"; cp "$here/../../tools/"{restart_inside,case_inside}.sh "$d/"
            if [ $v = river ]; then
                cp "$OUT/ocean_rivers.nc" "$d/"
                env=(-e OCEANSED="$river_sed" -e PREP="cp /work/ocean_rivers.nc .")
            else
                env=()
            fi
            docker run --rm --user "$(id -u):$(id -g)" -v "$d:/work" -w /work "${env[@]}" \
                coawst-test:rst-$v-$side bash /work/restart_inside.sh $c "$TOTAL" "$RST" $TI $TJ $NWAV \
                > "$d/runner.log" 2>&1 || true
            echo "   $v-$side: $(grep -E '^(straight|part1|part2):' "$d/runner.log" | paste -sd' ')"
        done
    done
    # baseline: the river case's image without the river (base A15 restarts to ~1e-7 m/s)
    d=$OUT/noriver-after; rm -rf "$d"; mkdir -p "$d"; cp "$here/../../tools/"{restart_inside,case_inside}.sh "$d/"
    docker run --rm --user "$(id -u):$(id -g)" -v "$d:/work" -w /work coawst-test:rst-river-after \
        bash /work/restart_inside.sh Reef_Ideal_A15 "$TOTAL" "$RST" $TI $TJ $NWAV > "$d/runner.log" 2>&1 || true
fi
if has check; then
    echo "== checks"
    "$PY" -I "$here/check_runs.py" "$OUT" | tee "$OUT/check.txt" || status=1
fi
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
