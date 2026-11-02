#!/bin/bash
# Thin-crest variants of Reef_Ideal_A15: does the full bottom stress fail where
# LIMIT_BSTRESS's cap would bind? (Record of 2026-11-02, see the patch document.)
#
#   tests/experimental/roms-bstress-implicit/thin_crest.sh OUTDIR [MINUTES] [GRIDS]
#
# make_thin_crest.py writes OUTDIR/Reef_Ideal_A15_thin (the case plus grids
# thin_smooth, thin_steep, steep_050; see its docstring). Builds three images
# (all -SPLINES_VVISC): cap (+LIMIT_BSTRESS), nocap (the explicit stress as
# shipped), imp (+BSTRESS_IMPLICIT), and runs each on each grid in GRIDS
# (default: thin_steep) for MINUTES (default 180: through low tide), ROMS 1x6
# + 2 SWAN, history every 10 min. Then thin_crest_summary.py and cap_stats.py
# print the fastest currents, vertical Courant numbers, crest current, set-up
# and the stress stability number on the crest. STAGES as in run.sh.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
root=$here/../../..
OUT=$(realpath -m "$1"); MIN=${2:-180}; GRIDS=${3:-thin_steep}
PY=${PYTHON:-python3}
STAGES=${STAGES:-build run check}
export MPIRUN_ARGS=${MPIRUN_ARGS:---oversubscribe}
mkdir -p "$OUT"
has() { [[ " $STAGES " == *" $1 "* ]]; }
if has build; then
    "$PY" -I "$here/make_thin_crest.py" "$root/tests/cases/Reef_Ideal_A15" "$OUT/Reef_Ideal_A15_thin"
    b() { "$root/build/coawst/build.sh" --case "$OUT/Reef_Ideal_A15_thin" --app REEF_IDEAL_A15 \
            --tag coawst-test:bsi-thin-$1 -- --build-arg CPP_OPTIONS="$2" > "$OUT/build-$1.log" 2>&1; }
    b cap "-SPLINES_VVISC +LIMIT_BSTRESS"
    b nocap "-SPLINES_VVISC"
    b imp "-SPLINES_VVISC +BSTRESS_IMPLICIT"
fi
runs=()
for g in $GRIDS; do for s in cap nocap imp; do runs+=("$s-$g"); done; done
if has run; then
    export OUTDT=10
    for r in "${runs[@]}"; do
        s=${r%%-*}; g=${r#*-}
        rm -rf "${OUT:?}/$r"
        OCEANSED="s/^( *GRDNAME *== *).*/\1roms_grid_$g.nc/" \
        SWANSED="s/'swan_bathy_default_1.bot'/'swan_bathy_$g.bot'/" \
        "$tools/run_case.sh" coawst-test:bsi-thin-$s "$OUT" "$r" Reef_Ideal_A15_thin 1 6 2 "$MIN" || true
    done
fi
if has check; then
    dirs=(); for r in "${runs[@]}"; do dirs+=("$OUT/$r"); done
    { "$PY" -I "$here/thin_crest_summary.py" "${dirs[@]}"; "$PY" -I "$here/cap_stats.py" "${dirs[@]}"; } | tee "$OUT/thin_crest.txt"
fi
