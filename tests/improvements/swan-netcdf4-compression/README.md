# Test: swan-netcdf4-compression

Checks [`2-improvements/swan-netcdf4-compression.patch`](../../../build/coawst/patches/2-improvements/swan-netcdf4-compression.md):
with `OUT_NETCDF4` and `DEFLATE`, SWAN writes compressed NetCDF-4 files with
exactly the same values; without them, nothing changes.

## The idea

Compression is lossless, so the same run written compressed and
uncompressed must give identical numbers. The test makes SWAN write all
three kinds of NetCDF output (fields, point tables, spectra) in three builds
and compares every variable.

## What it does, step by step

1. **Builds** COAWST's coupled Inlet_test three times:
   - `before`: the series up to the patch, with
     `CPP_OPTIONS="+OUT_NETCDF4 +DEFLATE"`. ROMS writes compressed NetCDF-4;
     SWAN, without the patch, still writes classic files;
   - `after-classic`: with the patch, no options;
   - `after`: with the patch and the options.
2. **Runs** each for 1 h (ROMS 1 tile + 1 SWAN process, about a minute),
   with SWAN output added every 10 min, all as NetCDF:
   - `BLOCK` on the computational grid: HSIGN, DIR, TM01, VEL, DISSIP, QB
     (`b_<quantity>.nc`; DISSIP and QB need `swan-netcdf-output`, earlier in
     the series);
   - `TABLE` at 9 points: HSIGN, DIR, TM01, DEPTH (`pts.nc`);
   - `SPECOUT` 2-D spectra at the same points (`spec.nc`).
3. **Checks** (`check.py`):
   - *format*: SWAN files classic (`NETCDF3_64BIT_OFFSET`) in `before` and
     `after-classic`, `NETCDF4` in `after`; in `after`, every
     multi-dimensional variable has shuffle + deflate and no 1-D variable
     does; ROMS's history is NetCDF-4 in both `before` and `after`;
   - *values*: every variable of every SWAN file (values, missing points,
     type, attributes) identical in the three runs; ROMS history identical
     between `before` and `after`;
   - *size*: SWAN files smaller in `after`, with the sizes per file.

## Running it

```bash
PYTHON=~/venv/bin/python tests/improvements/swan-netcdf4-compression/run.sh OUTDIR
```

About 15 min on 4 vCPUs (three builds and three short runs). Needs Docker
and Python with numpy and netCDF4.

## Reading the output

```
ok  filters after: 30 multi-dimensional variables with shuffle + deflate, 14 1-D variables plain
ok  SWAN values: 44 variables in 8 files identical in all three runs
ok  size: SWAN files 1.58 MB (before) -> 0.78 MB (after), 2.0x smaller; ...
```

## Last result

2026-10-31, control VM: PASS. 44 variables in 8 SWAN files and 211 ROMS
history variables identical; SWAN files 2.0x smaller (fields 1.7-7x,
spectra 2x; the 6 kB point table grew to HDF5's minimum, 30 kB).
