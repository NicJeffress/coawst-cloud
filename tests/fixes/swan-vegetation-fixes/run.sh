#!/bin/bash
# Test of 1-fixes/swan-vegetation-fixes.patch: COAWST's vegetation routine in
# SWAN (VEGETATION 3, SVEG_COAWST) and SWAN's plant input (veg3_young_modulus, veg3_flexible_plants, plant_input_grids, veg3_emergent_cd and dicd_output).
#
#   tests/fixes/swan-vegetation-fixes/run.sh SOURCE OUTDIR
#
# SOURCE: a COAWST tree or tarball at the pinned commit (for the source check).
#   1. Source check (check_source.py), before and after the patch:
#      veg3_flexible_plants  flexible-plant formulas (second moment of area, Cauchy number)
#      plant_input_grids plant height/diameter/thickness read on their own input grids
#   2. COAWST's Veg_test (ROMS + SWAN, VEG_SWAN_COUPLING) with SWAN's
#      VEGETATION 1 switched to VEGETATION 3, SWAN bounds-checked
#      (-fcheck=bounds), 10 min, DICD and DEPTH written every 5 min:
#        submerged  the case's plants (0.3 m in 1 m of water)
#        emergent   the same with 1.5 m plants (init file edited)
#      before: stops at once: Young's modulus VEGYML read but never allocated
#              (veg3_young_modulus)
#      after:  runs; DICD is written (dicd_output) and is the drag method's 1.0
#              also where plants stick out of the water (veg3_emergent_cd; stock: 1.95)
# Needs Docker and Python with numpy, scipy and netCDF4 (PYTHON). About 25 min.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
SRC=$1 OUT=$(realpath -m "$2")
PY=${PYTHON:-python3}
P=1-fixes/swan-vegetation-fixes.patch
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
    "$PY" -I "$here/check_source.py" "$OUT/src-$side/SWAN/src" | tee "$OUT/source-$side.txt" | sed 's/^/   /' || true
    rm -rf "$OUT/src-$side"
done
grep -q INCONSISTENT "$OUT/source-before.txt" || { echo "FAIL: stock source not flagged"; status=1; }
grep -qx CONSISTENT "$OUT/source-after.txt" || { echo "FAIL: patched source inconsistent"; status=1; }

echo "== 2. Veg_test with VEGETATION 3"
"$tools/build_pair.sh" $P coawst-test:vegsw --project Projects/Veg_test --app VEG_TEST -- \
    --build-arg SWAN_FFLAGS_EXTRA=-fcheck=bounds
# Veg_test's initial file with 1.5 m plants (emergent in 1 m of water)
docker run --rm -v "$OUT:/o" --user "$(id -u):$(id -g)" coawst-test:vegsw-after \
    cp /opt/coawst/Projects/Veg_test/init_veg_test.nc /o/init_veg_test.nc
"$PY" -I - "$OUT/init_veg_test.nc" "$OUT/init_emergent.nc" <<'EOF'
import shutil, sys
from netCDF4 import Dataset
shutil.copy(sys.argv[1], sys.argv[2])
with Dataset(sys.argv[2], "a") as d:
    h = d["plant_height"][:]
    h[h > 0] = 1.5
    d["plant_height"][:] = h
EOF
outreq="BLOCK 'COMPGRID' NOHEADER 'dicd.mat' LAY 4 DICD 1. OUTPUT 20000101.000000 5 MIN\nBLOCK 'COMPGRID' NOHEADER 'depth.mat' LAY 4 DEPTH 1. OUTPUT 20000101.000000 5 MIN"
export SWANSED="s/^VEGETATION 1 /VEGETATION 3 /; s#^(COMPUTE NONSTATIONARY)#${outreq}\n\1#"
args=(Projects/Veg_test coupling_veg_test.in ocean_veg_test.in swan_veg_test.in 1 1 1 10)
for side in before after; do
    "$tools/run_project.sh" coawst-test:vegsw-$side "$OUT" submerged-$side "${args[@]}" || true
    mkdir -p "$OUT/emergent-$side" && cp "$OUT/init_emergent.nc" "$OUT/emergent-$side/"
    OCEANSED="s#^( *ININAME *== *).*#\1init_emergent.nc#" \
        "$tools/run_project.sh" coawst-test:vegsw-$side "$OUT" emergent-$side "${args[@]}" || true
done
for r in submerged-before emergent-before; do
    if grep -q "array 'vegyml' above upper bound" "$OUT/$r/log.txt"; then
        echo "   $r: stops, VEGYML never allocated (veg3_young_modulus)          ok"
    else
        echo "   $r: did not stop at VEGYML                            BAD"; status=1
    fi
done
for r in submerged-after emergent-after; do
    if grep -q "Fortran runtime error" "$OUT/$r/log.txt"; then echo "   $r: run-time error  BAD"; status=1; fi
done
"$PY" -I "$here/check_runs.py" "$OUT/submerged-after" "$OUT/emergent-after" "$OUT/init_emergent.nc" \
    | tee "$OUT/check-after.txt" || status=1
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
