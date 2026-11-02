# SWAN command catalogue (COAWST v3.9 bundled SWAN)

> Compiled 2026-11-02 from the SWAN source bundled with COAWST at commit 26e6fb7 (parser `swanpre1.ftn`, defaults in `swanmain.ftn`), cross-checked against the 41.51 manuals in `docs/manuals/`. A companion to the project's options document (kept with the project's case records); the line numbers refer to that commit. Written with automated help and reviewed for the commands the reef cases use; for any other command, check the cited lines before relying on a default.


Ground truth for this document is the SWAN command parser and initialisation code bundled with COAWST v3.9:

* source root: `COAWST/SWAN/src` (cited below as `swanpre1.ftn:NNN`, `swanmain.ftn:NNN`, etc.)
* parser: `swanpre1.ftn` (physics/numerics/grid commands), `swanpre2.ftn` (boundary, output, input-grid reading), `swanpre3.ftn`
* defaults: subroutine `SWINIT` in `swanmain.ftn` (lines 2016–2800), post-parse consistency checks in `ERRCHK` (`swanmain.ftn` 7860–8220)
* physics: `swancom1.ftn` (driver `SWCOMP`, source-term assembly), `swancom2.ftn` (bottom friction, vegetation, mud, breaking, whitecapping), `swancom3.ftn` (wind input, drag), `swancom4.ftn` (quadruplets, triads), `swancom5.ftn` (propagation velocities, dispersion)
* COAWST additions: `waves_coupler.ftn` (MCT exchange), `waves_control.ftn` (multi-grid driver), `#ifdef SWAN_MODEL / COAWST_COUPLING` blocks throughout.

Cross-checks are against the official SWAN 41.51 user manual (`swanuse.txt`, cited as "swanuse 41.51 §x") and the COAWST v3.9 user manual (`manual.txt`, cited as "COAWST manual §x"). Where parser and manual disagree the parser wins and the disagreement is flagged with **[DISCREPANCY]**.

**Version note.** `swanmain.ftn:2214` sets `VERNUM = 41.51`, but the source carries change tags up to 42.15 and 43.02 (e.g. `TRIAD ... IC` 42.15, `BREAKING ASYM` 41.97, `WCAP AB CURRENT` 42.04, `OBST FIG [dss]` 42.06, `SET [excmark]` 43.01, `COMPDA = 0.` 43.02). The bundled SWAN is therefore a post-41.51 development snapshot of SWAN that reports itself as 41.51; a few commands exist in the code that the 41.51 manual does not document (noted below).

**Parser conventions used below.** Keyword matching is on the leading characters shown in capitals (e.g. `BRE`, `FRIC`, `NONSTAT`). Numeric arguments are read with `INREAL/ININTG(name, var, mode, default)`: mode `REQ` = required, `STA` = optional with the stated default *assigned if omitted*, `UNC` = optional and the variable is *left unchanged* (so the effective default is whatever `SWINIT` set). Parameter arrays: `PNUMS` (numerics), `PSURF` (breaking), `PBOT` (friction), `PWCAP` (whitecapping), `PTRIAD` (triads), `PQUAD` (quadruplets), `PWIND` (wind), `PWTAIL` (spectral tail), `PMUD`, `PTURBV`, `PDIFFR`, `PSETUP`.

---

## 1. Start-up commands

### 1.1 `MODE`

Syntax (`swanpre1.ftn:772–810`):

```
MODE  STATionary | NONSTationary(=DYNamic)    ONEDimensional | TWODimensional    [NOUPDAT]
```

| keyword | effect in source | notes |
|---|---|---|
| `STAT` (default) | `NSTATM = 0` | default `NSTATM=-1` (unknown) at `swanmain.ftn:2347`; a `COMPUTE` without time arguments also forces stationary |
| `NONSTAT` / `DYN` | `NSTATM=1, NSTATC=1, ICOND=1, PNUMS(30)=0` (`swanpre1.ftn:774–781`) | switches on default initial condition and *disables under-relaxation* |
| `ONED` | `ONED=.TRUE.`; fatal (`MSGERR 4`) in parallel runs (`swanpre1.ftn:792–797`) | COAWST always runs MPI, so 1D mode is effectively unusable in coupled runs |
| `TWOD` (default) | `ONED=.FALSE.` | |
| `NOUPDAT` | `ACUPDA=.FALSE.` (undocumented): action densities are not updated | test option |

Mode governs the propagation scheme choice (see §PROP) and the iteration count (`ITERMX=MXITST` for stationary, `=MXITNS` for nonstationary; `swanpre1.ftn:1003–1007`). All COAWST examples use `MODE NONSTATIONARY TWODIMENSIONAL`.

### 1.2 `SET`

Syntax as parsed (`swanpre1.ftn:2471–2530`):

```
SET [level] [nor] [depmin] [maxmes] [maxerr] [grav] [rho] [cdcap] [uscap] [inrhog] [hsrerr]
    NAUTical|CARTesian [pwtail] [froudmax] [icewind] [excmark] [sort] [nsweep] CURV [printf] [prtest]
```

| parameter | variable | default (source) | meaning |
|---|---|---|---|
| `[level]` | `WLEV` | 0 | uniform water-level offset added to depth everywhere (`DEPW = DEP + WLVL + WLEV`, `swanmain.ftn` SNEXTI) |
| `[nor]` | `DNORTH` | 90 (`swanmain.ftn:2273`) | direction of North w.r.t. x-axis |
| `[depmin]` | `DEPMIN` | 0.05 m (`swanmain.ftn:2403`) | positive depths smaller than this are clipped to `DEPMIN`; COAWST examples use 0.10 |
| `[maxmes]` | `MAXMES` | 200 (set in OCPINI) | max error messages before abort |
| `[maxerr]` | `MAXERR` | 1 (`swanmain.ftn:340`) | error level above which no computation starts |
| `[grav]` | `GRAV` | 9.81 (`:2265`) | |
| `[rho]` | `RHO` | 1025 (`:2275`); also resets `PWIND(9)=PWIND(16)/RHO` and `PWIND(17)` in ERRCHK (`:7868–7869`) | water density |
| `[cdcap]` | `CDCAP` | 99999 (`:2268`) (= no cap) | cap on wind drag coefficient (Wu/FIT drag) |
| `[uscap]` | `USCAP` | 99999 (`:2269`) | cap on u* (ST6 physics) — not in COAWST manual |
| `[inrhog]` | `INRHOG` | 0 (`:2402`) | 0: output in variance units (m²), 1: true energy (×ρg). **All COAWST example inputs use `INRHOG 1`** because ROMS divides the imported dissipation fields by `rho0` (`Master/mct_roms_swan.h:1414,1461,1505`) expecting W/m². With `INRHOG 0` the dissipation sent to ROMS is too small by ρg. |
| `[hsrerr]` | `HSRERR` | 0.1 (`:2447`) | relative Hs mismatch at boundary that triggers warnings |
| `NAUT` / `CART` | `BNAUT` | CART (`:2439`) | direction convention; `NAUT` also sets `OUTPAR(4)=0` |
| `[pwtail]` | `PWTAIL(1)` | 4 (`:2278`); `PWTAIL(3)=pwtail+1` | power of the f⁻ⁿ high-frequency tail; GEN1/GEN2/GEN3 JANSSEN force 5 if left at 4 |
| `[froudmax]` | `PNUMS(18)` | 0.8 (`:2576`) | currents are scaled down so that U ≤ froudmax·√(gd) (`swanmain.ftn:9181–9190`), applied to coupled ROMS currents too |
| `[icewind]` | `ICEWIND` | 0 | scaling of wind input by open-water fraction |
| `[excmark]` | `excmark` | 999 (`:2335`, tag 43.01) | unstructured-grid boundary marker |
| `[sort]`, `[nsweep]`, `CURV` | `usort`, `nsweep`, `CCURV` | −999, −999, F | undocumented sweep-ordering controls (41.48–41.68) |

### 1.3 `COORDINATES`

```
COORDinates  CARTesian | SPHErical [rearth] CCM|QC     REPeating        (swanpre1.ftn:874–912)
```

* `CART` → `KSPHER=0` (default, `swanmain.ftn:2458`).
* `SPHE [rearth]` → `KSPHER=1`, `REARTH` default 2·10⁷/π (`:2461`), projection `PROJ_METHOD`: `QC` quasi-Cartesian (=0, the SWINIT default) or `CCM` uniform Mercator (=1, the parser default when `SPHE` is given — `INKEYW('STA','CCM')`). **[DISCREPANCY]** swanuse 41.51 §4.4 lists `CCM` as default; SWINIT initialises `PROJ_METHOD=0` (QC) but the parser overrides to CCM whenever `SPHE` is given, so CCM is the effective default.
* `REP` → `KREPTX=1`: periodic in computational x (wave energy leaving one x-end enters the other). ERRCHK forbids it on curvilinear/unstructured grids and requires `MXC ≥ 1/2/3` for BSBT/SORDUP/S&L respectively (`swanmain.ftn:8130–8140`). COAWST's MCT export handles `KREPTX=1` specially (`waves_coupler.ftn:1020–1060`), so periodic-x SWAN domains are supported in coupling. (COAWST also adds `SWAN_NS_PERIODIC`, see §12.)
* `SETUP` is flagged as incorrect with spherical coordinates (`swanpre1.ftn:2385`).

