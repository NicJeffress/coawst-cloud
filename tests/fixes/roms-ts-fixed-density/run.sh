#!/bin/bash
# Test of 1-fixes/roms-ts-fixed-density.patch: with TS_FIXED, a run stopped and
# restarted from its restart files must continue exactly as the uninterrupted run.
#
#   tests/fixes/roms-ts-fixed-density/run.sh OUTDIR [TOTAL RST]
#
# Idea: with TS_FIXED, main3d skipped rho_eos, so the depth-averaged densities
# of the barotropic pressure gradient (rhoA, rhoS), the density and the buoyancy
# frequency were computed once, at initialization, from the layer depths of the
# start time; a restarted run computes them at the restart time, with another
# free surface, and differs from the uninterrupted run in the last bits from its
# first barotropic step on. The patch calls rho_eos every step with TS_FIXED too.
# Builds (the fixes series without and with this patch):
#   tsfixed-before, tsfixed-after   tests/cases/Reef_Ideal_A15_veg (TS_FIXED)
#   evolve-before, evolve-after     tests/cases/Reef_Ideal_A15 with -TS_FIXED
# Runs (tests/tools/restart_inside.sh, ROMS 1x2 + 2 SWAN): straight 0 -> TOTAL
#   (default 60 min); part1 0 -> RST (30); part2 RST -> TOTAL, for the TS_FIXED
#   builds; the -TS_FIXED builds run 10 min with history every 2 min.
# Checks (check.py), on the double-precision restart records at TOTAL:
#   bug       before the patch the restarted run differs from the straight one
#   fixed     after it, u, v, ubar, vbar and zeta are bit-identical
#   unchanged evolve-before and evolve-after (no TS_FIXED): identical history
# STAGES (default "build run check"). Needs Docker and Python with numpy and
# netCDF4 (PYTHON).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
root=$here/../../..
OUT=$(realpath -m "$1") TOTAL=${2:-60} RST=${3:-30}
PY=${PYTHON:-python3}
STAGES=${STAGES:-build run check}
TI=${TI:-1} TJ=${TJ:-2} NWAV=${NWAV:-2}
P=1-fixes/roms-ts-fixed-density.patch
mkdir -p "$OUT"
has() { [[ " $STAGES " == *" $1 "* ]]; }
if has build; then
    echo "== build"
    { grep -vE '^[[:space:]]*(#|$)' "$root/build/coawst/patches/series" | grep '^1-fixes/'
      echo 2-improvements/swan-netcdf-output.patch
      echo 2-improvements/swan-periodic-curvilinear.patch; } > "$OUT/series-after"
    grep -vxF "$P" "$OUT/series-after" > "$OUT/series-before"
    for side in before after; do
        "$root/build/coawst/build.sh" --case "$root/tests/cases/Reef_Ideal_A15_veg" --app REEF_IDEAL_A15 \
            --series "$OUT/series-$side" --tag coawst-test:tsfixed-$side > "$OUT/build-tsfixed-$side.log" 2>&1
        "$root/build/coawst/build.sh" --case "$root/tests/cases/Reef_Ideal_A15" --app REEF_IDEAL_A15 \
            --series "$OUT/series-$side" --tag coawst-test:evolve-$side -- --build-arg CPP_OPTIONS="-TS_FIXED" \
            > "$OUT/build-evolve-$side.log" 2>&1
        echo "   $side: built"
    done
fi
if has run; then
    echo "== runs"
    for side in before after; do
        d=$OUT/tsfixed-$side; rm -rf "$d"; mkdir -p "$d"; cp "$tools/"{restart_inside,case_inside}.sh "$d/"
        docker run --rm --user "$(id -u):$(id -g)" -v "$d:/work" -w /work \
            coawst-test:tsfixed-$side bash /work/restart_inside.sh Reef_Ideal_A15_veg "$TOTAL" "$RST" $TI $TJ $NWAV \
            > "$d/runner.log" 2>&1 || true
        echo "   tsfixed-$side: $(grep -E '^(straight|part1|part2):' "$d/runner.log" | paste -sd' ')"
        rm -rf "$OUT/evolve-$side"
        OUTDT=2 "$tools/run_case.sh" coawst-test:evolve-$side "$OUT" evolve-$side Reef_Ideal_A15 $TI $TJ $NWAV 10 || true
    done
fi
if has check; then
    echo "== checks"
    "$PY" -I "$here/check.py" "$OUT" | tee "$OUT/check.txt"
fi
