#!/bin/bash
# Test of 1-fixes/swan-stop-on-input-errors.patch: when SWAN reports errors in
# its input, the whole coupled run must stop, with SWAN's PRINT file saying why.
#
#   tests/fixes/swan-stop-on-input-errors/run.sh OUTDIR
#
# Stock Inlet_test with one output request SWAN refuses (BLOCK ... 'wdirbot.nc'
# DIRBOT: no NetCDF name for this quantity in stock SWAN, error level 2), built
# before and after the patch with SWAN's run-time checks (-fcheck=bounds), 1 h:
#   before: SWAN prints "No start of computation", COAWST carries on into the
#           run, and the first output with the refused request goes out of
#           bounds (run-time error in swanout1)
#   after:  the MPI job stops at once ("SWAN input error level  2 > MAXERR");
#           no run-time error; the PRINT file holds SWAN's error message
# About 15 min on 4 vCPUs.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
OUT=$(realpath -m "$1")
mkdir -p "$OUT"
"$tools/build_pair.sh" 1-fixes/swan-stop-on-input-errors.patch coawst-test:stoperr -- \
    --build-arg SWAN_FFLAGS_EXTRA=-fcheck=bounds
dirbot="s#^(COMPUTE NONSTATIONARY)#BLOCK 'COMPGRID' NOHEADER 'wdirbot.nc' LAY 4 DIRBOT 1. OUTPUT 20000101.000000 1 HR\n\1#"
for side in before after; do
    SWANSED="$dirbot" "$tools/run_inlet.sh" coawst-test:stoperr-$side "$OUT" $side 1 1 1 1 || true
done
status=0
check() { # run file pattern expect description
    if grep -qE "$3" "$OUT/$1"/$2 2>/dev/null; then got=yes; else got=no; fi
    printf '   %-7s %-60s %s\n' "$1" "$5" "$([ $got = "$4" ] && echo ok || echo FAILED)"
    [ $got = "$4" ] || status=1
}
check before log.txt "No start of computation|Fortran runtime error" yes "SWAN refuses the input but the run carries on"
check before log.txt "Fortran runtime error" yes "and goes out of bounds"
check after log.txt "SWAN input error level +2 > MAXERR" yes "stops: SWAN input error level 2 > MAXERR"
check after log.txt "Fortran runtime error" no "no run-time error"
check after "PRINT*" "netCDF output not allowed for wdirbot.nc" yes "PRINT file says what was wrong"
for r in before after; do
    echo "-- $r, log:"; grep -E "Fortran runtime error|At line|MAXERR|No start" "$OUT/$r/log.txt" | head -4 | sed 's/^/   /' || true
done
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
