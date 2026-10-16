# SPDX-License-Identifier: GPL-2.0-only OR MIT
"""Offline tests for mtp_probe.py: no device, no m1n1 client, no network.

usage: python3 -I test_mtp_probe.py
"""
import contextlib
import io
import json
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import mtp_adt  # noqa: E402
import mtp_probe as P  # noqa: E402

ADT = P.DEFAULT_ADT


def repo_regions():
    return P.regions_from_facts(mtp_adt.facts(ADT))


class FakeProxy:
    """A register file. Any write-ish attribute use is a test failure."""

    def __init__(self, regs=None, fault_at=()):
        self.regs = dict(regs or {})
        self.fault_at = set(fault_at)
        self.log = []
        self._exc = 0

    def read32(self, address):
        self.log.append(address)
        if address in self.fault_at:
            self._exc += 1
            return 0
        return self.regs.get(address, 0)

    def get_exc_count(self):
        count, self._exc = self._exc, 0
        return count

    def __getattr__(self, name):
        raise AssertionError("probe touched proxy.%s" % name)


def t8110_regs(reg, base_offset=0, num_sids=16, ttbr_sids=(0,)):
    base = reg["dart"] + base_offset
    regs = {
        base + 0x00: 0x00000001, base + 0x04: 0x00000001,
        base + 0x08: (36 << 24) | (32 << 16) | (1 << 8) | 0,      # PA 36, VA 32, v1.0
        base + 0x0c: (16 << 16) | num_sids,
    }
    for sid in ttbr_sids:
        regs[base + 0x1000 + 4 * sid] = 0x1               # translate enable
        regs[base + 0x1400 + 4 * sid] = 0x80000001        # valid, address field
    regs[base + 0xc00] = sum(1 << s for s in ttbr_sids)
    return regs


def device(reg, **kw):
    regs = t8110_regs(reg, **kw)
    regs[reg["asc"] + 0x44] = 0x10                         # started
    mbox = reg["asc"] + 0x8000
    regs[mbox + 0x110] = 1 << 17                           # both directions empty
    regs[mbox + 0x114] = 1 << 17
    regs[reg["dock"][3] + 0x14] = mtp_adt.FIFO_SIZE        # TX free
    return regs


def run(proxy, reg):
    ro = P.ReadOnly(proxy, P.allowlist(reg))
    reads, values, dart = P.run_reads(ro, reg)
    return ro, reads, values, dart


class Plan(unittest.TestCase):
    def test_addresses_follow_the_adt_facts(self):
        reg = repo_regions()
        plan = {(g, n): a for g, n, a in P.static_plan(reg)}
        self.assertEqual(plan[("asc", "cpu_control")], 0x294600044)
        self.assertEqual(plan[("mailbox", "a2i_control_v4")], 0x294608110)
        self.assertEqual(plan[("mailbox", "i2a_control_v4")], 0x294608114)
        self.assertEqual(plan[("dart_plus0", "params3")], 0x294800008)
        self.assertEqual(plan[("dart_plus8000", "params3")], 0x294808008)
        self.assertEqual(plan[("dockchannel", "local_tx_free")], 0x294b34014)
        self.assertEqual(plan[("dockchannel", "remote_rx_count")], 0x294b2c02c)

    def test_no_side_effect_registers_are_ever_planned(self):
        reg = repo_regions()
        plan = P.static_plan(reg) + P.dart_plan(reg["dart"], 32)
        forbidden = set()
        for off in P.FORBIDDEN["mailbox"]:
            forbidden.add(reg["asc"] + P.MBOX_BASE_OFFSET + off)
        for base in (reg["dock"][3], reg["dock"][5]):
            for off in P.FORBIDDEN["dockchannel_data"]:
                forbidden.add(base + off)
        self.assertFalse(forbidden & {a for _, _, a in plan})

    def test_every_planned_read_is_inside_a_declared_region_and_aligned(self):
        reg = repo_regions()
        spans = P.allowlist(reg)
        for _, _, address in P.static_plan(reg) + P.dart_plan(reg["dart"], 32) + \
                P.dart_plan(reg["dart"] + P.DART_ALT_BASE, 32):
            self.assertEqual(address % 4, 0)
            self.assertTrue(any(lo <= address and address + 4 <= hi for lo, hi in spans),
                            hex(address))

    def test_sid_reads_are_capped(self):
        reg = repo_regions()
        plan = P.dart_plan(reg["dart"], 256)
        self.assertEqual(len([1 for _, n, _ in plan if n.startswith("tcr_")]), P.DART_MAX_SIDS_READ)


