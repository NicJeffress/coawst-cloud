#!/bin/bash
# Test of 1-fixes/roms-roller-substeps.patch on tests/cases/Reef_Ideal_A15.
#
#   tests/fixes/roms-roller-substeps/run.sh OUTDIR [MINUTES]
#
# Idea: with ROLLER_RENIERS the roller area is advected by an explicit upwind
# step at the current plus the wave celerity, one step per baroclinic DT.
# On the A15 reef crest at DT 6 s its Courant number exceeds 1 and the run
# blows up about 22 min after the waves reach the reef. The patch takes as
# many sub-steps as that Courant number needs.
# Builds (the whole series without and with this patch):
#   roller-before, roller-after   +ROLLER_RENIERS
#   plain-before, plain-after     the case as it is (no roller)
# Runs of MINUTES (default 40), ROMS 1x2 + 2 SWAN, DT 6 s, WEC_ALPHA 0.5:
#   roller-before, roller-after
# Checks:
#   bug       roller-before blows up (ROMS "Blowing-up" in the log)
#   fixed     roller-after runs to the end, finite
#   unchanged plain-before and plain-after: identical executables
# STAGES (default "build run check"). Needs Docker.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
root=$here/../../..
OUT=$(realpath -m "$1") MIN=${2:-40}
STAGES=${STAGES:-build run check}
TI=${TI:-1} TJ=${TJ:-2} NWAV=${NWAV:-2}
P=1-fixes/roms-roller-substeps.patch
case=$root/tests/cases/Reef_Ideal_A15
export MPIRUN_ARGS=${MPIRUN_ARGS:---oversubscribe}
mkdir -p "$OUT"
has() { [[ " $STAGES " == *" $1 "* ]]; }
status=0
if has build; then
    echo "== build"
    grep -vE '^[[:space:]]*(#|$)' "$root/build/coawst/patches/series" > "$OUT/series-after"
    grep -vxF "$P" "$OUT/series-after" > "$OUT/series-before"
    for side in before after; do
        "$root/build/coawst/build.sh" --case "$case" --app REEF_IDEAL_A15 --series "$OUT/series-$side" \
            --tag coawst-test:roller-$side -- --build-arg CPP_OPTIONS="+ROLLER_RENIERS" > "$OUT/build-roller-$side.log" 2>&1
        "$root/build/coawst/build.sh" --case "$case" --app REEF_IDEAL_A15 --series "$OUT/series-$side" \
            --tag coawst-test:plain-$side > "$OUT/build-plain-$side.log" 2>&1
        docker run --rm --entrypoint md5sum coawst-test:plain-$side /opt/coawst/coawstM | cut -d' ' -f1 > "$OUT/md5-plain-$side"
    done
fi
if has run; then
    echo "== runs"
    export OUTDT=10 OCEANSED='s/^( *WEC_ALPHA *== *)[0-9.d+-]+/\10.5d0/'
    for side in before after; do
        "$tools/run_case.sh" coawst-test:roller-$side "$OUT" roller-$side Reef_Ideal_A15 $TI $TJ $NWAV "$MIN" || true
    done
fi
if has check; then
    echo "== checks"
    # ROMS reports a blow-up as "Blowing-up" or, in some builds, only as an error in
    # the time-stepping loop (main3d.F) with an absurd speed in the step listing
    if grep -q "Blowing-up\|Source: ROMS/Nonlinear/main3d.F" "$OUT/roller-before/log.txt"; then
        echo "   bug       roller-before blew up (step listing: $(grep -E '^ +[0-9]+ 0001' "$OUT/roller-before/log.txt" | tail -1 | xargs))    PASS"
    else
        echo "   bug       roller-before did not blow up    FAIL"; status=1
    fi
    if ! grep -q "Blowing-up" "$OUT/roller-after/log.txt" && grep -q "ROMS: DONE" "$OUT/roller-after/log.txt"; then
        echo "   fixed     roller-after ran $MIN min to the end    PASS"
    else
        echo "   fixed     roller-after did not finish cleanly    FAIL"; status=1
    fi
    if cmp -s "$OUT/md5-plain-before" "$OUT/md5-plain-after"; then
        echo "   unchanged builds without ROLLER_RENIERS: identical executables    PASS"
    else
        echo "   unchanged builds without ROLLER_RENIERS: executables differ    FAIL"; status=1
    fi
fi
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
