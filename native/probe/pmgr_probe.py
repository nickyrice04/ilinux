#!/usr/bin/env python3
"""Proxy-driven PMGR probe for the J716c (t6050): read-only first (private iLinux tooling).

Attempt 14's silent SoC reset came about 5.6 s after Linux's genpd sync_state powered
off the unclaimed boot-on PMGR domains. The m1n1 proxy can ask the same question one
domain at a time, in seconds, with no kernel build and no Linux boot (the standard Asahi
bring-up method). Never for upstream.

Subcommands, all against the installed boot021 m1n1 in a human-started lab RAM session:

  read   Stage 1, READ ONLY. Reads the ADT PMGR device table and every power-state
         register through the proxy, prints a sanitized table and optionally writes a
         JSON file. Sends no write request of any kind (it does not even build
         ProxyUtils, which would issue two heap-bookkeeping requests).
  plan   Prints which named domains stage 2 would power-cycle, or why it refuses each.
         Offline from a stage-1 JSON file (--from-json) or live (read only).
  cycle  Stage 2, WRITES. For explicitly named domains only (at most 4): power each
         off in the order given (children first), settle with the link checked after
         every one, then power them back on in reverse order and verify. Everything
         `plan` refuses is refused here, before the first write.

Register layout and the clear/set sequence are m1n1's own (src/pmgr.c: PS_TARGET bits
3:0, PS_ACTUAL bits 7:4, pmgr_set_mode() clears AUTO_ENABLE|WAS_CLKGATED|WAS_PWRGATED
and the target, then sets the new one). A dropped link or a reset must leave the last
printed line naming the domain, so every write is announced (and flushed) first.

The target's console text is never echoed (tty_enable off): it can carry the device
serial. Error text carries class names only, never a callout path; Ctrl-C prints one
scrubbed line.
"""
import argparse
import collections
import contextlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BOOT = ROOT / "native" / "boot"
sys.path.insert(0, str(BOOT))
import launch  # noqa: E402  (pin, marker gate helpers; unchanged and reviewed)
sys.path.insert(0, str(ROOT / "tools" / "m1n1-client"))
import usb_identity  # noqa: E402

CHIP_T6050 = 0x6050
CONFIRM_READ = "PMGR-PROBE-J716C-READ"
CONFIRM_CYCLE = "PMGR-PROBE-J716C-POWER-CYCLE"
SCHEMA = 1

# src/pmgr.h and src/pmgr.c in the pinned m1n1.
DIE_OFFSET = 0x2000000000
PS_ACTIVE, PS_CLKGATE, PS_PWRGATE = 0xF, 0x4, 0x0
RESET = 1 << 31
AUTO_ENABLE = 1 << 28
PS_AUTO = 0xF << 24
PARENT_OFF = 1 << 11
DEV_DISABLE = 1 << 10
WAS_CLKGATED = 1 << 9
WAS_PWRGATED = 1 << 8
PS_ACTUAL = 0xF0
PS_TARGET = 0xF
SET_MODE_CLEAR = AUTO_ENABLE | WAS_CLKGATED | WAS_PWRGATED | PS_TARGET  # pmgr_set_mode()

# ADT device flag names, most significant bit first (m1n1/adt.py PMGRDeviceFlags).
FLAG_NAMES = ("b7", "b6", "perf", "no_ps", "critical", "b2", "notify_pmp", "on")
FLAG_CODES = {"critical": "C", "no_ps": "V", "notify_pmp": "N", "on": "O", "perf": "P"}

# Device names whose parent closure the proxy link itself needs. This is what the
# m1n1 hypervisor's map_essential() keeps on for its USB link (UART0, ATCn_USB and
# ATCn_USB_AON, plus every parent). All ports are protected: the probe cannot know
# which one carries the cable.
LINK_ROOTS = (r"UART0", r"ATC\d+_USB", r"ATC\d+_USB_AON")

# Domains whose power-off is self-destructive although the ADT does not flag them
# critical (found in the real t6050 table: CPU cores and cluster managers are plain
# non-critical PS domains, as is the interrupt controller). Refused by name.
SYSTEM_ESSENTIAL = (
    (r"[MPE]CPU\d*(_\d+)?", "CPU core domain"),
    (r"[MPE]CPM\d*", "CPU cluster power manager"),
    (r"AIC\w*", "interrupt controller"),
)

MAX_DOMAINS = 4                 # power cycles per run
SETTLE_DEFAULT, SETTLE_MIN, SETTLE_MAX = 10.0, 1.0, 60.0
TAIL_DEFAULT, TAIL_MAX = 10.0, 60.0
STATE_POLL_TIMEOUT = 2.0        # seconds for ACTUAL to follow TARGET
LINK_POLL_INTERVAL = 0.5

EXIT_OK, EXIT_STOP, EXIT_REFUSED, EXIT_LINK_LOST, EXIT_NOT_RESTORED, EXIT_INTERRUPTED = (
    0, 1, 3, 4, 5, 130)

