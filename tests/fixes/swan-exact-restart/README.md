# Test: swan-exact-restart

Checks [`1-fixes/swan-exact-restart.patch`](../../../build/coawst/patches/1-fixes/swan-exact-restart.md):
a SWAN run restarted from its periodic restart files must continue exactly
as if it had never stopped.

## The idea

Run the same case twice: straight through for 40 min, and in two pieces,
20 min writing restart files, then 20 min starting from them. If restarts are
exact, the two give the same Hs at 40 min to the last bit. Do it with binary
(`UNFORMATTED`) and text (`FREE`) restart files, before and after the patch.

## What it does, step by step

1. Builds `tests/cases/Swan_Periodic_Test` (standalone SWAN) before and after
   the patch.
2. Uses the periodic reef of `swan-periodic-fixes` (`tall-rep-mid`, from its
   `make_inputs.py`), 2 SWAN processes (one restart file each), Hs every
   10 min.
3. For each image:
   - `straight`: 0-40 min;
   - for each format (`UNFORMATTED`, `FREE`):
     - `part1`: 0-20 min with `RESTART 'output/swan_rst.dat' <FORMAT> 20 MIN`
       placed before `COMPUTE` (SWAN reads commands after `COMPUTE` only at the
       end);
     - `part2`: `INIT HOTSTART MULTIPLE 'swan_rst.dat' <FORMAT>` from part1's
       files, then 20-40 min.
4. Compares Hs at 40 min, part2 vs straight (`tests/tools/compare_nc.py
   --last`).

PASS: the binary restart before the patch does not reproduce the straight run
(it fails or differs), and after the patch it is bit-identical. The text
restart is shown for reference: it keeps about 5 significant digits, so it
differs before and after.

## Running it

```bash
PYTHON=~/venv/bin/python tests/fixes/swan-exact-restart/run.sh OUTDIR
```

About 15 min on 4 vCPUs.

## Reading the output

```
== Hs at 40 min, restarted vs straight
   before UNFORMATTED RESTART FAILED
   before FREE        hs   0.0007648   1.373   (1, 62)   NO DIFFERENCES FOUND
   after  UNFORMATTED hs   0           1.373   ()        yes ALL BIT-IDENTICAL
   after  FREE        hs   0.0007648   1.373   (1, 62)   NO DIFFERENCES FOUND
PASS
```

"RESTART FAILED" before the patch: SWAN tried to read its restart files as
binary and hit the end of the file, because stock SWAN had written them as
text whatever the keyword. The logs are in `OUTDIR/<side>-<format>-part2/`.

## Last result

2026-10-31, control VM: PASS.
