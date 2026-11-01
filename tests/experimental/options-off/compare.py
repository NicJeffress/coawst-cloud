"""Compare two folders of preprocessed Fortran (options-off test).

    python -I compare.py DIR_WITHOUT DIR_WITH

Files must be the same, except for two kinds of line that cannot change what
is computed:
  - comment lines (starting with "!") present on one side only;
  - lines that differ only in integer literals and contain "MyFile": ROMS
    passes __LINE__ with MyFile to its timers and error messages
    (wclock_on/off, FoundError), and the patches shift line numbers.
Prints each file with such differences and how many lines of each kind;
exit status 1 if any other difference is found.
"""
import difflib
import re
import sys
from pathlib import Path

a, b = Path(sys.argv[1]), Path(sys.argv[2])
bad, total = [], {"line numbers": 0, "comment lines": 0}
names = sorted({p.name for p in a.glob("*.f90")} | {p.name for p in b.glob("*.f90")})
for n in names:
    if not (a / n).exists() or not (b / n).exists():
        bad.append(f"{n}: only on one side")
        continue
    x, y = (a / n).read_text().splitlines(), (b / n).read_text().splitlines()
    if x == y:
        continue
    kinds = {"line numbers": 0, "comment lines": 0}
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, x, y, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        old, new = x[i1:i2], y[j1:j2]
        if tag == "replace" and len(old) == len(new) and all(
                "MyFile" in o and re.sub(r"\d+", "N", o) == re.sub(r"\d+", "N", w) for o, w in zip(old, new)):
            kinds["line numbers"] += len(old)
        elif all(l.strip().startswith("!") or not l.strip() for l in old + new):
            kinds["comment lines"] += len(old) + len(new)
        else:
            bad.append(f"{n}: {tag} {i1 + 1}-{i2} / {j1 + 1}-{j2}: {old[:2]} -> {new[:2]}")
    print(f"   {n}: only " + ", ".join(f"{v} {k}" for k, v in kinds.items() if v))
    for k in total:
        total[k] += kinds[k]
for line in bad:
    print("   DIFFERENT " + line)
print(f"   {len(names)} files; differences only in __LINE__ numbers ({total['line numbers']} lines) and "
      f"comment lines ({total['comment lines']})" if not bad else "   real differences found")
sys.exit(1 if bad else 0)