# A callout path embeds the device serial number.
DEVICE_PATH = re.compile(r"/dev/(?:cu|tty)\.[^\s'\"`:;,)\]}>]*")


class ProbeStop(Exception):
    """A deliberate stop with a sanitized message and an exit code."""

    def __init__(self, message, code=EXIT_STOP):
        super().__init__(message)
        self.code = code


class MmioFault(Exception):
    """The proxy reported an exception while accessing a register."""


def say(text):
    print(text, flush=True)


def scrub(text):
    """text with any /dev/cu.* or /dev/tty.* callout path removed."""
    return DEVICE_PATH.sub("<device>", str(text))


# --- state decoding -------------------------------------------------------------------
def state_name(value):
    return {PS_ACTIVE: "ACTIVE", PS_CLKGATE: "CLKGATE", PS_PWRGATE: "PWRGATE"}.get(
        value, "0x%x" % value)


def decode_state(raw):
    """Fields of one PS register word."""
    return {
        "raw": raw & 0xFFFFFFFF,
        "actual": (raw & PS_ACTUAL) >> 4,
        "target": raw & PS_TARGET,
        "auto_enable": bool(raw & AUTO_ENABLE),
        "reset": bool(raw & RESET),
        "dev_disable": bool(raw & DEV_DISABLE),
        "parent_off": bool(raw & PARENT_OFF),
        "was_clkgated": bool(raw & WAS_CLKGATED),
        "was_pwrgated": bool(raw & WAS_PWRGATED),
        "ps_auto": (raw & PS_AUTO) >> 24,
    }


# --- the ADT model --------------------------------------------------------------------
Device = collections.namedtuple("Device", "index name dev_id parents flags address users")
Model = collections.namedtuple("Model", "devices dies pmgr_path")


def _flag_set(flags):
    return frozenset(name for name in FLAG_NAMES if getattr(flags, name, False))


def _users(adt, ids):
    """{device id: [consumer node names]} from clock-gates/power-gates. Best effort."""
    users = {dev_id: [] for dev_id in ids}
    try:
        for node in adt["/arm-io"]:
            name = str(getattr(node, "name", "")) or "?"
            for attr in ("clock_gates", "power_gates"):
                for value in getattr(node, attr, None) or ():
                    dev_id = int(value) & 0xFFFF
                    if dev_id in users and name not in users[dev_id]:
                        users[dev_id].append(name)
    except Exception:  # a consumer walk must never stop the probe
        return {dev_id: [] for dev_id in ids}
    return users


def load_model(adt):
    """Device records from the client's parsed ADT (m1n1.adt.load_adt result)."""
    path = adt._pmgr_path
    node = adt[path]
    raw_devices = list(node.devices)
    ids = [adt.pmgr_dev_get_id(dev) for dev in raw_devices]
    users = _users(adt, ids)
    devices = []
    for index, (dev, dev_id) in enumerate(zip(raw_devices, ids)):
        flags = _flag_set(dev.flags)
        address = None
        if "no_ps" not in flags:
            try:
                address = int(adt.pmgr_dev_get_addr(dev))
            except Exception:
                address = None  # shown as "no address"; never read
        parents = tuple(int(p) for p in adt.pmgr_dev_get_parents(dev) if p)
        devices.append(Device(index, str(dev.name), int(dev_id), parents, flags, address,
                              tuple(users.get(dev_id, ()))))
    dies = 1
    try:
        dies = max(1, int(getattr(adt["/arm-io"], "die_count")))
    except Exception:
        dies = 1
    return Model(tuple(devices), dies, str(path))


def model_to_json(model):
    return {"pmgr_path": model.pmgr_path, "dies": model.dies,
            "devices": [{"index": d.index, "name": d.name, "id": d.dev_id,
                         "parents": list(d.parents), "flags": sorted(d.flags),
                         "address": d.address, "users": list(d.users)}
                        for d in model.devices]}


def model_from_json(doc):
    """Inverse of model_to_json()/stage-1 JSON; strict about the shape."""
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise ProbeStop("stage-1 JSON has an unsupported schema")
    meta = doc.get("model")
    if not isinstance(meta, dict) or not isinstance(meta.get("devices"), list):
        raise ProbeStop("stage-1 JSON lacks the device list")
    devices = []
    for entry in meta["devices"]:
        try:
            address = entry["address"]
            if address is not None and not isinstance(address, int):
                raise TypeError
            devices.append(Device(int(entry["index"]), str(entry["name"]), int(entry["id"]),
                                  tuple(int(p) for p in entry["parents"]),
                                  frozenset(entry["flags"]), address,
                                  tuple(str(u) for u in entry.get("users", ()))))
        except (KeyError, TypeError, ValueError):
            raise ProbeStop("stage-1 JSON has a malformed device entry") from None
    states = {}
    for key, value in (doc.get("states") or {}).items():
        try:
            die, index = (int(x) for x in key.split(":"))
        except ValueError:
            raise ProbeStop("stage-1 JSON has a malformed state key") from None
        states[(die, index)] = (("ok", int(value["raw"])) if value.get("status") == "ok"
                                else ("trapped", str(value.get("error", "?"))))
    return Model(tuple(devices), int(meta.get("dies", 1)), str(meta.get("pmgr_path", "?"))), states