### 1.4 `NSGRIDS` (COAWST only)

```
NSGRIDS [numgrids] [mygrid] [myparent]          (swanpre1.ftn:855–861, under #ifdef SWAN_MODEL)
```

Read by the SWAN parser only for `NUM_SGRIDS` (the two other integers are read as `JUNK`); the grid id and parent id are parsed independently by `waves_control.ftn:126–145` (single-digit reads!). Grids with `myparent>0` receive 2-D spectra at their boundaries from the parent at every parent step, linearly interpolated in time (`swanmain.ftn:8870–8890`); the child time step must divide the parent's (`dtscale = INT(DT_parent/DT_child)`, `waves_control.ftn:329–333`). See COAWST manual §10.

---

## 2. `CGRID` — computational and spectral grid

```
CGRID  REGular [xpc] [ypc] [alpc] [xlenc] [ylenc] [mxc] [myc]
     | CURVilinear [mxc] [myc] (EXCeption [xexc] [yexc])
     | UNSTRUCtured
       CIRcle | SECtor [dir1] [dir2]    [mdc] [flow] [fhigh] [msc]        (swanpre1.ftn:1861–2170)
```

Frequency axis (`swanpre1.ftn:1991–2022`): `FLOW`, `FHIGH`, `MSC` are each optional (`STA`, −999); any two are enough, the third is computed with γ=1.1 (`MSS = NINT(log(fhigh/flow)/log 1.1)` etc.). Frequencies are logarithmic: `MSC = msc+1` bins, `σ_{i+1} = γσ_i`, γ = (fhigh/flow)^{1/msc}. The relative resolution `df/f = γ−1` is printed. ERRCHK warns if `|γ−1.1| > 0.055` when DIA quadruplets (`IQUAD` 1–3, 8) are on (`swanmain.ftn:8178–8188`) because the DIA is calibrated for 10 % resolution.

Direction axis: `CIRCLE [mdc]` → `DDIR = 2π/mdc`, with the first bin centred at `ALPC + DDIR/2` (`:2026–2030`); `SECTOR [dir1] [dir2] [mdc]` → `MDC = mdc+1` bins over the sector (nautical → Cartesian swap if `NAUT`). ERRCHK: quadruplets with a sector < 30° → error level 2; any sector → warning (`swanmain.ftn:8120–8135`). The `LSPNAR` flag (too narrow directional spread) forces `BRESCL=.FALSE.` and `PNUMS(6)=1` (full upwind in θ) (`:8102–8110`).

Implications: `[mdc]` sets the directional diffusion/garden-sprinkler behaviour and the refraction CFL; 36 bins (10°) is the COAWST manual example (`CGRID CURVILINEAR 86 64 EXC ... CIRCLE 36 0.04 1.0 24`, COAWST manual §10). The first bin should carry no energy (swanuse 41.51 §4.5.1 recommends `flow` = 0.03 Hz). With `BIN` boundary spectra (`MSC=3`) quadruplets are fatal (`:8142–8146`).

Under `SWAN_MODEL` all spectral arrays live in per-grid modules (`M_GENARR_MOD(ng)%SPCSIG_G` …) to allow several SWAN grids in one executable (`:2043–2049`).

---

## 3. Input grids: `INPGRID` / `READINP` and how coupling overrides them

```
INPgrid BOTtom|WLEVel|CURrent|VX|VY|FRiction|WInd|WX|WY|NPLAnts|TURB|MUDL|AICE|HICE|HSS|TSS|DSS
        [NPHT|NPDA|NPTK  (SWAN_MODEL only)]
        REG [xpinp] [ypinp] [alpinp] [mxinp] [myinp] [dxinp] [dyinp] | CURV [stagrx] [stagry] [mxinp] [myinp] | UNSTRUC
        (NONSTATionary [tbeginp] [deltinp] SEC|MIN|HR|DAY [tendinp])        (swanpre1.ftn:1410–1700, 4404–4440)
```

Grid numbers `IGRD`: 1 bottom, 2/3 current, 4 friction, 5/6 wind, 7 water level, 10 ASTD, 11 NPLANTS, 12 TURB, 13 MUDL, 14 AICE, 15 HICE, 16 HSS, 17 TSS, 18 DSS (and, under `SWAN_MODEL`, 18 NPHT, 19 NPDA, 20 NPTK — **note the clash: NPHT and DSS both use IGRD=18** in the SWAN_MODEL build, `swanpre1.ftn:1613–1621`).

`NONSTAT` sets `IFLDYN(igrd)=1` and the file-time bookkeeping (`:4404–4432`); it is a fatal error in stationary mode and forbidden for bottom/coordinates.

**COAWST behaviour (important):** in the `SWAN_MODEL` build the time-dependent *file* reads for currents (fields 2,3), friction (4) and water level (7) in `SNEXTI` are compiled out (`swanmain.ftn:9071–9077`, `9100–9106`, `9170–9176`, all `#ifndef SWAN_MODEL`). Those fields are filled only by the MCT coupler (`WAVFOCN_COUPLING`, `waves_coupler.ftn:2185–2275`) into `COMPDA(:,JWLV2)`, `JVX2/JVY2`, `JFRC2`, `JNPLA2…JNPTK2` (and bottom level `JBOTLV` when `SED_MORPH`). The *rest* of the `IFLDYN=1` block still runs, i.e. the depth is recomputed as `DEP + WLVL + WLEV` and the Froude limiter is applied to the currents **only if `NONSTAT` was given on the corresponding `INPGRID`**. Consequently every COAWST coupled example contains

```
INPGRID CURRENT CURVILINEAR 0 0 86 81 EXC 9.999000e+003  &  NONSTAT 20000101.000000 25 DAY 20000126.000000
INPGRID WLEV    CURVILINEAR ... NONSTAT ...
INPGRID FRIC    CURVILINEAR ... NONSTAT ...
```

with **no `READINP`** (`Projects/Inlet_test/DiffGrid/swan_inlet_test_diff.in:26–35`). Omitting `INPGRID WLEV … NONSTAT` means ROMS water levels are received but never added to the depth. Omitting `INPGRID CURRENT` altogether means `ICUR` stays 0 and `JVX2/JVY2` are never allocated, so currents are ignored; giving it without `NONSTAT` still feeds the coupled currents into the propagation (the coupler writes `JVX2/JVY2` directly) but skips the Froude limiter. Omitting `INPGRID FRIC` leaves `VARFR=.FALSE.`, so the ROMS roughness is never used by `SBOT` even with `BBL_MODEL`. `INPGRID CURRENT` under `COAWST_COUPLING` also sets `ICUR=1` and allocates `UXB/UYB` (`swanpre1.ftn:1420–1448`); `INPGRID FRIC` sets `VARFR=.TRUE.` and initialises the friction array to 1e-4 (`:1462–1474`); `INPGRID WIND` sets `LWINDR=2`, `VARWI=.TRUE.` (`:1476–1507`). Wind files *are* read in COAWST unless `AIR_WAVES` (coupled to WRF) is defined (`swanmain.ftn:9027`).

Bottom from ROMS: only when `SED_MORPH` is defined is `DEPTH` overwritten with ROMS bathymetry each exchange (`waves_coupler.ftn:2153–2173`); otherwise SWAN uses its own `READINP BOTTOM`.

Friction from ROMS: the ocean sends `ZO` (bottom roughness). With `BBL_MODEL` it is stored as `COMPDA(JFRC2)=MAX(ZO, cff2)` where `cff2` is the uniform coefficient of the chosen friction law (`PBOT(3)` JONSWAP, `PBOT(2)` Collins, `PBOT(5)` Madsen; `waves_coupler.ftn:2203–2230`); without `BBL_MODEL` the array is simply set to `cff2`. `SBOT` (`swancom2.ftn:233–270`) uses the spatially varying array **only for COLLINS (as cfw) and MADSEN (as kn)**; JONSWAP always uses the scalar `PBOT(3)`. So a ROMS roughness length is physically meaningful only with `FRICTION MADSEN` (which is what all COAWST examples use: `FRICTION MADSEN 0.05`). With COLLINS the roughness in metres would be interpreted as a dimensionless cfw.

Several imports are accumulated and averaged over the coupling interval when `Numcouple>1` (`io.eq.1` first fill, then add; `waves_coupler.ftn:2233–2275`).

---

## 4. Initial conditions, hot files and restarts

```
INITial  DEFault | ZERO | PAR [hs] [per] [dir] [dd] | HOTStart MULTiple|SINGle 'fname' FREE|UNFormatted      (swanpre1.ftn:6829–6960)
HOTFile  'fname' FREE|UNFormatted                                                                      (swanpre1.ftn:1378–1395, 7400–7420)
RESTART  'fname' FREE|UNFormatted [delt] SEC|MIN|HR|DAY                                               (COAWST only; swanpre1.ftn:7546–7552)
```

