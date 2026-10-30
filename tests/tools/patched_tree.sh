#!/bin/bash
# Make a COAWST source tree with a patch series applied (no build).
#
#   tests/tools/patched_tree.sh SOURCE SERIES OUTDIR
#
# SOURCE  an unpacked COAWST tree or a tarball of one (one top-level folder)
# SERIES  a series file (paths relative to build/coawst/patches/) or "none"
# OUTDIR  created; receives the patched tree
# For tests that check the source itself rather than a model run.
set -euo pipefail
src=$1 series=$2 out=$3
pdir=$(cd "$(dirname "$0")/../../build/coawst/patches" && pwd)
mkdir -p "$out"
if [ -d "$src" ]; then
    cp -a "$src/." "$out/"
else
    tar -xzf "$src" -C "$out" --strip-components=1
fi
sh "$pdir/../apply_series.sh" "$series" "$pdir" "$out" > /dev/null
