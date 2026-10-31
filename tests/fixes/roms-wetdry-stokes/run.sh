#!/bin/bash
# Test of 1-fixes/roms-wetdry-stokes.patch on tests/cases/Reef_Ideal_A15.
#
#   tests/fixes/roms-wetdry-stokes/run.sh OUTDIR [MINUTES]
#
# Idea: A15 never dries (shallowest water 0.35 m at low tide, drying threshold
# DCRIT 0.10 m), so switching wetting and drying on must not change the flow
# much. With WET_DRY, waves (WEC) and the LF-AM3 barotropic step, COAWST drops
# the Stokes transport towards -i and -j in the first predictor sub-step of
# every baroclinic step, so it does change: that difference is the bug.
# Builds (all with the fixes + the borrowed swan-netcdf-output and
# swan-periodic-curvilinear that A15's SWAN setup needs):
#   wd-before    +WET_DRY, the series without this patch
#   wd-after     +WET_DRY, the series with it
#   nowd-before  +LIMIT_BSTRESS (the bottom-stress cap WET_DRY brings, without
#                wetting and drying), without this patch
#   nowd-after   +LIMIT_BSTRESS, with this patch
# Checks:
#   nowd-before and nowd-after: identical executables (the patch touches only
#   WET_DRY code)
#   runs of MINUTES (default 60), ROMS 1x2 + 2 SWAN (TI, TJ, NWAV):
#     wd-before vs nowd: large difference (Stokes transport dropped)
#     wd-after  vs nowd: small (only the other, minor WET_DRY effects remain)
# STAGES (default "build run check") as in the other tests: build the images,
# run wd-before, wd-after, nowd elsewhere into OUTDIR/<name>, then check.
# Needs Docker and Python with numpy and netCDF4 (PYTHON).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
root=$here/../../..
OUT=$(realpath -m "$1") MIN=${2:-60}
PY=${PYTHON:-python3}
STAGES=${STAGES:-build run check}
TI=${TI:-1} TJ=${TJ:-2} NWAV=${NWAV:-2}
P=1-fixes/roms-wetdry-stokes.patch
case=$root/tests/cases/Reef_Ideal_A15
mkdir -p "$OUT"
has() { [[ " $STAGES " == *" $1 "* ]]; }
status=0
if has build; then
    echo "== build"
    { grep -vE '^[[:space:]]*(#|$)' "$root/build/coawst/patches/series" | grep '^1-fixes/'
      echo 2-improvements/swan-netcdf-output.patch
      echo 2-improvements/swan-periodic-curvilinear.patch; } > "$OUT/series-after"
    grep -vxF "$P" "$OUT/series-after" > "$OUT/series-before"
    for side in before after; do
        for v in wd nowd; do
            [ $v = wd ] && opt="+WET_DRY" || opt="+LIMIT_BSTRESS"
            "$root/build/coawst/build.sh" --case "$case" --app REEF_IDEAL_A15 --series "$OUT/series-$side" \
                --tag coawst-test:wetdry-$v-$side -- --build-arg CPP_OPTIONS="$opt" \
                > "$OUT/build-$v-$side.log" 2>&1
        done
    done
    for side in before after; do
        docker run --rm coawst-test:wetdry-nowd-$side md5sum /opt/coawst/coawstM | cut -d' ' -f1 > "$OUT/md5-nowd-$side"
    done
    echo "   coawstM without WET_DRY: before $(cat "$OUT/md5-nowd-before"), after $(cat "$OUT/md5-nowd-after")"
fi
if has run; then
    echo "== runs"
    for r in wd-before wd-after nowd-after; do
        OUTDT=10 "$tools/run_case.sh" coawst-test:wetdry-$r "$OUT" $r Reef_Ideal_A15 $TI $TJ $NWAV "$MIN" || true
    done
fi
if has check; then
    echo "== checks"
    if [ -f "$OUT/md5-nowd-before" ]; then
        if cmp -s "$OUT/md5-nowd-before" "$OUT/md5-nowd-after"; then
            echo "   builds without WET_DRY: identical executables          ok"
        else
            echo "   builds without WET_DRY: executables differ             BAD"; status=1
        fi
    fi
    "$PY" -I "$here/check_runs.py" "$OUT" | tee "$OUT/check.txt" || status=1
fi
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