* `ICOND`: 0 none, 1 default (JONSWAP from local wind, set automatically by `MODE NONSTAT` or by `GEN3` without `AGROW`), 2 parametric, 3 zero, 4 hotfile.
* `HOTSTART SINGLE` reads one global file (written by a 1-processor run), `MULTIPLE` reads per-node files `fname-NNN`.
* **COAWST `RESTART`** reuses the `BACKUP` routine with the keyword `REST` and additionally reads a restart interval `[delt]` (`ININTV('DELT', rstdt, 'STA', 0.)`), storing name/unit/interval per grid; `SWAN_RST` writes a hot-start-format file every `INT(dtswanrst/DT)` steps (`swanmain.ftn:960–975`), called from `waves_control.ftn:378` after each parent step. Example: `RESTART 'swan_rst.dat' FREE 1 HR` before `COMPUTE` (COAWST manual §5.3.7 and §10). The written file is a normal SWAN hot file and is read back with `INIT HOTSTART`.
* `BOUNDSPEC SHAPE JONswap [gamma=3.3] | PM | GAUSs [sigfr=0.01] | BIN | TMA [gamma] [d]  PEAK|MEAN  DSPR POWer|DEGRees` (`swanpre2.ftn:3192–3250`) controls parametric boundary/initial spectra; `PSHAPE(1)=3.3` default (`swanmain.ftn:2300`).

---

## 5. Wind input and generation mode: `GEN1`, `GEN2`, `GEN3`, `WIND`, `SSWELL`, `NEGATINP`

### 5.1 `WIND [vel] [dir] [astd]` (`swanpre1.ftn:3154–3186`)
Uniform wind; sets `LWINDR=1`, `IWIND=LWINDM` (defaults to 4 = Janssen if no GEN command yet, `:3179`). Ignored if an `INPGRID WIND` was already given (`VARWI`).

### 5.2 `GEN1` / `GEN2` (`swanpre1.ftn:3189–3260`)
```
GEN1 [cf10] [cf20] [cf30] [cf40] [edmlpm] [cdrag] [umin] [cfpm]
GEN2 [cf10] [cf20] [cf30] [cf40] [cf50] [cf60] [edmlpm] [cdrag] [umin] [cfpm]
```
Set `IGEN=1|2`, `LWINDM=1|2`, and switch off quadruplets and whitecapping (`IQUAD=0, IWCAP=0`). Defaults (`PWIND`, `swanmain.ftn:2733–2745`): cf10 188, cf20 0.59, cf30 0.12, cf40 250, cf50 0.0023, cf60 −0.223, edmlpm 0.0036, cdrag 0.00123, umin 1.0, cfpm 0.13. `PWTAIL(1)` is set to 5 if still 4. First/second-generation parametric growth with a PM limit spectrum.

### 5.3 `GEN3` (`swanpre1.ftn:3285–3465`)
```
GEN3  JANSsen [cds1] [delta] | KOMen [cds2] [stpm] | WESTH [cds2] [br] (default) | YAN (undoc.)
    | ST6 [a1sds] [a2sds] [p1sds] [p2sds] UP|DOWN HWANG|FAN|ECMWF VECTAU|SCATAU TRUE10|U10Proxy [windscaling] (DEBias [cdfac])
    | BABanin [a1sds] [a2sds] [p1sds] [p2sds] [cdsv] [feswell] UP|DOWN (VECTAU) (TRUE10)   (legacy)
      ( DRAG WU|FIT|SWELL )   ( AGROW [a] )
```

| option | source effect | defaults |
|---|---|---|
| (default) `WESTH` | `LWINDM=5` (Yan 1987 wind input), `IWCAP=7` (Alves & Banner / Van der Westhuysen 2007 saturation-based whitecapping) `:3316–3323` | `cds2=5.0e-5` (`PWCAP(1)`), `br=1.75e-3` (`PWCAP(12)`) — assigned with `STA`, i.e. always reset. SWINIT also pre-sets `IWCAP=7` (`swanmain.ftn:2371`) and `IDRAG=1` so even without any GEN3 line the model is third-generation WESTH. |
| `KOMEN` | `LWINDM=3`, `IWCAP=1` | `cds2=2.36e-5` (`PWCAP(1)`, `:2613`), `stpm=3.02e-3` (`PWCAP(2)`), `powst=2`, `delta=1` (`PWCAP(10)`, changed from 0 since 40.91A), `powk=1` |
| `JANSSEN` | `LWINDM=4`, `IWCAP=2`; allocates u*, z0, Cd, τw arrays; forces `pwtail=5` | `cds1=4.5` (`PWCAP(3)`), `delta=0.5` (`PWCAP(4)`); the used coefficient is `PWCAP(1)=cds1·stpm^powst` (`:3301`) |
| `ST6` | `LWINDM=8`, `IWCAP=8` (Rogers/Babanin/Zieger observation-based input and dissipation, `SdsBabanin.ftn90`) | a1sds 2.8e-6, a2sds 3.5e-5 (`swanmain.ftn:2649–2650`), p1sds=p2sds=4, `UP`, `HWANG` drag (`IDRAG=4`; FAN=5, ECMWF=6), `VECTAU`, `U10PROXY` with `WNDSCL=32`, `CDFAC=1`. ST6 skips the `DRAG` keyword (`IF (IWIND.NE.8)`) |
| `BABANIN` | legacy spelling; all four coefficients plus `[cdsv] [feswell]` are **required**, forces `IDRAG=4` and the Rogers swell dissipation | |
| `DRAG WU|FIT|SWELL` | `IDRAG=1|2|3` (`:3428–3438`): Wu (1982) `Cd=(0.8+0.065U10)·1e-3` for U10>7.5, else 1.2875e-3 (`swancom3.ftn:1000–1012`); FIT = Zijlema et al. (2012) 2nd-order polynomial with u* capped at 1.9441 above 50.7 m/s; SWELL = swell-dependent drag | default `IDRAG=1` (`swanmain.ftn:2368`). **[DISCREPANCY]** The source comment says "when coupled with ADCIRC default is ADCIRC drag" and the code tag is 42.00; swanuse 41.51 also says WU is default — consistent. |
| `AGROW [a]` | `PWIND(31)=a` (Cavaleri & Malanotte-Rizzoli linear growth), default 0.0015; if absent in nonstationary mode `ICOND=1` (default initial spectrum) | `PWIND(31)=0` otherwise (`swanmain.ftn:2757`) |

COAWST additions: under `SWAN_MODEL` every `GEN3` (except `IWIND=4`) allocates `JUSTAR` *and* `JCDRAG` (`swanpre1.ftn:3444–3452`, tagged JCW) so u* and Cd are available for export to WRF; `DRAGLIM_DAVIS` caps the Wu drag at 2.4e-3 (`swancom3.ftn:1005–1007`; COAWST manual §4.3.8 says 2.85e-3 — **[DISCREPANCY]** the code uses 0.0024).

ERRCHK consistency rules (`swanmain.ftn:7930–7975`): Komen/Yan wind with non-Komen/non-AB whitecapping, AB whitecapping without Yan wind, Babanin input/dissipation mixed with others, Janssen wind with non-Janssen whitecapping → warnings. Quadruplets off with 3rd-generation wind → error 2 (`:8101–8106`) — COAWST examples nevertheless use `GEN3` + `OFF QUAD` (the run continues).

### 5.4 `SSWELL ROGers [cdsv] [feswell] | ARDhuin [cdsv] | ZIEger [b1]` (`:3501–3523`)
Swell (non-breaking) dissipation; default `ARDHUIN` with `cdsv=1.2`, `ZIEGER b1=0.00025`. Intended for ST6. `NEGatinp [rdcoef]` (`:3526–3529`) enables negative wind input (fraction, default 0).

### 5.5 `GEN4` (`:3468–3498`) — quasi-coherent 4th-generation mode: turns off wind/quads/whitecapping/diffraction/setup, disables the limiter, fixes the stopping criterion. Research option; not usable with COAWST surf-zone physics.

---

## 6. `WCAPPING`

```
WCAPping  KOMen [cds2] [stpm] [powst] [delta] [powk] | JANSsen [cds1] [delta] [pwtail] | LHIG [cflhig]
        | BJ [bjstp] [bjalf] | KBJ [bjstp] [bjalf] [kconv] | AB [cds2] [br] (CURrent [cds3])        (swanpre1.ftn:2762–2850)
```

Default keyword `AB` (`INKEYW('STA','AB')`, tag 42.00): `IWCAP=7`, `cds2=5.0e-5`, `br=1.75e-3`. `KOMEN` → `IWCAP=1` (all parameters `UNC`, so defaults from SWINIT: 2.36e-5, 3.02e-3, 2, 1, 1). `JANSSEN` → `IWCAP=2`, `cds1=4.5`, `delta=0.5`, `pwtail=5`. Undocumented: `LHIG` (`IWCAP=3`, `PWCAP(5)=1`), `BJ` (4, `PWCAP(6)=0.88`, `PWCAP(7)=1`), `KBJ` (5, plus `PWCAP(8)=0.75`). `AB … CURRENT [cds3]` (tag 42.04, **not in swanuse 41.51**) sets `IWCCUR=1`, `PWCAP(14)=0.8`: enhanced current-induced dissipation (Van der Westhuysen 2012). With XNL quadruplets (`IQUAD` 51–53) AB `br` is changed to 1.95e-3 (`swanmain.ftn:8192–8196`). `OFF WCAP` sets `IWCAP=0`.

