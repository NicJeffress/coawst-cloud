#!/bin/bash
# Has upstream ROMSPath moved on, and do the fork's commits still apply to it?
#
#   tests/ci/romspath_upstream.sh
#
# Clones the fork (ROMSPATH_REPO) and upstream imcslatte/ROMSPath, lists the
# upstream commits the fork does not have yet, and replays the fork's own
# commits onto upstream's latest master (in a scratch clone, nothing is
# pushed). PASS if upstream has nothing new, or if every fork commit still
# applies; FAIL names the first commit that conflicts. Needs git.
set -euo pipefail
FORK=${ROMSPATH_REPO:-https://github.com/NicJeffress/ROMSPath.git}
UP=https://github.com/imcslatte/ROMSPath.git
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
git clone -q "$FORK" "$work/r"
cd "$work/r"
git -c user.name=ci -c user.email=ci@localhost remote add upstream "$UP"
git fetch -q upstream master
base=$(git merge-base HEAD upstream/master)
new=$(git rev-list --count "$base..upstream/master")
ours=$(git rev-list --count "upstream/master..HEAD")
echo "fork: $ours commits on top of upstream $(git rev-parse --short=7 "$base")"
if [ "$new" = 0 ]; then
    echo "PASS  upstream master has no commits the fork lacks"
    exit 0
fi
echo "upstream master has $new new commits:"
git log --format='      %h %cs %s' "$base..upstream/master"
if git -c user.name=ci -c user.email=ci@localhost rebase -q upstream/master > rebase.log 2>&1; then
    echo "PASS  all $ours fork commits replay cleanly on upstream master (rebase the fork)"
else
    stop=$(git rev-parse --short=7 REBASE_HEAD 2>/dev/null || echo "?")
    echo "FAIL  fork commit $stop ($(git log -1 --format=%s "$stop" 2>/dev/null)) conflicts with upstream"
    git -c core.pager=cat diff --name-only --diff-filter=U | sed 's/^/      conflict: /'
    exit 1
fi
