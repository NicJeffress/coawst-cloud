#!/bin/bash
# Test of 3-experimental/roms-bstress-implicit.patch (cpp option
# BSTRESS_IMPLICIT, with SSW_BBL): bottom stress taken implicitly instead of
# explicitly (and instead of LIMIT_BSTRESS's cap).
#
#   tests/experimental/roms-bstress-implicit/run.sh OUTDIR [MINUTES]
#
# Builds (whole series; all with -SPLINES_VVISC, which the option requires:
# its drag goes into the tridiagonal vertical viscosity solve) and runs,
# MINUTES each (default 60):
#   a15-exp, a15-imp          Reef_Ideal_A15 (no cap), without / with the option
#   circle-cap, circle-imp    Circle_Island with +LIMIT_BSTRESS (the cap the
#                             option replaces) / with +BSTRESS_IMPLICIT
# check.py reports whether each run finished and the differences (depth-mean
# currents, sea level, Hs). It is a record of what the option does, not a
# pass/fail accuracy test: on a realistic case the option failed (see the
# patch document). PASS if the A15 runs finished.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
root=$here/../../..
OUT=$(realpath -m "$1")
MIN=${2:-60}
PY=${PYTHON:-python3}
STAGES=${STAGES:-build run check}
export MPIRUN_ARGS=${MPIRUN_ARGS:---oversubscribe}
mkdir -p "$OUT"
has() { [[ " $STAGES " == *" $1 "* ]]; }
b() {   # b TAG CASE APP CPP
    "$root/build/coawst/build.sh" --case "$root/tests/cases/$2" --app $3 --tag coawst-test:bsi-$1 \
        ${4:+-- --build-arg CPP_OPTIONS="$4"} > "$OUT/build-$1.log" 2>&1
}
if has build; then
    b a15-exp Reef_Ideal_A15 REEF_IDEAL_A15 "-SPLINES_VVISC"
    b a15-imp Reef_Ideal_A15 REEF_IDEAL_A15 "-SPLINES_VVISC +BSTRESS_IMPLICIT"
    b circle-cap Circle_Island CIRCLE_ISLAND "-SPLINES_VVISC +LIMIT_BSTRESS"
    b circle-imp Circle_Island CIRCLE_ISLAND "-SPLINES_VVISC +BSTRESS_IMPLICIT"
fi
if has run; then
    export OUTDT=10
    for r in a15-exp a15-imp; do
        rm -rf "${OUT:?}/$r"; "$tools/run_case.sh" coawst-test:bsi-$r "$OUT" $r Reef_Ideal_A15 1 6 2 "$MIN" || true
    done
    for r in circle-cap circle-imp; do
        rm -rf "${OUT:?}/$r"; "$tools/run_case.sh" coawst-test:bsi-$r "$OUT" $r Circle_Island 6 1 2 "$MIN" || true
    done
fi
status=0
if has check; then
    "$PY" -I "$here/check.py" "$OUT" | tee "$OUT/check.txt" || status=1
fi
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
