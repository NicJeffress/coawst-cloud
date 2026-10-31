"""Checks for 2-improvements/swan-periodic-curvilinear.patch.

    python -I check.py OUTDIR

OUTDIR from run.sh: <case>-np<N> (with the patch) and <case>-np1-before
(without it); cases from make_inputs.py. All fields at the last output
time (1 h). Checks:
  refused       stock SWAN stops on a REPEATING curvilinear grid
  same grid     the uniform grid as CURVILINEAR = as REGULAR, bit for bit
  shift         seam through the pass = pass in the middle rolled by half a
                period (stretched grid; Reef_Ideal_A15's grid), 1 and 4
                processes: within SWAN's iteration error at the seam
                (< 1e-4 m stretched, < 5e-4 m A15); a geometry error at the
                seam would be 0.1-1 m
  processes     4 processes = 1, bit for bit (Hs, FORCE)
  periodic      the periodic boundary matters: non-periodic differs
  flat reef     no pass: Hs the same in every column of a row, within the
                stretching effect (< 1e-4 m uniform grid, < 5e-3 m stretched)
  search        FRAME output over two periods: none missing, each period a
                copy of the other, equal to interpolated grid output; POINTS
                in the seam mesh and whole periods away found and equal to it
  bad period    a closing column that is not column 1 shifted by one period:
                SWAN stops with a message
  unchanged     without vs with the patch, cases that do not need it
                (regular periodic, curvilinear non-periodic): bit-identical,
                except FORCE at the seam of the regular grid (corrected)
"""
import sys
from pathlib import Path

import netCDF4
import numpy as np

out = Path(sys.argv[1])
ok = True


def check(name, good, text):
    global ok
    ok &= bool(good)
    print(f"{'ok ' if good else 'BAD'} {name}: {text}")


def field(run, fname="hsign.nc", var=None):
    """(y, x) field at the last output time, NaN where masked; None if missing."""
    f = out / run / "output" / fname
    if not f.exists():
        return None
    with netCDF4.Dataset(f) as d:
        v = d.variables[var] if var else [v for v in d.variables.values() if v.ndim == 3][0]
        return np.ma.filled(v[-1].astype(float), np.nan)


def maxdiff(a, b):
    """Largest |a - b| (inf if missing or shapes or masks differ)."""
    if a is None or b is None or a.shape != b.shape or not np.array_equal(np.isnan(a), np.isnan(b)):
        return np.inf
    d = np.abs(a - b)
    return 0.0 if np.isnan(d).all() else float(np.nanmax(d))


def along_range(a):
    return np.inf if a is None else float(np.nanmax(np.nanmax(a, axis=1) - np.nanmin(a, axis=1)))


def text(run):
    d = out / run
    return "".join(p.read_text(errors="replace") for p in [d / "log.txt", *d.glob("PRINT*")] if p.exists())


# refused before the patch
t = text("str-mid-np1-before")
check("refused before", "Curvilinear grid cannot be REPeating" in t and field("str-mid-np1-before") is None,
      "stock SWAN: 'Curvilinear grid cannot be REPeating', no output" if "cannot be REP" in t
      else "no refusal message found")

# same grid
d = {q: maxdiff(field("uni-crv-mid-np1", q), field("uni-reg-mid-np1", q)) for q in ("hsign.nc", "dir.nc", "dissip.nc")}
check("same grid", all(v == 0 for v in d.values()),
      "uniform grid, curvilinear vs regular: " + ", ".join(f"{q[:-3]} {v:.1e}" for q, v in d.items()))

