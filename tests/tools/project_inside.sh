#!/bin/bash
# Run a COAWST project inside a coawst image, in the current folder.
#
#   project_inside.sh PROJECT COUPLING OCEAN SWAN [TI TJ NWAV MINUTES]
#
# PROJECT   the project folder in the image, e.g. Projects/Veg_test
# COUPLING  its coupling input file name, e.g. coupling_veg_test.in
# OCEAN     its ROMS input file name, e.g. ocean_veg_test.in
# SWAN      its SWAN input file name, e.g. swan_veg_test.in
# TI TJ     ROMS tiles (default 1 1); NWAV SWAN processes (default 1)
# MINUTES   simulated minutes (default: as in the files)
# Environment: OCEANSED / SWANSED (sed -E scripts for the ROMS and SWAN inputs,
# applied last), MPIRUN_ARGS.
#
# The three input files are copied here and edited; everything else is read
# from the image (Projects and ROMS are linked here, so paths in the inputs
# work). The SWAN run must start at 20000101.000000 (true of COAWST's
# projects); its end is set to the start plus MINUTES. image_info.txt gets the
# COAWST commit, the applied patches, the layout and the wall time.
set -euo pipefail
P=$1 CPL=$2 OCN=$3 WAV=$4
TI=${5:-1} TJ=${6:-1} NWAV=${7:-1} MINUTES=${8:-}
NOCN=$((TI * TJ))
ln -sfn /opt/coawst/Projects Projects
ln -sfn /opt/coawst/ROMS ROMS
cp "/opt/coawst/$P/$CPL" coupling.in
cp "/opt/coawst/$P/$OCN" ocean.in
cp "/opt/coawst/$P/$WAV" swan.in
sed -i -E "s#^( *WAV_name *= *).*#\1swan.in#; s#^( *OCN_name *= *).*#\1ocean.in#" coupling.in
sed -i -E "s/^( *NnodesWAV *= *)[0-9]+/\1${NWAV}/; s/^( *NnodesOCN *= *)[0-9]+/\1${NOCN}/" coupling.in
# The run writes the interpolation weights file (projects on different ROMS
# and SWAN grids): here, since the project folder in the image is read-only.
sed -i -E "s#^( *SCRIP_COAWST_NAME *= *).*#\1scrip_weights.nc#" coupling.in
sed -i -E "s/^( *NtileI *== *)[0-9]+/\1${TI}/; s/^( *NtileJ *== *)[0-9]+/\1${TJ}/" ocean.in
if [ -n "$MINUTES" ]; then
    dt=$(sed -nE 's/^ *DT *== *([0-9.]+)d?0?.*/\1/p' ocean.in | head -1)
    nt=$(awk -v m="$MINUTES" -v dt="$dt" 'BEGIN { printf "%d", m * 60 / dt + 0.5 }')
    sed -i -E "s/^( *NTIMES *== *)[0-9]+/\1${nt}/" ocean.in
    end=$(date -u -d "2000-01-01 00:00:00 UTC + ${MINUTES} minutes" +%Y%m%d.%H%M%S)
    sed -i -E "s/^(COMPUTE +NONSTAT[A-Z]* +20000101\.000000 +[0-9.]+ +[A-Z]+) +[0-9.]+/\1 ${end}/" swan.in
    grep -q " ${end}" swan.in || { echo "project_inside: could not set the SWAN end time" >&2; exit 1; }
fi
if [ -n "${OCEANSED:-}" ]; then sed -i -E "$OCEANSED" ocean.in; fi
if [ -n "${SWANSED:-}" ]; then sed -i -E "$SWANSED" swan.in; fi
{ cat /opt/coawst/COAWST_COMMIT /opt/coawst/PATCHES_APPLIED
  echo "layout $P ROMS ${TI}x${TJ} + ${NWAV} SWAN, ${MINUTES:-as shipped} min, $(nproc) vCPUs"; } > image_info.txt
start=$(date +%s)
mpirun --use-hwthread-cpus --bind-to none ${MPIRUN_ARGS:-} -np $((NOCN + NWAV)) \
    coawstM coupling.in > log.txt 2>&1 || { tail -30 log.txt; exit 1; }
echo "wall_s $(($(date +%s) - start))" >> image_info.txt
