"""Generate the SWAN patches of the series against COAWST commit 26e6fb7.

Usage: python3 -I make_swan_patches.py <COAWST tree>/SWAN/src <build/coawst/patches> [--without NAME[,NAME]]

Reads the unpatched SWAN sources and writes the SWAN patches listed in GROUPS
(at the end) into the patch folder, one per group. Each change_* function below
is one change, named as in the patch documents (e.g. periodic_y_strips in
1-fixes/swan-periodic-fixes.md); the changes edit the source text by search and
replace and stop with a message if the text they expect is not there. GROUPS runs them in the order of the series
(fixes first, then improvements), and each patch holds the changes of its group
relative to the source after the groups before it, so the patches apply in that
order. tests/same_source/compare_series.sh checks a regenerated series against
the previous one.
"""
import difflib
import re
import sys
from pathlib import Path

src, out = Path(sys.argv[1]), Path(sys.argv[2])   # SWAN/src, patch folder
# --without NAME[,NAME...]: leave those changes out (for tests that compare a
# build with and without one change, e.g. --without periodic_coupled_stokes)
WITHOUT = set()
if "--without" in sys.argv:
    WITHOUT = set(sys.argv[sys.argv.index("--without") + 1].split(","))


def load(name):
    return (src / name).read_text().splitlines(keepends=True)


def replace_once(lines, old, new, name):
    hits = [i for i, l in enumerate(lines) if old in l]
    if len(hits) != 1:
        sys.exit(f"{name}: expected 1 match for {old!r}, found {len(hits)}")
    lines[hits[0]] = lines[hits[0]].replace(old, new)


# Energy-type quantities are in W m-2 with SET INRHOG 1 (required for COAWST
# coupling) and m2 s-1 with INRHOG 0.
E = " (m2 s-1 if INRHOG=0)"

# New NetCDF quantities: (SWAN IVTYPE, STNAMES column, nc name, long name, units).
# Column 2 is the second component of a vector quantity. A long name of None
# means the record already exists in nctablemd and only the STNAMES entry is new.
new_vars = [
    (7, 1, "dissip", "total wave energy dissipation" + E, "W m-2"),
    (8, 1, "qb", "fraction of breaking waves", "1"),
    (9, 1, "leak", "energy leak over spectral boundaries" + E, "W m-2"),
    (15, 1, "tdir", "direction of the energy transport", "degree"),
    (18, 1, "steepness", "wave steepness", "1"),
    (19, 1, "xtra", "x component of wave energy transport (m3 s-1 if INRHOG=0)", "W m-1"),
    (19, 2, "ytra", "y component of wave energy transport (m3 s-1 if INRHOG=0)", "W m-1"),
    (20, 1, "xfor", "x component of wave driven force per unit surface", "N m-2"),
    (20, 2, "yfor", "y component of wave driven force per unit surface", "N m-2"),
    (27, 1, "fric", "bottom friction coefficient", "1"),
    (33, 1, "fspr", "frequency spectral width (kappa)", "1"),
    (36, 1, "zlen", "zero velocity thickness of boundary layer", "m"),
    (39, 1, "setup", "setup due to waves", "m"),
    (42, 1, "per", "average absolute wave period (PER)", "s"),
    (43, 1, "rper", "average relative wave period (RPER)", "s"),
    (45, 1, "ursell", "Ursell number", "1"),
    (46, 1, "astd", None, None),
    (49, 1, "difpar", "diffraction parameter", "1"),
    (50, 1, "tmbot", "near bottom wave period", "s"),
    (54, 1, "disbot", "bottom friction dissipation" + E, "W m-2"),
    (55, 1, "dissurf", "surf breaking dissipation" + E, "W m-2"),
    (56, 1, "diswcap", "whitecapping dissipation" + E, "W m-2"),
    (57, 1, "disveg", "vegetation dissipation" + E, "W m-2"),
    (58, 1, "qp", "peakedness of the wave spectrum", "1"),
    (59, 1, "bfi", "Benjamin-Feir index", "1"),
    (60, 1, "genera", "total energy generation" + E, "W m-2"),
    (61, 1, "genwind", "wind source term" + E, "W m-2"),
    (62, 1, "redist", "total energy redistribution" + E, "W m-2"),
    (63, 1, "redquad", "total absolute 4-wave interaction" + E, "W m-2"),
    (64, 1, "redtriad", "total absolute 3-wave interaction" + E, "W m-2"),
    (65, 1, "propagat", "total energy propagation" + E, "W m-2"),
    (66, 1, "propxy", "xy-propagation" + E, "W m-2"),
    (67, 1, "propthet", "theta-propagation" + E, "W m-2"),
    (68, 1, "propsigm", "sigma-propagation" + E, "W m-2"),
    (69, 1, "radstr", "energy transfer by radiation stress" + E, "W m-2"),
    (70, 1, "npl", "number of plants per square meter", "m-2"),
    (71, 1, "lwavp", "peak wave length", "m"),
    (72, 1, "disturb", "turbulent dissipation" + E, "W m-2"),
    (73, 1, "turb", "turbulent viscosity", "m2 s-1"),
    (74, 1, "dismud", "fluid mud dissipation" + E, "W m-2"),
    (75, 1, "disswell", "swell dissipation" + E, "W m-2"),
    (76, 1, "disice", "sea ice dissipation" + E, "W m-2"),
    (77, 1, "aice", "sea ice concentration (fraction)", "1"),
    (78, 1, "hice", "sea ice thickness", "m"),
    (79, 1, "redbragg", "total absolute Bragg scattering" + E, "W m-2"),
    (80, 1, "redqcm", "total absolute quasi-coherent scattering" + E, "W m-2"),
    (81, 1, "hig", "bound infragravity wave height", "m"),
    (82, 1, "gamma", "breaker index", "1"),
    (83, 1, "biphase", "biphase", "degree"),
    (171, 1, "npartitions", None, None),
    (200, 1, "dirbot", "average bottom wave direction", "degree"),
    (201, 1, "dicd", "spectral drag coefficient (vegetation)", "1"),
]
for k in range(6, 10):
    new_vars += [
        (100 + k, 1, f"phs{k}", f"significant wave height of partition {k}", "m"),
        (110 + k, 1, f"ptp{k}", f"relative peak period of partition {k}", "s"),
        (130 + k, 1, f"pdir{k}", f"mean wave direction of partition {k}", "degree"),
        (140 + k, 1, f"pspr{k}", f"directional spread of partition {k}", "degree"),
    ]
for k in range(10):
    new_vars += [
        (120 + k, 1, f"pwlen{k}", f"average wave length of partition {k}", "m"),
        (150 + k, 1, f"pwfrac{k}", f"wind fraction of partition {k}", "1"),
        (160 + k, 1, f"psteep{k}", f"wave steepness of partition {k}", "1"),
    ]
new_recs = [v for v in new_vars if v[3] is not None]

files = {}



# Helpers used by several changes.


def check_columns(lines, name):
    """Fixed-form source: changed code must end by column 72 once switch.pl
    has removed the !WFR / !MPI prefixes."""
    for l in set(lines) - set(load_original(name)):
        code = re.sub(r"^(!WFR)?(!MPI)?", "", l.rstrip("\n"))
        code = re.sub(r"\s+\d+\.\d+[A-Z]?(\s+\d+\.\d+[A-Z]?)*\s*$", "", code)  # version tags
        if not code.startswith("!") and len(code.split("!")[0].rstrip()) > 72:
            sys.exit(f"{name}: line exceeds column 72: {l!r}")


def find(lines, regex, name, lo=0, hi=None, count=1):
    hits = [i for i in range(lo, len(lines) if hi is None else hi) if re.search(regex, lines[i])]
    if len(hits) != count:
        sys.exit(f"{name}: expected {count} match(es) for {regex!r}, found {len(hits)}")
    return hits


def insert_after(lines, regex, new, name, lo=0, hi=None):
    i = find(lines, regex, name, lo, hi)[0]
    lines[i + 1:i + 1] = new


def replace_lines(lines, regex, new, name, count=1):
    for i in reversed(find(lines, regex, name, count=count)):
        lines[i:i + 1] = new


def wfr(text):
    """Code lines with the wavefront tag; cpp lines as they are."""
    out = []
    for l in text.strip("\n").splitlines():
        l = l if l.startswith("#") else "!WFR" + l
        if not l.startswith("#") and len(l) - 4 > 72:
            sys.exit(f"halo_exchange_nonblocking: line longer than 72 columns: {l}")
        out.append(l + "\n")
    return out


def replace_block(sub, first, last, new):
    i = next(k for k, l in enumerate(sub) if l.startswith(first))
    j = next(k for k in range(i, len(sub)) if sub[k].startswith(last))
    return sub[:i] + new + sub[j + 1:]


def change_nc_filename_length():
    # nc_filename_length: ocpmix.ftn: FOR used a fixed 140-char dummy for its filename argument.
    #    Fixed-form source: pad 5 spaces so the version tag stays past column 72.
    name = "ocpmix.ftn"
    lines = load(name)
    replace_once(lines, "      CHARACTER DDNAME*(LENFNM), SF*2     ",
                 "      CHARACTER DDNAME*(*), SF*2          ", name)
    files[name] = lines


def change_stnames_size():
    # stnames_size: swn_outnc.ftn90: the name table STNAMES(171,2) is indexed with
    #     COAWST's quantity numbers (IVTYPE) up to 202 (DIRBOT, DICD, SSPEC):
    #     enlarge it to 202.
    name = "swn_outnc.ftn90"
    lines = load(name)
    replace_once(lines, "STNAMES(171,2) = ''", "STNAMES(202,2) = ''", name)
    files[name] = lines


def change_netcdf_names():
    global stnames
    # netcdf_names: swn_outnc.ftn90: NetCDF names for the quantities that netcdf_records adds.
    name = "swn_outnc.ftn90"
    lines = load(name)
    end = [i for i, l in enumerate(lines) if "stnames_initialized = .true." in l]
    if len(end) != 1:
        sys.exit(f"{name}: stnames_init end not found")
    existing = {(int(m.group(1)), int(m.group(2))): m.group(3) for m in
                re.finditer(r"STNAMES\(\s*(\d+),\s*(\d)\)\s*=\s*'([^']+)'", "".join(lines))}
    for iv, col, nc, _, _ in new_vars:
        if (iv, col) in existing:
            sys.exit(f"{name}: STNAMES({iv},{col}) already set to {existing[(iv, col)]!r}")
    added = [f"        STNAMES({iv:3d}, {col}) = '{nc}'\n" for iv, col, nc, _, _ in sorted(new_vars)]
    lines[end[0]:end[0]] = added
    files[name] = lines
    stnames = set(existing.values()) | {v[2] for v in new_vars}


def change_netcdf_records():
    global n_new
    # netcdf_records: nctablemd.ftn90: store everything as 32-bit float; add records.
    name = "nctablemd.ftn90"
    lines = load(name)
    n_old = 66
    n_new = n_old + len(new_recs)
    records = set(re.findall(r'nctable_record\("([^"]+)"', "".join(lines)))
    clash = records & {v[2] for v in new_recs}
    if clash:
        sys.exit(f"{name}: records already exist for {sorted(clash)}")
    unmatched = stnames - records - {v[2] for v in new_recs}
    if unmatched:
        sys.exit(f"{name}: STNAMES without a table record: {sorted(unmatched)}")
    replace_once(lines, f":: nctable({n_old})", f":: nctable({n_new})", name)
    lines = [l.replace("NF90_SHORT", "NF90_FLOAT").replace("NF90_BYTE", "NF90_FLOAT")
              .replace("nf90_byte", "NF90_FLOAT") for l in lines]
    last = [i for i, l in enumerate(lines) if f"nctable({n_old}) / nctable_record" in l]
    if len(last) != 1:
        sys.exit(f"{name}: last record not found")
    close = last[0] + 3          # line ending the final record with "variddum) /"
    if not lines[close].rstrip().endswith("variddum) /"):
        sys.exit(f"{name}: unexpected end of data statement: {lines[close]!r}")
    lines[close] = lines[close].rstrip("\n") + ", &\n"
    recs = []
    for j, (iv, col, nc, lname, units) in enumerate(new_recs):
        sep = ", &" if j < len(new_recs) - 1 else ""
        recs += [
            f'             nctable({n_old + 1 + j}) / nctable_record("{nc}",&\n',
            '                            "none",&\n',
            f'                            "{lname}", &\n',
            f'                            "{units}", NF90_FLOAT, 0., 0., variddum) /{sep}\n',
        ]
    lines[close + 1:close + 1] = recs
    files[name] = lines