---

## 7. `QUADRUPL` and `MDIA`

```
QUADrupl [iquad] [lambda] [Cnl4] [Csh1] [Csh2] [Csh3]                  (swanpre1.ftn:3672–3690; all UNC)
MDIA LAMbda < [lambda] >  CNL4 < [cnl4] > | CNL4_12 < [cnl4_1] [cnl4_2] >   (:3538–3600)
```

| parameter | variable | default | meaning |
|---|---|---|---|
| `[iquad]` | `IQUAD` | 2 (`swanmain.ftn:2370`) | 1 semi-implicit DIA per sweep; 2 explicit DIA per sweep; 3 explicit DIA per iteration; 8 per-iteration with piecewise-constant interpolation (faster); 4 multiple DIA (`MDIA`); 51/52/53 exact XNL (deep, WAM depth scaling, finite depth) via `mod_xnl4v5.ftn90` |
| `[lambda]` | `PQUAD(1)` | 0.25 | DIA configuration |
| `[Cnl4]` | `PQUAD(2)` | 3e7 | DIA proportionality |
| `[Csh1..3]` | `PQUAD(3..5)` | 5.5, 0.833, −1.25 | shallow-water scaling (WAM) |
| MDIA | `LAMBDA(6)`, `CNL4_1/2(6)` | λ = 0.08 0.09 0.11 0.15 0.16 0.29; C = 8.77 −13.82 10.02 −15.92 14.41 0.65 (×(2π)⁹) (`swanmain.ftn:2430–2434`) | |

**COAWST-specific override:** in ERRCHK, if currents are present and `IQUAD` is 1 or 2, SWAN normally only prints a recommendation; COAWST adds `IQUAD = 3` (`swanmain.ftn:8097–8098`, tagged `!jcw`), i.e. **any coupled run with currents silently switches the DIA to per-iteration integration** (doubles memory for the interaction arrays). The action limiter is disabled (`PNUMS(20)=1e20`) when `IQUAD=0` (`:8166–8170`), so `OFF QUAD` also removes the limiter unless re-set with `NUM … [limiter]`. Quadruplets are switched off locally where the Ursell number exceeds `PTRIAD(3)` (`LIMITER [ursell]`, default 10).

---

## 8. `BREAKING`

```
BREaking  CONstant [alpha] [gamma]
        | VARiable|NELson [alpha] [gammin] [gammax] [gamneg] [coeff1] [coeff2]
        | RUEssink [alpha] [a] [b]
        | TG [alpha] [gamma] [pown]
        | BKD [alpha] [gamma0] [a1] [a2] [a3] [npnts]
        | ASYM [alpha] [gamma0] [a]
        ( DIRectionality [spread] )  ( FREQDep [power] [fmin] [fmax] )            (swanpre1.ftn:2678–2760)
```

Breaking is **on by default** (`ISURF=1`, `swanmain.ftn:2372`, Battjes–Janssen with `alpha=1.0`, `gamma=0.73`, `:2675–2676`); `OFF BREAKING` sets `ISURF=0`.

| option | `ISURF` | parameters (defaults assigned with `STA`) | physics |
|---|---|---|---|
| `CONSTANT` | 1 | `PSURF(1)=alpha=1.0`, `PSURF(2)=gamma=0.73` | Battjes & Janssen (1978) bore dissipation with H_max=γd; `Qb` from the B&J implicit relation (`FRABRE`, `swancom2.ftn:1952`) |
| `VARIABLE`/`NELSON` | 2 | `alpha=1.5`, `gammin=0.55`, `gammax=0.81`, `gamneg=0.73`, `coeff1=0.88`, `coeff2=0.012` (`PSURF(1,4,5,6,7,8)`) | Nelson (1987) slope-dependent γ: `γ = gammin + coeff1·exp(−coeff2/slope)` on positive slopes (in mean wave direction), `gamneg` on negative slopes (`swancom2.ftn:3530–3538`) |
| `RUESSINK` | 3 | `alpha=1.0`, `a=0.76`, `b=0.29` | γ = a·kₚd + b, clipped to [0.3, 1.2] (`:3567–3570`) |
| `TG` | 4 | `alpha=1.0`, `gamma=0.42`, `pown=4.0` | Thornton & Guza (1983) Rayleigh-weighted dissipation (`:2499–2505`) |
| `BKD` | 6 | `alpha=1.0`, `gamma0=0.54`, `a1=7.59`, `a2=−8.06`, `a3=8.09` (`PSURF(1,4,5,6,7)`), `[npnts]=95` → `PNUMS(37)` (undocumented) | Salmon et al. (2015) β–kd breaker index: `γ = (γ0 + a1·β) / tanh((γ0+a1β)/(a2+a3·k̃d))` with |β| the local bottom slope (limited to ≤ 1:10) and k̃ the WAM mean wavenumber (`swancom2.ftn:3573–3610`). `BKD` automatically switches on `DIRECTIONALITY` (`IF (KEYWIS('DIR').OR.ISURF.EQ.6)`, `swanpre1.ftn:2727`). During iteration the index is modified until `npnts` % of points converged (`MODGAM`, `swancom1.ftn:2376`) |
| `ASYM` | 7 | `alpha=1.0`, `gamma0=0.6`, `a=0.8` (tag 41.97, **not in swanuse 41.51**) | breaker index tied to wave asymmetry/biphase (needs triads with biphase) |
| `DIRECTIONALITY [spread]` | `IDISRF=1`, `PSURF(15)=12.5°` | reduces dissipation for directionally spread seas: `KTETA = max(1, DSPR/spread)` (`swancom2.ftn:3693`) |
| `FREQDEP [power] [fmin] [fmax]` | `IFRSRF=1`, `PSURF(16..18)=2.0, 0, 1000` | frequency-dependent (f^power) distribution of the breaking dissipation instead of proportional to E(σ,θ) |

`JGAMMA` storage (`BKD`, `ASYM`) adds a column to `COMPDA`. **[DISCREPANCY]** swanuse 41.51 documents only `CONSTANT` and `BKD`; `VARIABLE`, `RUESSINK`, `TG`, `ASYM`, `DIR`, `FREQDEP` are parsed but undocumented. The COAWST examples use `BREAKING CONSTANT 1.0 0.73`.

---

## 9. `FRICTION`

```
FRICtion  JONswap CONstant [cfjon] | JONswap VARiable [cfj1] [cfj2] [dsp1] [dsp2]
        | COLLins [cfw] [cfc] | MADsen [kn] | RIPples [S] [D]                        (swanpre1.ftn:2853–2893)
```

Bottom friction is **off by default** (`IBOT=0`, `swanmain.ftn:2373`). Giving `FRICTION` with no keyword → JONSWAP CONSTANT.

| option | `IBOT` | parameter | default | formula (`SBOT`, `swancom2.ftn:233–500`) |
|---|---|---|---|---|
| `JONSWAP CONSTANT` | 1 | `[cfjon]`→`PBOT(3)` (`UNC`) | 0.038 m²s⁻³ (`swanmain.ftn:2669`, changed from 0.067 at 41.49) | `S_bf = −(cfjon/g²)·σ²/sinh²(kd)·E`; **ignores any spatially varying friction grid** |
| `JONSWAP VARIABLE` | 4 | `PBOT(6..9)` = 0.038, 0.067, 10°, 30° | | cfjon varies linearly with per-frequency directional spread between `dsp1` and `dsp2` (undocumented) |
| `COLLINS` | 2 | `[cfw]`→`PBOT(2)`, `[cfc]`→`PBOT(1)` | 0.015, 0 | `S_bf ∝ cfw·U_rms,bot/g`; uses `FRCOEF` if `VARFR` |
| `MADSEN` | 3 | `[kn]`→`PBOT(5)` (`UNC`) | 0.05 m (`:2671`); `PBOT(4)=−0.08` fixed | Madsen et al. (1988) friction factor from Jonsson's implicit relation with A_b/kn (Newton iteration), `fw=0.3` for A_b/kn ≤ 1.57; uses `FRCOEF` as kn if `VARFR`. **Used by all COAWST examples (`FRICTION MADSEN 0.05`) and the only law that interprets the ROMS `ZO` import physically** (see §3) |
| `RIPPLES` | 5 | `[S]`→`PBOT(6)`, `[D]`→`PBOT(7)` | 2.65, 0.0001 m (`:2672–2673`, tag 41.51) | Smith et al. (2011): Shields/mobility-number ripple geometry → Nikuradse kn → Swart friction factor; allocates `JFRC2` to carry fw between iterations/time steps. Note `PBOT(6),(7)` are shared with JONSWAP VARIABLE |

---

## 10. `TRIAD`

