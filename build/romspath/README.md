# ROMSPath image

[ROMSPath](https://github.com/imcslatte/ROMSPath) (Hunter et al., 2022,
*Geosci. Model Dev.*) tracks particles offline in ROMS output: advection with
4th-order Runge-Kutta on the ROMS grid, vertical and horizontal turbulence,
behaviour, nested grids. This folder builds it into a small container image,
separate from the COAWST image: tracking runs one core per task and does not
need MPI, ROMS or SWAN.

## Where the source comes from

The image is built from the fork
[NicJeffress/ROMSPath](https://github.com/NicJeffress/ROMSPath) at the commit
pinned in the [Dockerfile](Dockerfile) (`ROMSPATH_REF`). The fork is upstream
ROMSPath at commit `6072ee9` (master, 2025-12-10) plus one commit per change:

| Commit | What it changes | Seen in the channel test |
|---|---|---|
| Periodic boundaries, ROMS Stokes names, gfortran date format | `PeriodicBoundary_X` / `PeriodicBoundary_Y` in the `hydroparam` namelist with a wrap across the seam; Stokes drift read as `u_stokes` / `v_stokes` (ROMS's names); a date format gfortran accepts | starting point |
| Periodic wrap by the ROMS period | a ROMS periodic grid repeats every Lm = xi_rho - 2 points; the wrap used xi_rho - 3, so each crossing moved a particle one cell; interpolation stencils now wrap too | yes |
| Position to grid index on Cartesian curvilinear grids | for `spherical = 0`, release positions were converted to grid indices as if grid lines ran along x and y | yes (rotated grid) |
| Record counter after the initial reads | from the third external step the hydro fields were one record behind the particle clock | yes, the largest error |
| RK4: fourth stage at X + k3 dt | was X + k3 dt/2 | no (uniform flow) |
| VTurb: set the smoothing-spline end weights | two weights were never set | no (no turbulence) |
| Per-particle CPU timers only with WriteModelTiming | seven system calls per particle and step; 29-43 % faster, same output | no (speed only) |
| First external step: records at their own times | the first step placed the three records one interval early | yes |
| RK4: evaluate the stages at their own times | all four stages used the velocities at the step start | yes |

Each commit message in the fork explains the bug and the change. The fork
exists so each change can be offered upstream as a pull request; the
engine builds from it until upstream has them.

**Licence.** Upstream ROMSPath has no licence file, so its code stays in the
fork (with its authors' rights) and is not copied into this repository. This
folder holds only the instructions to fetch and compile it.

## Building

```bash
build/romspath/build.sh                       # the pinned commit, from GitHub
build/romspath/build.sh --source ~/ROMSPath   # a local checkout (to try changes)
build/romspath/build.sh -- --build-arg ROMSPATH_REF=<sha>
```

The image is `coawst-romspath:latest` (about 200 MB). The makefile's debug
flags `-g -O0` are replaced by `-O3 -march=x86-64-v3` (`OPT_FLAGS`): 3-4 times
faster, and x86-64-v3 (AVX2) runs on every current x86 cloud machine, whatever
CPU built the image. `/opt/romspath/PROVENANCE` records the source commit and
the flags.

## Running

```bash
docker run --rm -u $(id -u):$(id -g) -v $PWD:/run coawst-romspath ROMSPath.exe ROMSPath.data
```

with `ROMSPath.data`, the particle seed file and the ROMS output in the current
folder (paths in `ROMSPath.data` relative to it). ROMSPath needs ROMS output
with u, v, w, zeta, AKs (with vertical turbulence), salt and temp (with
`SaltTempOn`) and, when built with `-DSTOKES` as here, `u_stokes` and
`v_stokes`; averages files usually suit it better than history files.

For a periodic grid (`EW_PERIODIC` in ROMS) set `PeriodicBoundary_X = .TRUE.`
in the `hydroparam` group (`PeriodicBoundary_Y` for `NS_PERIODIC`).

## Test

[`tests/romspath/periodic-channel`](../../tests/romspath/periodic-channel/README.md):
every commit of the fork, and the image, on a periodic channel whose exact
answer is known, with straight and rotated grid lines. About a minute.
