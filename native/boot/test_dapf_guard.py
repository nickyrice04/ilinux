"""RAM data-workaround tests; only synthetic memory and ADT metadata."""
import contextlib
import hashlib
import io
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dapf_guard as guard
import launch
from test_launcher import FakeADT, FakeInterface, FakeProxy, FakeUtils, LauncherTests, prepared


def node(types):
    return SimpleNamespace(instance=b''.join(struct.pack('<4I', t, i, 0, 0) for t, i in types),
                           reg=[(0, 0x4000)] * len(types), compatible=['dart,t8110'])


def fake_image():
    image = bytearray(guard.TABLE_OFFSET + 96)
    for n, (path, index, offset) in enumerate(guard.ENTRIES):
        image[offset:offset + len(path) + 1] = path.encode() + b'\0'
        struct.pack_into('<QiI', image, guard.TABLE_OFFSET + n * 16, 0, index, 0)
    struct.pack_into('<QiI', image, guard.TABLE_OFFSET + 80, 0, -1, 0)
    return bytes(image)


class Memory(FakeInterface):
    def __init__(self, image, base=0x1000):
        super().__init__(prepared())
        self.image, self.base = bytearray(image), base
        self.drop_write = False
        for n, (_, _, offset) in enumerate(guard.ENTRIES):
            struct.pack_into('<Q', self.image, guard.TABLE_OFFSET + n * 16, base + offset)

    def readmem(self, address, size):
        if address == 0x1100 or address == 0x9000:
            return super().readmem(address, size)
        for start, data in reversed(self.writes):
            if start >= 0x200000 and start <= address and address + size <= start + len(data):
                return data[address - start:address - start + size]
        offset = address - self.base
        assert 0 <= offset and offset + size <= len(self.image)
        return bytes(self.image[offset:offset + size])

    def writemem(self, address, data):
        super().writemem(address, data)
        if address == self.base + guard.TABLE_OFFSET and not self.drop_write:
            self.image[guard.TABLE_OFFSET:guard.TABLE_OFFSET + len(data)] = data


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.image = fake_image()
        self.iface = Memory(self.image)
        self.adt = {
            '/arm-io/gpio0': FakeADT()['/arm-io/gpio0'],
            '/arm-io/dart-aop': node([(guard.DART, 0), (guard.GAPF, 0)]),
            '/arm-io/dart-mtp': node([(guard.DART, 0), (guard.DAPF, 0), (guard.GAPF, 0)]),
            '/arm-io/dart-isp0': node([(guard.DART, n) for n in range(5)] + [(guard.DAPF, 0), (guard.GAPF, 0)])}
        p = patch.object(guard, 'IMAGE_SHA256', hashlib.sha256(self.image).hexdigest())
        p.start(); self.addCleanup(p.stop)

    def plan(self):
        return guard.prepare(self.iface, self.iface.base, self.image, self.adt)

    def test_only_absent_aop_removed_one_bounded_write(self):
        before = bytes(self.iface.image)
        plan = self.plan()
        self.assertFalse(self.iface.writes)
        guard.apply(self.iface, plan)
        self.assertEqual(self.iface.writes, [(self.iface.base + guard.TABLE_OFFSET, plan.corrected)])
        self.assertEqual(before[:guard.TABLE_OFFSET], self.iface.image[:guard.TABLE_OFFSET])
        self.assertEqual(plan.corrected[:80], plan.original[16:])
        self.assertEqual(plan.corrected[80:], plan.original[80:])

    def test_unknown_image_stops(self):
        with self.assertRaisesRegex(ValueError, 'unsupported'):
            guard.prepare(self.iface, self.iface.base, b'unknown', self.adt)
        self.assertFalse(self.iface.writes)

    def test_register_encodings(self):
        self.assertEqual(guard.register_count(bytes(32)), 2)
        self.assertEqual(guard.register_count([1, 0x4000]), 1)
        self.assertEqual(guard.register_count([SimpleNamespace(addr=1, size=0x4000)]), 1)
        for value in (b'bad', b'', [], [1, 2, 3], None):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'encoding'):
                guard.register_count(value)

    def test_live_code_mismatch_stops(self):
        self.iface.image[guard.FUNCTION_START] ^= 1
        with self.assertRaisesRegex(ValueError, 'live code'): self.plan()

    def test_table_pointer_index_or_padding_mismatch_stops(self):
        for off in (0, 8, 12, 80, 88):
            self.iface = Memory(self.image)
            self.iface.image[guard.TABLE_OFFSET + off] ^= 1
            with self.subTest(off=off), self.assertRaisesRegex(ValueError, 'table changed'):
                self.plan()
            self.assertFalse(self.iface.writes)

    def test_live_path_mismatch_stops(self):
        self.iface.image[guard.ENTRIES[0][2]] ^= 1
        with self.assertRaisesRegex(ValueError, 'entry name'): self.plan()

    def test_aop_with_real_dapf_is_not_omitted(self):
        self.adt['/arm-io/dart-aop'] = node([(guard.DART, 0), (guard.DAPF, 0)])
        with self.assertRaisesRegex(ValueError, 'AOP layout'): self.plan()
        self.assertFalse(self.iface.writes)

    def test_aop_absent_or_metadata_missing_stops(self):
        self.adt.pop('/arm-io/dart-aop')
        with self.assertRaisesRegex(ValueError, 'AOP node absent'): self.plan()
        self.adt['/arm-io/dart-aop'] = SimpleNamespace()
        with self.assertRaisesRegex(ValueError, 'metadata absent'): self.plan()

    def test_malformed_and_duplicate_or_moved_dapf_stops(self):
        for types in [[(guard.DART, 0), (guard.GAPF, 0)],
                      [(guard.DAPF, 0), (guard.DAPF, 0)],
                      [(guard.DAPF, 0), (guard.DART, 0)]]:
            self.adt['/arm-io/dart-mtp'] = node(types)
            with self.subTest(types=types), self.assertRaisesRegex(ValueError, 'separate review'):
                self.plan()
        self.adt['/arm-io/dart-mtp'].instance = b'bad'
        with self.assertRaisesRegex(ValueError, 'malformed'): self.plan()

    def test_changed_table_before_apply_stops_without_write(self):
        plan = self.plan()
        self.iface.image[guard.TABLE_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, 'before correction'): guard.apply(self.iface, plan)
        self.assertFalse(self.iface.writes)

    def test_failed_readback_stops(self):
        plan = self.plan(); self.iface.drop_write = True
        with self.assertRaisesRegex(ValueError, 'readback failed'): guard.apply(self.iface, plan)

    def test_second_application_requires_fresh_boot(self):
        guard.apply(self.iface, self.plan())
        with self.assertRaisesRegex(ValueError, 'fresh boot'): self.plan()

    def test_full_launcher_correction_before_handoff(self):
        f = LauncherTests(); f.setUp()
        f.files['m1n1.bin'] = self.image
        def factory(proxy):
            u = FakeUtils(proxy)
            class ADT(dict): compatible = ['J716cAP']
            u.adt = ADT(self.adt)
            return u
        with contextlib.redirect_stdout(io.StringIO()):
            launch.launch_session(self.iface, f.proxy, factory, f.manifest, f.files)
        self.assertEqual(len(f.proxy.boots), 1)
        self.assertEqual(len(self.iface.writes), 5)
        self.assertEqual(self.iface.writes[-2][0], self.iface.base + guard.TABLE_OFFSET)
        self.assertEqual(self.iface.writes[-1][0], 0x200050)

    def test_full_launcher_failure_does_not_handoff(self):
        f = LauncherTests(); f.setUp(); f.files['m1n1.bin'] = self.image
        def factory(proxy):
            u = FakeUtils(proxy)
            class ADT(dict): compatible = ['J716cAP']
            u.adt = ADT(self.adt)
            return u
        self.iface.drop_write = True
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, 'readback failed'):
            launch.launch_session(self.iface, f.proxy, factory, f.manifest, f.files)
        self.assertEqual(f.proxy.boots, [])

    def test_prepared_dt_rejection_leaves_table_untouched(self):
        f = LauncherTests(); f.setUp(); f.files['m1n1.bin'] = self.image
        self.iface.tree = prepared(storage=True)
        def factory(proxy):
            u = FakeUtils(proxy)
            class ADT(dict): compatible = ['J716cAP']
            u.adt = ADT(self.adt)
            return u
        before = bytes(self.iface.image)
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, 'storage'):
            launch.launch_session(self.iface, f.proxy, factory, f.manifest, f.files)
        self.assertEqual(len(self.iface.writes), 3)
        self.assertEqual(bytes(self.iface.image), before)
        self.assertEqual(f.proxy.boots, [])

    def test_layout_rejection_prevents_any_upload(self):
        f = LauncherTests(); f.setUp(); f.files['m1n1.bin'] = self.image
        self.adt['/arm-io/dart-aop'] = node([(guard.DART, 0), (guard.DAPF, 0)])
        def factory(proxy):
            u = FakeUtils(proxy)
            class ADT(dict): compatible = ['J716cAP']
            u.adt = ADT(self.adt)
            return u
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, 'AOP layout'):
            launch.launch_session(self.iface, f.proxy, factory, f.manifest, f.files)
        self.assertFalse(self.iface.writes)
        self.assertFalse(f.proxy.boots)


if __name__ == '__main__':
    unittest.main(defaultTest='GuardTests')
