# Build settings: compiler flags and SWAN_SINGLESPEC

| | |
|---|---|
| **Type** | improvement (Dockerfile settings, not a source patch) |
| **Changes results?** | speed: the coupled idealized reef runs 1.7x faster; results within 6e-5 (relative) of COAWST's flags after 1 h. Output: `SPECOUT` spectra correct with several SWAN processes |
| **Default** | on (`BUILD_SETTINGS=engine`); `BUILD_SETTINGS=stock` keeps COAWST's choices |
| **Files** | `build/coawst/Dockerfile` (edits `Compilers/Linux-gfortran.mk`, `SWAN/src/CMakeLists.txt` and the case header at build time) |
| **Evidence** | Reef_Ideal_A15, 1 h: 267 s -> 152 s on AMD, 315 s -> 198 s on Intel, identical results on both; Inlet_test: `SPECOUT` on 2 SWAN processes truncated with `SWAN_SINGLESPEC`, equal to 1 process without |
| **Test** | [`tests/improvements/build-settings/run.sh`](../../../../tests/improvements/build-settings/run.sh), see its [README](../../../../tests/improvements/build-settings/README.md) |
| **Upstream** | not reported yet |

## In short

COAWST's build script compiles ROMS with `-O3 -ffast-math` and SWAN with `-O`
(which for gfortran means `-O1`, light optimization), and Inlet_test's header
switches on `SWAN_SINGLESPEC`. The engine builds differently:

| Setting | COAWST v3.9 | Engine | Why | Effect measured |
|---|---|---|---|---|
| SWAN optimization | `-O` (= `-O1`) | `-O3` | SWAN is usually the slow side of a coupled run | A15: 1.7x faster overall (ROMS waits for SWAN 4x less) |
| CPU target | none (generic x86-64) | `-march=x86-64-v3` | AVX2 and FMA instructions, present on every current x86 cloud machine | part of the above; results differ from stock in the last digits (FMA rounds once instead of twice) |
| ROMS `-ffast-math` | on | off | IEEE-standard arithmetic (see below) | no measurable speed or reproducibility difference |
| `-g` | no | yes | line numbers in crash backtraces | none (the generated code is the same) |
| `SWAN_SINGLESPEC` | defined in Inlet_test's header | undefined in every case header | it breaks spectral point output with several SWAN processes | `SPECOUT` files correct |

## Background: what the flags mean

- **`-O1` / `-O3`**: how hard the compiler optimizes. `-O3` adds loop
  vectorization (several array elements per instruction), inlining and loop
  transformations. It does not change the order of floating-point
  operations within an expression, so results are the same as `-O1` except
  where vector instructions round differently (they do not on x86).
- **`-march=x86-64-v3`**: lets the compiler use the instruction set of
  Intel Haswell (2013) and AMD Zen (2017) and later: AVX2 (wider vectors) and
  FMA (fused multiply-add, `a*b + c` with one rounding instead of two). FMA
  changes the last bits of results. Every machine type a cloud run would use
  has it; `-march=native` is avoided so the image does not depend on the
  machine it was built on.
- **`-ffast-math`**: allows the compiler to treat floating-point arithmetic
  as if it were exact real arithmetic: reorder sums, replace divisions by
  multiplications with the reciprocal, assume no NaN or infinity ever occurs,
  and (when linking) flush very small numbers to zero. Faster in principle,
  but results then depend on compiler choices, NaN checks may be optimized
  away, and tiny values become exactly zero. ROMS's own blow-up check is safe
  either way (it prints the energy to text and looks for "NaN").
- **`SWAN_SINGLESPEC`**: a COAWST option meant to avoid one temporary file
  per SWAN process for spectral output. With it, SWAN skips the step that
  merges the processes' pieces at the end of the run, so with more than one
  SWAN process several processes write into one file and nothing merges
  them.

## The change

In `build/coawst/Dockerfile` (shared stage, before the case is built):

```dockerfile
ARG BUILD_SETTINGS=engine
ARG ARCH_FLAGS="-march=x86-64-v3 -g"
RUN case "${BUILD_SETTINGS}" in \
        engine) \
            sed -i "s|^\( *FFLAGS += \)-ffast-math$|\1${ARCH_FLAGS}|" Compilers/Linux-gfortran.mk \
            && sed -i "s|\"-O -w -fno-second-underscore|\"-O3 ${ARCH_FLAGS} -w -fno-second-underscore|" SWAN/src/CMakeLists.txt \
            ...
```