def change_netcdf_float():
    # netcdf_float: agioncmd.ftn90: never add packing attributes to float variables.
    name = "agioncmd.ftn90"
    lines = load(name)
    replace_once(lines, "            if ( rng /= 0 ) then",
                 "            if ( rng /= 0 .and. trecord%nctype /= NF90_FLOAT ) then", name)
    files[name] = lines


def change_stop_on_input_errors():
    # stop_on_input_errors: waves_control.ftn: COAWST carried on into the run (and the first coupling
    #    exchange) even when SWAN_INITIALIZE reported input errors, e.g. a rejected
    #    output request, which then led to out-of-bounds writes in SWOEXC. Stop the
    #    whole MPI job instead, after flushing the PRINT file (MPI_ABORT would
    #    lose the buffered messages). Fixed-form source: code stays within
    #    column 72.
    name = "waves_control.ftn"
    lines = load(name)
    replace_once(lines, "      USE OCPCOMM4, ONLY: SCREEN\n",
                 "      USE OCPCOMM4, ONLY: SCREEN, PRINTF, LEVERR, MAXERR\n", name)
    call = [i for i, l in enumerate(lines)
            if l.strip() == "CALL SWAN_INITIALIZE (NUM_SGRIDS, MyCOMM, Wname(ng))"]
    if len(call) != 1:
        sys.exit(f"{name}: SWAN_INITIALIZE call not found exactly once")
    stop = [
        "!       Do not run with a SWAN setup that has input errors.\n",
        "        IF (LEVERR.GT.MAXERR .AND. MAXERR.NE.-1) THEN\n",
        "          WRITE (SCREEN,'(A,I3,A)') ' SWAN input error level',\n",
        "     &      LEVERR, ' > MAXERR: stopping, see SWAN PRINT file'\n",
        "          LEVERR = MAX(LEVERR, 4)\n",
        "          FLUSH (PRINTF)\n",
        "          CALL SWEXITMPI\n",
        "        END IF\n",
    ]
    for l in stop:
        if not l.startswith("!") and len(l.rstrip("\n")) > 72:
            sys.exit(f"{name}: line exceeds column 72: {l!r}")
    lines[call[0] + 1:call[0] + 1] = stop
    files[name] = lines


def change_table_nc_coordinates():
    # table_nc_coordinates: swanparll.ftn: with more than one SWAN process, TABLE output to .nc is
    #    merged by SWCOLBLK, which wrote the coordinates of the first grid cells
    #    (XGRDGL) as the point locations. Pass the output point coordinates
    #    XP/YP from SWCOLOUT and use them for TABLE. Lines starting !NCF are
    #    code when SWAN is built with NetCDF.
    name = "swanparll.ftn"
    lines = load(name)
    replace_once(lines, "!NCF     &                            BLKND, XC, YC )\n",
                 "!NCF     &                            BLKND, XC, YC, XP, YP )\n", name)
    replace_once(lines, "     &                            BLKND, XC, YC )                         40.51 40.41\n",
                 "     &                            BLKND, XC, YC, XP, YP )\n", name)
    replace_once(lines, "     &                      XC    , YC )                                  40.51\n",
                 "     &                      XC    , YC    , XP    , YP )\n", name)
    decl = "      REAL      BLKND(MXCGL,MYCGL), XC(MXK*MYK), YC(MXK*MYK)              40.51\n"
    hits = [i for i, l in enumerate(lines) if l == decl]
    if len(hits) != 1:
        sys.exit(f"{name}: SWCOLBLK declaration not found exactly once")
    lines.insert(hits[0] + 1, "      REAL      XP(MXK*MYK), YP(MXK*MYK)\n")
    start = [i for i, l in enumerate(lines) if l.startswith("      SUBROUTINE SWCOLBLK")][0]
    opt = [i for i, l in enumerate(lines)
           if i > start and l == "!NCF                IF (OPTG.NE.5) THEN\n"]
    if not opt or lines[opt[0] + 1][4:].strip() != "CALL swn_outnc_openblockfile(FILENM, MYK, MXK,":
        sys.exit(f"{name}: openblockfile call in SWCOLBLK not found")
    tab = [
        "!NCF                IF (RTYPE.EQ.'TABC') THEN\n",
        "!NCF!                  TABLE: locations of the output points\n",
        "!NCF                  CALL swn_outnc_openblockfile(FILENM, MYK, MXK,\n",
        "!NCF     &                                         OVLNAM, XP, YP,\n",
        "!NCF     &                                         OQI, OQR, IVTYP, IRQ)\n",
        "!NCF                ELSE IF (OPTG.NE.5) THEN\n",
    ]
    lines[opt[0]:opt[0] + 1] = tab
    for l in set(lines) - set(load_original(name)):
        code = l[4:] if l.startswith("!NCF") and not l.startswith("!NCF!") else l
        if not code.startswith("!"):
            if len(code.rstrip("\n")) > 72:
                sys.exit(f"{name}: line exceeds column 72: {l!r}")
    files[name] = lines


def change_compgrid_nc_coordinates():
    # compgrid_nc_coordinates: swanout2.ftn (SWBLOK): with one SWAN process, BLOCK output on COMPGRID
    #    took its x/y from the XP/YP output quantities, which SWOEXC sets to the
    #    exception value (-1e10) at inactive grid points (bottom exception value,
    #    e.g. land). With several processes SWCOLBLK writes the grid coordinates
    #    (XGRDGL + XOFFS). Write the grid coordinates in the serial case too.
    #    Other frames keep XP/YP (computed there without masking).
    name = "swanout2.ftn"
    lines = load(name)
    replace_once(lines, "      USE SWCOMM3, ONLY: NSTATM                                           41.62\n",
                 "      USE SWCOMM3, ONLY: NSTATM, MXC, MYC\n", name)
    use = [i for i, l in enumerate(lines) if l.startswith("      USE OUTP_DATA")]
    if not use or use[0] > 60:
        sys.exit(f"{name}: USE OUTP_DATA in SWBLOK not found")
    lines[use[0] + 1:use[0] + 1] = [
        "      USE SWCOMM2, ONLY: OPTG, XOFFS, YOFFS\n",
        "      USE M_GENARR, ONLY: XCGRID, YCGRID\n",
    ]
    call = [
        "!NCF        CALL swn_outnc_openblockfile(FILENM, MYK, MXK,\n",
        "!NCF     &                               OVLNAM, VOQ(:,VOQR(1)),\n",
        "!NCF     &                               VOQ(:,VOQR(2)),\n",
        "!NCF     &                               OQI, OQR, IVTYP, IRQ)\n",
    ]
    hits = [i for i in range(len(lines)) if lines[i:i + 4] == call]
    if len(hits) != 1:
        sys.exit(f"{name}: openblockfile call in SWBLOK not found exactly once")
    lines[hits[0]:hits[0] + 4] = [
        "!NCF        IF (PSNAME.EQ.'COMPGRID' .AND. OPTG.NE.5 .AND.\n",
        "!NCF     &      MXK.EQ.MXC .AND. MYK.EQ.MYC) THEN\n",
        "!NCF!         grid coordinates, also at inactive points\n",
        "!NCF          CALL swn_outnc_openblockfile(FILENM, MYK, MXK,\n",
        "!NCF     &                                 OVLNAM, XCGRID+XOFFS,\n",
        "!NCF     &                                 YCGRID+YOFFS,\n",
        "!NCF     &                                 OQI, OQR, IVTYP, IRQ)\n",
        "!NCF        ELSE\n",
        "!NCF          CALL swn_outnc_openblockfile(FILENM, MYK, MXK,\n",
        "!NCF     &                                 OVLNAM, VOQ(:,VOQR(1)),\n",
        "!NCF     &                                 VOQ(:,VOQR(2)),\n",
        "!NCF     &                                 OQI, OQR, IVTYP, IRQ)\n",
        "!NCF        END IF\n",
    ]
    for l in set(lines) - set(load_original(name)):
        code = l[4:] if l.startswith("!NCF") and not l.startswith("!NCF!") else l
        if not code.startswith("!"):
            if len(code.rstrip("\n")) > 72:
                sys.exit(f"{name}: line exceeds column 72: {l!r}")
    files[name] = lines


def change_block_point_owner():
    # block_point_owner: In a parallel run each process outputs the BLOCK
    #     points it owns (SWOEXC marks them in IONOD), and SWCOLBLK merges the
    #     process files, taking each point from the process the global map
    #     BLKND names. Both turned a point's grid coordinate (0-based) into an
    #     index by INT(XC) + 1, except when XC is a whole number other than 0
    #     (only BLKV output always added 1). A point on grid line k > 0 thus
    #     got index k instead of k+1: one row off. The first row of each
    #     process's strip was then output by the process below it, as its
    #     first halo row. That is harmless for quantities computed from the
    #     spectrum, but FORCE (SWOEXF) also needs Hs (COMPDA) at the rows
    #     either side, and Hs is only set up to the first halo row: the point
    #     got the exception value, so FORCE lost one row at every strip
    #     boundary. Now every BLOCK point on a grid line gets index k+1, in
    #     SWOEXC and SWCOLBLK alike, so each row is output by the process that
    #     computes it.
    name = "swanout1.ftn"
    lines = load(name)
    lo = find(lines, r"^      SUBROUTINE SWOEXC ", name)[0]
    i = find(lines, r"^            IF \( \.NOT\.EQREAL\(XC\(IP\),RVAL1\) \.OR\. EQREAL\(XC\(IP\),0\.\) \.OR\.$", name, lo)[0]
    lines[i:i] = ["!           swan-force-strip-rows (block_point_owner): a BLOCK point on\n",
                  "!           grid line k (0-based) is index k+1, as SWCOLBLK takes it\n"]
    replace_lines(lines, r"^     &           RTYPE\.EQ\.'BLKV' \) IX = IX \+ 1$",
                  ["     &           RTYPE(1:3).EQ.'BLK' ) IX = IX + 1\n"], name)
    replace_lines(lines, r"^     &           RTYPE\.EQ\.'BLKV' \) IY = IY \+ 1$",
                  ["     &           RTYPE(1:3).EQ.'BLK' ) IY = IY + 1\n"], name)
    check_columns(lines, name)
    files[name] = lines

    name = "swanparll.ftn"
    lines = load(name)
    lo = find(lines, r"^      SUBROUTINE SWCOLBLK ", name)[0]
    hi = find(lines, r"^!JAC      SUBROUTINE SWBLKCOL ", name)[0]
    n = 0
    k = lo
    while True:
        hits = [j for j in range(k, hi) if re.match(r"^ +IF \( \.NOT\.EQREAL\(XC\(IP\),RVAL1\) \.OR\.$", lines[j])]
        if not hits:
            break
        j = hits[0]
        ind = lines[j][:len(lines[j]) - len(lines[j].lstrip())]
        assert re.match(r"^     & +EQREAL\(XC\(IP\),0\.   \) \) IXK = IXK \+ 1$", lines[j + 1])
        assert re.match(r"^ +IF \( \.NOT\.EQREAL\(YC\(IP\),RVAL2\) \.OR\.$", lines[j + 2])
        assert re.match(r"^     & +EQREAL\(YC\(IP\),0\.   \) \) IYK = IYK \+ 1$", lines[j + 3])
        lines[j:j + 4] = ["!" + ind[1:] + "swan-force-strip-rows (block_point_owner): a point on\n",
                          "!" + ind[1:] + "grid line k (0-based) is index k+1, as in SWOEXC\n",
                          ind + "IXK = IXK + 1\n",
                          ind + "IYK = IYK + 1\n"]
        n += 1
        k = j + 4
    if n != 2:
        sys.exit(f"{name}: expected 2 index blocks in SWCOLBLK, changed {n}")
    check_columns(lines, name)
    files[name] = lines


