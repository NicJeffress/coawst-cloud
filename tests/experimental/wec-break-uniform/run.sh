#!/bin/bash
# Test of 3-experimental/wec-break-uniform.patch (cpp option
# WEC_BREAK_UNIFORM): the WEC_VF breaking acceleration spread evenly over the
# water column instead of concentrated near the surface (a sensitivity
# switch).
#
#   tests/experimental/wec-break-uniform/run.sh OUTDIR [MINUTES]
#
# Reef_Ideal_A15 (whole series; DIAGNOSTICS_UV is on in the case) without and
# with +WEC_BREAK_UNIFORM, MINUTES each (default 60), ROMS 1x6 + 2 SWAN.
# check.py: in the columns with the strongest breaking, how the breaking
# acceleration (ocean_dia.nc u_wbrk, v_wbrk) varies over depth (top over
# bottom layer): surface-intensified without, even with the option; and the
# difference it makes to the currents. PASS if the option's profile is even
# (top/bottom within 1 %) and the default one is not.
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
if has build; then
    for v in default uniform; do
        opt=""; [ $v = uniform ] && opt="+WEC_BREAK_UNIFORM"
        "$root/build/coawst/build.sh" --case "$root/tests/cases/Reef_Ideal_A15" --app REEF_IDEAL_A15 \
            --tag coawst-test:wbu-$v ${opt:+-- --build-arg CPP_OPTIONS="$opt"} > "$OUT/build-$v.log" 2>&1
    done
fi
if has run; then
    export OUTDT=10
    for v in default uniform; do
        rm -rf "${OUT:?}/$v"; "$tools/run_case.sh" coawst-test:wbu-$v "$OUT" $v Reef_Ideal_A15 1 6 2 "$MIN" || true
    done
fi
status=0
if has check; then
    "$PY" -I "$here/check.py" "$OUT" | tee "$OUT/check.txt" || status=1
fi
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
