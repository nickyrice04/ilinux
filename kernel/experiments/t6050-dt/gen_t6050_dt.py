#!/usr/bin/env python3
"""Generate a DRAFT Linux device tree for Apple t6050 (M5 Max, Mac17,6 / J716c)
from the sanitized macOS ADT capture (hardware/adt/adt-sanitized.json).

Outputs (in OUTDIR):
  t6050.dtsi        CPUs (MPIDR-corrected), OPP tables + cpufreq controllers,
                    AIC3, timer, WDT, pinctrl, I2C, UART, PMGR containers,
                    draft DARTs, SART (SARTv4), ANS mailbox, NVMe (M4+ ABI)
  t6050-pmgr.dtsi   PMGR power domains decoded from the ADT `devices` table,
                    with parent dependencies
  t6050-j716c.dts   board file

Evidence / provenance:
  * PMGR `devices` record layout (48 bytes), `ps-groups`/`ps-regs` records and
    the u8/u16 device-id detection follow m1n1 (MIT/GPL-2.0+, AsahiLinux/m1n1):
    proxyclient/m1n1/adt.py (PMGRDevices, PMGRPSRegs, pmgr_dev_get_*) and
    src/pmgr.c (struct pmgr_device, pmgr_device_get_addr).  The DT node layout
    mirrors m1n1 proxyclient/tools/pmgr_adt2dt.py and Asahi's t8132-pmgr.dtsi.
    No m1n1 code is copied; this is an independent stdlib-only decoder.
  * CPU MPIDR layout (M core = 0x40000|cluster<<8|core, P core =
    0x10000|cluster<<8|core) from m1n1 commit 5d84c4c3 (2026-06-29).
  * M4+ NVMe register split (NVMMU = ans reg[3], NVMe = ans reg[9]) from m1n1
    commit 53f8ee9b; SARTv4 from m1n1 commit 9bfdf8ae.

STATUS: never booted.  Values marked HYPOTHESIS must be confirmed on hardware.
This file is local research output (Asahi's generative-AI policy forbids
submitting it upstream; see README.md).

Usage: gen_t6050_dt.py ADT_JSON OUTDIR
"""
import json
import re
import struct
import sys

PAGE = 0x4000

# --------------------------------------------------------------- ADT helpers


def load(path):
    tree = json.load(open(path))
    nodes = {}

    def walk(n):
        nodes[n["path"].replace("/Root/device-tree", "") or "/"] = n["values"]
        for c in n["children"]:
            walk(c)
    walk(tree["children"][0])
    return nodes


def u32s(v):
    if isinstance(v, int):
        return [v]
    return [int(x, 16) if isinstance(x, str) else x for x in v]


def blob(v):
    return bytes.fromhex(v["hex"])


def arm_io_ranges(nodes):
    w = u32s(nodes["/arm-io"]["ranges"])
    out = []
    for i in range(0, len(w) - 5, 6):
        child = w[i] | (w[i + 1] << 32)
        parent = w[i + 2] | (w[i + 3] << 32)
        size = w[i + 4] | (w[i + 5] << 32)
        out.append((child, parent, size))
    return out


def translate(ranges, addr):
    for child, parent, size in ranges:
        if child <= addr < child + size:
            return parent + (addr - child)
    raise ValueError("address %#x not covered by arm-io ranges" % addr)


def reg_of(nodes, path, index=0):
    r = nodes[path]["reg"][index]
    return int(r["addr"], 16), int(r["size"], 16)


def cells(addr, size):
    return "<0x%x 0x%08x 0x%x 0x%x>" % (addr >> 32, addr & 0xFFFFFFFF, size >> 32,
                                        size & 0xFFFFFFFF)


def irqs(nodes, path):
    return u32s(nodes[path].get("interrupts", []))


def align_up(x, a):
    return (x + a - 1) & ~(a - 1)


def label_of(name):
    return re.sub(r"[^a-z0-9_]", "_", name.lower())


# --------------------------------------------------------------- PMGR decode
# Record layouts as documented in m1n1 proxyclient/m1n1/adt.py:
#   PMGRDevices (48 bytes): flags u8 | unk1 u8[2] | id1 u8 | parents
#     (u8[2]+pad or u16[2]) | perf_idx u8 | perf_block u8 | psidx u8 | psreg u8 |
#     unk2_0 u16 | pd u8 | ps_cfg16 u8 | offset u24 | group u8 | unk2_2 u32 |
#     unk2_3 u16 | id2 u16 | unk3 u32 | name char[16]
#   flags bits (MSB..LSB): b7 b6 perf no_ps critical b2 notify_pmp on
#   PMGRPSRegs (12 bytes): reg u32 | offset u32 | mask u32  (ps-regs, ps-groups)
FLAG_ON, FLAG_NOTIFY_PMP, FLAG_B2, FLAG_CRITICAL, FLAG_NO_PS = 0x01, 0x02, 0x04, 0x08, 0x10