def change_veg3_young_modulus():
    # veg3_young_modulus: swanpre1.ftn (VEGEtation command): iveg 3 selects COAWST's SVEG_COAWST,
    #    which reads Young's modulus VEGYML(1), but only the VEGCtation command
    #    (iveg 2) allocates VEGYML, so `VEGETATION 3 ...` read an unallocated
    #    array. Allocate it here with a rigid default (1e9 Pa, as in COAWST
    #    v3.7's VEGCoawst line) when the command did not set it.
    name = "swanpre1.ftn"
    lines = load(name)
    alloc = "        IF (.NOT.ALLOCATED(VEGDRL)) ALLOCATE(VEGDRL(ILMAX))\n"
    hits = [i for i, l in enumerate(lines) if l == alloc]
    if len(hits) != 2 or "VEGE" not in "".join(lines[hits[0] - 60:hits[0]]):
        sys.exit(f"{name}: VEGEtation allocation block not found as expected")
    lines[hits[0] + 1:hits[0] + 1] = [
        "!       SVEG_COAWST (iveg 3) reads Young's modulus; default: rigid\n",
        "        IF (.NOT.ALLOCATED(VEGYML)) THEN\n",
        "          ALLOCATE(VEGYML(ILMAX))\n",
        "          VEGYML = 1.E9\n",
        "        END IF\n",
    ]
    for l in set(lines) - set(load_original(name)):
        if not l.startswith("!") and len(l.rstrip("\n")) > 72:
            sys.exit(f"{name}: line exceeds column 72: {l!r}")
    files[name] = lines


def change_veg3_flexible_plants():
    # veg3_flexible_plants: swancom2.ftn (SVEG_COAWST, flexible vegetation): the second moment of
    #    area was VEGDIL*VEGTHK**(3./12.) (thickness^0.25; operator precedence)
    #    and the Cauchy number divided by CFF2+MAX_EPS (1e12), so the Cauchy
    #    number was always ~0 and every plant behaved as rigid. ROMS's own
    #    vegetation_drag.F (VEG_FLEX) uses diam*thck**3/12 and divides by
    #    MAX(E*I, min_eps); CFF2 here is already MAX(E*I, MIN_EPS).
    name = "swancom2.ftn"
    lines = load(name)
    replace_once(lines, "            SMA        = VEGDIL_LOC*VEGTHK_LOC**(3./12.) \n",
                 "            SMA        = VEGDIL_LOC*VEGTHK_LOC**3/12.\n", name)
    replace_once(lines, "            CAUCHY_NUM = MIN(CFF1/(CFF2+MAX_EPS), MAX_EPS)\n",
                 "            CAUCHY_NUM = MIN(CFF1/CFF2, MAX_EPS)\n", name)
    files[name] = lines


def change_plant_input_grids():
    # plant_input_grids: Plant height/diameter/thickness input grids are registered as grids
    #     18/19/20 (INPGRID and READINP, swanpre1.ftn) but SWRBC and the
    #     unstructured branch (swanmain.ftn) interpolated them with grids
    #     16/17/18 (the sea-swell HSS/TSS/DSS grids of SWAN 41.51), i.e. with
    #     an undefined grid geometry: garbage plant properties, or a segfault
    #     in SVALQI/EQREAL at startup (seen on Batch with 12 ROMS + 4 SWAN).
    #     Also INPGRID NPHT set VARNPL instead of VARNPH (READINP sets VARNPH).
    name = "swanmain.ftn"
    lines = load(name)
    for q, old, new in (("NPHTF", 16, 18), ("NPDAF", 17, 19), ("NPTKF", 18, 20)):
        hits = [i for i, l in enumerate(lines) if f"= SVALQI (XP, YP, {old}, {q}, 1 ," in l]
        if len(hits) != 2:
            sys.exit(f"{name}: expected 2 SVALQI calls for {q}, found {len(hits)}")
        for i in hits:
            lines[i] = lines[i].replace(f"SVALQI (XP, YP, {old}, {q},", f"SVALQI (XP, YP, {new}, {q},")
    files[name] = lines
    name = "swanpre1.ftn"
    lines = load(name)          # already changed by veg3_young_modulus
    start = [i for i, l in enumerate(lines) if "ELSE IF (KEYWIS ('NPHT')) THEN" in l][0]
    nxt = [i for i in range(start, start + 8) if "VARNPL = .TRUE." in lines[i]]
    if len(nxt) != 1:
        sys.exit(f"{name}: VARNPL line in INPGRID NPHT not found")
    lines[nxt[0]] = lines[nxt[0]].replace("VARNPL = .TRUE.", "VARNPH = .TRUE.")
    files[name] = lines




def change_periodic_compgrid_frame():
    # periodic_compgrid_frame: swanpre1.ftn (CGRID): with COORDINATES ... REPEATING the grid has MXC
    #     points x = 0 .. XCLEN-DX (x = XCLEN is x = 0 again), but the built-in
    #     COMPGRID output frame spread its MXC points over 0 .. XCLEN, so BLOCK
    #     output on COMPGRID was interpolated between grid points (spacing
    #     XCLEN/(MXC-1)) and many points came out as exception values.
    name = "swanpre1.ftn"
    lines = load(name)          # already changed by veg3_young_modulus and plant_input_grids
    hits = [i for i, l in enumerate(lines) if "%OPR(3) = XCLEN" in l]
    if len(hits) != 2:
        sys.exit(f"{name}: expected 2 COMPGRID frame definitions, found {len(hits)}")
    for i in reversed(hits):
        target = lines[i].split("=")[0].strip()          # ...%OPR(3)
        lines[i + 1:i + 1] = [
            "!             REPeating grid: MXC points end one mesh before XCLEN\n",
            "              IF (KREPTX.EQ.1)\n",
            f"     &          {target} = XCLEN - DX\n",
        ]
    check_columns(lines, name)
    files[name] = lines


def change_periodic_y_strips():
    # periodic_y_strips: With COORDINATES ... REPEATING and more than one SWAN process, SWAN cut
    #     the grid into x-strips whenever MXC > MYC, but its halo exchange never
    #     wraps around in x: the strips at the periodic seam got no neighbour
    #     data (segfault in SWRECVAC, or garbage wave heights). Always cut a
    #     periodic grid into y-strips, so each process holds the whole period.
    #     The strip direction is decided from MXC > MYC (MXCGL > MYCGL) in the
    #     partitioner, the sweep pipeline, output collection, nesting and the
    #     COAWST coupler; all of them get ".AND.KREPTX.EQ.0".
    XSTRIPS = re.compile(r"\bMXC(GL)?\s*\.gt\.\s*MYC(GL)?\b", re.I)
    need_use = {"swanparll.ftn": ("SWPARTIT", "SWBLADM", "SWCOLLECT"),
                "swanpre3.ftn": ("swan_ref_init",)}
    expected = {"swanparll.ftn": 4, "swancom1.ftn": 4, "swanmain.ftn": 2,
                "swanpre3.ftn": 1, "waves_coupler.ftn": 11}
    for name, count in expected.items():
        lines = load(name)
        hits = [i for i, l in enumerate(lines)
                if XSTRIPS.search(l) and not l.startswith("!JAC")
                and (not l.lstrip().startswith("!") or l.startswith("!WFR"))]
        if len(hits) != count:
            sys.exit(f"{name}: expected {count} strip-direction tests, found {len(hits)}")
        for i in reversed(hits):                         # a split adds a line
            l = lines[i].rstrip("\n")
            code, tag = (l[:72].rstrip(), "") if l.startswith("!") else (l, "")
            if l.startswith("!WFR"):                     # drop the version tag
                code = re.sub(r"\s+\d+\.\d+(\s+\d+\.\d+)*\s*$", "", l)
            new = XSTRIPS.sub(lambda m: f"({m.group(0).upper().replace(' ', '')}"
                                        ".AND.KREPTX.EQ.0)", code)
            prefix = re.match(r"^(!WFR)?(!MPI)?", new).group(0)
            if len(new) - len(prefix) > 72 and " .OR. " in new:
                head, tail = new.split(" .OR. ", 1)
                lines[i:i + 1] = [f"{head} .OR.\n", f"{prefix}     &       {tail}\n"]
            else:
                lines[i] = new + "\n"
        for routine in need_use.get(name, ()):
            start = [i for i, l in enumerate(lines)
                     if re.match(rf"^\s+SUBROUTINE\s+{routine}\b", l, re.I)]
            use = [i for i in range(start[0], start[0] + 80)
                   if re.match(r"^\s+USE M_PARALL\b", lines[i])]
            if len(start) != 1 or not use:
                sys.exit(f"{name}: USE M_PARALL in {routine} not found")
            lines.insert(use[0] + 1, "      USE SWCOMM4, ONLY: KREPTX\n")
        check_columns(lines, name)
        files[name] = lines


