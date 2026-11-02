"""Compare the examples sweep's runs: stock vs patched, patched vs engine.

    python -I tests/examples/compare.py RUNS MANIFEST [NAME ...]

RUNS holds NAME/VARIANT/ folders written by example_inside.sh (image_info.txt
and output/). Prints a Markdown report: each run's outcome, then for both
pairs whether every output file is bit-identical, and if not the largest
relative difference (largest |A - B| of a variable over the largest |A|) and
the variables that differ most. The summary column shows the main fields
(MAIN), since a variable that is nearly zero everywhere (v in a 2-D slice)
has a large relative difference that means nothing.

Compared: NetCDF files (every variable in both; values >= 1e30, land and
fill, left out of the maximums), SWAN .mat files (every array), and text
output (SWAN tables and spectra: numbers token by token, scaled by the
largest number in the file). Wave directions (Dwave, Dwavep, Dir) differ
modulo 360. Left out: SWAN's
PRINT files, Errfile, norm_end and swaninit (run logs). Needs numpy, scipy
and netCDF4.
"""
import os
import re
import sys

import numpy as np

# Pairs compared; environment PAIRS="A:B C:D" replaces them (e.g. consecutive
# upto-<patch> builds, to find the patch behind a change).
PAIRS = ([tuple(p.split(":")) for p in os.environ["PAIRS"].split()] if os.environ.get("PAIRS")
         else [("stock", "patched"), ("patched", "engine")])
SKIP = re.compile(r"^(PRINT.*|Errfile.*|ERRFILE.*|norm_end|swaninit|\.start)$")
# Main fields, for the summary column: sea level, currents, temperature and
# salinity, wave height (ROMS names; SWAN .mat arrays Hsig_<time>).
MAIN = re.compile(r"^(zeta|ubar|vbar|u|v|temp|salt|Hwave|Hsig|Hsig_.*)$")
# Wave directions (degrees): 0 and 360 are the same direction.
DIRECTION = re.compile(r"^(Dwave|Dwavep|Dir|Dir_.*)$")
NUM = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eEdD][-+]?\d+)?")


def info(run):
    """Fields of image_info.txt (outcome, exit, wall_s) and the layout line."""
    out = {"outcome": "not run"}
    p = os.path.join(run, "image_info.txt")
    if os.path.exists(p):
        for line in open(p):
            k, _, v = line.strip().partition(" ")
            if k in ("outcome", "exit", "wall_s", "example"):
                out[k] = v
    return out


def arrays_nc(path):
    from netCDF4 import Dataset
    d = Dataset(path)
    d.set_auto_mask(False)
    out = {}
    for n, v in d.variables.items():
        a = v[...]
        if a.dtype.kind in "fiu":
            out[n] = np.asarray(a, dtype=np.float64)
        else:
            out[n] = np.asarray(a)
    d.close()
    return out


def arrays_mat(path):
    from scipy.io import loadmat
    m = loadmat(path)
    return {k: np.asarray(v, dtype=np.float64) for k, v in m.items() if not k.startswith("__")}


def arrays_text(path):
    """Numbers of a text file, one array per line; None if not text."""
    try:
        lines = open(path, encoding="ascii").read().splitlines()
    except (UnicodeDecodeError, ValueError):
        return None
    out = {}
    for i, line in enumerate(lines):
        nums = NUM.findall(line)
        words = NUM.sub("#", line).split()
        key = f"line {i + 1}: {' '.join(words)[:40]}"
        out[key] = np.array([float(x.replace("d", "e").replace("D", "e")) for x in nums])
    return out


def load(path):
    if path.endswith(".nc"):
        return arrays_nc(path)
    if path.endswith(".mat"):
        return arrays_mat(path)
    return arrays_text(path)


def compare_arrays(a, b):
    """Rows (name, max|A-B|, max|A|) of differing arrays, and notes."""
    rows, notes = [], []
    for n in a:
        if n not in b:
            notes.append(f"{n} only in A")
            continue
        x, y = a[n], b[n]
        if x.shape != y.shape:
            notes.append(f"{n}: shapes {x.shape} vs {y.shape}")
            continue
        if x.dtype.kind not in "f":
            if not np.array_equal(x, y):
                notes.append(f"{n}: differs (non-numeric)")
            continue
        if np.array_equal(x, y, equal_nan=True):
            continue
        ok = (np.abs(x) < 1e30) & (np.abs(y) < 1e30) & np.isfinite(x) & np.isfinite(y)
        nanmismatch = int(np.sum(np.isnan(x) != np.isnan(y)))
        if nanmismatch:
            notes.append(f"{n}: {nanmismatch} points NaN in one only")
        d = np.abs(x[ok] - y[ok])
        if DIRECTION.match(n):
            d = np.minimum(d % 360, 360 - d % 360)
        diff = float(np.max(d)) if ok.any() else 0.0
        big = float(np.max(np.abs(x[ok]))) if ok.any() else 0.0
        if diff > 0 or not nanmismatch:
            rows.append((n, diff, big))
    notes += [f"{n} only in B" for n in b if n not in a]
    return rows, notes


