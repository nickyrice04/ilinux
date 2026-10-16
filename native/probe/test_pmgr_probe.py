"""Offline tests for pmgr_probe.py (private iLinux tooling). No target, no m1n1 client.

A fake ADT (the attributes the m1n1 client's parsed ADT offers) and a fake proxy
(registers, a PS state machine, a link that can die) drive the real module. The
mutation class at the bottom applies textual mutants of pmgr_probe.py and requires
the rest of this file to notice.

Run with python3 -I native/probe/test_pmgr_probe.py
"""
import contextlib
import io
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import types
from types import SimpleNamespace
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
import pmgr_probe  # noqa: E402

P = pmgr_probe          # the module under test; the mutation class swaps it
SOURCE = (HERE / "pmgr_probe.py").read_text()
ROOT = HERE.parents[1]
BOOT_MANIFEST = json.loads((ROOT / "native/boot/package-manifest.json").read_text())
MARKER = BOOT_MANIFEST["m1n1_version_marker"]
MARKER_OFFSET = BOOT_MANIFEST["m1n1_version_offset"]
BASE = 0x2_8000_0000
ON = 0xFF               # ACTUAL 0xf, TARGET 0xf
OFF = 0x00
FLAG_NAMES = ("b7", "b6", "perf", "no_ps", "critical", "b2", "notify_pmp", "on")


# --- fakes ----------------------------------------------------------------------------
def flags(*names):
    return SimpleNamespace(**{n: n in names for n in FLAG_NAMES})


class FakeDevice:
    def __init__(self, name, dev_id, parents=(), flag_names=(), slot=None):
        self.name, self.id = name, dev_id
        self.parents = (list(parents) + [0, 0])[:2]
        self.flags = flags(*flag_names)
        self.slot = slot


class FakeNode:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __iter__(self):
        return iter(self.children)


class FakeADT:
    _pmgr_path = "/arm-io/pmgr"

    def __init__(self, devices, consumers=(), die_count=1):
        self.devices, self.consumers, self.die_count = list(devices), list(consumers), die_count

    def __getitem__(self, path):
        if path == "/arm-io/pmgr":
            return FakeNode(devices=self.devices)
        if path == "/arm-io":
            return FakeNode(children=self.consumers, die_count=self.die_count)
        raise KeyError(path)

    def pmgr_dev_get_id(self, dev):
        return dev.id

    def pmgr_dev_get_parents(self, dev):
        return dev.parents

    def pmgr_dev_get_addr(self, dev):
        if dev.slot is None:
            raise KeyError("no register")
        return BASE + 8 * dev.slot


def standard_devices():
    """A small tree shaped like the real one: link roots, a GPU with a child, odd ones."""
    return [
        FakeDevice("SOC_TOP", 1, (), ("critical", "on"), 0),
        FakeDevice("FAB", 2, (1,), ("on",), 1),
        FakeDevice("UART0", 3, (2,), ("on",), 2),
        FakeDevice("ATC0_USB", 4, (2,), ("on",), 3),
        FakeDevice("ATC0_USB_AON", 5, (1,), ("on",), 4),
        FakeDevice("SIO", 6, (2,), ("on",), 5),
        FakeDevice("GPU", 7, (2,), ("on",), 6),
        FakeDevice("GPU_SHADER", 8, (7,), ("on",), 7),
        FakeDevice("ISP", 9, (2,), ("on", "notify_pmp"), 8),
        FakeDevice("VIRT_GRP", 10, (2,), ("no_ps",), None),
        FakeDevice("ANS", 11, (2,), ("on",), 9),
        FakeDevice("AUTO_DOM", 12, (2,), ("on",), 10),
        FakeDevice("OFF_DOM", 13, (2,), (), 11),
        FakeDevice("PINNED_VIRT", 14, (11,), ("no_ps", "critical"), None),
        FakeDevice("LEAF", 15, (2,), ("on",), 12),
        FakeDevice("TWIN", 16, (2,), ("on",), 13),
        FakeDevice("twin", 17, (2,), ("on",), 14),
    ]


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def sleep(self, seconds):
        self.now += seconds

    def monotonic(self):
        return self.now


class FakeProxy:
    """Registers with a PS state machine, the proxy calls the probe uses, a dying link."""

    def __init__(self, devices, log=None):
        self.regs = {}
        for dev in devices:
            if dev.slot is not None:
                self.regs[BASE + 8 * dev.slot] = ON
        self.regs[BASE + 8 * 10] = ON | (1 << 28)      # AUTO_DOM: auto-enable set
        self.regs[BASE + 8 * 11] = OFF                 # OFF_DOM: powered off
        self.log = log if log is not None else []
        self.writes = []
        self.chip, self.alive_cpus = 0x6050, set()
        self.dead = False
        self.exc, self.exc_addrs = 0, set()
        self.stuck_off, self.no_return = set(), set()
        self.die_after_off = {}        # address -> nops survived after its power-off write
        self.nops = 0
        self.nop_budget = None
        self.pending = {}

    # --- link ---
    def nop(self):
        if self.dead:
            raise ConnectionError("link lost")
        self.nops += 1
        if self.nop_budget is not None:
            self.nop_budget -= 1
            if self.nop_budget < 0:
                self.dead = True
                raise ConnectionError("link lost")

    def get_chipid(self):
        return self.chip

    def get_base(self):
        return BASE

    def smp_is_alive(self, cpu):
        return cpu in self.alive_cpus

    def get_bootargs_rev(self):
        return 0x4000, 3

    # --- registers ---
    def read32(self, address):
        if self.dead:
            raise ConnectionError("link lost")
        if address in self.exc_addrs:
            self.exc = 1
            return 0
        if address in self.pending:
            target, left = self.pending[address]
            if left <= 0:
                self.regs[address] = (self.regs[address] & ~0xF0) | (target << 4)
                del self.pending[address]
            else:
                self.pending[address] = (target, left - 1)
        return self.regs[address]

    def get_exc_count(self):
        value, self.exc = self.exc, 0
        return value

    def mask32(self, address, clear, setbits):
        if self.dead:
            raise ConnectionError("link lost")
        self.log.append(("write", address, clear, setbits))
        self.writes.append((address, clear, setbits))
        value = (self.regs[address] & ~clear) | setbits
        self.regs[address] = value
        target = value & 0xF
        if target == 0 and address in self.stuck_off:
            return value
        if target == 0xF and address in self.no_return:
            return value
        self.pending[address] = (target, 1)
        if target == 0 and address in self.die_after_off:
            self.nop_budget = self.die_after_off[address]
        return value


class FakeIface:
    def __init__(self, marker=MARKER):
        self.marker = marker
        self.tty_enable = True
        self.dev = SimpleNamespace(timeout=None)

    def readmem(self, address, size):
        if address == BASE + MARKER_OFFSET:
            return (self.marker.encode("ascii") + b"\0")[:size]
        return b"\0" * size

    def readstruct(self, address, kind):
        return SimpleNamespace(devtree=0x9000, virt_base=0x8000, phys_base=0x1000,
                               devtree_size=0x1234, kind=kind)


class FakeTransport:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def make_api(proxy, iface, adt, clock=None):
    clock = clock or FakeClock()
    transport = FakeTransport()
    return SimpleNamespace(
        open_primary=lambda device: (transport, iface),
        M1N1Proxy=lambda i: proxy,
        load_adt=lambda data: adt,
        bootargs_types={0: "r1", 1: "r1", 2: "r2", 3: "r3"},
        sleep=clock.sleep, clock=clock.monotonic, transport=transport, clk=clock)


