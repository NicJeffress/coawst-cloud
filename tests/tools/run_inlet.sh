#!/bin/bash
# Run COAWST's Inlet_test (Coupled) from an image on this machine (Docker).
#
#   tests/tools/run_inlet.sh IMAGE OUTDIR NAME [TI TJ NWAV HOURS]
#
# IMAGE   a coawst image of Inlet_test (build/coawst/build.sh, no --case)
# OUTDIR  host folder; the run goes to OUTDIR/NAME (inputs, log, output)
# TI TJ NWAV HOURS, OCEANSED, SWANSED, MPIRUN_ARGS: see inlet_inside.sh, which
# does the work inside the container. MALLOC_PERTURB_, if set, is passed on
# (glibc fills new memory with a pattern: shows reads of uninitialised memory).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
[ $# -ge 3 ] || { sed -n '2,9p' "$0"; exit 2; }
IMAGE=$1 OUT=$(realpath -m "$2") NAME=$3
shift 3
run=$OUT/$NAME
mkdir -p "$run"
cp "$here/inlet_inside.sh" "$run/"
docker run --rm --user "$(id -u):$(id -g)" -v "$run:/work" -w /work \
    -e OCEANSED="${OCEANSED:-}" -e SWANSED="${SWANSED:-}" -e MPIRUN_ARGS="${MPIRUN_ARGS:-}" \
    ${MALLOC_PERTURB_:+-e MALLOC_PERTURB_=$MALLOC_PERTURB_} \
    "$IMAGE" bash /work/inlet_inside.sh "$@"
echo "$NAME: $(tail -2 "$run/image_info.txt" | paste -sd' ')"
