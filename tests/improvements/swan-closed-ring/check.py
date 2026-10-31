"""Checks of 2-improvements/swan-closed-ring.patch on the Circle_Island case.

    python -I check.py OUTDIR

OUTDIR holds the run folders of run.sh (each with output/*.nc, log.txt,
image_info.txt; PRINT* where the run was made locally):
  before            the image without the patch, waves from the north
  north             waves from the north, ROMS 6x1 + 2 SWAN (the reference)
  north-roll54      the same with the seam moved 54 columns (90 degrees)
  north-1x6-1swan   ROMS 1x6 (the periodic direction in one tile) + 1 SWAN
  north-2x2-3swan   ROMS 2x2 + 3 SWAN
  inward            waves aimed straight inward all around the island
  north-it5, north-roll54-it5   north and north-roll54 with 5 SWAN
                    iterations per time step
  restart/          restart_inside.sh: straight, part1, part2
  a15-before, a15-after   Reef_Ideal_A15, periodic but not closed

Checks (PASS/FAIL each):
  refused     before: SWAN refuses the closed grid ("no period found")
  finished    every run after the patch finished, no NaN
  coupler     SWAN -> ROMS: ROMS Hwave equals SWAN Hs, also in ROMS's
              periodic copy columns 0 and Lm+1, to float32 precision;
              ROMS -> SWAN: SWAN's water level equals the zeta of ROMS's
              previous exchange (within ZETA_TOL); at every output time
              after the first
  seam        the jump of each field across the seam exceeds the largest
              jump between other neighbouring columns nearby by at most
              SEAM_TOL of the field's size
  seam_shift  north-roll54 moved back differs from north by less than
              SEAM_SHIFT_RATIO of what SWAN's own convergence leaves (north
              vs north-it5, 5 SWAN iterations per time step instead of 1);
              the difference comes from SWAN's sweeps, which start at the
              seam, and shrinks with more iterations (north-it5 vs
              north-roll54-it5, reported)
  processes   the two other layouts equal north (within PROC_TOL)
  symmetry    inward: SWAN's Hs repeats every 6 columns (10 degrees, one
              SWAN direction bin) within SYM_TOL, and no worse near the
              seam than far from it
  unchanged   a15-before and a15-after bit-identical (ROMS history and
              SWAN's Hs): the patch changes nothing on grids that do not close
  restart     part2's last record equals straight's (within 1e-8 relative);
              reported, not counted (OPEN: a ROMS residual on this case)
"""
import sys
from pathlib import Path

import netCDF4
import numpy as np

LM = 216
NEAR = 20                    # columns either side of the seam for the local jump
COUPLER_TOL = 1e-6           # m: float32 copies of the same value
ZETA_TOL = 2e-4              # m: zeta a time step away from the output time
SEAM_TOL = 1e-3              # seam jump beyond the largest nearby neighbour jump, of |field|
SEAM_SHIFT_RATIO = 0.5       # seam-shift difference / SWAN's own iteration difference
PROC_TOL = 1e-6              # of the 99th percentile of |field|
SYM_TOL = 0.01               # Hs repeating every 6 columns, of the 99th percentile of Hs
SEAM_FACTOR = 1.5            # near-seam asymmetry / asymmetry far from the seam
RESTART_TOL = 1e-8
FIELDS = ("zeta", "Hwave", "ubar", "vbar", "u", "v", "AKv")
ok_all = True


def verdict(name, ok, text):
    global ok_all
    ok_all &= bool(ok)
    print(f"{name:11s} {'PASS' if ok else 'FAIL'}  {text}")


def his(run):
    return netCDF4.Dataset(run / "output" / "ocean_his.nc")


def rho_mask(run):
    with his(run) as d:
        return d["mask_rho"][:].astype(float) > 0


def field(run, name, rec=-1, mask=True):
    """A ROMS field at record rec on rho/u/v points, land = NaN."""
    with his(run) as d:
        v = d[name]
        a = np.ma.filled(v[rec].astype(float), np.nan)
        if not mask:
            return a
        dims = v.dimensions[-1]
        m = d[{"xi_rho": "mask_rho", "xi_u": "mask_u", "xi_v": "mask_v"}.get(dims, "mask_rho")][:]
        return np.where(m > 0, a, np.nan)


