#!/bin/bash
# Restart test of a tests/cases case, inside a coawst image, in the current
# folder: one uninterrupted run and the same run stopped and restarted.
#
#   restart_inside.sh CASE TOTAL RST [TI TJ NWAV]
#
# CASE   folder under /opt/coawst/Projects (coupling.in, ocean.in, swan.in)
# TOTAL  simulated minutes; RST: minute of the restart (a multiple of the
#        coupling interval and of OUTDT)
# Runs, each in its own folder (straight/, part1/, part2/):
#   straight  0 -> TOTAL
#   part1     0 -> RST, writing ROMS's restart file (PERFECT_RESTART) and SWAN's
#             restart files (RESTART ... UNFORMATTED, one per SWAN process) at RST
#   part2     RST -> TOTAL from part1's restart files
# Environment: OUTDT (history and SWAN output every OUTDT minutes, default 10),
# NHISSTEP, OCEANSED, SWANSED, PREP (a command run in each run folder after the
# case is copied, e.g. to add a river file), MPIRUN_ARGS.
# Compare part2's last records with straight's (tests/tools/compare_nc.py --last).
set -uo pipefail
CASE=$1 TOTAL=$2 RST=$3 TI=${4:-} TJ=${5:-} NWAV=${6:-}
here=$(cd "$(dirname "$0")" && pwd)
export OUTDT=${OUTDT:-10}
top=$PWD
seg() { # name minutes ocean-sed swan-sed
    mkdir -p "$top/$1" && cd "$top/$1"
    cp -r "/opt/coawst/Projects/$CASE/." .
    if [ -n "${PREP:-}" ]; then bash -c "$PREP" || return 1; fi
    OCEANSED="$3${OCEANSED:+; $OCEANSED}" SWANSED="$4${SWANSED:+; $SWANSED}" \
        bash "$here/case_inside.sh" "$CASE" $TI $TJ $NWAV "$2"
    local rc=$?
    echo "$1: exit $rc, $(grep -m1 wall_s image_info.txt)"
    cd "$top"
    return $rc
}
dt=$(sed -nE 's/^ *DT *== *([0-9.]+)d?0?.*/\1/p' "/opt/coawst/Projects/$CASE/ocean.in" | head -1)
DT=${DT:-$dt}
nrst=$(awk -v m="$RST" -v d="$DT" 'BEGIN { printf "%d", m * 60 / d + 0.5 }')
nrest=$(awk -v m="$((TOTAL - RST))" -v d="$DT" 'BEGIN { printf "%d", m * 60 / d + 0.5 }')
t0=$(date -u -d "2000-01-01 00:00:00 UTC + ${RST} minutes" +%Y%m%d.%H%M%S)
# ROMS: restart record at RST, not cycled; SWAN: periodic binary restart files
# at RST (RESTART must come before COMPUTE to act during the run)
roms="s/^( *NRST *== *)[0-9]+/\1${nrst}/; s/^( *LcycleRST *== *)[TF]/\1F/"
swan="/^RESTART '/d; s#^(COMPUTE NONSTATIONARY )#RESTART 'output/swan_rst.dat' UNFORMATTED ${RST} MIN\n\1#"
# part2: ROMS from the last record of part1's restart file (on a restart ROMS
# runs NTIMES more steps), SWAN from part1's files
cont="s#^( *NRREC *== *)[-0-9]+#\1-1#; s#^( *ININAME *== *).*#\1../part1/output/ocean_rst.nc#; s#^( *NTIMES *== *)[0-9]+#\1${nrest}#"
# ($swan has already put the RESTART line and a newline in front of COMPUTE)
hot="s#(^|\n)COMPUTE NONSTATIONARY 20000101.000000 #\1INIT HOTSTART MULTIPLE '../part1/output/swan_rst.dat' UNFORMATTED\nCOMPUTE NONSTATIONARY ${t0} #"
status=0
seg straight "$TOTAL" "$roms" "$swan" || status=1
seg part1 "$RST" "$roms" "$swan" || status=1
# part2: MINUTES = TOTAL sets SWAN's end time; NTIMES (the remaining steps)
# and SWAN's start time are then set by $cont and $hot
seg part2 "$TOTAL" "$roms; $cont" "$swan; $hot" || status=1
exit $status
