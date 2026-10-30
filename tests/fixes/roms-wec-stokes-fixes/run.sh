#!/bin/bash
# Test of 1-fixes/roms-wec-stokes-fixes.patch: the u-point spectral Stokes drift
# loop must mirror the v-point loop.
#
#   tests/fixes/roms-wec-stokes-fixes/run.sh SOURCE OUTDIR [HOURS]
#
# SOURCE is a COAWST tree or tarball at the pinned commit (e.g. a tarball in
# build/coawst/vendor/, or a clone of DOI-USGS/COAWST at COAWST_REF).
#   1. Source check (check_source.py) on the series before and after the patch:
#      before, the u loop averages one spectral field over the v-point
#      neighbour (i,j-1), adds bins up to kDmax instead of kD2deep, and computes
#      an unused SINH; after, both loops agree.
#   2. Effect: stock Inlet_test (SPECTRUM_STOKES, waves from SWAN) before and
#      after the patch, HOURS simulated hours (default 2), compared in the
#      Stokes drift and currents of the last history record, and wall time.
#      How large the change is depends on how fast the wave field varies
#      between neighbouring cells (2026-10-30: up to 3.7 % of u_stokes at the
#      inlet mouth). The step reports the differences; it does not pass or fail.
# Needs Docker and Python with numpy and netCDF4 (PYTHON, default python3).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
SRC=$1 OUT=$(realpath -m "$2") HOURS=${3:-2}
PY=${PYTHON:-python3}
P=1-fixes/roms-wec-stokes-fixes.patch
mkdir -p "$OUT"
status=0
echo "== 1. source check"
for side in before after; do
    if [ $side = before ]; then "$tools/series_upto.sh" $P --before > "$OUT/series-$side"
    else "$tools/series_upto.sh" $P > "$OUT/series-$side"; fi
    s=$OUT/series-$side; [ "$(cat "$s")" = none ] && s=none
    rm -rf "$OUT/src-$side"
    "$tools/patched_tree.sh" "$SRC" "$s" "$OUT/src-$side"
    echo "-- $side the patch"
    "$PY" -I "$here/check_source.py" "$OUT/src-$side/ROMS/Nonlinear/WEC/wec_stokes.F" \
        | tee "$OUT/source-$side.txt" | sed 's/^/   /' || true
    rm -rf "$OUT/src-$side"
done
grep -q INCONSISTENT "$OUT/source-before.txt" || { echo "FAIL: stock source not flagged"; status=1; }
grep -qx CONSISTENT "$OUT/source-after.txt" || { echo "FAIL: patched source inconsistent"; status=1; }
echo "== 2. Inlet_test, ${HOURS} h, before vs after"
"$tools/build_pair.sh" $P coawst-test:stokes
for side in before after; do
    "$tools/run_inlet.sh" coawst-test:stokes-$side "$OUT" run-$side 1 2 1 "$HOURS"
done
"$PY" -I "$tools/compare_nc.py" "$OUT/run-before/ocean_his_coupled.nc" \
    "$OUT/run-after/ocean_his_coupled.nc" u_stokes v_stokes ubar vbar zeta --last \
    | tee "$OUT/compare_runs.txt" || true
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
