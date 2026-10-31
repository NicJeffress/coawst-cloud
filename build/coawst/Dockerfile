# COAWST (ROMS + SWAN coupled through MCT), no WRF / WW3.
#
# Build with build.sh (it assembles the build context, including your case):
#   build/coawst/build.sh                       stock Inlet_test (Coupled)
#   build/coawst/build.sh --case DIR --app NAME your case (DIR holds name.h, .in files)
# Build arguments (pass after -- to build.sh):
#   COAWST_REF=<commit sha>      COAWST commit to build
#   SERIES=none                  build without our patches
#   BUILD_SETTINGS=stock         COAWST's own compiler flags and SWAN_SINGLESPEC
#                                (with SERIES=none: COAWST exactly as shipped)
#   ARCH_FLAGS="..."             CPU target and debug flags (default
#                                "-march=x86-64-v3 -g")
#   CPP_OPTIONS="+X -Y"          add #define X / #undef Y to the case header
# Steps shared by every case come first, so a new case reuses the cached
# COAWST download, MCT build and patches.
#
# The cpp options in the case header are compiled into coawstM, so an ensemble
# that only varies .in files and input NetCDF can share one image.

############################ build stage ############################
FROM ubuntu:24.04 AS build

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential gfortran cpp make cmake perl git patch ca-certificates \
        openmpi-bin libopenmpi-dev \
        libnetcdf-dev libnetcdff-dev netcdf-bin \
    && rm -rf /var/lib/apt/lists/*

ARG COAWST_REF=26e6fb73c5a8c4d37a83bd8339ae25c8db0ba2be

ENV COAWST_ROOT=/opt/COAWST
WORKDIR ${COAWST_ROOT}

# Fetch exactly one commit (no history) from the public repository. If GitHub
# is unavailable, put COAWST-<COAWST_REF>.tar.gz (a tarball of that commit) in
# build/coawst/vendor/ and it is used instead.
COPY vendor/ /tmp/vendor/
RUN if [ -f /tmp/vendor/COAWST-${COAWST_REF}.tar.gz ]; then \
        tar -xzf /tmp/vendor/COAWST-${COAWST_REF}.tar.gz --strip-components=1 \
        && echo "${COAWST_REF} (archive vendor/COAWST-${COAWST_REF}.tar.gz)" > COAWST_COMMIT; \
    else \
        git init -q . \
        && git remote add origin https://github.com/DOI-USGS/COAWST.git \
        && git fetch -q --depth 1 origin ${COAWST_REF} \
        && git checkout -q FETCH_HEAD \
        && git rev-parse HEAD > COAWST_COMMIT \
        && rm -rf .git; \
    fi \
    && rm -rf /tmp/vendor

# MCT coupling library (bundled with COAWST) -> /usr/local/mct, where
# Compilers/Linux-gfortran.mk looks for it by default. COAWST stores MCT's
# autotools scripts without the executable bit, and gfortran 10 and later
# reject MCT's mismatched MPI argument types without -fallow-argument-mismatch.
RUN cd Lib/MCT \
    && chmod +x configure config.guess config.sub install-sh mkinstalldirs \
    && ./configure --prefix=/usr/local/mct FC=gfortran MPIFC=mpif90 \
           FCFLAGS="-O2 -fallow-argument-mismatch" \
    && make \
    && make install

# Our patches, in the order of patches/series (see patches/README.md).
# SERIES=none builds stock COAWST. The applied list ends up in PATCHES_APPLIED.
COPY apply_series.sh /usr/local/bin/
COPY patches/ /tmp/patches/
ARG SERIES=series
RUN sh /usr/local/bin/apply_series.sh \
        $([ "${SERIES}" = none ] && echo none || echo /tmp/patches/${SERIES}) /tmp/patches

# Build settings (patches/2-improvements/build-settings.md). BUILD_SETTINGS=engine
# (default): ROMS without -ffast-math, SWAN at -O3 instead of -O (= -O1), both
# with ARCH_FLAGS: x86-64-v3 = AVX2/FMA, which every current x86 cloud machine
# has (not -march=native, so the image does not depend on the CPU it was built
# on); -g adds line numbers to crash backtraces without changing the code.
# BUILD_SETTINGS=stock keeps COAWST's flags (ROMS -O3 -ffast-math, SWAN -O).
ARG BUILD_SETTINGS=engine
ARG ARCH_FLAGS="-march=x86-64-v3 -g"
RUN case "${BUILD_SETTINGS}" in \
        engine) \
            sed -i "s|^\( *FFLAGS += \)-ffast-math$|\1${ARCH_FLAGS}|" Compilers/Linux-gfortran.mk \
            && sed -i "s|\"-O -w -fno-second-underscore|\"-O3 ${ARCH_FLAGS} -w -fno-second-underscore|" SWAN/src/CMakeLists.txt \
            && ! grep -q "ffast-math" Compilers/Linux-gfortran.mk \
            && grep -q "FFLAGS += ${ARCH_FLAGS}" Compilers/Linux-gfortran.mk \
            && grep -q "\"-O3 ${ARCH_FLAGS} -w" SWAN/src/CMakeLists.txt ;; \
        stock) ;; \
        *) echo "BUILD_SETTINGS must be engine or stock" >&2; exit 1 ;; \
    esac

# Extra compiler flags, for checks (tests use e.g. SWAN_FFLAGS_EXTRA="-fcheck=bounds",
# which stops at the first out-of-bounds access). Empty by default.
ARG ROMS_FFLAGS_EXTRA=""
ARG SWAN_FFLAGS_EXTRA=""
RUN if [ -n "${ROMS_FFLAGS_EXTRA}" ]; then \
        echo "FFLAGS += ${ROMS_FFLAGS_EXTRA}" >> Compilers/Linux-gfortran.mk; \
    fi \
    && if [ -n "${SWAN_FFLAGS_EXTRA}" ]; then \
        sed -i "s| -w -fno-second-underscore| ${SWAN_FFLAGS_EXTRA} -w -fno-second-underscore|" SWAN/src/CMakeLists.txt \
        && grep -q -- "${SWAN_FFLAGS_EXTRA} -w" SWAN/src/CMakeLists.txt; \
    fi

############ case-specific steps (after the shared, cached ones) ############
ARG COAWST_APPLICATION=INLET_TEST
ARG CASE_DIR=Projects/Inlet_test/Coupled
ARG NJOBS=4

# A case from outside COAWST (build.sh --case) joins the stock Projects.
COPY cases/ ${COAWST_ROOT}/Projects/

# Adapt the stock build script: Linux paths, OpenMPI, gfortran, chosen case.
RUN sed -i \
        -e "s|^export   COAWST_APPLICATION=.*|export   COAWST_APPLICATION=${COAWST_APPLICATION}|" \
        -e "s|^export   MY_ROOT_DIR=.*|export   MY_ROOT_DIR=${COAWST_ROOT}|" \
        -e "s|^ export         which_MPI=intel.*| export         which_MPI=openmpi|" \
        -e "s|^   export     MY_HEADER_DIR=.*|   export     MY_HEADER_DIR=\${MY_PROJECT_DIR}/${CASE_DIR}|" \
        -e "s|^   export MY_ANALYTICAL_DIR=.*|   export MY_ANALYTICAL_DIR=\${MY_PROJECT_DIR}/${CASE_DIR}|" \
        build_coawst.sh \
    && grep -E "COAWST_APPLICATION=|MY_ROOT_DIR=|which_MPI=openmpi|MY_HEADER_DIR=|FORT=gfortran" build_coawst.sh

# COAWST's SWAN_SINGLESPEC option (defined in Inlet_test's header) skips SWAN's
# collection of spectral point output, so with more than one SWAN process
# SPECOUT files come out truncated or unreadable. BUILD_SETTINGS=engine turns
# it off in the case header (patches/2-improvements/build-settings.md).
RUN if [ "${BUILD_SETTINGS}" = engine ]; then \
        sed -i "s|^#define SWAN_SINGLESPEC\b.*|#undef SWAN_SINGLESPEC  /* build settings: breaks SPECOUT with >1 SWAN process */|" \
            ${CASE_DIR}/*.h \
        && ! grep -q "^#define SWAN_SINGLESPEC" ${CASE_DIR}/*.h; \
    fi