def compare_runs(ra, rb):
    """Per-file results between two runs' output folders."""
    fa = set(os.listdir(os.path.join(ra, "output"))) if os.path.isdir(os.path.join(ra, "output")) else set()
    fb = set(os.listdir(os.path.join(rb, "output"))) if os.path.isdir(os.path.join(rb, "output")) else set()
    res = {}
    for f in sorted(fa | fb):
        if SKIP.match(f):
            continue
        if f not in fb or f not in fa:
            res[f] = ("only in " + ("A" if f in fa else "B"), [], [])
            continue
        pa, pb = os.path.join(ra, "output", f), os.path.join(rb, "output", f)
        if open(pa, "rb").read() == open(pb, "rb").read():
            res[f] = ("identical", [], [])
            continue
        try:
            a, b = load(pa), load(pb)
        except Exception as e:  # unreadable file: report, do not stop
            res[f] = (f"unreadable ({type(e).__name__})", [], [])
            continue
        if a is None or b is None:
            res[f] = ("differs (binary)", [], [])
            continue
        rows, notes = compare_arrays(a, b)
        if not (f.endswith(".nc") or f.endswith(".mat")):
            # Text: one array per line, so scale each line by the largest
            # number in the whole file, not on that line (often 0).
            big = max((float(np.max(np.abs(v))) for v in a.values() if v.size), default=0.0)
            rows = [(n, d, big) for n, d, _ in rows]
        res[f] = ("identical" if not rows and not notes else "differs", rows, notes)
    return res


def rel(row):
    _, d, big = row
    return d / big if big > 0 else (0.0 if d == 0 else float("inf"))


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    runs, manifest, names = argv[0], argv[1], argv[2:]
    rows = [l.rstrip("\n").split("\t") for l in open(manifest) if l.strip() and not l.startswith("#")]
    order = [r[0] for r in rows]
    names = names or order
    variants = sorted({v for n in names if os.path.isdir(os.path.join(runs, n))
                       for v in os.listdir(os.path.join(runs, n))},
                      key=lambda v: (["stock", "patched", "engine"].index(v) if v in ("stock", "patched", "engine") else 9, v))

    print("## Outcomes\n")
    print("| Example | " + " | ".join(variants) + " | wall time, s (" + " / ".join(variants) + ") |")
    print("|---|" + "---|" * len(variants) + "---|")
    for n in names:
        inf = [info(os.path.join(runs, n, v)) for v in variants]
        print(f"| {n} | " + " | ".join(i["outcome"] for i in inf) + " | "
              + " / ".join(i.get("wall_s", "-") for i in inf) + " |")

    details = []
    for va, vb in PAIRS:
        if va not in variants or vb not in variants:
            continue
        print(f"\n## {va} vs {vb}\n")
        print("| Example | Output files | Result | Main fields: largest relative difference | In | Any variable | In |")
        print("|---|---|---|---|---|---|---|")
        for n in names:
            ra, rb = os.path.join(runs, n, va), os.path.join(runs, n, vb)
            if info(ra)["outcome"] == "not run" or info(rb)["outcome"] == "not run":
                print(f"| {n} | | not run | | |")
                continue
            res = compare_runs(ra, rb)
            nd = [f for f, r in res.items() if r[0] != "identical"]
            allrows = [(f, r) for f, (_, rs, _) in res.items() for r in rs]
            if not res:
                verdict = "no output"
            elif not nd:
                verdict = "**identical**"
            else:
                verdict = f"differs ({len(nd)} of {len(res)} files)"
            cells = []
            for sel in ([fr for fr in allrows if MAIN.match(fr[1][0])], allrows):
                if sel:
                    f, r = max(sel, key=lambda fr: rel(fr[1]))
                    cells += [f"{rel(r):.1e} ({r[0]})", f]
                else:
                    cells += ["", ""]
            print(f"| {n} | {len(res)} | {verdict} | " + " | ".join(cells) + " |")
            if nd:
                lines = [f"### {n}: {va} vs {vb}\n"]
                for f in nd:
                    status, rs, notes = res[f]
                    lines.append(f"- `{f}`: {status}")
                    for r in sorted(rs, key=rel, reverse=True)[:6]:
                        lines.append(f"  - {r[0]}: max |A-B| {r[1]:.3g}, max |A| {r[2]:.3g}, relative {rel(r):.1e}")
                    if len(rs) > 6:
                        lines.append(f"  - ... {len(rs) - 6} more")
                    for t in notes[:6]:
                        lines.append(f"  - {t}")
                details.append("\n".join(lines))
    if details:
        print("\n## Details\n")
        print("\n\n".join(details))


if __name__ == "__main__":
    main(sys.argv[1:])