def change_periodic_curvilinear():
    # periodic_curvilinear: COORDINATES ... REPEATING on curvilinear grids (SWAN stopped with
    #     "Curvilinear grid cannot be REPeating"). The wrap itself is in index
    #     space (IXCGRD +- MXC) and grid-type independent; what needs the period
    #     is every place that differences coordinates of neighbours across the
    #     seam, and the search for output locations.
    #     - READGRID COORDINATES reads one extra column, column 1 shifted by one
    #       period (the same file as for the non-periodic grid); the period
    #       vector (XCPER,YCPER) is the difference, checked to be the same in
    #       every row (new routine CVPERI). For regular grids XCPER/YCPER are
    #       set from the grid too.
    #     - SWGEOM (upwind stencil geometry) and SPREDT (CURV option) add or
    #       subtract the period when the upwind x-neighbour is across the seam.
    #     - SWOEXF (FORCE output): same for its x-derivatives; this also fixes
    #       FORCE at the seam of regular REPEATING grids.
    #     - CVMESH (output locations): new wrapper that tries the point shifted
    #       by whole periods; NEWTON also searches the cell between column MXC
    #       and column 1 + period; XC is returned in 0 <= XC < MXC, as for
    #       regular repeating grids. SINCMP accepts such points.






    name = "swmod1.ftn"
    lines = load(name)
    insert_after(lines, r"^!\s+in subroutine SANDL\)", [
        "! XCPER  [    0.] x component of the period vector of a repeating grid (KREPTX>0): grid\n",
        "!                 column MXC+1 (not stored) is column 1 shifted by (XCPER,YCPER)\n",
        "! YCPER  [    0.] y component of that period vector\n"], name)
    insert_after(lines, r"^      REAL    WAVAGE,    REARTH,    LENDEG", ["      REAL    XCPER,     YCPER\n"], name)
    files[name] = lines

    name = "swanmain.ftn"
    lines = load(name)                  # already changed by plant_input_grids and periodic_y_strips
    insert_after(lines, r"^      KREPTX = 0 ", ["      XCPER  = 0.\n", "      YCPER  = 0.\n"], name)
    i = find(lines, r"LOGICAL FUNCTION SINCMP", name)[0]
    insert_after(lines, r"^      USE SWCOMM3\b", ["      USE SWCOMM4\n"], name, i, i + 80)
    replace_lines(lines, r"^        IF \(XC \.GT\. REAL\(MXC-1\)\+0\.01\) SINCMP = \.FALSE\.", [
        "!       REPeating grid: XC may lie between column MXC and the next one,\n",
        "!       column 1 shifted by one period (see CVMESH)\n",
        "        IF (XC .GT. REAL(MXC-1)+0.01 .AND. KREPTX.EQ.0) SINCMP = .FALSE.\n"], name)
    i = find(lines, r'"GE" changed to "EQ" since OPTG\.EQ\.3', name)[0]
    if "Curvilinear grid cannot be REPeating" not in lines[i + 2]:
        sys.exit(f"{name}: curvilinear REPeating stop not found")
    lines[i:i + 3] = [
        "!       --- curvilinear: the period comes from READGRID COORDINATES,\n",
        "!           which reads one extra column (column 1 shifted by a period)\n",
        "        IF (OPTG.EQ.3 .AND. XCPER.EQ.0. .AND. YCPER.EQ.0.)\n",
        "     &  CALL MSGERR (3, 'REPeating curvilinear grid: no period found')\n"]
    check_columns(lines, name)
    files[name] = lines

    name = "swanpre1.ftn"
    lines = load(name)                  # already changed by veg3_young_modulus, plant_input_grids and periodic_compgrid_frame
    i = find(lines, r"^              YCGRID\(I,J\)=VALY ", name)[0]
    if not (lines[i + 2].startswith(" 200 ") and lines[i + 3] == "        ENDIF\n"):
        sys.exit(f"{name}: end of the regular grid coordinate loop not found")
    lines[i + 3:i + 3] = [
        "!         period of a REPeating grid: MXC meshes along the grid x-axis\n",
        "          IF (KREPTX.GT.0) THEN\n",
        "            XCPER = COSPC*MXC*DX\n",
        "            YCPER = SINPC*MXC*DX\n",
        "          ENDIF\n"]
    insert_after(lines, r"^        MYG\(IGR2\) = MYC$", [
        "!       REPeating curvilinear grid: the file has one more column, column\n",
        "!       1 shifted by the period (see CVPERI)\n",
        "        IF (KREPTX.GT.0 .AND. OPTG.EQ.3) THEN\n",
        "          MXG(IGR1) = MXC+1\n",
        "          MXG(IGR2) = MXC+1\n",
        "        ENDIF\n"], name)
    replace_lines(lines, r"^         CALL SWCOPR\( TARR, XCGRID, MXG\(IGR1\)\*MYG\(IGR1\) \)",
                  ["         CALL CVPERI( TARR, XCGRID, 1 )\n"], name, count=2)
    replace_lines(lines, r"^           CALL SWCOPR\( TARR, YCGRID, MXG\(IGR2\)\*MYG\(IGR2\) \)",
                  ["           CALL CVPERI( TARR, YCGRID, 2 )\n"], name, count=2)
    i = find(lines, r"^! \* end of subroutine SREDEP \*", name)[0]
    lines[i + 2:i + 2] = """\
!***********************************************************************
!                                                                      *
      SUBROUTINE CVPERI (TARR, CGRID, ICOO)
!                                                                      *
!***********************************************************************
!
!     Copies coordinates read with READGRID COORDINATES (TARR) to the
!     computational grid array CGRID (ICOO=1: x, ICOO=2: y).
!     REPeating curvilinear grid: TARR has MXC+1 columns, the last one
!     being column 1 shifted by one period. CGRID gets columns 1..MXC,
!     and the period vector (XCPER,YCPER) is column MXC+1 minus column
!     1, which must be the same in every row.
!
      USE OCPCOMM4
      USE SWCOMM2
      USE SWCOMM3
      USE SWCOMM4
!
      INTEGER ICOO
      REAL    TARR(*), CGRID(MXC,MYC)
!
      INTEGER IX, IY, I1, NROW
      REAL    PMIN, PMAX, CMAX, EXCV, TOL
      REAL, SAVE :: XSPRD = 0., XCMAX = 0.
!     sum of the row periods in double precision: in single precision the
!     rounding of the growing sum (e.g. 111 rows x 6 km) is centimetres
      DOUBLE PRECISION PER
      LOGICAL EQREAL
!
      IF (KREPTX.EQ.0 .OR. OPTG.NE.3) THEN
         CALL SWCOPR (TARR, CGRID, MXC*MYC)
         RETURN
      ENDIF
      EXCV = EXCFLD(7+ICOO)
      PER  = 0.D0
      PMIN =  1.E30
      PMAX = -1.E30
      CMAX = 0.
      NROW = 0
      DO IY = 1, MYC
         I1 = (IY-1)*(MXC+1)
         DO IX = 1, MXC
            CGRID(IX,IY) = TARR(I1+IX)
         ENDDO
         IF (.NOT.EQREAL(TARR(I1+1),EXCV) .AND.
     &       .NOT.EQREAL(TARR(I1+MXC+1),EXCV)) THEN
            NROW = NROW + 1
            PER  = PER + DBLE(TARR(I1+MXC+1) - TARR(I1+1))
            PMIN = MIN(PMIN, TARR(I1+MXC+1) - TARR(I1+1))
            PMAX = MAX(PMAX, TARR(I1+MXC+1) - TARR(I1+1))
            CMAX = MAX(CMAX, ABS(TARR(I1+1)), ABS(TARR(I1+MXC+1)))
         ENDIF
      ENDDO
      IF (NROW.EQ.0) THEN
         CALL MSGERR (3, 'REPeating curvilinear grid: no row with '//
     &                   'valid first and last coordinates')
         RETURN
      ENDIF
      IF (ICOO.EQ.1) THEN
         XCPER = REAL(PER / DBLE(NROW))
         XSPRD = PMAX - PMIN
         XCMAX = CMAX
      ELSE
         YCPER = REAL(PER / DBLE(NROW))
!        allow for rounding of large (e.g. UTM) single precision values
         TOL = 1.E-4*SQRT(XCPER**2+YCPER**2) + 1.E-6*MAX(XCMAX,CMAX)
         IF (MAX(XSPRD, PMAX-PMIN) .GT. TOL) THEN
            CALL MSGERR (3, 'REPeating curvilinear grid: last column '//
     &                   'is not column 1 shifted by one period')
         ENDIF
         WRITE (PRINTF, '(A,2(1X,E14.7))')
     &      ' REPeating curvilinear grid, period vector (x,y):',
     &      XCPER, YCPER
      ENDIF
      RETURN
! * end of subroutine CVPERI *
      END
""".splitlines(keepends=True)
    check_columns(lines, name)
    files[name] = lines

    name = "swancom5.ftn"
    lines = load(name)
    i = find(lines, r"^      IF \(KREPTX\.GT\.0\) THEN ", name)[0]          # SWGEOM
    if "repeating x-axis (only regular grids)" not in lines[i + 1]:
        sys.exit(f"{name}: SWGEOM repeating branch not found")
    lines[i:i + 2] = ["      IF (KREPTX.GT.0 .AND. OPTG.EQ.1) THEN\n",
                      "!       repeating x-axis, regular grid\n"]
    insert_after(lines, r"^        DY1 = YCGRID\(IXCGRD\(1\),IYCGRD\(1\)\) - YCGRID\(IXCGRD\(2\),IYCGRD\(2\)\)", """\
!       repeating x-axis, curvilinear grid: the upwind neighbour in x
!       of column 1 (sweeps 1, 4) is column MXC shifted back by one
!       period, that of column MXC (sweeps 2, 3) column 1 shifted on
        IF (KREPTX.GT.0) THEN
          IF ((SWPDIR.EQ.1 .OR. SWPDIR.EQ.4) .AND. IXCGRD(1).EQ.1) THEN
            DX1 = DX1 + XCPER
            DY1 = DY1 + YCPER
          ELSE IF ((SWPDIR.EQ.2 .OR. SWPDIR.EQ.3) .AND.
     &             IXCGRD(1).EQ.MXC) THEN
            DX1 = DX1 - XCPER
            DY1 = DY1 - YCPER
          ENDIF
        ENDIF
""".splitlines(keepends=True), name)
    insert_after(lines, r"^      REAL     IDX, IDY, CLAT ", ["      REAL     DXW\n"], name)   # SPREDT
    replace_lines(lines, r"^        IDX=1\./\(XCGRID\(IXCGRD\(1\),IYCGRD\(1\)\)-XCGRID\(IXCGRD\(2\),IYCGRD\(2\)\)\)", """\
        DXW = XCGRID(IXCGRD(1),IYCGRD(1))-XCGRID(IXCGRD(2),IYCGRD(2))
!       repeating x-axis: upwind neighbour across the seam (see SWGEOM)
        IF (KREPTX.GT.0) THEN
          IF ((SWPDIR.EQ.1 .OR. SWPDIR.EQ.4) .AND. IXCGRD(1).EQ.1) THEN
            DXW = DXW + XCPER
          ELSE IF ((SWPDIR.EQ.2 .OR. SWPDIR.EQ.3) .AND.
     &             IXCGRD(1).EQ.MXC) THEN
            DXW = DXW - XCPER
          ENDIF
        ENDIF
        IDX=1./DXW
""".splitlines(keepends=True), name)
    check_columns(lines, name)
    files[name] = lines

    name = "swanout1.ftn"
    lines = load(name)
    i = find(lines, r"SYLO\*\(YCGRID\(JXUP,JYLO\)-YCGRID\(JXLO,JYLO\)\)\)", name)[0]   # SWOEXF
    if lines[i + 1] != "        ENDIF\n":
        sys.exit(f"{name}: SWOEXF x-derivatives not found")
    lines[i + 2:i + 2] = """\
!       repeating grid: JXUP wrapped around to the start of the grid,
!       so its coordinates are one period off
        IF (KREPTX.GT.0 .AND. JXUP.LT.JXLO) THEN
          DXI = DXI + RRDI * XCPER
          DYI = DYI + RRDI * YCPER
        ENDIF
""".splitlines(keepends=True)
    check_columns(lines, name)
    files[name] = lines

    name = "swanser.ftn"
    lines = load(name)
    i = find(lines, r"^      SUBROUTINE CVMESH \(XP, YP, XC, YC, KGRPNT, XCGRID ,YCGRID, KGRBND\)$", name)[0]
    lines[i] = lines[i].replace("SUBROUTINE CVMESH", "SUBROUTINE CVMSH1")
    lines[i - 2:i - 2] = """\
!***********************************************************************
!                                                                      *
      SUBROUTINE CVMESH (XP, YP, XC, YC, KGRPNT, XCGRID ,YCGRID, KGRBND)
!                                                                      *
!***********************************************************************
!
!     Finds the location (XC,YC), in grid index units, of the point
!     (XP,YP) in a curvilinear grid (CVMSH1). REPeating grid: the point
!     may lie in a copy of the grid shifted by whole periods
!     (XCPER,YCPER), or between column MXC and column 1 shifted by one
!     period; XC is then returned in the range 0 <= XC < MXC. CVMSH1
!     only searches that last mesh with its first, short Newton run, so
!     if it fails the mesh is searched explicitly.
!
      USE OCPCOMM4
      USE SWCOMM2
      USE SWCOMM3
      USE SWCOMM4
!
      REAL     XCGRID(MXC,MYC),    YCGRID(MXC,MYC)
      REAL     XP, YP, XC, YC
      INTEGER  KGRPNT(MXC,MYC), KGRBND(*)
!
      INTEGER  IY, NPER, ISH, ITRY, IYMIN, IXK, IYK, ITER, MXITW
      REAL     XPS, YPS, DIS, DISMIN
      LOGICAL  FINDXY
!
      IF (KREPTX.EQ.0 .OR. OPTG.NE.3) THEN
         CALL CVMSH1 (XP, YP, XC, YC, KGRPNT, XCGRID, YCGRID, KGRBND)
         RETURN
      ENDIF
!     whole periods from the first active point of column 1 to (XP,YP);
!     a guess, so the copies one period either side are tried as well
      NPER = 0
      DO IY = 1, MYC
         IF (KGRPNT(1,IY).GT.1) THEN
            NPER = FLOOR(((XP-XCGRID(1,IY))*XCPER +
     &                    (YP-YCGRID(1,IY))*YCPER) /
     &                   (XCPER**2 + YCPER**2))
            EXIT
         ENDIF
      ENDDO
      DO ITRY = 1, 3
         ISH = NPER
         IF (ITRY.EQ.2) ISH = NPER - 1
         IF (ITRY.EQ.3) ISH = NPER + 1
         XPS = XP - REAL(ISH)*XCPER
         YPS = YP - REAL(ISH)*YCPER
         CALL CVMSH1 (XPS, YPS, XC, YC, KGRPNT, XCGRID, YCGRID, KGRBND)
         IF (XC.GT.-98.) THEN
            IF (XC.GE.REAL(MXC)) XC = XC - REAL(MXC)
            RETURN
         ENDIF
      ENDDO
!     Newton search started in the mesh between column MXC and column
!     1 + period, at the row of the nearest point of column MXC
      MXITW = 20
      DO ITRY = 1, 3
         ISH = NPER
         IF (ITRY.EQ.2) ISH = NPER - 1
         IF (ITRY.EQ.3) ISH = NPER + 1
         XPS = XP - REAL(ISH)*XCPER
         YPS = YP - REAL(ISH)*YCPER
         DISMIN = 1.E20
         IYMIN  = 1
         DO IY = 1, MYC
            DIS = (XPS-XCGRID(MXC,IY))**2 + (YPS-YCGRID(MXC,IY))**2
            IF (DIS.LT.DISMIN) THEN
               DISMIN = DIS
               IYMIN  = IY
            ENDIF
         ENDDO
         XC = REAL(MXC) + 0.5
         YC = REAL(IYMIN)
         CALL NEWTON (XPS, YPS, XCGRID, YCGRID, MXITW, ITER, XC, YC,
     &                FINDXY)
         IF (FINDXY) THEN
            IXK = INT(XC+3.001)-2
            IF (IXK.GT.MXC) IXK = IXK - MXC
            IYK = INT(YC+3.001)-2
            IF (KGRPNT(IXK,IYK).LE.1) THEN
               WRITE (PRINTF, '(A,2F12.4,A)') ' point with location ',
     &            XP+XOFFS, YP+YOFFS, ' is not active'
               XC = -99.
               YC = -99.
            ELSE IF (XC.GE.REAL(MXC)) THEN
               XC = XC - REAL(MXC)
            ENDIF
            RETURN
         ENDIF
      ENDDO
      XC = -99.
      YC = -99.
      RETURN
! * end of subroutine CVMESH *
      END
""".splitlines(keepends=True)
    insert_after(lines, r"^      INTEGER       :: IX, IY, K1, IXMIN, IYMIN, IBND$", ["      INTEGER       :: IXK\n"], name)
    replace_lines(lines, r"^  80  IF \(KGRPNT\(INT\(XC\+3\.001\)-2,INT\(YC\+3\.001\)-2\)\.LE\.1\) THEN", [
        "  80  IXK = INT(XC+3.001)-2\n",
        "      IF (KREPTX.GT.0 .AND. IXK.GT.MXC) IXK = IXK - MXC\n",
        "      IF (KGRPNT(IXK,INT(YC+3.001)-2).LE.1) THEN\n"], name)
    lo = find(lines, r"^      SUBROUTINE NEWTON \(", name)[0]
    hi = find(lines, r"^      SUBROUTINE NEWT1D \(", name)[0]
    newton = lines[lo:hi]
    i = find(newton, r"^      INTEGER, SAVE :: IENT = 0$", name)[0]
    newton[i + 1:i + 2] = """\
!     corner coordinates of the current mesh; in a REPeating grid the
!     mesh I1=MXC lies between column MXC and column 1 shifted by one
!     period (XCPER,YCPER), so XC may go up to MXC+1
      REAL    X11, X12, X21, X22, Y11, Y12, Y21, Y22, XCMAX
      IF (LTRACE) CALL STRACE (IENT,'NEWTON')
      XCMAX = REAL(MXC)
      IF (KREPTX.GT.0) XCMAX = REAL(MXC+1)
""".splitlines(keepends=True)
    i = find(newton, r"^        IF \(I1 \.EQ\. MXC\) I1 = I1 - 1$", name)[0]
    if not newton[i + 3].startswith("        J2  = J1 + 1"):
        sys.exit(f"{name}: NEWTON mesh indices not found")
    newton[i:i + 4] = """\
        IF (KREPTX.GT.0) THEN
          IF (I1 .GT. MXC) I1 = MXC
        ELSE
          IF (I1 .EQ. MXC) I1 = I1 - 1
        ENDIF
        IF (J1 .EQ. MYC) J1 = J1 - 1
        I2  = I1 + 1
        J2  = J1 + 1
        X11 = XCGRID(I1,J1)
        X12 = XCGRID(I1,J2)
        Y11 = YCGRID(I1,J1)
        Y12 = YCGRID(I1,J2)
        IF (I2 .GT. MXC) THEN
          X21 = XCGRID(1,J1) + XCPER
          X22 = XCGRID(1,J2) + XCPER
          Y21 = YCGRID(1,J1) + YCPER
          Y22 = YCGRID(1,J2) + YCPER
        ELSE
          X21 = XCGRID(I2,J1)
          X22 = XCGRID(I2,J2)
          Y21 = YCGRID(I2,J1)
          Y22 = YCGRID(I2,J2)
        ENDIF
""".splitlines(keepends=True)
    corners = re.compile(r"([XY])CGRID\((I[12]),(J[12])\)")
    for k in range(i + 23, len(newton)):           # the bilinear map, its derivatives, test output
        newton[k] = corners.sub(lambda m: f"{m.group(1)}{m.group(2)[1]}{m.group(3)[1]}", newton[k])
    replace_lines(newton, r"^        IF \(XC \.GT\. MXC\) XC = FLOAT\(MXC\)$",
                  ["        IF (XC .GT. XCMAX) XC = XCMAX\n"], name)
    lines[lo:hi] = newton
    check_columns(lines, name)
    files[name] = lines


