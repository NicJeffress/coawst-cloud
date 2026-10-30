#!/bin/bash
# Run COAWST's Inlet_test (Coupled) inside a coawst image, in the current folder.
# Called by run_inlet.sh (Docker on this machine) and usable unchanged on a batch
# system that starts the image itself.
#
#   inlet_inside.sh [TI TJ NWAV HOURS]
#
# TI TJ   ROMS tiles in i and j (default 1 1); NOCN = TI x TJ processes
# NWAV    SWAN processes (default 1)
# HOURS   simulated hours (default 12, the case as shipped)
# Environment: OCEANSED / SWANSED (sed -E scripts applied to the ocean and SWAN
# input files), MPIRUN_ARGS (extra mpirun arguments). MPI slots are hardware
# threads (--use-hwthread-cpus), so 4 processes fit on 4 vCPUs.
#
# The case's input files are copied here and edited; grid and forcing files are
# read from the image. ROMS and SWAN write their output here. image_info.txt
# gets the COAWST commit, the applied patches and the wall time.
set -euo pipefail
TI=${1:-1} TJ=${2:-1} NWAV=${3:-1} HOURS=${4:-12}
NOCN=$((TI * TJ))
C=/opt/coawst/Projects/Inlet_test/Coupled
ln -sfn /opt/coawst/Projects Projects
ln -sfn /opt/coawst/ROMS ROMS
cp $C/coupling_inlet_test.in coupling.in
cp $C/ocean_inlet_test.in ocean.in
cp $C/swan_inlet_test.in swan.in
sed -i -E "s#^( *WAV_name *= *).*#\1swan.in#; s#^( *OCN_name *= *).*#\1ocean.in#" coupling.in
sed -i -E "s/^( *NnodesWAV *= *)[0-9]+/\1${NWAV}/; s/^( *NnodesOCN *= *)[0-9]+/\1${NOCN}/" coupling.in
NT=$((HOURS * 60))                          # DT = 60 s
sed -i -E "s/^( *NtileI *== *)[0-9]+/\1${TI}/; s/^( *NtileJ *== *)[0-9]+/\1${TJ}/; s/^( *NTIMES *== *)[0-9]+/\1${NT}/" ocean.in
END=$(printf '20000101.%02d0000' "$HOURS")
sed -i -E "s/^(COMPUTE NONSTATIONARY 20000101.000000 60 SEC) [0-9.]+/\1 ${END}/" swan.in
if [ -n "${OCEANSED:-}" ]; then sed -i -E "$OCEANSED" ocean.in; fi
if [ -n "${SWANSED:-}" ]; then sed -i -E "$SWANSED" swan.in; fi
{ cat /opt/coawst/COAWST_COMMIT /opt/coawst/PATCHES_APPLIED
  echo "layout ROMS ${TI}x${TJ} + ${NWAV} SWAN, ${HOURS} h, $(nproc) vCPUs"; } > image_info.txt
start=$(date +%s)
mpirun --use-hwthread-cpus --bind-to none ${MPIRUN_ARGS:-} -np $((NOCN + NWAV)) \
    coawstM coupling.in > log.txt 2>&1 || { tail -30 log.txt; exit 1; }
echo "wall_s $(($(date +%s) - start))" >> image_info.txt