# Options without a new case folder: CPP_OPTIONS appends "#define X" (+X) or
# "#undef X" (-X) to the end of the case header (<application in lower
# case>.h), so they override its choices, e.g. CPP_OPTIONS="-DJ_GRADPS +PJ_GRADPQ4".
ARG CPP_OPTIONS=""
RUN h=${CASE_DIR}/$(echo ${COAWST_APPLICATION} | tr A-Z a-z).h \
    && test -f $h \
    && for o in ${CPP_OPTIONS}; do \
           case "$o" in \
               +*) echo "#define ${o#+}  /* CPP_OPTIONS build arg */" ;; \
               -*) echo "#undef ${o#-}  /* CPP_OPTIONS build arg */" ;; \
               *) echo "CPP_OPTIONS: $o must start with + or -" >&2; exit 1 ;; \
           esac; \
       done >> $h \
    && echo "CPP_OPTIONS: ${CPP_OPTIONS:-none}"

# SWAN is built by CMake, which needs the MPI compiler wrapper (FC) and MCT's
# location from the environment. build_coawst.sh carries on even if SWAN
# fails, so check for its library explicitly.
ENV FC=mpif90 \
    MCT_INCDIR=/usr/local/mct/include \
    MCT_LIBDIR=/usr/local/mct/lib
RUN ./build_coawst.sh -j ${NJOBS} > build.log 2>&1 \
    || (tail -100 build.log; exit 1); \
    tail -5 build.log \
    && ls SWAN/build/lib/libswan*.a \
    && test -x coawstM

# No separate SCRIP build: COAWST v3.9 compiles Lib/SCRIP_COAWST into coawstM
# and makes interpolation weights at startup when the grids differ.

############################ runtime stage ############################
FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive
# RUNTIME_PKGS: extra packages, e.g. libasan8 for a memory-checking build.
ARG RUNTIME_PKGS=""
RUN apt-get update && apt-get install -y --no-install-recommends \
        openmpi-bin libnetcdff7 libgfortran5 netcdf-bin ca-certificates \
        ${RUNTIME_PKGS} \
    && rm -rf /var/lib/apt/lists/*

ARG CASE_DIR=Projects/Inlet_test/Coupled
ENV COAWST_ROOT=/opt/coawst
WORKDIR ${COAWST_ROOT}

COPY --from=build /opt/COAWST/coawstM /opt/COAWST/COAWST_COMMIT /opt/COAWST/PATCHES_APPLIED ./
COPY --from=build /opt/COAWST/build_coawst.sh /opt/COAWST/build.log ./build/
COPY --from=build /opt/COAWST/ROMS/External/varinfo.yaml ./ROMS/External/
COPY --from=build /opt/COAWST/${CASE_DIR} ./${CASE_DIR}

# Containers (and Cloud Batch) run as root, which OpenMPI refuses by default.
# The vader setting avoids a ptrace error for shared-memory copies in Docker.
ENV PATH=${COAWST_ROOT}:${PATH} \
    OMPI_ALLOW_RUN_AS_ROOT=1 \
    OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1 \
    OMPI_MCA_btl_vader_single_copy_mechanism=none

CMD ["bash"]
