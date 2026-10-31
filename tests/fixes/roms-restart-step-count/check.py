"""Checks of 1-fixes/roms-restart-step-count.patch.

    python -I check.py OUTDIR

OUTDIR/<variant>-<side>/{straight,part1,part2} from run.sh (restart_inside.sh):
variant normal (Reef_Ideal_A15 as it is, DSTART 0, start time 0) or far
(DSTART -730119 days: the start time 730119 days after DSTART, as for an
initial file dated 2000-01-01 with DSTART 0), side before or after the patch.

Checks:
  bug        far-before: the restarted run does not continue the straight
             one (ROMS's step counter overflowed to garbage)
  stops      far-after: the restarted run stops at once with the message
             "GET_STATE - perfect restart: the step number ..."
  warns      far-after: the fresh runs print "GET_STATE - warning" and are
             bit-identical to normal-after's (except the stored dstart);
             normal-after prints no warning
  exact      normal-before and normal-after restart exactly (< 1e-8 m/s)
  unchanged  normal: before = after, bit for bit (ROMS history, SWAN Hs)
"""
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

out = Path(sys.argv[1])
ok = True
VEL = ("ubar", "vbar", "u", "v")
MSG = "GET_STATE - perfect restart: the step number"


def verdict(name, good, text):
    global ok
    ok &= bool(good)
    print(f"{name:10s} {'PASS' if good else 'FAIL'}  {text}")


def his(run):
    return Dataset(run / "output/ocean_his.nc")


def restart_diff(base):
    with his(base / "straight") as s, his(base / "part2") as p:
        if float(s["ocean_time"][-1]) != float(p["ocean_time"][-1]):
            return None
        return max(float(np.nanmax(np.abs(np.ma.filled(s[v][-1], np.nan).astype(float)
                                         - np.ma.filled(p[v][-1], np.nan).astype(float)))) for v in VEL)


def identical(a, b):
    """Every variable of the ROMS history and SWAN's Hs bit-identical."""
    bad = []
    for f in ("ocean_his.nc", "hsign.nc"):
        with Dataset(a / "output" / f) as x, Dataset(b / "output" / f) as y:
            for v in x.variables:
                if v in y.variables and x[v].dtype.kind in "fiu":
                    if not np.array_equal(np.ma.filled(x[v][:], np.nan), np.ma.filled(y[v][:], np.nan), equal_nan=True):
                        bad.append(f"{f}:{v}")
    return bad


def times(run):
    with his(run) as h:
        return [float(t) for t in h["ocean_time"][:]]


d = restart_diff(out / "far-before")
verdict("bug", d is None or d > 1e-8,
        f"far-before: output times straight {times(out / 'far-before/straight')}, restarted "
        f"{times(out / 'far-before/part2')} s; "
        f"{'no common last record' if d is None else f'restarted vs straight {d:.1e} m/s'}")

log = (out / "far-after/part2/log.txt").read_text(errors="replace")
try:
    with his(out / "far-after/part2") as p:
        nrec = len(p["ocean_time"])
except (FileNotFoundError, OSError):
    nrec = 0
msg = [ln.strip() for ln in log.splitlines() if "GET_STATE - perfect restart" in ln or "(time - DSTART)" in ln]
verdict("stops", MSG in log and nrec == 0, f"far-after part2: message {'found' if MSG in log else 'missing'}, "
        f"history records {nrec}; {' | '.join(msg[:2])}")

for side in ("before", "after"):
    d = restart_diff(out / f"normal-{side}")
    verdict("exact", d is not None and d < 1e-8, f"normal-{side}: restarted vs straight {d:.1e} m/s" if d is not None
            else f"normal-{side}: no common last record")

flog = (out / "far-after/straight/log.txt").read_text(errors="replace")
nlog = (out / "normal-after/straight/log.txt").read_text(errors="replace")
fresh = {r: [b for b in identical(out / "far-after" / r, out / "normal-after" / r) if not b.endswith(":dstart")]
         for r in ("straight", "part1")}
verdict("warns", "GET_STATE - warning" in flog and "GET_STATE - warning" not in nlog and not any(fresh.values()),
        f"far-after warning {'printed' if 'GET_STATE - warning' in flog else 'missing'}, normal-after "
        f"{'none' if 'GET_STATE - warning' not in nlog else 'PRINTED'}; far = normal fresh runs: "
        + ", ".join(f"{r} {'yes' if not b else 'NO ' + str(b[:3])}" for r, b in fresh.items()))

bad = {r: identical(out / "normal-before" / r, out / "normal-after" / r) for r in ("straight", "part1", "part2")}
verdict("unchanged", not any(bad.values()),
        "normal before = after, bit for bit: " + ", ".join(f"{k} {'yes' if not b else 'NO ' + str(b[:3])}" for k, b in bad.items()))
print("ALL OK" if ok else "SOME CHECKS BAD")
sys.exit(0 if ok else 1)
