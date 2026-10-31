# swan-nc-crash.patch: SWAN's NetCDF output read past a file name and past its name table

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | no (memory-safety fix: removes a crash and silent memory corruption) |
| **Default** | on |
| **Files** | `SWAN/src/ocpmix.ftn` (`nc_filename_length`), `SWAN/src/swn_outnc.ftn90` (`stnames_size`) |
| **Evidence** | SWAN built with gfortran run-time checks: stock stops at both accesses, patched runs clean (results below); Valgrind 16 invalid accesses before, 0 after (2026-10-20) |
| **Test** | [`tests/fixes/swan-nc-crash/run.sh`](../../../../tests/fixes/swan-nc-crash/run.sh) |
| **Upstream** | related reports DOI-USGS/COAWST#455 (malloc error in Inlet_test/Coupled) and #333 (unreliable SWAN `.nc` output); fix not yet proposed |

Each change below is named as its function in
[`generators/make_swan_patches.py`](../generators/make_swan_patches.py)
(`change_<name>`), which writes all SWAN patches of the series.

## Summary

Two places in SWAN's NetCDF output code accessed memory past the end of what
they owned. Fortran does not check this unless asked to, so the program
carried on with whatever happened to be there: on most machines nothing
visible, on some an abort. COAWST's own Inlet_test, which writes one SWAN
NetCDF file (`hsig.nc`), crashed on some cloud VMs with
`malloc(): unaligned tcache chunk detected` and ran on others.

## `nc_filename_length`: a 140-character file name read from an 11-character string

`FOR` (`ocpmix.ftn`) opens files. It declared its file-name argument as
`CHARACTER DDNAME*(LENFNM)`, i.e. exactly 140 characters. For NetCDF output,
`swanout2` calls it with `TRIM(FILENM)//'.dum'`, a temporary that is only as
long as the name (11 characters for `hsig.nc.dum`). `FOR` then treats the
argument as 140 characters: it reads them, and loops over all 140 replacing
`\` with `/`, writing into whatever heap memory follows the string. Whether
that crashes depends on what sits next to the string.

Fix: assumed length, so `DDNAME` is as long as what the caller passes.

```fortran
-      CHARACTER DDNAME*(LENFNM), SF*2
+      CHARACTER DDNAME*(*), SF*2
```

Callers that pass 140-character variables, as all other callers do, behave
exactly as before.

## `stnames_size`: the NetCDF name table indexed past its end

`swn_outnc.ftn90` keeps the NetCDF name of each SWAN output quantity in
`STNAMES(171,2)`, indexed by the quantity number `IVTYPE`. COAWST added
quantities numbered up to 202 (`DIRBOT` 200, `DICD` 201, `SSPEC` 202), and
`swanpre2.ftn` looks up `STNAMES(IVTYPE,1)` for every NetCDF output request
to see whether the quantity can be written. A NetCDF request for one of
COAWST's quantities therefore read past the end of the table. Fix: the table
has 202 rows.

(The same file also gets NetCDF names for many more quantities; that is part
of the improvement `2-improvements/swan-netcdf-output.patch`, not of this fix.)

## Test

`tests/fixes/swan-nc-crash/run.sh` builds stock Inlet_test before and after
the patch with SWAN compiled with `-fcheck=bounds` (build argument
`SWAN_FFLAGS_EXTRA`), which makes gfortran stop at the first access past the
end of an array or a string, and runs 1 h:

| Run | Before the patch | After the patch |
|---|---|---|
| Inlet_test as shipped (`hsig.nc`) | stops in `FOR` | runs to the end, no error |
| plus `BLOCK ... 'wdirbot.nc' ... DIRBOT` | stops in `swanpre2` | no error about the table |

## Engine test results

Run 2026-10-30 on the control VM, stock Inlet_test, 1 h, SWAN built with
`-fcheck=bounds`; "before" is the series up to this patch (the ROMS fixes
only), "after" adds it. PASS:

```
shipped-before: At line 1592 of file .../ocpmix.f
   Fortran runtime error: Actual string length is shorter than the declared
   one for dummy argument 'ddname' (11/140)
shipped-after:  no run-time error, runs to the end
dirbot-before:  At line 1255 of file .../swanpre2.f
   Fortran runtime error: Index '200' of dimension 1 of array 'stnames'
   above upper bound of 171
dirbot-after:   no error about stnames; SWAN refuses the request ("netCDF
   output not allowed for wdirbot.nc"), carries on, and then stops in
   swanout1 ('voq' above upper bound of 0): the next bug, fixed by
   swan-stop-on-input-errors.patch
```

With the whole of SWAN bounds-checked, the shipped case runs its hour without
any other out-of-bounds access.

## Also found: the original diagnosis

Found 2026-10-20 when Inlet_test aborted on a cloud VM (n2d) and ran on the
control VM (e2). Valgrind on the control VM: 16 invalid reads and writes in
`FOR` before the fix, 0 after.
