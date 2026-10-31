"""Checks for the build settings (2-improvements/build-settings.md).

    python -I check.py OUTDIR

OUTDIR from run.sh:
  inlet-<settings>-<n>swan/   Inlet_test, 2 h, n = 1 or 2 SWAN processes, with
                              SPECOUT at 9 points (spread.spc2d, spread.nc)
                              and the case's own point1.spc2d
  a15-<settings>-<machine>-<k>/  Reef_Ideal_A15, 1 h (case_inside.sh); machine
                              e.g. amd or intel, k a repeat number
settings = stock (COAWST's flags and SWAN_SINGLESPEC) or engine.
Checks:
  specout      engine: 2 SWAN processes give the same spectra as 1 (text
               files equal up to trailing blanks, every NetCDF variable
               equal); stock: broken with 2 (shown, expected)
  repeat       the same image on the same machine type twice: identical
  machines     the same image on AMD and Intel machines: identical or not
               (reported)
  flags        A15, engine vs stock: how far apart after 1 h (reported;
               must stay far below the physical signal: relative < 1e-2)
  speed        wall times (reported)
"""
import re
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

out = Path(sys.argv[1])
ok = True
VARS = ("u", "v", "zeta", "ubar", "vbar", "u_stokes", "AKv", "tke")


def check(name, good, text):
    global ok
    ok &= bool(good)
    print(f"{'ok ' if good else 'BAD'} {name}: {text}")


def report(name, text):
    print(f"--  {name}: {text}")


def text_same(a, b):
    if not a.exists() or not b.exists():
        return False
    la = [l.rstrip() for l in a.read_text(errors="replace").splitlines()]
    lb = [l.rstrip() for l in b.read_text(errors="replace").splitlines()]
    return la == lb


def nc_same(a, b):
    try:
        x, y = Dataset(a), Dataset(b)
    except OSError as e:
        return False, f"unreadable ({str(e)[:40]})"
    bad = [v for v in x.variables if v not in y.variables
           or not np.array_equal(np.ma.filled(x[v][:], np.nan), np.ma.filled(y[v][:], np.nan), equal_nan=True)]
    return not bad, ("all variables equal" if not bad else f"differ: {', '.join(bad)}")


# specout
for s in ("stock", "engine"):
    one, two = out / f"inlet-{s}-1swan", out / f"inlet-{s}-2swan"
    if not one.exists():
        continue
    t1 = text_same(one / "spread.spc2d", two / "spread.spc2d")
    t2 = text_same(one / "point1.spc2d", two / "point1.spc2d")
    n_ok, n_txt = nc_same(one / "spread.nc", two / "spread.nc")
    size = lambda d, f: (d / f).stat().st_size if (d / f).exists() else 0
    detail = (f"spread.spc2d {size(one, 'spread.spc2d')} vs {size(two, 'spread.spc2d')} bytes "
              f"({'same' if t1 else 'differ'}), point1.spc2d {'same' if t2 else 'differ'}, spread.nc {n_txt}")
    if s == "engine":
        check("specout engine, 2 SWAN = 1", t1 and t2 and n_ok, detail)
    else:
        report("specout stock (SWAN_SINGLESPEC), 2 SWAN vs 1", detail)


def his(run):
    return Dataset(out / run / "output" / "ocean_his.nc")


def diff(a, b):
    """{var: (max |diff|, relative to the field's largest value)} at the last record."""
    r = {}
    for v in VARS:
        if v not in a.variables:
            continue
        x = np.ma.filled(a[v][-1], np.nan).astype(float)
        y = np.ma.filled(b[v][-1], np.nan).astype(float)
        d = float(np.nanmax(np.abs(x - y)))
        r[v] = (d, d / float(np.nanmax(np.abs(x))))
    return r


runs = sorted(p.name for p in out.glob("a15-*") if (p / "output" / "ocean_his.nc").exists())
by = {}
for r in runs:
    _, s, m, k = r.split("-")
    by.setdefault((s, m), []).append(r)

# repeat: same settings and machine type
for (s, m), rs in sorted(by.items()):
    if len(rs) > 1:
        same = all(max(d for d, _ in diff(his(rs[0]), his(x)).values()) == 0 for x in rs[1:])
        check(f"repeat {s} {m}", same, f"{len(rs)} runs on {m} machines: {'identical' if same else 'differ'}")

# machines: AMD vs Intel, same image
for s in ("stock", "engine"):
    ms = sorted({m for (ss, m) in by if ss == s})
    if len(ms) > 1:
        d = diff(his(by[(s, ms[0])][0]), his(by[(s, ms[1])][0]))
        worst = max(rel for _, rel in d.values())
        report(f"machines {s}", f"{ms[0]} vs {ms[1]}: " + ("identical" if worst == 0 else
               f"largest relative difference {worst:.1e} (" + ", ".join(f"{v} {a:.1e}" for v, (a, _) in d.items()) + ")"))

# flags: engine vs stock on the same machine type
for m in sorted({m for (_, m) in by}):
    if ("stock", m) in by and ("engine", m) in by:
        d = diff(his(by[("stock", m)][0]), his(by[("engine", m)][0]))
        worst = max(rel for _, rel in d.values())
        check(f"flags {m}", worst < 1e-2, f"engine vs stock after 1 h: largest relative difference {worst:.1e} ("
              + ", ".join(f"{v} {a:.1e}" for v, (a, _) in d.items()) + ")")


# speed
def wall(run):
    m = re.search(r"wall_s (\d+)", (out / run / "image_info.txt").read_text())
    return int(m.group(1)) if m else None


for (s, m), rs in sorted(by.items()):
    report(f"speed a15 {s} {m}", "wall " + ", ".join(f"{wall(r)} s" for r in rs))
for s in ("stock", "engine"):
    rs = [f"inlet-{s}-{n}swan" for n in (1, 2) if (out / f"inlet-{s}-{n}swan").exists()]
    if rs:
        report(f"speed inlet {s}", ", ".join(f"{r.split('-')[-1]} {wall(r)} s" for r in rs))
print("ALL OK" if ok else "SOME CHECKS BAD")
sys.exit(0 if ok else 1)