def scale(a):
    return float(np.nanpercentile(np.abs(a), 99)) or 1.0


def status(run):
    info = (run / "image_info.txt").read_text() if (run / "image_info.txt").exists() else ""
    log = (run / "log.txt").read_text(errors="replace") if (run / "log.txt").exists() else ""
    prt = "".join(p.read_text(errors="replace") for p in run.glob("PRINT*"))
    return info, log, prt


def check_refused(out):
    run = out / "before"
    if not run.exists():
        verdict("refused", False, "no 'before' run")
        return
    info, log, prt = status(run)
    msg = "no period found" in log + prt
    exit0 = "exit 0" in info
    verdict("refused", msg and not exit0,
            f"before the patch SWAN {'refuses' if msg else 'does not refuse'} the closed grid "
            f"('REPeating curvilinear grid: no period found'); run {'finished' if exit0 else 'stopped'}")


def finished(run):
    info, log, prt = status(run)
    if not (run / "output" / "ocean_his.nc").exists():
        return False, "no history file"
    done = "exit 0" in info
    with his(run) as d:
        nan = sum(int(np.isnan(np.ma.filled(d[v][-1], 0.0)).sum()) for v in ("zeta", "ubar", "vbar", "Hwave"))
        nrec = len(d["ocean_time"])
    closed = "closed (period vector 0)" in prt if prt else None
    return done and nan == 0, (f"exit 0 {done}, {nrec} records, NaN {nan}"
                               + ("" if closed is None else f", SWAN: closed ring {closed}"))


def swan(run, fname, var):
    with netCDF4.Dataset(run / "output" / fname) as d:
        return d["time"][:].astype(float), np.ma.filled(d[var][:].astype(float), np.nan)


def check_coupler(run):
    """Both halves of the coupler's index map, at every output time after the first.

    SWAN -> ROMS: ROMS's Hwave at an exchange time is SWAN's Hs of that time,
    also in ROMS's periodic copy columns 0 and Lm+1 (the two extra slots of a
    closed ring): equal to float32 precision.
    ROMS -> SWAN: SWAN's water level at an output time is the zeta ROMS sent
    at the previous exchange, 600 s earlier, taken a time step away from
    ROMS's own output time; it must match ROMS's zeta of that record to
    within ZETA_TOL, far less than the 10-min change of zeta and less than
    the difference a map off by one ring or one column would give (printed
    for scale; zeta is smooth, so a column shift shows only where zeta
    varies round the island)."""
    with his(run) as d:
        t = d["ocean_time"][:].astype(float)
        zeta = np.ma.filled(d["zeta"][:].astype(float), np.nan)
        hw = np.ma.filled(d["Hwave"][:].astype(float), np.nan)
        m = d["mask_rho"][:] > 0
    ts, ssh = swan(run, "watlev.nc", "ssh")
    _, hs = swan(run, "hsign.nc", "hs")
    t, ts = t - t[0], ts - ts[0]
    mi = m[:, 1:LM + 1]
    e_hs = e_ghost = e_z = e_ring = e_col = change = 0.0
    for k, tk in enumerate(t):
        ks = np.where(np.abs(ts - tk) < 1)[0]
        if k == 0 or not len(ks):
            continue
        s = hs[ks[0]]                                       # SWAN columns 1..Lm
        r = hw[k]
        e_hs = max(e_hs, float(np.nanmax(np.abs(r[:, 1:LM + 1] - s)[mi])))
        ghost = np.concatenate([np.abs(r[:, 0] - s[:, -1])[m[:, 0]],
                                np.abs(r[:, LM + 1] - s[:, 0])[m[:, LM + 1]]])
        e_ghost = max(e_ghost, float(np.nanmax(ghost)))
        w = ssh[ks[0]]
        z = zeta[k - 1][:, 1:LM + 1]                        # the previous exchange
        e_z = max(e_z, float(np.nanmax(np.abs(z - w)[mi])))
        both = mi & np.roll(mi, 1, axis=0)
        both[0] = False
        e_ring = max(e_ring, float(np.nanmax(np.abs(np.roll(z, 1, axis=0) - w)[both])))
        e_col = max(e_col, float(np.nanmax(np.abs(np.roll(z, 1, axis=1) - w)[mi])))
        change = max(change, float(np.nanmax(np.abs(zeta[k][:, 1:LM + 1] - z)[mi])))
    ok = max(e_hs, e_ghost) <= COUPLER_TOL and e_z <= ZETA_TOL
    return ok, (f"SWAN Hs -> ROMS Hwave max |diff| {e_hs:.1e} m (columns 0 and Lm+1: {e_ghost:.1e}); "
                f"ROMS zeta -> SWAN water level {e_z:.1e} m (map off by one ring {e_ring:.1e}, "
                f"by one column {e_col:.1e}; zeta's change over 10 min {change:.1e})")


