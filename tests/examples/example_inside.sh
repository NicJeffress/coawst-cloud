#!/bin/bash
# Run COAWST examples inside the sweep image (tests/examples/run.sh, stage
# pack), each with every build variant in turn, in the current folder.
#
#   example_inside.sh [NAME ...]
#
# NAME      examples from /opt/sweep/examples.tsv. None: the one numbered
#           BATCH_TASK_INDEX (0 = first row), so each Cloud Batch task runs one
#           example (all its variants on the same machine).
# VARIANTS  (environment) default: those packed (/opt/sweep/variants)
# TIMEOUT_MIN  (environment) limit per run, default 60
# MINUTES   (environment) run length for every example instead of the manifest's
#           (quick checks)
#
# Each run goes to NAME/VARIANT/: the edited input files, log.txt (model
# output), image_info.txt (patches, layout, exit status, outcome, wall time)
# and output/ (every file the run wrote). Input files are copied from the
# example folder and edited: process layout, run length (when the manifest
# gives minutes), and the coupling file's input and weight file names; paths
# inside them still work because Projects and ROMS are linked here.
# Outcome: finished, blew up (ROMS BLOWUP), error (another abnormal end, or
# for SWAN alone an Errfile; coawstM's SWAN writes no norm_end),
# failed (non-zero exit), timeout, no binary (the build failed).
set -uo pipefail
sweep=/opt/sweep
VARIANTS=${VARIANTS:-$(cat "$sweep/variants" 2>/dev/null || echo stock patched engine)}
rows() { grep -v '^#' "$sweep/examples.tsv" | grep -v '^[[:space:]]*$'; }
[ $# -gt 0 ] || set -- "$(rows | sed -n "$((${BATCH_TASK_INDEX:-0} + 1))p" | cut -f1)"
top=$PWD

# Number of values (= grids) on a ROMS input line, e.g. "DT == 60.0d0 10.0d0".
values() { sed -nE "s/^ *$2 *== *([^!]*).*/\1/p" "$1" | head -1; }

# ROMS input: every grid's tiles, and NTIMES from each grid's DT.
edit_ocean() {  # FILE TI TJ MINUTES
    local f=$1 ti=$2 tj=$3 min=$4 dts n ntimes="" d
    dts=$(values "$f" DT)
    n=$(echo "$dts" | wc -w)
    sed -i -E "s/^( *NtileI *== *)[^!]*/\1$(yes "$ti" | head -n "$n" | xargs) /; \
               s/^( *NtileJ *== *)[^!]*/\1$(yes "$tj" | head -n "$n" | xargs) /" "$f"
    [ "$min" = - ] && return 0
    for d in $dts; do
        ntimes="$ntimes $(awk -v m="$min" -v d="${d//[dD]/e}" 'BEGIN { printf "%d", m * 60 / d + 0.5 }')"
    done
    sed -i -E "s/^( *NTIMES *== *)[^!]*/\1${ntimes# } /" "$f"
}

# SWAN input: end of the COMPUTE period = start (2000-01-01 in every example)
# plus MINUTES.
edit_swan() {  # FILE MINUTES
    local f=$1 min=$2 end
    [ "$min" = - ] && return 0
    end=$(date -u -d "2000-01-01 00:00:00 UTC + $min minutes" +%Y%m%d.%H%M%S)
    sed -i -E "s/^(COMPUTE +NONSTAT[A-Z]* +20000101\.000000 +[0-9.]+ +[A-Z]+) +[0-9.]+/\1 $end/" "$f"
    grep -q "^COMPUTE.* $end" "$f" || { echo "could not set the SWAN end time in $f"; return 1; }
}

# File names after KEY in a COAWST coupling file, following "\" continuations.
coupling_files() {  # FILE KEY
    awk -v key="$2" '
        $0 ~ "^ *" key " *=" { on = 1; sub("^ *" key " *= *", "") }
        on { line = $0; sub(/!.*/, "", line); more = (line ~ /\\[ \t]*$/)
             gsub(/\\/, "", line); printf "%s ", line; if (!more) on = 0 }' "$1" | xargs
}

# Replace KEY's value (with its continuation lines) in a coupling file.
set_coupling() {  # FILE KEY VALUE...
    local f=$1 key=$2; shift 2
    awk -v key="$key" -v vals="$*" '
        skip { line = $0; sub(/!.*/, "", line); if (line !~ /\\[ \t]*$/) skip = 0; next }
        $0 ~ "^ *" key " *=" {
            line = $0; sub(/!.*/, "", line); skip = (line ~ /\\[ \t]*$/)
            n = split(vals, v, " ")
            for (i = 1; i <= n; i++)
                printf "%s%s%s\n", (i == 1 ? "   " key " = " : "              "), v[i], (i < n ? " \\" : "")
            next }
        { print }' "$f" > "$f.new" && mv "$f.new" "$f"
}

run_one() {  # NAME PROJECT MODE INPUT LAYOUT MINUTES VARIANT
    local name=$1 project=$2 mode=$3 input=$4 layout=$5 min=$6 v=$7
    local d=$top/$name/$v exe=$sweep/$v/$name/coawstM np args ti tj nwav i f swans=""
    rm -rf "$d"; mkdir -p "$d"; cd "$d" || return
    ln -sfn /opt/coawst/Projects Projects
    ln -sfn "$sweep/$v/ROMS" ROMS
    if [ ! -x "$exe" ]; then echo "outcome no binary" > image_info.txt; echo "$name $v: no binary"; return; fi
    read -r ti tj nwav <<< "$layout"
    case $mode in
        roms)
            cp "Projects/${project#Projects/}/$input" ocean.in
            edit_ocean ocean.in "$ti" "$tj" "$min"
            np=$((ti * tj)); args=ocean.in ;;
        swan)
            nwav=$ti; i=0
            for f in ${input//,/ }; do
                i=$((i + 1)); cp "Projects/${project#Projects/}/$f" "swan$i.in"
                edit_swan "swan$i.in" "$min" || return; swans="$swans swan$i.in"
            done
            np=$nwav; args=$swans ;;
        coupled)
            cp "Projects/${project#Projects/}/$input" coupling.in
            cp "$(coupling_files coupling.in OCN_name)" ocean.in
            edit_ocean ocean.in "$ti" "$tj" "$min"
            i=0
            for f in $(coupling_files coupling.in WAV_name); do
                i=$((i + 1)); cp "$f" "swan$i.in"
                edit_swan "swan$i.in" "$min" || return; swans="$swans swan$i.in"
            done
            set_coupling coupling.in OCN_name ocean.in
            # shellcheck disable=SC2086
            set_coupling coupling.in WAV_name $swans
            set_coupling coupling.in SCRIP_COAWST_NAME scrip_weights.nc
            sed -i -E "s/^( *NnodesOCN *= *)[0-9]+/\1$((ti * tj))/; s/^( *NnodesWAV *= *)[0-9]+/\1$nwav/" coupling.in
            np=$((ti * tj + nwav)); args=coupling.in ;;
    esac
    { cat "$sweep/$v/$name/PATCHES_APPLIED"
      echo "example $name ($project), variant $v, $mode, layout $layout, minutes $min, $np processes, $(nproc) vCPUs"
    } > image_info.txt
    touch .start
    local start status outcome
    start=$(date +%s)
    # shellcheck disable=SC2086
    timeout "${TIMEOUT_MIN:-60}m" mpirun --use-hwthread-cpus --bind-to none --oversubscribe -np "$np" "$exe" $args > log.txt 2>&1
    status=$?
    mkdir -p output
    find . -maxdepth 1 -type f -newer .start ! -name log.txt ! -name image_info.txt -exec mv {} output/ \;
    if [ $status -eq 124 ]; then outcome=timeout
    elif grep -q "Abnormal termination: BLOWUP" log.txt; then outcome="blew up"
    elif grep -q "Abnormal termination" log.txt; then outcome=error
    elif [ $status -ne 0 ]; then outcome=failed
    elif [ "$mode" = swan ] && [ -n "$(find output -iname 'errfile*' -size +0)" ]; then outcome=error
    elif [ "$mode" != swan ] && ! grep -q "ROMS: DONE" log.txt; then outcome=error
    else outcome=finished
    fi
    { echo "exit $status"; echo "outcome $outcome"; echo "wall_s $(($(date +%s) - start))"; } >> image_info.txt
    echo "$name $v: $outcome (exit $status, $(($(date +%s) - start)) s)"
}

for name in "$@"; do
    r=$(rows | awk -F'\t' -v n="$name" '$1 == n')
    [ -n "$r" ] || { echo "example_inside: no example $name"; continue; }
    IFS=$'\t' read -r _ project _ mode input layout min <<< "$r"
    min=${MINUTES:-$min}
    for v in $VARIANTS; do
        run_one "$name" "$project" "$mode" "$input" "$layout" "$min" "$v"
        cd "$top" || exit 1
    done
done
