"""Register census rules for the private hv002 hypervisor (private iLinux tooling).

Shared by census.py (standalone H1 session) and hv_launch.py (in-boot preflight
before the chainload). Every read goes through ProxyUtils.mrs under m1n1's
exception guard; a trap is reported, never raised. Classes only, no raw values.
"""

# (name, encoding, classifier); classifiers reveal only what the gates need.
# hv_start() (C) reads AMX/APVMKEY/APSTS, ACTLR_EL2, ACTLR_EL12 (architectural:
# t6050 has actlr_el2), CNTHCTL and SPRR/GXF config without an exception guard.
# Every HV exception reads/writes PMCR0; the HV FIQ path reads IPI_SR.
REGS = (
    ("ID_AA64MMFR0_EL1", (3, 0, 0, 7, 0), lambda v: "ECV=%d" % (v >> 60)),
    ("VM_TMR_FIQ_ENA_EL2", (3, 5, 15, 1, 3), lambda v: "ENA_V=%d ENA_P=%d" % (v & 1, v >> 1 & 1)),
    ("HACR_EL2", (3, 4, 1, 1, 7), None),
    ("AMX_CTL_EL2", (3, 4, 15, 4, 7), None),
    ("APVMKEYLO_EL2", (3, 6, 15, 14, 4), None),
    ("APVMKEYHI_EL2", (3, 6, 15, 14, 5), None),
    ("APSTS_EL12", (3, 6, 15, 14, 7), None),
    ("ACTLR_EL2", (3, 4, 1, 0, 1), None),
    ("ACTLR_EL12", (3, 5, 1, 0, 1), None),
    ("IMP_APL_ACTLR_EL12", (3, 6, 15, 14, 6), None),
    ("SPRR_CONFIG_EL1", (3, 6, 15, 1, 0), None),
    ("GXF_CONFIG_EL1", (3, 6, 15, 1, 2), None),
    ("CNTHCTL_EL2", (3, 4, 14, 1, 0), None),
    ("CNTV_CTL_EL02", (3, 5, 14, 3, 1), lambda v: "ctl=%d" % (v & 7)),
    ("CNTP_CTL_EL02", (3, 5, 14, 2, 1), lambda v: "ctl=%d" % (v & 7)),
    ("PMCR0", (3, 1, 15, 0, 0), None),
    ("IPI_SR_EL1", (3, 5, 15, 1, 1), None),
    ("UPMCR0", (3, 7, 15, 0, 4), None),
    ("UPMSR", (3, 7, 15, 6, 4), None),
)

# Read for the record only. On t6050 (features_m4: actlr_el2 = true, no
# uncore_version) neither m1n1 nor the Python HV touches these.
INFORMATIONAL = {"IMP_APL_ACTLR_EL12", "UPMCR0", "UPMSR"}


def classify(value, fn):
    if fn:
        return fn(value)
    return "zero" if value == 0 else "nonzero"


def census(utils, errors):
    rows = []
    for name, enc, fn in REGS:
        try:
            rows.append((name, "readable", classify(utils.mrs(enc), fn)))
        except errors as exc:
            rows.append((name, "trapped", type(exc).__name__))
    return rows


def verdict(rows):
    """Blockers for hv002. Guest-timer FIQ enables may be set (hv002 masks
    the timers at their source), but that needs the ECV timer traps."""
    get = {n: (s, c) for n, s, c in rows}
    blockers = [n for n, s, _ in rows if s != "readable" and n not in INFORMATIONAL]
    if get.get("ID_AA64MMFR0_EL1") == ("readable", "ECV=0"):
        blockers.append("no ECV: hv002 cannot trap and shadow guest timers")
    return blockers