def decode_pmgr(nodes, rng):
    pm = nodes["/arm-io/pmgr"]
    raw = blob(pm["devices"])
    assert len(raw) % 48 == 0, "unexpected PMGR device record size"
    devs = []
    for i in range(0, len(raw), 48):
        e = raw[i:i + 48]
        devs.append({
            "index": i // 48,
            "flags": e[0],
            "id1": e[3],
            "par8": (e[4], e[5]),
            "par16": struct.unpack_from("<HH", e, 4),
            "psidx": e[10],
            "psreg": e[11],
            "offset": e[16] | (e[17] << 8) | (e[18] << 16),
            "group": e[19],
            "id2": struct.unpack_from("<H", e, 26)[0],
            "name": e[32:48].split(b"\0")[0].decode("ascii"),
        })
    # m1n1: u8 ids are in use iff the first two records have different id1
    u8id = len(devs) >= 2 and devs[0]["id1"] != devs[1]["id1"]
    for d in devs:
        d["id"] = d["id1"] if u8id else d["id2"]
        d["parents"] = [p for p in (d["par8"] if u8id else d["par16"]) if p]
    if "ps-regs" in pm:
        mode, table = "ps-regs", blob(pm["ps-regs"])
    else:
        mode, table = "ps-groups", blob(pm["ps-groups"])
    psrec = [struct.unpack_from("<III", table, i) for i in range(0, len(table), 12)]
    preg = pm["reg"]
    for d in devs:
        if d["flags"] & FLAG_NO_PS:
            d["block"] = None
            continue
        if mode == "ps-groups":
            ri, roff, _ = psrec[d["group"]]
            off = roff + d["offset"]
            d["block_key"] = d["group"]
        else:
            ri, roff, _ = psrec[d["psreg"]]
            off = roff + d["psidx"] * 8
            d["block_key"] = d["psreg"]
        child, size = int(preg[ri]["addr"], 16), int(preg[ri]["size"], 16)
        d["reg_index"] = ri
        d["block"] = (translate(rng, child), size)
        d["ps_offset"] = off
    return devs, mode, psrec, u8id


# Domains Linux must never manage through genpd: CPU cores/cluster power
# managers, fabrics, die-to-die bridges, memory controllers.  Asahi's
# t8132-pmgr.dtsi omits the same classes.  (Most are flagged `critical`.)
PMGR_EXCLUDE = re.compile(
    r"^(MCPU\d+_\d+|PCPU_\d+|ECPU\d*_?\d*|MCPM\d+|PCPM|ECPM\d*|[MPE]ACC.*|"
    r"FAB.*|AFI.*|AFC.*|B2B.*|AMCC\d+|DCS_\d+|SBR.*|PMS|PMS_GFX|TRACE_FAB.*|"
    r"FPPT.*|PMGR_SOC_OCLA.*)$")

# apple,always-on overrides (in addition to the ADT `critical` flag).
PMGR_ALWAYS_ON = {
    "AIC": "core device",
    "AIC_GFX": "core device (second die), HYPOTHESIS",
    "ANS": "Asahi t8132: device reboots after 3-5 min if disabled",
    "DISP_SYS": "TODO: boot framebuffer; figure out if PM can be enabled",
    "DISP_FE": "TODO: boot framebuffer; figure out if PM can be enabled",
    "UART_P": "parent of uart0 (Asahi t8132 marks it always-on)",
    "SPI_P": "Asahi t8132 marks it always-on",
    "CS": "GPU-side fabric block, conservative HYPOTHESIS",
}
# Locked by firmware on M4 (Asahi t8132-pmgr.dtsi): never touch.
PMGR_LOCKED = re.compile(r"^(DISP_CPU|DISPEXT\d+_CPU)$")

# Container labels per ps-group (t6050-specific, see README.md):
PMGR_BLOCK_LABELS = {
    0: "pmgr",          # ADT pmgr reg[0]
    1: "pmgr1",         # reg[1]  (SIO, I2C, UART, ANS, APCIE ...)
    2: "pmgr_mini",     # reg[9]  (always-on NUB: SPMI, NUB_GPIO, ATC USB ...)
    3: "pmgr_gfx",      # reg[51] (GPX/AFR/CS/GFX, like t6031 pmgr_gfx)
    4: "pmgr_die1",     # reg[46] (+0x21_0000_0000: *_GFX duplicates, media, AMCC)
    5: "pmgr_die1_mini",  # reg[49] (NUB_GFX_GPIO, DEBUG_GFX_GATED)
}


class Pmgr:
    def __init__(self, nodes, rng):
        self.devs, self.mode, self.psrec, self.u8id = decode_pmgr(nodes, rng)
        self.by_id = {d["id"]: d for d in self.devs}
        self.by_name = {}
        for d in self.devs:
            if d["block"] is not None:
                self.by_name.setdefault(d["name"], d)
        self.emit = [d for d in self.devs
                     if d["block"] is not None and not PMGR_EXCLUDE.match(d["name"])]
        self.emit_ids = {d["id"] for d in self.emit}
        seen = {}
        for d in self.emit:
            lab = "ps_" + label_of(d["name"])
            if lab in seen:
                lab += "_%d" % d["id"]
            seen[lab] = d
            d["label"] = lab
        self.blocks = {}
        for d in self.emit:
            self.blocks.setdefault(d["block_key"], []).append(d)

    def resolve(self, dev_id, depth=0):
        """Nearest emitted ancestors of a device (walks through virtual and
        excluded devices, which have no node in the DT)."""
        if depth > 32:
            raise RuntimeError("PMGR parent cycle at id %d" % dev_id)
        d = self.by_id.get(dev_id)
        if d is None:
            return []
        if d["id"] in self.emit_ids:
            return [d]
        out = []
        for p in d["parents"]:
            for a in self.resolve(p, depth + 1):
                if a not in out:
                    out.append(a)
        return out

    def parents_of(self, d):
        out = []
        for p in d["parents"]:
            for a in self.resolve(p):
                if a not in out and a is not d:
                    out.append(a)
        return out

    def domains_for_gates(self, gates):
        """ADT clock-gates value(s) -> list of emitted PMGR devices."""
        out = []
        for g in gates:
            dev_id = g & 0xFFFF   # m1n1 PMGR_DEVICE_ID; die in bits 31:28
            for a in self.resolve(dev_id):
                if a not in out:
                    out.append(a)
        return out

    def label(self, name):
        d = self.by_name.get(name)
        if d is None or "label" not in d:
            return None
        return d["label"]

    def block_reg(self, key):
        devs = self.blocks[key]
        base, size = devs[0]["block"]
        maxoff = max(d["ps_offset"] for d in devs)
        return base, min(size, align_up(maxoff + 4, PAGE))


