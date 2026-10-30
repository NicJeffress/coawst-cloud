#!/bin/bash
# Test of 1-fixes/swan-output-fixes.patch: SWAN output at the wrong place or
# missing (items 6, 7 and 14).
#
#   tests/fixes/swan-output-fixes/run.sh OUTDIR
#
# Stock Inlet_test, 1 h, before and after the patch, with 1 and with 2 SWAN
# processes, plus output requests that show the bugs:
#   POINTS 'pts' at 9 locations between grid points, written as TABLE text
#   (pts.table) and as TABLE NetCDF (pts.nc); the case's own BLOCK hsig.nc.
# MALLOC_PERTURB_ fills newly allocated memory with a non-zero pattern, so the
# never-initialised flags of item 14 read "true" every time instead of at
# random (glibc feature; it does not change correct code).
# check.py compares: before, some checks are BAD; after, all ok.
# Needs Docker and Python with numpy and netCDF4 (PYTHON). About 20 min.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
OUT=$(realpath -m "$1")
PY=${PYTHON:-python3}
mkdir -p "$OUT"
"$tools/build_pair.sh" 1-fixes/swan-output-fixes.patch coawst-test:swanout
pts="POINTS 'pts' 4930. 9930. 5070. 9930. 5210. 9930. 4930. 10070. 5070. 10070. 5210. 10070. 4930. 10210. 5070. 10210. 5210. 10210."
req="$pts\nTABLE 'pts' NOHEADER 'pts.table' HSIGN OUTPUT 20000101.000000 10 MIN\nTABLE 'pts' NOHEADER 'pts.nc' HSIGN OUTPUT 20000101.000000 10 MIN"
export SWANSED="s#^(COMPUTE NONSTATIONARY)#${req}\n\1#"
export MALLOC_PERTURB_=85
for side in before after; do
    "$tools/run_inlet.sh" coawst-test:swanout-$side "$OUT" $side-1swan 1 1 1 1
    "$tools/run_inlet.sh" coawst-test:swanout-$side "$OUT" $side-2swan 1 1 2 1
done
status=0
for side in before after; do
    echo "== $side the patch"
    "$PY" -I "$here/check.py" "$OUT/$side-1swan" "$OUT/$side-2swan" | tee "$OUT/check-$side.txt" || true
done
grep -q "SOME CHECKS BAD" "$OUT/check-before.txt" || { echo "FAIL: no bug shown before the patch"; status=1; }
grep -q "ALL OK" "$OUT/check-after.txt" || { echo "FAIL: checks bad after the patch"; status=1; }
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