# --- reading --------------------------------------------------------------------------
def guarded_read32(proxy, address):
    """One register read; the proxy runs reads under its own exception guard."""
    value = proxy.read32(address)
    if proxy.get_exc_count():
        raise MmioFault("exception while reading a PMGR register")
    return value & 0xFFFFFFFF


def read_states(read32, model, dies=None):
    """{(die, index): ("ok", raw) | ("trapped", ExceptionClassName)} for PS registers."""
    states = {}
    for die in range(model.dies if dies is None else dies):
        for dev in model.devices:
            if dev.address is None:
                continue
            try:
                states[(die, dev.index)] = ("ok", read32(dev.address + DIE_OFFSET * die))
            except MmioFault as exc:
                # Only a register fault is a per-register result. A transport error
                # (dead link, timeout) propagates: looping over 188 reads at 15 s each
                # would only hide it.
                states[(die, dev.index)] = ("trapped", type(exc).__name__)
    return states


def by_id(model):
    return {dev.dev_id: dev for dev in model.devices}


def link_protected(model):
    """{device index: root name} for devices the proxy link needs (roots and ancestors)."""
    ids = by_id(model)
    protected = {}

    def add(dev, root):
        if dev.index in protected:
            return
        protected[dev.index] = root
        for parent_id in dev.parents:
            if parent_id in ids:
                add(ids[parent_id], root)

    for dev in model.devices:
        if any(re.fullmatch(pattern, dev.name, re.IGNORECASE) for pattern in LINK_ROOTS):
            add(dev, dev.name)
    return protected


def children_of(model):
    """{device id: [child devices]} from the parent links."""
    kids = collections.defaultdict(list)
    for dev in model.devices:
        for parent_id in dev.parents:
            kids[parent_id].append(dev)
    return kids


def _busy_children(dev, model, states, die, off_names, kids, visited):
    """Names of descendants that keep `dev` in use (fail closed on anything unreadable).

    A child with a PS register is busy while its ACTUAL state is not PWRGATE (or the
    register cannot be read). A virtual child has no register: it is busy when it is
    flagged critical or when one of ITS children is busy.
    """
    busy = []
    for child in kids.get(dev.dev_id, ()):
        if child.index in visited or child.name in off_names:
            continue
        visited.add(child.index)
        if child.address is None or "no_ps" in child.flags:
            if "critical" in child.flags:
                busy.append(child.name)
            else:
                busy.extend(_busy_children(child, model, states, die, off_names, kids, visited))
            continue
        entry = states.get((die, child.index))
        if entry is None or entry[0] != "ok" or decode_state(entry[1])["actual"] != PS_PWRGATE:
            busy.append(child.name)
    return busy


def cycle_refusal(model, states, die, dev, off_names=frozenset(), protected=None, kids=None):
    """(code, text) why `dev` may not be power-cycled right now, or None when it may.

    off_names are domains an earlier step of the same run has powered off (children
    named before their parent). Codes: virt, crit, sys, trap, off, auto, flags, link, kids.
    """
    protected = link_protected(model) if protected is None else protected
    kids = children_of(model) if kids is None else kids
    if "no_ps" in dev.flags or dev.address is None:
        return "virt", "virtual domain (no PS register)"
    if "critical" in dev.flags:
        return "crit", "always-on (critical flag)"
    for pattern, what in SYSTEM_ESSENTIAL:
        if re.fullmatch(pattern, dev.name, re.IGNORECASE):
            return "sys", "system-essential (%s)" % what
    entry = states.get((die, dev.index))
    if entry is None or entry[0] != "ok":
        return "trap", "register could not be read"
    st = decode_state(entry[1])
    if st["reset"] or st["dev_disable"]:
        return "flags", "reset or device-disable bit is set"
    if st["auto_enable"]:
        return "auto", "auto-enable is set (hardware-managed)"
    if dev.name in off_names:
        return "off", "already powered off by an earlier step of this run"
    if st["actual"] != PS_ACTIVE or st["target"] != PS_ACTIVE:
        return "off", "not fully on (actual %s, target %s)" % (state_name(st["actual"]),
                                                               state_name(st["target"]))
    if dev.index in protected:
        return "link", "needed by the proxy link (parent closure of %s)" % protected[dev.index]
    if not any(re.fullmatch(p, d.name, re.IGNORECASE) for d in model.devices
               for p in LINK_ROOTS):
        return "link", "no UART0/ATC USB device found in the ADT: link dependency unknown"
    busy = sorted(set(_busy_children(dev, model, states, die, off_names, kids, {dev.index})))
    if busy:
        return "kids", "children still powered: " + ", ".join(sorted(busy))
    return None


