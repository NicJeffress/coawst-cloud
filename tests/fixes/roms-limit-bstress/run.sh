#!/bin/bash
# Test of 1-fixes/roms-limit-bstress.patch: the bottom-stress limiter follows
# LIMIT_BSTRESS instead of WET_DRY. A compile-time test: no model run needed.
#
#   tests/fixes/roms-limit-bstress/run.sh OUTDIR
#
# Builds COAWST's Veg_test (SSW_BBL bottom boundary layer, WET_DRY on) up to the
# build stage, before and after the patch, in two configurations:
#   shipped   the case as it is (WET_DRY, which also defines LIMIT_BSTRESS)
#   nowetdry  CPP_OPTIONS="-WET_DRY +LIMIT_BSTRESS" (limiter wanted, no wet/dry)
# and compares the preprocessed Fortran ROMS compiles (Build_roms/*.f90):
#   1. patched source: the 13 limiter blocks test LIMIT_BSTRESS, none WET_DRY
#   2. shipped:  before and after identical (builds with WET_DRY unchanged)
#   3. nowetdry: the limiter is absent before the patch, present after it
# About 15 min on 4 vCPUs.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
OUT=$(realpath -m "$1")
P=1-fixes/roms-limit-bstress.patch
mkdir -p "$OUT"
proj=(--project Projects/Veg_test --app VEG_TEST)
"$tools/build_pair.sh" $P coawst-test:lbs-shipped "${proj[@]}" -- --target build
"$tools/build_pair.sh" $P coawst-test:lbs-nowetdry "${proj[@]}" -- --target build \
    --build-arg CPP_OPTIONS="-WET_DRY +LIMIT_BSTRESS"
for cfg in shipped nowetdry; do
    for side in before after; do
        d=$OUT/$cfg-$side
        rm -rf "$d" && mkdir -p "$d"
        docker run --rm coawst-test:lbs-$cfg-$side \
            bash -c 'cd /opt/COAWST/Build_roms && tar -cf - *.f90' | tar -xf - -C "$d"
    done
done
status=0
files="ROMS/Nonlinear/BBL/ssw_bbl.h ROMS/Nonlinear/BBL/sg_bbl.h ROMS/Nonlinear/BBL/mb_bbl.h ROMS/Nonlinear/set_vbc.F"
echo "== 1. limiter blocks in the patched source"
n=$(docker run --rm coawst-test:lbs-shipped-after bash -c "cd /opt/COAWST && cat $files" \
    | grep -cE '^# *(ifdef|if defined) *LIMIT_BSTRESS' || true)
w=$(docker run --rm coawst-test:lbs-shipped-after bash -c "cd /opt/COAWST && grep -n 'WET_DRY in place of' $files" || true)
echo "   blocks testing LIMIT_BSTRESS: $n (expected 13)"
[ "$n" = 13 ] || status=1
echo "== 2. shipped (WET_DRY): preprocessed Fortran before vs after"
if diff -rq "$OUT/shipped-before" "$OUT/shipped-after"; then
    echo "   identical ($(ls "$OUT/shipped-after" | wc -l) files)"
else
    echo "   DIFFERENT"; status=1
fi
echo "== 3. -WET_DRY +LIMIT_BSTRESS: limiter (MIN(ABS(bustr...))) in the compiled code"
for side in before after; do
    c=$(cat "$OUT"/nowetdry-$side/*.f90 | grep -ciE 'min *\( *abs *\( *b[uv]str' || true)
    echo "   $side: $c limiter lines"
    eval "c_$side=$c"
done
[ "$c_before" = 0 ] && [ "$c_after" -gt 0 ] || status=1
echo "   files that differ:"; diff -rq "$OUT/nowetdry-before" "$OUT/nowetdry-after" | sed 's/^/   /' || true
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
