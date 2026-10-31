# swan-nc-crash.patch: SWAN's NetCDF output read past a file name and past its name table

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | no (memory-safety fix: removes a crash and silent memory corruption) |
| **Default** | on |
| **Files** | `SWAN/src/ocpmix.ftn` (`nc_filename_length`), `SWAN/src/swn_outnc.ftn90` (`stnames_size`) |
| **Evidence** | SWAN built with gfortran's run-time checks: stock stops at both accesses, patched runs clean; Valgrind 16 invalid accesses before, 0 after (2026-10-20) |
| **Test** | [`tests/fixes/swan-nc-crash/run.sh`](../../../../tests/fixes/swan-nc-crash/run.sh), see its [README](../../../../tests/fixes/swan-nc-crash/README.md) |
| **Upstream** | related reports DOI-USGS/COAWST#455 (malloc error in Inlet_test/Coupled) and #333 (unreliable SWAN `.nc` output); fix not yet proposed |

Each change below is named as its function in
[`generators/make_swan_patches.py`](../generators/make_swan_patches.py)
(`change_<name>`), which writes all SWAN patches of the series.

## In short

Two places in SWAN's NetCDF output code accessed memory beyond what they
owned. Fortran does not check array or string bounds unless asked to, so the
program carried on with whatever happened to be in that memory: on most
machines nothing visible, on some an abort. COAWST's own Inlet_test, which
writes one SWAN NetCDF file (`hsig.nc`), crashed on some cloud VMs with
`malloc(): unaligned tcache chunk detected` and ran fine on others, which made
the problem look random.

| Change | What was wrong | Consequence |
|---|---|---|
| `nc_filename_length` | the file-opening routine treated every file name as 140 characters, even an 11-character one | read and overwrote 129 bytes of memory after the name: heap corruption, random crashes |
| `stnames_size` | a table of NetCDF variable names had 171 rows but was looked up with quantity numbers up to 202 | read past the end of the table for COAWST's added quantities |

## Background: what "heap corruption" means here

A running program keeps most of its data in a region of memory called the
heap. The C library (glibc) hands out pieces of the heap on request
(`malloc`) and keeps its own bookkeeping, small records stored right next to
each piece. A program that writes past the end of its piece overwrites the
neighbour: perhaps other data, perhaps glibc's bookkeeping. Nothing happens at
that moment. Later, when glibc next allocates or frees memory and reads its
damaged records, it either notices and aborts the program (`malloc():
unaligned tcache chunk detected`, `munmap_chunk(): invalid pointer`) or does
not, and the program carries on with corrupted data. Which of the two happens
depends on the exact memory layout: the machine, the library versions, the
number of processes. That is why the same run crashed on one VM type and not
on another.

Two tools make such errors visible deterministically: Valgrind (used when the
bug was found) and, for Fortran, gfortran's run-time checks
(`-fcheck=bounds`), which stop the program at the first access past the end of
an array or string. The engine test uses the latter.

## nc_filename_length: a 140-character file name read from an 11-character string

`FOR` (`ocpmix.ftn`) opens files for SWAN. It declared its file-name argument
with a fixed length, `LENFNM` = 140 characters:

```fortran
      CHARACTER DDNAME*(LENFNM), SF*2
```

In Fortran, a character argument declared with a fixed length is simply
assumed to be that long: the routine receives only the address of the first
character. For NetCDF output, `swanout2` calls `FOR` with a temporary string,
`TRIM(FILENM)//'.dum'`, which is only as long as the name: 11 characters for
`hsig.nc.dum`. `FOR` then reads 140 characters from that address, and loops
over all 140 replacing `\` with `/` (a Windows path convention), writing into
the 129 bytes of heap memory that follow the temporary string.

**The fix** declares the argument with assumed length, so `DDNAME` is exactly
as long as what the caller passes:

```fortran
-      CHARACTER DDNAME*(LENFNM), SF*2
+      CHARACTER DDNAME*(*), SF*2
```

All other callers pass 140-character variables, for which nothing changes.

## stnames_size: the NetCDF name table indexed past its end

`swn_outnc.ftn90` keeps the NetCDF variable name of each SWAN output quantity
in a table `STNAMES(171,2)`, indexed by the quantity's number `IVTYPE`
(column 2 holds the name of the second component of vector quantities):

```fortran
    character*40                :: STNAMES(171,2) = ''
```

COAWST added quantities numbered up to 202 (`DIRBOT` 200, `DICD` 201,
`SSPEC` 202). When SWAN reads a `BLOCK` or `TABLE` request for a NetCDF file,
`swanpre2.ftn` checks whether the quantity has a NetCDF name with
`STNAMES(IVTYPE,1)`, so a NetCDF request for one of COAWST's quantities read
past the end of the table.

**The fix** gives the table 202 rows:

```fortran
-    character*40                :: STNAMES(171,2) = ''
+    character*40                :: STNAMES(202,2) = ''
```

(Rows 172-202 stay empty here. The improvement
`2-improvements/swan-netcdf-output.patch` later in the series fills in NetCDF
names for these and many other quantities.)

## How the test works

`tests/fixes/swan-nc-crash/run.sh` ([README](../../../../tests/fixes/swan-nc-crash/README.md))
builds stock Inlet_test before and after the patch with SWAN compiled with
`-fcheck=bounds` (build argument `SWAN_FFLAGS_EXTRA`), so that any access past
the end of an array or string stops the run at once with the source line,
instead of corrupting memory silently. It runs 1 h:

| Run | Before the patch | After the patch |
|---|---|---|
| Inlet_test as shipped (`hsig.nc`) | stops in `FOR` (`nc_filename_length`) | runs to the end, no error |
| plus `BLOCK ... 'wdirbot.nc' ... DIRBOT` (quantity 200) | stops in `swanpre2` (`stnames_size`) | no error about the table |

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

The "(11/140)" in the first message is exactly the bug: an 11-character
actual argument for a 140-character dummy. With the whole of SWAN
bounds-checked, the shipped case runs its hour without any other
out-of-bounds access.

## The original diagnosis

Found 2026-10-20 when Inlet_test aborted on a cloud VM (n2d) and ran on the
control VM (e2). Valgrind on the control VM: 16 invalid reads and writes in
`FOR` before the fix, 0 after.

## Who is affected

Every run that writes SWAN output as NetCDF (`BLOCK`/`TABLE` with a `.nc`
file name), including COAWST's own Inlet_test: random crashes depending on the
machine. `stnames_size`: NetCDF requests for COAWST's quantities 172-202.
