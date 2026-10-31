"""Source checks for 1-fixes/roms-vegetation.patch.

    python -I check_source.py COAWST_TREE

  drag_work_array   vegetation_drag.F declares wrk with the halo bounds
                    LBi:UBi,LBj:UBj that the exchange routines use
  zero_gap_stop     vegetation_turb.F stops when diameter x thickness x
                    density >= 1 (zero gap between plants)
  tau_veg_units     tau_veg uses the plant work per unit mass (divided by the
                    w-cell thickness), not integrated over the cell
  v_drag_depth      step2d_LF_AM3.h: the barotropic vegetation drag on v uses
                    the v-point depth average Drhs(i,j-1), Drhs(i,j)
Exit 1 if a check fails.
"""
import re
import sys

t = sys.argv[1]
drag = open(f"{t}/ROMS/Nonlinear/Vegetation/vegetation_drag.F").read()
turb = open(f"{t}/ROMS/Nonlinear/Vegetation/vegetation_turb.F").read()
s2d = open(f"{t}/ROMS/Nonlinear/step2d_LF_AM3.h").read()
code = lambda s: "\n".join(l.split("!")[0] for l in s.splitlines())
ok = True


def check(name, what, good, detail):
    global ok
    ok &= good
    print(f"{name:18s} {what:58s} {detail:34s} {'ok' if good else 'BAD'}")


m = re.search(r"dimension\(([^)]*)\)\s*::\s*wrk\s*$", code(drag), re.M)
check("drag_work_array", "wrk declared with the halo bounds", bool(m) and m.group(1).replace(" ", "") == "LBi:UBi,LBj:UBj",
      f"dimension({m.group(1) if m else '?'})")
check("zero_gap_stop", "stop when diameter x thickness x density >= 1",
      bool(re.search(r"IF\s*\(\s*solid\s*\.ge\.\s*1\.0_r8\s*\)", code(turb))), "")
cff2 = re.search(r"^\s*cff2\s*=\s*MIN\(\s*\(1\.0_r8/\(ck\*\*2\.0_r8\*(\w+)\)\)", code(turb), re.M)
per_mass = bool(re.search(r"Pveg\s*=\s*tke_loc_veg\s*/\s*\(0\.5_r8\*\(Hz\(i,j,k\)\+Hz\(i,j,k\+1\)\)\)", code(turb)))
check("tau_veg_units", "tau_veg from the plant work per unit mass",
      bool(cff2) and cff2.group(1) == "Pveg" and per_mass, f"uses {cff2.group(1) if cff2 else '?'}")
vd = re.search(r"DO j=JstrV,Jend\s*\n\s*cff3=2\.0_r8/\((Drhs\([^)]*\))\+Drhs\(i,j\)\)\s*\n\s*fac=step2d_vveg", code(s2d))
check("v_drag_depth", "v-point vegetation drag uses Drhs(i,j-1)", bool(vd) and vd.group(1) == "Drhs(i,j-1)",
      vd.group(1) if vd else "not found")
print("CONSISTENT" if ok else "INCONSISTENT")
sys.exit(0 if ok else 1)
