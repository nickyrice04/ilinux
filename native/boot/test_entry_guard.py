"""Bounded descriptor writes using synthetic framebuffer metadata only."""
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import entry_guard
import launch
from fdt import properties
from test_launcher import LauncherTests, prepared, FakeUtils


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.image = bytes(64) + entry_guard.MAGIC + bytes(16)
        self.tree = properties(prepared())
        self.fb = self.tree['/chosen/framebuffer@10000000']

    def test_descriptor(self):
        offset, data = entry_guard.plan(self.image, self.tree)
        self.assertEqual(offset, 80)
        self.assertEqual(struct.unpack('<QQ', data), (0x10000000, 2560))

    def test_marker_rejections(self):
        for image in (bytes(128), self.image * 2, b'x' + self.image,
                      self.image[:-1], self.image[:-1] + b'x'):
            with self.assertRaises(ValueError):
                entry_guard.descriptor_offset(image)

    def test_framebuffer_rejections(self):
        for key, val in [('format', b'r5g6b5\0'), ('stride', struct.pack('>I', 32772)),
                         ('width', struct.pack('>I', 100)), ('height', struct.pack('>I', 100)),
                         ('reg', struct.pack('>QQ', 0x10000001, 2560 * 480)),
                         ('reg', struct.pack('>QQ', 0x10000000, 256 * 1024**2 + 1))]:
            old = self.fb[key]; self.fb[key] = val
            with self.assertRaises(ValueError): entry_guard.plan(self.image, self.tree)
            self.fb[key] = old

    def test_single_write_readback_and_repeat_rejected(self):
        class Memory:
            data = bytes(16)
            writes = []
            def readmem(mem, address, size):
                self.assertEqual((address, size), (0x200050, 16))
                return mem.data
            def writemem(mem, address, data):
                mem.writes.append((address, data)); mem.data = data
        mem = Memory()
        plan = entry_guard.plan(self.image, self.tree)
        entry_guard.apply(mem, 0x200000, plan)
        self.assertEqual(len(mem.writes), 1)
        with self.assertRaisesRegex(ValueError, 'fresh boot'):
            entry_guard.apply(mem, 0x200000, plan)
        self.assertEqual(len(mem.writes), 1)

    def test_failed_readback(self):
        class Memory:
            def readmem(self, *args): return bytes(16)
            def writemem(self, *args): pass
        with self.assertRaisesRegex(ValueError, 'readback'):
            entry_guard.apply(Memory(), 0x200000, entry_guard.plan(self.image, self.tree))

    def test_guard_failure_blocks_handoff(self):
        fixture = LauncherTests(); fixture.setUp()
        with patch.object(launch.dapf_guard, 'prepare', return_value='plan'), \
             patch.object(launch.dapf_guard, 'apply'), \
             patch.object(launch.entry_guard, 'apply', side_effect=ValueError('readback')):
            with self.assertRaisesRegex(ValueError, 'readback'):
                launch.launch_session(fixture.iface, fixture.proxy, FakeUtils,
                                      fixture.manifest, fixture.files)
        self.assertFalse(fixture.proxy.boots)


if __name__ == '__main__': unittest.main(defaultTest='GuardTests')
