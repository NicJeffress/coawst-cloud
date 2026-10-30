#!/bin/bash
# Do two patch series give the same COAWST source?
#
#   compare_series.sh SOURCE SERIES_A PATCH_DIR_A SERIES_B PATCH_DIR_B
#
# SOURCE is an unpacked COAWST tree or a tarball of one (one top-level folder).
# Each SERIES file lists patches relative to its PATCH_DIR, as
# build/coawst/patches/series does. Both series are applied to fresh copies of
# SOURCE with build/coawst/apply_series.sh, and the two trees are compared file
# by file. Exit 0 and "IDENTICAL" if every file matches, 1 with the list of
# differing files otherwise.
#
# Use it whenever the series is reorganised (reordered, split, regenerated):
# the reorganised series must give exactly the source of the old one, or the
# difference must be the intended change.
set -euo pipefail
[ $# -eq 5 ] || { sed -n '2,15p' "$0"; exit 2; }
src=$1 sa=$2 pa=$3 sb=$4 pb=$5
apply=$(cd "$(dirname "$0")/../../build/coawst" && pwd)/apply_series.sh
work=$(mktemp -d "${TMPDIR:-/tmp}/compare_series.XXXXXX")
trap 'rm -rf "$work"' EXIT

mkdir "$work/base"
if [ -d "$src" ]; then
    cp -a "$src/." "$work/base/"
else
    tar -xzf "$src" -C "$work/base" --strip-components=1
fi
for side in a b; do
    cp -a "$work/base" "$work/$side"
done
rm -rf "$work/base"

echo "== series A: $sa"
sh "$apply" "$sa" "$pa" "$work/a" | sed 's/^/   /'
echo "== series B: $sb"
sh "$apply" "$sb" "$pb" "$work/b" | sed 's/^/   /'

# PATCHES_APPLIED names the patches, which may differ; everything else must match.
if diff -rq -x PATCHES_APPLIED "$work/a" "$work/b" > "$work/diff.txt"; then
    n=$(find "$work/a" -type f | wc -l)
    echo "IDENTICAL: $n files"
else
    echo "DIFFERENT: $(wc -l < "$work/diff.txt") entries"
    sed "s|$work/||g" "$work/diff.txt"
    exit 1
fi
