#!/bin/bash
# Run a case whose input files name each other without paths (e.g. the
# idealized reef cases in tests/cases), inside a coawst image, in the current
# folder.
#
#   case_inside.sh CASE [TI TJ NWAV MINUTES]
#
# CASE      folder name under /opt/coawst/Projects in the image, e.g. Reef_Ideal_A15;
#           it must hold coupling.in, ocean.in and swan.in
# TI TJ     ROMS tiles (default 1 x NOCN from the case); NWAV SWAN processes
# MINUTES   simulated minutes (default: as in the files)
# Environment:
#   DT        ROMS baroclinic step in s (NDTFAST is set to keep the case's
#             barotropic step)
#   OUTDT     ROMS history and SWAN's BLOCK output every OUTDT minutes
#   NHISSTEP  ROMS history every NHISSTEP steps (applied after OUTDT)
#   OCEANSED, SWANSED  sed -E scripts for ocean.in / swan.in (applied last)
#   MPIRUN_ARGS
# The case folder is copied here; output goes to ./output. image_info.txt gets
# the COAWST commit, the applied patches, the layout and the wall time.
set -euo pipefail
CASE=$1
cp -r "/opt/coawst/Projects/$CASE/." .
mkdir -p output
ln -sfn /opt/coawst/ROMS ROMS
TI=${2:-} TJ=${3:-} NWAV=${4:-} MINUTES=${5:-}
[ -n "$TI" ] && sed -i -E "s/^( *NtileI *== *)[0-9]+/\1${TI}/; s/^( *NtileJ *== *)[0-9]+/\1${TJ}/" ocean.in
TI=$(sed -nE 's/^ *NtileI *== *([0-9]+).*/\1/p' ocean.in | head -1)
TJ=$(sed -nE 's/^ *NtileJ *== *([0-9]+).*/\1/p' ocean.in | head -1)
NOCN=$((TI * TJ))
[ -n "$NWAV" ] || NWAV=$(sed -nE 's/^ *NnodesWAV *= *([0-9]+).*/\1/p' coupling.in)
sed -i -E "s/^( *NnodesWAV *= *)[0-9]+/\1${NWAV}/; s/^( *NnodesOCN *= *)[0-9]+/\1${NOCN}/" coupling.in
dt0=$(sed -nE 's/^ *DT *== *([0-9.]+)d?0?.*/\1/p' ocean.in | head -1)
nf0=$(sed -nE 's/^ *NDTFAST *== *([0-9]+).*/\1/p' ocean.in | head -1)
DT=${DT:-$dt0}
if [ "$DT" != "$dt0" ]; then
    nf=$(awk -v d="$DT" -v d0="$dt0" -v n="$nf0" 'BEGIN { printf "%d", n * d / d0 + 0.5 }')
    sed -i -E "s/^( *DT *== *)[0-9.d]+/\1${DT}d0/; s/^( *NDTFAST *== *)[0-9]+/\1${nf}/" ocean.in
fi
steps() { awk -v m="$1" -v d="$DT" 'BEGIN { printf "%d", m * 60 / d + 0.5 }'; }
if [ -n "$MINUTES" ]; then
    sed -i -E "s/^( *NTIMES *== *)[0-9]+/\1$(steps "$MINUTES")/" ocean.in
    end=$(date -u -d "2000-01-01 00:00:00 UTC + ${MINUTES} minutes" +%Y%m%d.%H%M%S)
    sed -i -E "s/^(COMPUTE +NONSTAT[A-Z]* +20000101\.000000 +[0-9.]+ +[A-Z]+) +[0-9.]+/\1 ${end}/" swan.in
    grep -q " ${end}" swan.in || { echo "case_inside: could not set the SWAN end time" >&2; exit 1; }
fi
if [ -n "${OUTDT:-}" ]; then
    n=$(steps "$OUTDT")
    sed -i -E "s/^( *N(HIS|AVG|DIA) *== *)[0-9]+/\1${n}/" ocean.in
    sed -i -E "s#^(BLOCK '[A-Z]+' +NOHEADER +'[^']+' +LAY 4 +[A-Z0-9]+ +1\.) *\$#\1 OUTPUT 20000101.000000 ${OUTDT} MIN#" swan.in
fi
[ -n "${NHISSTEP:-}" ] && sed -i -E "s/^( *NHIS *== *)[0-9]+/\1${NHISSTEP}/" ocean.in
if [ -n "${OCEANSED:-}" ]; then sed -i -E "$OCEANSED" ocean.in; fi
if [ -n "${SWANSED:-}" ]; then sed -i -E "$SWANSED" swan.in; fi
{ cat /opt/coawst/COAWST_COMMIT /opt/coawst/PATCHES_APPLIED
  echo "layout $CASE ROMS ${TI}x${TJ} + ${NWAV} SWAN, ${MINUTES:-as in the files} min, DT ${DT} s, $(nproc) vCPUs"; } > image_info.txt
start=$(date +%s)
rc=0
mpirun --use-hwthread-cpus --bind-to none ${MPIRUN_ARGS:-} -np $((NOCN + NWAV)) \
    coawstM coupling.in > log.txt 2>&1 || rc=$?
echo "wall_s $(($(date +%s) - start)) exit $rc" >> image_info.txt
exit $rc