def eligibility(model, states, die=0):
    """{device index: refusal code or 'ok'} for the stage-1 table."""
    protected, kids = link_protected(model), children_of(model)
    result = {}
    for dev in model.devices:
        refusal = cycle_refusal(model, states, die, dev, protected=protected, kids=kids)
        result[dev.index] = "ok" if refusal is None else refusal[0]
    return result


# --- plan -----------------------------------------------------------------------------
Step = collections.namedtuple("Step", "device raw note")
Plan = collections.namedtuple("Plan", "steps refusals die")


def parse_names(text):
    names = [part.strip() for part in text.split(",")]
    if not names or any(not name for name in names):
        raise ProbeStop("domain list is empty or has an empty entry")
    return names


def plan_power_cycle(model, states, names, die=0, max_domains=MAX_DOMAINS):
    """Plan with every refusal; nothing is written. Order is the order given."""
    refusals, steps = [], []
    if die < 0 or die >= model.dies:
        return Plan((), [("--die", "die %d does not exist (die-count %d)" % (die, model.dies))],
                    die)
    if len(names) > max_domains:
        refusals.append(("--power-cycle", "%d domains named, at most %d per run"
                         % (len(names), max_domains)))
    protected, kids = link_protected(model), children_of(model)
    seen, off_names = set(), set()
    for name in names:
        key = name.lower()
        if key in seen:
            refusals.append((name, "named twice"))
            continue
        seen.add(key)
        matches = [d for d in model.devices if d.name.lower() == key]
        if not matches:
            refusals.append((name, "unknown domain"))
            continue
        if len(matches) > 1:
            refusals.append((name, "ambiguous: %d devices carry this name" % len(matches)))
            continue
        dev = matches[0]
        refusal = cycle_refusal(model, states, die, dev, frozenset(off_names), protected, kids)
        if refusal is not None:
            refusals.append((dev.name, refusal[1]))
            continue
        note = ""
        if "notify_pmp" in dev.flags:
            note = ("notify_pmp: macOS/Linux report this domain's state change to the PMP; "
                    "this probe does not (Hypothesis: that mismatch matters)")
        steps.append(Step(dev, states[(die, dev.index)][1], note))
        off_names.add(dev.name)    # powered off by this run before the next name is checked
    if refusals:
        steps = []
    return Plan(tuple(steps), refusals, die)


def show_plan(plan, out=say):
    for step in plan.steps:
        d = step.device
        out("PLAN %s (id %d, die %d) reg 0x%x raw 0x%08x: ACTIVE -> PWRGATE (restored in "
            "reverse order afterwards)"
            % (d.name, d.dev_id, plan.die, d.address + DIE_OFFSET * plan.die, step.raw))
        if step.note:
            out("  NOTE: " + step.note)
    for name, reason in plan.refusals:
        out("REFUSED %s: %s" % (name, reason))


# --- stage 1 output -------------------------------------------------------------------
def flag_text(flags):
    return "".join(code for name, code in FLAG_CODES.items() if name in flags) or "-"


def render_table(model, states, die=0, elig=None, show_virtual=False):
    """Plain table lines for one die; hex and names only.

    Virtual domains (no PS register) are listed only with show_virtual; they still
    appear in the PARENTS column and in the JSON.
    """
    ids = by_id(model)
    elig = eligibility(model, states, die) if elig is None else elig
    lines = ["%4s %-16s %5s %-8s %-8s %-6s %-5s %s"
             % ("#", "NAME", "ID", "ACTUAL", "TARGET", "FLAGS", "CYCLE", "PARENTS / ADDRESS")]
    for dev in model.devices:
        entry = states.get((die, dev.index))
        if "no_ps" in dev.flags and not show_virtual:
            continue
        if "no_ps" in dev.flags:
            actual = target = "virtual"
        elif entry is None:
            actual = target = "-"
        elif entry[0] != "ok":
            actual = target = "trapped"
        else:
            st = decode_state(entry[1])
            actual, target = state_name(st["actual"]), state_name(st["target"])
            if st["auto_enable"]:
                target += "+auto"
        parents = ",".join(ids[p].name if p in ids else "#%d" % p for p in dev.parents) or "-"
        where = "reg 0x%x" % (dev.address + DIE_OFFSET * die) if dev.address is not None else "-"
        lines.append("%4d %-16s %5d %-8s %-8s %-6s %-5s %s | %s"
                     % (dev.index, dev.name[:16], dev.dev_id, actual, target,
                        flag_text(dev.flags), elig.get(dev.index, "-"), parents, where))
    return lines


