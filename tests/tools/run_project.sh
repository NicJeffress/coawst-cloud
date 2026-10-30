#!/bin/bash
# Run a COAWST project from an image on this machine (Docker).
#
#   tests/tools/run_project.sh IMAGE OUTDIR NAME PROJECT COUPLING OCEAN SWAN [TI TJ NWAV MINUTES]
#
# e.g. run_project.sh coawst:veg_test out veg Projects/Veg_test \
#        coupling_veg_test.in ocean_veg_test.in swan_veg_test.in 1 1 1 20
# The run goes to OUTDIR/NAME. Arguments after NAME, OCEANSED, SWANSED and
# MPIRUN_ARGS: see project_inside.sh, which does the work inside the
# container. MALLOC_PERTURB_, if set, is passed on.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
[ $# -ge 7 ] || { sed -n '2,10p' "$0"; exit 2; }
IMAGE=$1 OUT=$(realpath -m "$2") NAME=$3
shift 3
run=$OUT/$NAME
mkdir -p "$run"
cp "$here/project_inside.sh" "$run/"
docker run --rm --user "$(id -u):$(id -g)" -v "$run:/work" -w /work \
    -e OCEANSED="${OCEANSED:-}" -e SWANSED="${SWANSED:-}" -e MPIRUN_ARGS="${MPIRUN_ARGS:-}" \
    ${MALLOC_PERTURB_:+-e MALLOC_PERTURB_=$MALLOC_PERTURB_} \
    "$IMAGE" bash /work/project_inside.sh "$@"
echo "$NAME: $(tail -2 "$run/image_info.txt" | paste -sd' ')"
