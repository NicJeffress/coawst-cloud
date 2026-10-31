#!/bin/bash
# Test of 1-fixes/roms-restart-step-count.patch: a perfect restart whose step
# number does not fit ROMS's step counter must stop, not restart inexactly.
#
#   tests/fixes/roms-restart-step-count/run.sh OUTDIR
#
# Reef_Ideal_A15 (its initial time is 0 days), built before and after the
# patch (all fixes, plus the two improvements A15's SWAN setup needs), each
# run with tests/tools/restart_inside.sh (60 min straight, 30 + 30 min
# restarted; ROMS TI x TJ + NWAV SWAN, default 1x2 + 2) in two variants:
#   normal  as the case is (DSTART 0)
#   far     DSTART -730119 days, so the start is 730119 days after DSTART, as
#           for an initial file dated 2000-01-01 with DSTART 0: ROMS's step
#           counter (time - DSTART)/DT + 1 overflows
# check.py: far-before restarts wrongly, far-after stops with a message (and its
# fresh runs warn and equal normal), normal restarts exactly and is bit-identical
# before and after. STAGES (default "build run check"); with STAGES=build the runs can be
# made elsewhere into OUTDIR/<variant>-<side>/, then STAGES=check.
# Needs Docker and Python with numpy and netCDF4 (PYTHON). About 10 min to
# build, 4 x 15 min of runs on 4 vCPUs.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
root=$here/../../..
OUT=$(realpath -m "$1")
PY=${PYTHON:-python3}
STAGES=${STAGES:-build run check}
TI=${TI:-1} TJ=${TJ:-2} NWAV=${NWAV:-2}
P=1-fixes/roms-restart-step-count.patch
FAR='s/^( *DSTART *= *)0\.0d0/\1-730119.0d0/'
mkdir -p "$OUT"
has() { [[ " $STAGES " == *" $1 "* ]]; }
if has build; then
    { grep -vE '^[[:space:]]*(#|$)' "$root/build/coawst/patches/series" | grep '^1-fixes/'
      echo 2-improvements/swan-netcdf-output.patch
      echo 2-improvements/swan-periodic-curvilinear.patch; } > "$OUT/series-after"
    grep -vxF "$P" "$OUT/series-after" > "$OUT/series-before"
    for side in before after; do
        "$root/build/coawst/build.sh" --case "$root/tests/cases/Reef_Ideal_A15" --app REEF_IDEAL_A15 \
            --series "$OUT/series-$side" --tag coawst-test:stepc-$side > "$OUT/build-$side.log" 2>&1
    done
fi
if has run; then
    for side in before after; do
        for v in normal far; do
            d=$OUT/$v-$side; rm -rf "$d"; mkdir -p "$d"; cp "$here/../../tools/"{restart_inside,case_inside}.sh "$d/"
            sed=""; [ $v = far ] && sed=$FAR
            docker run --rm --user "$(id -u):$(id -g)" -v "$d:/work" -w /work -e OCEANSED="$sed" \
                coawst-test:stepc-$side bash /work/restart_inside.sh Reef_Ideal_A15 60 30 $TI $TJ $NWAV \
                > "$d/runner.log" 2>&1 || true
            echo "   $v-$side: $(grep -E '^(straight|part1|part2):' "$d/runner.log" | paste -sd' ')"
        done
    done
fi
status=0
if has check; then
    "$PY" -I "$here/check.py" "$OUT" | tee "$OUT/check.txt" || status=1
fi
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
