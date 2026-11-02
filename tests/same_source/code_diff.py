"""Do two versions of a source file differ in code, or only in comments?

    python -I code_diff.py FILE_A FILE_B

Prints "comments" if the files are the same once comments and trailing blanks
are removed, otherwise "code" and the first differing code lines. Comments:
Fortran "!" to the end of the line (outside quoted strings), and in
fixed-form SWAN files (.ftn) whole lines starting with C, c or * in column 1.
Blank lines are ignored. C preprocessor lines (#...) count as code, including
the text of #error messages.
"""
import difflib
import sys


def strip(line, fixed):
    if fixed and line[:1] in ("C", "c", "*"):
        return ""
    quote = None
    for k, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "!" and not line.lstrip().startswith("#"):
            return line[:k].rstrip()
    return line.rstrip()


def code(path):
    fixed = path.endswith(".ftn")
    lines = open(path, encoding="latin-1").read().split("\n")
    return [s for s in (strip(l, fixed) for l in lines) if s.strip()]


def main(a, b):
    ca, cb = code(a), code(b)
    if ca == cb:
        print("comments")
        return 0
    print("code")
    for l in list(difflib.unified_diff(ca, cb, lineterm="", n=0))[2:12]:
        print("    " + l[:150])
    return 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:]))