def change_output_obstacle_flags():
    # output_obstacle_flags: swanout1.ftn: the obstacle-crossing flags of output points, CROSS(4,MIP),
    #     were allocated but never set (the initialisation is commented out and
    #     nothing assigns them). SWIPOL drops a grid corner from the
    #     interpolation when its flag reads true, so FRAME/POINTS/TABLE values
    #     between grid points came out as exception values (-9, -99) at random,
    #     depending on leftover memory (small TABLE outputs most often). Output on
    #     grid points (BLOCK 'COMPGRID') was not affected. Set them to .FALSE.
    name = "swanout1.ftn"
    lines = load(name)                  # already changed by periodic_curvilinear
    for i in reversed(find(lines, r"^        ALLOCATE\(CROSS\(4,MIP\)\)", name, count=3)):
        lines.insert(i + 1, "        CROSS = .FALSE.\n")
    check_columns(lines, name)
    files[name] = lines


def change_periodic_coupled_stokes():
    # periodic_coupled_stokes: waves_coupler.ftn (WAV2OCN_COUPLING): with REPEATING, the coupling
    #     layout has one more column per row than SWAN's grid (ROMS's i = 0..Lm+1
    #     against SWAN's MXC), and the ordinary wave fields are re-indexed for
    #     that. The spectral Stokes fields (SPECTRUM_STOKES: KSS, USS, VSS)
    #     were still taken as in the non-periodic layout, so row j came out
    #     shifted by j-1 columns: in A15 the deep pass's spectra landed on the
    #     0.5 m deep crest, Stokes drift reached 1.4 m/s and ROMS blew up after
    #     35 min. Build the index map once (isrc) and use it for the spectra.
    name = "waves_coupler.ftn"
    lines = load(name)                  # already changed by periodic_y_strips
    lo = find(lines, r"^      SUBROUTINE WAV2OCN_COUPLING ", name)[0]
    hi = find(lines, r"^      END SUBROUTINE WAV2OCN_COUPLING", name)[0]
    insert_after(lines, r"^      integer, pointer :: points\(:\)", ["      integer, allocatable :: isrc(:)\n"], name, lo, hi)
    hi += 1
    insert_after(lines, r"^      allocate \( avdata\(gsmsize\),stat=ierr \)", ["      allocate ( isrc(gsmsize),stat=ierr )\n"], name, lo, hi)
    hi += 1
    i = find(lines, r"^            avdata\(IPI\)=REAL\( VOQ\(IP,VOQR\(IVTYPE\)\),m8 \)", name, lo, hi)[0]
    lines.insert(i + 1, "            isrc(IPI)=IP\n")
    hi += 1
    i = find(lines, r"^          avdata\(IPI\)=REAL\( VOQ\(IP,VOQR\(IVTYPE\)\),m8 \)", name, lo, hi)[0]
    lines.insert(i + 1, "          isrc(IPI)=IP\n")
    hi += 1
    i = find(lines, r"^          avdata\(IP\)=REAL\( VOQ\(points\(IP\),VOQR\(IVTYPE\)\),m8 \)", name, lo, hi)[0]
    lines.insert(i + 1, "          isrc(IP)=points(IP)\n")
    hi += 1
    for q in ("KSS", "USS", "VSS"):
        i = find(lines, rf"^            avdata\(IP\)= REAL\({q}\(points\(IP\),IZ\), m8\)", name, lo, hi)[0]
        lines[i] = lines[i].replace(f"{q}(points(IP),IZ)", f"{q}(isrc(IP),IZ)")
    i = find(lines, r"^      deallocate \(avdata, points, DIRE, DIRN\)$", name, lo, hi)[0]
    lines[i] = "      deallocate (avdata, points, DIRE, DIRN, isrc)\n"
    check_columns(lines, name)
    files[name] = lines


def change_veg3_emergent_cd():
    # veg3_emergent_cd: swancom2.ftn (SVEG_COAWST, VEGETATION 3): where the plants reach the
    #     surface (depth < plant height) the drag coefficient was a fixed 1.95,
    #     whatever the drag method of the VEGETATION 3 command (1: Cd = 1, as
    #     for submerged plants and in ROMS's CD_VEG); SVEG (VEGETATION 1) keeps
    #     the given Cd there. Depth exactly equal to the plant height had no
    #     branch at all (no dissipation, Cd undefined). Treat both like the
    #     submerged case with the canopy filling the water column: method 1
    #     Cd = 1, method 2 from the Keulegan-Carpenter number with the orbital
    #     velocity at the surface (alpha = h/d = 1).
    name = "swancom2.ftn"
    lines = load(name)                  # already changed by veg3_flexible_plants
    replace_lines(lines, r"^      ELSE IF \( DEP2\(KCGRD\(1\)\)\.LT\.SLAYH \) THEN$", [
        "      ELSE\n",
        "!        Project patch: plants up to or through the surface. Cd from\n",
        "!        the VEGETATION 3 drag method, as for submerged plants (it was\n",
        "!        a fixed 1.95; depth = height had no branch), with the canopy\n",
        "!        filling the water column (alpha = 1).\n",
        "         IF    ( VEGDRL(1).EQ.1. ) THEN\n",
        "            VEGDRL_CAL = 1.\n",
        "         ELSEIF( VEGDRL(1).EQ.2. ) THEN\n",
        "            KC_NUM     = MIN( SQRT(2.*ETOT)*SMEBRK*COSH(KD)/SINH(KD)\n",
        "     &                        *(2.*PI/SMEBRK)/VEGDIL_LOC, MAX_EPS )\n",
        "            VEGDRL_CAL = MIN(EXP(-0.0138*KC_NUM)/(KC_NUM**0.3),MAX_EPS)\n",
        "         ENDIF\n",
    ], name)
    replace_lines(lines, r"^         VEGDRL_CAL=1\.95$", [], name)
    check_columns(lines, name)
    files[name] = lines


