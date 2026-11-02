# Third-party software

This repository does not contain COAWST's source. The build downloads it from
https://github.com/DOI-USGS/COAWST at a pinned commit and applies the patches in
`build/coawst/patches/`. The licenses below were read from that repository on
2026-10-30.

| Component | License | Notes |
|---|---|---|
| COAWST (USGS parts) | Public domain in the United States; CC0 1.0 worldwide (`LICENSE.md`) | |
| ROMS | MIT (`License_ROMS.md`, Copyright (c) 2002-2026 ROMS group) | Our ROMS patches keep this notice. |
| SWAN | GNU General Public License | Our SWAN patches are distributed under the GPL. A published image built from this repository has its complete source available: the pinned COAWST commit plus these patches. |
| MCT (Model Coupling Toolkit) | Argonne open-source license (BSD style) | Bundled with COAWST. |
| SCRIP | Los Alamos open-source license (BSD style) | Bundled with COAWST. |
| ROMSPath | No license file in https://github.com/imcslatte/ROMSPath (checked 2026-11-02) | Not in this repository: `build/romspath` fetches it from a fork at a pinned commit and compiles it. Its bundled Mersenne Twister (`random_module.f90`) carries its own BSD-style license. |

When using or citing COAWST, follow the guidance in COAWST's README and do not
imply endorsement by the USGS.
