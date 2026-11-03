#!/bin/bash
# Test of 1-fixes/roms-quicksave-uv.patch on tests/cases/Reef_Ideal_A15.
#
#   tests/fixes/roms-quicksave-uv/run.sh OUTDIR [MINUTES]
#
# Idea: the quicksave file (QCKNAME) defines the 3-D velocity u and v when
# Qout(idUvel) / Qout(idVvel) are T, but ROMS's standard NetCDF writer
# (wrt_quick_nf90) never wrote them (only the PIO writer did): they stayed
# fill values. With the patch they must equal the history file's u and v at
# the same times, and nothing else may change.
# Builds: the whole series without (before) and with (after) this patch. Runs of MINUTES (default
# 30), ROMS 1x2 + 2 SWAN, history and quicksave every 10 min, with
# Qout(idUvel) and Qout(idVvel) T. Checks (check.py):
#   bug       before: quicksave u, v are all fill values
#   fixed     after: quicksave u, v equal the history u, v at every common time
#   unchanged the history files bit-identical before and after
# STAGES (default "build run check"). Needs Docker and Python with numpy and
# netCDF4 (PYTHON).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
root=$here/../../..
OUT=$(realpath -m "$1") MIN=${2:-30}
PY=${PYTHON:-python3}
STAGES=${STAGES:-build run check}
TI=${TI:-1} TJ=${TJ:-2} NWAV=${NWAV:-2}
export MPIRUN_ARGS=${MPIRUN_ARGS:---oversubscribe}
mkdir -p "$OUT"
has() { [[ " $STAGES " == *" $1 "* ]]; }
status=0
if has build; then
    echo "== build"
    # the whole series without and with this patch (A15's periodic SWAN needs the
    # improvements tier, so build_pair.sh's series-up-to-the-patch does not run it)
    grep -vE '^[[:space:]]*(#|$)' "$root/build/coawst/patches/series" > "$OUT/series-after"
    grep -vxF 1-fixes/roms-quicksave-uv.patch "$OUT/series-after" > "$OUT/series-before"
    for side in before after; do
        "$root/build/coawst/build.sh" --case "$root/tests/cases/Reef_Ideal_A15" --app REEF_IDEAL_A15 \
            --series "$OUT/series-$side" --tag coawst-test:quickuv-$side > "$OUT/build-$side.log" 2>&1
    done
fi
if has run; then
    echo "== runs"
    export OUTDT=10
    # quicksave every 10 min (DT 6 s: 100 steps) with the 3-D velocity
    # (and into output/, which the runner copies back: the case's QCKNAME has no folder)
    export OCEANSED='s/^( *NQCK *== *)[0-9]+/\1100/; s/^(Qout\(id[UV]vel\) *== *)F/\1T/; s#^( *QCKNAME *== *).*#\1output/ocean_qck.nc#'
    for side in before after; do
        "$tools/run_case.sh" coawst-test:quickuv-$side "$OUT" $side Reef_Ideal_A15 $TI $TJ $NWAV "$MIN" || status=1
    done
fi
if has check; then
    echo "== checks"
    "$PY" -I "$here/check.py" "$OUT" | tee "$OUT/check.txt" || status=1
fi
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
