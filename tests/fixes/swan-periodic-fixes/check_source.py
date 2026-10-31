"""Source checks for 1-fixes/swan-periodic-fixes.patch (items 12 and 15).

    python -I check_source.py SWAN_SRC_DIR

Item 12: SWAN cuts its grid into x-strips when it has more points in x than
in y (MXC > MYC, MXCGL > MYCGL). Its halo exchange never wraps around in x,
so with a periodic (REPEATING) grid every such test must also require a
non-periodic grid (KREPTX = 0).
Item 15 (waves_coupler.ftn, WAV2OCN_COUPLING): the spectral Stokes fields
(KSS, USS, VSS) must be taken from the same grid points as the ordinary wave
fields, i.e. through the index map isrc built with them, not points().
Exit 1 if a check fails.
"""
import re
import sys
from pathlib import Path

d = Path(sys.argv[1])
ok = True
strip_tests, bad = 0, []
for f in sorted(d.glob("*.ftn")) + sorted(d.glob("*.ftn90")):
    for n, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
        # code switched on by SWAN's build (switch.pl) keeps prefixes such as !WFR!MPI
        code = re.sub(r"^(![A-Z]{3})+", "", line).split("!")[0]
        for m in re.finditer(r"MXC(GL)?\s*\.GT\.\s*MYC(GL)?", code, re.I):
            strip_tests += 1
            if not re.search(r"KREPTX\s*\.EQ\.\s*0", code, re.I):
                bad.append(f"{f.name}:{n}")
good = strip_tests > 0 and not bad
ok &= good
print(f"item 12  x-strip tests (MXC > MYC): {strip_tests}, without KREPTX.EQ.0: {len(bad)}"
      f"{' (' + ', '.join(bad[:4]) + (', ...' if len(bad) > 4 else '') + ')' if bad else ''}  {'ok' if good else 'BAD'}")

cpl = (d / "waves_coupler.ftn").read_text()
spec = re.findall(r"avdata\(IP\)\s*=\s*REAL\(\s*(KSS|USS|VSS)\((\w+)\(IP\)", cpl)
uses = sorted({idx for _, idx in spec})
good = bool(spec) and uses == ["isrc"]
ok &= good
print(f"item 15  spectral Stokes fields KSS/USS/VSS taken through: {uses}  {'ok' if good else 'BAD'}")
print("CONSISTENT" if ok else "INCONSISTENT")
sys.exit(0 if ok else 1)