```
TRIad  DCTA [trfac] [p] COLL|NONC (default)
     | LTA  [trfac] [cutfr] [dint]
     | FTIM [trfac] [dint]
     | SPB  [trfac] [a] [b] [dint]
     | [itriad] [trfac] [cutfr] [dint] [a] [b] [p] [urcrit] [urslim] [ic]      (obsolete form)
       ( BIPHase ELDeberky [urcrit] | SAPRykina [a] | DEWIT [lpar] )
       ( TRAnsfer FG | MS | BRedmose | QUadwave )                                   (swanpre1.ftn:3723–3870)
```

Triads are **off by default** (`ITRIAD=0`). The bare word `TRIAD` selects DCTA (`ITRIAD=5`).

| option | `ITRIAD` | parameters (`STA` defaults) | physics |
|---|---|---|---|
| `DCTA` | 5 | `trfac=4.4` (`PTRIAD(1)`), `p=4/3` (`PTRIAD(2)`), `COLL` (collinear only, `TCOLL=.TRUE.`) or `NONC` | Booij et al. (2009) distributed collinear triad approximation; `p` shapes the high-frequency tail |
| `LTA` | 1 | `trfac=1.0`, `cutfr=−1` (= no cut-off; `−1` means `ISMAX=MSC`, `swancom4.ftn:3956`), `dint=60°` (`PTRIAD(8)`; directional integration width, `−1` = none) | Eldeberky (1996) lumped triad approximation, extended version (41.01+) |
| `FTIM` | 3 | `trfac=1.0`, `dint=−1` | full triad interaction model |
| `SPB` | 2 | `trfac=0.90`, `a=0.95` (`PTRIAD(6)`), `b=0.0` (`PTRIAD(7)`), `dint=−1` | Becq-Girard et al. (1999) with relaxed resonance `K = a·k_loc + b` |
| obsolete `[itriad]` | 1,2,3,5,11 | 11 = original LTA (`trfac=0.05`, `cutfr=2.5`); also reads `urcrit=0.63` (`PTRIAD(4)`), `urslim=0.1` (`PTRIAD(5)`), `ic` (`PTRIAD(10)`) | |
| `BIPHASE` | `IBIPH` | ELDEBERKY (1, `urcrit=0.63`), SAPRYKINA (2, `a=1.0`), DEWIT (3, `lpar=0`) | biphase β = −π/2 + π/2·tanh(urcrit/Ur) (Eldeberky); De Wit (2022) slope/period based |
| `TRANSFER` | `PTRIAD(10)` | FG=1, MS=2, BREDMOSE=3, QUADWAVE=4; if unset ERRCHK chooses MS for SPB/old-LTA and QUADWAVE (Akrish et al. 2024) otherwise (`swanmain.ftn:8024–8036`) | interaction coefficient for shoaling waves |

Triads are active only where the Ursell number ≥ `urslim` (`PTRIAD(5)`, `swancom4.ftn:3960, 4306`). **[DISCREPANCY]** The SWINIT default of `PTRIAD(1)` is 1.0 and `PTRIAD(2)` is 2.5 (`swanmain.ftn:2709–2710`) but every parser branch re-assigns them with `STA`, so the effective defaults are those in the table; `swmod1.ftn` comments still list `trfac=0.65`, `urslim=0.01` (stale). The stopping criterion `[dabs]` becomes 0.01 instead of 0.005 when FTIM is used (`swanmain.ftn:8010–8016`). The `TRIAD … [ic]`/`TRANSFER` and `DEWIT` options are 42.x features present in the code; swanuse 41.51 documents `DCTA/LTA/FTIM/SPB`, `BIPHASE ELDEBERKY/DEWIT` and `TRANSFER` already.

---

## 11. Vegetation: `VEGETATION` and `VEGCOAWST`

```
VEGEtation [iveg] < [height] [diamtr] [nstems] [drag] >                       (swanpre1.ftn:2981–3040)
VEGCoawst  < [height] [diamtr] [nstems] [drag] [youngsmod] >                   (COAWST only; :3049–3118)
INPGRID NPLANTS ... / READINP NPLANTS     (spatially varying stem density; VARNPL)
INPGRID NPHT|NPDA|NPTK ...                (SWAN_MODEL only: plant height, diameter, thickness)
```

* `VEGETATION`: `IVEG=iveg` (default 1); repeat groups define vertical layers (`LAYH, VEGDIL, VEGNSL, VEGDRL`); layers > 1 only allowed for `iveg=1`. `iveg=1` Dalrymple (1984)/Suzuki et al. (2011) frequency-independent damping (`SVEG`, `swancom2.ftn:852`); `iveg=2` Jacobsen et al. (2019) frequency-dependent canopy model (`:934`), no vertical layering, no current effects (ERRCHK warning `swanmain.ftn:8040–8046`). `nstems` is multiplied by the `NPLANTS` grid if present.
* `VEGCOAWST` (COAWST): same four parameters plus a required Young's modulus `[youngsmod]` (`VEGYML`), and sets **`IVEG = 2`** (`swanpre1.ftn:3050`).
* Dispatch in `SWCOMP` (`swancom1.ftn:7821–7849`): under `SWAN_MODEL`, `IVEG=1` or `2` → `SVEG` (Dalrymple or Jacobsen); `IVEG=3` → `SVEG_COAWST` (`swancom2.ftn:1041–1401`), which uses the ROMS-supplied spatially varying height/diameter/thickness/density (`NPHT2, NPDA2, NPTK2, NPLA2`), computes a flexible-blade effective length via the Cauchy number (Luhar & Nepf 2016), a KC-number-based drag (`VEGDRL(1)=2` → Mendez & Losada 2004 Cd; `=1` → Cd=1; emergent case Cd=1.95), and exports the drag coefficient `CDVEG_COAWST` (`DICDVG`) and dissipation `DISVEG` to ROMS (`waves_coupler.ftn:1127–1134`, with `VEG_STREAMING`).
* **[INCONSISTENCY in source]** `VEGCOAWST` sets `IVEG=2`, which routes to the standard Jacobsen `SVEG`, *not* to `SVEG_COAWST`; `SVEG_COAWST` is reached only with `VEGETATION 3 …`, but then `VEGYML` (only allocated by `VEGCOAWST`) is used uninitialised at `swancom2.ftn:1317`. The print-out also labels `IVEG=3` as "Dalrymple" (`swancom1.ftn:4287–4289`). To use the COAWST flexible-vegetation routine both commands apparently have to be present (`VEGC` first to allocate `VEGYML`, then `VEGE 3 …`); the COAWST manual (§4.3.9, §6.21 Veg_test) only says to use "`NPLANTS` and `VEGETATION`". Treat `VEGCOAWST` as experimental.
* `VEG_SWAN_COUPLING` adds `VEGDENS, VEGHGHT, VEGDIAM, VEGTHCK` to the ocean→wave exchange (`waves_coupler.ftn:699–718`).

---

## 12. Other dissipation/scattering terms

| command | syntax / defaults (source) | notes |
|---|---|---|
| `MUD [layer] [rhom] [viscm] [rhow] [viscw]` (`swanpre1.ftn:2895–2905`) | `IMUD=1`; `PMUD` = 0, 1300 kg/m³, 0.0076 m²/s, RHO, 1.3e-6 (`swanmain.ftn:2678–2682`); layer may vary via `INPGRID MUDL` | Ng (2000) two-layer viscous mud dissipation; modifies the dispersion relation (`SWAPAR`) |
| `TURBulence [ctb] (CURrent [tbcur])` (`:3121–3150`) | `ITURBV=1`, `ctb=0.01`, `tbcur=0.004` (viscosity = tbcur·d·|U|) or from `INPGRID TURB` | Tolman-type turbulent-viscosity dissipation (`STURBV`) |
| `ICE [aice] [hice]`, `SICE R19 [c0..c6] | D15 [Chf] | M18 [Chf] | R21B [Chf] [npf]`, `IC4M2 …` (`:2914–2978`) | `IICE=3..6`; R19 defaults c2=1.06e-3, c4=2.3e-2 | sea-ice dissipation; not relevant for reefs |
| `BRAGg [ibrag] [nreg] [cutoff] FT | FILE 'fname' [idla] [mkx] [mky] [dkx] [dky]` (`:3875–3972`) | `IBRAG=1`, `cutoff=5` (`PBRAG(2)`), regular bottom grid required | Ardhuin & Herbers (2002) Bragg scattering by small-scale bathymetry; stiff — needs small Δt or under-relaxation |
| `SCAT [iqcm] (GRID WIDth [rfac] | Kxy …) (TRUnc [alpha] [qmax])` (`:3975–4028`) | `IQCM=1`, `PSCAT(1)=1`, `PSCAT(2)=99999`, `PSCAT(7)=1` | quasi-coherent scattering (Smit & Janssen); incompatible with diffraction, breaking, triads (research) |
| `SURFBeat [df] [nmax] [emin] UNIForm|LOGarithmic` (`:2434–2468`) | `df=0.01`, `nmax=50000`, `emin=0.05`; regular grids, 2D, stationary two-`COMPUTE` workflow only | infragravity energy module (Reniers & Zijlema 2022) — stationary only, not usable in coupled nonstationary runs |
| `OBSTACLE FIG [alpha1] [hss] [tss] [dss] [dd] [minfr] [shape]` (`:1174–1200`) | free-infragravity radiation from shorelines (Ardhuin et al. 2014) | `[minfr] [shape]` tagged 42.09, undocumented in 41.51 |

