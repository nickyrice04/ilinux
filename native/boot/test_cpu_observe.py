"""CPU-profile refusal tests, using the exact local boot042 package DT."""
import hashlib
import os
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import cpu_observe as cpu
import fdt
import launch
from test_ramroot import run_main, run_connect, run_session


class CpuObserveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base=Path(os.environ.get('ILINUX_BOOT042', str(HERE.parents[1]/'build/native-boot042/verified')))
        cls.package=base
        cls.base=(base/'t6050-j716c-stage-b.dtb').read_bytes()
        cls.candidate=cpu.prepare_dt(cls.base)

    def prepared(self):
        tree=cpu.fdtedit.parse(self.candidate)
        for n in tree.node('/cpus').children:
            if n.name.startswith('cpu@') and n.name != 'cpu@40000': n.set('status',b'disabled\0')
        n=tree.node('/chosen/framebuffer@0')
        n.set('status',b'okay\0'); n.set('reg',struct.pack('>QQ',0x10000000,640*480*4))
        for key,value in [('width',640),('height',480),('stride',2560)]: n.set(key,struct.pack('>I',value))
        n.set('format',b'x8r8g8b8\0')
        return tree

    def test_exact_delta(self):
        self.assertEqual(hashlib.sha256(self.candidate).hexdigest(),cpu.DT_SHA)
        fdt.check_stage_b(self.candidate,cpu_reference=self.candidate)

    def test_old_profile_still_rejects_candidate(self):
        with self.assertRaises(ValueError): fdt.check_stage_b(self.candidate)
        fdt.check_stage_b(self.base)

    def test_modified_base_refused(self):
        with self.assertRaises(ValueError): cpu.prepare_dt(self.base[:-1]+b'x')

    def test_prepared_tree_passes_all_common_guards(self):
        fdt.check_stage_b(cpu.fdtedit.encode(self.prepared()),True,self.candidate)

    def test_storage_still_disabled(self):
        t=self.prepared(); t.node('/soc/nvme@45dcc0000').set('status',b'okay\0')
        with self.assertRaises(ValueError): fdt.check_stage_b(cpu.fdtedit.encode(t),True,self.candidate)

    def test_opp_voltage_frequency_level_changes_rejected(self):
        for key in ('opp-hz','opp-level','opp-microvolt'):
            t=self.prepared(); n=t.node('/opp-table-0/opp01'); n.set(key,b'changed')
            with self.assertRaises(ValueError): fdt.check_stage_b(cpu.fdtedit.encode(t),True,self.candidate)

    def test_controller_reg_or_compat_changes_rejected(self):
        for key in ('reg','compatible','phandle'):
            t=self.prepared(); t.node(cpu.CONTROLLERS[0]).set(key,b'bad\0')
            with self.assertRaises(ValueError): fdt.check_stage_b(cpu.fdtedit.encode(t),True,self.candidate)

    def test_second_enabled_core_rejected(self):
        t=self.prepared(); t.node('/cpus/cpu@40001').set('status',b'okay\0')
        with self.assertRaises(ValueError): fdt.check_stage_b(cpu.fdtedit.encode(t),True,self.candidate)

    def test_wrong_policy_association_rejected(self):
        t=self.prepared(); t.node('/cpus/cpu@40000').set('performance-domains',b'xxxx')
        with self.assertRaises(ValueError): fdt.check_stage_b(cpu.fdtedit.encode(t),True,self.candidate)

    def test_untrusted_reference_refused(self):
        with self.assertRaises(ValueError): fdt.check_stage_b(self.candidate,cpu_reference=self.base)

    def test_exact_boot_arguments(self):
        p=launch.PROFILES['cpu-observe']
        self.assertEqual(p.bootargs, 'console=tty0 rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.default_governor=userspace pd_ignore_unused clk_ignore_unused quiet')
        self.assertEqual(p.confirm,'BOOT-J716C-CPU-OBSERVE-28')
        self.assertEqual(p.deadline,300)
        self.assertTrue(p.exact_append)

    def test_non_cpu_profile_arguments_unchanged(self):
        self.assertIn('cpufreq.off=1',launch.PROFILES['ramroot'].bootargs.split())
        self.assertIn('cpufreq.off=1',launch.PROFILES['omarchy'].bootargs.split())

    def test_requires_specific_confirmation_before_package_or_usb(self):
        for token in ('BOOT-J716C-RAM-ROOT', 'BOOT-J716C-OMARCHY-ROOT'):
            result, out, err, launches = run_main(launch, [
                '--package','/fake','--profile','cpu-observe','--ramroot','/fake/root',
                '--launch','--device','auto','--confirm',token])
            self.assertEqual((result,out,launches),('exit 2','',[]))
            self.assertIn('BOOT-J716C-CPU-OBSERVE-28',err[0])

    def test_operator_overlay_rejected_before_loading(self):
        result, out, err, launches = run_main(launch, [
            '--package','/fake','--profile','cpu-observe','--ramroot','/fake/root',
            '--operator-key','/fake/key.pub'])
        self.assertEqual((result,out,launches),('exit 2','',[]))
        self.assertIn('operator',err[0])

    def test_candidate_requires_paired_stage_one(self):
        result, out, err, launches = run_main(launch, [
            '--package','/fake','--profile','cpu-observe'])
        self.assertEqual((result,out,launches),('exit 2','',[]))
        self.assertIn('requires --ramroot',err[0])

    def test_bad_payload_refuses_before_first_proxy_request(self):
        log, _, error = run_session(launch, {}, launch.PROFILES['cpu-observe'])
        self.assertIsNotNone(error)
        self.assertEqual(log,[])

    def test_cpu_profile_deadline_and_transport_cleanup(self):
        alarms, message, opens, closed, _, restored = run_connect(launch, launch.PROFILES['cpu-observe'])
        self.assertEqual((alarms,len(opens),closed,restored),([300,0],1,True,['old']))
        self.assertIn('300 seconds',message)

    def payloads(self):
        candidates = [HERE.parents[1]/'build/attempt28/stage1.cpio.zst',
                      HERE.parents[1]/'virtualization/jobs/052-cpu-observation/out/stage1.cpio.zst']
        first = next((p for p in candidates if p.is_file()), None)
        if first is None: self.skipTest('the private attempt28 stage-one image is absent')
        return {'Image': (self.package/'Image').read_bytes(),
                't6050-j716c-stage-b.dtb': self.candidate,
                'ramroot.cpio.zst': first.read_bytes()}

    def test_exact_payload_reaches_one_fake_handoff(self):
        tree=self.prepared()
        p=launch.PROFILES['cpu-observe']
        tree.node('/chosen').set('bootargs',(p.bootargs+' idle=nop arm64.nowfxt').encode()+b'\0')
        log, _, error=run_session(launch, {'files':self.payloads(), 'tree':cpu.fdtedit.encode(tree)}, p)
        self.assertIsNone(error)
        self.assertEqual(len([row for row in log if row[:2]==('proxy','kboot_boot')]),1)

    def test_payload_mutation_prevents_proxy_contact(self):
        files=self.payloads(); files['ramroot.cpio.zst'] += b'x'
        log, _, error=run_session(launch, {'files':files}, launch.PROFILES['cpu-observe'])
        self.assertIn('payload digest differs',error)
        self.assertEqual(log,[])


