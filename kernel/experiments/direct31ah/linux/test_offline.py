#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic format and policy rejection tests. No artifacts are executed."""
import gzip
import importlib.util
import struct
import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
def load(name):
    spec=importlib.util.spec_from_file_location(name,HERE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

config=load('check_config');dt=load('check_dtb');derivative=load('make_diag_dt')
fdt=load('fdt_read');ram=load('make_initramfs')

def tree():
    cpus=fdt.Node('cpus')
    for i,mpidr in enumerate(dt.EXPECTED):
        cpus.children.append(fdt.Node(f'cpu@{mpidr:x}',{
            'reg':struct.pack('>Q',mpidr),'cpu-release-addr':bytes(8),
            'enable-method':b'spin-table\0','capacity-dmips-mhz':struct.pack('>I',794 if i<12 else 1024)}))
    return fdt.Node('',{'compatible':b'apple,j716c\0apple,t6050\0'},[cpus,
        fdt.Node('nhi@1',{'compatible':b'apple,t6050-usb4-nhi\0','apple,thunderbolt-drom':b'synthetic-unit-drom'}),
        fdt.Node('nhi@2',{'compatible':b'apple,t6050-usb4-nhi\0','apple,thunderbolt-drom':b'\0'}),
        fdt.Node('sep@3',{'compatible':b'apple,t6050-sep\0'}),
        fdt.Node('usb@4',{'compatible':b'apple,t6050-dwc3\0'})])

def encoded(root=None):return fdt.encode(root or tree(),[(0x800000000,0x10000)],0)
def executable():
    data=bytearray(120);data[:6]=b'\x7fELF\x02\x01'
    struct.pack_into('<HH',data,16,2,183)
    struct.pack_into('<Q',data,32,64)
    struct.pack_into('<HHH',data,52,64,56,1)
    struct.pack_into('<2I6Q',data,64,1,5,0,0,0,120,120,4096)
    return data

class Configuration(unittest.TestCase):
    def base(self):
        c={s:'y' for s in config.REQUIRED_Y}
        c.update(NVME_APPLE='m',APPLE_SART='m',NR_CPUS='64')
        return c
    def test_resolved_profile(self):self.assertEqual(config.check(self.base()),[])
    def test_sep_write_driver_rejected(self):
        c=self.base();c['APPLE_SEP']='m';self.assertTrue(config.check(c))
    def test_builtin_storage_rejected(self):
        c=self.base();c['NVME_APPLE']='y';self.assertTrue(config.check(c))
    def test_missing_radio_dependency_rejected(self):
        c=self.base();c['RFKILL']='m';self.assertTrue(config.check(c))
    def test_small_cpu_limit_rejected(self):
        c=self.base();c['NR_CPUS']='16';self.assertTrue(config.check(c))
    def test_page_size_conflict_rejected(self):
        c=self.base();c['ARM64_4K_PAGES']='y';self.assertTrue(config.check(c))
    def test_duplicate_symbol_rejected(self):
        with self.assertRaises(ValueError):config.parse('CONFIG_SMP=y\nCONFIG_SMP=n')

class DeviceTree(unittest.TestCase):
    def test_exact_static_topology(self):
        r=dt.inspect(encoded());self.assertEqual(r['cpu_count'],18)
        self.assertEqual(r['cluster_core_types'],['M','M','P'])
        self.assertFalse(r['native_qualified'])
    def test_wrong_board_rejected(self):
        root=tree();root.props['compatible']=b'apple,j714c\0apple,t6050\0'
        with self.assertRaises(ValueError):dt.inspect(encoded(root))
    def test_disabled_core_rejected(self):
        root=tree();root.children[0].children[1].props['status']=b'disabled\0'
        with self.assertRaises(ValueError):dt.inspect(encoded(root))
    def test_mpidr_order_rejected(self):
        root=tree();root.children[0].children.reverse()
        with self.assertRaises(ValueError):dt.inspect(encoded(root))
    def test_release_width_rejected(self):
        root=tree();root.children[0].children[1].props['cpu-release-addr']=bytes(4)
        with self.assertRaises(ValueError):dt.inspect(encoded(root))
    def test_core_type_collapsing_rejected(self):
        root=tree();root.children[0].children[17].props['capacity-dmips-mhz']=struct.pack('>I',794)
        with self.assertRaises(ValueError):dt.inspect(encoded(root))
    def test_derivative_removes_drom_and_disables_sep(self):
        result,receipt=derivative.transform(encoded());root,_,_=fdt.parse(result)
        self.assertEqual(receipt['publisher_droms_removed'],1)
        self.assertEqual(receipt['placeholder_droms_removed'],1)
        self.assertFalse(any('apple,thunderbolt-drom' in n.props for _,n in fdt.walk(root)))
        self.assertEqual(root.children[3].props['status'],b'disabled\0')
        self.assertNotIn('status',root.children[4].props)
        self.assertEqual(dt.inspect(result)['cpu_count'],18)
    def test_missing_public_drom_rejected(self):
        root=tree();del root.children[1].props['apple,thunderbolt-drom']
        with self.assertRaises(ValueError):derivative.transform(encoded(root))
    def test_truncated_fdt_rejected(self):
        with self.assertRaises(ValueError):fdt.parse(encoded()[:-1])
    def test_region_overlap_rejected(self):
        data=bytearray(encoded());struct.pack_into('>I',data,12,56)
        with self.assertRaises(ValueError):fdt.parse(data)
    def test_reservation_overlap_rejected(self):
        data=bytearray(encoded());struct.pack_into('>I',data,16,72)
        with self.assertRaises(ValueError):fdt.parse(data)
    def test_bad_reservation_overflow_rejected(self):
        data=bytearray(encoded());struct.pack_into('>2Q',data,40,(1<<64)-1,16)
        with self.assertRaises(ValueError):fdt.parse(data)
    def test_duplicate_nodes_rejected(self):
        root=tree();root.children.append(fdt.Node('cpus'))
        with self.assertRaises(ValueError):fdt.parse(encoded(root))
    def test_nested_cpu_named_child_not_counted(self):
        root=tree();root.children[0].children[0].children.append(fdt.Node('extra'))
        self.assertEqual(dt.inspect(encoded(root))['cpu_count'],18)

class Initramfs(unittest.TestCase):
    def test_only_ram_whitelist_entries(self):
        data=gzip.decompress(ram.build(executable()));at=0;names=[]
        while at<len(data):
            self.assertEqual(data[at:at+6],b'070701')
            h=[int(data[at+6+i*8:at+14+i*8],16) for i in range(13)]
            size,namesize=h[6],h[11]
            name=data[at+110:at+110+namesize-1].decode();names.append(name)
            at=(at+110+namesize+3)&~3;at=(at+size+3)&~3
            if name=='TRAILER!!!':break
        self.assertEqual(names,['dev','proc','sys','run','init','TRAILER!!!'])
        self.assertEqual(ram.build(executable()),ram.build(executable()))
    def test_wrong_arch_rejected(self):
        data=executable();struct.pack_into('<H',data,18,62)
        with self.assertRaises(ValueError):ram.build(data)
    def test_dynamic_interpreter_rejected(self):
        data=executable();struct.pack_into('<I',data,64,3)
        with self.assertRaises(ValueError):ram.build(data)
    def test_missing_program_table_rejected(self):
        data=executable();struct.pack_into('<H',data,56,0)
        with self.assertRaises(ValueError):ram.build(data)
    def test_truncated_load_segment_rejected(self):
        data=executable();struct.pack_into('<Q',data,96,10000)
        with self.assertRaises(ValueError):ram.build(data)

if __name__=='__main__':unittest.main(verbosity=2)
