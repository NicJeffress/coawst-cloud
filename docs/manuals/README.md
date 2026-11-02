# Reference manuals

The manuals used when choosing options and reading the code. They are
third-party documents, so this repository does not include them (see
`THIRD_PARTY.md`): get each one from its publisher and put it in this
folder under the file name below. `.gitignore` keeps local copies out of
commits. They are the versions current at the dates given; the code is the
authority where a manual disagrees with it, and `docs/options/` records
those disagreements.

| File name | What | Version and date | Caveats |
|---|---|---|---|
| `COAWST_User_Manual_v3.9.docx` | COAWST user manual (USGS, distributed with COAWST): libraries, build, cpp options for the coupled system (section 4.3), the examples, ROMS/SWAN/WW3/coupled set-up tutorials, change log | v3.9, 29 September 2026 (USGS) | Its ROMS section is a tutorial, not an option list: use `ROMS/Include/cppdefs.h` and the `.in` glossaries for those. Some numbers differ from the code (e.g. the `DRAGLIM_DAVIS` cap is 2.4e-3 in the source, 2.85e-3 in the manual) |
| `swanuse_41.51.pdf` | SWAN user manual (TU Delft, SWAN website): every command with its parameters and defaults | Cycle III 41.51, 13 March 2026 (TU Delft) | The SWAN bundled with COAWST v3.9 reports 41.51 but carries later code (breaking `ASYM`, `WCAP AB CURRENT`, `TRIAD ... IC`); several `BREAKING` variants are parsed but not documented. COAWST's own additions (`NSGRIDS`, `RESTART`, `VEGETATION 3`, coupled `INPGRID` lines) are in the COAWST manual and in `docs/options/swan_command_catalogue.md` |
| `swantech_41.51.pdf` | SWAN scientific and technical documentation (TU Delft, SWAN website): the source terms, the numerics (propagation schemes, limiter, refraction in nonstationary runs, breaking linearization) | Cycle III 41.51, 13 March 2026 | - |
| `living-with-roms_cherian_2020.pdf` | "Living with ROMS", Deepak Cherian's notes (from the author): forum wisdom on time steps, GLS, pressure gradient schemes, open boundaries, mixing, floats, performance | 20 April 2020 | Predates ROMS 4.x and COAWST v3.9: option names and defaults may have moved; the reasoning is what it is kept for |

Not in this folder, but part of the same reference set: the pinned
COAWST source (`build/coawst/Dockerfile`, commit `26e6fb7`), whose
`ROMS/Include/cppdefs.h`, `ROMS/Include/globaldefs.h`, `ROMS/External/*.in`
glossaries and `SWAN/src/swanpre1.ftn` parser are the primary sources for
`docs/options/`.
