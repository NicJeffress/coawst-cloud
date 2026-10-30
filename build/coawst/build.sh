#!/bin/bash
# Build a COAWST image.
#
#   build/coawst/build.sh [--case DIR --app NAME] [--tag TAG] [-- DOCKER_BUILD_ARGS...]
#
#   (no --case)   stock Inlet_test, Projects/Inlet_test/Coupled
#   --case DIR    a case folder anywhere on disk: its header (lower-case NAME.h),
#                 analytical files and .in files; copied to Projects/<folder name>
#   --app NAME    the case's cpp application flag, e.g. REEF_IDEAL_A15
#   --tag TAG     image tag (default coawst:<app in lower case>)
# Anything after -- goes to docker build, e.g. -- --build-arg SERIES=none
#
# The build context is put together in a temporary folder (Dockerfile,
# apply_series.sh, patches/, vendor/ and the case), so cases never have to
# live in this repository.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
case_dir="" app="" tag=""
while [ $# -gt 0 ]; do
    case "$1" in
        --case) case_dir=$2; shift 2 ;;
        --app)  app=$2; shift 2 ;;
        --tag)  tag=$2; shift 2 ;;
        --)     shift; break ;;
        *) echo "build.sh: unknown argument $1" >&2; exit 2 ;;
    esac
done
if [ -n "$case_dir" ] && [ -z "$app" ]; then
    echo "build.sh: --case needs --app" >&2; exit 2
fi

ctx=$(mktemp -d)
trap 'rm -rf "$ctx"' EXIT
cp "$here/Dockerfile" "$here/apply_series.sh" "$ctx/"
cp -r "$here/patches" "$ctx/patches"
mkdir -p "$ctx/vendor" "$ctx/cases"
cp "$here"/vendor/*.tar.gz "$ctx/vendor/" 2>/dev/null || true

args=()
if [ -n "$case_dir" ]; then
    name=$(basename "$(cd "$case_dir" && pwd)")
    cp -r "$case_dir" "$ctx/cases/$name"
    args+=(--build-arg COAWST_APPLICATION="$app" --build-arg CASE_DIR="Projects/$name")
else
    app=INLET_TEST
fi
tag=${tag:-coawst:$(echo "$app" | tr A-Z a-z)}

docker build -t "$tag" "${args[@]}" "$@" "$ctx"
echo "built $tag"