class Lines(list):
    """An out() that also stamps the proxy's event log, so print-before-write is checkable."""

    def __init__(self, log=None):
        super().__init__()
        self.log = log

    def __call__(self, text):
        self.append(text)
        if self.log is not None:
            self.log.append(("out", text))


def standard_world(**kw):
    devices = standard_devices()
    adt = FakeADT(devices, consumers=[SimpleNamespace(name="uart0", clock_gates=[3],
                                                       power_gates=[]),
                                      SimpleNamespace(name="gpu", clock_gates=[7, 8],
                                                      power_gates=[7])],
                  die_count=kw.get("dies", 1))
    proxy = FakeProxy(devices)
    return devices, adt, proxy


def load(adt, proxy):
    model = P.load_model(adt)
    states = P.read_states(lambda a: P.guarded_read32(proxy, a), model)
    return model, states


def run_live(mode, **options):
    devices, adt, proxy = standard_world()
    return run_live_with(proxy, adt, mode, **options)


def run_live_with(proxy, adt, mode, iface=None, **options):
    proxy.log = []
    lines = Lines(proxy.log)
    api = make_api(proxy, iface or FakeIface(), adt)
    code = P.live_session(api, "auto", mode, out=lines, **options)
    return code, lines, proxy, api


# --- decoding and the model -----------------------------------------------------------
class DecodeTests(unittest.TestCase):
    def test_fields_match_m1n1_layout(self):
        st = P.decode_state(0x1000_0000 | (0x3 << 24) | (1 << 11) | (1 << 10) | (1 << 9) |
                            (1 << 8) | (0x4 << 4) | 0xF | (1 << 31))
        self.assertEqual((st["actual"], st["target"]), (0x4, 0xF))
        self.assertTrue(st["auto_enable"] and st["reset"] and st["dev_disable"])
        self.assertTrue(st["parent_off"] and st["was_clkgated"] and st["was_pwrgated"])
        self.assertEqual(st["ps_auto"], 3)

    def test_state_names(self):
        self.assertEqual([P.state_name(v) for v in (0xF, 0x4, 0x0, 0x7)],
                         ["ACTIVE", "CLKGATE", "PWRGATE", "0x7"])

    def test_constants_equal_pinned_m1n1_pmgr(self):
        self.assertEqual((P.PS_ACTIVE, P.PS_CLKGATE, P.PS_PWRGATE), (0xF, 0x4, 0x0))
        self.assertEqual(P.DIE_OFFSET, 0x2000000000)
        self.assertEqual(P.SET_MODE_CLEAR, (1 << 28) | (1 << 9) | (1 << 8) | 0xF)


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.devices, self.adt, self.proxy = standard_world()

    def test_devices_ids_parents_flags_addresses_users(self):
        model = P.load_model(self.adt)
        self.assertEqual(len(model.devices), 17)
        gpu = next(d for d in model.devices if d.name == "GPU")
        self.assertEqual((gpu.dev_id, gpu.parents), (7, (2,)))
        self.assertEqual(gpu.address, BASE + 8 * 6)
        self.assertEqual(gpu.users, ("gpu",))
        self.assertIn("notify_pmp", next(d for d in model.devices if d.name == "ISP").flags)
        virt = next(d for d in model.devices if d.name == "VIRT_GRP")
        self.assertIsNone(virt.address)
        self.assertEqual(model.pmgr_path, "/arm-io/pmgr")
        self.assertEqual(model.dies, 1)

    def test_die_count(self):
        self.assertEqual(P.load_model(FakeADT(self.devices, die_count=2)).dies, 2)

    def test_broken_consumer_walk_does_not_stop_the_model(self):
        adt = FakeADT(self.devices, consumers=[SimpleNamespace(name="x", clock_gates=5)])
        self.assertEqual(P.load_model(adt).devices[0].users, ())

    def test_link_protected_is_the_parent_closure_of_uart_and_atc(self):
        model = P.load_model(self.adt)
        names = {d.name for d in model.devices if d.index in P.link_protected(model)}
        self.assertEqual(names, {"UART0", "ATC0_USB", "ATC0_USB_AON", "FAB", "SOC_TOP"})


