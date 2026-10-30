#!/bin/bash
# Build a COAWST image.
#
#   build/coawst/build.sh [--case DIR --app NAME] [--tag TAG] [-- DOCKER_BUILD_ARGS...]
#
#   (no --case)   stock Inlet_test, Projects/Inlet_test/Coupled
#   --case DIR    a case folder anywhere on disk: its header (lower-case NAME.h),
#                 analytical files and .in files; copied to Projects/<folder name>
#   --project P   a project that ships with COAWST instead, e.g. Projects/Veg_test
#   --app NAME    the case's cpp application flag, e.g. REEF_IDEAL_A15 or VEG_TEST
#   --tag TAG     image tag (default coawst:<app in lower case>)
#   --series FILE apply this series file instead of patches/series (paths in it
#                 relative to patches/, e.g. 1-fixes/x.patch); for tests that
#                 build with part of the series. "none": stock COAWST.
# Anything after -- goes to docker build, e.g. -- --build-arg CPP_OPTIONS="+X"
#
# The build context is put together in a temporary folder (Dockerfile,
# apply_series.sh, patches/, vendor/ and the case), so cases never have to
# live in this repository.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
case_dir="" project="" app="" tag="" series=""
while [ $# -gt 0 ]; do
    case "$1" in
        --case)   case_dir=$2; shift 2 ;;
        --project) project=$2; shift 2 ;;
        --app)    app=$2; shift 2 ;;
        --tag)    tag=$2; shift 2 ;;
        --series) series=$2; shift 2 ;;
        --)     shift; break ;;
        *) echo "build.sh: unknown argument $1" >&2; exit 2 ;;
    esac
done
if { [ -n "$case_dir" ] || [ -n "$project" ]; } && [ -z "$app" ]; then
    echo "build.sh: --case and --project need --app" >&2; exit 2
fi

ctx=$(mktemp -d)
trap 'rm -rf "$ctx"' EXIT
cp "$here/Dockerfile" "$here/apply_series.sh" "$ctx/"
cp -r "$here/patches" "$ctx/patches"
mkdir -p "$ctx/vendor" "$ctx/cases"
cp "$here"/vendor/*.tar.gz "$ctx/vendor/" 2>/dev/null || true

args=()
if [ "$series" = none ]; then
    args+=(--build-arg SERIES=none)
elif [ -n "$series" ]; then
    cp "$series" "$ctx/patches/series.custom"
    args+=(--build-arg SERIES=series.custom)
fi
if [ -n "$case_dir" ]; then
    name=$(basename "$(cd "$case_dir" && pwd)")
    cp -r "$case_dir" "$ctx/cases/$name"
    args+=(--build-arg COAWST_APPLICATION="$app" --build-arg CASE_DIR="Projects/$name")
elif [ -n "$project" ]; then
    args+=(--build-arg COAWST_APPLICATION="$app" --build-arg CASE_DIR="$project")
else
    app=INLET_TEST
fi
tag=${tag:-coawst:$(echo "$app" | tr A-Z a-z)}

docker build -t "$tag" "${args[@]}" "$@" "$ctx"
echo "built $tag"
