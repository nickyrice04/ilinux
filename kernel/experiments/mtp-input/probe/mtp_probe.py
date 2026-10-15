#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only OR MIT
"""Read-only m1n1-proxy probe of the J716c MTP (keyboard/trackpad coprocessor) blocks.

PREPARED, NOT RUN. Needs the user's approval and the M1 agent; see
tools/m1n1-client style instructions in ../README.md ("Hardware experiments").

It sends 32-bit register READS only, to a fixed list of offsets derived from the
target's own ADT, inside the regions that ADT declares, and never to a register
whose read has a side effect (mailbox RECV, DockChannel RX data). The object the
read code sees cannot write: there is no write method on it to call.

What it answers (each is a Hypothesis in the README until a run says otherwise):
  * DART: where the register block starts (+0 or +0x8000 of the ADT region),
    version, number of stream ids, and which stream ids iBoot left translating
    (TCR/TTBR). That settles "which SID does the MTP ASC use" and whether
    `iommus = <&mtp_dart 1>` or `<&mtp_dart 0>` is right.
  * ASC: is the MTP CPU running, and is its mailbox empty/idle (v4 or M3 layout).
  * DockChannel: FIFO depth (TX free when idle), RX count, thresholds, IRQ mask/flag.

usage:
  python3 -I mtp_probe.py plan [--adt PATH]            offline: the exact read list
  python3 -I mtp_probe.py read --device auto --confirm MTP-PROBE-J716C-READ --json NEW.json
"""
import argparse
import json
import os
import re
import signal
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(EXPERIMENT))
import mtp_adt  # noqa: E402

CHIP_T6050 = 0x6050
CONFIRM_READ = "MTP-PROBE-J716C-READ"
SCHEMA = 1
DEFAULT_ADT = ROOT / "hardware" / "adt" / "adt-sanitized.json"

EXIT_OK, EXIT_STOP, EXIT_INTERRUPTED = 0, 1, 130

# ---- register layouts (public Linux 77cb8f24 and m1n1 57a9339 headers; labelled there)
ASC_CPU_CONTROL = 0x44          # m1n1 src/asc.c
ASC_CPU_CONTROL_START = 0x10
MBOX_BASE_OFFSET = 0x8000       # m1n1 asc_init(): base + 0x8000
MBOX_V4 = {"a2i_control": 0x110, "i2a_control": 0x114}      # apple,asc-mailbox-v4
MBOX_M3 = {"a2i_control": 0x50, "i2a_control": 0x80}        # apple,m3-mailbox-v2
MBOX_FULL, MBOX_EMPTY = 1 << 16, 1 << 17

DART_WINDOW = 0xc000
DART_ALT_BASE = 0x8000          # Asahi M2/M3 DTs put the register block here
DART_PARAMS = (0x00, 0x04, 0x08, 0x0c)      # PARAMS1, PARAMS2, T8110 PARAMS3, PARAMS4
DART_ERROR, DART_ERROR_MASK, DART_PROTECT = 0x100, 0x104, 0x200
DART_ENABLE_STREAMS, DART_ENABLE_WORDS = 0xc00, 8
DART_TCR, DART_TTBR = 0x1000, 0x1400        # ttbr_count == 1 for t8110
DART_MAX_SIDS_READ = 32

DOCK_CONFIG = {"tx_thresh": 0x0, "rx_thresh": 0x4}
DOCK_DATA = {"tx_free": 0x14, "rx_count": 0x2c}    # DATA_RX8/16/24/32 pop: never read
DOCK_IRQ = {"irq_mask": 0x0, "irq_flag": 0x4}
DOCK_REGION = 0x1000

# Offsets that must never appear in a read plan (reading them consumes data).
FORBIDDEN = {
    # v4 A2I/I2A RECV0/1 and M3 A2I/I2A RECV0/1: reading dequeues a mailbox message
    "mailbox": {0x810, 0x818, 0x830, 0x838, 0x70, 0x78, 0xa0, 0xa8},
    # DATA_RX8/16/24/32: reading pops bytes out of the DockChannel RX FIFO
    "dockchannel_data": {0x1c, 0x20, 0x24, 0x28},
}