def summarize(model, states, die=0):
    counts = collections.Counter()
    for dev in model.devices:
        counts["devices"] += 1
        for name in ("critical", "no_ps", "notify_pmp", "on"):
            if name in dev.flags:
                counts[name] += 1
        entry = states.get((die, dev.index))
        if entry is None:
            continue
        if entry[0] != "ok":
            counts["trapped"] += 1
            continue
        st = decode_state(entry[1])
        counts["actual_" + state_name(st["actual"]).lower()] += 1
        if st["auto_enable"]:
            counts["auto_enable"] += 1
        if st["actual"] == PS_ACTIVE and "critical" not in dev.flags and "no_ps" not in dev.flags:
            counts["on_not_critical"] += 1
            if "notify_pmp" in dev.flags:
                counts["on_not_critical_notify_pmp"] += 1
    elig = eligibility(model, states, die)
    counts["cycle_ok"] = sum(1 for v in elig.values() if v == "ok")
    counts["link_protected"] = len(link_protected(model))
    return counts


def stage1_document(model, states, marker):
    return {
        "schema": SCHEMA,
        "tool": "pmgr_probe",
        "chip": "0x%x" % CHIP_T6050,
        "m1n1_marker": marker,
        "model": model_to_json(model),
        "states": {"%d:%d" % key: ({"status": "ok", "raw": value[1]} if value[0] == "ok"
                                   else {"status": "trapped", "error": value[1]})
                   for key, value in sorted(states.items())},
        "summary": {str(die): dict(summarize(model, states, die)) for die in range(model.dies)},
    }


def print_stage1(model, states, out=say, show_virtual=False):
    out("PMGR node %s: %d devices, %d die(s)" % (model.pmgr_path, len(model.devices), model.dies))
    for die in range(model.dies):
        out("--- die %d ---%s" % (die, "" if show_virtual else " (virtual domains hidden; "
                                  "--show-virtual lists them)"))
        for line in render_table(model, states, die, show_virtual=show_virtual):
            out(line)
        counts = summarize(model, states, die)
        out("Summary die %d: %s" % (die, ", ".join("%s=%d" % kv for kv in sorted(counts.items()))))
    protected = link_protected(model)
    out("Link-protected (never cycled; parent closure of UART0 and the ATC USB devices): %s"
        % (", ".join(sorted(d.name for d in model.devices if d.index in protected)) or "NONE FOUND"))
    out("FLAGS: C critical (always-on) V virtual (no PS register) N notify_pmp O boot-on flag "
        "P perf")
    out("CYCLE: ok = stage 2 would accept; crit sys virt trap off auto flags link kids = "
        "refusal reason")
    out("Stage 1 finished: read only, no write request was sent.")


# --- stage 2: execution ---------------------------------------------------------------
class Io:
    """The few proxy operations stage 2 uses, so tests can inject a fake."""

    def __init__(self, proxy, sleep=time.sleep, clock=time.monotonic):
        self.proxy, self.sleep, self.clock = proxy, sleep, clock

    def read32(self, address):
        return guarded_read32(self.proxy, address)

    def mask32(self, address, clear, setbits):
        self.proxy.mask32(address, clear, setbits)
        if self.proxy.get_exc_count():
            raise MmioFault("exception while writing a PMGR register")

    def nop(self):
        self.proxy.nop()


def _wait_actual(io, address, want, timeout):
    """Poll the PS register until ACTUAL == want. (reached, elapsed seconds, last raw)."""
    start, raw = io.clock(), 0
    while True:
        raw = io.read32(address)
        elapsed = io.clock() - start
        if (raw & PS_ACTUAL) >> 4 == want:
            return True, elapsed, raw
        if elapsed >= timeout:
            return False, elapsed, raw
        io.sleep(0.02)


def _link_alive(io):
    try:
        io.nop()
    except TimeoutError:
        raise
    except Exception:
        return False
    return True


def _watch(io, seconds):
    """Keep the link under a NOP every LINK_POLL_INTERVAL for `seconds`.

    Returns (alive, elapsed seconds). A dead link ends the watch at once.
    """
    start = io.clock()
    while True:
        elapsed = io.clock() - start
        if elapsed >= seconds:
            return True, elapsed
        io.sleep(LINK_POLL_INTERVAL)
        if not _link_alive(io):
            return False, io.clock() - start


def _restore(io, step, plan, out):
    """Power one domain back on and verify. (restored, elapsed, raw)."""
    dev = step.device
    address = dev.address + DIE_OFFSET * plan.die
    out("POWER-ON %s (id %d): target %s" % (dev.name, dev.dev_id, state_name(PS_ACTIVE)))
    io.mask32(address, SET_MODE_CLEAR, PS_ACTIVE)
    return _wait_actual(io, address, PS_ACTIVE, STATE_POLL_TIMEOUT)


