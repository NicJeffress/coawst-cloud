# vendor/: fallback copy of the COAWST source

Empty in normal use: the Dockerfile fetches COAWST from GitHub at `COAWST_REF`.

If GitHub or the DOI-USGS/COAWST repository is unavailable, put a tarball of the
pinned commit here as `COAWST-<COAWST_REF>.tar.gz` (one top-level folder, as
GitHub's "Download ZIP/tar.gz" makes it). `build.sh` copies it into the build
context and the Dockerfile uses it instead of GitHub. Tarballs are git-ignored.
