#!/bin/bash
# Run a tests/cases case (e.g. Reef_Ideal_A15) from an image on this machine.
#
#   tests/tools/run_case.sh IMAGE OUTDIR NAME CASE [TI TJ NWAV MINUTES]
#
# The image must contain the case (build/coawst/build.sh --case tests/cases/CASE).
# The run goes to OUTDIR/NAME. Arguments after NAME and the environment (DT,
# OUTDT, NHISSTEP, OCEANSED, SWANSED, MPIRUN_ARGS): see case_inside.sh, which
# does the work inside the container. MALLOC_PERTURB_, if set, is passed on.
# Exit status: the model's.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
[ $# -ge 4 ] || { sed -n '2,10p' "$0"; exit 2; }
IMAGE=$1 OUT=$(realpath -m "$2") NAME=$3
shift 3
run=$OUT/$NAME
mkdir -p "$run"
cp "$here/case_inside.sh" "$run/"
rc=0
docker run --rm --user "$(id -u):$(id -g)" -v "$run:/work" -w /work \
    -e DT="${DT:-}" -e OUTDT="${OUTDT:-}" -e NHISSTEP="${NHISSTEP:-}" \
    -e OCEANSED="${OCEANSED:-}" -e SWANSED="${SWANSED:-}" -e MPIRUN_ARGS="${MPIRUN_ARGS:-}" \
    ${MALLOC_PERTURB_:+-e MALLOC_PERTURB_=$MALLOC_PERTURB_} \
    "$IMAGE" bash /work/case_inside.sh "$@" || rc=$?
echo "$NAME: $(tail -2 "$run/image_info.txt" | paste -sd' ')"
exit $rc
