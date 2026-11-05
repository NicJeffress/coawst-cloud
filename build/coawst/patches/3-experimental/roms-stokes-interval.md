# roms-stokes-interval.patch: update the spectral Stokes drift less often than every step

| | |
|---|---|
| **Type** | experimental (cpp option `STOKES_INTERVAL`, with `WEC_VF` and `SPECTRUM_STOKES`; `STOKES_NCPL` in `ocean.in`) |
| **Changes results?** | with the option and `STOKES_NCPL` above 0: yes, slightly (below). With `STOKES_NCPL` 0, or without the option: no, bit-identical |
| **Default** | off |
| **Files** | `ROMS/Nonlinear/WEC/wec_stokes.F`, `ROMS/Modules/mod_scalars.F`, `ROMS/Utility/read_phypar.F` |
| **Evidence** | Reef_Ideal_A15_veg, density 1, DT 2.5 s, 24 h, 10 ROMS + 6 SWAN: 1.9 to 2.2x faster. Updating every 120 s, against every step: set-up -0.003 %, transports within 0.002 %, budget unchanged to three decimals |
| **Test** | [`tests/experimental/roms-stokes-interval`](../../../../tests/experimental/roms-stokes-interval/README.md) |
| **Upstream** | not proposed yet |

## In short

`SPECTRUM_STOKES` sums SWAN's spectrum over its frequency bins, in every layer of every column, on every baroclinic step. SWAN's spectrum only changes at the wave-to-ocean exchange: at DT 2.5 s and a 600 s exchange, 240 sums use the same spectrum, and only the layer depths differ. On this case that sum was most of the 59 % of ROMS's time spent in the WEC kernel.

The option holds `u_stokes` and `v_stokes` between updates. `STOKES_NCPL` sets the updates per exchange:

| `STOKES_NCPL` | Update (600 s exchange) |
|---|---|
| 0 | every baroclinic step, as without the option |
| 1 | at each exchange, 600 s |
| 5 | 120 s |
| 20 | 30 s |

It must divide the exchange's number of steps, or the run stops with an error. Tying it to the exchange means a change of DT doesn't change the update interval.

## The change

- In `wec_stokes_tile`, the two `SPECTRUM_STOKES` loops, the boundary conditions of `u_stokes`, `v_stokes` and their halo exchange run only when `MOD(iic-1, steps between updates) = 0`, the phase of `ocean_coupling`, or on the run's first step.
- Everything computed from them still runs every step, from the held `u_stokes`, `v_stokes` and the current `Hz`: `W_stokes`, `ubar_stokes`, `vbar_stokes`. So the 2-D and 3-D Stokes transports stay consistent with each other.
- With `MCT` coupling only: it reads `nOCNFWAV` from `mct_coupler_params`.

## Results

Reef_Ideal_A15_veg, density 1, DT 2.5 s, N 15, 34 frequencies, 24 h, against every step, hours 12-24:

| | Every step | 600 s | 120 s | 30 s |
|---|---|---|---|---|
| wall s per simulated hour | 280 | 135 | 127 | 144 |
| WEC kernel, share of ROMS time | 59 % | 11 % | 13 % | 19 % |
| set-up, 25.69 mm | | -0.03 % | -0.003 % | -0.001 % |
| set-up range, 19.08 mm | | -0.4 % | -0.01 % | -0.01 % |
| crest transport, 720 m³/s | | +0.01 % | under 0.001 % | under 0.001 % |
| pass transport, 814 m³/s | | -0.01 % | -0.002 % | under 0.001 % |
| surface/mean speed, fore reef | | +2.1 % | -0.02 % | +0.09 % |
| peak Cw, 0.160 | | -1.1 % | -0.3 % | -0.1 % |

- The wall times are from separate VMs, so a few percent is noise; 120 s can't really be cheaper than 600 s.
- The momentum budget by zone is unchanged to three decimals at all three, and closes to about 1e-10.
- `STOKES_NCPL` 0: all 62 history and 83 diagnostic variables bit-identical to the build without the patch (2 h).
- `STOKES_NCPL` 1, 8 h with a restart at 4 h: bit-identical to the straight run from hour 5 in every variable. The first history record after a restart differs only in the output-only fields, as without the patch.
- Beyond 2 km from shore the flow differs by 7-30 % rms at all three, and that barely shrinks with the interval; see the twin test in the test's README.

## Limits

- Keep restarts on a multiple of the update interval; a restart elsewhere recomputes the sums one step early.
- Tested on one case: uniform canopy, 12 h tide of 0.15 m, water 0.5 m deep at mean sea level on the crest. A large tide over very shallow water changes the layers more between updates.
- The bulk Stokes option (`BULK_STOKES`) isn't touched: it is cheap already.