DEVICE_PATH = re.compile(r"/dev/(?:cu|tty)\.[^\s'\"`:;,)\]}>]*")


class ProbeStop(Exception):
    def __init__(self, message, code=EXIT_STOP):
        super().__init__(message)
        self.code = code


class Forbidden(Exception):
    """Raised by the read-only proxy wrapper: a write attempt or an unplanned read."""


def say(text):
    print(text, flush=True)


def scrub(text):
    return DEVICE_PATH.sub("<device>", str(text))


# ------------------------------------------------------------------- regions

def regions_from_facts(facts):
    """The addresses the probe needs, from mtp_adt.facts() of the repo's ADT export."""
    dock = facts["dock_regs"]
    return {
        "asc": facts["asc"], "asc_window": facts["asc_window"],
        "dart": facts["dart"], "dart_window": facts["dart_window"],
        "dock": list(dock), "dock_sid_count": facts["sid_count"], "dart_sid": list(facts["sid"]),
    }


def regions_from_live_adt(adt):
    """Same dictionary from the target's parsed ADT (m1n1.adt.load_adt result).

    Only get_reg() and path indexing are used: both exist on every ADT node."""
    asc_addr, asc_size = adt["/arm-io/mtp"].get_reg(0)
    dart_addr, dart_size = adt["/arm-io/dart-mtp"].get_reg(0)
    dock = []
    node = adt["/arm-io/dockchannel-mtp"]
    for index in range(6):
        addr, size = node.get_reg(index)
        if size != DOCK_REGION:
            raise ProbeStop("dockchannel-mtp reg %d has size 0x%x, expected 0x%x"
                            % (index, size, DOCK_REGION))
        dock.append(int(addr))
    return {
        "asc": int(asc_addr), "asc_window": int(asc_size),
        "dart": int(dart_addr), "dart_window": int(dart_size),
        "dock": dock,
        "dock_sid_count": getattr(adt["/arm-io/dart-mtp"], "sid_count", None),
        "dart_sid": None,
    }


def compare_regions(repo, live):
    """List of differences between the repo's ADT facts and the target's ADT."""
    diffs = []
    for key in ("asc", "asc_window", "dart", "dart_window"):
        if repo[key] != live[key]:
            diffs.append("%s: repo 0x%x, target 0x%x" % (key, repo[key], live[key]))
    if repo["dock"] != live["dock"]:
        diffs.append("dockchannel regs differ")
    return diffs


def allowlist(regions):
    spans = [(regions["asc"], regions["asc"] + regions["asc_window"]),
             (regions["dart"], regions["dart"] + regions["dart_window"])]
    spans += [(base, base + DOCK_REGION) for base in regions["dock"]]
    return spans


# --------------------------------------------------------------- read wrapper

class ReadOnly:
    """read32 inside the declared regions, nothing else. No write method exists."""

    def __init__(self, proxy, spans):
        self._proxy = proxy
        self._spans = list(spans)
        self.reads = 0

    def read32(self, address):
        if not any(lo <= address and address + 4 <= hi for lo, hi in self._spans):
            raise Forbidden("read outside the declared regions: 0x%x" % address)
        value = self._proxy.read32(address)
        self.reads += 1
        return value & 0xffffffff

    def faulted(self):
        return bool(self._proxy.get_exc_count())

    def __getattr__(self, name):
        raise Forbidden("the probe's proxy has no %r (read-only)" % name)


# ---------------------------------------------------------------- read plan