class ReadOnlyWrapper(unittest.TestCase):
    def setUp(self):
        self.reg = repo_regions()
        self.proxy = FakeProxy()
        self.ro = P.ReadOnly(self.proxy, P.allowlist(self.reg))

    def test_reads_inside_regions_work(self):
        self.assertEqual(self.ro.read32(self.reg["asc"] + 0x44), 0)

    def test_reads_outside_regions_are_refused(self):
        for address in (0x0, self.reg["asc"] - 4, self.reg["asc"] + self.reg["asc_window"],
                        self.reg["dart"] + self.reg["dart_window"] - 2):
            with self.subTest(hex(address)):
                with self.assertRaises(P.Forbidden):
                    self.ro.read32(address)
        self.assertEqual(self.proxy.log, [])

    def test_there_is_no_way_to_write(self):
        for name in ("write32", "write64", "set32", "clear32", "mask32", "write8", "memcpy32",
                     "iface", "call", "exit", "reboot", "hv_start"):
            with self.subTest(name):
                with self.assertRaises(P.Forbidden):
                    getattr(self.ro, name)


class Run(unittest.TestCase):
    def setUp(self):
        self.reg = repo_regions()

    def test_t8110_at_plus0(self):
        proxy = FakeProxy(device(self.reg))
        ro, reads, values, dart = run(proxy, self.reg)
        self.assertEqual(dart["chosen"], "plus0")
        dec = dart["candidates"]["plus0"]["decoded"]
        self.assertEqual((dec["ver_major"], dec["num_sids"], dec["num_clients"]), (1, 16, 16))
        self.assertEqual(dart["enabled_sids"], [0])
        self.assertTrue(dart["streams"]["0"]["tcr_decoded"]["translate"])
        self.assertTrue(dart["streams"]["0"]["ttbr_decoded"]["valid"])
        self.assertFalse(dart["streams"]["1"]["ttbr_decoded"]["valid"])
        rows = P.summarize(self.reg, values, dart)
        verdicts = {r["name"]: r["verdict"] for r in rows}
        self.assertTrue(all(v == "match" for v in verdicts.values()), verdicts)
        # everything it read was planned
        planned = {a for _, _, a in P.static_plan(self.reg)} | \
            {a for _, _, a in P.dart_plan(self.reg["dart"], 16)}
        self.assertEqual(set(proxy.log) - planned, set())
        self.assertEqual(ro.reads, len(proxy.log))

    def test_block_at_plus_8000_is_found(self):
        proxy = FakeProxy(device(self.reg, base_offset=P.DART_ALT_BASE))
        _, _, _, dart = run(proxy, self.reg)
        self.assertEqual(dart["chosen"], "plus8000")
        self.assertEqual(dart["enabled_sids"], [0])

    def test_both_candidates_prefer_plus0(self):
        regs = device(self.reg)
        regs.update(t8110_regs(self.reg, base_offset=P.DART_ALT_BASE))
        _, _, _, dart = run(FakeProxy(regs), self.reg)
        self.assertEqual(dart["chosen"], "plus0")

    def test_no_plausible_block_stops_the_dart_phase(self):
        proxy = FakeProxy({self.reg["asc"] + 0x44: 0x10})
        _, reads, _, dart = run(proxy, self.reg)
        self.assertIsNone(dart["chosen"])
        self.assertFalse([r for r in reads if r["group"] == "dart"])
        rows = P.summarize(self.reg, {}, dart)
        self.assertEqual(rows[0]["verdict"], "differs")

    def test_version_zero_is_not_a_dart(self):
        regs = device(self.reg)
        base = self.reg["dart"]
        regs[base + 0x08] = (36 << 24) | (32 << 16)          # widths look fine, version 0.0
        _, _, _, dart = run(FakeProxy(regs), self.reg)
        self.assertIsNone(dart["chosen"])

    def test_streams_translating_other_than_sid0_is_reported(self):
        proxy = FakeProxy(device(self.reg, ttbr_sids=(0, 1)))
        _, _, values, dart = run(proxy, self.reg)
        rows = {r["name"]: r for r in P.summarize(self.reg, values, dart)}
        row = rows["stream ids translating after iBoot (macOS remaps 1-4 to 0)"]
        self.assertEqual(row["verdict"], "differs")
        self.assertEqual(row["observed"], [0, 1])

    def test_mailbox_layout_is_reported(self):
        regs = device(self.reg)
        _, _, values, dart = run(FakeProxy(regs), self.reg)
        rows = {r["name"]: r for r in P.summarize(self.reg, values, dart)}
        row = rows["mailbox: exactly one register layout (v4 or m3) has plausible control words"]
        self.assertEqual((row["verdict"], row["observed"]), ("match", ["v4"]))
        m3 = {self.reg["asc"] + 0x8000 + 0x50: 1 << 17, self.reg["asc"] + 0x8000 + 0x80: 1 << 17}
        regs = device(self.reg)
        regs.pop(self.reg["asc"] + 0x8000 + 0x110)
        regs.pop(self.reg["asc"] + 0x8000 + 0x114)
        regs.update(m3)
        _, _, values, dart = run(FakeProxy(regs), self.reg)
        rows = {r["name"]: r for r in P.summarize(self.reg, values, dart)}
        row = rows["mailbox: exactly one register layout (v4 or m3) has plausible control words"]
        self.assertEqual((row["verdict"], row["observed"]), ("differs", ["m3"]))

    def test_a_trapped_read_is_recorded_not_fatal(self):
        bad = self.reg["asc"] + 0x44
        proxy = FakeProxy(device(self.reg), fault_at=[bad])
        _, reads, values, _ = run(proxy, self.reg)
        entry = [r for r in reads if r["address"] == bad][0]
        self.assertEqual(entry["status"], "trapped")
        self.assertNotIn(("asc", "cpu_control"), values)
        rows = {r["name"]: r for r in P.summarize(self.reg, values, {"chosen": None})}
        self.assertEqual(rows["MTP CPU started by iBoot"]["verdict"], "n/a")

    def test_report_prints_and_json_is_serialisable_and_clean(self):
        proxy = FakeProxy(device(self.reg))
        ro, reads, values, dart = run(proxy, self.reg)
        rows = P.summarize(self.reg, values, dart)
        lines = []
        P.print_report(self.reg, [], dart, rows, lines.append)
        self.assertTrue(any("DART block plus0" in l for l in lines))
        doc = P.document(self.reg, [], reads, values, dart, rows, P.CHIP_T6050, "marker")
        text = json.dumps(doc, sort_keys=True)
        self.assertEqual(json.loads(text)["schema"], P.SCHEMA)
        # nothing that looks like a serial, UUID, MAC or callout path
        for pattern in (r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-", r"(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}",
                        r"/dev/(?:cu|tty)", r"serial", r"\bC0[0-9A-Z]{9}\b"):
            self.assertIsNone(re.search(pattern, text), pattern)


