#!/bin/bash
# Test of 1-fixes/roms-vandera-no-sand.patch: with van der A bedload and no
# sand class, the van der A output fields must not be unset memory.
#
#   tests/fixes/roms-vandera-no-sand/run.sh OUTDIR [MINUTES]
#
# Builds, before and after the patch:
#   Inlet_test DiffGrid (mud only: NCS 1, NNS 0) with ROMS_FFLAGS_EXTRA=
#     -finit-real=snan, so local memory that is never set holds NaN;
#   Inlet_test Coupled (sand), as usual.
# Runs each for MINUTES simulated minutes (default 120): DiffGrid with ROMS 2x2
# + 2 SWAN, Coupled with ROMS 1x2 + 1 SWAN. check.py:
#   DiffGrid before: fd_wbl is NaN (the loop that sets it never ran)
#   DiffGrid after:  fd_wbl (and any other van der A field written) is zero;
#                    every other variable bit-identical to before
#   Coupled: every variable bit-identical before vs after (with sand the
#            loop sets the arrays, so the patch changes nothing)
# STAGES (default "build run check"). Needs Docker and Python with numpy and
# netCDF4 (PYTHON). About 15 min to build, 10 min of runs on 4 vCPUs.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
OUT=$(realpath -m "$1") MINUTES=${2:-120}
PY=${PYTHON:-python3}
STAGES=${STAGES:-build run check}
P=1-fixes/roms-vandera-no-sand.patch
mkdir -p "$OUT"
has() { [[ " $STAGES " == *" $1 "* ]]; }
if has build; then
    "$tools/build_pair.sh" $P coawst-test:vns-diffgrid \
        --project Projects/Inlet_test/DiffGrid --app INLET_TEST \
        -- --build-arg ROMS_FFLAGS_EXTRA="-finit-real=snan"
    "$tools/build_pair.sh" $P coawst-test:vns-inlet
fi
if has run; then
    export MPIRUN_ARGS=--oversubscribe
    for side in before after; do
        "$tools/run_project.sh" coawst-test:vns-diffgrid-$side "$OUT" diffgrid_$side \
            Projects/Inlet_test/DiffGrid coupling_inlet_test_diffgrid.in ocean_inlet_test.in \
            swan_inlet_test_diff.in 2 2 2 "$MINUTES"
        "$tools/run_inlet.sh" coawst-test:vns-inlet-$side "$OUT" inlet_$side 1 2 1 \
            "$(awk -v m="$MINUTES" 'BEGIN { print m / 60 }')"
    done
fi
status=0
if has check; then
    "$PY" -I "$here/check.py" "$OUT" | tee "$OUT/check.txt" || status=1
fi
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