def change_dicd_output():
    # dicd_output: swanout1.ftn (SWOEXD): the output of COAWST's vegetation drag
    #     coefficient (DICD, quantity 201, COMPDA(:,JDSXC)) tested and filled
    #     quantity 80, which SWAN 41.51 uses for REDC (QC scattering; that block
    #     comes later and overwrote it). So DICD output was always 0. Use 201.
    name = "swanout1.ftn"
    lines = load(name)                  # already changed by periodic_curvilinear and output_obstacle_flags
    lo = find(lines, r"^!     vegetation drag coefficient", name)[0]
    hi = find(lines, r"^            VOQ\(IP,VOQR\(80\)\)  = OVEXCV\(80\) ", name, lo)[0]
    n80 = 0
    for i in range(lo, hi + 1):
        new, k = re.subn(r"(?<=[(\s])80(?=[),])", "201", lines[i])
        lines[i], n80 = new, n80 + k
    if n80 != 9:
        sys.exit(f"{name}: expected 9 references to quantity 80 in the DICD block, found {n80}")
    i = find(lines, r"CALL SWIPOL\(COMPDA\(1,JDSXC\),OVEXCV\(201\), XC,", name, lo, hi)[0]
    lines[i] = lines[i].replace("OVEXCV(201), XC,", "OVEXCV(201),XC,")      # stay within column 72
    check_columns(lines, name)
    files[name] = lines


def change_closed_ring():
    # closed_ring: Closed periodic curvilinear grids (O-grids around an island; new
    #     feature). The grid's last column
    #     (column MXC+1 in READGRID COORDINATES) is column 1 itself, so the
    #     period vector is zero.
    #     - CVPERI: a period below the coordinate tolerance means a closed
    #       grid: XCPER = YCPER = 0 exactly and KRING = 1. ERRCHK no longer
    #       calls that "no period found"; CVMESH skips the whole-period guess
    #       (it divided by the period length).
    #     - Coupler: with REPEATING the layout had MXC+1 columns per row
    #       (ROMS i = 0..Lm+1 against SWAN's MXC = Lm+1 columns: SWAN's period
    #       one column longer than ROMS's). On a closed grid that extra column
    #       sits on top of ROMS column 0 (zero-width mesh), so with KRING = 1
    #       SWAN has exactly ROMS's period (MXC = Lm, SWAN column k = ROMS i = k)
    #       and the layout MXC+2 columns: ROMS i = 0 gets SWAN column MXC,
    #       i = Lm+1 SWAN column 1, and SWAN skips both when receiving (i = 0
    #       at the start of each row, i = Lm+1 by the existing skip at its end).
    name = "swmod1.ftn"
    lines = load(name)                  # already changed by periodic_curvilinear
    insert_after(lines, r"^! YCPER  \[    0\.\] y component of that period vector$", [
        "! KRING  [    0 ] 1: repeating curvilinear grid that closes on itself (O-grid),\n",
        "!                 i.e. period vector 0; the coupler then maps ROMS i = 1..Lm to\n",
        "!                 SWAN columns 1..MXC\n"], name)
    insert_after(lines, r"^      REAL    XCPER,     YCPER$", ["      INTEGER KRING\n"], name)
    files[name] = lines

    name = "swanmain.ftn"
    lines = load(name)                  # already changed by plant_input_grids, periodic_y_strips and periodic_curvilinear
    insert_after(lines, r"^      YCPER  = 0\.$", ["      KRING  = 0\n"], name)
    replace_lines(lines, r"^        IF \(OPTG\.EQ\.3 \.AND\. XCPER\.EQ\.0\. \.AND\. YCPER\.EQ\.0\.\)$", [
        "        IF (OPTG.EQ.3 .AND. XCPER.EQ.0. .AND. YCPER.EQ.0. .AND.\n",
        "     &      KRING.EQ.0)\n"], name)
    check_columns(lines, name)
    files[name] = lines

    name = "swanpre1.ftn"
    lines = load(name)                  # already changed by veg3_young_modulus, plant_input_grids, periodic_compgrid_frame and periodic_curvilinear
    i = find(lines, r"^     &      ' REPeating curvilinear grid, period vector \(x,y\):',$", name)[0]
    if lines[i + 1] != "     &      XCPER, YCPER\n":
        sys.exit(f"{name}: CVPERI period message not found")
    lines[i + 2:i + 2] = """\
!        closed grid (O-grid around an island): column MXC+1 is column 1
!        itself and the period vector is zero
         IF (SQRT(XCPER**2+YCPER**2) .LE. TOL) THEN
            XCPER = 0.
            YCPER = 0.
            KRING = 1
            WRITE (PRINTF, '(A)') ' REPeating curvilinear grid is '//
     &         'closed (period vector 0)'
         ENDIF
""".splitlines(keepends=True)
    check_columns(lines, name)
    files[name] = lines

    #     - VALIDBP (CGBOUN's test for isolated wet points and 1-D connections,
    #       which SWAN removes from the grid) did not wrap around the seam: on
    #       an island O-grid a wet point in column 1 whose only wet
    #       neighbours are above it and across the seam was removed (dry in
    #       SWAN, wet in ROMS). It now wraps for any REPEATING grid (A15 has
    #       no such point: unchanged).
    lo = find(lines, r"^      LOGICAL FUNCTION VALIDBP \(IX, IY, KGRPNT,WNP\)$", name)[0]
    hi = find(lines, r"^      SUBROUTINE SEPARAREA\(IX, IY, KGRPNT,IDIR\)$", name)[0]
    insert_after(lines, r"^      USE OCPCOMM4 ", ["      USE SWCOMM4\n"], name, lo, hi)
    hi += 1
    insert_after(lines, r"^      INTEGER IENT$", ["      INTEGER IXV, IXVM, IXVP\n"], name, lo, hi)
    hi += 1
    insert_after(lines, r"^      VALIDBP = \.TRUE\.$", """\
!     REPeating grid: the point (CGBOUN also asks for IX = 0) and its
!     x-neighbours wrap around the seam
      IXV = IX
      IF (KREPTX.GT.0) THEN
        IF (IXV.LT.1)   IXV = IXV + MXC
        IF (IXV.GT.MXC) IXV = IXV - MXC
      ENDIF
      IXVM = IXV - 1
      IXVP = IXV + 1
      IF (KREPTX.GT.0) THEN
        IF (IXVM.LT.1)   IXVM = MXC
        IF (IXVP.GT.MXC) IXVP = 1
      ENDIF
""".splitlines(keepends=True), name, lo, hi)
    hi += 13
    n = 0
    for k in range(lo, hi):
        if "PVALID(IX" in lines[k] and not lines[k].startswith("!"):
            new = lines[k].replace("PVALID(IX-1,", "PVALID(IXVM,").replace("PVALID(IX+1,", "PVALID(IXVP,") \
                          .replace("PVALID(IX,", "PVALID(IXV,")
            n += new != lines[k]
            lines[k] = new
    if n != 26:
        sys.exit(f"{name}: expected 26 PVALID lines in VALIDBP, changed {n}")
    check_columns(lines, name)
    files[name] = lines

    name = "swanser.ftn"
    lines = load(name)                  # already changed by periodic_curvilinear
    replace_lines(lines, r"^         IF \(KGRPNT\(1,IY\)\.GT\.1\) THEN$", [
        "         IF (KGRPNT(1,IY).GT.1 .AND. KRING.EQ.0) THEN\n"], name)
    check_columns(lines, name)
    files[name] = lines

    name = "waves_coupler.ftn"
    lines = load(name)                  # already changed by periodic_y_strips and periodic_coupled_stokes
    lo = find(lines, r"^      SUBROUTINE INITIALIZE_WAV_COUPLING$", name)[0]
    hi = find(lines, r"^      SUBROUTINE INITIALIZE_WAV_ROUTERS$", name)[0]
    for regex, old, new in [
            (r"^          Isize=MXCGL\+1$", "MXCGL+1", "MXCGL+1+KRING"),
            (r"^            Isize=MXC-IHALOX\*IBLKAD\(1\)\+1$", "+1\n", "+1+KRING\n"),
            (r"^            Isize=MXC\+1$", "MXC+1", "MXC+1+KRING"),
            (r"^        MXCGLc=MXCGL\+1$", "MXCGL+1", "MXCGL+1+KRING")]:
        i = find(lines, regex, name, lo, hi)[0]
        lines[i] = lines[i].replace(old, new)
    i = find(lines, r"^!  Add offset of 1 for repeating x-dir grids\.$", name, lo, hi)[0]
    lines[i:i + 1] = ["!  Add offset of 1 for repeating x-dir grids, 2 for closed ones\n",
                      "!  (KRING: ROMS i = 0 and Lm+1 are both outside SWAN's grid).\n"]
    lo = find(lines, r"^      SUBROUTINE WAV2OCN_COUPLING ", name)[0]
    hi = find(lines, r"^      END SUBROUTINE WAV2OCN_COUPLING", name)[0]
    for regex, old, new in [
            (r"^          Isize=MXCGL\+1$", "MXCGL+1", "MXCGL+1+KRING"),
            (r"^            Isize=MXC-IHALOX\*IBLKAD\(1\)\+1$", "+1\n", "+1+KRING\n"),
            (r"^            Isize=MXC\+1$", "MXC+1", "MXC+1+KRING")]:
        i = find(lines, regex, name, lo, hi)[0]
        lines[i] = lines[i].replace(old, new)
    i = find(lines, r"^        DO j=1,Jsize$", name, lo, hi, count=2)[0]
    if not (lines[i + 1] == "          DO i=1,Isize-1\n" and lines[i - 1] == "        IPI=0\n"):
        sys.exit(f"{name}: WAV2OCN periodic packing loop not found")
    lines[i + 1:i + 2] = """\
!         closed grid: the first slot (ROMS i = 0) is SWAN column MXC
          IF (KRING.EQ.1) THEN
            IPI=IPI+1
            avdata(IPI)=REAL( VOQ(IP+MXC,VOQR(IVTYPE)),m8 )
            isrc(IPI)=IP+MXC
          END IF
          DO i=1,Isize-1-KRING
""".splitlines(keepends=True)
    i = find(lines, r"^! now fill the far right$", name, lo, hi)[0]
    if not (lines[i + 5] == "          IP=IP+Isize-1\n" and lines[i + 7].startswith("          avdata(IPI)=")
            and lines[i + 8] == "          isrc(IPI)=IP\n"):
        sys.exit(f"{name}: WAV2OCN far-right loop not found")
    lines[i + 5] = "          IP=IP+Isize-1-KRING\n"
    lines[i + 7:i + 9] = """\
!         closed grid: the last slot (ROMS i = Lm+1) is SWAN column 1
          IF (KRING.EQ.1) THEN
            avdata(IPI)=REAL( VOQ(IP-MXC+1,VOQR(IVTYPE)),m8 )
            isrc(IPI)=IP-MXC+1
          ELSE
            avdata(IPI)=REAL( VOQ(IP,VOQR(IVTYPE)),m8 )
            isrc(IPI)=IP
          END IF
""".splitlines(keepends=True)
    lo = find(lines, r"^      SUBROUTINE WAVFOCN_COUPLING ", name)[0]
    hi = find(lines, r"^      SUBROUTINE WAVFATM_COUPLING ", name)[0]
    rows = find(lines, r"^ *DO IY=Jstr,Jend$", name, lo, hi, count=11)
    for i in reversed(rows):
        ind = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
        if not (lines[i + 1] == ind + "  DO IX=Istr,Iend\n" and lines[i + 2] == ind + "    IP=IP+1\n"):
            sys.exit(f"{name}: WAVFOCN row loop at line {i + 1} not as expected")
        end = next(k for k in range(i + 3, i + 20) if lines[k] == ind + "  END DO\n")
        if lines[end + 1:end + 4] != [ind + "  IF (KREPTX.EQ.1) THEN\n", ind + "    IP=IP+1\n", ind + "  END IF\n"]:
            sys.exit(f"{name}: WAVFOCN row skip after line {end + 1} not as expected")
        lines[i + 1:i + 1] = [ind + "  IF (KREPTX.EQ.1) IP=IP+KRING\n"]
    check_columns(lines, name)
    files[name] = lines


