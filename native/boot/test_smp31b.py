import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

s = importlib.util.spec_from_file_location('smp31b', Path(__file__).with_name('smp31b.py'))
c = importlib.util.module_from_spec(s)
s.loader.exec_module(c)
BASE = 0x800000000
HELPER_ADDR = BASE + 0x400000
IMAGE = bytearray(3932160)
IMAGE[c.OFF['features']:c.OFF['features'] + 20] = bytes(13) + b'\1' + bytes(3) + b'\1' + bytes(2)
IMAGE = bytes(IMAGE)


class Clock:
    def __init__(self): self.now = 0.0
    def __call__(self): return self.now
    def sleep(self, duration): self.now += duration


class Fake:
    """Full controller/census model. No bulk start/stop, SMP-call or IPI APIs.

    Literal write/call allowlists are independent of controller constants.
    Synthetic lifecycle models publication, entry and callback completion;
    it cannot emulate Apple reset, exception levels, caches, WFE or PMGR.
    """
    def __init__(self):
        self.ram = bytearray(0x404000)
        self.ram[:len(IMAGE)] = IMAGE
        self.ram[:0x70000] = c.relocated_text(IMAGE, BASE)
        self.writes, self.calls, self.events, self.mutations = [], [], 0, 0
        self.fail_mutation = self.trap_mutation = self.pending_fault = 0
        self.arrival = True
        self.complete = True
        self.bad_mpidr = self.bad_stack = self.other_core = self.stale_timer = False
        self.return_el, self.return_pfr, self.return_part = 8, 0, 0x610f0680
        self.return_mpidr, self.return_sctlr = 0x80040000, 1
        self.alloc = HELPER_ADDR
        self.bad_text = self.bad_helper = self.bad_setup = False
        self.ticks = 1000000
        self.hw = []
        self.put(0x90000, '<Q', 0x80040000)
        self.put(0x90008, '<I', 0)
        self.put(0x90210, '<Q', 0x40000)
        self.put(0x90010, '<QQ', 0x40000, BASE + 0x3c0000)
        for n in range(1, 32): self.put(0x90010 + n * 16, '<QQ', (1 << 64) - 1, 0)
        self.put(0x1012d0, '<Q', BASE + 0x7fba8)
        for n in range(18):
            self.put(0x1171e8 + n * 16, '<4B4xQ', 1, 0, n // 6, n % 6,
                     0x210050000 + (n // 6) * 0x1000000 + (n % 6) * 0x100000)
        self.put(0x1173e8, '<Q', 0x280688000)
        self.put(0x1173f0, '<B', 1)

    def put(self, offset, fmt, *values): struct.pack_into(fmt, self.ram, offset, *values)
    def nop(self): pass
    def get_chipid(self): return 0x6050
    def get_base(self): return BASE
    def get_exc_count(self):
        assert not self.hw, 'read/clear counter after CPU1 start'
        result, self.pending_fault = self.pending_fault, 0
        self.put(0x110038, '<I', 0)
        return result
    def smp_is_alive(self, cpu): return bool(struct.unpack_from('<Q', self.ram, 0x90218 + cpu * 64)[0])
    def readmem(self, address, size):
        assert not self.hw, 'bulk read after start would erase secondary fault evidence'
        return self.memory(address, size)
    def memory(self, address, size):
        if self.bad_text and address == BASE + 0x10000: return b'X' * size
        if self.bad_helper and address == HELPER_ADDR: return b'X' * size
        assert BASE <= address < address + size <= BASE + len(self.ram)
        return bytes(self.ram[address - BASE:address - BASE + size])
    def read32(self, address): return struct.unpack('<I', self.memory(address, 4))[0]
    def read64(self, address):
        if address in (0x210050000, 0x210150000): return BASE | 1
        return struct.unpack('<Q', self.memory(address, 8))[0]
    def mutation(self):
        self.mutations += 1
        if self.mutations == self.fail_mutation: raise TimeoutError('simulated lost reply')
        if self.mutations == self.trap_mutation:
            self.pending_fault = 1
            self.put(0x110038, '<I', 1)
            return False
        return True
    def memalign(self, alignment, size):
        assert (alignment, size) == (0x4000, 0x4000)
        self.mutation()
        return self.alloc
    def writemem(self, address, data):
        assert address == HELPER_ADDR and data == c.HELPER
        self.writes.append(('helper', address, len(data)))
        if self.mutation(): self.ram[address - BASE:address - BASE + len(data)] = data
    def dc_cvau(self, address, size):
        assert (address, size) == (HELPER_ADDR, 192)
        self.mutation()
    def ic_ivau(self, address, size):
        assert (address, size) == (HELPER_ADDR | 0xc0000000000, 192)
        self.mutation()
    def smp_set_wfe_mode(self, mode):
        assert mode is True and not self.hw and not any(self.smp_is_alive(n) for n in range(32))
        if self.mutation(): self.put(0x90a14, '<B', 1)
    def write32(self, address, value):
        assert (address, value) in ((BASE + 0x90a10, 1), (0x280688004, 2), (0x280688008, 2))
        self.writes.append(('write32', address, value))
        okay = self.mutation()
        if address < BASE:
            self.hw.append((address, value))
            if okay and address == 0x280688008 and self.arrival: self.enter()
        elif okay and not self.bad_setup: self.put(address - BASE, '<I', value)
    def write64(self, address, value):
        assert not self.hw and (address, value) == (BASE + 0x90a20, BASE + 0x178000)
        self.writes.append(('write64', address, value))
        if self.mutation(): self.put(address - BASE, '<Q', value)
    def enter(self):
        self.put(0x90250, '<QQ', 0x40002 if self.bad_mpidr else 0x40001, 1)
        self.put(0x90020, '<QQ', 0x40001, BASE + (0x178010 if self.bad_stack else 0x178000))
        if self.other_core: self.put(0x90298, '<Q', 1)
    def call(self, address, *args):
        self.calls.append(address)
        offset = address - (HELPER_ADDR | 0xc0000000000)
        assert offset in (0, 16, 32, 48, 64, 80, 96, 112, 160), 'unreviewed function call'
        if offset == 96:
            assert len(args) == 1 and args[0] % 8 == 0 and (
                BASE + 0x90000 <= args[0] <= BASE + 0x90a20 or args[0] == BASE + 0x110038)
            return self.read64(args[0])
        if offset == 112:
            assert args in ((BASE + 0x90218, 7), (BASE + 0x90290, 240))
            value = 0
            for index in range(args[1]): value |= self.read64(args[0] + index * 8)
            return value
        if offset == 160:
            assert args == (BASE + 0x90260, BASE + 0x37f20)
            if not self.mutation(): return 0
            self.writes.append(('publish', *args))
            self.put(0x90260, '<Q', args[1])
        else:
            assert not args
        if offset not in (0, 160):
            return {16:self.return_el, 32:self.return_pfr, 48:self.return_mpidr,
                    64:self.return_part, 80:self.return_sctlr}[offset]
        self.events += 1
        if self.complete:
            flag = self.read64(BASE + 0x90258)
            self.put(0x90258, '<Q', flag + 1)
            self.put(0x90260, '<Q', 0)
            self.put(0x90288, '<Q', self.ticks)
            if not self.stale_timer: self.ticks += 100000
        return 0x31b


def controller(fake):
    clock, journal = Clock(), []
    ctl = c.Controller(fake, fake, IMAGE, journal.append, clock=clock, sleep=clock.sleep,
                       metadata=lambda *_: None, bounds=lambda *_: (BASE, BASE + 0x800000))
    return ctl, journal, clock


def run(ctl):
    with patch.object(c.census, 'verify_image'), patch.object(c, 'verify_local'):
        return ctl.run()


class ControllerTests(unittest.TestCase):
    def test_source_pins_rechecked_before_live(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp, patch.object(c, 'ROOT', Path(tmp)):
            names = ['native/boot/smp31b.py', 'tools/m1n1-client/attempt31b-supervise.py',
                     'tools/m1n1-client/attempt31b-instructions.md']
            for name in names:
                p = Path(tmp) / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b'test')
            digest = hashlib.sha256(b'test').hexdigest()
            manifest=Path(tmp) / 'native/boot/attempt31b/source-sha256.txt'
            manifest.parent.mkdir()
            manifest.write_text(''.join(digest+'  '+name+'\n' for name in names))
            self.assertEqual(len(c.verify_sources()),64)
            (Path(tmp)/names[0]).write_bytes(b'changed')
            with self.assertRaisesRegex(c.Refusal,'source_digest'): c.verify_sources()
            manifest.write_text(digest+'  ../../outside\n')
            with self.assertRaisesRegex(c.Refusal,'manifest_path'): c.verify_sources()

    def test_complete_exact_scope(self):
        f = Fake(); ctl, journal, clock = controller(f)
        result = run(ctl)
        self.assertEqual(result['result'], 'CPU1_ENTRY_AND_REQUESTS_PASS')
        self.assertEqual(f.hw, [(0x280688004, 2), (0x280688008, 2)])
        self.assertEqual(f.events, 2)
        self.assertEqual(result['requests_completed'], 2)
        self.assertTrue(result['counter_progress_verified'])
        self.assertEqual(result['linux_boot'], 'NOT RUN')
        self.assertEqual(f.read64(BASE + 0x90a20), BASE + 0x178000)
        self.assertEqual(f.memory(BASE, 0x70000), c.relocated_text(IMAGE, BASE))
        self.assertEqual(journal[-1]['result'], result['result'])

    def test_once_even_after_refusal(self):
        for failure in (False, True):
            f = Fake(); f.bad_text = failure; ctl, _, _ = controller(f)
            try: run(ctl)
            except c.Refusal: pass
            before = list(f.writes)
            with self.assertRaisesRegex(c.Refusal, 'already_used'): run(ctl)
            self.assertEqual(f.writes, before)

    def test_code_mismatch_before_mutation(self):
        f = Fake(); f.bad_text = True; ctl, _, _ = controller(f)
        with self.assertRaisesRegex(c.Refusal, 'text_changed'): run(ctl)
        self.assertEqual(f.mutations, 0)

    def test_relocated_literals_are_checked_not_skipped(self):
        for offset in c.TEXT_RELOCS:
            f = Fake(); f.ram[offset] ^= 1; ctl, _, _ = controller(f)
            with self.subTest(offset=offset), self.assertRaisesRegex(c.Refusal, 'text_changed'): run(ctl)
            self.assertEqual(f.mutations, 0)

    def test_features_and_freshness_before_mutation(self):
        for offset in (0x1012d0, 0x7fba8, 0x90020, 0x90250, 0x90a10, 0x90a14,
                       0x90a18, 0x90a20):
            f = Fake(); f.ram[offset] ^= 1; ctl, _, _ = controller(f)
            with self.subTest(offset=offset), self.assertRaises(ValueError): run(ctl)
            self.assertEqual(f.mutations, 0)

    def test_guard_read_is_not_a_bulk_self_checksum(self):
        f = Fake(); f.put(0x11003c, '<I', 1); ctl, _, _ = controller(f)
        with self.assertRaisesRegex(c.Refusal, 'exception_or_guard'): run(ctl)
        self.assertEqual(f.hw, [])

    def test_secondary_fault_counter_retained(self):
        f = Fake(); f.trap_mutation = 10; ctl, _, _ = controller(f)
        with self.assertRaisesRegex(c.Refusal, 'exception_or_guard'): run(ctl)
        self.assertEqual(f.read32(BASE + 0x110038), 1)
        self.assertEqual(ctl.state['requests_completed'], 0)

    def test_allocation_ranges(self):
        for value in (0, BASE, HELPER_ADDR + 1, BASE + 0x800000, 1 << 48):
            f = Fake(); f.alloc = value; ctl, _, _ = controller(f)
            with self.subTest(value=value), self.assertRaisesRegex(c.Refusal, 'allocation_range'): run(ctl)
            self.assertEqual(f.writes, [])

    def test_helper_identity_checks_before_start(self):
        for name, value in (('bad_helper', True), ('return_el', 12), ('return_pfr', 0x1000),
                ('return_mpidr', 0x40001), ('return_part', 0x410f0680), ('return_sctlr', 0),
                ('bad_setup', True)):
            f = Fake(); setattr(f, name, value); ctl, _, _ = controller(f)
            with self.subTest(name=name), self.assertRaises(c.Refusal): run(ctl)
            self.assertFalse(f.hw)

    def test_every_mutation_fault_stops_without_retry(self):
        # 11 modeled mutations: allocation, code, caches, WFE, RAM setup,
        # two start writes and two request publications.
        for fail in range(1, 12):
            for kind in ('trap_mutation', 'fail_mutation'):
                f = Fake(); setattr(f, kind, fail); ctl, journal, _ = controller(f)
                with self.subTest(fail=fail, kind=kind), self.assertRaises((ValueError, TimeoutError)):
                    run(ctl)
                self.assertEqual(f.mutations, fail)
                self.assertEqual(journal[-1]['mutation_requests'], fail)
                self.assertLessEqual(len(f.hw), 2)
                before = list(f.writes)
                with self.assertRaises(c.Refusal): run(ctl)
                self.assertEqual(before, f.writes)

    def test_first_start_fault_prevents_second(self):
        f = Fake(); f.trap_mutation = 8; ctl, _, _ = controller(f)
        with self.assertRaises(c.Refusal): run(ctl)
        self.assertEqual(f.hw, [(0x280688004, 2)])

    def test_no_arrival_preserves_stack_and_timeout(self):
        f = Fake(); f.arrival = False; ctl, _, clock = controller(f)
        with self.assertRaisesRegex(c.Refusal, 'arrival_timeout'): run(ctl)
        self.assertLess(clock.now, 3.02)
        self.assertEqual(f.events, 0)
        self.assertEqual(f.read64(BASE + 0x90a20), BASE + 0x178000)
        # Late entry uses retained state; no cleanup or third write occurs.
        before = list(f.writes); f.enter()
        self.assertEqual(f.writes, before)

    def test_wrong_arrival_never_issues_request(self):
        for name in ('bad_mpidr', 'bad_stack', 'other_core'):
            f = Fake(); setattr(f, name, True); ctl, _, _ = controller(f)
            with self.subTest(name=name), self.assertRaises(c.Refusal): run(ctl)
            self.assertEqual(f.events, 0)

    def test_pending_request_never_reissued(self):
        f = Fake(); f.complete = False; ctl, _, clock = controller(f)
        with self.assertRaisesRegex(c.Refusal, 'request_timeout'): run(ctl)
        self.assertEqual(f.events, 1)
        self.assertEqual(ctl.state['requests_completed'], 0)
        self.assertLess(clock.now, 1.02)
        self.assertEqual(f.read64(BASE + 0x90260), BASE + 0x37f20)

    def test_counter_stall_is_not_success(self):
        f = Fake(); f.stale_timer = True; ctl, _, _ = controller(f)
        with self.assertRaisesRegex(c.Refusal, 'counter_not_progressing'): run(ctl)
        self.assertEqual(ctl.state['result'], 'STOP')

    def test_late_rpc_cannot_pass_expired_observation(self):
        for phase, delay in (('cpu1_arrival', 4), ('cpu1_requests', 2)):
            f = Fake(); ctl, _, clock = controller(f); original = f.call
            delayed = []
            def call(address, *args):
                result = original(address, *args)
                if ctl.state['phase'] == phase and not delayed and (
                        phase == 'cpu1_arrival' or address == (HELPER_ADDR | c.RX_ALIAS) + 160):
                    clock.now += delay
                    delayed.append(True)
                return result
            f.call = call
            with self.subTest(phase=phase), self.assertRaisesRegex(c.Refusal, 'timeout'):
                run(ctl)
            self.assertEqual(ctl.state['result'], 'STOP')
            self.assertLessEqual(f.events, 1)

    def test_public_output_has_no_addresses(self):
        import json
        ctl, _, _ = controller(Fake()); result = json.dumps(run(ctl))
        self.assertNotIn(str(BASE), result)
        self.assertNotIn('0x', result)

    def test_receipt_exclusive_and_symlink_refusal(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(c, 'ROOT', Path(tmp)):
            path = Path(tmp) / 'build/sub/receipt.jsonl'
            stream, journal = c.reserve(path)
            journal({'phase':'test'}); stream.close()
            with self.assertRaises(FileExistsError): c.reserve(path)
            (Path(tmp) / 'build/link').symlink_to(Path(tmp) / 'build/sub')
            with self.assertRaises(c.Refusal): c.reserve(Path(tmp) / 'build/link/other.jsonl')


if __name__ == '__main__':
    unittest.main()