class MemoryObserveTests(CpuObserveTests):
    # Inherit every DT/payload/refusal test, substituting only the profile under
    # test while production cpu-observe remains untouched.
    def setUp(self):
        self.original = launch.PROFILES['cpu-observe']
        launch.PROFILES['cpu-observe'] = launch.PROFILES['memory-observe']
    def tearDown(self):
        launch.PROFILES['cpu-observe'] = self.original
    def test_exact_boot_arguments(self):
        p=launch.PROFILES['memory-observe']
        self.assertEqual(p.bootargs,self.original.bootargs)
        self.assertEqual(p.confirm,'BOOT-J716C-MEMORY-OBSERVE-29')
        self.assertEqual(p.deadline,300)
    def test_requires_specific_confirmation_before_package_or_usb(self):
        result,out,err,launches=run_main(launch,[
            '--package','/fake','--profile','memory-observe','--ramroot','/fake/root',
            '--launch','--device','auto','--confirm','BOOT-J716C-CPU-OBSERVE-28'])
        self.assertEqual((result,out,launches),('exit 2','',[]))
        self.assertIn('BOOT-J716C-MEMORY-OBSERVE-29',err[0])


class DesktopLatencyTests(CpuObserveTests):
    # Inherit every DT/payload/refusal test, substituting only the profile under
    # test while production cpu-observe remains untouched.
    def setUp(self):
        self.original = launch.PROFILES['cpu-observe']
        launch.PROFILES['cpu-observe'] = launch.PROFILES['desktop-latency']
    def tearDown(self):
        launch.PROFILES['cpu-observe'] = self.original
    def test_exact_boot_arguments(self):
        p=launch.PROFILES['desktop-latency']
        self.assertEqual(p.bootargs,self.original.bootargs)
        self.assertEqual(p.confirm,'BOOT-J716C-DESKTOP-LATENCY-30')
        self.assertEqual(p.deadline,300)
    def test_requires_specific_confirmation_before_package_or_usb(self):
        result,out,err,launches=run_main(launch,[
            '--package','/fake','--profile','desktop-latency','--ramroot','/fake/root',
            '--launch','--device','auto','--confirm','BOOT-J716C-CPU-OBSERVE-28'])
        self.assertEqual((result,out,launches),('exit 2','',[]))
        self.assertIn('BOOT-J716C-DESKTOP-LATENCY-30',err[0])


if __name__ == '__main__': unittest.main()