---

## 13. `LIMITER`

```
LIMiter [ursell] [qb]            (swanpre1.ftn:2203–2208; both UNC)
```
`[ursell]`→`PTRIAD(3)` default 10 (`swanmain.ftn:2711`): quadruplets (and therefore the action limiter) are switched off where Ur > ursell. `[qb]`→`PNUMS(28)` default 1.0 (`:2553`): the action limiter is not applied to *decreasing* action where the fraction of breaking waves Qb exceeds this value (so by default it is never relaxed; setting e.g. 0.3 lets breaking reduce energy faster in the surf zone).

---

## 14. `OBSTACLE`

```
OBSTacle  TRANSm [trcoef] | TRANS1D <[trcoef]> | TRANS2D <[trcoef]> | DAM GODA [hgt] [alpha] [beta] | DAM DANGremond [hgt] [slope] [Bk]
          ( FIG ... )  ( REFLec [reflc] RSPEC | RDIFF [pown] )  ( FREEboard [hgt] [gammat] [gammar] QUAY )  LINe < [xp] [yp] >
                                                                                                (swanpre1.ftn:1021–1360)
```
Not allowed in 1D. Defaults: `trcoef=0` (`TRANS`), `GODA alpha=2.6, beta=0.15` (`:1157–1158`), `reflc=1` if `REFL` given, `pown=1`, `gammat=gammar=1`. `TRANS1D` requires `msc+1` values, `TRANS2D` `(msc+1)·mdc`. Reflections need `CIRCLE`. Obstacles are sub-grid transmission/reflection lines between neighbouring grid points; see swanuse 41.51 §4.5.4 for placement rules. Obstacle handling is per computational face (`SwanCrossObstacle`, `swancom*`), unchanged by COAWST.

---

## 15. `SETUP`

```
SETUP [supcor]                   (swanpre1.ftn:2384–2412)
```
`LSETUP=1`, `PSETUP(2)=supcor` (level correction, default 0). Wave-induced set-up computed from radiation-stress gradients with a SOR solver (`NUM SETUP [eps2=1e-6] [outp=0] [niter=1000]`, `PNUMS(23..25)`). **Fatal in parallel 2-D runs** (`MSGERR 4 'setup is not supported in parallel run'`, `:2388–2391`), not supported on unstructured grids, incorrect with spherical coordinates. In COAWST the set-up is produced by ROMS (radiation stress / vortex force via `WEC_VF`), and SWAN is run under MPI, so `SETUP` must not be used in coupled runs.

---

## 16. `DIFFRACTION`

```
DIFFRac [idiffr] [smpar] [smnum] [cgmod]           (swanpre1.ftn:2416–2423)
```
`IDIFFR=1` (default when the command is given), `PDIFFR(1)=smpar=0` (smoothing weight a), `PDIFFR(2)=smnum=0` (number of smoothing passes), `PDIFFR(3)=cgmod=1` (modify propagation velocities). Phase-decoupled refraction–diffraction (Holthuijsen et al. 2003). Convergence requires under-relaxation `NUM STAT [alfa]≈0.01` — which is only meaningful in stationary mode (`PNUMS(30)` is zeroed by `MODE NONSTAT`) — or smoothing (not on unstructured grids). Disabled automatically with `GEN4`/`SCAT`.

---

## 17. `OFF`

```
OFF  WINDGrowth | QUADrupl | WCAPping | BREaking | REFrac | FSHift | BNDCHK | RESCALE | SOURCES     (swanpre1.ftn:4032–4060)
```
`WINDG`→`IWIND=0`; `QUAD`→`IQUAD=0` (and the limiter is then switched off in ERRCHK); `WCAP`→`IWCAP=0`; `BRE`→`ISURF=0`; `REF`→`IREFR=0` (no θ-transport); `FSH`→`ITFRE=0` (no σ-transport, i.e. no current-induced frequency shifting); `BNDCHK`→ no Hs boundary check (useful in nonstationary runs to suppress warnings); undocumented `RESCALE`→`BRESCL=.FALSE.` (no rescaling of the solution after the limiter), `SOURCES`→ all source terms off (propagation only). COAWST examples use `OFF QUAD`.

---

## 18. `PROP` — propagation schemes

```
PROP  BSBT | GSE [waveage] SEC|MIN|HR|DAY     ( FLUXLIM )            (swanpre1.ftn:825–847)
```

Scheme variables: `PROPSS` (stationary), `PROPSN` (nonstationary), `PROPSC` (chosen at run time). SWINIT defaults `PROPSS=2`, `PROPSN=3` (`swanmain.ftn:2452–2453`) and ERRCHK sets `PROPSC = PROPSN` if `NSTATC=1` else `PROPSS` (`:7860–7864`).

| scheme | `PROPSC` | when allowed | description |
|---|---|---|---|
| BSBT | 1 | both modes; `PROP BSBT` sets `PROPSN=PROPSS=1` | first-order backward-space/backward-time upwind implicit scheme; unconditionally stable, diffusive, cheapest, most robust on curvilinear grids with sharp metric changes. **All COAWST examples use `PROP BSBT`.** |
| SORDUP | 2 | **stationary only** — `MSGERR 3 'SORDUP scheme only in stationary run'` if used nonstationary (`:8143–8145`) | second-order upwind (Rogers et al. 2002), default for stationary runs; fully implemented on curvilinear grids |
| S&L (Stelling & Leendertse) | 3 | **nonstationary only** — `MSGERR 3 'S&L scheme not in stationary run'` (`:8146–8148`); default in nonstationary mode | second-order in space and time (three time levels: requires `AC1`, allocated when `NSTATM=1 .AND. MXITNS>1 .OR. PROPSC=3`, `swanmain.ftn:478`); less diffusive, better swell propagation; warning that it is *not fully implemented* for curvilinear grids (`:8151–8160`); garden-sprinkler diffusion only works with S&L |
| `GSE [waveage]` | — | only with S&L (`PROPSN=3`) or unstructured (`OPTG=5`), else error (`swanpre1.ftn:831–834`) | adds diffusion scaled by wave age to counteract the garden-sprinkler effect; `WAVAGE` default 0 (none); conditionally stable |
| `FLUXLIM` | `PROPFL=1`, `PNUMS(6)=0` | undocumented | flux-limited θ-scheme |

Unstructured grids always use a first-order vertex-based upwind scheme (`SwanCompUnstruc`). Nonstationary mode therefore **forces S&L unless `PROP BSBT` is given**; a `REPEATING` x-direction needs `MXC ≥ 3` with S&L.

---

## 19. `NUMERIC`

```
NUMeric ( STOPC [dabs] [drel] [curvat] [npnts] [dtabs] [curvt] | ACCUR [drel] [dhoval] [dtoval] [npnts] )
        ( STAT [mxitst] [alfa] | NONSTAT [mxitns] | ITERMX [mxitst] )  [limiter]
        ( DIRimpl [cdd] [cdlim] DEP|WNUM )  ( REFRLim [frlim] [power] )
        ( SIGIMpl [css] [eps1] [eps2] [outp] [niter] | SIGEXpl [css] [cfl] | FIL [diffc] )
        ( CTheta [cfl] )  ( CSigma [cfl] )  ( SETUP [eps2] [outp] [niter] )                     (swanpre1.ftn:2241–2375)
```

