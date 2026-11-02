"""Particle positions in the periodic channel against the exact answer.

    python -I check.py HYDRO.nc OUT.nc            prints the largest error per output time
    python -I check.py --summary HYDRO.nc OUT.nc  prints one line: errors at 1 h and 2 h

The flow is uniform and runs along xi: u = U0 + dU * record, with record r at
r * dt. Between records ROMSPath interpolates in time, so a particle released at
t = 0 has moved s(t) = U0 t + dU t^2 / (2 dt) along xi. The error is the
distance along xi between ROMSPath's position and xi0 + s(t), taken modulo the
channel's period (a particle that crossed the seam is compared with the exact
position after the same crossings), and the distance across (along eta), which
should stay zero. Needs numpy and netCDF4.
"""
import sys

import numpy as np
from netCDF4 import Dataset


def errors(hydro, out):
    """Times (s), along-channel and across-channel errors (time, particle), status."""
    with Dataset(hydro) as h:
        th = np.deg2rad(h.rotation_deg)
        period = float(h.period_m)
        u = h["u"][:, 0, 0, 0].astype(float)
        dt = float(h["ocean_time"][1] - h["ocean_time"][0])
    u0, du = u[0], u[1] - u[0]
    with Dataset(out) as o:
        o.set_auto_mask(False)
        t = o["model_time"][:].astype(float)
        x = o["lon"][:].astype(float)
        y = o["lat"][:].astype(float)
        status = o["status"][:]
    along = np.cos(th) * x + np.sin(th) * y
    across = -np.sin(th) * x + np.cos(th) * y
    s = u0 * t + du * t ** 2 / (2 * dt)
    exact = along[0] + s[:, None]
    e_along = (along - exact + period / 2) % period - period / 2
    e_across = across - across[0]
    return t, e_along, e_across, status


def main(args):
    summary = args[0] == "--summary"
    hydro, out = args[1:] if summary else args
    t, ea, ec, status = errors(hydro, out)
    worst = np.maximum(np.abs(ea), np.abs(ec)).max(axis=1)
    signed = ea[np.arange(len(t)), np.abs(ea).argmax(axis=1)]
    if summary:
        k1, k2 = np.argmin(abs(t - 3600)), np.argmin(abs(t - 7200))
        print(f"{signed[k1]:+10.4f} {signed[k2]:+10.4f} {worst.max():10.4f}")
        return
    print(f"{'time (s)':>8} {'along (m)':>10} {'largest |error| (m)':>20}")
    for k in range(len(t)):
        print(f"{t[k]:8.0f} {signed[k]:+10.4f} {worst[k]:20.4f}")
    print(f"particles: {ea.shape[1]}; status values at the end: {sorted(set(status[-1].tolist()))}")


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    main(sys.argv[1:])
