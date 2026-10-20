import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import observe28 as obs


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.put('sys/firmware/devicetree/base/compatible', b'apple,j716c\0apple,t6050\0')
        self.put('proc/cmdline', ' '.join(sorted(obs.REQUIRED)))
        self.put('proc/cpuinfo', 'CPU part : 0x053\nSerial : must-not-appear\n')
        self.put('sys/devices/system/cpu/online', '0')
        self.put('sys/devices/system/cpu/cpu0/of_node/reg', struct.pack('>Q', 0x40103))
        self.put('proc/sys/kernel/osrelease', 'test-kernel')

    def put(self, name, value):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(value if isinstance(value, bytes) else value.encode())

    def test_real_cpu_node_used_and_serial_excluded(self):
        ident = obs.identity(self.root)
        self.assertEqual((ident['cluster'], ident['core']), (1, 3))
        self.assertNotIn('Serial', ident['part_fields'])
        self.assertNotIn('must-not-appear', json.dumps(ident))

    def test_wrong_board_rejected(self):
        self.put('sys/firmware/devicetree/base/compatible', b'apple,j716c\0apple,t8103\0')
        with self.assertRaises(ValueError): obs.identity(self.root)

    def test_second_cpu_rejected(self):
        self.put('sys/devices/system/cpu/online', '0-1')
        with self.assertRaises(ValueError): obs.identity(self.root)

    def test_governor_and_idle_guards_required(self):
        for field in ('cpufreq.default_governor=userspace', 'idle=nop', 'nr_cpus=1'):
            self.put('proc/cmdline', ' '.join(sorted(obs.REQUIRED - {field})))
            with self.assertRaises(ValueError): obs.identity(self.root)

    def test_duplicate_guard_rejected(self):
        self.put('proc/cmdline', ' '.join(sorted(obs.REQUIRED)) + ' maxcpus=1')
        with self.assertRaises(ValueError): obs.identity(self.root)

    def test_unknown_cpu_refused(self):
        self.put('sys/devices/system/cpu/cpu0/of_node/reg', struct.pack('>Q', 0x100))
        with self.assertRaises(ValueError): obs.identity(self.root)

    def test_missing_telemetry_remains_null(self):
        s = obs.measurement.snapshot(self.root)
        self.assertIsNone(s['thermal_zones'])
        self.assertIsNone(s['power_watts'])

    def test_disabled_module_without_policy_is_observation(self):
        for k,v in [('ilinux_enable_writes','N'),('ilinux_max_pstate','0')]:
            self.put('sys/module/apple_soc_cpufreq/parameters/' + k, v)
        self.assertEqual(obs.driver_state(self.root), {})

    def test_writes_enabled_refused(self):
        self.put('sys/module/apple_soc_cpufreq/parameters/ilinux_enable_writes', 'Y')
        self.put('sys/module/apple_soc_cpufreq/parameters/ilinux_max_pstate', '3')
        with self.assertRaises(ValueError): obs.driver_state(self.root)

    def test_wrong_governor_refused(self):
        for k,v in [('ilinux_enable_writes','N'),('ilinux_max_pstate','0')]:
            self.put('sys/module/apple_soc_cpufreq/parameters/' + k, v)
        self.put('sys/devices/system/cpu/cpufreq/policy0/scaling_governor', 'schedutil')
        with self.assertRaises(ValueError): obs.driver_state(self.root)

    def test_asset_tamper_refused(self):
        names={'apple-soc-cpufreq.ko','cpubench','membench','chase_short','measurement.py','observe28.py'}
        for n in names: self.put(n, 'fixture')
        manifest={'attempt':28,'frequency_writes':False,'sha256':{n:hashlib.sha256(b'fixture').hexdigest() for n in names}}
        self.put('assets.json', json.dumps(manifest))
        obs.verify_assets(self.root)
        self.put('apple-soc-cpufreq.ko', 'changed')
        with self.assertRaises(ValueError): obs.verify_assets(self.root)

    def test_collect_explicit_no_write_and_no_retry(self):
        with patch.object(obs.os, 'geteuid', return_value=0), patch.object(obs,'identity',return_value={}), \
             patch.object(obs,'verify_assets',return_value={}), patch.object(Path,'exists',return_value=False), \
             patch.object(obs.os,'open',return_value=123), patch.object(obs.os,'close'), \
             patch.object(obs.os,'sched_setaffinity',create=True), patch.object(obs,'emit') as emitted, \
             patch.object(obs,'benchmarks') as benches, patch.object(obs.measurement,'snapshot',return_value={}), \
             patch.object(obs,'driver_state',return_value={}), patch.object(obs,'command',return_value=(0,'','')) as command:
            self.assertEqual(obs.collect(),0)
            self.assertEqual(command.call_args_list[0].args[0][-2:], ['ilinux_enable_writes=0','ilinux_max_pstate=0'])
            self.assertEqual(sum(c.args[0][0] == '/usr/bin/insmod' for c in command.call_args_list),1)
            benches.assert_called_once_with('before_module')
            self.assertEqual(emitted.call_args.kwargs['status'],'OBSERVED_NO_POLICY')


if __name__ == '__main__': unittest.main()
