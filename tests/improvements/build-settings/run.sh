#!/bin/bash
# Test of the build settings (2-improvements/build-settings.md): ROMS without
# -ffast-math, SWAN at -O3, both -march=x86-64-v3 -g; SWAN_SINGLESPEC off.
#
#   tests/improvements/build-settings/run.sh OUTDIR
#
# Builds, all with the series up to roms-wec-stokes-fast, with
# BUILD_SETTINGS=stock (COAWST's flags and SWAN_SINGLESPEC) and =engine:
#   Inlet_test     2 h with SPECOUT (text and NetCDF) at 9 points across the
#                  domain, on 1 and on 2 SWAN processes
#   Reef_Ideal_A15 1 h, ROMS 1x2 + 2 SWAN here (TI, TJ, NWAV); its runs
#                  are named a15-<settings>-<machine>-<k>
# check.py: SPECOUT on 2 processes = 1 with the engine settings (broken with
# stock); engine vs stock A15 after 1 h; repeats identical; wall times.
# The comparison across machine types (AMD vs Intel) needs runs made
# elsewhere (e.g. Cloud Batch) into OUTDIR/a15-<settings>-<machine>-<k>/.
# STAGES (default "build run check"). Needs Docker and Python with numpy and
# netCDF4 (PYTHON). About 40 min to build, 10 min for Inlet, 30 min for A15.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
build=$here/../../../build/coawst/build.sh
OUT=$(realpath -m "$1")
PY=${PYTHON:-python3}
STAGES=${STAGES:-build run check}
TI=${TI:-1} TJ=${TJ:-2} NWAV=${NWAV:-2} MACHINE=${MACHINE:-local}
mkdir -p "$OUT"
has() { [[ " $STAGES " == *" $1 "* ]]; }
if has build; then
    "$tools/series_upto.sh" 2-improvements/roms-wec-stokes-fast.patch > "$OUT/series"
    for s in stock engine; do
        "$build" --series "$OUT/series" --tag coawst-test:bs-inlet-$s -- --build-arg BUILD_SETTINGS=$s \
            > "$OUT/build-inlet-$s.log" 2>&1
        "$build" --series "$OUT/series" --case "$here/../../cases/Reef_Ideal_A15" --app REEF_IDEAL_A15 \
            --tag coawst-test:bs-a15-$s -- --build-arg BUILD_SETTINGS=$s > "$OUT/build-a15-$s.log" 2>&1
        echo "built coawst-test:bs-inlet-$s coawst-test:bs-a15-$s"
    done
fi
if has run; then
    T="OUTPUT 20000101.000000 30 MIN"
    req="POINTS 'pspread' 2000. 8000. 7500. 9000. 13000. 8000. 2000. 11000. 7500. 11000. 13000. 11000. 2000. 13500. 7500. 13500. 13000. 13500."
    req="$req\nSPECOUT 'pspread' SPEC2D ABS 'spread.spc2d' $T\nSPECOUT 'pspread' SPEC2D ABS 'spread.nc' $T"
    for s in stock engine; do
        for nw in 1 2; do
            rm -rf "$OUT/inlet-$s-${nw}swan"
            SWANSED="s#^(COMPUTE NONSTATIONARY)#${req}\n\1#" \
                "$tools/run_inlet.sh" coawst-test:bs-inlet-$s "$OUT" inlet-$s-${nw}swan 1 1 $nw 2 || true
        done
        for k in 1 2; do
            rm -rf "$OUT/a15-$s-$MACHINE-$k"
            "$tools/run_case.sh" coawst-test:bs-a15-$s "$OUT" a15-$s-$MACHINE-$k Reef_Ideal_A15 $TI $TJ $NWAV 60 || true
        done
    done
fi
status=0
if has check; then
    "$PY" -I "$here/check.py" "$OUT" | tee "$OUT/check.txt" || status=1
fi
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