| item | variable | default | meaning |
|---|---|---|---|
| `STOPC` (default criterion, `PNUMS(21)=1`, `swanmain.ftn:2584`) | `dabs`→`PNUMS(2)`, `drel`→`PNUMS(1)`, `curvat`→`PNUMS(15)`, `npnts`→`PNUMS(4)`, `dtabs`→`PNUMS(3)`, `curvt`→`PNUMS(16)` | `dabs=−1` → resolved in ERRCHK to 0.005 m (0.01 with FTIM triads, 0.05 with QC) (`:8008–8020`); `drel=0.01`; `curvat=0.005`; `npnts=99.5 %`; `dtabs=1000` s, `curvt=1000` (i.e. Tm01 criteria inactive) | iteration stops when (|ΔHs|<dabs or ΔHs/Hs<drel and curvature<curvat) in ≥ npnts % of wet points (`SwanConvStopc.ftn90`) |
| `ACCUR` (old criterion, `PNUMS(21)=0`) | `drel`, `dhoval`→`PNUMS(15)`, `dtoval`→`PNUMS(16)`, `npnts` | obsolete; with `GEN4` it is overridden | |
| `STAT [mxitst] [alfa]` | `MXITST`, `PNUMS(30)` | 50 (`swanmain.ftn:2352`), 0.0 | max iterations (stationary); frequency-dependent under-relaxation (≈0.01 for diffraction). `alfa` is zeroed by `MODE NONSTAT` |
| `NONSTAT [mxitns]` | `MXITNS` | 1 (`:2353`) | max iterations *per time step*; the `DO 450 ITER=1,ITERMX` loop in `SWCOMP` (`swancom1.ftn:1494`) exits early when the stopping criterion is met (never on iteration 1 with STOPC) |
| `[limiter]` | `PNUMS(20)` | 0.1 (`:2549`) | max relative change of action per bin per iteration as a fraction of the Phillips level (Hersbach–Janssen limiter); set to 1e20 when `IQUAD=0` |
| `DIRIMPL [cdd] [cdlim] DEP|WNUM` | `PNUMS(6)`, `PNUMS(17)`, `PNUMS(32)` | `cdd=0.5` (`:2505`), `cdlim=−1` (no Ctheta limiter; 0 = refraction off), `WNUM` (`PNUMS(32)=1`: cθ from wavenumber gradients, since 41.07) | θ-space scheme: 0 central, 1 first-order upwind; ERRCHK recommends `cdd=1` with currents (`swanmain.ftn:7988–7999`) |
| `REFRLIM [frlim] [power]` | `PNUMS(29)=1`, `PNUMS(26)=0.2`, `PNUMS(27)=2` | undocumented | frequency-dependent limitation of refraction below `frlim` Hz |
| `SIGIMPL [css] [eps1] [eps2] [outp] [niter]` | `PNUMS(8)=1`, `PNUMS(7)=0.5`, `PNUMS(11)`, `PNUMS(12)=1e-4`, `PNUMS(13)=0`, `PNUMS(14)=20` | implicit (SIP solver) σ-transport, the default (`PNUMS(8)=-999`→1 in ERRCHK, `:7976–7980`) | `css` 0 central / 1 upwind; recommended 1 with currents |
| `SIGEXPL [css] [cfl]` | `PNUMS(8)=2`, `PNUMS(19)=0.5√2` | explicit σ-scheme with CFL removal | undocumented |
| `FIL [diffc]` | `PNUMS(8)=3`, `PNUMS(9)=0.01` | explicit with diffusion filter | undocumented |
| `CTHETA [cfl]` | `PNUMS(35)=1`, `PNUMS(36)=0.9` | off unless given | limits the refraction turning rate cθ by a CFL number — recommended for coarse/steep bathymetry (reef walls) |
| `CSIGMA [cfl]` | `PNUMS(33)=1`, `PNUMS(34)=0.9` | off unless given | limits the frequency-shift rate cσ (strong current gradients) |
| `SETUP [eps2] [outp] [niter]` | `PNUMS(23)=1e-6`, `(24)=0`, `(25)=1000` | SOR solver for set-up | |

Stationary and nonstationary iteration counts can also be given with the obsolete `ITERMX` keyword (sets both). The Froude limiter `PNUMS(18)` is set via `SET [froudmax]`.

---

## 20. `COMPUTE` and the nonstationary time step

```
COMPute  STATionary [time]  |  NONSTationary [tbegc] [deltc] SEC|MIN|HR|DAY [tendc]          (swanpre1.ftn:928–1010)
```

* Stationary: `NSTATC=0`, `DT=1e10`, `MTC=1`, `ITERMX=MXITST`.
* Nonstationary: `NSTATC=1`, `DT=deltc`, `MTC = NINT((tendc−tbegc)/DT)` (warning if not an integer number of steps), `ITERMX=MXITNS`, `RDTIM=1/DT` (used in the time-derivative term of the implicit sweep). Up to 300 `COMPUTE` commands are stored in `RCOMPT` (`:988–995`). Successive `COMPUTE STAT` with times give a quasi-stationary series.
* Time stepping is fully implicit (four-sweep Gauss–Seidel per iteration); there is no CFL restriction on Δt for stability, only accuracy and the source-term splitting error. With the default `MXITNS=1` each time step performs one sweep-set with the action limiter controlling the source-term growth, so the solution lags the forcing; `NUM NONSTAT [mxitns]` > 1 iterates to convergence within the step (and allocates `AC1`).
* **COAWST driver** (`waves_control.ftn:297–382`): grids are advanced one `DT_G(ng)` at a time; after each parent step the MCT exchange `SWAN_CPL` is called and exports/imports actually happen only when `MOD(iics(1), nWAV2OCN) == 0` (`swanmain.ftn:1012–1027, 1036–1041`), where `nWAV2OCN = TI_WAV2OCN/DT` is set from the coupling interval in `coupling.in`. Hence **the coupling interval must be an integer multiple of the SWAN parent `deltc`**, and child grids must use `DT_child = DT_parent/n`. Time-varying boundary spectra for child grids are interpolated between the two parent time levels (`swanmain.ftn:8870–8890`). Water level/current updates from ROMS are therefore piecewise constant in time between exchanges.
* Output/export fields are computed by `SWOUTO` at coupling times with the standard output machinery (`IVTYPE` codes), so `SET INRHOG` and `QUANTITY` settings affect exported values.

---

## 21. What the coupling exchanges (`waves_coupler.ftn`)

**SWAN → ROMS** (`wav2ocn_AV`, `waves_coupler.ftn:448–630`; `IVTYPE` mapping at `:1068–1140`): `DISBOT` (bottom-friction dissipation, IVTYPE 54), `DISSURF` (depth-induced breaking dissipation, 55), `DISWCAP` (whitecapping dissipation, 56), `HSIGN` (10), `RTP` (relative peak period, 12), `TMBOT` (near-bottom period, 50), `UBOT` (rms bottom orbital velocity, 6), `DIRE/DIRN` (sin/cos of mean direction, 13), `DIREP/DIRNP` (peak direction, 14), `WLEN` (mean wavelength, 17), `WLENP` (peak wavelength, 71), `QB` (fraction breaking, 8), `WDSPR` (directional spread, 16), `WQP` (peakedness, 58); optionally `DISVEG`, `DICDVG` (vegetation, with `VEG_STREAMING`), `KS01..`, `US01..`, `VS01..` per-frequency Stokes spectra (`SPECTRUM_STOKES`, IVTYPE 202), and partition fields `HsPT01/02, TpPT01/02, WlPT01/02, DrE/NPT01/02` (`WAVE_PARTITION`). Dissipation units follow `INRHOG` (m²/s or W/m²); ROMS divides by `rho0` (`Master/mct_roms_swan.h`).

**ROMS → SWAN** (`ocn2wav_AV`, `:649–730`): `DEPTH` (used only with `SED_MORPH`), `WLEV`, `VELX`, `VELY` (or `VELX01..VELXnn`, `VELY..` per frequency bin with `UV_BANIHASHEMI`, which also enlarges `COMPDA` by `2·MSC` columns, `swanpre1.ftn:1432–1440`, and passes per-bin currents into the propagation velocities `SPROXY/SPROSD`, `swancom1.ftn:3360–3420`), `ZO` (bottom roughness → friction array, see §3), and `VEGDENS, VEGHGHT, VEGDIAM, VEGTHCK` with `VEG_SWAN_COUPLING`. The choice of surface-current definition sent by ROMS (`UV_KIRBY`, `UV_BANIHASHEMI`, `UV_CONST`, default surface/depth-averaged current) is a ROMS-side cpp option (COAWST manual §4.3.2).

**SWAN ↔ WRF** (`:744–810`): imports `U10, V10` into the wind arrays `JWX2/JWY2` (`:2716–2720`) and exports `HSIGN, WLENP, DIREP, DIRNP, RTP, Z0_WAV, CPL_MASK`. Roughness formulas `COARE_*`, `DRENNAN`, `Z0_WAV_SIN` (SWAN only with JANSSEN wind), `Z0_PORCHETTA` are selected on the WRF/ROMS side (COAWST manual §4.3.6).

---

## 22. Compile-time (cpp) options that change SWAN physics or numerics

The SWAN sources are pre-processed with the ROMS `cppdefs.h` (`swancpp.h`), so options come from the application header, not from `CMakeLists.txt` (which only sets compiler flags). Macros found in `SWAN/src` (count of occurrences in parentheses):

