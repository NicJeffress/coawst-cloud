#!/bin/bash
# Test of 3-experimental/roms-step2d-fb.patch (cpp option STEP2D_FB_AB3_AM4):
# the AB3-AM4 barotropic kernel against COAWST's LF-AM3 and a reference with
# smaller time steps, and its speed.
#
#   tests/experimental/roms-step2d-fb/run.sh OUTDIR [MINUTES]
#
# Builds (whole series, with PROFILE) Reef_Ideal_A15 and Circle_Island, each
# with LF-AM3 and with +STEP2D_FB_AB3_AM4, and runs each case for MINUTES
# (default 60) three ways:
#   lf    LF-AM3, the case's DT and NDTFAST
#   fb    AB3-AM4, the same DT and NDTFAST (one kernel call per fast step
#         instead of two, plus no auxiliary step)
#   ref   LF-AM3 with DT and the fast step both 4 times smaller (A15 DT 1.5 s,
#         Circle DT 1 s; NDTFAST unchanged)
# check.py: differences of lf and fb from ref at the end (each field, largest
# and RMS), lf vs fb, wall time and ROMS's PROFILE time of the 2-D kernel.
# STAGES (default "build run check"); with STAGES=build the runs can be made
# elsewhere into OUTDIR/<case>-<lf|fb|ref>/, then STAGES=check.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
root=$here/../../..
OUT=$(realpath -m "$1")
MIN=${2:-60}
PY=${PYTHON:-python3}
STAGES=${STAGES:-build run check}
mkdir -p "$OUT"
has() { [[ " $STAGES " == *" $1 "* ]]; }
if has build; then
    for c in "a15 Reef_Ideal_A15 REEF_IDEAL_A15" "circle Circle_Island CIRCLE_ISLAND"; do
        set -- $c
        "$root/build/coawst/build.sh" --case "$root/tests/cases/$2" --app $3 --tag coawst-test:fb-$1-lf \
            -- --build-arg CPP_OPTIONS="+PROFILE" > "$OUT/build-$1-lf.log" 2>&1
        "$root/build/coawst/build.sh" --case "$root/tests/cases/$2" --app $3 --tag coawst-test:fb-$1-fb \
            -- --build-arg CPP_OPTIONS="+PROFILE +STEP2D_FB_AB3_AM4" > "$OUT/build-$1-fb.log" 2>&1
    done
fi
if has run; then
    export OUTDT=10
    run() {   # run NAME IMAGE CASE TI TJ NWAV [DT NDTFAST]
        rm -rf "${OUT:?}/$1"
        DT=${7:-} OCEANSED=${8:+"s/^( *NDTFAST *== *)[0-9]+/\\1$8/"} \
            "$tools/run_case.sh" "$2" "$OUT" "$1" "$3" "$4" "$5" "$6" "$MIN" || true
    }
    run a15-lf coawst-test:fb-a15-lf Reef_Ideal_A15 1 6 2
    run a15-fb coawst-test:fb-a15-fb Reef_Ideal_A15 1 6 2
    run a15-ref coawst-test:fb-a15-lf Reef_Ideal_A15 1 6 2 1.5 24
    run circle-lf coawst-test:fb-circle-lf Circle_Island 6 1 2
    run circle-fb coawst-test:fb-circle-fb Circle_Island 6 1 2
    run circle-ref coawst-test:fb-circle-lf Circle_Island 6 1 2 1 10
fi
status=0
if has check; then
    "$PY" -I "$here/check.py" "$OUT" | tee "$OUT/check.txt" || status=1
fi
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
