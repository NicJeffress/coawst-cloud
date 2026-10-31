"""Inputs for the SWAN halo-exchange test: a long periodic channel.

    python -I make_inputs.py OUT_DIR [MXC]

Standalone SWAN, flat 10 m deep bottom, periodic in x (REPEATING), MXC points
alongshore (default 1100) x 31 cross-shore, 20 m mesh; waves Hs 1 m, Tp 10 s
from 20 deg east of north on the north side; 10 min nonstationary, 60 s steps.
With REPEATING, SWAN cuts the grid into y-strips, so the rows that SWAN
processes exchange (halo rows) are MXC points long: 1100 REALs = 4.4 kB, above
MPI's eager limit (4 kB in OpenMPI's shared-memory transport).
Writes OUT_DIR/swan.in, bathy.bot, output/.
"""
import sys
from pathlib import Path

out = Path(sys.argv[1])
mxc = int(sys.argv[2]) if len(sys.argv) > 2 else 1100
dx, myc = 20.0, 31
xlen, ylen = mxc * dx, (myc - 1) * dx
(out / "output").mkdir(parents=True, exist_ok=True)
with open(out / "bathy.bot", "w") as f:
    for _ in range(myc):
        f.write(" ".join(["10.0"] * (mxc + 1)) + "\n")
(out / "swan.in").write_text(f"""\
PROJECT '' ' '
 'halo exchange test, {mxc} x {myc}'
MODE NONSTATIONARY TWODIMENSIONAL
SET DEPMIN 0.10 INRHOG 1 NAUTICAL
COORDINATES CARTESIAN REPEATING
CGRID REGULAR 0. 0. 0. {xlen:.1f} {ylen:.1f} {mxc} {myc - 1} CIRCLE 36 0.04 1.0 20
INPGRID BOTTOM REGULAR 0. 0. 0. {mxc} {myc - 1} {dx:.1f} {dx:.1f}
READINP BOTTOM 1 'bathy.bot' 3 0 FREE
BOUND SHAPESPEC JONSWAP 3.3 PEAK DSPR DEGREES
BOUNDSPEC SIDE NORTH CONSTANT PAR 1.0 10.0 20.0 4.0
GEN3
OFF QUAD
BREAKING CON 1.0 0.73
PROP BSBT
FRAME 'grid' 0. 0. 0. {xlen - dx:.1f} {ylen:.1f} {mxc - 1} {myc - 1}
BLOCK 'grid' NOHEADER 'output/hsign.nc' LAY 4 HSIGN 1. OUTPUT 20000101.000000 10 MIN
COMPUTE NONSTATIONARY 20000101.000000 60 SEC 20000101.001000
STOP
""")
print(f"wrote {out}: {mxc} x {myc} points, period {xlen:.0f} m")
