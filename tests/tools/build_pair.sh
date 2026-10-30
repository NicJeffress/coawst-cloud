#!/bin/bash
# Build the "before" and "after" images for one patch of the series.
#
#   tests/tools/build_pair.sh PATCH TAG [build.sh arguments ...]
#
# TAG-before: the series up to, not including, PATCH (the bug is there)
# TAG-after:  the series up to and including PATCH (the fix)
# Further arguments go to build/coawst/build.sh (e.g. --case DIR --app NAME,
# or -- --build-arg CPP_OPTIONS="+X"). Prints the two image names.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
build=$here/../../build/coawst/build.sh
p=$1 tag=$2
shift 2
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
for side in before after; do
    if [ $side = before ]; then
        "$here/series_upto.sh" "$p" --before > "$tmp/series"
    else
        "$here/series_upto.sh" "$p" > "$tmp/series"
    fi
    if [ "$(cat "$tmp/series")" = none ]; then s=none; else s=$tmp/series; fi
    "$build" --series "$s" --tag "$tag-$side" "$@" > "$tmp/build-$side.log" 2>&1 \
        || { tail -40 "$tmp/build-$side.log"; exit 1; }
    echo "$tag-$side"
done