def power_cycle(io, plan, settle, tail, out=say):
    """Execute a plan. Returns EXIT_OK, or the exit code of the failure after printing why.

    Domains are powered off in the order given (children first, which the plan has
    already validated), each followed by its own settle with the link checked, so a loss
    is attributed to the domain that was powered off last. Then they are powered back
    on in the REVERSE order (parents first). Every write is announced and flushed BEFORE
    it is sent, so a lost link or a reset leaves the domain's name as the last line.
    """
    off = []                    # steps whose power-off request has been sent, in order
    restored = set()            # device indexes whose restore was verified
    try:
        for step in plan.steps:
            dev = step.device
            address = dev.address + DIE_OFFSET * plan.die
            out("POWER-OFF %s (id %d, die %d) reg 0x%x raw 0x%08x: target %s -> %s%s"
                % (dev.name, dev.dev_id, plan.die, address, step.raw, state_name(PS_ACTIVE),
                   state_name(PS_PWRGATE),
                   "" if not off else " (already off: %s)" % ", ".join(s.device.name
                                                                       for s in off)))
            off.append(step)    # before the write: an interrupted request is also restored
            io.mask32(address, SET_MODE_CLEAR, PS_PWRGATE)
            reached, elapsed, raw = _wait_actual(io, address, PS_PWRGATE, STATE_POLL_TIMEOUT)
            if not reached:
                out("  actual did not reach PWRGATE within %.1f s (raw 0x%08x); restoring "
                    "everything this run powered off" % (STATE_POLL_TIMEOUT, raw))
                code = EXIT_STOP
                break
            out("  actual PWRGATE after %.3f s; settling %.1f s with the link checked every "
                "%.1f s" % (elapsed, settle, LINK_POLL_INTERVAL))
            alive, waited = _watch(io, settle)
            if not alive:
                out("LINK LOST %.1f s after powering off %s (id %d; already off: %s). The SoC "
                    "may have reset: look at the M5 (restarted, or frozen), power it off "
                    "completely, and report this line. Nothing was restored."
                    % (waited, dev.name, dev.dev_id,
                       ", ".join(s.device.name for s in off[:-1]) or "none"))
                return EXIT_LINK_LOST
        else:
            code = EXIT_OK
        failed = []
        for step in reversed(off):
            back, elapsed, raw = _restore(io, step, plan, out)
            if back:
                restored.add(step.device.index)
                out("  %s restored: actual ACTIVE after %.3f s (raw 0x%08x)"
                    % (step.device.name, elapsed, raw))
            else:
                out("NOT RESTORED: %s actual did not return to ACTIVE within %.1f s (raw "
                    "0x%08x). Power the Mac off completely and report this line."
                    % (step.device.name, STATE_POLL_TIMEOUT, raw))
                failed.append(step.device.name)
        if failed:
            return EXIT_NOT_RESTORED
        if code != EXIT_OK:
            out("STOP: %s never reached PWRGATE although the register accepted the write; "
                "everything was restored." % off[-1].device.name)
            return code
    except BaseException:
        # An interrupt or a transport error with something powered off: one best-effort
        # restore request each (reverse order), and the outcome is stated either way.
        todo = [s for s in reversed(off) if s.device.index not in restored]
        pending = []
        for step in todo:
            address = step.device.address + DIE_OFFSET * plan.die
            try:
                io.mask32(address, SET_MODE_CLEAR, PS_ACTIVE)
            except BaseException:
                pending.append(step.device.name)
        if todo and not pending:
            out("Interrupted with %s powered off: restore requests sent (not verified); power "
                "the Mac off completely before the next run." % ", ".join(
                    s.device.name for s in todo))
        elif pending:
            out("NOT RESTORED: %s may still be powered off; power the Mac off completely."
                % ", ".join(pending))
        raise
    if tail > 0:
        out("Watching the link for %.1f s after the last restore (attempt 14's reset came about "
            "5.6 s after the power-off)." % tail)
        alive, waited = _watch(io, tail)
        if not alive:
            out("LINK LOST %.1f s after the last restore (%s). The SoC may have reset: look at "
                "the M5, power it off completely, and report this line."
                % (waited, ", ".join(s.device.name for s in off) or "none"))
            return EXIT_LINK_LOST
    out("PROBE PASS: %d domain(s) powered off in order and restored in reverse, link alive "
        "through every settle and a %.1f s tail: %s"
        % (len(off), tail, ", ".join(s.device.name for s in off) or "none"))
    return EXIT_OK


