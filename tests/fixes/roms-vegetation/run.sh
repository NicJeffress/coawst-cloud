#!/bin/bash
# Test of 1-fixes/roms-vegetation.patch on tests/cases/Reef_Ideal_A15_veg.
#
#   tests/fixes/roms-vegetation/run.sh SOURCE OUTDIR
#
# SOURCE: a COAWST tree or tarball at the pinned commit (for the source check).
# STAGES (default "source build run check") picks steps, e.g. STAGES="build"
# to build the images and run the cases elsewhere (each run in OUTDIR/<name>
# as tests/tools/run_case.sh makes it), then STAGES="check".
#
# The case needs periodic curvilinear SWAN and its NetCDF output, so every
# build borrows two improvements:
#   series S = the fixes in patches/series + 2-improvements/swan-netcdf-output
#              + 2-improvements/swan-periodic-curvilinear
#   before:  S without roms-vegetation.patch
#   after:   S
#   nounits: S with roms-vegetation.patch minus tau_veg_units (one line)
# Runs (ROMS 1x2 + 2 SWAN here; on 8 vCPUs use TI=1 TJ=6):
#   before    30 min   the case          -> ROMS crashes at the start (drag_work_array)
#   after     60 min   the case          -> runs
#   zerogap   10 min   plants 0.5 m thick (diameter x thickness x density = 1)
#                                        -> stops with a message (zero_gap_stop)
#   nounits   60 min   the case          -> canopy eddy viscosity vs after
# Source check (check_source.py) before and after the patch.
# Needs Docker and Python with numpy and netCDF4 (PYTHON). About 1.5 h on 4 vCPUs.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
root=$here/../../..
SRC=$1 OUT=$(realpath -m "$2")
PY=${PYTHON:-python3}
STAGES=${STAGES:-source build run check}
TI=${TI:-1} TJ=${TJ:-2} NWAV=${NWAV:-2}
P=1-fixes/roms-vegetation.patch
case=$root/tests/cases/Reef_Ideal_A15_veg
mkdir -p "$OUT"
has() { [[ " $STAGES " == *" $1 "* ]]; }
status=0
if has source; then
    echo "== source check"
    for side in before after; do
        if [ $side = before ]; then "$tools/series_upto.sh" $P --before > "$OUT/series-src"
        else "$tools/series_upto.sh" $P > "$OUT/series-src"; fi
        rm -rf "$OUT/src"; "$tools/patched_tree.sh" "$SRC" "$OUT/series-src" "$OUT/src"
        echo "-- $side the patch"
        "$PY" -I "$here/check_source.py" "$OUT/src" | tee "$OUT/source-$side.txt" | sed 's/^/   /' || true
        rm -rf "$OUT/src"
    done
    grep -q INCONSISTENT "$OUT/source-before.txt" || { echo "FAIL: stock source not flagged"; status=1; }
    grep -qx CONSISTENT "$OUT/source-after.txt" || { echo "FAIL: patched source inconsistent"; status=1; }
fi
if has build; then
    echo "== build"
    { grep -vE '^[[:space:]]*(#|$)' "$root/build/coawst/patches/series" | grep '^1-fixes/'
      echo 2-improvements/swan-netcdf-output.patch
      echo 2-improvements/swan-periodic-curvilinear.patch; } > "$OUT/series-after"
    grep -vxF "$P" "$OUT/series-after" > "$OUT/series-before"
    # nounits: the patch with tau_veg computed from the work integrated over the cell
    rm -rf "$OUT/patches-nounits"; cp -r "$root/build/coawst/patches" "$OUT/patches-nounits"
    sed -i 's#^+              Pveg=tke_loc_veg/(0.5_r8\*(Hz(i,j,k)+Hz(i,j,k+1)))$#+              Pveg=tke_loc_veg#' \
        "$OUT/patches-nounits/$P"
    grep -q '^+              Pveg=tke_loc_veg$' "$OUT/patches-nounits/$P"
    b() { "$root/build/coawst/build.sh" --case "$case" --app REEF_IDEAL_A15 "$@"; }
    b --series "$OUT/series-before" --tag coawst-test:veg-before > "$OUT/build-before.log" 2>&1
    b --series "$OUT/series-after" --tag coawst-test:veg-after > "$OUT/build-after.log" 2>&1
    b --series "$OUT/series-after" --patch-dir "$OUT/patches-nounits" --tag coawst-test:veg-nounits \
        > "$OUT/build-nounits.log" 2>&1
    # the case's initial file with 0.5 m thick plants
    "$PY" -I - "$case/init_reef.nc" "$OUT/init_zero_gap.nc" <<'EOF'
import shutil, sys
from netCDF4 import Dataset
shutil.copy(sys.argv[1], sys.argv[2])
with Dataset(sys.argv[2], "a") as d:
    t = d["plant_thickness"][:]
    t[t > 0] = 0.5
    d["plant_thickness"][:] = t
EOF
    echo "   images coawst-test:veg-before, -after, -nounits; $OUT/init_zero_gap.nc"
fi
if has run; then
    echo "== runs"
    r() { "$tools/run_case.sh" "$@" || true; }
    r coawst-test:veg-before "$OUT" before Reef_Ideal_A15_veg $TI $TJ $NWAV 30
    OUTDT=30 r coawst-test:veg-after "$OUT" after Reef_Ideal_A15_veg $TI $TJ $NWAV 60
    mkdir -p "$OUT/zerogap" && cp "$OUT/init_zero_gap.nc" "$OUT/zerogap/"
    OCEANSED="s#^( *ININAME *== *).*#\1init_zero_gap.nc#" \
        r coawst-test:veg-after "$OUT" zerogap Reef_Ideal_A15_veg $TI $TJ $NWAV 10
    OUTDT=30 r coawst-test:veg-nounits "$OUT" nounits Reef_Ideal_A15_veg $TI $TJ $NWAV 60
fi
if has check; then
    echo "== checks"
    "$PY" -I "$here/check_runs.py" "$OUT" | tee "$OUT/check.txt" || status=1
fi
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
