#!/bin/sh
# Apply a patch series to a COAWST source tree.
#
#   apply_series.sh SERIES_FILE PATCH_DIR [SOURCE_DIR]
#
# SERIES_FILE lists one patch per line, relative to PATCH_DIR, in the order they
# are applied; blank lines and lines starting with # are skipped. SERIES_FILE
# "none" applies nothing (the stock build). SOURCE_DIR defaults to the current
# directory. Each patch must apply completely (no rejects, no reversed hunks).
# The names of the applied patches are appended to SOURCE_DIR/PATCHES_APPLIED.
#
# Used by the Dockerfile and by tests/same_source/compare_series.sh, so a series
# is applied the same way in both.
set -eu
series=$1
pdir=$2
src=${3:-.}
: > "$src/PATCHES_APPLIED"
[ "$series" = none ] && { echo "apply_series: none (stock COAWST)"; exit 0; }
grep -vE '^[[:space:]]*(#|$)' "$series" | while read -r p; do
    echo "apply_series: $p"
    patch -d "$src" -p1 --forward --no-backup-if-mismatch -s < "$pdir/$p"
    echo "$p" >> "$src/PATCHES_APPLIED"
done