# --- connection -----------------------------------------------------------------------
def open_primary(device, UartInterface, Serial):
    """Descriptor-verified primary callout: (transport, interface). No console echo.

    Errors carry the exception class only; a callout path embeds the device serial.
    """
    try:
        selected = usb_identity.select_primary(usb_identity.discover(), device)
    except TimeoutError:
        raise
    except Exception as exc:
        raise ProbeStop("USB identity check failed (%s); no port opened" % type(exc).__name__) \
            from None
    transport = None
    try:
        transport = Serial(selected, UartInterface.DEFAULT_BAUD_RATE)
        iface = UartInterface(device=transport)
        iface.tty_enable = False
        iface.dev.timeout = 15
    except BaseException as exc:
        if transport is not None:
            with contextlib.suppress(Exception):
                transport.close()
        if isinstance(exc, Exception) and not isinstance(exc, TimeoutError):
            raise ProbeStop("USB transport failed (%s); do not automatically retry"
                            % type(exc).__name__) from None
        raise
    return transport, iface


def check_target(iface, proxy, marker, offset):
    """The same gates as native/boot/launch.py: chip, installed boot021, no secondaries."""
    proxy.nop()
    if proxy.get_chipid() != CHIP_T6050:
        raise ProbeStop("target chip is not t6050")
    want = marker.encode("ascii") + b"\0"
    if iface.readmem(proxy.get_base() + offset, len(want)) != want:
        raise ProbeStop("target m1n1 does not match " + marker)
    try:
        launch.ensure_no_secondaries(proxy)
    except ValueError as exc:
        raise ProbeStop(str(exc)) from None


def fetch_model(iface, proxy, load_adt, bootargs_types):
    """The raw ADT from the target, parsed. Reads only (no ProxyUtils, no heap request)."""
    ba_addr, rev = proxy.get_bootargs_rev()
    ba_type = bootargs_types.get(rev)
    if ba_type is None:
        raise ProbeStop("unsupported boot_args revision %d" % rev)
    ba = iface.readstruct(ba_addr, ba_type)
    if not 0 < ba.devtree_size <= 64 * 1024 * 1024:
        raise ProbeStop("ADT size 0x%x is implausible" % ba.devtree_size)
    adt_addr = (ba.devtree - ba.virt_base + ba.phys_base) & 0xFFFFFFFFFFFFFFFF
    data = iface.readmem(adt_addr, ba.devtree_size)
    return load_model(load_adt(data))


def live_session(api, device, mode, names=None, die=0, settle=SETTLE_DEFAULT,
                 tail=TAIL_DEFAULT, json_path=None, show_virtual=False, out=say):
    """read / plan / cycle against the target. Returns an exit code."""
    boot_m = json.loads((BOOT / "package-manifest.json").read_text())
    marker, offset = boot_m["m1n1_version_marker"], boot_m["m1n1_version_offset"]
    transport = None

    def alarm(*_):
        raise TimeoutError("probe exceeded its time budget; do not automatically retry")

    budget = 120 if mode != "cycle" else int(120 + len(names or ()) * (settle + 20) + tail)
    old = signal.signal(signal.SIGALRM, alarm)
    signal.alarm(budget)
    try:
        transport, iface = api.open_primary(device)
        proxy = api.M1N1Proxy(iface)
        check_target(iface, proxy, marker, offset)
        out("Target PASS: t6050, installed boot021, no started secondaries.")
        model = fetch_model(iface, proxy, api.load_adt, api.bootargs_types)
        states = read_states(lambda a: guarded_read32(proxy, a), model)
        if mode == "read":
            print_stage1(model, states, out, show_virtual)
            if json_path is not None:
                write_json(json_path, stage1_document(model, states, marker))
                out("Wrote %s" % json_path.name)
            return EXIT_OK
        plan = plan_power_cycle(model, states, names, die)
        show_plan(plan, out)
        if plan.refusals:
            out("PLAN REFUSED: nothing was written.")
            return EXIT_REFUSED
        if mode == "plan":
            out("PLAN OK: stage 2 would accept every named domain (nothing was written).")
            return EXIT_OK
        io = Io(proxy, api.sleep, api.clock)
        out("Power-cycling %d domain(s); settle %.1f s each, tail %.1f s. Film the M5 and note "
            "the time of the last line you see." % (len(plan.steps), settle, tail))
        return power_cycle(io, plan, settle, tail, out)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)
        if transport is not None:
            with contextlib.suppress(Exception):
                transport.close()


def write_json(path, document):
    with path.open("x") as handle:
        json.dump(document, handle, indent=1, sort_keys=True)
        handle.write("\n")


