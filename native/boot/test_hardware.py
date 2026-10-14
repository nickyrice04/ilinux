"""Fail-closed tests of board-specific CPU/AIC/timer binding, with fake DTs."""
import copy
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fdt import properties, check_hardware
from test_launcher import prepared

class HardwareTests(unittest.TestCase):
    def setUp(self):
        self.tree = properties(prepared())
        self.aic = self.tree['/soc/interrupt-controller@280400000']
        self.timer = self.tree['/timer']
        self.cpu = self.tree['/cpus/cpu@40000']

    def reject(self, message):
        with self.assertRaisesRegex(ValueError, message):
            check_hardware(self.tree)

    def test_current_layout_passes(self):
        check_hardware(self.tree)

    def test_wrong_soc(self):
        self.tree['/']['compatible'] = b'apple,j716c\0apple,t6040\0'
        self.reject('chip')

    def test_wrong_aic_generation(self):
        self.aic['compatible'] = b'apple,t8122-aic3\0'
        self.reject('one t6050')

    def test_disabled_controller_or_ancestor(self):
        for path in ('/soc', '/soc/interrupt-controller@280400000'):
            self.tree[path]['status'] = b'disabled\0'
            self.reject('disabled')
            del self.tree[path]['status']

    def test_bad_aic_layout(self):
        self.aic['reg'] = struct.pack('>4Q', 0x280400000, 0x1cc000, 0x280450000, 0x4000)
        self.reject('layout')

    def test_bad_aic_address_translation(self):
        self.tree['/soc']['ranges'] = bytes(16)
        self.reject('translation')

    def test_bad_interrupt_cells(self):
        self.aic['#interrupt-cells'] = struct.pack('>I', 4)
        self.reject('malformed')

    def test_ambiguous_aic(self):
        self.tree['/soc/other'] = copy.deepcopy(self.aic)
        self.reject('one t6050')

    def test_ambiguous_phandle(self):
        self.cpu['phandle'] = self.aic['phandle']
        self.reject('ambiguous')

    def test_invalid_phandle(self):
        for value in (b'', bytes(4), b'\xff'*4):
            self.aic['phandle'] = value
            self.reject('phandle')

    def test_timer_parent_wrong(self):
        self.timer['interrupt-parent'] = struct.pack('>I', 1)
        self.reject('routed')

    def test_timer_host_and_guest_swapped(self):
        self.timer['interrupts'] = struct.pack('>12I', 1, 0, 4, 1, 1, 4, 1, 2, 4, 1, 3, 4)
        self.reject('routes')

    def test_timer_names_wrong(self):
        self.timer['interrupt-names'] = b'phys\0virt\0hyp-virt\0hyp-phys\0'
        self.reject('routes')

    def test_missing_disabled_or_duplicate_timer(self):
        self.timer['status'] = b'disabled\0'
        self.reject('one enabled')
        del self.timer['status']
        self.tree['/other-timer'] = self.timer.copy()
        self.reject('one enabled')
        del self.tree['/other-timer']
        del self.tree['/timer']
        self.reject('one enabled')

    def test_cpu_cells_wrong(self):
        self.tree['/cpus']['#address-cells'] = struct.pack('>I', 1)
        self.reject('encoding')

    def test_cpu_unknown_or_duplicate_mpidr(self):
        saved = self.cpu['reg']
        self.cpu['reg'] = struct.pack('>Q', 0x100)
        self.reject('topology')
        self.cpu['reg'] = saved
        self.tree['/cpus/cpu@40001'] = self.cpu.copy()
        self.reject('topology')

    def test_cpu_family_mismatch(self):
        self.cpu['compatible'] = b'apple,sotra-p\0'
        self.reject('topology')

    def test_other_observed_core_family_allowed(self):
        self.cpu['compatible'] = b'apple,sotra-p\0'
        self.cpu['reg'] = struct.pack('>Q', 0x10200)
        check_hardware(self.tree)

    def test_missing_or_malformed_cpu(self):
        self.cpu['reg'] = bytes(4)
        self.reject('malformed')
        del self.tree['/cpus/cpu@40000']
        self.reject('missing')

if __name__ == '__main__':
    unittest.main()