# shift (seam through the pass vs rolled)
for case, lim in (("str", 1e-4), ("a15", 5e-4)):
    for np_ in (1, 4):
        mid, seam = field(f"{case}-mid-np{np_}"), field(f"{case}-seam-np{np_}")
        w = maxdiff(seam, None if mid is None else np.roll(mid, -(mid.shape[1] // 2), axis=1))
        check(f"shift {case} np{np_}", w < lim, f"seam through the pass vs rolled: max |dHs| {w:.1e} m (limit {lim:.0e})")

# processes
pairs = [(f"{c}-np4", f"{c}-np1", "hsign.nc", None) for c in ("str-mid", "str-seam", "str-flat", "a15-mid", "a15-seam")]
bad = [f"{a}" for a, b, f, v in pairs if maxdiff(field(a, f, v), field(b, f, v)) != 0]
check("processes", not bad, f"Hs in {len(pairs)} runs, 4 processes vs 1: " + ("all identical" if not bad else "differ: " + ", ".join(bad)))
# FORCE with several processes: stock SWAN leaves out the rows at the
# boundaries between the processes' strips (also on regular grids, with or
# without REPEATING; not changed by this patch, see its document). Compare
# where both runs have values, and name the missing rows.
for q in ("xfor", "yfor"):
    a, b = field("str-flat-np4", "force.nc", q), field("str-flat-np1", "force.nc", q)
    both = ~np.isnan(a) & ~np.isnan(b)
    rows = sorted(set(np.nonzero(np.isnan(a) & ~np.isnan(b))[0].tolist()))
    whole = all(np.isnan(a[r]).all() for r in rows)
    w = float(np.max(np.abs(a[both] - b[both])))
    check(f"processes FORCE {q}", w == 0 and whole and len(rows) <= 3,
          f"4 processes vs 1: identical where both have values; rows {rows} missing with 4 "
          f"(the strip boundaries; stock SWAN does the same)")

# periodic boundary in effect
for case in ("str", "a15"):
    rep, norep = field(f"{case}-mid-np1"), field(f"{case}-norep-np1")
    w = np.inf if rep is None or norep is None else float(np.nanmax(np.abs(norep[:, :rep.shape[1]] - rep)))
    check(f"periodic {case}", 0.1 < w < np.inf, f"non-periodic vs periodic: max |dHs| {w:.2f} m")

# flat reef
for case, lim in (("uni-reg-flat-np1", 1e-4), ("str-flat-np1", 5e-3), ("str-flat-np4", 5e-3)):
    r = along_range(field(case))
    fr = max(along_range(field(case, "force.nc", q)) for q in ("xfor", "yfor"))
    check(f"flat reef {case[:-4]}{'' if case.endswith('np1') else ' np4'}", r < lim,
          f"largest Hs range along a row {r:.1e} m (limit {lim:.0e}); FORCE range {fr:.1e} N m-2")

# search: FRAME and POINTS
run = out / "str-search-np1"
coords = np.loadtxt(run / "coord.grd")
ny = coords.shape[0] // 2
xs, ys = coords[0], coords[ny:, 0]           # rectilinear: x per column, y per row
period = xs[-1] - xs[0]
mid1 = field("str-mid-np1")
n = mid1.shape[1]


def interp(F, xp, yp):
    """Bilinear in index space (SWAN's for a rectilinear grid), periodic in x."""
    Fc = np.concatenate([F, F[:, :1]], axis=1)
    xw = xs[0] + np.mod(xp - xs[0], period)
    i = np.clip(np.searchsorted(xs, xw, side="right") - 1, 0, n - 1)
    j = np.clip(np.searchsorted(ys, yp, side="right") - 1, 0, ny - 2)
    tx = (xw - xs[i]) / (xs[i + 1] - xs[i])
    ty = (yp - ys[j]) / (ys[j + 1] - ys[j])
    return ((1 - tx) * (1 - ty) * Fc[j, i] + tx * (1 - ty) * Fc[j, i + 1]
            + (1 - tx) * ty * Fc[j + 1, i] + tx * ty * Fc[j + 1, i + 1])


check("search grid", maxdiff(field("str-search-np1"), mid1) == 0, "str-search grid output = str-mid")
frm = field("str-search-np1", "hsign_frm.nc")
if frm is None:
    check("search FRAME", False, "no FRAME output")
else:
    line = [l for l in (run / "swan.in").read_text().splitlines() if l.startswith("FRAME")][0].split()
    fx0, fy0, flen, fylen, fmx, fmy = (float(line[2]), float(line[3]), float(line[5]),
                                       float(line[6]), int(line[7]), int(line[8]))
    fx, fy = np.meshgrid(fx0 + np.arange(fmx + 1) * flen / fmx, fy0 + np.arange(fmy + 1) * fylen / fmy)
    sq = np.sqrt(interp(mid1 ** 2, fx, fy))            # SWAN interpolates Hs^2 (energy)
    miss = int(np.isnan(frm).sum())
    w_copy = maxdiff(frm[:, :fmx // 2], frm[:, fmx // 2:fmx])
    # the seam mesh: between the last column and column 1 + period
    col = np.searchsorted(xs, xs[0] + np.mod(fx - xs[0], period), side="right") - 1
    err = np.abs(frm - sq)
    w_seam, w_in = float(np.nanmax(err[col >= n - 1])), float(np.nanmax(err[col < n - 1]))
    check("search FRAME", miss == 0 and w_copy == 0 and w_seam < 1e-5,
          f"{frm.size} points over two periods, {miss} missing; one period vs the next {w_copy:.1e}; "
          f"in the seam mesh vs interpolated grid output {w_seam:.1e} m "
          f"(elsewhere {w_in:.1e}, 99th percentile {np.nanpercentile(err[col < n - 1], 99):.0e}: "
          f"this interpolation is not exactly SWAN's at steep gradients)")
tab = run / "output" / "pts.tab"
if not tab.exists():
    check("search POINTS", False, "no POINTS output")
else:
    pts = np.loadtxt(run / "points.txt")
    hs = np.loadtxt(tab)[-len(pts):, 2]
    sq = np.sqrt(interp(mid1 ** 2, pts[:, 0], pts[:, 1]))
    found = int(np.sum(hs > -9))
    w = float(np.max(np.abs(hs - sq)))
    same = len(set(hs[4:8])) == 1                    # column 11 and its copies 1 and 2 periods away
    check("search POINTS", found == len(pts) and w <= 5e-4 and same,
          f"{found}/{len(pts)} points found (in the seam mesh, 1 and 2 periods away), copies equal: {same}; "
          f"vs interpolated {w:.1e} m (the table prints 3 decimals)")

# bad closing column
t = text("str-badper-np1")
check("bad period", "not column 1 shifted by one period" in t and field("str-badper-np1") is None,
      "stops: 'last column is not column 1 shifted by one period'" if "shifted by one period" in t
      else "no message")

# unchanged where the patch is not needed
for case, qs in (("uni-reg-mid", ("hsign.nc", "dir.nc", "dissip.nc")), ("str-norep", ("hsign.nc", "dir.nc", "dissip.nc")),
                 ("uni-reg-flat", ("hsign.nc", "dir.nc", "dissip.nc"))):
    d = {q: maxdiff(field(f"{case}-np1", q), field(f"{case}-np1-before", q)) for q in qs}
    check(f"unchanged {case}", all(v == 0 for v in d.values()),
          "before vs after: " + ", ".join(f"{q[:-3]} {v:.1e}" for q, v in d.items()))
for q in ("xfor", "yfor"):
    a, b = field("uni-reg-flat-np1", "force.nc", q), field("uni-reg-flat-np1-before", "force.nc", q)
    if a is None or b is None:
        check(f"FORCE {q} regular seam", False, "missing")
        continue
    diff = np.abs(a - b)
    cols = sorted(set(np.nonzero(np.nan_to_num(diff) > 0)[1].tolist()))
    check(f"FORCE {q} regular seam", all(c in (0, a.shape[1] - 1) for c in cols),
          f"before vs after: differs only in columns {cols} (the seam), by up to {np.nanmax(diff):.2e} N m-2; "
          f"after, range along a row {along_range(a):.1e}, before {along_range(b):.1e}")
print("ALL OK" if ok else "SOME CHECKS BAD")
sys.exit(0 if ok else 1)