def connect_and_run(m1n1, device, mode, **options):
    pin = subprocess.check_output(["git", "-C", str(m1n1), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(m1n1), "status", "--porcelain",
                                     "--untracked-files=no"], text=True)
    if pin != launch.M1N1_COMMIT or dirty:
        raise ProbeStop("client must be the clean pinned m1n1 checkout")
    sys.path.insert(0, str(m1n1 / "proxyclient"))
    from m1n1.adt import load_adt
    from m1n1.proxy import M1N1Proxy, UartInterface, Serial
    from m1n1.tgtypes import BootArgs_r1, BootArgs_r2, BootArgs_r3
    # A class body resolves a name it also assigns in class, global and builtin scope
    # only, never in the enclosing function, so alias the local imports first.
    proxy_cls, adt_loader = M1N1Proxy, load_adt

    class Api:
        M1N1Proxy = staticmethod(proxy_cls)
        load_adt = staticmethod(adt_loader)
        bootargs_types = {0: BootArgs_r1, 1: BootArgs_r1, 2: BootArgs_r2, 3: BootArgs_r3}
        sleep = staticmethod(time.sleep)
        clock = staticmethod(time.monotonic)

        @staticmethod
        def open_primary(dev):
            return open_primary(dev, UartInterface, Serial)

    return live_session(Api, device, mode, **options)


# --- command line ---------------------------------------------------------------------
def _output_path(text):
    """A new file in an existing, writable directory (checked before any USB access)."""
    path = Path(text)
    if os.path.lexists(path):
        raise argparse.ArgumentTypeError("file exists; choose a new name")
    parent = path.parent if str(path.parent) else Path(".")
    if not parent.is_dir() or not os.access(parent, os.W_OK):
        raise argparse.ArgumentTypeError("directory does not exist or is not writable")
    return path


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)

    def live_args(p, confirm):
        p.add_argument("--device", help="auto, or the exact descriptor-verified primary callout")
        p.add_argument("--confirm", default="", help="LIVE: must equal " + confirm)
        p.add_argument("--m1n1", type=Path, default=ROOT / "third_party" / "m1n1")

    read = sub.add_parser("read", help="stage 1: read-only table of every PMGR domain")
    live_args(read, CONFIRM_READ)
    read.add_argument("--json", type=_output_path, help="also write a new JSON file")
    read.add_argument("--show-virtual", action="store_true",
                      help="also list virtual domains (no PS register); the JSON always has them")

    plan = sub.add_parser("plan", help="show what stage 2 would do or refuse; writes nothing")
    plan.add_argument("domains", help="comma-separated domain names (ADT names)")
    plan.add_argument("--from-json", type=Path, help="offline: a stage-1 JSON file")
    plan.add_argument("--die", type=int, default=0)
    live_args(plan, CONFIRM_READ)

    cycle = sub.add_parser("cycle", help="stage 2: power-cycle the named domains (WRITES)")
    cycle.add_argument("domains", help="comma-separated domain names (ADT names), at most %d"
                       % MAX_DOMAINS)
    cycle.add_argument("--die", type=int, default=0)
    cycle.add_argument("--settle", type=float, default=SETTLE_DEFAULT,
                       help="seconds each domain stays off (%g..%g, default %g)"
                       % (SETTLE_MIN, SETTLE_MAX, SETTLE_DEFAULT))
    cycle.add_argument("--tail", type=float, default=TAIL_DEFAULT,
                       help="seconds to keep watching the link after the last restore "
                       "(0..%g, default %g)" % (TAIL_MAX, TAIL_DEFAULT))
    live_args(cycle, CONFIRM_CYCLE)
    return parser


def main(argv=None, runner=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    runner = runner or connect_and_run
    if args.mode == "plan" and args.from_json is not None:
        if args.device is not None or args.confirm:
            parser.error("--from-json is offline; it does not accept --device or --confirm")
        model, states = model_from_json(json.loads(args.from_json.read_text()))
        plan = plan_power_cycle(model, states, parse_names(args.domains), args.die)
        show_plan(plan)
        if plan.refusals:
            say("PLAN REFUSED: nothing was written.")
            return EXIT_REFUSED
        say("PLAN OK (offline, from the stage-1 file): nothing was written.")
        return EXIT_OK
    needed = CONFIRM_CYCLE if args.mode == "cycle" else CONFIRM_READ
    if args.device is None or args.confirm != needed:
        parser.error("live use requires --device and --confirm " + needed)
    if args.mode == "cycle":
        if not SETTLE_MIN <= args.settle <= SETTLE_MAX:
            parser.error("--settle must be between %g and %g seconds" % (SETTLE_MIN, SETTLE_MAX))
        if not 0 <= args.tail <= TAIL_MAX:
            parser.error("--tail must be between 0 and %g seconds" % TAIL_MAX)
    options = {}
    if args.mode in ("plan", "cycle"):
        options.update(names=parse_names(args.domains), die=args.die)
    if args.mode == "cycle":
        options.update(settle=args.settle, tail=args.tail)
    if args.mode == "read":
        options.update(json_path=args.json, show_virtual=args.show_virtual)
    return runner(args.m1n1, args.device, args.mode, **options)


def stop_line(exc):
    return "STOP: %s %s" % (type(exc).__name__, scrub(exc))


def cli(argv=None):
    """main() as a process: no traceback and no exception chain is ever printed."""
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
        print(stop_line(exc), file=sys.stderr)
        return EXIT_STOP


if __name__ == "__main__":
    sys.exit(cli())