def change_exact_restart():
    # exact_restart: Exact restarts (needed to resume runs on Spot VMs). COAWST's
    #     RESTART 'fname' FREE|UNFormatted <interval> command writes SWAN's
    #     state every interval, but RESTART_SWAN always wrote the formatted
    #     text layout, where WRSPEC keeps about 5 significant digits of each
    #     spectrum, and it saved only the action densities. After INIT HOTSTART
    #     SWAN's first step (IT = 0) zeroes the dissipation and recomputes the
    #     bottom orbital fields, so the first exchange sent ROMS other fields
    #     than the uninterrupted run (restarted A15 currents 2 cm/s off after
    #     30 min).
    #     - RESTART ... UNFormatted now writes the binary HOTFILE layout (read
    #       by INIT HOTSTART MULTiple 'fname' UNFormatted), followed by one
    #       extra record set: MCGRD, MCMVAR, MDC, MSC, then COMPDA and AC2
    #       (every computed field: depths and currents at both time levels,
    #       dissipation, bottom orbital velocity, plants, ...).
    #     - The periodic restart is written before the coupling exchange of
    #       that step (waves_control.ftn), i.e. the state the exchange uses.
    #     - After that exchange SWAN_RST_POST appends COMPDA again: the
    #       exchange writes ROMS's fields (water level, currents, roughness,
    #       plants) into COMPDA, and at the restart ROMS cannot send the same
    #       values (it computed them before that exchange).
    #     - INIT HOTSTART ... UNFormatted reads the extra records when present
    #       (one grid only). SWAN_RUN puts COMPDA and AC2 back at IT = 0, after
    #       SNEXTI and the IT = 0 initialisation and before the output; after
    #       the first exchange SWAN_RST_POST puts back the COMPDA of after the
    #       exchange. Files without them read as before.
    name = "swan_iounits.ftn"
    lines = load(name)
    insert_after(lines, r"^      integer, dimension\(:\), pointer :: SwanRstFnum$", [
        "!  swan-exact-restart: SwanRstUnf, RESTART files binary (exact);\n",
        "!  HotFull, HotCompda, HotAc2: the full state read by INIT HOTSTART\n",
        "!  ... UNFormatted, restored in SWAN_RUN at IT = 0 (one grid only)\n",
        "      logical, dimension(:), pointer :: SwanRstUnf\n",
        "      logical :: HotFull = .FALSE., HotPost = .FALSE.\n",
        "      real, allocatable :: HotCompda(:,:), HotAc2(:,:,:)\n",
        "      real, allocatable :: HotCompdaPost(:,:)\n"], name)
    insert_after(lines, r"^      allocate \(SwanRstFnum\(NUM_SGRIDS\)\)$", [
        "      allocate (SwanRstUnf(NUM_SGRIDS))\n",
        "      SwanRstUnf=.FALSE.\n"], name)
    check_columns(lines, name)
    files[name] = lines

    name = "swanpre1.ftn"
    lines = load(name)
    # BACKUP (HOTFILE and RESTART commands): remember the format
    lo = find(lines, r"^      SUBROUTINE BACKUP \(AC2, SPCSIG, SPCDIR, KGRPNT,", name)[0]
    hi = find(lines, r"^!     end of subr BACKUP$", name)[0]
    insert_after(lines, r"^       CALL FOR \(NREF, FILENM, 'UU', IOSTAT\)", [
        "#ifdef SWAN_MODEL\n",
        "       SwanRstUnf(ng)=.TRUE.\n",
        "#endif\n"], name, lo, hi)
    insert_after(lines, r"^       CALL FOR \(NREF, FILENM, 'UF', IOSTAT\)", [
        "#ifdef SWAN_MODEL\n",
        "       SwanRstUnf(ng)=.FALSE.\n",
        "#endif\n"], name, lo, hi + 6)
    # RESTART_SWAN: binary branch with the full state
    lo = find(lines, r"^      SUBROUTINE RESTART_SWAN \(AC2, SPCSIG, SPCDIR, KGRPNT,", name)[0]
    hi = find(lines, r"^!     end of subr RESTART$", name)[0]
    insert_after(lines, r"^      USE M_COUPLING$", ["      USE M_PARALL2, ONLY: COMPDA\n"], name, lo, hi)
    hi += 1
    i = find(lines, r"^      CALL FOR \(NREF,  SwanRstName\(ng\), 'UF', IOSTAT\)", name, lo, hi)[0]
    lines[i:i] = """\
!     UNFormatted (swan-exact-restart): the binary HOTFILE layout, exact,
!     then MCGRD, MCMVAR, MDC, MSC, COMPDA and AC2 for an exact restart
      IF (SwanRstUnf(ng)) THEN
       CALL FOR (NREF, SwanRstName(ng), 'UU', IOSTAT)
       IF (STPNOW()) RETURN
       WRITE (NREF) VERTXT
       WRITE (NREF) PROJID, PROJNR
       WRITE (NREF) NSTATM
       IF (NSTATM.EQ.1) WRITE (NREF) ITMOPT
       WRITE (NREF) OPTG
       IF (OPTG.NE.5) THEN
         WRITE (NREF) MXC*MYC, MXC, MYC
         DO IX = 1, MXC
            DO IY = 1, MYC
               IF ( EQREAL(XCGRID(IX,IY), EXCFLD(8)) .AND.
     &              EQREAL(YCGRID(IX,IY), EXCFLD(9)) ) THEN
                  WRITE (NREF) EXCFLD(8)+XOFFS, EXCFLD(9)+YOFFS
               ELSE
                  WRITE (NREF) XCGRID(IX,IY)+XOFFS, YCGRID(IX,IY)+YOFFS
               ENDIF
            ENDDO
         ENDDO
       ELSE
         WRITE (NREF) nverts
         DO K = 1, nverts
            WRITE (NREF) xcugrd(K)+XOFFS, ycugrd(K)+YOFFS
         ENDDO
       ENDIF
       WRITE (NREF) MSC
       DO IS = 1, MSC
         WRITE (NREF) SPCSIG(IS)/PI2
       ENDDO
       WRITE (NREF) MDC
       DO ID = 1, MDC
         WRITE (NREF) SPCDIR(ID,1)*180./PI
       ENDDO
       IF (NSTATM.EQ.1) WRITE (NREF) CHTIME_M
       IF (OPTG.NE.5) THEN
         DO IX = 1, MXC
            DO IY = 1, MYC
               INDX = KGRPNT(IX,IY)
               WRITE (NREF) INDX
               IF (INDX.NE.1) WRITE (NREF) AC2(:,:,INDX)
            ENDDO
         ENDDO
       ELSE
         DO K = 1, nverts
            WRITE(NREF) AC2(:,:,K)
         ENDDO
       ENDIF
       WRITE (NREF) MCGRD, MCMVAR, MDC, MSC
       WRITE (NREF) COMPDA(1:MCGRD,1:MCMVAR)
       WRITE (NREF) AC2(:,:,1:MCGRD)
       CLOSE (NREF)
       RETURN
      ENDIF
""".splitlines(keepends=True)
    # INITVA: read the extra records of a full-state restart file
    lo = find(lines, r"^      SUBROUTINE INITVA\( AC2, SPCSIG, SPCDIR, KGRPNT \)", name)[0]
    hi = find(lines, r"^!     end of subr INITVA$", name)[0]
    insert_after(lines, r"^      USE SwanGriddata ", [
        "#ifdef SWAN_MODEL\n",
        "      USE swan_iounits\n",
        "      USE M_COUPLING\n",
        "#endif\n"], name, lo, lo + 20)
    hi += 4
    i = find(lines, r"^         CALL IGNORE \('FREE'\) ", name, lo, hi)[0] - 1
    if not lines[i].startswith("        ELSE ") or lines[i - 1] != "         ENDIF\n":
        sys.exit(f"{name}: end of the binary branch of INITVA not found")
    lines[i:i] = """\
#ifdef SWAN_MODEL
!        full SWAN state of RESTART ... UNFormatted (swan-exact-restart),
!        put back in SWAN_RUN at IT = 0
         READ (NREF, IOSTAT=IOS) N1, N2, N3, N4
         IF (IOS.EQ.0 .AND. N1.EQ.MCGRD .AND. N3.EQ.MDC .AND.
     &       N4.EQ.MSC .AND. NUM_SGRIDS.EQ.1) THEN
           IF (ALLOCATED(HotCompda)) DEALLOCATE(HotCompda, HotAc2)
           ALLOCATE (HotCompda(N1,N2), HotAc2(N3,N4,N1))
           READ (NREF) HotCompda
           READ (NREF) HotAc2
           HotFull = .TRUE.
           IF (ALLOCATED(HotCompdaPost)) DEALLOCATE(HotCompdaPost)
           ALLOCATE (HotCompdaPost(N1,N2))
           READ (NREF, IOSTAT=IOS) HotCompdaPost
           HotPost = IOS.EQ.0
           IF (.NOT.HotPost) DEALLOCATE(HotCompdaPost)
           WRITE (PRINTF, *) 'full SWAN state read (exact restart)',
     &                       HotPost
         ENDIF
#endif
""".splitlines(keepends=True)
    check_columns(lines, name)
    files[name] = lines

    name = "swanmain.ftn"
    lines = load(name)
    lo = find(lines, r"^      SUBROUTINE SWAN_RUN \(IT_in, ngp, first\)", name)[0]
    i = find(lines, r"^            do_output=1$", name, lo)[0]
    lines[i:i] = """\
!     swan-exact-restart: the full state of an exact restart, after the
!     IT = 0 initialisation and before the output and the first exchange
            IF (HotFull .AND. IT.EQ.0) THEN
              IF (SIZE(HotCompda,2).EQ.MCMVAR) THEN
                COMPDA(1:MCGRD,1:MCMVAR) = HotCompda
                AC2(:,:,1:MCGRD) = HotAc2
              ELSE
                WRITE (PRINTF, *) 'full SWAN state not used: MCMVAR'
              ENDIF
              DEALLOCATE (HotCompda, HotAc2)
              HotFull = .FALSE.
            ENDIF
""".splitlines(keepends=True)
    check_columns(lines, name)
    files[name] = lines

    name = "swanmain.ftn"
    lines = load(name)
    i = find(lines, r"^      END SUBROUTINE SWAN_RST$", name)[0]
    lines[i + 1:i + 1] = """\

!***********************************************************************
!                                                                      *
      SUBROUTINE SWAN_RST_POST (IT_in)
!                                                                      *
!***********************************************************************
!
!     swan-exact-restart: after a coupling exchange at which a binary
!     restart file was written, append COMPDA (the exchange put ROMS's
!     fields into it). After the first exchange of a run started from
!     such a file, first put back the COMPDA of the uninterrupted run.
!
      USE TIMECOMM
      USE SWCOMM3
      USE M_PARALL
      USE M_PARALL2, ONLY: COMPDA
      USE M_COUPLING
      USE SWPOINT_MOD, ONLY: INIT_POINTERS
      USE swan_iounits
!
      IMPLICIT NONE
!
      INTEGER,  intent(in) :: IT_in
      INTEGER   nsrst, NREF
!
      Gridnum=ng
      CALL INIT_POINTERS(ng)
      IF (HotPost .AND. IT_in.EQ.0) THEN
        COMPDA(1:MCGRD,1:MCMVAR) = HotCompdaPost
        DEALLOCATE (HotCompdaPost)
        HotPost = .FALSE.
      ENDIF
      nsrst=INT(dtswanrst(ng)/DT)
      IF (nsrst.gt.0 .AND. SwanRstUnf(ng)) THEN
        IF (MOD(IT_in, nsrst).eq.0) THEN
          NREF=SwanRstFnum(ng)
          OPEN (NREF, FILE=TRIM(SwanRstName(ng)), FORM='UNFORMATTED',
     &          STATUS='OLD', POSITION='APPEND')
          WRITE (NREF) COMPDA(1:MCGRD,1:MCMVAR)
          CLOSE (NREF)
        END IF
      END IF

      RETURN
      END SUBROUTINE SWAN_RST_POST
""".splitlines(keepends=True)
    check_columns(lines, name)
    files[name] = lines

    name = "waves_control.ftn"
    lines = load(name)
    i = find(lines, r"^        CALL SWAN_CPL \(0\)$", name)[0]
    lines[i + 1:i + 1] = [
        "!     swan-exact-restart: COMPDA after the exchange (exact restarts)\n",
        "        DO ng=1,NUM_SGRIDS\n",
        "          CALL SWAN_RST_POST (0)\n",
        "        END DO\n"]
    i = find(lines, r"^          CALL SWAN_CPL \(1\)$", name)[0]
    j = find(lines, r"^            CALL SWAN_RST \(iics\(ng\)\)$", name)[0]
    blk_cpl = lines[i - 5:i + 3]          # #ifdef .. #endif around SWAN_CPL (1)
    blk_rst = lines[j - 2:j + 3]          # DO ng .. END DO around SWAN_RST
    if not (blk_cpl[0] == "#ifdef COAWST_COUPLING\n" and blk_cpl[-1] == "#endif\n"
            and blk_rst[0] == "        DO ng=1,NUM_SGRIDS\n" and blk_rst[-1] == "        END DO\n"
            and j - 2 == i + 3):
        sys.exit(f"{name}: coupling and restart blocks not as expected")
    blk_cpl[-2:-2] = ["          DO ng=1,NUM_SGRIDS\n",
                      "            CALL SWAN_RST_POST (iics(ng))\n",
                      "          END DO\n"]
    lines[i - 5:j + 3] = (["!     restart files hold the state the coupling exchange uses, then\n",
                           "!     COMPDA after it (swan-exact-restart)\n"] + blk_rst + blk_cpl)
    check_columns(lines, name)
    files[name] = lines


