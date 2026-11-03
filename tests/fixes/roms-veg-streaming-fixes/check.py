"""Checks for roms-veg-streaming-fixes (see run.sh).

    python -I check.py OUTDIR

OUTDIR/stream-<side>: history at step 110 (ocean_his.nc, last record 660 s) and the
momentum diagnostics of step 111 alone (ocean_dia.nc, last record; the Adams-Bashforth mix of steps
109-111, all with the wave fields of the 600 s exchange); side = before or after
the patch. The streaming force is computed from the state and wave fields of the history record, so its depth integral at u-points must be

    0.5 [B(i) + B(i-1)],   B = (Dissip_fric + Dissip_veg)/rho0 * k cos(theta)/sigma,

k = 2 pi / max(Lwave, 1), theta = 1.5 pi - Dwave (Dwave in radians; the history file has degrees; angle 0), sigma = min(sqrt(g k tanh(k D)), 2),
D = h + zeta: what wec_streaming.F and vegetation_stream.F compute, with the bottom part spread
over the wave boundary layer and the canopy part over the canopy, each integrating to its total.
The diagnostic u_bstm is per unit mass (m/s2) in each layer; times the layer thickness Hz (from
zeta, h and the s-coordinate in the history file, Vtransform 2) and summed, it is that integral.
OUTDIR/plain-<side>: 10 min without streaming; their histories must be identical.
"""
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

out = Path(sys.argv[1])
G, RHO0 = 9.81, None


def last(ds, v):
    x = np.ma.filled(ds[v][-1], 0.0).astype(float)
    x[np.abs(x) > 1e30] = 0.0          # the land row is written as the fill value 1e37
    return x


def misfit(side):
    global RHO0
    d = out / f"stream-{side}" / "output"
    with Dataset(d / "ocean_his.nc") as h, Dataset(d / "ocean_dia.nc") as a:
        assert abs(float(h["ocean_time"][-1]) - 660.0) < 1e-6, h["ocean_time"][:]
        assert abs(float(a["ocean_time"][-1]) - 666.0) < 1e-6, a["ocean_time"][:]
        RHO0 = float(h["rho0"][:])
        hh = np.ma.filled(h["h"][:], 0.0).astype(float)
        zeta = last(h, "zeta")
        hc, s_w, Cs_w = float(h["hc"][:]), np.asarray(h["s_w"][:], float), np.asarray(h["Cs_w"][:], float)
        assert int(h["Vtransform"][:]) == 2
        S = (hc * s_w[:, None, None] + hh[None] * Cs_w[:, None, None]) / (hc + hh[None])
        z_w = zeta[None] + (zeta[None] + hh[None]) * S
        Hz = np.diff(z_w, axis=0)
        Hz_u = 0.5 * (Hz[:, :, 1:] + Hz[:, :, :-1])
        # dissipation in W/m2 in the history file (scale rho0); ROMS uses W/m2 / rho0
        Ef, Ev = last(h, "Dissip_fric"), last(h, "Dissip_veg")
        print(f"   {side:6s}: largest Dissip_fric {Ef.max():.1f} W/m2, Dissip_veg {Ev.max():.1f} W/m2")
        E = (Ef + Ev) / RHO0
        k = 2 * np.pi / np.maximum(last(h, "Lwave"), 1.0)
        th = 1.5 * np.pi - np.deg2rad(last(h, "Dwave"))    # written in degrees, used in radians
        D = hh + zeta
        sigma = np.minimum(np.sqrt(G * k * np.tanh(k * D)), 2.0)
        B = E * k * np.cos(th) / sigma
        expect = 0.5 * (B[:, 1:] + B[:, :-1])
        got = (last(a, "u_bstm") * Hz_u).sum(axis=0)
        mask = np.ma.filled(h["mask_u"][:], 1.0) > 0
    # interior u-points away from the periodic seam and the closed/open edges
    sl = (slice(2, -2), slice(2, -2))
    e, g, m = expect[sl], got[sl], mask[sl]
    w = m & (np.abs(e) > 0.01 * np.abs(e[m]).max())
    rms = np.sqrt(np.mean((g[w] - e[w]) ** 2)) / np.sqrt(np.mean(e[w] ** 2))
    ratio = np.sum(g[w] * e[w]) / np.sum(e[w] ** 2)
    print(f"   {side:6s}: {w.sum()} wave points, depth-integrated streaming force / "
          f"(Dissip_fric + Dissip_veg) k cos/sigma = {ratio:.3f} (least squares), rms misfit {rms:.1e}")
    return rms


ok = True
res = {}
for side in ("before", "after"):
    try:
        res[side] = misfit(side)
    except (FileNotFoundError, OSError, KeyError, IndexError, AssertionError) as exc:
        print(f"   {side}: missing or incomplete output ({exc!r})")
good = res.get("before", 0) > 0.1
ok &= good
print(f"   bug       before: rms misfit {res.get('before', float('nan')):.1e}    {'PASS' if good else 'FAIL'}")
good = res.get("after", 1) < 0.01
ok &= good
print(f"   fixed     after: rms misfit {res.get('after', float('nan')):.1e}    {'PASS' if good else 'FAIL'}")
try:
    with Dataset(out / "plain-before/output/ocean_his.nc") as a, Dataset(out / "plain-after/output/ocean_his.nc") as b:
        good = len(a["ocean_time"]) > 1 and all(
            np.array_equal(np.ma.filled(a[v][:], 0), np.ma.filled(b[v][:], 0))
            for v in a.variables if a[v].dimensions[:1] == ("ocean_time",))
except (FileNotFoundError, OSError):
    good = False
ok &= good
print(f"   unchanged runs without streaming: {'bit-identical' if good else 'different or missing'}    "
      f"{'PASS' if good else 'FAIL'}")


def restart(side):
    """Restart records at 20 min of the straight and restarted runs: None if missing."""
    d = out / f"restart-{side}"
    try:
        with Dataset(d / "straight/output/ocean_rst.nc") as a, Dataset(d / "part2/output/ocean_rst.nc") as b:
            ta, tb = list(np.asarray(a["ocean_time"][:])), list(np.asarray(b["ocean_time"][:]))
            if 1200.0 not in ta or 1200.0 not in tb:
                return None
            i, j = ta.index(1200.0), tb.index(1200.0)
            return max(int((np.ma.filled(a[v][i], 0.0) + 0.0 != np.ma.filled(b[v][j], 0.0) + 0.0).sum())
                       for v in ("u", "v", "ubar", "vbar", "zeta"))
    except (FileNotFoundError, OSError, IndexError, KeyError):
        return None


rb, ra = restart("before"), restart("after")
print(f"   restart   before: {'no complete restart pair (as expected)' if rb is None else f'{rb} points differ'}; "
      f"after: {'missing' if ra is None else f'{ra} points differ'}")
good = rb is None and ra == 0
ok &= good
print(f"   restart   before fails, after bit-identical    {'PASS' if good else 'FAIL'}")
sys.exit(0 if ok else 1)
