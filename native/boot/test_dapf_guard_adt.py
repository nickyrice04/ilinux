"""Pinned upstream parser plus synthetic ADT and actual RAM guard; no USB."""
import hashlib
import os
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(os.environ.get('M1N1_SOURCE', HERE.parents[1] / 'third_party/m1n1')) / 'proxyclient'))
from m1n1.adt import ADTNode, ADTNodeStruct
import dapf_guard as guard
from test_dapf_guard import Memory, fake_image


def tree(aop_types, decoded=False):
    def node(props, children=()):
        result = struct.pack('<II', len(props), len(children))
        for name, value in props.items():
            result += name.encode().ljust(32, b'\0') + struct.pack('<I', len(value))
            result += value + b'\0' * (-len(value) % 4)
        return result + b''.join(children)
    def dart(name, kinds):
        return node({'name': name.encode() + b'\0', 'compatible': b'dart,t8110\0',
                     'instance': b''.join(struct.pack('<4I', t, i, 0, 0) for t, i in kinds),
                     'reg': b''.join(struct.pack('<QQ', 0x10000000 + n * 0x4000, 0x4000)
                                     for n in range(len(kinds)))})
    props = {'name': b'arm-io\0', '#address-cells': struct.pack('<I', 2),
             '#size-cells': struct.pack('<I', 2)}
    if decoded: props['ranges'] = b''
    arm = node(props,
               (dart('dart-aop', aop_types), dart('dart-mtp', [(guard.DART, 0), (guard.DAPF, 0), (guard.GAPF, 0)])))
    return ADTNode(ADTNodeStruct.parse(node({'name': b'device-tree\0', 'compatible': b'J716cAP\0'}, (arm,))))


class PinnedGuardTests(unittest.TestCase):
    def test_real_parser_layout_and_ram_correction(self):
        for decoded in (False, True):
            adt = tree([(guard.DART, 0), (guard.GAPF, 0)], decoded=decoded)
            self.assertIsInstance(adt['/arm-io/dart-aop'].instance, bytes)
            self.assertEqual(guard.register_count(adt['/arm-io/dart-aop'].reg), 2)
            image = fake_image(); iface = Memory(image)
            with self.subTest(decoded=decoded), patch.object(guard, 'IMAGE_SHA256', hashlib.sha256(image).hexdigest()):
                plan = guard.prepare(iface, iface.base, image, adt)
                guard.apply(iface, plan)
            self.assertEqual(len(iface.writes), 1)

    def test_real_dapf_is_not_removed(self):
        image = fake_image(); iface = Memory(image)
        with patch.object(guard, 'IMAGE_SHA256', hashlib.sha256(image).hexdigest()), \
             self.assertRaisesRegex(ValueError, 'AOP layout'):
            guard.prepare(iface, iface.base, image, tree([(guard.DART, 0), (guard.DAPF, 0)]))
        self.assertFalse(iface.writes)


if __name__ == '__main__':
    unittest.main()
