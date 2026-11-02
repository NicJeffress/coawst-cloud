"""ROMSPath input for the periodic channel: ROMSPath.data and the particle seeds.

    python -I make_input.py TEMPLATE HYDRO.nc RUNDIR

TEMPLATE is the ROMSPath.data that ships with ROMSPath. The keys below are
replaced, PeriodicBoundary_X/Y are added to the hydroparam group, and RUNDIR
gets ROMSPath.data, seeds.csv (10 particles along the channel at mid-depth, all
released at t = 0) and an empty out/. HYDRO.nc must be named <prefix>00001.nc.
Needs numpy and netCDF4.
"""
import os
import re
import sys

import numpy as np
from netCDF4 import Dataset

NPAR = 10


def keys(prefix):
    return {
        "numpar": NPAR, "days": 2.0 / 24, "iprint": 600, "dt": 600, "idt": 10,
        "stokesprefix": f"'{prefix}'", "turbstd_v_a_prefix": "''", "wavestd_prefix": "''",
        "Process_VA": ".FALSE.", "Process_WA": ".FALSE.",
        "VTurbOn": ".FALSE.", "HTurbOn": ".FALSE.",
        "OpenOceanBoundary": ".FALSE.", "swimslow": 0.0, "swimfast": 0.0, "Hswimspeed": 0.0,
        "mortality": ".FALSE.", "settlementon": ".FALSE.", "holesExist": ".FALSE.",
        "Ngrid": 1, "refine": 1,
        "prefix": f"'{prefix}'", "time_vname": "'ocean_time'", "time_dname": "'ocean_time'",
        "filenum": "00001", "numdigits": 5, "multifile": ".TRUE.",
        "parfile": "'seeds.csv'", "outpath": "'out/'", "NCOutFile": "'channel'", "OutDir": "'out/'",
        "SaltTempOn": ".FALSE.", "SaltTempMean": ".FALSE.", "WriteBottom": ".FALSE.",
        "WriteWaterDepth": ".FALSE.", "seed": 1,
    }


def set_key(text, k, v):
    # a value may continue on following lines that start with a comma (one per grid)
    pat = rf"^(\s*{re.escape(k)}\s*=\s*)(?:'[^']*'|[^\s!]+)(?:[^\n]*\n\s*,[^\n]*)*"
    text, n = re.subn(pat, lambda m: m.group(1) + str(v), text, count=1, flags=re.M | re.I)
    if n != 1:
        raise SystemExit(f"make_input: key {k} not found in the template")
    return text


def main(template, hydro, run):
    text = open(template, encoding="latin-1").read().replace("\r", "")
    stem = os.path.basename(hydro)
    if not stem.endswith("00001.nc"):
        raise SystemExit("make_input: the hydro file must be named <prefix>00001.nc")
    for k, v in keys(stem[:-len("00001.nc")]).items():
        text = set_key(text, k, v)
    text, n = re.subn(r"^(\$hydroparam\n)", r"\1  PeriodicBoundary_X = .TRUE.\n  PeriodicBoundary_Y = .FALSE.\n",
                      text, count=1, flags=re.M)
    if n != 1:
        raise SystemExit("make_input: no $hydroparam group in the template")
    os.makedirs(os.path.join(run, "out"), exist_ok=True)
    open(os.path.join(run, "ROMSPath.data"), "w").write(text)
    with Dataset(hydro) as d:
        th = np.deg2rad(d.rotation_deg)
        dx = 1 / float(d["pm"][0, 0])
        L = len(d.dimensions["xi_rho"])
        M = len(d.dimensions["eta_rho"])
        depth = float(d["h"][0, 0])
    # grid coordinates (along xi, along eta) in metres: rho point i sits at (i - 0.5) dx
    xi = np.linspace(2.3, L - 3.3, NPAR) * dx
    eta = np.full(NPAR, (M / 2 - 0.3) * dx)
    x = np.cos(th) * xi - np.sin(th) * eta
    y = np.sin(th) * xi + np.cos(th) * eta
    seeds = np.c_[x, y, np.full(NPAR, -depth / 2), np.zeros(NPAR)]
    np.savetxt(os.path.join(run, "seeds.csv"), seeds, fmt="%.6f", delimiter=",")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
