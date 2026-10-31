# Reef_Ideal_A15_veg: A15 with a constant canopy

`Reef_Ideal_A15` (application flag `REEF_IDEAL_A15`, same domain, tide, waves
and periodic SWAN; see its README) plus vegetation drag everywhere.

> **Vegetation elements are cylinders: `plant_thickness = (pi/4) x
> plant_diameter`.** ROMS takes each plant's horizontal footprint as
> diameter x thickness (a flat blade); for a cylinder that must be pi D^2/4.
> The footprint sets the gap between plants in `VEG_TURB`; with thickness =
> diameter this canopy fills the bed completely (diameter x thickness x density
> = 1), the gap is zero and ROMS blows up (`1-fixes/roms-vegetation.patch`
> now stops with a message instead).

- Header: `VEGETATION`, `VEG_DRAG`, `VEG_TURB`, `VEG_SWAN_COUPLING` on;
  `VEG_FLEX`, `VEG_STREAMING` off.
- `init_reef.nc`: plant density 4 m-2, diameter 0.5 m, height 0.4 m
  everywhere (frontal area per bed area 0.8), thickness (pi/4) x 0.5 =
  0.3927 m (bed coverage 0.785). The crest is 0.50 m deep, 0.35 m at low tide,
  so the 0.4 m canopy reaches the surface there around low tide.
- `swan.in`: `VEGETATION 3 0.4 0.5 1 1`: COAWST's `SVEG_COAWST`, which takes
  density, height, diameter and thickness at each point from ROMS's plant
  fields through the coupler (so they may vary in space); the last value is the
  drag method (1: Cd = 1.0 = `CD_VEG` in `vegetation.in`). With this constant
  canopy it gives the same result as `VEGETATION 1 0.4 0.5 1 1.0` to
  single-precision rounding. Needs `1-fixes/swan-vegetation-fixes.patch`.
- Spatially varying canopies are written into a copy of `init_reef.nc`.

Kept as shipped in COAWST v3.9 (author's decision): `VEG_TURB` uses only the
canopy time scale (the free-turbulence time scale `k/epsilon` is never used);
see `1-fixes/roms-vegetation.md`.

Time step: 6 s, as A15. The explicit vegetation drag limits it where the
canopy is dense and the flow fast: a patchy canopy blew up at 6 s and ran at
3 s (`3-experimental/roms-veg-implicit.patch` takes the drag implicitly).