so ROMS gets `-O3 -march=x86-64-v3 -g` and SWAN `-O3 -march=x86-64-v3 -g`;
the build stops if either replacement did not happen. And in the case stage:

```dockerfile
RUN if [ "${BUILD_SETTINGS}" = engine ]; then \
        sed -i "s|^#define SWAN_SINGLESPEC\b.*|#undef SWAN_SINGLESPEC  /* build settings: ... */|" \
            ${CASE_DIR}/*.h \
        ...
```

`--build-arg BUILD_SETTINGS=stock` skips both (with `SERIES=none`: COAWST
exactly as shipped). `ARCH_FLAGS` can be changed for other CPUs or checks.

## How the test works

`tests/improvements/build-settings/run.sh`
([README](../../../../tests/improvements/build-settings/README.md)) builds
Inlet_test and Reef_Ideal_A15 with each setting (all patches up to
`roms-wec-stokes-fast` in all four) and runs:

- Inlet_test, 2 h, with spectral output (`SPECOUT`, text and NetCDF) at 9
  points across the domain, on 1 and on 2 SWAN processes;
- Reef_Ideal_A15, 1 h, several times per image, on AMD (c2d) and Intel (n2)
  Cloud Batch machines.

## Engine test results

Run 2026-10-31. PASS.

**`SPECOUT` with 2 SWAN processes** (Inlet_test, 9 points, 2 h):

| | 1 SWAN process | 2 SWAN processes |
|---|---|---|
| stock (`SWAN_SINGLESPEC`): `spread.spc2d` | 174 kB | **59 kB, truncated** |
| stock: `spread.nc` | valid | **not a NetCDF file** |
| engine: `spread.spc2d` | 174 kB | the same (up to trailing blanks in two header lines) |
| engine: `spread.nc` | valid | every variable equal |

(The case's own single point, `point1.spc2d`, happened to be complete in
both, because one process owns it.)

**Results** (Reef_Ideal_A15, ROMS 1x6 + 2 SWAN, 1 h):

| Comparison | Result |
|---|---|
| the same image run 3 times on AMD c2d-standard-8 | identical (both settings) |
| the same image on AMD c2d and Intel n2 | identical (both settings) |
| engine vs stock | largest relative difference 5.6e-5 (v 1.5e-5 m/s, AKv 1.6e-5 m2/s, zeta 3.9e-7 m) |

The engine-vs-stock differences start in the last bits (FMA, SWAN's
vectorized loops) and grow slowly in the turbulent flow over the reef;
after 1 h they are five orders of magnitude below the currents.

**Speed** (wall time of the whole coupled run):

| Run | stock | engine |
|---|---|---|
| A15, AMD c2d-standard-8 (3 runs) | 266-268 s | 149-154 s |
| A15, Intel n2-standard-8 | 315 s | 198 s |
| Inlet_test, 1 SWAN process (control VM) | 137 s | 100 s |
| Inlet_test, 2 SWAN processes | 112 s | 75 s |

**Where the time goes** (A15 with ROMS's `PROFILE`, CPU seconds summed over
the 6 ROMS processes, two runs each):

| Build | wall | ROMS computing | ROMS waiting for SWAN |
|---|---|---|---|
| stock | 267 s | 653-670 | 876-903 |
| engine, `-ffast-math` added back | 146-151 s | 601-619 | 222-229 |
| engine | 150-155 s | 621-674 | 198-221 |

So the speed-up comes from SWAN: at `-O3` it keeps up with ROMS, and ROMS's
waiting at the coupling exchanges drops by three quarters. **`-ffast-math`
makes no measurable difference** to ROMS's own computing time (the spread
between two runs of the same image, about 8 %, is larger than any
difference), and both settings reproduce exactly across machine types. It
stays off because IEEE-standard arithmetic costs nothing measurable here:
no reordering of sums, NaN and infinity kept, tiny numbers not flushed to
zero.

Note: all earlier tests in this repository were built before these settings
existed, that is with COAWST's flags; each compares builds made with the
same flags, so their conclusions hold.

## Who is affected

Every build of the engine (`BUILD_SETTINGS=engine` is the default): coupled
runs are faster, and results differ from a COAWST build with its own flags at
the level of rounding. Cases that define `SWAN_SINGLESPEC` get it removed;
put `--build-arg BUILD_SETTINGS=stock` to keep COAWST's choices.
