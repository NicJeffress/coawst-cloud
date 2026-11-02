#!/bin/bash
# Does the patch series apply to COAWST, and is it complete?
#
#   tests/ci/series_check.sh [REF]
#
# REF: a COAWST commit or branch (default: COAWST_REF of build/coawst/Dockerfile;
# "main" tries the series on upstream's latest code). Fetches that one commit
# from GitHub, or uses COAWST_TARBALL (a tarball of it) if set. Checks:
#   - every patch named in patches/series exists and has its .md document;
#   - every .patch file in the tier folders is named in patches/series;
#   - the series applies in order with no rejects (the first patch that does
#     not apply is named).
# Exit 0 if all pass. Needs git and patch. About a minute plus the download.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
p=$root/build/coawst/patches
REF=${1:-$(sed -n 's/^ARG COAWST_REF=//p' "$root/build/coawst/Dockerfile")}
fail=0

# 1. series file against the tier folders
listed=$(grep -vE '^[[:space:]]*(#|$)' "$p/series")
for f in $listed; do
    [ -f "$p/$f" ] || { echo "FAIL  series names $f, which does not exist"; fail=1; }
    [ -f "$p/${f%.patch}.md" ] || { echo "FAIL  $f has no document ${f%.patch}.md"; fail=1; }
done
for f in $(cd "$p" && ls [0-9]-*/*.patch); do
    echo "$listed" | grep -qx "$f" || { echo "FAIL  $f is not in series"; fail=1; }
done
[ $fail = 0 ] && echo "PASS  series: $(echo "$listed" | wc -l) patches, each with its document"

# 2. apply to COAWST at REF
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
if [ -n "${COAWST_TARBALL:-}" ]; then
    tar -xzf "$COAWST_TARBALL" -C "$work" --strip-components=1
    got="tarball $(basename "$COAWST_TARBALL")"
else
    git -C "$work" init -q
    git -C "$work" fetch -q --depth 1 https://github.com/DOI-USGS/COAWST.git "$REF"
    git -C "$work" checkout -q FETCH_HEAD
    got="DOI-USGS/COAWST $REF = $(git -C "$work" rev-parse --short=12 HEAD), $(git -C "$work" log -1 --format=%cs)"
fi
if sh "$root/build/coawst/apply_series.sh" "$p/series" "$p" "$work" > "$work/apply.log" 2>&1; then
    echo "PASS  every patch applies to $got"
else
    echo "FAIL  the series stops on $got:"
    tail -15 "$work/apply.log" | sed 's/^/      /'
    fail=1
fi
[ $fail = 0 ] && echo PASS || echo FAIL
exit $fail