def static_plan(reg):
    """Reads that do not depend on earlier results: (group, name, address)."""
    plan = []
    plan.append(("asc", "cpu_control", reg["asc"] + ASC_CPU_CONTROL))
    mbox = reg["asc"] + MBOX_BASE_OFFSET
    for layout, offsets in (("v4", MBOX_V4), ("m3", MBOX_M3)):
        for name, off in offsets.items():
            plan.append(("mailbox", "%s_%s" % (name, layout), mbox + off))
    for tag, base in (("plus0", reg["dart"]), ("plus8000", reg["dart"] + DART_ALT_BASE)):
        for index, off in enumerate(DART_PARAMS):
            plan.append(("dart_%s" % tag, "params%d" % (index + 1), base + off))
    dock = reg["dock"]
    plan.append(("dockchannel", "irq_mask", dock[1] + DOCK_IRQ["irq_mask"]))
    plan.append(("dockchannel", "irq_flag", dock[1] + DOCK_IRQ["irq_flag"]))
    for side, (cfg, dat) in (("local", (dock[2], dock[3])), ("remote", (dock[4], dock[5]))):
        for name, off in DOCK_CONFIG.items():
            plan.append(("dockchannel", "%s_%s" % (side, name), cfg + off))
        for name, off in DOCK_DATA.items():
            plan.append(("dockchannel", "%s_%s" % (side, name), dat + off))
    return plan


def dart_plan(base, num_sids):
    plan = []
    for name, off in (("error", DART_ERROR), ("error_mask", DART_ERROR_MASK),
                      ("protect", DART_PROTECT)):
        plan.append(("dart", name, base + off))
    for word in range(DART_ENABLE_WORDS):
        plan.append(("dart", "enable_streams%d" % word, base + DART_ENABLE_STREAMS + 4 * word))
    for sid in range(min(num_sids, DART_MAX_SIDS_READ)):
        plan.append(("dart", "tcr_sid%d" % sid, base + DART_TCR + 4 * sid))
        plan.append(("dart", "ttbr_sid%d" % sid, base + DART_TTBR + 4 * sid))
    return plan


def decode_params(p3, p4):
    return {
        "pa_width": (p3 >> 24) & 0x3f, "va_width": (p3 >> 16) & 0x3f,
        "ver_major": (p3 >> 8) & 0xff, "ver_minor": p3 & 0xff,
        "num_clients": (p4 >> 16) & 0x1ff, "num_sids": p4 & 0x1ff,
    }


def plausible(decoded):
    return (decoded["ver_major"] != 0 and 1 <= decoded["num_sids"] <= 256
            and 16 <= decoded["va_width"] <= 48 and 16 <= decoded["pa_width"] <= 48)


def decode_tcr(value):
    return {"translate": bool(value & 1), "bypass_dart": bool(value & 2),
            "bypass_dapf": bool(value & 4), "four_level": bool(value & 8),
            "remap_en": bool(value & 0x80), "remap": (value >> 8) & 0xf}


def decode_ttbr(value):
    return {"valid": bool(value & 1), "address": (value & 0xfffffffc) << 12}


# --------------------------------------------------------------------- run

