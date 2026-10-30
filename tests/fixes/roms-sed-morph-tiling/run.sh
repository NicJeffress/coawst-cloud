#!/bin/bash
# Test of 1-fixes/roms-sed-morph-tiling.patch: with sediment morphology, ROMS
# results must not depend on how the grid is cut into MPI tiles.
#
#   tests/fixes/roms-sed-morph-tiling/run.sh OUTDIR [HOURS]
#
# Builds stock Inlet_test (SED_MORPH, Van der A bedload with WENO, MPDATA sand)
# before and after the patch, runs each with ROMS on 1x1 and on 1x2 tiles
# (1 SWAN process each, HOURS simulated hours, default 6; the third bug first
# shows after 3.4 h), and compares the last history record of 1x1 against 1x2.
#   before: the two tilings differ (bathymetry, sea level, currents, bed)
#   after:  bit-identical, and the 1x1 run equals the 1x1 run before the patch
#           (the patch changes nothing on one tile)
# Needs Docker and Python with numpy and netCDF4 (PYTHON, default python3).
# About 40 min on 4 vCPUs.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
OUT=$(realpath -m "$1") HOURS=${2:-6}
PY=${PYTHON:-python3}
mkdir -p "$OUT"
"$tools/build_pair.sh" 1-fixes/roms-sed-morph-tiling.patch coawst-test:sedtile
for side in before after; do
    "$tools/run_inlet.sh" coawst-test:sedtile-$side "$OUT" ${side}_1x1 1 1 1 "$HOURS"
    "$tools/run_inlet.sh" coawst-test:sedtile-$side "$OUT" ${side}_1x2 1 2 1 "$HOURS"
done
vars="bath zeta ubar vbar u v bed_thickness"
status=0
for side in before after; do
    echo "== $side the patch: ROMS 1x1 vs 1x2, last record"
    "$PY" -I "$tools/compare_nc.py" "$OUT/${side}_1x1/ocean_his_coupled.nc" \
        "$OUT/${side}_1x2/ocean_his_coupled.nc" $vars --last | tee "$OUT/compare_$side.txt" || true
done
echo "== one tile, before vs after the patch (must be identical)"
"$PY" -I "$tools/compare_nc.py" "$OUT/before_1x1/ocean_his_coupled.nc" \
    "$OUT/after_1x1/ocean_his_coupled.nc" $vars | tee "$OUT/compare_1x1.txt" || status=1
grep -q "DIFFERENCES FOUND" "$OUT/compare_before.txt" || { echo "FAIL: no tiling difference before the patch"; status=1; }
grep -q "ALL BIT-IDENTICAL" "$OUT/compare_after.txt" || { echo "FAIL: tilings differ after the patch"; status=1; }
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
