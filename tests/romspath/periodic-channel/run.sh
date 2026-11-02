#!/bin/bash
# ROMSPath on a periodic channel with an exact answer, commit by commit.
#
#   tests/romspath/periodic-channel/run.sh OUTDIR
#
# Builds the ROMSPath image (build/romspath), then compiles every commit of the
# fork after upstream (UPSTREAM..REF) with that commit's own makefile, and runs
# each, and the image, on two channels: grid lines along x, and the same grid
# rotated by 30 degrees. check.py compares the particles with the exact answer.
#
#   PASS if: the image and the last commit are exact (largest error below 1 mm,
#   on both grids); the first commit (periodic switches only) is off by more
#   than 1 m (the test can see the bugs).
#
# Environment:
#   ROMSPATH_SOURCE  a local checkout of the fork (default: clone ROMSPATH_REPO)
#   ROMSPATH_REPO    default https://github.com/NicJeffress/ROMSPath.git
#   REF              last commit to test (default: ROMSPATH_REF of the Dockerfile)
#   UPSTREAM         upstream commit the fork starts from (default 6072ee9)
#   PYTHON           Python with numpy and netCDF4 (default python3)
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../.." && pwd)
out=$(realpath -m "${1:?usage: run.sh OUTDIR}")
PY=${PYTHON:-python3}
REPO=${ROMSPATH_REPO:-https://github.com/NicJeffress/ROMSPath.git}
UPSTREAM=${UPSTREAM:-6072ee9}
REF=${REF:-$(sed -n 's/^ARG ROMSPATH_REF=//p' "$root/build/romspath/Dockerfile")}
mkdir -p "$out"

# 1. source, image, build-stage image
if [ ! -d "$out/src/.git" ]; then
    if [ -n "${ROMSPATH_SOURCE:-}" ]; then git clone -q "$ROMSPATH_SOURCE" "$out/src"
    else git clone -q "$REPO" "$out/src"; fi
fi
git -C "$out/src" checkout -q "$REF"
"$root/build/romspath/build.sh" --source "$out/src" --tag coawst-romspath:test-channel
"$root/build/romspath/build.sh" --source "$out/src" --tag coawst-romspath:test-channel-build --target build

# 2. the two channels
for g in straight rotated; do
    mkdir -p "$out/$g"
    angle=0; [ $g = rotated ] && angle=30
    (cd "$out/$g" && "$PY" -I "$here/make_hydro.py" hydro_00001.nc --angle $angle > /dev/null \
        && "$PY" -I "$here/make_input.py" "$out/src/ROMSPath.data" hydro_00001.nc .)
done

run() {   # run EXE_DIR NAME: ROMSPath.exe from EXE_DIR (in the build image) on both channels
    for g in straight rotated; do
        rm -f "$out/$g/out/channel.nc"
        docker run --rm -u "$(id -u):$(id -g)" -v "$out:$out" -w "$out/$g" coawst-romspath:test-channel-build \
            "$1/ROMSPath.exe" ROMSPath.data > "$out/$g/log_$2.txt" 2>&1 || true
        if [ -f "$out/$g/out/channel.nc" ]; then
            mv "$out/$g/out/channel.nc" "$out/$g/out/$2.nc"
            echo "$2 $g $("$PY" -I "$here/check.py" --summary "$out/$g/hydro_00001.nc" "$out/$g/out/$2.nc")"
        else
            echo "$2 $g no-output"
        fi
    done
}

# 3. every commit after upstream, compiled with its own makefile
: > "$out/results.txt"
for c in $(git -C "$out/src" rev-list --reverse "$UPSTREAM..$REF"); do
    h=$(git -C "$out/src" rev-parse --short=7 "$c")
    rm -rf "$out/build/$h"; mkdir -p "$out/build/$h"
    git -C "$out/src" archive "$c" | tar -x -C "$out/build/$h"
    docker run --rm -u "$(id -u):$(id -g)" -v "$out:$out" -w "$out/build/$h" coawst-romspath:test-channel-build \
        make > "$out/build/$h.log" 2>&1 || { echo "build of $h failed, see $out/build/$h.log"; exit 1; }
    run "$out/build/$h" "$h" >> "$out/results.txt"
done

# 4. the image (optimised build of REF)
mkdir -p "$out/build/image"
docker run --rm -u "$(id -u):$(id -g)" -v "$out:$out" coawst-romspath:test-channel \
    cp /opt/romspath/ROMSPath.exe "$out/build/image/"
run "$out/build/image" image >> "$out/results.txt"

# 5. report
"$PY" -I - "$out/results.txt" "$out/src" <<'EOF'
import subprocess, sys
rows = [l.split() for l in open(sys.argv[1])]
subj = lambda h: h if h == "image" else subprocess.run(
    ["git", "-C", sys.argv[2], "log", "-1", "--format=%s", h], capture_output=True, text=True).stdout.strip()
res = {}
for r in rows:
    res.setdefault(r[0], {})[r[1]] = None if r[2] == "no-output" else [float(x) for x in r[2:]]
order = list(res)
print(f"{'build':8} {'straight 1 h':>12} {'2 h':>9} {'rotated 1 h':>12} {'2 h':>9}  commit")
for h in order:
    cells = []
    for g in ("straight", "rotated"):
        v = res[h].get(g)
        cells += ["no output", ""] if v is None else [f"{v[0]:+.4f}", f"{v[1]:+.4f}"]
    print(f"{h:8} {cells[0]:>12} {cells[1]:>9} {cells[2]:>12} {cells[3]:>9}  {subj(h)[:60]}")
print("(signed along-channel error of the worst particle, m; all errors are positions "
      "against the exact answer)")
ok = True
def check(name, passed, detail):
    global ok
    ok &= passed
    print(f"{'PASS' if passed else 'FAIL'}  {name}: {detail}")
worst = lambda h: max((res[h][g] or [0, 0, float('inf')])[2] for g in ("straight", "rotated"))
last = [h for h in order if h != "image"][-1]
first = order[0]
check("last commit exact", worst(last) < 1e-3, f"largest error {worst(last):.2e} m")
check("image exact", worst("image") < 1e-3, f"largest error {worst('image'):.2e} m")
check("first commit off (the test sees the bugs)", worst(first) > 1, f"largest error {worst(first):.1f} m")
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
EOF
