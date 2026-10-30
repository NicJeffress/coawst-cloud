# COAWST (ROMS + SWAN coupled through MCT), no WRF / WW3.
#
# Build with build.sh (it assembles the build context, including your case):
#   build/coawst/build.sh                       stock Inlet_test (Coupled)
#   build/coawst/build.sh --case DIR --app NAME your case (DIR holds name.h, .in files)
# Build arguments (pass after -- to build.sh):
#   COAWST_REF=<commit sha>      COAWST commit to build
#   SERIES=none                  build without our patches (stock COAWST)
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
