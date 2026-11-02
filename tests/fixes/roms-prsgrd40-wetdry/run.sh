#!/bin/bash
# Test of 1-fixes/roms-prsgrd40-wetdry.patch on tests/cases/Reef_Ideal_A15.
#
#   tests/fixes/roms-prsgrd40-wetdry/run.sh OUTDIR [MINUTES]
#
# Idea: the pressure-gradient scheme PJ_GRADP (prsgrd40.h) does not compile
# together with WET_DRY in COAWST v3.9; with the patch it does, and nothing
# else changes. Builds of A15 (fixes + the borrowed swan-netcdf-output and
# swan-periodic-curvilinear that A15's SWAN setup needs), with
# CPP_OPTIONS "-DJ_GRADPS +PJ_GRADP" and:
#   pgwd-before  +WET_DRY, the series without this patch: must fail to compile
#                on the undeclared wet/dry masks
#   pgwd-after   +WET_DRY, with the patch: must compile, and run MINUTES
#                (default 30) to the end with finite fields (history every
#                10 min)
#   pg-before, pg-after   without WET_DRY: identical executables (the patch
#                touches only WET_DRY code)
# Runs: ROMS 1x2 + 2 SWAN (TI, TJ, NWAV). Prints PASS or FAIL.
# Needs Docker and Python with numpy and netCDF4 (PYTHON). About 20 min.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
root=$here/../../..
OUT=$(realpath -m "$1") MIN=${2:-30}
PY=${PYTHON:-python3}
TI=${TI:-1} TJ=${TJ:-2} NWAV=${NWAV:-2}
P=1-fixes/roms-prsgrd40-wetdry.patch
case=$root/tests/cases/Reef_Ideal_A15
mkdir -p "$OUT"
ok=1
report() { echo "$1  $2"; [ "$1" = PASS ] || ok=0; }

{ grep -vE '^[[:space:]]*(#|$)' "$root/build/coawst/patches/series" | grep '^1-fixes/'
  echo 2-improvements/swan-netcdf-output.patch
  echo 2-improvements/swan-periodic-curvilinear.patch; } > "$OUT/series-after"
grep -vxF "$P" "$OUT/series-after" > "$OUT/series-before"
build() {   # build NAME SIDE OPTIONS
    "$root/build/coawst/build.sh" --case "$case" --app REEF_IDEAL_A15 --series "$OUT/series-$2" \
        --tag "coawst-test:prsgrd40-$1-$2" -- --build-arg CPP_OPTIONS="-DJ_GRADPS +PJ_GRADP $3" \
        > "$OUT/build-$1-$2.log" 2>&1
}

echo "== builds"
if build pgwd before "+WET_DRY"; then
    report FAIL "PJ_GRADP + WET_DRY before the patch: compiled (expected the undeclared-mask error)"
elif grep -qE "Symbol '(u|v)mask_wet' .*has no IMPLICIT type" "$OUT/build-pgwd-before.log"; then
    report PASS "PJ_GRADP + WET_DRY before the patch: does not compile ($(grep -oE "Symbol '(u|v)mask_wet'" "$OUT/build-pgwd-before.log" | sort -u | sed -E "s/Symbol //" | paste -sd' ') have no IMPLICIT type)"
else
    report FAIL "PJ_GRADP + WET_DRY before the patch: failed for another reason (see build-pgwd-before.log)"
fi
if build pgwd after "+WET_DRY"; then
    report PASS "PJ_GRADP + WET_DRY with the patch: compiles"
else
    report FAIL "PJ_GRADP + WET_DRY with the patch: does not compile (see build-pgwd-after.log)"
fi
build pg before "" && build pg after ""
m1=$(docker run --rm coawst-test:prsgrd40-pg-before md5sum /opt/coawst/coawstM | cut -d' ' -f1)
m2=$(docker run --rm coawst-test:prsgrd40-pg-after md5sum /opt/coawst/coawstM | cut -d' ' -f1)
[ "$m1" = "$m2" ] && report PASS "PJ_GRADP without WET_DRY: identical executables before and after ($m1)" \
                  || report FAIL "PJ_GRADP without WET_DRY: executables differ ($m1, $m2)"

echo "== run: PJ_GRADP + WET_DRY with the patch, $MIN min, ROMS ${TI}x${TJ} + $NWAV SWAN"
if docker image inspect coawst-test:prsgrd40-pgwd-after > /dev/null 2>&1 \
   && OUTDT=10 "$tools/run_case.sh" coawst-test:prsgrd40-pgwd-after "$OUT" pgwd-after Reef_Ideal_A15 $TI $TJ $NWAV "$MIN" \
      > "$OUT/run.log" 2>&1; then
    if line=$("$PY" -I - "$OUT/pgwd-after" <<'PYEOF'
import glob, sys
import numpy as np
from netCDF4 import Dataset
f = sorted(glob.glob(sys.argv[1] + "/output/*his*.nc"))[0]
with Dataset(f) as d:
    t = d["ocean_time"][:]
    bad = [v for v in ("zeta", "ubar", "vbar", "u", "v") if not np.isfinite(np.ma.filled(d[v][:], 0.0)).all()]
    umax = float(np.abs(d["u"][-1]).max())
print(f"{len(t)} records to {(t[-1] - t[0]) / 60:.0f} min, largest |u| at the end {umax:.3f} m/s"
      + (f", NaN in {', '.join(bad)}" if bad else ", all finite"))
sys.exit(1 if bad else 0)
PYEOF
    ); then report PASS "run with the patch: $line"; else report FAIL "run with the patch: $line"; fi
else
    report FAIL "run with the patch: did not finish (see run.log and pgwd-after/log.txt)"
fi
[ $ok = 1 ] && echo PASS || echo FAIL
[ $ok = 1 ]
