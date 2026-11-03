# Test: roms-veg-streaming-fixes

Checks [`1-fixes/roms-veg-streaming-fixes.patch`](../../../build/coawst/patches/1-fixes/roms-veg-streaming-fixes.md):
with `BOTTOM_STREAMING` and `VEG_STREAMING`, the wave streaming force must
carry the wave momentum that bottom friction and the plants take out.

## What it does

1. **Builds** tests/cases/Reef_Ideal_A15_veg with the fixes series without
   (*before*) and with (*after*) this patch, each with
   `+BOTTOM_STREAMING +VEG_STREAMING` and as the case stands.
2. **Runs** the streaming builds for 111 steps (ROMS 1 x 2 + 2 SWAN, DT 6 s):
   history at step 110, the momentum diagnostics of step 111 alone
   (`NTSDIA` 111, `NDIA` 1; the Adams-Bashforth mix of steps 109-111, all after
   the 600 s wave exchange). The builds without streaming run 10 min with
   history every 2 min.
3. **Checks**, each PASS or FAIL:
   - *bug*: before, the depth-integrated force (`u_bstm` times the layer
     thickness, summed) differs from (Dissip_fric + Dissip_veg) k cos(theta)/sigma,
     rebuilt from the history file, by more than 10 % (rms over the wave points);
   - *fixed*: after, by less than 1 %;
   - *unchanged*: the builds without streaming write bit-identical history.

## Running it

```bash
PYTHON=~/venv/bin/python tests/fixes/roms-veg-streaming-fixes/run.sh /tmp/vegstream
```

About 5 min per build (four builds) and 2-4 min per run on a 4-vCPU machine.
Result of 2026-11-03: PASS (before: ratio 0.293, misfit 0.71; after: ratio
1.000, misfit 3.5e-4; without streaming bit-identical). The history file
holds `Dwave` in degrees; ROMS uses radians.