def pd_list(labels):
    return ", ".join("<&%s>" % l for l in labels)


# --------------------------------------------------------------- CPU / DVFS


def mpidr_of(v):
    """m1n1 5d84c4c3: MPIDR_EL1 = 0x80000X0Y (E), 0x80010X0Y (P), 0x80040X0Y (M),
    X = cluster, Y = core.  DT `reg` = MPIDR & 0xffffff (m1n1 dt_set_cpus)."""
    reg = int(v["reg"][0]["addr"], 16)
    cluster, core = (reg >> 8) & 0x7, reg & 0xFF
    ctype = v["cluster-type"][0]
    aff2 = {"P": 0x1, "M": 0x4, "E": 0x0}[ctype]
    return (aff2 << 16) | (cluster << 8) | core


def dvfs_tables(nodes):
    """acc-clusters: u32 pairs (cluster << 8 | voltage-states index, 0).
    voltage-statesN-sram: (freq kHz, SRAM mV); voltage-statesN: (65535e6/f_kHz,
    core mV).  Returns {cluster: [(hz, core_uV), ...]}."""
    pm = nodes["/arm-io/pmgr"]
    acc = struct.unpack("<6I", blob(pm["acc-clusters"]))
    out = {}
    for i in range(0, len(acc), 2):
        cluster, table = acc[i] >> 8, acc[i] & 0xFF
        core = struct.unpack("<%dI" % (len(blob(pm["voltage-states%d" % table])) // 4),
                             blob(pm["voltage-states%d" % table]))
        sram = struct.unpack("<%dI" % (len(blob(pm["voltage-states%d-sram" % table])) // 4),
                             blob(pm["voltage-states%d-sram" % table]))
        ops = []
        for j in range(0, len(sram), 2):
            khz, period, mv = sram[j], core[j], core[j + 1]
            # consistency check of the decoded semantics: period * f == 65535e6
            assert abs(period * khz - 65535e6) / 65535e6 < 0.001, (table, j)
            ops.append((khz * 1000, mv * 1000))
        out[cluster] = (table, ops)
    return out


# HYPOTHESIS (see kernel/native-enablement/plan.md, item f): from macOS
# IOReport energy (benchmarks/results/macos-2026-10-11-power): P core
# ~5.65 W at 4512 MHz / 1.090 V; M core ~2.48 W at 4380 MHz / 1.015 V.
# dynamic-power-coefficient = P[uW] / (V^2 * f[MHz]); includes leakage.
DPC = {"P": 1054, "M": 550}
# HYPOTHESIS: M-core per-clock throughput ~0.75x P (bg-QoS FMA run at an
# uncertain M-core clock).  Must be measured natively at equal frequency.
CAPACITY = {"P": 1024, "M": 768}
# PLACEHOLDER: not measured (m1n1 experiments/cpu_pstate_latencies.py).
CLOCK_LATENCY_NS = 50000


# --------------------------------------------------------------- DARTs

DART_SKIP = {
    "/arm-io/dart-sep": "SEP (secure)",
    "/arm-io/dart-ane0": "ANE is exclave-managed (ane,t8132exclave)",
    "/arm-io/dart-isp0": "ISP has exclave mappers",
    "/arm-io/dart-aop": "AOP has an exclave mapper",
    "/arm-io/dart-pmp0": "PMP coprocessor, no Linux consumer planned",
    "/arm-io/dart-scaler": "aggregate of dart-scaler0/1 (same MMIO)",
}


def dart_instances(v):
    """`instance` = 16-byte records (FourCC type, index, char name[8]) that
    label the `reg` entries 1:1 (e.g. DART/DART, SMMU, DAPF, GAPF/PS_PROT)."""
    w = u32s(v.get("instance", []))
    out = []
    for i in range(0, len(w) - 3, 4):
        t = struct.pack(">I", w[i]).decode("ascii", "replace")
        out.append((t, w[i + 1]))
    return out


# --------------------------------------------------------------- main


def main():
    adt, outdir = sys.argv[1], sys.argv[2]
    nodes = load(adt)
    rng = arm_io_ranges(nodes)
    pmgr = Pmgr(nodes, rng)
    cpus = sorted((p for p in nodes if re.match(r"^/cpus/cpu\d+$", p)),
                  key=lambda p: nodes[p]["cpu-id"])
    dvfs = dvfs_tables(nodes)

    L = []
    a = L.append
    a("// SPDX-License-Identifier: GPL-2.0+ OR MIT")
    a("/*")
    a(" * Apple t6050 \"M5 Max\" SoC - DRAFT device tree.")
    a(" *")
    a(" * Generated by kernel/experiments/t6050-dt/gen_t6050_dt.py from a sanitized")
    a(" * macOS ADT capture of a Mac17,6 (J716c).  UNTESTED: never booted.  See")
    a(" * README.md and kernel/native-enablement/plan.md for evidence labels.")
    a(" */")
    a("")
    a("#include <dt-bindings/interrupt-controller/apple-aic.h>")
    a("#include <dt-bindings/interrupt-controller/irq.h>")
    a("#include <dt-bindings/pinctrl/apple.h>")
    a("")
    a("/ {")
    a('\tcompatible = "apple,t6050", "apple,arm-platform";')
    a("\t#address-cells = <2>;")
    a("\t#size-cells = <2>;")
    a("")
    a("\tcpus {")
    a("\t\t#address-cells = <2>;")
    a("\t\t#size-cells = <0>;")
    a("")
    a("\t\tcpu-map {")
    clusters = {}
    for p in cpus:
        clusters.setdefault(nodes[p]["cluster-id"], []).append(p)
    labels = {}
    for cid in sorted(clusters):
        a("\t\t\tcluster%d {" % cid)
        for i, p in enumerate(clusters[cid]):
            v = nodes[p]
            ctype = v["cluster-type"][0].lower()
            lab = "cpu_%s%d%d" % (ctype, cid, i) if ctype == "m" else "cpu_%s%d" % (ctype, i)
            labels[p] = lab
            a("\t\t\t\tcore%d {" % i)
            a("\t\t\t\t\tcpu = <&%s>;" % lab)
            a("\t\t\t\t};")
        a("\t\t\t};")
    a("\t\t};")
    a("")
    for p in cpus:
        v = nodes[p]
        mpidr = mpidr_of(v)
        ctype = v["cluster-type"][0]
        cid = v["cluster-id"]
        a("\t\t/* ADT %s: cluster %d type %s (%s), ADT reg 0x%s; MPIDR per m1n1 5d84c4c3 */"
          % (p.split("/")[-1], cid, ctype, v["compatible"][0], v["reg"][0]["addr"][2:]))
        a("\t\t%s: cpu@%x {" % (labels[p], mpidr))
        a('\t\t\tcompatible = "apple,sotra-%s"; /* placeholder: needs a DT binding */'
          % ctype.lower())
        a('\t\t\tdevice_type = "cpu";')
        a("\t\t\treg = <0x0 0x%x>;" % mpidr)
        a('\t\t\tenable-method = "spin-table";')
        a("\t\t\tcpu-release-addr = <0 0>; /* filled in by m1n1 */")
        a("\t\t\tnext-level-cache = <&l2_cache_%d>;" % cid)
        a("\t\t\ti-cache-size = <0x%x>;" % (0x30000 if ctype == "P" else 0x20000))
        a("\t\t\td-cache-size = <0x%x>;" % (0x20000 if ctype == "P" else 0x10000))
        if cid in dvfs:
            a("\t\t\toperating-points-v2 = <&cluster%d_opp>;" % cid)
            a("\t\t\tperformance-domains = <&cpufreq%d>;" % cid)
            a("\t\t\tcapacity-dmips-mhz = <%d>; /* HYPOTHESIS */" % CAPACITY[ctype])
            a("\t\t\tdynamic-power-coefficient = <%d>; /* HYPOTHESIS */" % DPC[ctype])
        a("\t\t};")
        a("")
    for cid in sorted(clusters):
        size = nodes[clusters[cid][0]]["l2-cache-size"]
        a("\t\tl2_cache_%d: l2-cache-%d {" % (cid, cid))
        a('\t\t\tcompatible = "cache";')
        a("\t\t\tcache-level = <2>;")
        a("\t\t\tcache-unified;")
        a("\t\t\tcache-size = <0x%x>;" % size)
        a("\t\t};")
        a("")
    a("\t};")
    a("")
    # OPP tables
    for cid in sorted(dvfs):
        table, ops = dvfs[cid]
        a("\t/*")
        a("\t * Cluster %d DVFS states from ADT pmgr voltage-states%d(-sram), selected by" % (cid, table))
        a("\t * pmgr acc-clusters.  opp-level = table index + 1 (HYPOTHESIS, M1-M3")
        a("\t * convention); opp-microvolt = core rail, only used by the energy model.")
        a("\t * clock-latency-ns is a PLACEHOLDER (not measured).")
        a("\t */")
        a("\tcluster%d_opp: opp-table-%d {" % (cid, cid))
        a('\t\tcompatible = "operating-points-v2";')
        a("\t\topp-shared;")
        a("")
        for i, (hz, uv) in enumerate(ops):
            a("\t\topp%02d {" % (i + 1))
            a("\t\t\topp-hz = /bits/ 64 <%d>;" % hz)
            a("\t\t\topp-level = <%d>;" % (i + 1))
            a("\t\t\topp-microvolt = <%d>;" % uv)
            a("\t\t\tclock-latency-ns = <%d>;" % CLOCK_LATENCY_NS)
            a("\t\t};")
        a("\t};")
        a("")
    a("\ttimer {")
    a('\t\tcompatible = "arm,armv8-timer";')
    a("\t\tinterrupt-parent = <&aic>;")
    a('\t\tinterrupt-names = "phys", "virt", "hyp-phys", "hyp-virt";')
    a("\t\tinterrupts = <AIC_FIQ AIC_TMR_GUEST_PHYS IRQ_TYPE_LEVEL_HIGH>,")
    a("\t\t\t     <AIC_FIQ AIC_TMR_GUEST_VIRT IRQ_TYPE_LEVEL_HIGH>,")
    a("\t\t\t     <AIC_FIQ AIC_TMR_HV_PHYS IRQ_TYPE_LEVEL_HIGH>,")
    a("\t\t\t     <AIC_FIQ AIC_TMR_HV_VIRT IRQ_TYPE_LEVEL_HIGH>;")
    a("\t};")
    a("")
    a("\tclkref: clock-ref {")
    a('\t\tcompatible = "fixed-clock";')
    a("\t\t#clock-cells = <0>;")
    a("\t\tclock-frequency = <%d>;" % nodes["/"]["clock-frequency"])
    a('\t\tclock-output-names = "clkref";')
    a("\t};")
    a("")
    a("\tsoc: soc {")
    a('\t\tcompatible = "simple-bus";')
    a("\t\t#address-cells = <2>;")
    a("\t\t#size-cells = <2>;")
    a("\t\tranges;")
    a("\t\tnonposted-mmio;")
    a("")
    body = []  # (address, lines) so that soc children are sorted by address

    def node(addr, lines):
        body.append((addr, lines))

    # cpufreq controllers: pmgr reg entries at acc-impl-reg base - 0xe0000
    preg = nodes["/arm-io/pmgr"]["reg"]
    ptrans = [(translate(rng, int(r["addr"], 16)), int(r["size"], 16)) for r in preg]
    for cid in sorted(clusters):
        acc = u32s(nodes[clusters[cid][0]]["acc-impl-reg"])
        acc_base = acc[0] | (acc[1] << 32)
        want = acc_base - 0xE0000
        hit = [s for b, s in ptrans if b == want]
        if not hit or cid not in dvfs:
            continue
        node(want, [
            "\t\t/* ADT pmgr reg entry 0x%x (+0x%x); same address pattern as the M1-M3"
            % (want, hit[0]),
            "\t\t * cluster DVFS blocks (LIKELY; register format unverified on t6050)."
            "  %d states" % len(dvfs[cid][1]),
            "\t\t * -> t8112-style 5-bit pstate field (as Asahi uses for M2/M3). */",
            "\t\tcpufreq%d: performance-controller@%x {" % (cid, want),
            '\t\t\tcompatible = "apple,t6050-cluster-cpufreq", "apple,t8112-cluster-cpufreq";',
            "\t\t\treg = %s;" % cells(want, 0x1000),
            "\t\t\t#performance-domain-cells = <0>;",
            "\t\t};",
        ])

    # PMGR containers (children are in t6050-pmgr.dtsi)
    for key in sorted(pmgr.blocks):
        base, size = pmgr.block_reg(key)
        lab = PMGR_BLOCK_LABELS.get(key, "pmgr_g%d" % key)
        ri = pmgr.blocks[key][0]["reg_index"]
        node(base, [
            "\t\t/* ADT pmgr ps-groups[%d] -> pmgr reg[%d] */" % (key, ri),
            "\t\t%s: power-management@%x {" % (lab, base),
            '\t\t\tcompatible = "apple,t6050-pmgr", "apple,t8103-pmgr", "syscon", "simple-mfd";',
            "\t\t\t#address-cells = <1>;",
            "\t\t\t#size-cells = <1>;",
            "\t\t\treg = %s;" % cells(base, size),
            "\t\t\t/* child nodes are added in t6050-pmgr.dtsi */",
            "\t\t};",
        ])

    # AIC3
    aic_child, aic_size = reg_of(nodes, "/arm-io/aic")
    aic = translate(rng, aic_child)
    iack = u32s(nodes["/arm-io/aic"].get("aic-iack-offset", [0x40000]))[0]
    pm_cores = [labels[p] for p in cpus if nodes[p]["cluster-type"][0] == "M"]
    pp_cores = [labels[p] for p in cpus if nodes[p]["cluster-type"][0] == "P"]
    node(aic, [
        "\t\t/* ADT aic: aic,3 rev %d, core size 0x%x (= t8122/t8132 AIC3).  IRQ_CFG at"
        % (nodes["/arm-io/aic"]["aic-rev"], aic_size),
        "\t\t * +extint-baseaddress 0x10000 and per-die stride 0x4a00 (= 4096 IRQs)",
        "\t\t * match the Linux AIC3 layout.  ADT aic-numdies-per-die = 2: whether",
        "\t\t * die-1 (GPU die) IRQs need 4-cell specifiers is UNKNOWN. */",
        "\t\taic: interrupt-controller@%x {" % aic,
        '\t\t\tcompatible = "apple,t6050-aic3", "apple,t8122-aic3";',
        "\t\t\t#interrupt-cells = <3>;",
        "\t\t\tinterrupt-controller;",
        "\t\t\treg = %s,\n\t\t\t      %s;" % (cells(aic, aic_size), cells(aic + iack, PAGE)),
        '\t\t\treg-names = "core", "event";',
        "\t\t\tpower-domains = <&%s>;" % pmgr.label("AIC"),
        "",
        "\t\t\taffinities {",
        "\t\t\t\tm-core-pmu-affinity {",
        "\t\t\t\t\tapple,fiq-index = <AIC_CPU_PMU_E>;",
        "\t\t\t\t\tcpus = <%s>;" % " ".join("&" + x for x in pm_cores),
        "\t\t\t\t};",
        "",
        "\t\t\t\tp-core-pmu-affinity {",
        "\t\t\t\t\tapple,fiq-index = <AIC_CPU_PMU_P>;",
        "\t\t\t\t\tcpus = <%s>;" % " ".join("&" + x for x in pp_cores),
        "\t\t\t\t};",
        "\t\t\t};",
        "\t\t};",
    ])

    # Watchdog: no PMGR device exists for it (it sits in the always-on
    # mini-PMGR MMIO window); Asahi's t8132 wdt has no power-domains either.
    w_child, w_size = reg_of(nodes, "/arm-io/wdt")
    w = translate(rng, w_child)
    node(w, [
        "\t\t/* ADT wdt-version %d: m1n1 disarms the secondary watchdog (reg[2]) before"
        % nodes["/arm-io/wdt"]["wdt-version"],
        "\t\t * boot.  No PMGR device -> no power-domains (as in Asahi t8132). */",
        "\t\twdt: watchdog@%x {" % w,
        '\t\t\tcompatible = "apple,t6050-wdt", "apple,t8103-wdt";',
        "\t\t\treg = %s;" % cells(w, w_size),
        "\t\t\tclocks = <&clkref>;",
        "\t\t\tinterrupt-parent = <&aic>;",
        "\t\t\tinterrupts = <AIC_IRQ %d IRQ_TYPE_LEVEL_HIGH>;" % irqs(nodes, "/arm-io/wdt")[0],
        "\t\t};",
    ])

    # Pinctrl / GPIO
    for path, lab, psname in (("/arm-io/gpio0", "pinctrl_ap", "GPIO"),
                              ("/arm-io/aop-gpio0", "pinctrl_aop", None),
                              ("/arm-io/nub-gpio0", "pinctrl_nub", "NUB_GPIO")):
        if path not in nodes or "reg" not in nodes[path]:
            continue
        c, s = reg_of(nodes, path)
        addr = translate(rng, c)
        npins = nodes[path].get("#gpio-pins")
        lines = ["\t\t%s: pinctrl@%x {" % (lab, addr),
                 '\t\t\tcompatible = "apple,t6050-pinctrl", "apple,t8103-pinctrl";',
                 "\t\t\treg = %s;" % cells(addr, s)]
        if psname and pmgr.label(psname):
            lines.append("\t\t\tpower-domains = <&%s>;" % pmgr.label(psname))
        else:
            lines.append("\t\t\t/* AOP_GPIO is a virtual PMGR device (AOP-managed): no domain */")
        lines += ["", "\t\t\tgpio-controller;", "\t\t\t#gpio-cells = <2>;"]
        if npins:
            lines += ["\t\t\tgpio-ranges = <&%s 0 0 %d>;" % (lab, npins),
                      "\t\t\tapple,npins = <%d>;" % npins]
        lines += ["", "\t\t\tinterrupt-controller;", "\t\t\t#interrupt-cells = <2>;",
                  "\t\t\tinterrupt-parent = <&aic>;",
                  "\t\t\tinterrupts = %s;" % ",\n\t\t\t\t     ".join(
                      "<AIC_IRQ %d IRQ_TYPE_LEVEL_HIGH>" % i for i in irqs(nodes, path)),
                  "\t\t};"]
        node(addr, lines)

    # I2C
    for i in range(16):
        path = "/arm-io/i2c%d" % i
        if path not in nodes:
            continue
        c, s = reg_of(nodes, path)
        addr = translate(rng, c)
        doms = pmgr.domains_for_gates(u32s(nodes[path].get("clock-gates", [])))
        node(addr, [
            "\t\ti2c%d: i2c@%x {" % (i, addr),
            '\t\t\tcompatible = "apple,t6050-i2c", "apple,t8103-i2c";',
            "\t\t\treg = %s;" % cells(addr, s),
            "\t\t\tclocks = <&clkref>;",
            "\t\t\tinterrupt-parent = <&aic>;",
            "\t\t\tinterrupts = <AIC_IRQ %d IRQ_TYPE_LEVEL_HIGH>;" % irqs(nodes, path)[0],
            "\t\t\t#address-cells = <0x1>;",
            "\t\t\t#size-cells = <0x0>;",
            "\t\t\tpower-domains = %s; /* ADT clock-gates */" % pd_list(d["label"] for d in doms),
            '\t\t\tstatus = "disabled";',
            "\t\t};",
        ])

    # UART0
    c, s = reg_of(nodes, "/arm-io/uart0")
    addr = translate(rng, c)
    doms = pmgr.domains_for_gates(u32s(nodes["/arm-io/uart0"].get("clock-gates", [])))
    node(addr, [
        "\t\t/* Not wired to an external connector on laptops; m1n1 uses the",
        "\t\t * dockchannel UART over debugusb instead (no Linux driver yet). */",
        "\t\tserial0: serial@%x {" % addr,
        '\t\t\tcompatible = "apple,s5l-uart";',
        "\t\t\treg = %s;" % cells(addr, s),
        "\t\t\treg-io-width = <4>;",
        "\t\t\tinterrupt-parent = <&aic>;",
        "\t\t\tinterrupts = <AIC_IRQ %d IRQ_TYPE_LEVEL_HIGH>;" % irqs(nodes, "/arm-io/uart0")[0],
        "\t\t\tclocks = <&clkref>, <&clkref>;",
        '\t\t\tclock-names = "uart", "clk_uart_baud0";',
        "\t\t\tpower-domains = %s; /* ADT clock-gates */" % pd_list(d["label"] for d in doms),
        '\t\t\tstatus = "disabled";',
        "\t\t};",
    ])

    # DARTs (draft, disabled: enable together with their consumer)
    for path in sorted(p for p in nodes if nodes[p].get("compatible", [""])[0] == "dart,t8110"):
        if path in DART_SKIP:
            continue
        v = nodes[path]
        inst = dart_instances(v)
        regs = v["reg"]
        name = path.split("/")[-1].replace("dart-", "")
        dart_regs = [(t, idx, r) for (t, idx), r in zip(inst, regs) if t == "DART"]
        gates = u32s(v.get("clock-gates", []))
        doms = pmgr.domains_for_gates(gates) if gates else []
        for t, idx, r in dart_regs:
            addr = translate(rng, int(r["addr"], 16))
            lab = "dart_%s%s" % (label_of(name), "_%d" % idx if len(dart_regs) > 1 else "")
            lines = ["\t\t%s: iommu@%x {" % (lab, addr),
                     '\t\t\tcompatible = "apple,t6050-dart", "apple,t8110-dart";',
                     "\t\t\treg = %s;" % cells(addr, int(r["size"], 16)),
                     "\t\t\t#iommu-cells = <1>;",
                     "\t\t\tinterrupt-parent = <&aic>;",
                     "\t\t\tinterrupts = <AIC_IRQ %d IRQ_TYPE_LEVEL_HIGH>;" % irqs(nodes, path)[0]]
            if doms:
                lines.append("\t\t\tpower-domains = %s; /* ADT clock-gates */"
                             % pd_list(d["label"] for d in doms))
            else:
                lines.append("\t\t\t/* TODO: power-domains (no ADT clock-gates) */")
            lines += ['\t\t\tstatus = "disabled"; /* DRAFT: ADT %s DART instance %d */'
                      % (path.split("/")[-1], idx), "\t\t};"]
            node(addr, lines)

    # SART (SARTv4 / sart,coastguard) + ANS mailbox + NVMe (M4+ register split)
    sv = nodes["/arm-io/sart-ans"]
    sc, ss = reg_of(nodes, "/arm-io/sart-ans")
    sart = translate(rng, sc)
    node(sart, [
        "\t\t/* ADT sart-ans: sart,coastguard, sart-version %d (m1n1 SARTv4, 9bfdf8ae)."
        % sv["sart-version"],
        "\t\t * Needs kernel/patches/t6050/0001 (no fallback: new register layout). */",
        "\t\tsart: iommu@%x {" % sart,
        '\t\t\tcompatible = "apple,t6050-sart";',
        "\t\t\treg = %s;" % cells(sart, ss),
        "\t\t\tpower-domains = <&%s>;" % pmgr.label("ANS"),
        "\t\t};",
    ])
    an = nodes["/arm-io/ans"]
    ans_base = translate(rng, int(an["reg"][0]["addr"], 16))
    nvmmu = translate(rng, int(an["reg"][3]["addr"], 16))
    nvmmu_size = int(an["reg"][3]["size"], 16)
    nvme = translate(rng, int(an["reg"][9]["addr"], 16))
    ans_irqs = u32s(an["interrupts"])
    nvme_irq = ans_irqs[an["nvme-interrupt-idx"]]
    mbox_irqs = sorted(ans_irqs[:4])
    node(ans_base + 0x8000, [
        "\t\t/* ASC mailbox at ans reg[0] + 0x8000 (m1n1 asc.c; works on t6050 in m1n1).",
        "\t\t * IRQ order sorted from ADT ans interrupts[0..3] (LIKELY, by analogy",
        "\t\t * with t8103/t6031). */",
        "\t\tans_mbox: mbox@%x {" % (ans_base + 0x8000),
        '\t\t\tcompatible = "apple,t6050-asc-mailbox", "apple,asc-mailbox-v4";',
        "\t\t\treg = %s;" % cells(ans_base + 0x8000, PAGE),
        "\t\t\tinterrupt-parent = <&aic>;",
        "\t\t\tinterrupts = %s;" % ",\n\t\t\t\t     ".join(
            "<AIC_IRQ %d IRQ_TYPE_LEVEL_HIGH>" % i for i in mbox_irqs),
        '\t\t\tinterrupt-names = "send-empty", "send-not-empty",',
        '\t\t\t\t\t  "recv-empty", "recv-not-empty";',
        "\t\t\tpower-domains = <&%s>;" % pmgr.label("ANS"),
        "\t\t\t#mbox-cells = <0>;",
        "\t\t};",
    ])
    st = [pmgr.label(n) for n in ("ANS", "APCIE_SYS_ST0", "APCIE_SYS_ST1")]
    node(nvme, [
        "\t\t/* ADT ans: iop,ascwrap-v6, nvme-secure-bar present -> M4+ layout (m1n1",
        "\t\t * 53f8ee9b): NVMe regs = reg[9], NVMMU regs = reg[3].  The nvme window is",
        "\t\t * 0x40000 because m1n1 accesses +0x24908..0x24910 through reg[9] although",
        "\t\t * the ADT size is 0x%x (LIKELY).  IRQ = interrupts[nvme-interrupt-idx=%d]."
        % (int(an["reg"][9]["size"], 16), an["nvme-interrupt-idx"]),
        "\t\t * Needs kernel/patches/t6050/0003. */",
        "\t\tnvme: nvme@%x {" % nvme,
        '\t\t\tcompatible = "apple,t6050-nvme-ans2", "apple,t8132-nvme-ans2";',
        "\t\t\treg = %s,\n\t\t\t      %s,\n\t\t\t      %s;" % (
            cells(nvme, 0x40000), cells(ans_base, PAGE), cells(nvmmu, nvmmu_size)),
        '\t\t\treg-names = "nvme", "ans", "nvmmu";',
        "\t\t\tinterrupt-parent = <&aic>;",
        "\t\t\tinterrupts = <AIC_IRQ %d IRQ_TYPE_LEVEL_HIGH>;" % nvme_irq,
        "\t\t\tmboxes = <&ans_mbox>;",
        "\t\t\tapple,sart = <&sart>;",
        "\t\t\tpower-domains = %s;" % pd_list(st),
        '\t\t\tpower-domain-names = "ans", "apcie0", "apcie1";',
        "\t\t\tresets = <&%s>;" % st[0],
        '\t\t\tstatus = "disabled"; /* DRAFT */',
        "\t\t};",
    ])

    for _, lines in sorted(body, key=lambda x: x[0]):
        L.extend(lines)
        L.append("")
    if L[-1] == "":
        L.pop()
    a("\t};")
    a("};")
    a("")
    a('#include "t6050-pmgr.dtsi"')
    open(outdir + "/t6050.dtsi", "w").write("\n".join(L) + "\n")

    # ---------------------------------------------------- t6050-pmgr.dtsi
    P = []
    b = P.append
    b("// SPDX-License-Identifier: GPL-2.0+ OR MIT")
    b("/*")
    b(" * PMGR power domains for the Apple t6050 \"M5 Max\" SoC - DRAFT, never booted.")
    b(" *")
    b(" * Generated by gen_t6050_dt.py from the ADT /arm-io/pmgr `devices` table")
    b(" * (%d records, %s ids, address mode %s) using the record layout documented in"
      % (len(pmgr.devs), "u8" if pmgr.u8id else "u16", pmgr.mode))
    b(" * m1n1 proxyclient/m1n1/adt.py.  Emitted: %d domains.  Skipped: %d virtual"
      % (len(pmgr.emit), sum(1 for d in pmgr.devs if d["block"] is None)))
    b(" * (no_ps) devices and %d CPU/fabric/memory-controller domains (as in Asahi's"
      % sum(1 for d in pmgr.devs if d["block"] is not None and PMGR_EXCLUDE.match(d["name"])))
    b(" * t8132-pmgr.dtsi).  Parents that are virtual or skipped are replaced by their")
    b(" * nearest emitted ancestors.  apple,always-on = ADT `critical` flag or an")
    b(" * override (commented).  First boots should use pd_ignore_unused.")
    b(" */")
    b("")
    for key in sorted(pmgr.blocks):
        lab = PMGR_BLOCK_LABELS.get(key, "pmgr_g%d" % key)
        b("&%s {" % lab)
        first = True
        for d in sorted(pmgr.blocks[key], key=lambda d: d["ps_offset"]):
            if not first:
                b("")
            first = False
            b("\t%s: power-controller@%x {" % (d["label"], d["ps_offset"]))
            b('\t\tcompatible = "apple,t6050-pmgr-pwrstate", "apple,t8103-pmgr-pwrstate";')
            b("\t\treg = <0x%x 4>;" % d["ps_offset"])
            b("\t\t#power-domain-cells = <0>;")
            b("\t\t#reset-cells = <0>;")
            b('\t\tlabel = "%s";' % label_of(d["name"]))
            parents = pmgr.parents_of(d)
            if parents:
                b("\t\tpower-domains = %s;" % pd_list(p["label"] for p in parents))
            if d["flags"] & FLAG_CRITICAL:
                b("\t\tapple,always-on; /* ADT critical */")
            elif d["name"] in PMGR_ALWAYS_ON:
                b("\t\tapple,always-on; /* %s */" % PMGR_ALWAYS_ON[d["name"]])
            if PMGR_LOCKED.match(d["name"]):
                b('\t\tstatus = "disabled"; /* Locked on M4 (Asahi t8132), don\'t touch */')
            b("\t};")
        b("};")
        b("")
    open(outdir + "/t6050-pmgr.dtsi", "w").write("\n".join(P))

    # ---------------------------------------------------- board file
    root = nodes["/"]
    B = []
    c = B.append
    c("// SPDX-License-Identifier: GPL-2.0+ OR MIT")
    c("/*")
    c(" * Apple MacBook Pro (16-inch, M5 Max), %s / %s - DRAFT, untested."
      % (root["model"][0], root["target-type"][0]))
    c(" *")
    c(" * m1n1 (M4+ path) appends \"idle=nop arm64.nowfxt\" to bootargs and reserves")
    c(" * the secondary-core CTRR region itself.  Recommended extra first-boot")
    c(" * arguments: pd_ignore_unused clk_ignore_unused (PMGR table never validated).")
    c(" */")
    c("")
    c("/dts-v1/;")
    c("")
    c('#include "t6050.dtsi"')
    c("")
    c("/ {")
    c('\tcompatible = "apple,%s", "apple,t6050", "apple,arm-platform";'
      % root["target-type"][0].lower())
    c('\tmodel = "Apple MacBook Pro (16-inch, M5 Max)";')
    c("")
    c("\taliases {")
    c("\t\tserial0 = &serial0;")
    c("\t};")
    c("")
    c("\tchosen {")
    c("\t\t#address-cells = <2>;")
    c("\t\t#size-cells = <2>;")
    c("\t\tranges;")
    c('\t\tstdout-path = "serial0";')
    c("\t};")
    c("")
    c("\tmemory@10000000000 {")
    c('\t\tdevice_type = "memory";')
    c("\t\treg = <0x100 0 0x2 0>; /* placeholder; m1n1 fills in the real map */")
    c("\t};")
    c("};")
    c("")
    c("&serial0 {")
    c('\tstatus = "okay";')
    c("};")
    open(outdir + "/t6050-%s.dts" % root["target-type"][0].lower(), "w").write("\n".join(B) + "\n")
    print("wrote t6050.dtsi, t6050-pmgr.dtsi and board dts: %d cpus, %d clusters, "
          "%d PMGR domains in %d blocks, %d OPP tables"
          % (len(cpus), len(clusters), len(pmgr.emit), len(pmgr.blocks), len(dvfs)),
          file=sys.stderr)


if __name__ == "__main__":
    main()