def run_reads(proxy, reg):
    """Execute the plan through @proxy (a ReadOnly). Returns the result document body."""
    reads = []
    values = {}

    def do(group, name, address):
        entry = {"group": group, "name": name, "address": address}
        try:
            value = proxy.read32(address)
            if proxy.faulted():
                entry.update(status="trapped")
            else:
                entry.update(status="ok", value=value)
                values[(group, name)] = value
        except Forbidden:
            raise
        reads.append(entry)

    for group, name, address in static_plan(reg):
        do(group, name, address)

    # which DART register base looks like a t8110 PARAMS block
    candidates = {}
    for tag, base in (("plus0", reg["dart"]), ("plus8000", reg["dart"] + DART_ALT_BASE)):
        p3 = values.get(("dart_" + tag, "params3"))
        p4 = values.get(("dart_" + tag, "params4"))
        if p3 is not None and p4 is not None:
            decoded = decode_params(p3, p4)
            candidates[tag] = {"base": base, "decoded": decoded, "plausible": plausible(decoded)}
    chosen = None
    for tag in ("plus0", "plus8000"):
        if candidates.get(tag, {}).get("plausible"):
            chosen = tag
            break
    dart = {"candidates": candidates, "chosen": chosen, "streams": {}}
    if chosen is not None:
        base = candidates[chosen]["base"]
        num = candidates[chosen]["decoded"]["num_sids"]
        for group, name, address in dart_plan(base, num):
            do(group, name, address)
        for sid in range(min(num, DART_MAX_SIDS_READ)):
            tcr = values.get(("dart", "tcr_sid%d" % sid))
            ttbr = values.get(("dart", "ttbr_sid%d" % sid))
            if tcr is None or ttbr is None:
                continue
            dart["streams"][str(sid)] = {"tcr": tcr, "ttbr": ttbr,
                                         "tcr_decoded": decode_tcr(tcr),
                                         "ttbr_decoded": decode_ttbr(ttbr)}
        words = [values.get(("dart", "enable_streams%d" % i)) for i in range(DART_ENABLE_WORDS)]
        dart["enabled_sids"] = [i * 32 + b for i, w in enumerate(words) if w is not None
                                for b in range(32) if w >> b & 1 and i * 32 + b < 256]
    return reads, values, dart


def summarize(reg, values, dart):
    """Expectation table: every verdict is about a Hypothesis the README states."""
    rows = []

    def row(name, expected, observed, ok):
        rows.append({"name": name, "expected": expected, "observed": observed,
                     "verdict": "n/a" if observed is None else ("match" if ok else "differs")})

    chosen = dart.get("chosen")
    row("dart register block at +0 (m1n1 convention)", "plus0", chosen or "none", chosen == "plus0")
    if chosen:
        dec = dart["candidates"][chosen]["decoded"]
        row("dart NUM_SIDS equals ADT sid-count", reg.get("dock_sid_count"), dec["num_sids"],
            reg.get("dock_sid_count") in (None, dec["num_sids"]))
        translating = [int(s) for s, v in dart["streams"].items() if v["tcr_decoded"]["translate"]
                       or v["ttbr_decoded"]["valid"]]
        row("stream ids translating after iBoot (macOS remaps 1-4 to 0)", [0], translating,
            translating == [0])
    cpu = values.get(("asc", "cpu_control"))
    row("MTP CPU started by iBoot", True, None if cpu is None else bool(cpu & ASC_CPU_CONTROL_START),
        cpu is not None and bool(cpu & ASC_CPU_CONTROL_START))
    plausible_layouts = []
    seen_layout = False
    for layout in ("v4", "m3"):
        a2i = values.get(("mailbox", "a2i_control_" + layout))
        i2a = values.get(("mailbox", "i2a_control_" + layout))
        if a2i is None or i2a is None:
            continue
        seen_layout = True
        # a live mailbox control word has EMPTY xor FULL set
        if all(bool(v & MBOX_EMPTY) != bool(v & MBOX_FULL) for v in (a2i, i2a)):
            plausible_layouts.append(layout)
    row("mailbox: exactly one register layout (v4 or m3) has plausible control words",
        ["v4"], plausible_layouts if seen_layout else None, plausible_layouts == ["v4"])
    free = values.get(("dockchannel", "local_tx_free"))
    row("dockchannel local TX free == fifo-size when idle", mtp_adt.FIFO_SIZE, free,
        free == mtp_adt.FIFO_SIZE)
    return rows


def document(reg, repo_diffs, reads, values, dart, rows, chip, marker):
    return {
        "schema": SCHEMA, "tool": "mtp_probe", "chip": "t6050" if chip == CHIP_T6050 else hex(chip),
        "m1n1_marker": marker,
        "regions": dict(reg),
        "adt_vs_repo": repo_diffs, "reads": reads, "dart": dart, "expectations": rows,
        "note": "read-only; addresses and register values only, no identifiers",
    }


