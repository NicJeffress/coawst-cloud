#!/bin/bash
# Test of 1-fixes/swan-nc-crash.patch: SWAN's NetCDF output read and wrote past
# the end of a file name (nc_filename_length), and its NetCDF name table was indexed past
# its end (stnames_size).
#
#   tests/fixes/swan-nc-crash/run.sh OUTDIR
#
# Builds stock Inlet_test before and after the patch with SWAN compiled with
# gfortran's run-time checks (SWAN_FFLAGS_EXTRA=-fcheck=bounds), which stop the
# run at the first access past the end of an array or string, and runs 1 h:
#   shipped  the case as it is (BLOCK output hsig.nc)
#     before: stops in FOR (ocpmix): "Actual string length is shorter than the
#             declared one for dummy argument 'ddname' (11/140)"
#     after:  runs to the end, no run-time error
#   dirbot   plus a NetCDF request for DIRBOT (SWAN quantity 200)
#     before: stops: "Index '200' of dimension 1 of array 'stnames' above upper
#             bound of 171"
#     after:  no error about stnames (SWAN refuses the request, since DIRBOT
#             has no NetCDF name in stock SWAN; see swan-stop-on-input-errors)
# Without the checks the same accesses corrupt memory silently or crash at
# random (malloc errors on some machines). About 15 min on 4 vCPUs.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
OUT=$(realpath -m "$1")
mkdir -p "$OUT"
"$tools/build_pair.sh" 1-fixes/swan-nc-crash.patch coawst-test:nccrash -- \
    --build-arg SWAN_FFLAGS_EXTRA=-fcheck=bounds
dirbot="s#^(COMPUTE NONSTATIONARY)#BLOCK 'COMPGRID' NOHEADER 'wdirbot.nc' LAY 4 DIRBOT 1. OUTPUT 20000101.000000 1 HR\n\1#"
for side in before after; do
    "$tools/run_inlet.sh" coawst-test:nccrash-$side "$OUT" shipped-$side 1 1 1 1 || true
    SWANSED="$dirbot" "$tools/run_inlet.sh" coawst-test:nccrash-$side "$OUT" dirbot-$side 1 1 1 1 || true
done
status=0
check() { # run pattern expect(yes|no) description
    if grep -qE "$2" "$OUT/$1/log.txt"; then got=yes; else got=no; fi
    printf '   %-16s %-55s %s\n' "$1" "$4" "$([ $got = "$3" ] && echo ok || echo FAILED)"
    [ $got = "$3" ] || status=1
}
echo "== run-time errors (SWAN with -fcheck=bounds)"
check shipped-before "string length is shorter.*'ddname'" yes "stops in FOR: file name read past its end"
check shipped-after "Fortran runtime error" no "no run-time error"
check shipped-after "ROMS: DONE" yes "runs to the end"
check dirbot-before "array 'stnames' above upper bound" yes "stops: name table indexed past its end"
check dirbot-after "array 'stnames'" no "no error about the name table"
for r in shipped-before shipped-after dirbot-before dirbot-after; do
    echo "-- $r:"; grep -E "Fortran runtime error|At line" "$OUT/$r/log.txt" | head -2 | sed 's/^/   /' || true
done
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
