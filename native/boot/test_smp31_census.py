import importlib.util
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

s = importlib.util.spec_from_file_location('census', Path(__file__).with_name('smp31_census.py'))
c = importlib.util.module_from_spec(s)
s.loader.exec_module(c)
BASE = 0x800000000
IMAGE = bytes(0x32000)


class Fake:
    def __init__(self):
        self.reads = []
        self.chip = 0x6050
        self.alive = False
        self.bad_code = False
        self.bad_info = False
        self.trap = False
        self.prior_fault = False
        self.values = [BASE | 1, BASE | 1]

    def nop(self): pass
    def get_chipid(self): return self.chip
    def get_base(self): return BASE
    def smp_is_alive(self, cpu): return self.alive and cpu == 1
    def read32(self, address):
        assert address == BASE + c.OFF['index']
        return 0
    def read64(self, address):
        self.reads.append(address)
        if address == BASE + c.OFF['mpidr']: return 0x80040000
        if address == BASE + c.OFF['start_base']: return 0x280688000
        assert address in c.RVBAR, 'unreviewed MMIO read'
        return self.values[c.RVBAR.index(address)]
    def get_exc_count(self):
        return int(self.prior_fault or self.trap and c.RVBAR[0] in self.reads)
    def readmem(self, address, size):
        if address == BASE + c.OFF['initialized']: return b'\x01'
        if address == BASE + c.OFF['info']:
            out = b''.join(struct.pack('<4B4xQ', 1, 0, i // 6, i % 6,
                    0x210050000 + (i // 6) * 0x1000000 + (i % 6) * 0x100000) for i in range(18))
            return (bytes(16) if self.bad_info else out[:16]) + out[16:] + bytes(14 * 16)
        assert (address - BASE, size) in ((0, 0x1000), (0x30000, 0x2000))
        return (b'X' if self.bad_code else b'\0') * size


def observe(f):
    with patch.object(c, 'verify_image'):
        return c.observe(f, f, IMAGE, metadata=lambda *_: None)


def topology():
    return [dict(id=i, reg=(i // 6) << 8 | i % 6,
                 impl=(0x210050000 + (i // 6) * 0x1000000 + (i % 6) * 0x100000, 0x9018),
                 state='running' if i == 0 else 'waiting', kind='M' if i < 12 else 'P') for i in range(18)]


class CensusTests(unittest.TestCase):
    def test_two_reads_only(self):
        f = Fake()
        result = observe(f)
        self.assertEqual([a for a in f.reads if a in c.RVBAR], list(c.RVBAR))
        self.assertEqual(result['cpu_starts'], 0)
        self.assertEqual(result['result'], 'CENSUS_COMPLETE_REVIEW_REQUIRED')

    def test_no_write_methods(self):
        # Fake deliberately implements no hardware/code/heap write or CPU-start API.
        observe(Fake())

    def test_refuse_before_mmio(self):
        for key, value in [('chip', 0x6051), ('alive', True), ('bad_code', True),
                           ('bad_info', True), ('prior_fault', True)]:
            f = Fake()
            setattr(f, key, value)
            with self.subTest(key=key), self.assertRaises(ValueError): observe(f)
            self.assertFalse(any(a in c.RVBAR for a in f.reads))

    def test_fault_stops_before_secondary(self):
        f = Fake()
        f.trap = True
        with self.assertRaises(ValueError): observe(f)
        self.assertNotIn(c.RVBAR[1], f.reads)

    def test_invalid_stops_before_secondary(self):
        f = Fake()
        f.values[0] = 0
        with self.assertRaises(ValueError): observe(f)
        self.assertNotIn(c.RVBAR[1], f.reads)

    def test_unknown_target_is_observation_not_permission(self):
        f = Fake()
        f.values[1] = 0x200000001
        result = observe(f)
        self.assertEqual(result['rows'][1]['target_relation'], 'outside-image')
        self.assertEqual(result['rows'][1]['image_offset'], hex(0x200000000 - BASE))
        self.assertEqual(result['cpu_starts'], 0)

    def test_unlocked_not_accepted_for_start(self):
        f = Fake()
        f.values[1] = BASE
        result = observe(f)
        self.assertFalse(result['rows'][1]['locked'])
        self.assertEqual(result['result'], 'CENSUS_COMPLETE_REVIEW_REQUIRED')

    def test_real_topology(self):
        c.validate_topology(['J716cAP'], topology(), [6, 0x60006, 0xc0006])

    def test_wrong_topology(self):
        for key, value in [('id', 0), ('reg', 9), ('impl', (0, 1)), ('state', 'running'), ('kind', 'P')]:
            cpus = topology()
            cpus[1][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                c.validate_topology(['J716cAP'], cpus, [6, 0x60006, 0xc0006])

    def test_wrong_cluster_stride(self):
        with self.assertRaises(ValueError):
            c.validate_topology(['J716cAP'], topology(), [4, 0x40004, 0x80004])

    def test_wrong_image(self):
        with self.assertRaises(ValueError): c.verify_image(IMAGE)


if __name__ == '__main__':
    unittest.main()
