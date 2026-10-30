"""Check that the u and v spectral Stokes drift loops of wec_stokes.F agree.

    python -I check_source.py PATH/TO/wec_stokes.F

The spectral Stokes drift (SPECTRUM_STOKES) has a u-point loop and a v-point
loop that must be mirror images: u-point averages over (i-1,j) and (i,j), v-point
averages over (i,j-1) and (i,j), and both add frequency bins while kD < kD2deep.
Prints what each loop does and exits 1 if they disagree.
"""
import re
import sys

text = open(sys.argv[1]).read().splitlines()


def block(start_pat, end_pat):
    """Lines of the loop that sums the spectrum into sdrx or sdry."""
    i0 = next(i for i, l in enumerate(text) if re.search(start_pat, l))
    i1 = next(i for i in range(i0, len(text)) if re.search(end_pat, text[i]))
    lo = max(i for i in range(i0) if re.match(r"\s*DO j=", text[i]))
    return [l.split("!")[0] for l in text[lo:i1 + 1]]


u = block(r"sdrx\s*=\s*0", r"u_stokes\(i,j,k\)\s*=\s*sdrx")
v = block(r"sdry\s*=\s*0", r"v_stokes\(i,j,k\)\s*=\s*sdry")
ok = True

# 1. Neighbour of every two-point average of a spectral field
for name, lines, good, bad in (("u", u, "i-1,j", "i,j-1"), ("v", v, "i,j-1", "i-1,j")):
    avgs = [l.strip() for l in lines if re.search(r"spec_(wn|us|vs)\(", l)]
    wrong = [a for a in avgs if bad.replace(" ", "") in a.replace(" ", "")]
    print(f"{name}-point loop: {len(avgs)} spectral averages, {len(wrong)} use the {bad} neighbour")
    for a in wrong:
        print(f"    {a}")
    ok &= not wrong

# 2. Frequency-bin limit of the DO WHILE loops
lim = {}
for name, lines in (("u", u), ("v", v)):
    joined = " ".join(l.strip().rstrip("&") for l in lines)
    m = re.search(r"DO WHILE.*?\(cff2\.lt\.(\w+)\)", joined)
    lim[name] = m.group(1) if m else None
    print(f"{name}-point loop adds bins while cff2 < {lim[name]}")
ok &= lim["u"] == lim["v"] == "kD2deep"

# 3. The unused cff5 of the u loop (one extra SINH per bin)
c5 = [l.strip() for l in u if re.match(r"\s*cff5\s*=", l)]
print(f"u-point loop computes cff5: {'yes' if c5 else 'no'}")
ok &= not c5

print("CONSISTENT" if ok else "INCONSISTENT")
sys.exit(0 if ok else 1)
