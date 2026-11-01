"""Checks of 3-experimental/roms-step2d-fb.patch (runs of run.sh).

    python -I check.py OUTDIR

OUTDIR/<case>-<run>/ for case a15 and circle, run lf (LF-AM3), fb (AB3-AM4,
same DT and NDTFAST) and ref (LF-AM3, DT and fast step 4 times smaller).

Reports, at the last common record: for zeta, ubar, vbar, u, v and Hwave the
largest and RMS difference of lf and of fb from ref, and of fb from lf; the
wall times; ROMS's PROFILE CPU time of the 2-D kernel, the 2-D halo
exchanges, waiting for SWAN, and in total.
PASS if all runs finished without NaN and fb is not further from ref than
FACTOR times lf (largest difference of every field).
"""
import re
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

out = Path(sys.argv[1])
FIELDS = ("zeta", "ubar", "vbar", "u", "v", "Hwave")
FACTOR = 2.0
ok = True


def last(run, n=None):
    with Dataset(run / "output/ocean_his.nc") as d:
        k = len(d["ocean_time"]) - 1 if n is None else n
        t = float(d["ocean_time"][k])
        f = {}
        for v in FIELDS:
            a = np.ma.filled(d[v][k].astype(float), np.nan)
            m = d[{"xi_u": "mask_u", "xi_v": "mask_v"}.get(d[v].dimensions[-1], "mask_rho")][:] > 0
            f[v] = np.where(m, a, np.nan)
        return t, f


def stats(a, b):
    d = (a - b)[np.isfinite(a - b)]
    return float(np.max(np.abs(d))), float(np.sqrt(np.mean(d ** 2)))


def info(run):
    txt = (run / "image_info.txt").read_text() if (run / "image_info.txt").exists() else ""
    wall = re.search(r"wall_s (\d+)", txt)
    log = (run / "log.txt").read_text(errors="replace") if (run / "log.txt").exists() else ""
    prof = {}
    for key, name in (("kernel", "Model 2D kernel"), ("halo", "Message Passage: 2D halo exchanges"),
                      ("wait", "Unused 04"), ("total", "Total:")):
        pat = rf"^\s*{re.escape(name)}\s*\.*\s*([0-9.]+)" if key != "total" else r"^ Total:\s+([0-9.]+)"
        m = re.findall(pat, log, re.M)
        if m:
            prof[key] = float(m[0])
    return (int(wall.group(1)) if wall else None), ("exit 0" in txt), prof


for case in ("a15", "circle"):
    runs = {r: out / f"{case}-{r}" for r in ("lf", "fb", "ref")}
    fin = {r: info(p) for r, p in runs.items()}
    if not all(f[1] for f in fin.values()):
        print(f"{case}: FAIL  not every run finished: {', '.join(r for r, f in fin.items() if not f[1])}")
        ok = False
        continue
    t, ref = last(runs["ref"])
    with Dataset(runs["ref"] / "output/ocean_his.nc") as d:
        t0 = float(d["ocean_time"][0])
    res = {}
    for r in ("lf", "fb"):
        with Dataset(runs[r] / "output/ocean_his.nc") as d:
            k = list(d["ocean_time"][:]).index(t)
        _, f = last(runs[r], k)
        res[r] = f
        nan = sum(int(np.isnan(f[v]).sum() - np.isnan(ref[v]).sum()) for v in FIELDS)
        if nan:
            ok = False
    print(f"== {case}, t = {(t - t0) / 60:.0f} min (largest / RMS difference)")
    print(f"   {'field':6s} {'lf - ref':>21s} {'fb - ref':>21s} {'fb - lf':>21s}")
    worse = []
    for v in FIELDS:
        a, b, c = stats(res["lf"][v], ref[v]), stats(res["fb"][v], ref[v]), stats(res["fb"][v], res["lf"][v])
        print(f"   {v:6s} {a[0]:10.2e} {a[1]:10.2e} {b[0]:10.2e} {b[1]:10.2e} {c[0]:10.2e} {c[1]:10.2e}")
        if b[0] > FACTOR * a[0] and b[0] > 1e-6:
            worse.append(v)
    w = {r: fin[r][0] for r in fin}
    p = {r: fin[r][2] for r in ("lf", "fb")}
    print(f"   wall: lf {w['lf']} s, fb {w['fb']} s, ref {w['ref']} s")
    print("   ROMS CPU time summed over processes (PROFILE, s): " + "; ".join(
        f"{k} lf {p['lf'].get(k, float('nan')):.0f} fb {p['fb'].get(k, float('nan')):.0f}"
        for k in ("kernel", "halo", "wait", "total")) + "  (kernel = 2-D kernel, halo = 2-D halo "
        "exchanges, wait = waiting for SWAN)")
    good = not worse
    ok &= good
    print(f"   {'PASS' if good else 'FAIL'}  fb no further from ref than {FACTOR} x lf"
          + ("" if good else f" (not for {', '.join(worse)})"))
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
