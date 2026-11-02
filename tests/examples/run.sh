#!/bin/bash
# COAWST examples sweep: build every example in examples.tsv as stock COAWST
# and with the engine's patches, run them, and compare the outputs.
#
#   tests/examples/run.sh OUTDIR [NAME ...]
#
# Three builds per example (variants):
#   stock    COAWST as shipped (no patches, COAWST's compiler flags)
#   patched  the whole patch series, COAWST's compiler flags
#   engine   the whole patch series, the engine's build settings (the default
#            build)
# stock vs patched shows what the patches change; patched vs engine what the
# build settings change. To find the patch behind a change, a variant
#   upto-<patch>  the series up to and including <patch> (its name without
#                 folder and .patch), COAWST's compiler flags
# builds part of the series; compare consecutive ones with PAIRS (compare.py).
#
# Stages (STAGES, default "build pack run compare"):
#   build    builds the images coawst-ex:<name>-<variant>; logs in OUTDIR/build/
#   pack     puts all binaries and the example folders into one image,
#            coawst-ex:sweep (so one Cloud Batch job can run everything)
#   run      runs the examples from that image on this machine, one after the
#            other (example_inside.sh); the same runner works as a Cloud Batch
#            task, one example per task (BATCH_TASK_INDEX)
#   compare  compares the outputs (compare.py) and writes OUTDIR/results.md
# NAME: only these examples (default: all). Environment: PYTHON (with numpy,
# scipy and netCDF4) for compare; VARIANTS to restrict the variants; MINUTES
# to run every example for that long instead (quick checks); PAIRS for
# compare (e.g. "stock:upto-roms-vegetation upto-roms-vegetation:patched").
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
[ $# -ge 1 ] || { sed -n '2,25p' "$0"; exit 2; }
OUT=$(realpath -m "$1"); shift
STAGES=${STAGES:-build pack run compare}
VARIANTS=${VARIANTS:-stock patched engine}
PYTHON=${PYTHON:-python3}
mkdir -p "$OUT"

rows() { grep -v '^#' "$here/examples.tsv" | grep -v '^[[:space:]]*$'; }
names=("$@")
[ ${#names[@]} -gt 0 ] || mapfile -t names < <(rows | cut -f1)
row() { rows | awk -F'\t' -v n="$1" '$1 == n' | grep . || { echo "run.sh: no example $1" >&2; exit 2; }; }
tag() { echo "coawst-ex:$(echo "$1" | tr 'A-Z' 'a-z')-$2"; }

variant_args() {
    case "$1" in
        stock)   echo "--series none -- --build-arg BUILD_SETTINGS=stock" ;;
        patched) echo "-- --build-arg BUILD_SETTINGS=stock" ;;
        engine)  echo "" ;;
        upto-*)
            local p=${1#upto-} f
            f=$(grep -E "(^|/)$p\.patch\$" "$repo/build/coawst/patches/series") \
                || { echo "run.sh: no patch $p in the series" >&2; exit 2; }
            "$repo/tests/tools/series_upto.sh" "$f" > "$OUT/build/series-$1"
            echo "--series $OUT/build/series-$1 -- --build-arg BUILD_SETTINGS=stock" ;;
        *) echo "run.sh: unknown variant $1" >&2; exit 2 ;;
    esac
}

if [[ " $STAGES " == *" build "* ]]; then
    mkdir -p "$OUT/build"
    for n in "${names[@]}"; do
        IFS=$'\t' read -r _ project app _ < <(row "$n")
        for v in $VARIANTS; do
            log=$OUT/build/$n-$v.log
            # shellcheck disable=SC2046
            if "$repo/build/coawst/build.sh" --project "$project" --app "$app" --tag "$(tag "$n" "$v")" \
                    $(variant_args "$v") > "$log" 2>&1; then
                echo "built $n $v"
            else
                echo "BUILD FAILED $n $v (see $log)"
            fi
        done
    done
fi

if [[ " $STAGES " == *" pack "* ]]; then
    # Files are copied out of each image into one build context, so the sweep
    # image adds two layers (Docker allows about 120).
    ctx=$(mktemp -d)
    trap 'rm -rf "$ctx"' EXIT
    mkdir -p "$ctx/sweep" "$ctx/coawst"
    cp "$here/examples.tsv" "$here/example_inside.sh" "$ctx/sweep/"
    echo "$VARIANTS" > "$ctx/sweep/variants"   # the runner's default
    base="" nbin=0
    for n in "${names[@]}"; do
        IFS=$'\t' read -r _ project _ < <(row "$n")
        for v in $VARIANTS; do
            t=$(tag "$n" "$v")
            docker image inspect "$t" > /dev/null 2>&1 || { echo "pack: $t missing (build failed?)"; continue; }
            base=${base:-$t}
            mkdir -p "$ctx/sweep/$v/$n" "$ctx/sweep/$v/ROMS/External" "$ctx/coawst/$(dirname "$project")"
            cid=$(docker create "$t")
            docker cp -q "$cid:/opt/coawst/coawstM" "$ctx/sweep/$v/$n/"
            docker cp -q "$cid:/opt/coawst/PATCHES_APPLIED" "$ctx/sweep/$v/$n/"
            docker cp -q "$cid:/opt/coawst/ROMS/External/varinfo.yaml" "$ctx/sweep/$v/ROMS/External/"
            [ -d "$ctx/coawst/$project" ] || docker cp -q "$cid:/opt/coawst/$project" "$ctx/coawst/$project"
            docker rm "$cid" > /dev/null
            nbin=$((nbin + 1))
        done
    done
    [ -n "$base" ] || { echo "run.sh: no images to pack" >&2; exit 1; }
    printf 'FROM %s\nCOPY sweep/ /opt/sweep/\nCOPY coawst/ /opt/coawst/\n' "$base" > "$ctx/Dockerfile"
    docker build -q -t coawst-ex:sweep "$ctx" > /dev/null
    echo "packed coawst-ex:sweep ($nbin binaries)"
fi

if [[ " $STAGES " == *" run "* ]]; then
    mkdir -p "$OUT/runs"
    docker run --rm --user "$(id -u):$(id -g)" -v "$OUT/runs:/work" -w /work \
        -e VARIANTS="$VARIANTS" -e MINUTES="${MINUTES:-}" coawst-ex:sweep bash /opt/sweep/example_inside.sh "${names[@]}"
fi

if [[ " $STAGES " == *" compare "* ]]; then
    PAIRS=${PAIRS:-} "$PYTHON" -I "$here/compare.py" "$OUT/runs" "$here/examples.tsv" "${names[@]}" | tee "$OUT/results.md"
fi