def print_report(reg, repo_diffs, dart, rows, out=say):
    out("ADT regions: asc 0x%x, dart 0x%x, dockchannel %s" % (
        reg["asc"], reg["dart"], ",".join("0x%x" % a for a in reg["dock"])))
    out("ADT vs repo facts: %s" % ("identical" if not repo_diffs else "; ".join(repo_diffs)))
    chosen = dart.get("chosen")
    if chosen:
        d = dart["candidates"][chosen]["decoded"]
        out("DART block %s: version %d.%d, %d SIDs, %d clients, VA %d bits, PA %d bits" % (
            chosen, d["ver_major"], d["ver_minor"], d["num_sids"], d["num_clients"],
            d["va_width"], d["pa_width"]))
        for sid, v in dart["streams"].items():
            if v["tcr_decoded"]["translate"] or v["ttbr_decoded"]["valid"]:
                out("  SID %s: translate=%s ttbr valid=%s ttbr=0x%x" % (
                    sid, v["tcr_decoded"]["translate"], v["ttbr_decoded"]["valid"],
                    v["ttbr_decoded"]["address"]))
    else:
        out("DART: no plausible PARAMS block at +0 or +0x8000")
    for r in rows:
        out("%-8s %s: expected %s, observed %s" % (r["verdict"].upper(), r["name"],
                                                   r["expected"], r["observed"]))


# ------------------------------------------------------------------- session

def session(api, device, json_path, adt_path, out=say):
    """One live read-only session. @api supplies open_primary/M1N1Proxy/load_adt/..."""
    repo_regions = regions_from_facts(mtp_adt.facts(adt_path))
    transport = None

    def alarm(*_):
        raise TimeoutError("probe exceeded its time budget; do not automatically retry")

    old = signal.signal(signal.SIGALRM, alarm)
    signal.alarm(120)
    try:
        transport, iface = api.open_primary(device)
        proxy = api.M1N1Proxy(iface)
        marker = api.check_target(iface, proxy)
        out("Target PASS: t6050, installed boot021, no started secondaries.")
        adt = api.fetch_adt(iface, proxy)
        reg = regions_from_live_adt(adt)
        reg["dock_sid_count"] = repo_regions["dock_sid_count"]
        diffs = compare_regions(repo_regions, reg)
        ro = ReadOnly(proxy, allowlist(reg))
        reads, values, dart = run_reads(ro, reg)
        rows = summarize(reg, values, dart)
        print_report(reg, diffs, dart, rows, out)
        if json_path is not None:
            with json_path.open("x") as handle:
                json.dump(document(reg, diffs, reads, values, dart, rows, CHIP_T6050, marker),
                          handle, indent=1, sort_keys=True)
                handle.write("\n")
            out("Wrote %s" % json_path.name)
        out("Finished: read only, no write request was sent (%d reads)." % ro.reads)
        return EXIT_OK
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)
        if transport is not None:
            try:
                transport.close()
            except Exception:
                pass


