#!/bin/bash
# Test that the experimental patches change nothing while their cpp options
# are off: every build preprocesses to the same Fortran with and without
# build/coawst/patches/3-experimental/.
#
#   tests/experimental/options-off/run.sh OUTDIR
#
# Builds (build stage only) each configuration twice, with the series without
# the 3-experimental patches and with the whole series, and compares the
# preprocessed ROMS sources (/opt/COAWST/Build_roms/*.f90) file by file:
#   inlet       COAWST's Inlet_test (sediment, morphology, WEC, SWAN)
#   a15veg      Reef_Ideal_A15_veg (vegetation drag and turbulence, WEC_VF,
#               SSW_BBL, GLS, periodic)
#   a15wetdry   Reef_Ideal_A15 with +WET_DRY (wetdry.F)
#   circle      Circle_Island (CURVGRID O-grid, closed SWAN ring)
# compare.py: the files must be the same except for the line numbers ROMS
# passes (__LINE__) to its timers and error messages, which the patches shift,
# and comment lines. PASS if so for all four. About 1 h on 4 vCPUs (eight
# builds).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
root=$here/../../..
build=$root/build/coawst/build.sh
OUT=$(realpath -m "$1")
STAGES=${STAGES:-build check}
has() { [[ " $STAGES " == *" $1 "* ]]; }
mkdir -p "$OUT"
grep -vE '^[[:space:]]*(#|$)' "$root/build/coawst/patches/series" > "$OUT/series-with"
grep -v '^3-experimental/' "$OUT/series-with" > "$OUT/series-without"
cfg() {   # cfg NAME build.sh-args...
    local name=$1; shift
    for side in without with; do
        "$build" --series "$OUT/series-$side" --tag coawst-test:off-$name-$side "$@" -- --target build \
            ${CPP:+--build-arg CPP_OPTIONS="$CPP"} > "$OUT/build-$name-$side.log" 2>&1
        rm -rf "$OUT/$name-$side" && mkdir -p "$OUT/$name-$side"
        docker run --rm coawst-test:off-$name-$side bash -c 'cd /opt/COAWST/Build_roms && tar -cf - *.f90' \
            | tar -xf - -C "$OUT/$name-$side"
    done
}
cases=$root/tests/cases
if has build; then
cfg inlet
cfg a15veg --case "$cases/Reef_Ideal_A15_veg" --app REEF_IDEAL_A15
CPP="+WET_DRY" cfg a15wetdry --case "$cases/Reef_Ideal_A15" --app REEF_IDEAL_A15
cfg circle --case "$cases/Circle_Island" --app CIRCLE_ISLAND
fi
status=0
for name in inlet a15veg a15wetdry circle; do
    echo "$name:"
    "${PYTHON:-python3}" -I "$here/compare.py" "$OUT/$name-without" "$OUT/$name-with" || status=1
done
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
