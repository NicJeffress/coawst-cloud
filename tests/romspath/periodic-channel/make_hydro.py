"""Synthetic ROMS-style hydro file for checking particle trackers.

A channel periodic in xi (like a ROMS EW_PERIODIC grid: Lm interior columns plus
the two ghost columns i = 0 = Lm and i = Lm + 1 = 1), uniform depth, uniform
eastward flow that changes from record to record: u = U0 + dU * record. A
particle's exact position is then known (x0 + U0 t + dU t^2 / (2 dt)), so the
tracker's record timing and its seam crossings can be checked directly.

With --angle the grid is rotated by that many degrees (x_rho, y_rho and angle),
so grid lines no longer run along x and y; the flow still runs along xi.

Usage: make_hydro.py OUT.nc [--lm 40] [--mm 10] [--n 4] [--dx 10]
           [--records 13] [--dt 600] [--u0 0.05] [--du 0.01] [--angle 0]
"""
import argparse

import netCDF4 as nc
import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("--lm", type=int, default=40)
    ap.add_argument("--mm", type=int, default=10)
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--dx", type=float, default=10.0)
    ap.add_argument("--depth", type=float, default=10.0)
    ap.add_argument("--records", type=int, default=13)
    ap.add_argument("--dt", type=float, default=600.0)
    ap.add_argument("--u0", type=float, default=0.05)
    ap.add_argument("--du", type=float, default=0.01)
    ap.add_argument("--angle", type=float, default=0.0, help="grid rotation (degrees, anticlockwise)")
    a = ap.parse_args()
    L, M, N = a.lm + 2, a.mm + 2, a.n
    i = np.arange(L)
    j = np.arange(M)
    x = (i - 0.5) * a.dx
    y = (j - 0.5) * a.dx
    X, Y = np.meshgrid(x, y)
    th = np.deg2rad(a.angle)
    X, Y = np.cos(th) * X - np.sin(th) * Y, np.sin(th) * X + np.cos(th) * Y
    hc = 1.0
    s_w = np.linspace(-1, 0, N + 1)
    s_r = 0.5 * (s_w[1:] + s_w[:-1])
    with nc.Dataset(a.out, "w") as d:
        for name, n in (("xi_rho", L), ("eta_rho", M), ("xi_u", L - 1), ("eta_u", M), ("xi_v", L),
                        ("eta_v", M - 1), ("s_rho", N), ("s_w", N + 1), ("ocean_time", None)):
            d.createDimension(name, n)

        def var(name, dims, val, dtype="f8", **att):
            v = d.createVariable(name, dtype, dims)
            v[:] = val
            for k, s in att.items():
                v.setncattr(k, s)
            return v
        var("Vtransform", (), 2, "i4")
        var("Vstretching", (), 1, "i4")
        var("theta_s", (), 0.0)
        var("theta_b", (), 0.0)
        var("hc", (), hc)
        var("spherical", (), 0, "i4")
        var("s_rho", ("s_rho",), s_r)
        var("s_w", ("s_w",), s_w)
        var("Cs_r", ("s_rho",), s_r)
        var("Cs_w", ("s_w",), s_w)
        r2 = ("eta_rho", "xi_rho")
        var("x_rho", r2, X)
        var("y_rho", r2, Y)
        var("h", r2, np.full((M, L), a.depth))
        var("pm", r2, np.full((M, L), 1 / a.dx))
        var("pn", r2, np.full((M, L), 1 / a.dx))
        var("angle", r2, np.full((M, L), th))
        var("mask_rho", r2, np.ones((M, L)))
        var("mask_u", ("eta_u", "xi_u"), np.ones((M, L - 1)))
        var("mask_v", ("eta_v", "xi_v"), np.ones((M - 1, L)))
        t = var("ocean_time", ("ocean_time",), a.dt * np.arange(a.records), units="seconds since 2000-01-01 00:00:00")
        del t
        R = a.records
        U = (a.u0 + a.du * np.arange(R))[:, None, None, None] * np.ones((R, N, M, L - 1))
        var("zeta", ("ocean_time",) + r2, np.zeros((R, M, L)))
        var("u", ("ocean_time", "s_rho", "eta_u", "xi_u"), U)
        var("v", ("ocean_time", "s_rho", "eta_v", "xi_v"), np.zeros((R, N, M - 1, L)))
        var("w", ("ocean_time", "s_w") + r2, np.zeros((R, N + 1, M, L)))
        var("AKs", ("ocean_time", "s_w") + r2, np.full((R, N + 1, M, L), 1e-4))
        var("salt", ("ocean_time", "s_rho") + r2, np.full((R, N, M, L), 35.0))
        var("temp", ("ocean_time", "s_rho") + r2, np.full((R, N, M, L), 20.0))
        var("u_stokes", ("ocean_time", "s_rho", "eta_u", "xi_u"), np.zeros((R, N, M, L - 1)))
        var("v_stokes", ("ocean_time", "s_rho", "eta_v", "xi_v"), np.zeros((R, N, M - 1, L)))
        d.period_m = a.lm * a.dx
        d.rotation_deg = a.angle
    print(f"wrote {a.out}: period {a.lm * a.dx:g} m, u = {a.u0} + {a.du} * record, dt {a.dt:g} s")


if __name__ == "__main__":
    main()
