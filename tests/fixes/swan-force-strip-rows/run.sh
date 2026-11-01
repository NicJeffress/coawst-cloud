#!/bin/bash
# Test of 1-fixes/swan-force-strip-rows.patch: SWAN's BLOCK output of the
# wave-driven force (FORCE) lost the grid row (or column) at every boundary
# between the SWAN processes' strips.
#
#   tests/fixes/swan-force-strip-rows/run.sh OUTDIR
#
# COAWST's Inlet_test (coupled ROMS + SWAN, a 77 x 72 curvilinear grid, not
# periodic), built before and after the patch, 1 h, with FORCE added to its
# BLOCK output (.mat, every 30 min), on 1, 2 and 3 SWAN processes.
# check.py: before, FORCE on 2 and 3 processes has whole rows/columns missing
# that 1 process has; after, FORCE on 2 and 3 equals 1 process exactly; every
# other BLOCK output (depth, Hs, dissipation, ...) is bit-identical before and
# after, and on 1 process FORCE too; so is ROMS's history. Needs Docker and
# Python with numpy, scipy and netCDF4 (PYTHON). About 10 min to build, 15 min of runs on 4 vCPUs.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
OUT=$(realpath -m "$1")
PY=${PYTHON:-python3}
STAGES=${STAGES:-build run check}
mkdir -p "$OUT"
has() { [[ " $STAGES " == *" $1 "* ]]; }
if has build; then
    "$tools/build_pair.sh" 1-fixes/swan-force-strip-rows.patch coawst-test:forcerows
fi
if has run; then
    req="BLOCK 'COMPGRID' NOHEADER 'force.mat' LAY 4 FORCE 1. OUTPUT 20000101.000000 30 MIN"
    export SWANSED="s#^(COMPUTE NONSTATIONARY)#${req}\n\1#"
    for side in before after; do
        for nw in 1 2 3; do
            rm -rf "${OUT:?}/$side-${nw}swan"
            "$tools/run_inlet.sh" coawst-test:forcerows-$side "$OUT" $side-${nw}swan 1 1 $nw 1 || true
        done
    done
fi
status=0
if has check; then
    "$PY" -I "$here/check.py" "$OUT" | tee "$OUT/check.txt" || status=1
fi
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