| macro | effect on SWAN |
|---|---|
| `SWAN_MODEL` (270) | enables the COAWST driver (`SWAN_INITIALIZE/RUN/CPL/RST/FINALIZE` instead of `PROGRAM SWAN`), per-grid module storage, `NSGRIDS`, `RESTART`, extra `COMPDA` columns (`JPBOT, JDSXB, JDSXS, JDSXW, JNPLA2/3, JDSXV, JTURB2/3, JNPHT2/3, JNPDA2/3, JNPTK2/3, JDSXC`, `swanmain.ftn:2825–2860`), `INPGRID NPHT/NPDA/NPTK`, the `SVEG_COAWST` path, `JCDRAG` allocation in `GEN3`, and **disables file reading of nonstationary current/level/friction grids** (`swanmain.ftn:9072, 9101, 9171`) |
| `COAWST_COUPLING` (35), `ROMS_COUPLING` (11), `WRF_COUPLING` (23), `WAVES_OCEAN` (7), `AIR_WAVES` (4), `MCT_INTERP_WV2AT` (14) | activate MCT initialisation and exchange; `AIR_WAVES` suppresses wind-file reading (`:9027`) |
| `NESTING` (35) | parent→child spectral boundary interpolation in time (`SNEXTI`), `AC2_parent` storage, nested time stepping in `waves_control.ftn` |
| `UV_BANIHASHEMI` (21) | per-frequency effective currents from ROMS (Banihashemi et al. 2017) used in `SPROXY/SPROSD` propagation velocities; adds `2·MSC` columns to `COMPDA` |
| `SPECTRUM_STOKES` (29) | computes and exports per-frequency Stokes-drift spectra (output quantity `SSPEC`, IVTYPE 202, `swanmain.ftn:4867–4878`; `swanout1.ftn`) |
| `VEGETATION` + `VEG_SWAN_COUPLING` (+`VEG_STREAMING`) (10) | exchange of vegetation properties and dissipation/drag with ROMS |
| `WAVE_PARTITION` (4) | exports two spectral partitions (`SwanSpectPart.ftn`) |
| `SED_MORPH` (2) | SWAN bathymetry updated from ROMS each exchange (`waves_coupler.ftn:2153–2173, 2235`) |
| `BBL_MODEL` (2) | ROMS `ZO` inserted into the friction array (`:2220–2230`); otherwise constant |
| `DRAGLIM_DAVIS` (1) | caps the Wu drag coefficient at 2.4e-3 (`swancom3.ftn:1005`) |
| `SWAN_NS_PERIODIC` (3) | COAWST-only periodic north–south (and west–east) exchange of boundary action densities across MPI tiles (`swanmain.ftn:8523–8600`) |
| `SWAN_SINGLESPEC` (5) | single 2-D spectrum output file in MPI runs (`swanpre2.ftn:2296`), output only |
| `WAV2ATM_FLUXES`, `ASSUMED_SHAPE`, `WRF_MODEL` | build/plumbing only |

`CMakeLists.txt` sets `SWITCHES -dos -cvis` and `-O2` Intel flags only; no physics options. The MPI build (`swanparll.ftn`) is standard SWAN; OpenMP directives are present in `swancom1.ftn`.

---

## 23. Summary of manual-versus-source discrepancies

1. Version: code says 41.51 but contains 42.0x–43.0x features (`ASYM` breaking, `WCAP AB CURRENT`, `TRIAD … IC/TRANSFER`, `DEWIT` biphase, `OBST FIG [dss] [minfr] [shape]`, `SET [excmark]`).
2. `COORD SPHE`: parser default projection is CCM, SWINIT's is QC; CCM wins when `SPHE` is given (matches swanuse 41.51).
3. `DRAGLIM_DAVIS`: COAWST manual says 2.85e-3, code caps at 2.4e-3.
4. `VEGCOAWST`: sets `IVEG=2` (Jacobsen) although the COAWST routine is wired to `IVEG=3`; `VEGYML` only allocated by `VEGC`.
5. `INPGRID NPHT` and `INPGRID DSS` both map to `IGRD=18` in the SWAN_MODEL build.
6. COAWST manual §5.3.7 / §10 imply currents/levels come from ROMS automatically; in fact `INPGRID CURRENT/WLEV/FRIC … NONSTAT` lines (without `READINP`) are required for the coupled fields to be applied (depth update, Froude limiter, `ICUR=1`).
7. `swmod1.ftn` comment defaults for `PTRIAD(1)=0.65`, `PTRIAD(5)=0.01`, `PNUMS(1)=0.02`, `PNUMS(4)=98` are stale; the executable defaults are those in §10 and §19.
8. `BREAKING`: manual documents only `CONSTANT` and `BKD`; the parser also accepts `VARIABLE/NELSON`, `RUESSINK`, `TG`, `ASYM`, `DIRECTIONALITY`, `FREQDEP`.
9. `WCAP KOMEN` with currents: COAWST forces `IQUAD=3` when `ICUR≠0` (standard SWAN only warns).
10. `FRICTION JONSWAP` ignores spatially varying friction (`FRCOEF`), so the ROMS `ZO` import has no effect with JONSWAP; the COAWST manual does not mention this.

---

## 24. Notes relevant to reef applications

(Steep forereef, breaking on a reef crest ~0.5 m deep, propagation across a lagoon with currents; nonstationary ROMS–SWAN coupling.)

**Options that matter most**

* **Depth-induced breaking (§8).** The default `BREAKING CONSTANT 1.0 0.73` applies a flat-bottom γ. On a steep forereef (slopes 1:5–1:20) the β–kd index `BREAKING BKD 1.0 0.54 7.59 -8.06 8.09` (Salmon et al. 2015) raises γ with slope and kd and lowers it on the flat reef top, and automatically includes the directional-spread correction; it is the best-founded choice in this code base. `TG` (Thornton–Guza) is an alternative for random breaking on a reef flat; `VARIABLE/NELSON` is slope-aware but tuned for beaches. With a 0.5 m deep crest, `SET DEPMIN` (COAWST uses 0.10 m) and ROMS wetting/drying thresholds should be consistent; depths below `DEPMIN` are clipped, not dried, on the SWAN side.
* **Bottom friction (§9).** Rough coral requires `FRICTION MADSEN [kn]` with kn of O(0.1–0.5 m); in coupled runs with `BBL_MODEL` the ROMS roughness `ZO` overrides `[kn]` point by point (as `max(ZO, kn)`), so the reef roughness must be set in ROMS. `JONSWAP` cannot take spatial roughness; `COLLINS` would misinterpret the imported roughness length.
* **Triads (§10).** Harmonic generation over the reef crest and lagoon needs `TRIAD` (default DCTA, `trfac=4.4`, `p=4/3`); for narrow reef flats the collinear DCTA with the default Eldeberky biphase (`urcrit=0.63`) is standard. Triads switch on only where Ur ≥ `urslim` (0.1).
* **Quadruplets and limiter (§7, §13).** `GEN3` + DIA quadruplets are not needed inside the lagoon; most COAWST reef/inlet set-ups use `OFF QUAD`, which also disables the action limiter (re-enable with `NUM … [limiter]` if source terms become unstable). If quadruplets are kept, COAWST forces `IQUAD=3` whenever currents are present (more memory). `LIMITER [ursell]` (default 10) already turns them off in the surf zone.
* **Currents in the lagoon (§3, §19).** Supply `INPGRID CURRENT … NONSTAT` and `INPGRID WLEV … NONSTAT` (no `READINP`) so ROMS currents and water levels are actually applied; the Froude limiter `SET … [froudmax]=0.8` caps supercritical currents over the crest. Use `NUM DIRIMPL 1 SIGIMPL 1` (full upwind in θ and σ) as ERRCHK recommends with currents, and `NUM CTHETA 0.9` (and `CSIGMA 0.9`) to prevent spurious refraction/frequency shifting at the reef wall where depth gradients are resolved by few cells. Consider `UV_BANIHASHEMI` for depth-sheared lagoon flows.
* **Propagation scheme (§18).** `PROP BSBT` is the robust choice on curvilinear reef grids (S&L is "not fully implemented" for curvilinear grids and can be unstable with `GSE`); it is what every COAWST example uses. The directional resolution (`CGRID … CIRCLE 36`) controls numerical diffusion; 10° or finer is advisable for refraction over a steep forereef. Keep `df/f≈0.1` and a `fhigh` ≥ 1 Hz so that triad harmonics on the reef flat are resolved.
* **Units (§1.2).** Use `SET … INRHOG 1 NAUTICAL` so that `DISSURF/DISBOT/DISWCAP` reach ROMS in W/m²; ROMS divides by ρ₀. With `WEC_VF` + `WDISS_WAVEMOD` the breaking dissipation drives the ROMS set-up/currents, so the breaking parameterisation above directly controls the lagoon circulation.

**Known problems in nonstationary coupled mode**

* `SETUP` is fatal in MPI runs and must not be used; set-up comes from ROMS.
* `DIFFRACTION` relies on stationary under-relaxation (`[alfa]`, zeroed by `MODE NONSTAT`); in nonstationary mode it converges poorly and can produce noise near reef gaps.
* `MODE NONSTAT` with the default `NUM NONSTAT [mxitns]=1` means one iteration per Δt; the solution across the crest depends on Δt and the limiter. Use `mxitns` 2–3 or a Δt small compared with the reef crossing time when breaking is strong; the coupling interval must be a multiple of Δt.
* `SURFBEAT` (IG module), `GEN4/SCAT`, `BRAGG` and 1-D mode are stationary-only or non-parallel and are unavailable in coupled runs.
* Spatial friction and vegetation from ROMS are averaged over the coupling interval; water levels are piecewise-constant between exchanges, so a long `TI_OCN2WAV` relative to tidal change over a 0.5 m crest produces stepwise breaking behaviour.
* `VEGCOAWST` routing is inconsistent (`IVEG=2` vs `3`), and `INPGRID NPHT` clashes with `DSS` — avoid combining vegetation coupling with FIG/DSS options.
* `OFF BNDCHK` or a large `[hsrerr]` is usually needed to silence boundary-mismatch warnings in nonstationary runs (`MAXMES` can otherwise terminate the run).
