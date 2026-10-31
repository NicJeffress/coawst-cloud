"""River (face source) file for the restart test on Reef_Ideal_A15.

    python -I make_river.py CASE_DIR OUT.nc [TRANSPORT_PER_FACE]

Three v-faces on the land wall at the south of the lagoon (ROMS j = 1, between
the land row 0 and the first water row; i = 60, 61, 62), each carrying
TRANSPORT_PER_FACE m3/s (default 5) northwards into the 10 m deep lagoon,
constant in time, all of it in the top 1 m of the water column (Vshape from
the case's own vertical coordinate: Vtransform 2, Vstretching 4, THETA_S,
THETA_B, TCLINE and N read from ocean.in). Temperature and salinity of the
river water are written too (25 C, 0), for cases that use them.
Use with LuvSrc == T in ocean.in (SSFNAME is already ocean_rivers.nc).
"""
import re
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

case, out = Path(sys.argv[1]), sys.argv[2]
q = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0
ocean = (case / "ocean.in").read_text()


def val(key):
    return float(re.search(rf"^\s*{key}\s*==\s*([0-9.eEdD+-]+)", ocean, re.M).group(1).replace("d", "e").replace("D", "e"))


n, ts, tb, hc = int(val("N")), val("THETA_S"), val("THETA_B"), val("TCLINE")
assert int(val("Vtransform")) == 2 and int(val("Vstretching")) == 4
g = Dataset(case / "roms_grid_default_1.nc")
mask_v, h = g["mask_v"][:], g["h"][:]
faces = [60, 61, 62]
for i in faces:
    assert mask_v[0, i] == 0 and g["mask_rho"][1, i] == 1, "the faces must be on the land wall"
# s-coordinate (ROMS Vstretching 4) at w levels, depth of the w levels below the surface
sw = np.linspace(-1.0, 0.0, n + 1)
c = (1.0 - np.cosh(ts * sw)) / (np.cosh(ts) - 1.0)
c = (np.exp(tb * c) - 1.0) / (1.0 - np.exp(-tb))
hh = float(h[1, faces[0]])
zw = hh * (hc * sw + hh * c) / (hc + hh)            # zeta = 0
top = zw[1:] > -1.0                                  # layers whose bottom is above 1 m depth ...
top[np.argmax(zw[1:] > -1.0)] = True                 # ... plus the one that contains 1 m
thick = np.diff(zw) * top
vshape = thick / thick.sum()
with Dataset(out, "w") as d:
    d.createDimension("river", len(faces))
    d.createDimension("s_rho", n)
    d.createDimension("river_time", 2)
    d.createVariable("river", "f8", ("river",))[:] = np.arange(1, len(faces) + 1)
    d.createVariable("river_Xposition", "f8", ("river",))[:] = faces
    d.createVariable("river_Eposition", "f8", ("river",))[:] = [1] * len(faces)
    v = d.createVariable("river_direction", "f8", ("river",))
    v[:] = [1] * len(faces)
    v.long_name = "river runoff direction: 1 = v-face (north-south)"
    v = d.createVariable("river_Vshape", "f8", ("s_rho", "river"))
    v[:] = np.repeat(vshape[:, None], len(faces), axis=1)
    v = d.createVariable("river_time", "f8", ("river_time",))
    v[:] = [0.0, 3650.0]
    v.units = "days since 0001-01-01 00:00:00"   # A15's clock starts at year 1 (no TIME_REF)
    v = d.createVariable("river_transport", "f8", ("river_time", "river"))
    v[:] = q
    v.units = "meter3 second-1"
    d.createVariable("river_temp", "f8", ("river_time", "s_rho", "river"))[:] = 25.0
    d.createVariable("river_salt", "f8", ("river_time", "s_rho", "river"))[:] = 0.0
    d.title = "Reef_Ideal_A15 test river: 3 v-faces at the south wall, top 1 m"
print(f"wrote {out}: faces i = {faces}, j = 1, {q} m3/s each, Vshape {np.round(vshape, 3).tolist()}, "
      f"layer bottoms {np.round(zw[:-1], 2).tolist()} m")