def connect_and_run(m1n1, device, json_path, adt_path):
    """Wire the pinned m1n1 client and the PMGR probe's reviewed gates; then session()."""
    sys.path.insert(0, str(ROOT / "native" / "probe"))
    import pmgr_probe as P  # reviewed gates: USB identity, chip, boot021 marker, no secondaries
    launch = P.launch
    import subprocess
    pin = subprocess.check_output(["git", "-C", str(m1n1), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(m1n1), "status", "--porcelain",
                                     "--untracked-files=no"], text=True)
    if pin != launch.M1N1_COMMIT or dirty:
        raise ProbeStop("client must be the clean pinned m1n1 checkout")
    sys.path.insert(0, str(m1n1 / "proxyclient"))
    from m1n1.adt import load_adt
    from m1n1.proxy import M1N1Proxy, UartInterface, Serial
    from m1n1.tgtypes import BootArgs_r1, BootArgs_r2, BootArgs_r3
    import json as _json
    manifest = _json.loads((P.BOOT / "package-manifest.json").read_text())
    marker, offset = manifest["m1n1_version_marker"], manifest["m1n1_version_offset"]
    types = {0: BootArgs_r1, 1: BootArgs_r1, 2: BootArgs_r2, 3: BootArgs_r3}

    class Api:
        M1N1Proxy = staticmethod(M1N1Proxy)

        @staticmethod
        def open_primary(dev):
            return P.open_primary(dev, UartInterface, Serial)

        @staticmethod
        def check_target(iface, proxy):
            P.check_target(iface, proxy, marker, offset)
            return marker

        @staticmethod
        def fetch_adt(iface, proxy):
            addr, rev = proxy.get_bootargs_rev()
            ba_type = types.get(rev)
            if ba_type is None:
                raise ProbeStop("unsupported boot_args revision %d" % rev)
            ba = iface.readstruct(addr, ba_type)
            if not 0 < ba.devtree_size <= 64 * 1024 * 1024:
                raise ProbeStop("ADT size 0x%x is implausible" % ba.devtree_size)
            adt_addr = (ba.devtree - ba.virt_base + ba.phys_base) & 0xFFFFFFFFFFFFFFFF
            return load_adt(iface.readmem(adt_addr, ba.devtree_size))

    return session(Api, device, json_path, adt_path)


# ---------------------------------------------------------------------- CLI

def _new_file(text):
    path = Path(text)
    if os.path.lexists(path):
        raise argparse.ArgumentTypeError("file exists; choose a new name")
    parent = path.parent if str(path.parent) else Path(".")
    if not parent.is_dir() or not os.access(parent, os.W_OK):
        raise argparse.ArgumentTypeError("directory does not exist or is not writable")
    return path


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    plan = sub.add_parser("plan", help="offline: print the exact read list (no device)")
    plan.add_argument("--adt", type=Path, default=DEFAULT_ADT)
    read = sub.add_parser("read", help="LIVE, read-only")
    read.add_argument("--device", help="auto, or the exact descriptor-verified primary callout")
    read.add_argument("--confirm", default="", help="must equal " + CONFIRM_READ)
    read.add_argument("--m1n1", type=Path, default=ROOT / "third_party" / "m1n1")
    read.add_argument("--adt", type=Path, default=DEFAULT_ADT)
    read.add_argument("--json", type=_new_file, help="also write a new JSON file")
    return ap


def main(argv=None, runner=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.mode == "plan":
        reg = regions_from_facts(mtp_adt.facts(args.adt))
        for group, name, address in static_plan(reg):
            say("READ %-18s %-22s 0x%x" % (group, name, address))
        for group, name, address in dart_plan(reg["dart"], 16):
            say("READ %-18s %-22s 0x%x  (after the DART base is chosen, at +0)" % (group, name, address))
        say("PLAN: %d reads, all 32-bit, none with a side effect; nothing was written."
            % (len(static_plan(reg)) + len(dart_plan(reg["dart"], 16))))
        return EXIT_OK
    if args.device is None or args.confirm != CONFIRM_READ:
        parser.error("live use requires --device and --confirm " + CONFIRM_READ)
    return (runner or connect_and_run)(args.m1n1, args.device, args.json, args.adt)


def cli(argv=None):
    try:
        return main(argv)
    except ProbeStop as exc:
        print("STOP: " + scrub(exc), file=sys.stderr)
        return exc.code
    except KeyboardInterrupt:
        print("STOP: KeyboardInterrupt", file=sys.stderr)
        return EXIT_INTERRUPTED
    except SystemExit:
        raise
    except BaseException as exc:
        print("STOP: %s %s" % (type(exc).__name__, scrub(exc)), file=sys.stderr)
        return EXIT_STOP


if __name__ == "__main__":
    sys.exit(cli())