class RegionsAndCompare(unittest.TestCase):
    class Node:
        def __init__(self, regs, **attrs):
            self._regs = regs
            self.__dict__.update(attrs)

        def get_reg(self, index):
            return self._regs[index]

    def fake_adt(self, reg, dock_size=0x1000, asc_shift=0):
        nodes = {
            "/arm-io/mtp": self.Node([(reg["asc"] + asc_shift, reg["asc_window"])]),
            "/arm-io/dart-mtp": self.Node([(reg["dart"], reg["dart_window"])], sid_count=16),
            "/arm-io/dockchannel-mtp": self.Node([(a, dock_size) for a in reg["dock"]]),
        }

        class Adt:
            def __getitem__(self_inner, path):
                return nodes[path]
        return Adt()

    def test_live_matches_repo(self):
        reg = repo_regions()
        live = P.regions_from_live_adt(self.fake_adt(reg))
        self.assertEqual(P.compare_regions(reg, live), [])

    def test_a_moved_block_is_reported(self):
        reg = repo_regions()
        live = P.regions_from_live_adt(self.fake_adt(reg, asc_shift=0x100000))
        self.assertEqual(len(P.compare_regions(reg, live)), 1)

    def test_a_moved_dockchannel_is_reported(self):
        reg = repo_regions()
        live = dict(P.regions_from_live_adt(self.fake_adt(reg)))
        live["dock"] = [a + 0x1000 for a in live["dock"]]
        self.assertEqual(P.compare_regions(reg, live), ["dockchannel regs differ"])

    def test_odd_dockchannel_window_stops(self):
        reg = repo_regions()
        with self.assertRaises(P.ProbeStop):
            P.regions_from_live_adt(self.fake_adt(reg, dock_size=0x2000))


