# ROMSPath (offline particle tracking on ROMS output), built from a fork of
# imcslatte/ROMSPath at a pinned commit (see README.md for why a fork).
#
# Build with build.sh:
#   build/romspath/build.sh                  the pinned commit, from GitHub
#   build/romspath/build.sh --source DIR     a local checkout instead (tests)
# Build arguments (pass after -- to build.sh):
#   ROMSPATH_REF=<commit sha>    commit to build
#   OPT_FLAGS="..."              replaces the makefile's -g -O0 (default
#                                "-O3 -march=x86-64-v3")
#
# The result is a small image with ROMSPath.exe on the PATH; it takes the
# ROMSPath.data file as its argument, like the stock program.

############################ build stage ############################
FROM ubuntu:24.04 AS build

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        gfortran make libnetcdff-dev git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ARG ROMSPATH_REPO=https://github.com/NicJeffress/ROMSPath.git
ARG ROMSPATH_REF=f9058a447a1cd5294ad170fd041ad11b7e08a31d

# Fetch exactly one commit from the fork. A local checkout put in src/ by
# build.sh --source is used instead (it must be at ROMSPATH_REF or later).
COPY src/ /tmp/src/
WORKDIR /opt/romspath-src
RUN if [ -f /tmp/src/makefile ]; then \
        cp -r /tmp/src/. . \
        && echo "local source $(cat /tmp/src/SOURCE_COMMIT 2>/dev/null)" > PROVENANCE; \
    else \
        git init -q . \
        && git remote add origin ${ROMSPATH_REPO} \
        && git fetch -q --depth 1 origin ${ROMSPATH_REF} \
        && git checkout -q FETCH_HEAD \
        && echo "${ROMSPATH_REPO} $(git rev-parse HEAD)" > PROVENANCE \
        && rm -rf .git; \
    fi \
    && rm -rf /tmp/src

# The fork's makefile keeps upstream's debug flags (-g -O0, 3-4 times slower).
# x86-64-v3 = AVX2/FMA, which every current x86 cloud machine has; not
# -march=native, so the image does not depend on the CPU it was built on.
ARG OPT_FLAGS="-O3 -march=x86-64-v3"
RUN grep -q '^  FFLAGS = -g -O0 ' makefile \
        || { echo "makefile: no '  FFLAGS = -g -O0' line to replace" >&2; exit 1; } \
    && sed -i "s/^  FFLAGS = -g -O0 /  FFLAGS = ${OPT_FLAGS} /" makefile \
    && echo "FFLAGS: ${OPT_FLAGS}" >> PROVENANCE \
    && make > build.log 2>&1 || { tail -30 build.log; exit 1; }

############################ run stage ##############################
FROM ubuntu:24.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends libnetcdff7 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /opt/romspath-src/ROMSPath.exe /opt/romspath-src/PROVENANCE /opt/romspath/
ENV PATH=/opt/romspath:$PATH
WORKDIR /run