# --- stage 1 --------------------------------------------------------------------------
class ReadTests(unittest.TestCase):
    def test_stage_one_sends_no_write_request_of_any_kind(self):
        code, lines, proxy, _ = run_live("read")
        self.assertEqual(code, P.EXIT_OK)
        self.assertEqual(proxy.writes, [])
        self.assertTrue(any("read only, no write request was sent" in l for l in lines))

    def test_table_lists_every_device_with_state_flags_and_cycle_code(self):
        code, lines, proxy, _ = run_live("read")
        text = "\n".join(lines)
        for name in ("SOC_TOP", "UART0", "GPU_SHADER", "ISP", "OFF_DOM"):
            self.assertIn(name, text)
        row = {l.split()[1]: l for l in lines if l[:4].strip().isdigit()}
        self.assertNotIn("VIRT_GRP", row)               # virtual rows are opt-in
        self.assertNotIn("PINNED_VIRT", row)
        self.assertIn("ACTIVE", row["ANS"])
        self.assertIn("PWRGATE", row["OFF_DOM"])
        self.assertIn("+auto", row["AUTO_DOM"])
        # CYCLE column
        cycle = {name: r.split()[6] for name, r in row.items()}      # # NAME ID ACT TGT FLAGS CYCLE
        self.assertEqual(cycle["SOC_TOP"], "crit")
        self.assertEqual(cycle["UART0"], "link")
        self.assertEqual(cycle["OFF_DOM"], "off")
        self.assertEqual(cycle["AUTO_DOM"], "auto")
        self.assertEqual(cycle["GPU"], "kids")
        self.assertEqual(cycle["ISP"], "ok")

    def test_show_virtual_lists_the_register_less_domains(self):
        devices, adt, proxy = standard_world()
        code, lines, _, _ = run_live_with(proxy, adt, "read", show_virtual=True)
        row = {l.split()[1]: l for l in lines if l[:4].strip().isdigit()}
        self.assertIn("virtual", row["VIRT_GRP"])
        self.assertEqual(row["VIRT_GRP"].split()[6], "virt")
        self.assertIn("PINNED_VIRT", row)

    def test_summary_counts(self):
        code, lines, proxy, _ = run_live("read")
        summary = next(l for l in lines if l.startswith("Summary die 0:"))
        for item in ("devices=17", "critical=2", "notify_pmp=1", "no_ps=2", "auto_enable=1"):
            self.assertIn(item, summary)
        self.assertIn("link_protected=5", summary)

    def test_trapped_read_is_a_row_not_a_failure(self):
        devices, adt, proxy = standard_world()
        proxy.exc_addrs.add(BASE + 8 * 9)            # ANS
        code, lines, _, _ = run_live_with(proxy, adt, "read")
        self.assertEqual(code, P.EXIT_OK)
        row = next(l for l in lines if l.split()[1:2] == ["ANS"])
        self.assertIn("trapped", row)

    def test_a_transport_error_stops_the_read_instead_of_looping(self):
        devices, adt, proxy = standard_world()
        calls = []
        real = proxy.read32

        def dying(address):
            calls.append(address)
            if len(calls) == 3:
                raise ConnectionError("link lost")
            return real(address)
        proxy.read32 = dying
        with self.assertRaises(ConnectionError):
            run_live_with(proxy, adt, "read")
        self.assertEqual(len(calls), 3)

    def test_second_die_uses_the_die_offset(self):
        devices = standard_devices()
        adt = FakeADT(devices, die_count=2)
        proxy = FakeProxy(devices)
        for dev in devices:
            if dev.slot is not None:
                proxy.regs[BASE + 8 * dev.slot + P.DIE_OFFSET] = ON
        model = P.load_model(adt)
        seen = []
        states = P.read_states(lambda a: seen.append(a) or ON, model)
        self.assertEqual(len(states), 2 * 15)
        self.assertIn(BASE + P.DIE_OFFSET, seen)
        self.assertIn((1, 0), states)

    def test_json_document_round_trips_to_the_same_plan(self):
        devices, adt, proxy = standard_world()
        model, states = load(adt, proxy)
        doc = json.loads(json.dumps(P.stage1_document(model, states, MARKER)))
        self.assertEqual(doc["schema"], P.SCHEMA)
        self.assertEqual(doc["m1n1_marker"], MARKER)
        model2, states2 = P.model_from_json(doc)
        self.assertEqual(model2, model)
        self.assertEqual(states2, states)
        for names in (["ISP"], ["GPU"], ["GPU_SHADER", "GPU"], ["CRIT"]):
            a = P.plan_power_cycle(model, states, names)
            b = P.plan_power_cycle(model2, states2, names)
            self.assertEqual([s.device.name for s in a.steps], [s.device.name for s in b.steps])
            self.assertEqual(a.refusals, b.refusals)

    def test_json_contains_no_device_path_or_serial_like_text(self):
        devices, adt, proxy = standard_world()
        model, states = load(adt, proxy)
        text = json.dumps(P.stage1_document(model, states, MARKER))
        self.assertNotIn("/dev/", text)
        self.assertNotIn("usbmodem", text)

    def test_malformed_json_is_a_stop(self):
        for bad in ({}, {"schema": 2}, {"schema": 1, "model": {"devices": [{"index": 1}]}},
                    {"schema": 1, "model": {"devices": []}, "states": {"x": {}}}):
            with self.assertRaises(P.ProbeStop):
                P.model_from_json(bad)

    def test_json_file_is_written_exclusively(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "out.json"
            code, lines, _, _ = run_live("read", json_path=path)
            self.assertEqual(code, P.EXIT_OK)
            self.assertEqual(json.loads(path.read_text())["schema"], P.SCHEMA)
            with self.assertRaises(FileExistsError):
                P.write_json(path, {})



def fake_m1n1_modules():
    """sys.modules entries that satisfy connect_and_run's imports without the client venv."""
    m1n1 = types.ModuleType("m1n1")
    adt = types.ModuleType("m1n1.adt")
    adt.load_adt = lambda blob: None
    proxy = types.ModuleType("m1n1.proxy")
    proxy.M1N1Proxy = lambda iface: None
    proxy.UartInterface = proxy.Serial = object
    tgtypes = types.ModuleType("m1n1.tgtypes")
    tgtypes.BootArgs_r1 = tgtypes.BootArgs_r2 = tgtypes.BootArgs_r3 = object
    return {"m1n1": m1n1, "m1n1.adt": adt, "m1n1.proxy": proxy, "m1n1.tgtypes": tgtypes}

# --- gates ----------------------------------------------------------------------------
class GateTests(unittest.TestCase):
    def test_wrong_chip_stops_before_any_register_read(self):
        devices, adt, proxy = standard_world()
        proxy.chip = 0x8103
        reads = []
        real = proxy.read32
        proxy.read32 = lambda a: reads.append(a) or real(a)
        with self.assertRaises(P.ProbeStop) as cm:
            run_live_with(proxy, adt, "read")
        self.assertIn("not t6050", str(cm.exception))
        self.assertEqual(reads, [])

    def test_wrong_marker_stops(self):
        devices, adt, proxy = standard_world()
        with self.assertRaises(P.ProbeStop):
            run_live_with(proxy, adt, "read", iface=FakeIface(marker="m1n1-something-else"))

    def test_started_secondary_stops(self):
        devices, adt, proxy = standard_world()
        proxy.alive_cpus.add(3)
        with self.assertRaises(P.ProbeStop):
            run_live_with(proxy, adt, "read")

    def test_gates_run_for_cycle_too_and_nothing_is_written(self):
        devices, adt, proxy = standard_world()
        proxy.chip = 0x6000
        with self.assertRaises(P.ProbeStop):
            run_live_with(proxy, adt, "cycle", names=["ISP"], settle=1.0, tail=0)
        self.assertEqual(proxy.writes, [])

    def test_implausible_adt_size_stops(self):
        devices, adt, proxy = standard_world()
        iface = FakeIface()
        iface.readstruct = lambda a, k: SimpleNamespace(devtree=0x9000, virt_base=0x8000,
                                                         phys_base=0x1000, devtree_size=0)
        with self.assertRaises(P.ProbeStop):
            run_live_with(proxy, adt, "read", iface=iface)

    def test_unsupported_boot_args_revision_stops(self):
        devices, adt, proxy = standard_world()
        proxy.get_bootargs_rev = lambda: (0x4000, 9)
        with self.assertRaises(P.ProbeStop):
            run_live_with(proxy, adt, "read")

    def test_live_wiring_builds_its_api_and_reaches_open_primary(self):
        # E1 session 1 (2026-10-16) stopped with NameError while building the Api
        # class: the class body could not see the function-local m1n1 imports.
        class Reached(Exception):
            pass

        def open_primary(dev, uart, serial):
            raise Reached(dev)

        calls = iter([P.launch.M1N1_COMMIT + "\n", ""])
        saved = {name: sys.modules.get(name) for name in fake_m1n1_modules()}
        original = (P.subprocess.check_output, P.open_primary)
        P.subprocess.check_output = lambda *a, **k: next(calls)
        P.open_primary = open_primary
        sys.modules.update(fake_m1n1_modules())
        try:
            with self.assertRaises(Reached):
                P.connect_and_run(Path("/nonexistent"), "auto", "read")
        finally:
            P.subprocess.check_output, P.open_primary = original
            for name, module in saved.items():
                if module is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = module

    def test_pin_check_refuses_an_unpinned_or_dirty_client(self):
        calls = iter(["deadbeef\n", ""])
        original = P.subprocess.check_output
        P.subprocess.check_output = lambda *a, **k: next(calls)
        try:
            with self.assertRaises(P.ProbeStop):
                P.connect_and_run(Path("/nonexistent"), "auto", "read")
        finally:
            P.subprocess.check_output = original


# --- plan and refusals ----------------------------------------------------------------
class PlanTests(unittest.TestCase):
    def setUp(self):
        self.devices, self.adt, self.proxy = standard_world()
        self.model, self.states = load(self.adt, self.proxy)

    def plan(self, names, **kw):
        return P.plan_power_cycle(self.model, self.states, names, **kw)

    def refused(self, names, **kw):
        return dict(self.plan(names, **kw).refusals)

    def test_an_ordinary_domain_is_accepted(self):
        plan = self.plan(["ISP"])
        self.assertEqual([s.device.name for s in plan.steps], ["ISP"])
        self.assertEqual(plan.refusals, [])
        self.assertIn("notify_pmp", plan.steps[0].note)
        self.assertIn("Hypothesis", plan.steps[0].note)

    def test_name_match_is_case_insensitive(self):
        self.assertEqual([s.device.name for s in self.plan(["isp"]).steps], ["ISP"])

    def test_system_essential_domains_are_refused_by_name(self):
        extra = [FakeDevice("MCPU0_0", 40, (), (), 20), FakeDevice("PCPU_3", 41, (), (), 21),
                 FakeDevice("MCPM1", 42, (), ("notify_pmp",), 22),
                 FakeDevice("PCPM", 43, (), ("notify_pmp",), 23),
                 FakeDevice("AIC", 44, (), (), 24), FakeDevice("AIC_GFX", 45, (), (), 25),
                 FakeDevice("ANE_CPU", 46, (2,), (), 26), FakeDevice("DISPEXT0_CPU", 47, (2,), (), 27),
                 FakeDevice("ECPU_1", 48, (), (), 28)]
        devices = standard_devices() + extra
        adt = FakeADT(devices)
        proxy = FakeProxy(devices)
        for dev in extra:
            proxy.regs[BASE + 8 * dev.slot] = ON
        model, states = load(adt, proxy)

        def reason(name):
            return dict(P.plan_power_cycle(model, states, [name]).refusals).get(name)
        for name in ("MCPU0_0", "PCPU_3", "MCPM1", "PCPM", "AIC", "AIC_GFX", "ECPU_1"):
            with self.subTest(name):
                self.assertIn("system-essential", reason(name))
        # coprocessor and display "CPU" domains are not CPU cores
        for name in ("ANE_CPU", "DISPEXT0_CPU"):
            with self.subTest(name):
                self.assertIsNone(reason(name))

    def test_every_refusal_has_its_reason(self):
        cases = {
            "SOC_TOP": "always-on",
            "VIRT_GRP": "virtual",
            "OFF_DOM": "not fully on",
            "AUTO_DOM": "auto-enable",
            "UART0": "proxy link",
            "FAB": "proxy link",
            "ATC0_USB_AON": "proxy link",
            "GPU": "children still powered: GPU_SHADER",
            "ANS": "children still powered: PINNED_VIRT",
            "NOPE": "unknown domain",
            "TWIN": "ambiguous",
        }
        for name, reason in cases.items():
            with self.subTest(name):
                got = self.refused([name])
                self.assertEqual(len(got), 1, got)
                self.assertIn(reason, list(got.values())[0])

    def test_refusal_clears_all_steps_so_nothing_runs(self):
        plan = self.plan(["ISP", "SOC_TOP"])
        self.assertEqual(plan.steps, ())
        self.assertEqual(len(plan.refusals), 1)

    def test_children_named_first_make_the_parent_acceptable(self):
        self.assertIn("GPU", self.refused(["GPU"]))
        plan = self.plan(["GPU_SHADER", "GPU"])
        self.assertEqual([s.device.name for s in plan.steps], ["GPU_SHADER", "GPU"])
        # the other order does not: the parent is checked while the child is still on
        self.assertIn("GPU", self.refused(["GPU", "GPU_SHADER"]))

    def test_virtual_critical_child_pins_its_parent(self):
        self.assertIn("children still powered", self.refused(["ANS"])["ANS"])

    def test_duplicate_names_are_refused(self):
        self.assertIn("named twice", self.refused(["ISP", "isp"])["isp"])

    def test_cap_on_domains_per_run(self):
        names = ["ISP", "SIO", "LEAF", "GPU_SHADER", "GPU"]
        self.assertEqual(len(names), P.MAX_DOMAINS + 1)
        self.assertIn("at most", self.refused(names)["--power-cycle"])
        self.assertEqual(self.plan(names[:P.MAX_DOMAINS]).refusals, [])

    def test_unreadable_register_is_refused(self):
        key = (0, next(d.index for d in self.model.devices if d.name == "ISP"))
        self.states[key] = ("trapped", "MmioFault")
        self.assertIn("could not be read", self.refused(["ISP"])["ISP"])

    def test_reset_or_disable_bits_are_refused(self):
        key = (0, next(d.index for d in self.model.devices if d.name == "ISP"))
        for bit in (31, 10):
            self.states[key] = ("ok", ON | (1 << bit))
            self.assertIn("bit is set", self.refused(["ISP"])["ISP"])

    def test_clock_gated_target_is_not_fully_on(self):
        key = (0, next(d.index for d in self.model.devices if d.name == "ISP"))
        self.states[key] = ("ok", 0x4F)
        self.assertIn("not fully on", self.refused(["ISP"])["ISP"])

    def test_missing_link_roots_fail_closed(self):
        devices = [d for d in standard_devices() if d.name not in ("UART0", "ATC0_USB",
                                                                    "ATC0_USB_AON")]
        adt = FakeADT(devices)
        proxy = FakeProxy(devices)
        model, states = load(adt, proxy)
        got = dict(P.plan_power_cycle(model, states, ["ISP"]).refusals)
        self.assertIn("link dependency unknown", got["ISP"])

    def test_nonexistent_die_is_refused(self):
        self.assertIn("does not exist", self.refused(["ISP"], die=1)["--die"])

    def test_empty_names_are_rejected_by_the_parser(self):
        for text in ("", " ", "ISP,", ",ISP"):
            with self.assertRaises(P.ProbeStop):
                P.parse_names(text)

    def test_plan_output_names_every_step_and_refusal(self):
        out = Lines()
        P.show_plan(self.plan(["ISP"]), out)
        self.assertTrue(out[0].startswith("PLAN ISP"))
        out = Lines()
        P.show_plan(self.plan(["SOC_TOP"]), out)
        self.assertTrue(out[0].startswith("REFUSED SOC_TOP"))

    def test_live_plan_writes_nothing(self):
        code, lines, proxy, _ = run_live("plan", names=["ISP"])
        self.assertEqual(code, P.EXIT_OK)
        self.assertEqual(proxy.writes, [])
        self.assertTrue(any(l.startswith("PLAN OK") for l in lines))
        code, lines, proxy, _ = run_live("plan", names=["UART0"])
        self.assertEqual(code, P.EXIT_REFUSED)
        self.assertEqual(proxy.writes, [])


# --- stage 2 --------------------------------------------------------------------------
class CycleTests(unittest.TestCase):
    ISP = BASE + 8 * 8
    ISP_TARGET = P.PS_ACTIVE

    def run_cycle(self, names=("ISP",), settle=2.0, tail=1.0, prepare=None):
        devices, adt, proxy = standard_world()
        if prepare:
            prepare(proxy)
        return run_live_with(proxy, adt, "cycle", names=list(names), settle=settle, tail=tail)

    def test_success_writes_exactly_off_then_on_with_m1n1s_mask(self):
        code, lines, proxy, _ = self.run_cycle()
        self.assertEqual(code, P.EXIT_OK, lines)
        clear = (1 << 28) | (1 << 9) | (1 << 8) | 0xF
        self.assertEqual(proxy.writes, [(self.ISP, clear, 0x0), (self.ISP, clear, 0xF)])
        self.assertEqual(proxy.regs[self.ISP] & 0xFF, 0xFF)
        self.assertTrue(any(l.startswith("PROBE PASS: 1 domain(s)") for l in lines))

    def test_every_write_is_announced_before_it_is_sent(self):
        code, lines, proxy, _ = self.run_cycle()
        log = proxy.log
        first_write = next(i for i, e in enumerate(log) if e[0] == "write")
        announced = [i for i, e in enumerate(log) if e[0] == "out" and e[1].startswith("POWER-OFF")]
        self.assertTrue(announced and announced[0] < first_write)
        second_write = [i for i, e in enumerate(log) if e[0] == "write"][1]
        power_on = next(i for i, e in enumerate(log)
                        if e[0] == "out" and e[1].startswith("POWER-ON"))
        self.assertLess(power_on, second_write)
        # the announcement names the domain and its address
        self.assertIn("ISP", log[announced[0]][1])
        self.assertIn("0x%x" % self.ISP, log[announced[0]][1])

    def test_the_link_is_checked_during_the_settle_and_the_tail(self):
        code, lines, proxy, _ = self.run_cycle(settle=3.0, tail=2.0)
        # 3 s / 0.5 s settle + 2 s / 0.5 s tail, plus the gate nop
        self.assertGreaterEqual(proxy.nops, 1 + 6 + 4)

    def test_group_is_powered_off_in_order_and_restored_in_reverse(self):
        code, lines, proxy, _ = self.run_cycle(names=("GPU_SHADER", "GPU"), settle=1.0, tail=0)
        self.assertEqual(code, P.EXIT_OK, lines)
        order = [((a - BASE) // 8, s) for a, c, s in proxy.writes]
        # shader off, gpu off (child first), then gpu on, shader on (parent first)
        self.assertEqual(order, [(7, 0x0), (6, 0x0), (6, 0xF), (7, 0xF)])
        off_line = next(l for l in lines if l.startswith("POWER-OFF GPU "))
        self.assertIn("already off: GPU_SHADER", off_line)

    def test_link_loss_in_a_group_names_the_domain_and_the_ones_already_off(self):
        def prepare(proxy):
            proxy.die_after_off[BASE + 8 * 6] = 2           # GPU, the second one
        code, lines, proxy, _ = self.run_cycle(names=("GPU_SHADER", "GPU"), settle=4.0, tail=0,
                                               prepare=prepare)
        self.assertEqual(code, P.EXIT_LINK_LOST)
        self.assertEqual(len(proxy.writes), 2)               # both power-offs, no restore
        lost = next(l for l in lines if l.startswith("LINK LOST"))
        self.assertIn("powering off GPU ", lost)
        self.assertIn("already off: GPU_SHADER", lost)

    def test_a_domain_that_will_not_power_off_restores_the_whole_group(self):
        code, lines, proxy, _ = self.run_cycle(
            names=("GPU_SHADER", "GPU"), settle=1.0, tail=0,
            prepare=lambda p: p.stuck_off.add(BASE + 8 * 6))
        self.assertEqual(code, P.EXIT_STOP)
        order = [((a - BASE) // 8, s) for a, c, s in proxy.writes]
        self.assertEqual(order, [(7, 0x0), (6, 0x0), (6, 0xF), (7, 0xF)])

    def test_an_error_during_the_restore_phase_still_tries_everything_once(self):
        devices, adt, proxy = standard_world()
        real = proxy.mask32
        state = {"n": 0}

        def flaky(address, clear, setbits):
            state["n"] += 1
            if state["n"] == 3:                  # the first restore write
                raise ConnectionError("link lost")
            return real(address, clear, setbits)
        proxy.mask32 = flaky
        lines = Lines()
        api = make_api(proxy, FakeIface(), adt)
        with self.assertRaises(ConnectionError):
            P.live_session(api, "auto", "cycle", names=["GPU_SHADER", "GPU"], settle=1.0, tail=0,
                           out=lines)
        self.assertTrue(any(l.startswith("Interrupted with") or l.startswith("NOT RESTORED")
                            for l in lines))

    def test_refused_plan_sends_no_write(self):
        code, lines, proxy, _ = self.run_cycle(names=("ISP", "UART0"))
        self.assertEqual(code, P.EXIT_REFUSED)
        self.assertEqual(proxy.writes, [])
        self.assertTrue(any("PLAN REFUSED: nothing was written" in l for l in lines))

    def test_link_loss_names_the_domain_and_does_not_try_to_restore(self):
        def prepare(proxy):
            proxy.die_after_off[self.ISP] = 3
        code, lines, proxy, _ = self.run_cycle(prepare=prepare, settle=5.0)
        self.assertEqual(code, P.EXIT_LINK_LOST)
        self.assertEqual(len(proxy.writes), 1)
        lost = next(l for l in lines if l.startswith("LINK LOST"))
        self.assertIn("ISP", lost)
        self.assertIn("Nothing was restored", lost)
        # the last announcement before the loss is the POWER-OFF line for ISP
        announcements = [l for l in lines if l.startswith("POWER-")]
        self.assertTrue(announcements[-1].startswith("POWER-OFF ISP"))

    def test_loss_in_the_tail_is_reported_with_the_restored_domains(self):
        def prepare(proxy):
            proxy.regs[self.ISP] = ON
            real = proxy.mask32

            def mask32(address, clear, setbits):
                value = real(address, clear, setbits)
                if setbits == 0xF:
                    proxy.nop_budget = 1
                return value
            proxy.mask32 = mask32
        code, lines, proxy, _ = self.run_cycle(prepare=prepare, settle=1.0, tail=5.0)
        self.assertEqual(code, P.EXIT_LINK_LOST)
        self.assertTrue(any(l.startswith("LINK LOST") and "ISP" in l and "last restore" in l
                            for l in lines))

    def test_a_domain_that_will_not_come_back_is_reported_not_restored(self):
        code, lines, proxy, _ = self.run_cycle(prepare=lambda p: p.no_return.add(self.ISP))
        self.assertEqual(code, P.EXIT_NOT_RESTORED)
        self.assertTrue(any(l.startswith("NOT RESTORED: ISP") for l in lines))

    def test_a_domain_that_will_not_power_off_is_restored_and_stopped(self):
        code, lines, proxy, _ = self.run_cycle(prepare=lambda p: p.stuck_off.add(self.ISP))
        self.assertEqual(code, P.EXIT_STOP)
        self.assertEqual(len(proxy.writes), 2)              # off request, then the restore
        self.assertTrue(any("never reached PWRGATE" in l for l in lines))

    def test_interrupt_after_the_power_off_attempts_one_restore_and_says_so(self):
        devices, adt, proxy = standard_world()
        clk = FakeClock()
        real_sleep = clk.sleep

        def interrupting(seconds):
            real_sleep(seconds)
            if proxy.writes and not hasattr(proxy, "tripped"):
                proxy.tripped = True
                raise KeyboardInterrupt
        clk.sleep = interrupting
        api = make_api(proxy, FakeIface(), adt, clk)
        lines = Lines()
        with self.assertRaises(KeyboardInterrupt):
            P.live_session(api, "auto", "cycle", names=["ISP"], settle=5.0, tail=0, out=lines)
        self.assertEqual(len(proxy.writes), 2)
        self.assertEqual(proxy.writes[1][2], 0xF)
        self.assertTrue(any(l.startswith("Interrupted with ISP powered off") for l in lines))

    def test_a_dead_link_during_the_interrupt_restore_prints_not_restored(self):
        devices, adt, proxy = standard_world()
        clk = FakeClock()
        real_sleep = clk.sleep

        def interrupting(seconds):
            real_sleep(seconds)
            if proxy.writes:
                proxy.dead = True
                raise KeyboardInterrupt
        clk.sleep = interrupting
        api = make_api(proxy, FakeIface(), adt, clk)
        lines = Lines()
        with self.assertRaises(KeyboardInterrupt):
            P.live_session(api, "auto", "cycle", names=["ISP"], settle=5.0, tail=0, out=lines)
        self.assertTrue(any(l.startswith("NOT RESTORED: ISP") for l in lines))

    def test_interrupt_mid_restore_retries_only_what_is_not_verified(self):
        devices, adt, proxy = standard_world()
        clk = FakeClock()
        real_sleep = clk.sleep

        def interrupting(seconds):
            real_sleep(seconds)
            if len(proxy.writes) == 4 and not hasattr(proxy, "tripped"):
                proxy.tripped = True          # shader's restore is in flight, gpu is verified
                raise KeyboardInterrupt
        clk.sleep = interrupting
        api = make_api(proxy, FakeIface(), adt, clk)
        lines = Lines()
        with self.assertRaises(KeyboardInterrupt):
            P.live_session(api, "auto", "cycle", names=["GPU_SHADER", "GPU"], settle=1.0,
                           tail=0, out=lines)
        self.assertEqual(len(proxy.writes), 5)           # 2 off, 2 on, ONE retry (the shader)
        self.assertEqual(proxy.writes[-1][0], BASE + 8 * 7)
        self.assertTrue(any(l.startswith("Interrupted with GPU_SHADER powered off")
                            for l in lines))

    def test_register_fault_on_the_write_is_not_swallowed(self):
        devices, adt, proxy = standard_world()
        real = proxy.mask32

        def faulting(address, clear, setbits):
            real(address, clear, setbits)
            proxy.exc = 1
        proxy.mask32 = faulting
        with self.assertRaises(P.MmioFault):
            run_live_with(proxy, adt, "cycle", names=["ISP"], settle=1.0, tail=0)
        # the faulting write may have taken effect: one restore request must follow it
        self.assertEqual([s for a, c, s in proxy.writes][:2], [0x0, 0xF])

    def test_second_die_writes_use_the_die_offset(self):
        devices = standard_devices()
        adt = FakeADT(devices, die_count=2)
        proxy = FakeProxy(devices)
        for dev in devices:
            if dev.slot is not None:
                proxy.regs[BASE + 8 * dev.slot + P.DIE_OFFSET] = ON
        proxy.regs[BASE + 8 * 10 + P.DIE_OFFSET] = ON | (1 << 28)
        proxy.regs[BASE + 8 * 11 + P.DIE_OFFSET] = OFF
        code, lines, proxy, _ = run_live_with(proxy, adt, "cycle", names=["ISP"], die=1,
                                              settle=1.0, tail=0)
        self.assertEqual(code, P.EXIT_OK, lines)
        self.assertEqual({a for a, c, s in proxy.writes}, {self.ISP + P.DIE_OFFSET})

    def test_alarm_budget_scales_with_the_run_and_is_cleared(self):
        seen = []
        real = P.signal.alarm
        P.signal.alarm = lambda s: seen.append(s) or real(0)
        try:
            self.run_cycle(names=("GPU_SHADER", "GPU"), settle=10.0, tail=10.0)
        finally:
            P.signal.alarm = real
        self.assertGreaterEqual(seen[0], 120 + 2 * 30)
        self.assertEqual(seen[-1], 0)
        self.assertEqual(signal.getsignal(signal.SIGALRM), signal.SIG_DFL)

    def test_transport_closed_on_every_exit(self):
        devices, adt, proxy = standard_world()
        api = make_api(proxy, FakeIface(), adt)
        P.live_session(api, "auto", "read", out=Lines())
        self.assertTrue(api.transport.closed)
        devices, adt, proxy = standard_world()
        proxy.chip = 0
        api = make_api(proxy, FakeIface(), adt)
        with self.assertRaises(P.ProbeStop):
            P.live_session(api, "auto", "read", out=Lines())
        self.assertTrue(api.transport.closed)


# --- connection and sanitizing --------------------------------------------------------
class FakeUart:
    DEFAULT_BAUD_RATE = 115200

    def __init__(self, device=None):
        self.device = device
        self.tty_enable = True
        self.dev = SimpleNamespace(timeout=None)


class OpenTests(unittest.TestCase):
    def setUp(self):
        self.saved = (P.usb_identity.discover, P.usb_identity.select_primary)
        P.usb_identity.discover = lambda: []
        P.usb_identity.select_primary = lambda found, device: "/dev/cu.usbmodemSECRET123"

    def tearDown(self):
        P.usb_identity.discover, P.usb_identity.select_primary = self.saved

    def test_console_echo_is_off_and_the_timeout_is_set(self):
        transport, iface = P.open_primary("auto", FakeUart, lambda path, baud: SimpleNamespace(
            path=path, close=lambda: None))
        self.assertFalse(iface.tty_enable)
        self.assertEqual(iface.dev.timeout, 15)

    def test_identity_errors_name_only_the_class(self):
        def raising(found, device):
            raise FileNotFoundError("/dev/cu.usbmodemSECRET123 missing")
        P.usb_identity.select_primary = raising
        with self.assertRaises(P.ProbeStop) as cm:
            P.open_primary("auto", FakeUart, lambda p, b: None)
        text = str(cm.exception)
        self.assertIn("FileNotFoundError", text)
        self.assertNotIn("SECRET", text)
        self.assertIsNone(cm.exception.__cause__)

    def test_open_errors_name_only_the_class_and_close_the_port(self):
        closed = []

        def serial(path, baud):
            return SimpleNamespace(close=lambda: closed.append(True))

        class Failing(FakeUart):
            def __init__(self, device=None):
                raise OSError("could not open port /dev/cu.usbmodemSECRET123")
        with self.assertRaises(P.ProbeStop) as cm:
            P.open_primary("auto", Failing, serial)
        self.assertNotIn("SECRET", str(cm.exception))
        self.assertIn("OSError", str(cm.exception))
        self.assertEqual(closed, [True])

    def test_alarm_timeout_passes_through_untouched(self):
        def raising(found, device):
            raise TimeoutError("alarm")
        P.usb_identity.select_primary = raising
        with self.assertRaises(TimeoutError):
            P.open_primary("auto", FakeUart, lambda p, b: None)


class CliTests(unittest.TestCase):
    def parse(self, argv, runner=None):
        runner = runner or (lambda *a, **k: 0)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = P.main(argv, runner=runner)
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    def test_live_use_requires_device_and_the_exact_confirmation(self):
        for argv in (["read"], ["read", "--device", "auto"],
                     ["read", "--device", "auto", "--confirm", "nope"],
                     ["read", "--device", "auto", "--confirm", P.CONFIRM_CYCLE],
                     ["cycle", "ISP", "--device", "auto"],
                     ["cycle", "ISP", "--device", "auto", "--confirm", P.CONFIRM_READ],
                     ["plan", "ISP", "--device", "auto", "--confirm", P.CONFIRM_CYCLE]):
            with self.subTest(argv):
                self.assertEqual(self.parse(argv)[0], 2)

    def test_read_confirmation_cannot_authorize_stage_two(self):
        called = []
        code, _, _ = self.parse(["cycle", "ISP", "--device", "auto", "--confirm", P.CONFIRM_READ],
                                runner=lambda *a, **k: called.append(1) or 0)
        self.assertEqual(code, 2)
        self.assertEqual(called, [])

    def test_settle_and_tail_bounds(self):
        base = ["cycle", "ISP", "--device", "auto", "--confirm", P.CONFIRM_CYCLE]
        for extra in (["--settle", "0.5"], ["--settle", "61"], ["--tail", "-1"], ["--tail", "61"]):
            with self.subTest(extra):
                self.assertEqual(self.parse(base + extra)[0], 2)
        self.assertEqual(self.parse(base + ["--settle", "1", "--tail", "0"])[0], 0)

    def test_arguments_reach_the_runner(self):
        got = {}

        def runner(m1n1, device, mode, **options):
            got.update(device=device, mode=mode, **options)
            return 0
        self.parse(["cycle", "isp, sio", "--device", "auto", "--confirm", P.CONFIRM_CYCLE,
                    "--settle", "3", "--tail", "4", "--die", "0"], runner=runner)
        self.assertEqual(got["names"], ["isp", "sio"])
        self.assertEqual((got["settle"], got["tail"], got["mode"]), (3.0, 4.0, "cycle"))

    def test_json_path_must_be_new_in_a_writable_directory(self):
        base = ["read", "--device", "auto", "--confirm", P.CONFIRM_READ]
        with tempfile.TemporaryDirectory() as d:
            existing = Path(d) / "have.json"
            existing.write_text("{}")
            self.assertEqual(self.parse(base + ["--json", str(existing)])[0], 2)
            self.assertEqual(self.parse(base + ["--json", str(Path(d) / "no/such/dir/x.json")])[0], 2)
            self.assertEqual(self.parse(base + ["--json", str(Path(d) / "new.json")])[0], 0)
            os.symlink(str(Path(d) / "missing-target"), str(Path(d) / "dangling.json"))
            self.assertEqual(self.parse(base + ["--json", str(Path(d) / "dangling.json")])[0], 2)

    def test_offline_plan_from_json_needs_no_device(self):
        devices, adt, proxy = standard_world()
        model, states = load(adt, proxy)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "stage1.json"
            path.write_text(json.dumps(P.stage1_document(model, states, MARKER)))
            code, out, _ = self.parse(["plan", "ISP,SIO", "--from-json", str(path)],
                                      runner=lambda *a, **k: self.fail("must not connect"))
            self.assertEqual(code, 0)
            self.assertIn("PLAN ISP", out)
            self.assertIn("PLAN OK (offline", out)
            code, out, _ = self.parse(["plan", "UART0", "--from-json", str(path)])
            self.assertEqual(code, P.EXIT_REFUSED)
            self.assertIn("REFUSED UART0", out)
            code, _, _ = self.parse(["plan", "ISP", "--from-json", str(path), "--device", "auto"])
            self.assertEqual(code, 2)

    def test_exit_codes_are_distinct(self):
        codes = {P.EXIT_OK, P.EXIT_STOP, P.EXIT_REFUSED, P.EXIT_LINK_LOST, P.EXIT_NOT_RESTORED,
                 P.EXIT_INTERRUPTED}
        self.assertEqual(len(codes), 6)
        self.assertNotIn(2, codes)      # argparse's own code stays unambiguous


class ScrubTests(unittest.TestCase):
    def test_scrub_removes_callout_paths_only(self):
        self.assertEqual(P.scrub("could not open /dev/cu.usbmodemABC123, retry"),
                         "could not open <device>, retry")
        self.assertEqual(P.scrub("/dev/tty.usbmodemX1 and /dev/cu.Y2"), "<device> and <device>")
        self.assertEqual(P.scrub("plain text 0x1234"), "plain text 0x1234")

    def run_cli(self, exc):
        def main(argv=None, runner=None):
            raise exc
        original = P.main
        P.main = main
        err, out = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                code = P.cli([])
        finally:
            P.main = original
        return code, out.getvalue(), err.getvalue()

    def test_stop_line_is_scrubbed_and_has_no_traceback(self):
        code, out, err = self.run_cli(RuntimeError("failed on /dev/cu.usbmodemSECRET9 now"))
        self.assertEqual(code, P.EXIT_STOP)
        self.assertNotIn("SECRET", err)
        self.assertNotIn("Traceback", err)
        self.assertEqual(err.count("\n"), 1)

    def test_ctrl_c_with_a_chained_device_path_prints_one_clean_line(self):
        try:
            try:
                raise OSError("could not open port /dev/cu.usbmodemSECRET9")
            except OSError:
                raise KeyboardInterrupt
        except KeyboardInterrupt as exc:
            error = exc
        code, out, err = self.run_cli(error)
        self.assertEqual(code, P.EXIT_INTERRUPTED)
        self.assertNotIn("SECRET", err + out)
        self.assertNotIn("Traceback", err)

    def test_probe_stop_carries_its_exit_code(self):
        code, out, err = self.run_cli(P.ProbeStop("refused", P.EXIT_REFUSED))
        self.assertEqual(code, P.EXIT_REFUSED)
        self.assertEqual(err.strip(), "STOP: refused")


# --- the real t6050 device table ------------------------------------------------------
REAL_ADT = ROOT / "hardware" / "adt" / "adt-sanitized.json"


def real_model():
    """The PMGR device records of the sanitized macOS ADT export, decoded like the client."""
    import struct
    doc = json.loads(REAL_ADT.read_text())

    def find(node, path):
        if node.get("path") == path:
            return node
        for child in node.get("children") or ():
            found = find(child, path)
            if found:
                return found
    node = find(doc, "/Root/device-tree/arm-io/pmgr")
    values = node["values"]
    raw = bytes.fromhex(values["devices"]["hex"])
    groups = bytes.fromhex(values["ps-groups"]["hex"])
    group_regs = [struct.unpack_from("<3I", groups, 12 * i)[0] for i in range(len(groups) // 12)]
    reg_bases = [int(r["addr"], 16) for r in values["reg"]]
    records = [raw[i * 48:(i + 1) * 48] for i in range(len(raw) // 48)]
    u8id = records[0][3] != records[1][3]
    devices = []
    for index, r in enumerate(records):
        bits = r[0]
        names = [n for k, n in enumerate(reversed(FLAG_NAMES)) if bits >> k & 1]
        dev_id = r[3] if u8id else struct.unpack_from("<H", r, 26)[0]
        parents = (tuple(p for p in r[4:6] if p) if u8id
                   else tuple(p for p in struct.unpack_from("<2H", r, 4) if p))
        address = None
        if "no_ps" not in names:
            address = reg_bases[group_regs[r[19]]] + int.from_bytes(r[16:19], "little")
        devices.append(P.Device(index, r[32:48].split(b"\0")[0].decode(), dev_id, parents,
                                frozenset(names), address, ()))
    return P.Model(tuple(devices), 1, "/arm-io/pmgr")


@unittest.skipUnless(REAL_ADT.is_file(), "sanitized ADT export not present")
class RealTableTests(unittest.TestCase):
    """The probe's rules against the real t6050 device table (all PS registers ACTIVE)."""

    @classmethod
    def setUpClass(cls):
        cls.model = real_model()
        cls.states = {(0, d.index): ("ok", ON) for d in cls.model.devices if d.address}
        cls.by_name = {}
        for d in cls.model.devices:
            cls.by_name.setdefault(d.name, []).append(d)

    def refusal(self, name):
        dev = self.by_name[name][0]
        got = P.cycle_refusal(self.model, self.states, 0, dev)
        return None if got is None else got[0]

    def test_table_shape(self):
        devices = self.model.devices
        count = lambda f: sum(1 for d in devices if f in d.flags)
        self.assertEqual(len(devices), 661)
        self.assertEqual((count("no_ps"), count("critical"), count("notify_pmp")), (338, 199, 53))
        self.assertEqual(sum(1 for d in devices if d.address is not None), 323)

    def test_link_roots_exist_and_the_closure_matches_the_hypervisors_essentials(self):
        protected = {self.model.devices[i].name for i in P.link_protected(self.model)}
        for name in ("UART0", "ATC0_USB", "ATC0_USB_AON", "UART_P", "SIO", "FAB8_SOC",
                     "FAB0_PIOGW", "ATC0_COMMON", "FAB3_SOC"):
            self.assertIn(name, protected)      # map_essential()'s list for a USB0 link
        self.assertEqual(len(protected), 19)

    def test_cpu_interrupt_controller_and_link_domains_are_never_accepted(self):
        for name in ("MCPU0_0", "MCPU1_5", "PCPU_0", "PCPU_5", "MCPM0", "PCPM", "AIC", "AIC_GFX"):
            with self.subTest(name):
                self.assertEqual(self.refusal(name), "sys")
        # link domains the ADT does not flag critical are caught by the closure; the rest are
        # already refused as always-on or virtual
        expected = {"UART0": "link", "UART_P": "link", "ATC0_USB": "link", "ATC1_USB": "link",
                    "ATC0_USB_AON": "link", "ATC0_COMMON": "link", "SIO": "crit",
                    "FAB8_SOC": "crit", "FAB0_PIOGW": "virt", "FAB3_SOC": "virt"}
        for name, code in expected.items():
            with self.subTest(name):
                self.assertEqual(self.refusal(name), code)
        for name in ("I2C0", "SPI0", "UART1"):          # children of the link, not parents
            with self.subTest(name):
                self.assertIsNone(self.refusal(name))

    def test_a_leaf_accelerator_domain_is_accepted_with_the_pmp_note(self):
        plan = P.plan_power_cycle(self.model, self.states, ["ISP_SYS"])
        self.assertEqual(plan.refusals, [])
        self.assertEqual([s.device.name for s in plan.steps], ["ISP_SYS"])
        self.assertIn("notify_pmp", plan.steps[0].note)

    def test_parents_need_their_children_off_first(self):
        self.assertEqual(self.refusal("DISPEXT0_SYS"), "kids")
        self.assertEqual(self.refusal("DISPEXT0_CPU"), None)

    def test_duplicate_names_in_the_real_table_are_ambiguous(self):
        self.assertEqual(len(self.by_name["APCIE_PHY_SW"]), 2)
        plan = P.plan_power_cycle(self.model, self.states, ["APCIE_PHY_SW"])
        self.assertIn("ambiguous", plan.refusals[0][1])

    def test_a_useful_number_of_domains_stay_cyclable(self):
        elig = P.eligibility(self.model, self.states, 0)
        ok = [self.model.devices[i] for i, v in elig.items() if v == "ok"]
        self.assertGreater(len(ok), 80)
        self.assertGreater(sum(1 for d in ok if "notify_pmp" in d.flags), 5)
        self.assertFalse(any(d.name.startswith(("MCPU", "PCPU", "AIC")) for d in ok))


# --- mutation checks ------------------------------------------------------------------
MUTANTS = (
    ("system-essential domains accepted",
     "        if re.fullmatch(pattern, dev.name, re.IGNORECASE):\n            return \"sys\"",
     "        if False:\n            return \"sys\""),
    ("critical domains accepted", '    if "critical" in dev.flags:\n        return "crit"',
     '    if False:\n        return "crit"'),
    ("link closure ignored", "    if dev.index in protected:\n        return \"link\"",
     "    if False:\n        return \"link\""),
    ("children ignored", "    if busy:\n        return \"kids\"", "    if False:\n        return \"kids\""),
    ("cap removed", "    if len(names) > max_domains:", "    if False:"),
    ("auto-enable accepted", "    if st[\"auto_enable\"]:\n        return \"auto\"",
     "    if False:\n        return \"auto\""),
    ("partially-off accepted", "    if st[\"actual\"] != PS_ACTIVE or st[\"target\"] != PS_ACTIVE:",
     "    if False:"),
    ("set_mode clear mask loses the target",
     "SET_MODE_CLEAR = AUTO_ENABLE | WAS_CLKGATED | WAS_PWRGATED | PS_TARGET",
     "SET_MODE_CLEAR = AUTO_ENABLE | WAS_CLKGATED | WAS_PWRGATED"),
    ("restore write dropped",
     "    io.mask32(address, SET_MODE_CLEAR, PS_ACTIVE)\n    return _wait_actual(io, address, PS_ACTIVE, STATE_POLL_TIMEOUT)",
     "    return _wait_actual(io, address, PS_ACTIVE, STATE_POLL_TIMEOUT)"),
    ("restore order not reversed",
     "        for step in reversed(off):\n            back, elapsed, raw = _restore(io, step, plan, out)",
     "        for step in off:\n            back, elapsed, raw = _restore(io, step, plan, out)"),
    ("link loss undetected", "        if not _link_alive(io):\n            return False, io.clock() - start",
     "        if False:\n            return False, io.clock() - start"),
    ("transport errors become rows", "            except MmioFault as exc:", "            except Exception as exc:"),
    ("console echo left on", "        iface.tty_enable = False", "        iface.tty_enable = True"),
    ("confirmation not checked", "    if args.device is None or args.confirm != needed:",
     "    if args.device is None:"),
    ("scrub is a no-op", 'return DEVICE_PATH.sub("<device>", str(text))', "return str(text)"),
    ("die offset dropped in stage 2", "        address = dev.address + DIE_OFFSET * plan.die\n",
     "        address = dev.address\n"),
    ("reads may write", "    value = proxy.read32(address)\n",
     "    value = proxy.read32(address)\n    proxy.mask32(address, 0, 0)\n"),
    ("Ctrl-C not caught", "    except KeyboardInterrupt:\n        print(\"STOP: KeyboardInterrupt\"",
     "    except ZeroDivisionError:\n        print(\"STOP: KeyboardInterrupt\""),
    ("interrupt restore dropped",
     "            try:\n                io.mask32(address, SET_MODE_CLEAR, PS_ACTIVE)\n            except BaseException:\n                pending.append(step.device.name)",
     "            try:\n                pass\n            except BaseException:\n                pending.append(step.device.name)"),
    ("power-off not recorded before the write",
     "            off.append(step)    # before the write: an interrupted request is also restored\n            io.mask32(address, SET_MODE_CLEAR, PS_PWRGATE)",
     "            io.mask32(address, SET_MODE_CLEAR, PS_PWRGATE)\n            off.append(step)"),
    ("restored domains are restored again after an interrupt",
     "        todo = [s for s in reversed(off) if s.device.index not in restored]",
     "        todo = [s for s in reversed(off)]"),
    ("json overwrite allowed", '    with path.open("x") as handle:', '    with path.open("w") as handle:'),
)


def mutated_module(old, new):
    if SOURCE.count(old) != 1:
        raise AssertionError("mutant anchor not unique: %r (%d)" % (old[:60], SOURCE.count(old)))
    module = types.ModuleType("pmgr_probe_mutant")
    module.__file__ = str(HERE / "pmgr_probe.py")
    exec(compile(SOURCE.replace(old, new), module.__file__, "exec"), module.__dict__)
    return module


class MutationTests(unittest.TestCase):
    """Each mutant of pmgr_probe.py must make at least one other test in this file fail."""

    CLASSES = (DecodeTests, ModelTests, ReadTests, GateTests, PlanTests, CycleTests,
               OpenTests, CliTests, ScrubTests, RealTableTests)

    def failures_with(self, module):
        global P
        saved, P = P, module
        try:
            suite = unittest.TestSuite()
            loader = unittest.TestLoader()
            for cls in self.CLASSES:
                suite.addTests(loader.loadTestsFromTestCase(cls))
            result = unittest.TestResult()
            suite.run(result)
            return len(result.failures) + len(result.errors)
        finally:
            P = saved

    def test_the_unmutated_module_passes_everything(self):
        self.assertEqual(self.failures_with(pmgr_probe), 0)

    def test_every_mutant_is_caught(self):
        survivors = []
        for name, old, new in MUTANTS:
            if self.failures_with(mutated_module(old, new)) == 0:
                survivors.append(name)
        self.assertEqual(survivors, [])


if __name__ == "__main__":
    unittest.main()
