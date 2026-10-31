# swan-exact-restart.patch: SWAN's restart files reproduce the uninterrupted run

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | restarts only: a run restarted from `RESTART ... UNFormatted` files now continues exactly as the uninterrupted run; runs without restarts are unchanged |
| **Default** | on (exact restarts need `UNFormatted` restart files) |
| **Files** | `swanpre1.ftn`, `swanmain.ftn`, `waves_control.ftn`, `swan_iounits.ftn` (`exact_restart`) |
| **Evidence** | standalone SWAN, 40 min straight vs 20 + 20 min restarted (results below); coupled with ROMS: see `roms-restart-wec` |
| **Test** | [`tests/fixes/swan-exact-restart/run.sh`](../../../../tests/fixes/swan-exact-restart/run.sh) |
| **Upstream** | not reported |

## Why exact restarts matter

Cheap cloud machines (Spot VMs) can be taken away at any time. A long run on
them must be cut into segments that each start from the restart files of the
previous one. For a segmented run to be trustworthy, and to compare runs
across an ensemble bit for bit, the restarted run must continue exactly as if
it had never stopped.

COAWST's SWAN has a periodic restart command, `RESTART 'fname' FREE|UNFormatted
interval`, which writes SWAN's state every interval, one file per SWAN process
(`fname-001`, ...), read back with `INIT HOTSTART MULTIPLE 'fname'`. Three
problems kept a restarted run from reproducing an uninterrupted one.

## The three problems

1. **The periodic files were always text.** `RESTART` accepted
   `UNFormatted`, but the periodic writer (`RESTART_SWAN`) always wrote the
   text layout, where `WRSPEC` keeps about 5 significant digits of each
   spectrum. Now `UNFormatted` writes SWAN's binary `HOTFILE` layout (exact).
2. **The files held only the wave spectra.** After `INIT HOTSTART`, SWAN's
   first step zeroes the dissipation and recomputes bottom orbital fields from
   the new spectra, so the first exchange with ROMS sent other wave fields
   than the uninterrupted run. The binary file now also holds `COMPDA` (every
   computed field: depths and currents at both time levels, dissipation,
   orbital velocity, plants, ...) and the spectra again, written before the
   coupling exchange of that step (the state the exchange uses;
   `waves_control.ftn` now calls `SWAN_RST` before `SWAN_CPL`), and `COMPDA`
   once more right after the exchange (`SWAN_RST_POST`), which holds ROMS's
   water level, currents, roughness and plants: at a restart ROMS cannot send
   those values again. `INIT HOTSTART ... UNFormatted` reads these records when
   present (one SWAN grid only), and SWAN puts them back at the first step,
   before the output and the first exchange. Older files read as before.
3. **`RESTART` acts only before `COMPUTE`.** SWAN reads the commands after
   `COMPUTE` only when the run ends, so placed there it gives a one-off file at
   the end. COAWST's example cases place it after `COMPUTE`; segmented runs
   must place it before (the tests do).

The binary files are about twice the size of one copy of the spectra
(145 MB per process for an idealized reef case on 2 SWAN processes); the
number of SWAN processes must stay the same across a restart.

## Test

`tests/fixes/swan-exact-restart/run.sh` runs standalone SWAN on the periodic
reef of `swan-periodic-fixes` with 2 processes: 40 min straight, and 20 min
with `RESTART ... 20 MIN` followed by 20 min from `INIT HOTSTART MULTIPLE`, in
both formats, before and after the patch, and compares Hs at 40 min.

## Engine test results

Run 2026-10-31 on the control VM, standalone periodic reef, 2 SWAN
processes; "before" is the series up to this patch, "after" adds it. Hs at
40 min, restarted after 20 min vs straight. PASS:

```
before UNFORMATTED  RESTART FAILED: SWAN reads its "binary" restart files and
                    stops with "End of file" (swanpre1, unit swan_rst.dat-001):
                    they were written as text
before FREE         max |diff| 0.76 mm (Hs up to 1.37 m)
after  UNFORMATTED  ALL BIT-IDENTICAL
after  FREE         max |diff| 0.76 mm (text keeps about 5 digits; as expected)
```

## Coupled runs

ROMS needs its own changes for an exact restart with waves
(`1-fixes/roms-restart-wec.patch`). Together, an idealized reef case
restarted after 30 of 60 min came out bit-identical in every SWAN output and
within round-off in ROMS (2e-10 m/s), against 2.4 cm/s off with COAWST as
shipped (2026-10-24; engine test with `roms-restart-wec`).
