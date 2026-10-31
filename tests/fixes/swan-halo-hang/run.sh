#!/bin/bash
# Test of 1-fixes/swan-halo-hang.patch: SWAN's halo exchange deadlocked once a
# halo row was longer than MPI's eager limit (item 20).
#
#   tests/fixes/swan-halo-hang/run.sh OUTDIR [TIMEOUT_S]
#
# Standalone SWAN (tests/cases/Swan_Periodic_Test build), a periodic channel
# 1100 x 31 points (make_inputs.py): with REPEATING SWAN cuts it into
# y-strips, so 2 processes exchange 1100-point rows (4.4 kB > 4 kB eager limit
# of OpenMPI's shared-memory transport). 10 simulated minutes, before and
# after the patch:
#   before: 2 processes hang (stopped after TIMEOUT_S, default 600 s); a
#           650-point channel (2.6 kB rows) runs, as the control
#   after:  2 processes finish, and give the same Hs as 1 process
# About 15 min (most of it the timeout).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
OUT=$(realpath -m "$1") TMO=${2:-600}
PY=${PYTHON:-python3}
mkdir -p "$OUT"
"$tools/build_pair.sh" 1-fixes/swan-halo-hang.patch coawst-test:halo \
    --case "$here/../../cases/Swan_Periodic_Test" --app SWAN_PERIODIC_TEST
run() { # side name mxc np
    local d=$OUT/$2
    rm -rf "$d"
    "$PY" -I "$here/make_inputs.py" "$d" "$3" > /dev/null
    local t0=$(date +%s) rc=0
    timeout "$TMO" docker run --rm --name "halo-$2" --user "$(id -u):$(id -g)" -v "$d:/run" -w /run \
        coawst-test:halo-$1 mpirun --use-hwthread-cpus --bind-to none -np "$4" coawstM swan.in \
        > "$d/log.txt" 2>&1 || rc=$?
    [ $rc = 124 ] && docker kill "halo-$2" > /dev/null 2>&1 || true
    echo "$rc $(( $(date +%s) - t0 ))" > "$d/result.txt"
    printf '   %-18s %4s points, np %s: %s after %s s\n' "$2" "$3" "$4" \
        "$([ $rc = 0 ] && echo finished || { [ $rc = 124 ] && echo HUNG || echo "failed ($rc)"; })" \
        "$(( $(date +%s) - t0 ))"
}
run before before-1100-np2 1100 2
run before before-650-np2 650 2
run after after-1100-np2 1100 2
run after after-1100-np1 1100 1
status=0
r() { cut -d' ' -f1 "$OUT/$1/result.txt"; }
[ "$(r before-1100-np2)" = 124 ] || { echo "FAIL: stock did not hang with 1100-point rows"; status=1; }
[ "$(r before-650-np2)" = 0 ] || { echo "FAIL: stock control (650 points) did not finish"; status=1; }
[ "$(r after-1100-np2)" = 0 ] && [ "$(r after-1100-np1)" = 0 ] || { echo "FAIL: patched runs did not finish"; status=1; }
if [ $status = 0 ]; then
    "$PY" -I "$tools/compare_nc.py" "$OUT/after-1100-np1/output/hsign.nc" \
        "$OUT/after-1100-np2/output/hsign.nc" | tail -3 | sed 's/^/   np1 vs np2: /' \
        | tee "$OUT/compare.txt"
    grep -q "ALL BIT-IDENTICAL" "$OUT/compare.txt" || status=1
fi
[ $status = 0 ] && echo "PASS" || echo "FAIL"
exit $status
