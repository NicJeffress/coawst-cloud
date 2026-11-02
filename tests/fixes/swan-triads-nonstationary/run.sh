#!/bin/bash
# Test of 1-fixes/swan-triads-nonstationary.patch on tests/cases/Reef_Ideal_A15_veg.
#
#   tests/fixes/swan-triads-nonstationary/run.sh OUTDIR [MINUTES]
#
# Idea: SWAN skipped the triad source term in the first iteration of every
# time step whenever currents are present. A coupled run always has currents
# and does one SWAN iteration per step, so TRIAD never acted: the triad
# transfer (REDTRIAD output) was zero everywhere and a run without the TRIAD
# line was bit-identical. Builds (the whole series, before = without this patch):
#   before, after
# Runs of MINUTES (default 60: the waves reach the crest by 30 min), ROMS
# 1x2 + 2 SWAN (TI, TJ, NWAV), SWAN BLOCK output and ROMS history every 10 min:
#   before          TRIAD in swan.in
#   after           TRIAD in swan.in
#   after-notriad   the TRIAD line removed
# Checks (check.py):
#   bug       before: REDTRIAD zero at every point and output time
#   fixed     after: REDTRIAD nonzero on the reef, and the run differs
#   unchanged after-notriad bit-identical to before (every SWAN and ROMS
#             output): the patch changes nothing else, and before had no triads
# STAGES (default "build run check") as in the other tests.
# Needs Docker and Python with numpy and netCDF4 (PYTHON).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
root=$here/../../..
OUT=$(realpath -m "$1") MIN=${2:-60}
PY=${PYTHON:-python3}
STAGES=${STAGES:-build run check}
TI=${TI:-1} TJ=${TJ:-2} NWAV=${NWAV:-2}
P=1-fixes/swan-triads-nonstationary.patch
case=$root/tests/cases/Reef_Ideal_A15_veg
export MPIRUN_ARGS=${MPIRUN_ARGS:---oversubscribe}
mkdir -p "$OUT"
has() { [[ " $STAGES " == *" $1 "* ]]; }
status=0
if has build; then
    echo "== build"
    grep -vE '^[[:space:]]*(#|$)' "$root/build/coawst/patches/series" > "$OUT/series-after"
    grep -vxF "$P" "$OUT/series-after" > "$OUT/series-before"
    for side in before after; do
        "$root/build/coawst/build.sh" --case "$case" --app REEF_IDEAL_A15 --series "$OUT/series-$side" \
            --tag coawst-test:triads-$side > "$OUT/build-$side.log" 2>&1
    done
fi
if has run; then
    echo "== runs"
    export OUTDT=10
    "$tools/run_case.sh" coawst-test:triads-before "$OUT" before Reef_Ideal_A15_veg $TI $TJ $NWAV "$MIN" || status=1
    "$tools/run_case.sh" coawst-test:triads-after "$OUT" after Reef_Ideal_A15_veg $TI $TJ $NWAV "$MIN" || status=1
    SWANSED='/^TRIAD *$/d' \
    "$tools/run_case.sh" coawst-test:triads-after "$OUT" after-notriad Reef_Ideal_A15_veg $TI $TJ $NWAV "$MIN" || status=1
fi
if has check; then
    echo "== checks"
    "$PY" -I "$here/check.py" "$OUT" | tee "$OUT/check.txt" || status=1
fi
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
