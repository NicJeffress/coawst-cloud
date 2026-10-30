#!/bin/sh
# Print the part of build/coawst/patches/series up to one patch.
#
#   tests/tools/series_upto.sh PATCH            the series up to and including PATCH
#   tests/tools/series_upto.sh PATCH --before   the series before PATCH ("none" if empty)
#
# PATCH as written in the series (e.g. 1-fixes/roms-sed-morph-tiling.patch).
# A fix's test builds both: "--before" (the bug) and up to PATCH (the fix), and
# passes the file to build/coawst/build.sh --series.
set -eu
series=$(cd "$(dirname "$0")/../../build/coawst/patches" && pwd)/series
p=$1
list=$(grep -vE '^[[:space:]]*(#|$)' "$series" || true)
echo "$list" | grep -qxF "$p" || { echo "series_upto: $p is not in $series" >&2; exit 1; }
if [ "${2:-}" = --before ]; then
    out=$(echo "$list" | sed "\#^$p\$#,\$d")
else
    out=$(echo "$list" | sed "\#^$p\$#q")
fi
[ -n "$out" ] && echo "$out" || echo none
