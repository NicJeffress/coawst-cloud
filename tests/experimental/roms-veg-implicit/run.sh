#!/bin/bash
# Test of 3-experimental/roms-veg-implicit.patch (cpp option
# VEG_DRAG_IMPLICIT): canopy drag taken implicitly, so a dense canopy no
# longer limits the time step.
#
#   tests/experimental/roms-veg-implicit/run.sh OUTDIR [MINUTES]
#
# Reef_Ideal_A15_veg (waves, tide, GLS, canopy drag and turbulence) built with
# the whole series, without and with +VEG_DRAG_IMPLICIT, from a copy of the
# case folder that also holds the patchy canopy of make_patchy_init.py
# (dense 4 m-2, sparse 1 m-2, bare, ~150 m patches over the reef). Runs, MINUTES
# each (default 60, ROMS TI x TJ + NWAV SWAN, default 1x6 + 2):
#   patchy-exp-dt6   explicit drag, DT 6 s (the case's): expected to blow up
#   patchy-imp-dt6   implicit, DT 6 s
#   patchy-exp-dt3   explicit, DT 3 s: the reference
#   patchy-imp-dt3   implicit, DT 3 s
#   const-exp-dt6, const-imp-dt6   the case's own uniform canopy
# check.py: the explicit DT 6 s run blows up (or not, reported); the implicit
# runs finish; implicit vs explicit differences (depth-mean currents, Hs).
# STAGES (default "build run check"); with STAGES=build the runs can be made
# elsewhere into OUTDIR/<run>/ (the initial file is OUTDIR/init_reef_patchy.nc;
# point ININAME to it), then STAGES=check.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
root=$here/../../..
OUT=$(realpath -m "$1")
MIN=${2:-60}
PY=${PYTHON:-python3}
STAGES=${STAGES:-build run check}
TI=${TI:-1} TJ=${TJ:-6} NWAV=${NWAV:-2}
export MPIRUN_ARGS=${MPIRUN_ARGS:---oversubscribe}
mkdir -p "$OUT"
has() { [[ " $STAGES " == *" $1 "* ]]; }
if has build; then
    rm -rf "$OUT/Reef_Ideal_A15_veg" && cp -r "$root/tests/cases/Reef_Ideal_A15_veg" "$OUT/"
    "$PY" -I "$OUT/Reef_Ideal_A15_veg/make_patchy_init.py" "$OUT/Reef_Ideal_A15_veg/init_reef_patchy.nc"
    cp "$OUT/Reef_Ideal_A15_veg/init_reef_patchy.nc" "$OUT/"
    for v in exp imp; do
        opt=""; [ $v = imp ] && opt="+VEG_DRAG_IMPLICIT"
        "$root/build/coawst/build.sh" --case "$OUT/Reef_Ideal_A15_veg" --app REEF_IDEAL_A15 \
            --tag coawst-test:vegimp-$v ${opt:+-- --build-arg CPP_OPTIONS="$opt"} > "$OUT/build-$v.log" 2>&1
    done
fi
if has run; then
    export OUTDT=10
    PATCHY='s/^( *ININAME *== *).*/\1init_reef_patchy.nc/'
    run() {   # run NAME exp|imp DT [patchy]
        rm -rf "${OUT:?}/$1"
        DT=$3 OCEANSED=${4:+$PATCHY} "$tools/run_case.sh" coawst-test:vegimp-$2 "$OUT" "$1" \
            Reef_Ideal_A15_veg $TI $TJ $NWAV "$MIN" || true
    }
    run patchy-exp-dt6 exp 6 patchy
    run patchy-imp-dt6 imp 6 patchy
    run patchy-exp-dt3 exp 3 patchy
    run patchy-imp-dt3 imp 3 patchy
    run const-exp-dt6 exp 6
    run const-imp-dt6 imp 6
fi
status=0
if has check; then
    "$PY" -I "$here/check.py" "$OUT" | tee "$OUT/check.txt" || status=1
fi
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