def change_halo_exchange_nonblocking():
    # halo_exchange_nonblocking: swanparll.ftn (SWEXCHG, wavefront version): the halo exchange between
    #     SWAN processes sent to every neighbour with a blocking MPI_SEND before
    #     receiving anything. MPI buffers a message only up to its eager limit
    #     (4 KB in shared memory = 1024 REALs); above that MPI_SEND waits for the
    #     matching receive, every process waits in its send, and SWAN hangs at
    #     100 % CPU after the first sweeps (found on an island O-grid with a
    #     2704-point halo row; 944 points just fit). Post all receives, then all
    #     sends, without blocking, and wait for every one (any message size).
    #     SWSENDAC/SWRECVAC (the sweep pipeline) are one-way and cannot deadlock.
    name = "swanparll.ftn"
    lines = load(name)
    start = next(i for i, l in enumerate(lines) if l.startswith("!WFR      SUBROUTINE SWEXCHG ( FIELD, KGRPNT )"))
    end = next(i for i in range(start, len(lines)) if lines[i].rstrip() == "!WFR      END")
    sub = lines[start:end + 1]






    sub = replace_block(sub, "!WFR      USE M_PARALL", "!WFR      USE M_PARALL", wfr("""
      USE M_PARALL
#ifdef SWAN_MODEL
      USE M_MPI
      USE mct_coupler_params
#else
      USE MPI
#endif
"""))
    sub = replace_block(sub, "!WFR      INTEGER IDOM, IENT, INB", "!WFR      REAL    WORK(MAX(MXC,MYC))", wfr("""
      INTEGER IDOM, IENT, IERR, INB, ISTART, ITAG, K, NNEIGH, NOVLU
      INTEGER, ALLOCATABLE :: IREQ(:)
      REAL, ALLOCATABLE :: WRCV(:,:), WSND(:,:)
"""))
    sub = replace_block(sub, "!WFR      NNEIGH = IBLKAD(1)", "!WFR!TIMG      CALL SWTSTO(203)", wfr("""
      NNEIGH = IBLKAD(1)

!     --- post every receive, then every send, and wait for all:
!         blocking sends to all neighbours first deadlock once a
!         message exceeds MPI's eager limit (swan-halo-hang.patch)

      ALLOCATE (WRCV(MAX(MXC,MYC),NNEIGH), WSND(MAX(MXC,MYC),NNEIGH))
      ALLOCATE (IREQ(2*NNEIGH))
      ITAG = 2
      DO INB = 1, NNEIGH
         IDOM   = IBLKAD(3*INB-1)
         ISTART = IBLKAD(3*INB+1)
         NOVLU  = IBLKAD(ISTART)
         CALL MPI_IRECV ( WRCV(1,INB), NOVLU, SWREAL, IDOM-1, ITAG,
#ifdef SWAN_MODEL
     &                    WAV_COMM_WORLD, IREQ(INB), IERR )
#else
     &                    MPI_COMM_WORLD, IREQ(INB), IERR )
#endif
      END DO
      DO INB = 1, NNEIGH
         IDOM   = IBLKAD(3*INB-1)
         ISTART = IBLKAD(3*INB+1)
         NOVLU  = IBLKAD(ISTART)
         DO K = 1, NOVLU
            WSND(K,INB) = FIELD(KGRPNT(IBLKAD(ISTART+K)))
         END DO
         CALL MPI_ISEND ( WSND(1,INB), NOVLU, SWREAL, IDOM-1, ITAG,
#ifdef SWAN_MODEL
     &                    WAV_COMM_WORLD, IREQ(NNEIGH+INB), IERR )
#else
     &                    MPI_COMM_WORLD, IREQ(NNEIGH+INB), IERR )
#endif
      END DO
      CALL MPI_WAITALL ( 2*NNEIGH, IREQ, MPI_STATUSES_IGNORE, IERR )
      IF ( IERR.NE.MPI_SUCCESS ) THEN
         CALL MSGERR ( 4, 'MPI error in halo exchange SWEXCHG' )
         RETURN
      END IF

!     --- store the received data

      DO INB = 1, NNEIGH
         ISTART = IBLKAD(3*INB+1)
         NOVLU  = IBLKAD(ISTART)
         DO K = 1, NOVLU
            FIELD(KGRPNT(IBLKAD(ISTART+NOVLU+K))) = WRCV(K,INB)
         END DO
      END DO
      DEALLOCATE (WRCV, WSND, IREQ)

!TIMG      CALL SWTSTO(203)
"""))
    lines[start:end + 1] = sub
    files[name] = lines


def change_netcdf4_compression():
    # netcdf4_compression: agioncmd.ftn90: compressed NetCDF-4 output, as ROMS writes with
    #     OUT_NETCDF4 + DEFLATE (the Dockerfile default). SWAN
    #     created its .nc files as classic 64-bit offset files. With both options
    #     in the case header (agioncmd now includes swancpp.h, i.e. cppdefs.h and
    #     the case header, like SWAN's .ftn files), create NetCDF-4/HDF5 files and
    #     give every multi-dimensional variable (BLOCK and TABLE quantities,
    #     curvilinear x/y, spectra) shuffle + deflate level 1, lossless, as ROMS's
    #     def_var.F does. Without the options the files stay classic.
    name = "agioncmd.ftn90"
    lines = load(name)                  # already changed by netcdf_float
    mod = [i for i, l in enumerate(lines) if l.rstrip() == "      module agioncmd"]
    if len(mod) != 1:
        sys.exit(f"netcdf4_compression: {name}: module line not found")
    lines[mod[0]:mod[0]] = ['#include "swancpp.h"\n']
    create = "            call nccheck ( nf90_create( ncfile, NF90_NOCLOBBER + NF90_64BIT_OFFSET, ncid) )\n"
    i = lines.index(create)
    lines[i:i + 1] = [
        "#if defined OUT_NETCDF4\n",
        "            ! compressed NetCDF-4/HDF5 file, as ROMS (swan-netcdf4-compression)\n",
        "            call nccheck ( nf90_create( ncfile, IOR(NF90_NOCLOBBER, NF90_NETCDF4), ncid) )\n",
        "#else\n",
        create,
        "#endif\n",
    ]
    i = lines.index("        end subroutine create_ncfile\n")
    lines[i + 1:i + 1] = ["\n"] + ("""\
        subroutine agnc_compress( ncid, varid )
            ! shuffle + deflate level 1 (lossless) in NetCDF-4 files, as
            ! ROMS's def_var.F (swan-netcdf4-compression; no cpp names in comments)
            integer,              intent(in)                    :: ncid, varid
#if defined OUT_NETCDF4 && defined DEFLATE
            call nccheck ( nf90_def_var_deflate( ncid, varid, 1, 1, 1 ) )
#endif
        end subroutine agnc_compress
""").splitlines(keepends=True)
    # After every nf90_def_var statement with an array of dimensions (/ ... /),
    # compress the variable just defined (its varid is the last argument).
    n_comp, i = 0, 0
    while i < len(lines):
        if "call nccheck ( nf90_def_var(" not in lines[i]:
            i += 1
            continue
        j = i
        while lines[j].rstrip().endswith("&"):
            j += 1
        stmt = "".join(lines[i:j + 1])
        if "(/" in stmt:
            m = re.search(r",[\s&]*([\w%]+)\s*\)\s*\)\s*;?\s*$", stmt)
            if m is None:
                sys.exit(f"netcdf4_compression: varid not found in {stmt!r}")
            varid = m.group(1)
            indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
            lines.insert(j + 1, f"{indent}call agnc_compress( ncid, {varid} )\n")
            n_comp += 1
        i = j + 1
    if n_comp != 16:
        sys.exit(f"netcdf4_compression: expected 16 multi-dimensional nf90_def_var calls, found {n_comp}")
    files[name] = lines


# ---------------------------------------------------------------------------
# Driver: run the changes in the order of GROUPS and write one patch per group.
load_original = load


def load(name):
    """A file as changed by the changes run so far (the original if untouched)."""
    return list(files[name]) if name in files else load_original(name)


GROUPS = [
    ("1-fixes/swan-nc-crash.patch", ["nc_filename_length", "stnames_size"]),
    ("1-fixes/swan-stop-on-input-errors.patch", ["stop_on_input_errors"]),
    ("1-fixes/swan-output-fixes.patch", ["table_nc_coordinates", "compgrid_nc_coordinates", "output_obstacle_flags"]),
    ("1-fixes/swan-force-strip-rows.patch", ["block_point_owner"]),
    ("1-fixes/swan-vegetation-fixes.patch", ["veg3_young_modulus", "veg3_flexible_plants", "plant_input_grids", "veg3_emergent_cd", "dicd_output"]),
    ("1-fixes/swan-periodic-fixes.patch", ["periodic_compgrid_frame", "periodic_y_strips", "periodic_coupled_stokes"]),
    ("1-fixes/swan-halo-hang.patch", ["halo_exchange_nonblocking"]),
    ("1-fixes/swan-exact-restart.patch", ["exact_restart"]),
    ("2-improvements/swan-netcdf-output.patch", ["netcdf_names", "netcdf_records", "netcdf_float"]),
    ("2-improvements/swan-netcdf4-compression.patch", ["netcdf4_compression"]),
    ("2-improvements/swan-periodic-curvilinear.patch", ["periodic_curvilinear"]),
    ("2-improvements/swan-closed-ring.patch", ["closed_ring"]),
]

if __name__ == "__main__":
    outdir = out
    for patch, items in GROUPS:
        before = {k: list(v) for k, v in files.items()}
        unknown = WITHOUT - {c for _, cs in GROUPS for c in cs}
        if unknown:
            sys.exit(f"--without: no such change {sorted(unknown)}")
        items = [it for it in items if it not in WITHOUT]
        for it in items:
            globals()["change_" + it]()
        path = outdir / patch
        path.parent.mkdir(parents=True, exist_ok=True)
        n = 0
        with path.open("w") as f:
            for name in sorted(files):
                old = before.get(name) or load_original(name)
                if files[name] != old:
                    f.writelines(difflib.unified_diff(old, files[name], f"a/SWAN/src/{name}",
                                                      f"b/SWAN/src/{name}"))
                    n += 1
        print(f"{patch}: {', '.join(items)}, {n} files")
