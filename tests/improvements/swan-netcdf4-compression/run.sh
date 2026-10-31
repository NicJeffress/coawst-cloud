#!/bin/bash
# Test of 2-improvements/swan-netcdf4-compression.patch: with OUT_NETCDF4 and
# DEFLATE, SWAN writes compressed NetCDF-4 files (as ROMS does), with exactly
# the same values; without them, nothing changes.
#
#   tests/improvements/swan-netcdf4-compression/run.sh OUTDIR
#
# Stock Inlet_test (Coupled), 1 h, ROMS 1x1 + 1 SWAN, three builds:
#   before        without the patch, CPP_OPTIONS="+OUT_NETCDF4 +DEFLATE":
#                 ROMS writes compressed NetCDF-4, SWAN classic files
#   after-classic with the patch, no options: SWAN classic files
#   after         with the patch and the options: SWAN compressed NetCDF-4
# SWAN output requested every 10 min, all as .nc: BLOCK fields on the
# computational grid (HSIGN, DIR, TM01, VEL, DISSIP, QB), TABLE at 9 points
# (HSIGN, DIR, TM01, DEPTH) and SPECOUT 2-D spectra at the same points.
# check.py: file formats and compression filters; every variable of every
# SWAN file and of the ROMS history identical between the runs; sizes.
# Needs Docker and Python with numpy and netCDF4 (PYTHON). About 15 min.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
build=$here/../../../build/coawst/build.sh
OUT=$(realpath -m "$1")
PY=${PYTHON:-python3}
P=2-improvements/swan-netcdf4-compression.patch
mkdir -p "$OUT"
"$tools/build_pair.sh" $P coawst-test:nc4 -- --build-arg CPP_OPTIONS="+OUT_NETCDF4 +DEFLATE"
"$tools/series_upto.sh" $P > "$OUT/series-after"
"$build" --series "$OUT/series-after" --tag coawst-test:nc4-after-classic > "$OUT/build-after-classic.log" 2>&1
echo coawst-test:nc4-after-classic

T="OUTPUT 20000101.000000 10 MIN"
req="POINTS 'pts' 4930. 9930. 5070. 9930. 5210. 9930. 4930. 10070. 5070. 10070. 5210. 10070. 4930. 10210. 5070. 10210. 5210. 10210."
for q in HSIGN DIR TM01 VEL DISSIP QB; do
    req="$req\nBLOCK 'COMPGRID' NOHEADER 'b_$(echo $q | tr 'A-Z' 'a-z').nc' LAY 4 $q 1. $T"
done
req="$req\nTABLE 'pts' NOHEADER 'pts.nc' HSIGN DIR TM01 DEPTH $T\nSPECOUT 'pts' SPEC2D ABS 'spec.nc' $T"
export SWANSED="s#^(COMPUTE NONSTATIONARY)#${req}\n\1#"
"$tools/run_inlet.sh" coawst-test:nc4-before "$OUT" before 1 1 1 1
"$tools/run_inlet.sh" coawst-test:nc4-after-classic "$OUT" after-classic 1 1 1 1
"$tools/run_inlet.sh" coawst-test:nc4-after "$OUT" after 1 1 1 1

status=0
"$PY" -I "$here/check.py" "$OUT" | tee "$OUT/check.txt" || status=1
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
