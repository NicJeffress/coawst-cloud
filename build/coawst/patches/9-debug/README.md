# Debug and sensitivity patches

These patches are **not in `series`** and never go into a default build. Each one
was made for a single test: a sensitivity run against a hard-coded constant or
formula, or a trace to find a bug. They are kept so those tests can be repeated.
The patches have no status cards; the results are in the idealized-reef notebook
entries named below.

| Patch | What it changes | Test it was made for |
|---|---|---|
| `streaming-kwd5.patch`, `streaming-kwd200.patch` | Bottom streaming (`wec_streaming.F`): the cap `KWDmax` on the inverse streaming-layer thickness, 20 (stock) to 5 or 200 | 2026-11-04 force shapes: set-up +6.1 % (cap 5) and -1.8 % (cap 200) against the stock cap |
| `streaming-ks03.patch` | Bottom streaming: the hard-coded roughness `ks` in the streaming-layer thickness, 0.03 m to 0.30 m | 2026-11-04 all defaults, streaming roughness: flow within 1.2 % |
| `wec-break-kumar.patch` | Vertical shape of the breaking force (`wec_vf.F`): Kumar et al. 2012, Eq. 30, cosh[2 pi (z+h)/H] with H = Hs/sqrt(2), instead of stock COAWST's length | 2026-11-04 force shapes: set-up within 0.7 %, fore-reef shear -5.4 % |
| `swan-bkd-gamma-live.patch` | SWAN (`swancom1.ftn`): the BKD breaker index is never frozen (stock COAWST freezes it once, when the accuracy first reaches 95 %) | 2026-11-04 all defaults: never frozen is within 2e-6 mm of set-up; the basis for `swan-bkd-exact-restart` |
| `rst-trace.patch` | ROMS (`main3d.F`): bit-exact checksums of the main arrays after each phase of steps 301-410, one file per MPI rank | 2026-11-03 restart residual: found the restart mismatches fixed by `roms-restart-roller` and `roms-ts-fixed-density` |

## Using one

Apply it after the full series, with a series file of your own (paths relative to
`patches/`):

```bash
cp build/coawst/patches/series /tmp/series.kwd5
echo 9-debug/streaming-kwd5.patch >> /tmp/series.kwd5
build/coawst/build.sh --case cases/<Case> --app <FLAG> --tag kwd5 --series /tmp/series.kwd5
```

All six apply after the full series as of 2026-11-12 (checked on the files they
touch); apply one at a time, since the three streaming patches edit the same lines.
They depend on series patches: `wec-break-kumar.patch` edits next to
`3-experimental/wec-break-uniform.patch`, and `swan-bkd-gamma-live.patch` removes
the log line that `1-fixes/swan-bkd-exact-restart.patch` adds. A later change to
the same files may need them refreshed.