class Session(unittest.TestCase):
    """The live path with every dependency faked: still read-only, still reports."""

    def api(self, regs):
        reg = repo_regions()
        proxy = FakeProxy(regs)
        node_test = RegionsAndCompare()

        class Api:
            transport_closed = False

            @staticmethod
            def open_primary(dev):
                class T:
                    def close(self_t):
                        Api.transport_closed = True
                return T(), object()

            @staticmethod
            def M1N1Proxy(iface):
                return proxy

            @staticmethod
            def check_target(iface, p):
                return "m1n1-marker"

            @staticmethod
            def fetch_adt(iface, p):
                return node_test.fake_adt(reg)
        return Api, proxy

    def test_session_ok_and_writes_json(self):
        reg = repo_regions()
        api, proxy = self.api(device(reg))
        lines = []
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "probe.json"
            code = P.session(api, "auto", out, ADT, lines.append)
            self.assertEqual(code, P.EXIT_OK)
            doc = json.loads(out.read_text())
            self.assertEqual(doc["chip"], "t6050")
            self.assertEqual(doc["adt_vs_repo"], [])
        self.assertTrue(api.transport_closed)
        self.assertTrue(any("no write request was sent" in l for l in lines))
        self.assertGreater(len(proxy.log), 20)


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


class LiveWiring(unittest.TestCase):
    def test_connect_and_run_builds_its_api_and_reaches_open_primary(self):
        # E1 session 1 (2026-10-16) stopped with NameError while building the Api
        # class: the class body could not see the function-local m1n1 imports.
        sys.path.insert(0, str(P.ROOT / "native" / "probe"))
        import pmgr_probe

        class Reached(Exception):
            pass

        def open_primary(dev, uart, serial):
            raise Reached(dev)

        calls = iter([pmgr_probe.launch.M1N1_COMMIT + "\n", ""])
        saved = {name: sys.modules.get(name) for name in fake_m1n1_modules()}
        original = (pmgr_probe.subprocess.check_output, pmgr_probe.open_primary)
        pmgr_probe.subprocess.check_output = lambda *a, **k: next(calls)
        pmgr_probe.open_primary = open_primary
        sys.modules.update(fake_m1n1_modules())
        try:
            with tempfile.TemporaryDirectory() as d:
                with self.assertRaises(Reached):
                    P.connect_and_run(Path("/nonexistent"), "auto", Path(d) / "x.json", ADT)
        finally:
            pmgr_probe.subprocess.check_output, pmgr_probe.open_primary = original
            for name, module in saved.items():
                if module is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = module


class Cli(unittest.TestCase):
    def test_plan_is_offline_and_exit_zero(self):
        buf = io.StringIO()
        old, sys.stdout = sys.stdout, buf
        try:
            code = P.main(["plan", "--adt", str(ADT)])
        finally:
            sys.stdout = old
        self.assertEqual(code, 0)
        self.assertIn("nothing was written", buf.getvalue())

    def test_live_requires_device_and_exact_confirm(self):
        for argv in (["read"], ["read", "--device", "auto"],
                     ["read", "--device", "auto", "--confirm", "yes"],
                     ["read", "--device", "auto", "--confirm", "pmgr-probe-j716c-read"]):
            with self.subTest(argv):
                with contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit):
                        P.main(argv)

    def test_confirmed_run_reaches_the_runner(self):
        seen = {}

        def runner(m1n1, device, json_path, adt):
            seen.update(device=device, json=json_path)
            return 0
        self.assertEqual(P.main(["read", "--device", "auto", "--confirm", P.CONFIRM_READ],
                                runner=runner), 0)
        self.assertEqual(seen["device"], "auto")

    def test_existing_json_is_refused_before_any_usb_access(self):
        with tempfile.TemporaryDirectory() as d:
            existing = Path(d) / "x.json"
            existing.write_text("{}")
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    P.main(["read", "--device", "auto", "--confirm", P.CONFIRM_READ,
                            "--json", str(existing)], runner=lambda *a: 0)

    def test_source_has_no_write_calls(self):
        text = (HERE / "mtp_probe.py").read_text()
        code = re.sub(r'"""[\s\S]*?"""', "", text)
        for token in (r"\.write32\(", r"\.write64\(", r"\.write8\(", r"\.set32\(", r"\.clear32\(",
                      r"\.mask32\(", r"\.writemem\(", r"ProxyUtils", r"\.call\(", r"\.hv_",
                      r"\.memcpy", r"\.dc_", r"\.smp_"):
            self.assertIsNone(re.search(token, code), token)


if __name__ == "__main__":
    unittest.main()
