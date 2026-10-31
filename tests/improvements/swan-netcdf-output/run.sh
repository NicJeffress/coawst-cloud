#!/bin/bash
# Test of 2-improvements/swan-netcdf-output.patch: SWAN writes every 2-D
# output quantity as NetCDF, at full (32-bit float) precision, and nothing
# else changes.
#
#   tests/improvements/swan-netcdf-output/run.sh OUTDIR
#
# Stock Inlet_test (Coupled), 1 h, ROMS 1x1 + 1 SWAN, before and after the
# patch. Each quantity is requested twice, as BLOCK .nc and as BLOCK .mat
# (SWAN's MATLAB output, single precision, the reference), every 30 min:
#   before-same  without the patch: the 7 quantities stock SWAN writes as .nc
#   after-same   with it: the same requests
#   after-all    with it: those 7 plus 18 quantities the patch adds
#   before-new   without it: DISSIP as .nc, which stock SWAN refuses
# check.py: before-same and after-same bit-identical (.mat files, ROMS
# history); .nc equal to .mat after the patch, off by up to half a packing
# step before; every added quantity equal to its .mat; the refusal.
# plot_precision.py draws docs/figures/swan-netcdf-output.png.
# Needs Docker and Python with numpy, scipy, netCDF4, matplotlib (PYTHON).
# About 10 min (two builds, four 1-min runs).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
OUT=$(realpath -m "$1")
PY=${PYTHON:-python3}
mkdir -p "$OUT"
"$tools/build_pair.sh" 2-improvements/swan-netcdf-output.patch coawst-test:ncout

# BLOCK requests for each quantity: n_<q>.nc and m_<q>.mat
blocks() {
    local r="" q lq
    for q in "$@"; do
        lq=$(echo "$q" | tr 'A-Z' 'a-z')
        r="$r\nBLOCK 'COMPGRID' NOHEADER 'n_$lq.nc' LAY 4 $q 1. OUTPUT 20000101.000000 30 MIN"
        r="$r\nBLOCK 'COMPGRID' NOHEADER 'm_$lq.mat' LAY 4 $q 1. OUTPUT 20000101.000000 30 MIN"
    done
    echo "${r#\\n}"
}
stock=(DEPTH WATLEV BOTLEV VEL HSIGN RTP UBOT)
added=(FRCOEF DISSIP TMBOT QB TRANSP FORCE STEEPNESS PER RPER URSELL DISBOT DISSURF
       DISWCAP GENERAT REDIST PROPAGAT RADSTR TDIR)
run() {   # image side, run name, requests
    SWANSED="s#^(COMPUTE NONSTATIONARY)#$3\n\1#" \
        "$tools/run_inlet.sh" "coawst-test:ncout-$1" "$OUT" "$2" 1 1 1 1 || true
}
run before before-same "$(blocks "${stock[@]}")"
run after after-same "$(blocks "${stock[@]}")"
run after after-all "$(blocks "${stock[@]}" "${added[@]}")"
run before before-new "BLOCK 'COMPGRID' NOHEADER 'n_dissip.nc' LAY 4 DISSIP 1. OUTPUT 20000101.000000 30 MIN"

status=0
"$PY" -I "$here/check.py" "$OUT" | tee "$OUT/check.txt" || status=1
"$PY" -I "$here/plot_precision.py" "$OUT" "$OUT/swan-netcdf-output.png" || true
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
