#!/bin/bash
# Test of 1-fixes/roms-veg-streaming-fixes.patch: with BOTTOM_STREAMING and
# VEG_STREAMING, the wave streaming force must carry the wave momentum that
# SWAN's bottom friction and vegetation take out, (Dissip_fric + Dissip_veg) k/sigma.
#
#   tests/fixes/roms-veg-streaming-fixes/run.sh OUTDIR
#
# Builds (tests/cases/Reef_Ideal_A15_veg, the fixes series without and with this patch):
#   stream-before, stream-after   +BOTTOM_STREAMING +VEG_STREAMING
#   plain-before, plain-after     the case as it is (no streaming)
# Runs (tests/tools/run_case.sh, ROMS 1x2 + 2 SWAN): 111 steps; history at step 110
# (660 s), the momentum diagnostics of step 111 alone (NTSDIA 111, NDIA 1). The
# diagnostic is the Adams-Bashforth mix of steps 109-111, all after the 600 s wave
# exchange, so the wave fields are those of the history record. (Later, with the
# waves at full height, this explicit-drag test case blows up on the crest with the
# streaming force on: see the patch document.) The plain builds run 10 min, history every 2 min.
# Checks (check.py):
#   bug       before the patch the depth-integrated streaming force differs from
#             (Dissip_fric + Dissip_veg) k/sigma by more than 10 % (rms over the wave points)
#   fixed     after it, by less than 1 % (the inputs are SWAN's float32 output)
#   unchanged plain-before and plain-after: identical history
#   restart   with both options, a run writing restart records every 2 min, 20 min
#             straight against 10 + 10 min (tests/tools/restart_inside.sh): before the
#             patch writing the restart file fails; after it the restarted run is
#             bit-identical (u, v, ubar, vbar, zeta in the double-precision records)
# STAGES (default "build run check"). Needs Docker and Python with numpy and netCDF4 (PYTHON).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
root=$here/../../..
OUT=$(realpath -m "$1")
PY=${PYTHON:-python3}
STAGES=${STAGES:-build run check}
TI=${TI:-1} TJ=${TJ:-2} NWAV=${NWAV:-2}
P=1-fixes/roms-veg-streaming-fixes.patch
case=$root/tests/cases/Reef_Ideal_A15_veg
mkdir -p "$OUT"
has() { [[ " $STAGES " == *" $1 "* ]]; }
if has build; then
    echo "== build"
    { grep -vE '^[[:space:]]*(#|$)' "$root/build/coawst/patches/series" | grep '^1-fixes/'
      echo 2-improvements/swan-netcdf-output.patch
      echo 2-improvements/swan-periodic-curvilinear.patch; } > "$OUT/series-after"
    grep -vxF "$P" "$OUT/series-after" > "$OUT/series-before"
    for side in before after; do
        "$root/build/coawst/build.sh" --case "$case" --app REEF_IDEAL_A15 --series "$OUT/series-$side" \
            --tag coawst-test:vegstream-$side -- --build-arg CPP_OPTIONS="+BOTTOM_STREAMING +VEG_STREAMING" \
            > "$OUT/build-stream-$side.log" 2>&1
        "$root/build/coawst/build.sh" --case "$case" --app REEF_IDEAL_A15 --series "$OUT/series-$side" \
            --tag coawst-test:vegplain-$side > "$OUT/build-plain-$side.log" 2>&1
        echo "   $side: built"
    done
fi
if has run; then
    echo "== runs"
    for side in before after; do
        rm -rf "$OUT/stream-$side"
        OUTDT=10 OCEANSED='s/^( *NTIMES *== *)[0-9]+/\1111/; s/^( *NHIS *== *)[0-9]+/\1110/; s/^( *NTSDIA *== *)[0-9]+/\1111/; s/^( *NDIA *== *)[0-9]+/\11/' \
            "$tools/run_case.sh" coawst-test:vegstream-$side "$OUT" stream-$side Reef_Ideal_A15_veg $TI $TJ $NWAV 12 || true
        rm -rf "$OUT/plain-$side"
        OUTDT=2 "$tools/run_case.sh" coawst-test:vegplain-$side "$OUT" plain-$side Reef_Ideal_A15_veg $TI $TJ $NWAV 10 || true
        d=$OUT/restart-$side; rm -rf "$d"; mkdir -p "$d"; cp "$tools/"{restart_inside,case_inside}.sh "$d/"
        docker run --rm --user "$(id -u):$(id -g)" -v "$d:/work" -w /work -e OUTDT=2 \
            -e OCEANSED='s/^( *NRST *== *)[0-9]+/\120/' \
            coawst-test:vegstream-$side bash /work/restart_inside.sh Reef_Ideal_A15_veg 20 10 $TI $TJ $NWAV \
            > "$d/runner.log" 2>&1 || true
        echo "   restart-$side: $(grep -E '^(straight|part1|part2):' "$d/runner.log" | paste -sd' ')"
    done
fi
if has check; then
    echo "== checks"
    "$PY" -I "$here/check.py" "$OUT" | tee "$OUT/check.txt"
fi
