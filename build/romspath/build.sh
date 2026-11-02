#!/bin/bash
# Build a ROMSPath image.
#
#   build/romspath/build.sh [--tag TAG] [--source DIR] [--target build] [-- DOCKER_BUILD_ARGS...]
#
#   (default)     the pinned commit of the fork (ROMSPATH_REF in the Dockerfile),
#                 fetched from GitHub; image coawst-romspath:latest
#   --source DIR  build a local checkout of ROMSPath instead (any commit; used by
#                 the tests, and to try changes before they are committed)
#   --target build  stop after the build stage: an image with gfortran and
#                 NetCDF-Fortran in which any ROMSPath commit can be compiled
#   --tag TAG     image tag (default coawst-romspath:latest)
# Anything after -- goes to docker build, e.g. -- --build-arg ROMSPATH_REF=<sha>
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tag=coawst-romspath:latest source="" target=()
while [ $# -gt 0 ]; do
    case "$1" in
        --tag)    tag=$2; shift 2 ;;
        --source) source=$(cd "$2" && pwd); shift 2 ;;
        --target) target=(--target "$2"); shift 2 ;;
        --)       shift; break ;;
        *) echo "build.sh: unknown argument $1" >&2; exit 2 ;;
    esac
done

ctx=$(mktemp -d)
trap 'rm -rf "$ctx"' EXIT
cp "$here/Dockerfile" "$ctx/"
mkdir -p "$ctx/src"
if [ -n "$source" ]; then
    if git -C "$source" rev-parse -q HEAD > /dev/null 2>&1; then
        git -C "$source" archive HEAD | tar -x -C "$ctx/src"
        git -C "$source" rev-parse HEAD > "$ctx/src/SOURCE_COMMIT"
    else
        cp -r "$source"/. "$ctx/src/"
    fi
fi

docker build -q -t "$tag" "${target[@]}" "$@" "$ctx" > /dev/null
echo "built $tag"