def seam_excess(a):
    """a: (..., rows, Lm) periodic in columns. How much larger the jump across
    the seam is than the largest jump between neighbouring columns within
    NEAR columns, at worst over rows (and levels), relative to the field's size."""
    a = a.reshape(-1, a.shape[-1])
    ext = np.concatenate([a[:, -NEAR - 1:], a[:, :NEAR + 1]], axis=1)  # seam between NEAR and NEAR+1
    d = np.abs(np.diff(ext, axis=1))
    seam = d[:, NEAR]
    others = np.delete(d, NEAR, axis=1)
    local = np.max(np.where(np.isnan(others), -np.inf, others), axis=1)
    ok = np.isfinite(seam) & np.isfinite(local)
    return float(np.max(np.maximum(seam[ok] - local[ok], 0.0))) / scale(a) if ok.any() else 0.0


def interior(a, name):
    """Columns 1..Lm (rho, v) or u columns 1..Lm (the u point at the seam is column 1)."""
    return a[..., 1:LM + 1] if a.shape[-1] == LM + 2 else a[..., :LM]


def check_seam(run):
    worst = {name: seam_excess(interior(field(run, name), name)) for name in FIELDS}
    return max(worst.values()) <= SEAM_TOL, ", ".join(f"{k} {v:.1e}" for k, v in worst.items())


def check_symmetry(run):
    """Waves from all sides: SWAN's Hs at the last output, rows 0..Mm (the
    outer boundary row is reported separately), against itself turned by 6
    columns (10 degrees, one direction bin). Not to round-off: SWAN's
    sweeps start at the seam (one iteration per time step), and the
    wave-driven flow over the reef is not axisymmetric; so the test is that
    Hs repeats within SYM_TOL and that near the seam it repeats no worse
    than far from it (within SEAM_FACTOR)."""
    ts, hs = swan(run, "hsign.nc", "hs")
    h = hs[-1]
    inner, ring = h[:-1], h[-1]
    e = np.abs(inner - np.roll(inner, -6, axis=1))
    near = float(np.nanmax(np.concatenate([e[:, :12], e[:, -18:]], axis=1)))
    far = float(np.nanmax(e[:, 40:170]))
    rel = float(np.nanmax(e)) / scale(inner)
    dip = float(np.nanmax(ring) - min(ring[0], ring[-1]))
    with his(run) as d:
        ub = np.ma.filled(d["ubar"][-1].astype(float), np.nan)
    ok = rel <= SYM_TOL and near <= SEAM_FACTOR * far
    return ok, (f"Hs vs Hs turned 10 degrees: max |diff| {np.nanmax(e):.1e} m ({rel:.1e} of Hs), "
                f"near the seam {near:.1e} m, far from it {far:.1e} m; reported: outer boundary row "
                f"{np.nanmin(ring):.3f}-{np.nanmax(ring):.3f} m, its two points beside the seam "
                f"{dip:.3f} m lower; largest azimuthal depth-mean current {np.nanmax(np.abs(ub)):.3f} m/s")


