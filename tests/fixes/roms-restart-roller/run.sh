#!/bin/bash
# Test of 1-fixes/roms-restart-roller.patch: with ROLLER_RENIERS, a run stopped
# and restarted from its restart files must continue as the uninterrupted run.
#
#   tests/fixes/roms-restart-roller/run.sh OUTDIR [TOTAL RST]
#
# Idea: the Reniers roller carries its own state, the roller area rollA, from
# step to step. COAWST does not write it to the restart file, so a restarted
# run starts with no roller and drifts away. The patch writes and reads it and
# the roller's dissipation, and takes no roller step in the first step after a
# perfect restart (the stored values already include that step's update).
# Builds (the whole series without and with this patch), tests/cases/Reef_Ideal_A15:
#   roller-before, roller-after   +ROLLER_RENIERS
#   plain-before, plain-after     the case as it is (no roller)
# Runs (tests/tools/restart_inside.sh, ROMS 1x2 + 2 SWAN, WEC_ALPHA 0.5):
#   straight 0 -> TOTAL (default 60 min); part1 0 -> RST (30), writing restart
#   files; part2 RST -> TOTAL from them, for roller-before and roller-after.
# Checks (check.py):
#   bug       before the patch the restarted run differs by more than 1e-6 m/s
#   fixed     after it, by less than 1e-8 m/s (round-off of the stored history)
#   unchanged plain-before and plain-after (no roller), 10 min each with
#             history every 2 min: identical history (the executables differ only in line numbers that
#             ROMS's error messages carry)
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
P=1-fixes/roms-restart-roller.patch
case=$root/tests/cases/Reef_Ideal_A15
mkdir -p "$OUT"
has() { [[ " $STAGES " == *" $1 "* ]]; }
status=0
if has build; then
    echo "== build"
    { grep -vE '^[[:space:]]*(#|$)' "$root/build/coawst/patches/series" | grep '^1-fixes/'
      echo 2-improvements/swan-netcdf-output.patch
      echo 2-improvements/swan-periodic-curvilinear.patch; } > "$OUT/series-after"
    grep -vxF "$P" "$OUT/series-after" > "$OUT/series-before"
    for side in before after; do
        "$root/build/coawst/build.sh" --case "$case" --app REEF_IDEAL_A15 --series "$OUT/series-$side" \
            --tag coawst-test:rstroller-$side -- --build-arg CPP_OPTIONS="+ROLLER_RENIERS" > "$OUT/build-roller-$side.log" 2>&1
        "$root/build/coawst/build.sh" --case "$case" --app REEF_IDEAL_A15 --series "$OUT/series-$side" \
            --tag coawst-test:rstplain-$side > "$OUT/build-plain-$side.log" 2>&1
    done
fi
if has run; then
    echo "== runs"
    for side in before after; do
        d=$OUT/roller-$side; rm -rf "$d"; mkdir -p "$d"; cp "$tools/"{restart_inside,case_inside}.sh "$d/"
        docker run --rm --user "$(id -u):$(id -g)" -v "$d:/work" -w /work \
            -e OCEANSED='s/^( *WEC_ALPHA *== *)[0-9.d+-]+/\10.5d0/' \
            coawst-test:rstroller-$side bash /work/restart_inside.sh Reef_Ideal_A15 "$TOTAL" "$RST" $TI $TJ $NWAV \
            > "$d/runner.log" 2>&1 || true
        echo "   roller-$side: $(grep -E '^(straight|part1|part2):' "$d/runner.log" | paste -sd' ')"
        rm -rf "$OUT/plain-$side"
        OUTDT=2 "$tools/run_case.sh" coawst-test:rstplain-$side "$OUT" plain-$side Reef_Ideal_A15 $TI $TJ $NWAV 10 || true
    done
fi
if has check; then
    echo "== checks"
    "$PY" -I "$here/check.py" "$OUT" | tee "$OUT/check.txt" || status=1
fi
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
