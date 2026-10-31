"""Source checks for 1-fixes/swan-vegetation-fixes.patch (veg3_flexible_plants and plant_input_grids).

    python -I check_source.py SWAN_SRC_DIR

veg3_flexible_plants (swancom2.ftn, SVEG_COAWST flexible vegetation): the second moment of
area is diameter x thickness^3 / 12 and the Cauchy number is not divided by
an extra 1e12 (the formulas of ROMS's vegetation_drag.F, VEG_FLEX).
plant_input_grids (swanmain.ftn): plant height, diameter and thickness are interpolated
on the input grids that INPGRID registers for them (swanpre1.ftn), and
INPGRID NPHT sets VARNPH.
Prints each check; exit 1 if one fails. A note lists what is known and left
unchanged (grid-type tests of the unstructured-grid branch).
"""
import re
import sys

d = sys.argv[1]
com2 = open(f"{d}/swancom2.ftn").read()
main = open(f"{d}/swanmain.ftn").read()
pre1 = open(f"{d}/swanpre1.ftn").read()
ok = True


def check(item, what, good, detail):
    global ok
    ok &= good
    print(f"{item:25s} {what:62s} {detail:28s} {'ok' if good else 'BAD'}")


sma = re.search(r"^\s*SMA\s*=\s*(.*)$", com2, re.M).group(1).split("!")[0].strip()
check("veg3_flexible_plants", "second moment of area = D t^3/12", sma.replace(" ", "") == "VEGDIL_LOC*VEGTHK_LOC**3/12.", sma)
cau = re.search(r"^\s*CAUCHY_NUM\s*=\s*(.*)$", com2, re.M).group(1).split("!")[0].strip()
check("veg3_flexible_plants", "Cauchy number not divided by an extra MAX_EPS", "CFF2+MAX_EPS" not in cau.replace(" ", ""), cau[:28])

reg = {}
for igrd, name in re.findall(r"IGRD\s*=\s*(\d+)[^\n]*\n\s*PSNAME\s*=\s*'(NP\w\wGRID)'", pre1):
    reg[name[:4]] = int(igrd)
print(f"         INPGRID registers: {reg}")
for field, key in (("NPHTF", "NPHT"), ("NPDAF", "NPDA"), ("NPTKF", "NPTK")):
    used = sorted({int(g) for g in re.findall(rf"SVALQI\s*\(\s*XP\s*,\s*YP\s*,\s*(\d+)\s*,\s*{field}", main)})
    check("plant_input_grids", f"{field} interpolated on input grid {reg.get(key)}", used == [reg.get(key)], f"SVALQI grids {used}")
blk = re.search(r"PSNAME\s*=\s*'NPHTGRID'.*?\n(.*?\n.*?\n)", pre1, re.S).group(1)
check("plant_input_grids", "INPGRID NPHT sets VARNPH", "VARNPH = .TRUE." in blk, "VARNPH" if "VARNPH" in blk else "VARNPL")

left = re.findall(r"IF \( IGTYPE\((\d+)\)\.EQ\.3 \) THEN\s*\n\s*XNP(\w) = NP(?:HT|DA|TK)F", main)
if left:
    print("note: unstructured-grid branch tests IGTYPE(" + ", ".join(g for g, _ in left)
          + ") for plant height/diameter/thickness (grids 18, 19, 20): left unchanged")
print("CONSISTENT" if ok else "INCONSISTENT")
sys.exit(0 if ok else 1)
