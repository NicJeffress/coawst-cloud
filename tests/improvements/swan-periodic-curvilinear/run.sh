#!/bin/bash
# Test of 2-improvements/swan-periodic-curvilinear.patch: SWAN on periodic
# (REPEATING) curvilinear grids.
#
#   tests/improvements/swan-periodic-curvilinear/run.sh OUTDIR
#
# Standalone SWAN (tests/cases/Swan_Periodic_Test), an A15-like reef with a
# pass, waves from 20 deg east of north, 1 h; 12 cases from make_inputs.py
# (uniform and stretched grids, the seam moved through the pass, a flat reef,
# output across the seam, a bad closing column, Reef_Ideal_A15's own grid).
#   after   every case on 1 process (4 at a time), the five that test
#           parallel runs again on 4 processes
#   before  without the patch: str-mid (stock SWAN must refuse the grid) and
#           the three cases that do not need the patch (uni-reg-mid,
#           uni-reg-flat, str-norep), to check what else the patch changes
# check.py: PASS/FAIL per check; plot.py draws the figure of the document.
# Needs Docker and Python with numpy, netCDF4, matplotlib (PYTHON).
# About 20 min on 4 vCPUs (two builds, 20 short runs).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
OUT=$(realpath -m "$1")
PY=${PYTHON:-python3}
mkdir -p "$OUT"
"$tools/build_pair.sh" 2-improvements/swan-periodic-curvilinear.patch coawst-test:swancurv \
    --case "$here/../../cases/Swan_Periodic_Test" --app SWAN_PERIODIC_TEST
rm -rf "$OUT/inputs"
"$PY" -I "$here/make_inputs.py" "$OUT/inputs"

run() {   # run SIDE CASE NP: OUT/CASE-npNP (after) or OUT/CASE-npNP-before
    local side=$1 case=$2 np=$3 d
    d=$OUT/$case-np$np; [ "$side" = before ] && d=$d-before
    rm -rf "$d" && cp -r "$OUT/inputs/$case" "$d"
    local rc=0
    docker run --rm --user "$(id -u):$(id -g)" -v "$d:/run" -w /run "coawst-test:swancurv-$side" \
        mpirun --use-hwthread-cpus --bind-to none -np "$np" coawstM swan.in > "$d/log.txt" 2>&1 || rc=$?
    [ $rc = 0 ] && echo "   $(basename "$d"): done" || echo "   $(basename "$d"): stopped (exit $rc)"
}
export -f run
export OUT
SERIAL="uni-reg-mid uni-crv-mid uni-reg-flat str-mid str-seam str-flat str-search str-norep str-badper a15-mid a15-seam a15-norep"
PARALLEL="str-mid str-seam str-flat a15-mid a15-seam"
echo "== runs"
echo $SERIAL | tr ' ' '\n' | xargs -P 4 -I{} bash -c 'run after {} 1'
for c in str-mid uni-reg-mid uni-reg-flat str-norep; do run before $c 1 & done; wait
for c in $PARALLEL; do run after $c 4; done

status=0
"$PY" -I "$here/check.py" "$OUT" | tee "$OUT/check.txt" || status=1
"$PY" -I "$here/plot.py" "$OUT" "$OUT/swan-periodic-curvilinear.png" || true
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
