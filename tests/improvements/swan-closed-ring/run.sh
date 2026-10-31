#!/bin/bash
# Test of 2-improvements/swan-closed-ring.patch: coupled ROMS + SWAN on a grid
# that closes on itself round an island (an O-grid), tests/cases/Circle_Island.
#
#   tests/improvements/swan-closed-ring/run.sh OUTDIR [MINUTES]
#
# Builds the case before and after the patch, then runs (MINUTES, default 60,
# output every 10 min, the coupling interval):
#   before            without the patch, waves from the north
#   north             waves from the north, ROMS 6x1 + 2 SWAN
#   north-roll54      the same domain with the seam moved 54 columns (90 deg)
#   north-1x6-1swan   ROMS 1x6 + 1 SWAN
#   north-2x2-3swan   ROMS 2x2 + 3 SWAN
#   inward            waves aimed straight inward all around the island
#   north-it5, north-roll54-it5   the north runs with 5 SWAN iterations per
#                     time step (the yardstick for the seam shift)
#   a15-before, a15-after   Reef_Ideal_A15 (periodic, not closed) before and
#                     after the patch, ROMS 1x6 + 2 SWAN
#   restart           MINUTES straight vs MINUTES/2 + MINUTES/2 restarted
# check.py: PASS/FAIL per check; plot.py draws the figure of the document.
# STAGES (default "build run check"); with STAGES=build the runs can be made
# elsewhere (e.g. Cloud Batch, about 5 min each on 8 vCPUs) into the same
# layout, then STAGES=check. Needs Docker and Python with numpy, netCDF4,
# matplotlib (PYTHON). About 20 min to build, 1.2 h of runs on 4 vCPUs.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
OUT=$(realpath -m "$1")
MIN=${2:-60}
PY=${PYTHON:-python3}
STAGES=${STAGES:-build run check}
CASE=Circle_Island
mkdir -p "$OUT"
has() { [[ " $STAGES " == *" $1 "* ]]; }
if has build; then
    "$tools/build_pair.sh" 2-improvements/swan-closed-ring.patch coawst-test:ring \
        --case "$here/../../cases/$CASE" --app CIRCLE_ISLAND
    "$tools/build_pair.sh" 2-improvements/swan-closed-ring.patch coawst-test:ringa15 \
        --case "$here/../../cases/Reef_Ideal_A15" --app REEF_IDEAL_A15
fi
export OUTDT=10
export MPIRUN_ARGS=${MPIRUN_ARGS:---oversubscribe}   # 8 processes on a 4-vCPU machine
ROLL_OCEAN='s/circle_grid\.nc/circle_grid_roll54.nc/'
ROLL_SWAN='s/swan_coord\.grd/swan_coord_roll54.grd/; s/swan_bathy\.bot/swan_bathy_roll54.bot/'
INWARD_SWAN='s/^\$INWARD //; s/^(BOUNDSPEC SEGMENT IJ [0-9 ]+ CONSTANT .*)/$ \1/'
IT5_SWAN='s/^(COMPUTE NONSTATIONARY)/NUMERIC STOPC 0. 0. 0. 100. NONSTAT 5\n\1/'
if has run; then
    run() {   # run NAME SIDE TI TJ NWAV
        rm -rf "${OUT:?}/$1"
        "$tools/run_case.sh" "coawst-test:ring-$2" "$OUT" "$1" $CASE "$3" "$4" "$5" "$MIN" || true
    }
    run before before 6 1 2
    run north after 6 1 2
    OCEANSED=$ROLL_OCEAN SWANSED=$ROLL_SWAN run north-roll54 after 6 1 2
    run north-1x6-1swan after 1 6 1
    run north-2x2-3swan after 2 2 3
    SWANSED=$INWARD_SWAN run inward after 6 1 2
    SWANSED=$IT5_SWAN run north-it5 after 6 1 2
    OCEANSED=$ROLL_OCEAN SWANSED="$ROLL_SWAN; $IT5_SWAN" run north-roll54-it5 after 6 1 2
    for side in before after; do     # an ordinary periodic grid: must be unchanged
        rm -rf "${OUT:?}/a15-$side"
        "$tools/run_case.sh" "coawst-test:ringa15-$side" "$OUT" "a15-$side" Reef_Ideal_A15 1 6 2 "$MIN" || true
    done
    rm -rf "$OUT/restart" && mkdir -p "$OUT/restart"
    cp "$tools/case_inside.sh" "$tools/restart_inside.sh" "$OUT/restart/"
    docker run --rm --user "$(id -u):$(id -g)" -v "$OUT/restart:/work" -w /work -e OUTDT -e MPIRUN_ARGS \
        coawst-test:ring-after bash restart_inside.sh $CASE "$MIN" $((MIN / 2)) 6 1 2 || true
fi
status=0
if has check; then
    "$PY" -I "$here/check.py" "$OUT" | tee "$OUT/check.txt" || status=1
    "$PY" -I "$here/plot.py" "$OUT" "$OUT/swan-closed-ring.png" || true
fi
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
