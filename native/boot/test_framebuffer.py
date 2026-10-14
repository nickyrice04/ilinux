"""Dependency-free rejection tests for the Linux framebuffer observation gate."""
import copy
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fdt import properties, check_framebuffer
from test_launcher import prepared


class FramebufferTests(unittest.TestCase):
    def setUp(self):
        self.tree = properties(prepared())
        self.frame = self.tree['/chosen/framebuffer@10000000']

    def test_geometry_and_ranges_required(self):
        for key, value in [('width', bytes(4)), ('height', b''), ('stride', struct.pack('>I', 4)),
                           ('reg', struct.pack('>QQ', 1, 1)), ('reg', bytes(16)),
                           ('reg', struct.pack('>QQ', (1 << 64) - 1, 128)),
                           ('format', b'unknown\0')]:
            tree = copy.deepcopy(self.tree)
            tree['/chosen/framebuffer@10000000'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                check_framebuffer(tree, prepared=True)

    def test_compatible_is_a_token_not_substring(self):
        self.frame['compatible'] = b'unrelated-simple-framebuffer\0'
        with self.assertRaisesRegex(ValueError, 'expected one'):
            check_framebuffer(self.tree, prepared=True)

    def test_disabled_and_ambiguous_frames_rejected(self):
        self.frame['status'] = b'disabled\0'
        with self.assertRaisesRegex(ValueError, 'still disabled'):
            check_framebuffer(self.tree, prepared=True)
        self.frame.pop('status')
        self.tree['/chosen/framebuffer@20000000'] = dict(self.frame)
        with self.assertRaisesRegex(ValueError, 'expected one'):
            check_framebuffer(self.tree, prepared=True)

    def test_parent_address_encoding_required(self):
        for key in ('#address-cells', '#size-cells', 'ranges'):
            tree = copy.deepcopy(self.tree)
            tree['/chosen'].pop(key)
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'identity ranges'):
                check_framebuffer(tree, prepared=True)

    def test_offline_requires_disabled_zero_placeholder(self):
        with self.assertRaises(ValueError):
            check_framebuffer(self.tree)
        self.tree.pop('/chosen/framebuffer@10000000')
        self.tree['/chosen/framebuffer@0'] = {'compatible': b'simple-framebuffer\0',
                                            'reg': bytes(16), 'status': b'disabled\0'}
        check_framebuffer(self.tree)
        self.tree['/chosen/framebuffer@0']['status'] = b'okay\0'
        with self.assertRaisesRegex(ValueError, 'disabled with zero'):
            check_framebuffer(self.tree)


if __name__ == '__main__':
    unittest.main()