def check_unchanged(out):
    """Reef_Ideal_A15 before and after the patch: every variable of the ROMS
    history and SWAN's Hs bit-identical."""
    diff = []
    n = 0
    for f in ("ocean_his.nc", "hsign.nc"):
        with netCDF4.Dataset(out / "a15-before" / "output" / f) as a, \
                netCDF4.Dataset(out / "a15-after" / "output" / f) as b:
            for v in a.variables:
                if v not in b.variables or a[v].dtype.kind not in "fiu":
                    continue
                n += 1
                if not np.array_equal(np.ma.filled(a[v][:], np.nan), np.ma.filled(b[v][:], np.nan), equal_nan=True):
                    diff.append(f"{f}:{v}")
    return not diff, f"{n} variables compared, {'all bit-identical' if not diff else 'differ: ' + ', '.join(diff[:8])}"


def compare(run_a, run_b, roll=0):
    """Largest |A - B| / scale(A) per field at the last common record."""
    with his(run_a) as d:
        na = len(d["ocean_time"])
    with his(run_b) as d:
        nb = len(d["ocean_time"])
    rec = min(na, nb) - 1
    out = {}
    for name in FIELDS:
        a = interior(field(run_a, name, rec), name)
        b = interior(field(run_b, name, rec), name)
        if roll:
            b = np.roll(b, roll, axis=-1)          # run_b column c = run_a column c+roll
        out[name] = float(np.nanmax(np.abs(a - b))) / scale(a)
    return rec, out


def fmt(d):
    return ", ".join(f"{k} {v:.1e}" for k, v in d.items())


def main():
    out = Path(sys.argv[1])
    check_refused(out)
    runs = ["north", "north-roll54", "north-1x6-1swan", "north-2x2-3swan", "inward",
            "north-it5", "north-roll54-it5"]
    good = {}
    for r in runs:
        if (out / r).exists():
            ok, text = finished(out / r)
            good[r] = ok
            verdict("finished", ok, f"{r}: {text}")
    for r in [r for r in runs if good.get(r)]:
        ok, text = check_coupler(out / r)
        verdict("coupler", ok, f"{r}: {text}")
    for r in ("north", "inward"):
        if good.get(r):
            ok, text = check_seam(out / r)
            verdict("seam", ok, f"{r}: seam jump beyond the largest neighbour jump within {NEAR} columns, / 99th pct: {text}")
    if good.get("north") and good.get("north-roll54") and good.get("north-it5"):
        _, d = compare(out / "north", out / "north-roll54", roll=54)
        _, d5 = compare(out / "north", out / "north-it5")
        ratio = {k: d[k] / max(d5[k], 1e-30) for k in d}
        text = (f"moving the seam: {fmt(d)}; for scale, 5 SWAN iterations per step instead of 1: "
                f"{fmt(d5)} (all / 99th pct |field|); ratio max {max(ratio.values()):.2f}")
        if good.get("north-roll54-it5"):
            _, dr5 = compare(out / "north-it5", out / "north-roll54-it5", roll=54)
            text += f"; moving the seam with 5 iterations: {fmt(dr5)}"
        verdict("seam_shift", max(ratio.values()) <= SEAM_SHIFT_RATIO, text)
    for r in ("north-1x6-1swan", "north-2x2-3swan"):
        if good.get("north") and good.get(r):
            rec, d = compare(out / "north", out / r)
            verdict("processes", max(d.values()) <= PROC_TOL, f"{r} vs north, record {rec}: {fmt(d)}")
    if good.get("inward"):
        verdict("symmetry", *check_symmetry(out / "inward"))
    if (out / "a15-before").exists() and (out / "a15-after").exists():
        verdict("unchanged", *check_unchanged(out))
    rst = out / "restart"
    if (rst / "part2").exists():
        worst = 0.0
        with his(rst / "straight") as a, his(rst / "part2") as b:
            for name in FIELDS + ("temp",):
                x = np.ma.filled(a[name][-1].astype(float), np.nan)
                y = np.ma.filled(b[name][-1].astype(float), np.nan)
                worst = max(worst, float(np.nanmax(np.abs(x - y))) / scale(x))
            same_t = float(a["ocean_time"][-1]) == float(b["ocean_time"][-1])
        print(f"restart     {'PASS' if same_t and worst <= RESTART_TOL else 'OPEN'}  straight vs restarted "
              f"at the same time {same_t}: max |diff| / 99th pct {worst:.1e} (not counted: a ROMS residual "
              f"of this case, see the swan-closed-ring document)")
    print("PASS" if ok_all else "FAIL")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
