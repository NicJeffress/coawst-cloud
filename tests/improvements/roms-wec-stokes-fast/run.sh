#!/bin/bash
# Test of 2-improvements/roms-wec-stokes-fast.patch: the spectral Stokes drift
# computed with about 3x fewer SINH/COSH/EXP calls, same physics.
#
#   tests/improvements/roms-wec-stokes-fast/run.sh OUTDIR [MINUTES]
#
# Reef_Ideal_A15 (waves from SWAN, SPECTRUM_STOKES, the v3.9 default with SWAN
# coupling), built before and after the patch, both with PROFILE so ROMS
# prints the CPU time of each part (the Stokes drift is in "Waves Effect on
# Currents kernel"). Runs of MINUTES (default 60), ROMS 1x2 + 2 SWAN here
# (TI, TJ, NWAV).
# check.py: Stokes drift, currents, sea level and turbulence after the patch
# equal to before at rounding level (relative < 1e-5, i.e. the last bits of
# the single-precision history); the WEC kernel's CPU time before and after.
# STAGES (default "build run check"): with STAGES=build the two runs can be
# made elsewhere into OUTDIR/before and OUTDIR/after (case_inside.sh), then
# STAGES=check. Needs Docker and Python with numpy and netCDF4 (PYTHON).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
OUT=$(realpath -m "$1") MIN=${2:-60}
PY=${PYTHON:-python3}
STAGES=${STAGES:-build run check}
TI=${TI:-1} TJ=${TJ:-2} NWAV=${NWAV:-2}
mkdir -p "$OUT"
has() { [[ " $STAGES " == *" $1 "* ]]; }
if has build; then
    "$tools/build_pair.sh" 2-improvements/roms-wec-stokes-fast.patch coawst-test:stfast \
        --case "$here/../../cases/Reef_Ideal_A15" --app REEF_IDEAL_A15 -- --build-arg CPP_OPTIONS="+PROFILE"
fi
if has run; then
    for side in before after; do
        rm -rf "$OUT/$side"
        "$tools/run_case.sh" coawst-test:stfast-$side "$OUT" $side Reef_Ideal_A15 $TI $TJ $NWAV "$MIN" || true
    done
fi
status=0
if has check; then
    "$PY" -I "$here/check.py" "$OUT" | tee "$OUT/check.txt" || status=1
fi
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
