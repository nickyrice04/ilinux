"""Host regressions use a small parser model; --real-parser runs in the VM."""
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import smp31c as c


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


t = load('old_tests', HERE / 'test_smp31b.py')
fx = load('fixture', HERE.parents[1] / 'kernel/experiments/smp31/memory_fixture31c.py')
REAL = '--real-parser' in sys.argv
if REAL:
    pos = sys.argv.index('--real-parser')
    sys.path.insert(0, sys.argv[pos + 1]); del sys.argv[pos:pos + 2]
else:
    # Host never executes downloaded code. A distinct VM run uses the actual
    # pinned parser on the same raw bytes and complete controller path.
    def parse_ba(data):
        return SimpleNamespace(revision=struct.unpack_from('<H', data)[0],
            virt_base=struct.unpack_from('<Q',data,8)[0],
            phys_base=struct.unpack_from('<Q',data,16)[0],
            mem_size=struct.unpack_from('<Q',data,24)[0],
            devtree=struct.unpack_from('<Q',data,96)[0],
            devtree_size=struct.unpack_from('<I',data,104)[0])
    def parse_adt(raw):
        # Only the independent fixture's chosen properties; rejects truncation.
        found={}
        for name in ('dram-base','dram-size'):
            needle=name.encode().ljust(32,b'\0') + struct.pack('<I',8)
            pos=raw.find(needle)
            if pos >= 0: found[name.replace('-','_')]=struct.unpack_from('<Q',raw,pos+36)[0]
        return {'/chosen':SimpleNamespace(**found)}
    tg=ModuleType('m1n1.tgtypes'); ad=ModuleType('m1n1.adt')
    tg.BootArgs_r2=SimpleNamespace(parse=parse_ba)
    tg.BootArgs_r3=SimpleNamespace(parse=parse_ba)
    ad.load_adt=parse_adt
    sys.modules.update({'m1n1':ModuleType('m1n1'), 'm1n1.tgtypes':tg, 'm1n1.adt':ad})


class Memory:
    def __init__(self, revision=3, phys=fx.PHYS, size=fx.DRAM_SIZE-0x8000):
        self.revision=revision; self.raw=fx.adt(); self.phys=phys
        self.ba=fx.bootargs(revision, phys, size)
        self.reads=[]
    def get_bootargs_rev(self): return fx.DRAM_BASE+0x10000, self.revision
    def readstruct(self, address, schema):
        assert address == fx.DRAM_BASE+0x10000
        return schema.parse(self.ba)
    def readmem(self, address, size):
        self.reads.append((address,size))
        assert (address,size)==(self.phys+fx.ADT_OFFSET,len(self.raw))
        return self.raw


class RamTests(unittest.TestCase):
    def test_old_bug_reproduced_and_new_parser_accepts_both_revisions(self):
        for revision in (2,3):
            f=Memory(revision)
            with self.subTest(revision=revision), self.assertRaisesRegex(c.Refusal,'ram_bounds'):
                c.core.ram_bounds(f,f)
            evidence={}
            self.assertEqual(c.read_bounds(f,f,evidence), (fx.PHYS,fx.PHYS+fx.DRAM_SIZE-0x8000))
            self.assertTrue(all(value is True for key,value in evidence.items() if key!='bootargs_revision'))
            self.assertEqual(evidence['bootargs_revision'],revision)

    def test_exact_bounds_and_carveout_preserved(self):
        for lo,size in ((fx.DRAM_BASE,fx.DRAM_SIZE),(fx.PHYS,0x800000)):
            self.assertEqual(c.validate_usable(lo,size,{}),(lo,lo+size))

    def test_bad_bounds_refused_before_adt_read(self):
        for phys,size in ((0x800000000,0x800000),(fx.DRAM_BASE-1,0x800000),
                (fx.DRAM_BASE+fx.DRAM_SIZE,0x4000),(fx.PHYS,fx.DRAM_SIZE),
                (fx.PHYS,0),(fx.PHYS,1<<64),(1<<64,1),(-1,1),(fx.PHYS,-1),
                (1<<42,0x4000),(True,0x800000),('bad',1)):
            with self.subTest(phys=phys,size=size), self.assertRaises(c.Refusal):
                c.validate_usable(phys,size,{})
        f=Memory(phys=0x800000000,size=0x800000)
        with self.assertRaisesRegex(c.Refusal,'within_machine_dram'): c.read_bounds(f,f,{})
        self.assertEqual(f.reads,[])

    def test_unknown_and_mismatched_revision(self):
        f=Memory(); f.revision=4
        with self.assertRaisesRegex(c.Refusal,'revision_supported'): c.read_bounds(f,f,{})
        f.revision=2
        with self.assertRaisesRegex(c.Refusal,'revision_consistent'): c.read_bounds(f,f,{})

    def test_adt_outside_usable_or_oversized_refused_before_read(self):
        for offset,value,fmt in ((96,fx.VIRT-8,'Q'),(96,fx.VIRT+fx.DRAM_SIZE,'Q'),
                                  (104,0,'I'),(104,2*1024**2+1,'I')):
            f=Memory(); data=bytearray(f.ba); struct.pack_into('<'+fmt,data,offset,value); f.ba=bytes(data)
            with self.subTest(offset=offset,value=value), self.assertRaisesRegex(c.Refusal,'adt_within_usable'):
                c.read_bounds(f,f,{})
            self.assertEqual(f.reads,[])

    def test_chosen_mismatch_or_missing_refused(self):
        for options in ({'base':0x800000000},{'size':fx.DRAM_SIZE//2},{'omit':'dram-base'},{'omit':'dram-size'}):
            f=Memory(); f.raw=fx.adt(**options); f.ba=fx.bootargs(adt_size=len(f.raw))
            with self.subTest(options=options), self.assertRaisesRegex(c.Refusal,'chosen_'): c.read_bounds(f,f,{})

    def test_short_adt_rejected(self):
        f=Memory(); read=f.readmem; f.readmem=lambda *args:read(*args)[:-1]
        with self.assertRaisesRegex(c.Refusal,'adt_read_complete'): c.read_bounds(f,f,{})

    def keep_patch(self, context):
        context.start(); self.addCleanup(context.stop)

    def high_controller(self):
        self.keep_patch(patch.object(t,'BASE',fx.DRAM_BASE+0x20000))
        self.keep_patch(patch.object(t,'HELPER_ADDR',fx.DRAM_BASE+0x420000))
        self.keep_patch(patch.object(c.core,'verify_local'))
        self.keep_patch(patch.object(c.core.census,'verify_image'))
        f=t.Fake(); mem=Memory()
        f.get_bootargs_rev=mem.get_bootargs_rev; f.readstruct=mem.readstruct
        oldread=f.readmem
        def read(address,size):
            if address == fx.PHYS+fx.ADT_OFFSET: return mem.readmem(address,size)
            return oldread(address,size)
        f.readmem=read
        clock=t.Clock(); journal=[]
        ctl=c.Controller(f,f,t.IMAGE,lambda state:journal.append(json.loads(json.dumps(state))),
                         clock=clock,sleep=clock.sleep,metadata=lambda *_:None)
        return f,mem,ctl,journal

    def test_complete_controller_at_m5_addresses_uses_real_bounds(self):
        f,mem,ctl,journal=self.high_controller()
        result=ctl.run()
        self.assertEqual(result['experiment'],'smp31c')
        self.assertEqual(result['result'],'CPU1_ENTRY_AND_REQUESTS_PASS')
        self.assertEqual(f.hw,[(0x280688004,2),(0x280688008,2)])
        self.assertEqual(result['mutation_requests'],11)
        self.assertEqual(result['requests_completed'],2)
        self.assertTrue(result['ram_check']['image_within_usable'])
        self.assertEqual(ctl.lo,fx.PHYS)  # Do not widen back to DRAM_BASE.
        self.assertNotIn('0x',json.dumps(result))
        self.assertNotIn(str(fx.DRAM_BASE),json.dumps(result))
        self.assertEqual(journal[-1],result)

    def test_bad_image_range_has_zero_mutations_and_specific_evidence(self):
        f,mem,ctl,journal=self.high_controller()
        mem.ba=fx.bootargs(phys=fx.DRAM_BASE+0x1000000,size=0x800000)
        mem.phys=fx.DRAM_BASE+0x1000000
        # ADT read address follows the changed boot-argument mapping.
        old=f.readmem
        f.readmem=lambda address,size:mem.readmem(address,size) if address==mem.phys+fx.ADT_OFFSET else old(address,size)
        with self.assertRaisesRegex(c.Refusal,'image_within_usable'): ctl.run()
        self.assertEqual(f.mutations,0)
        self.assertIs(journal[-1]['ram_check']['image_within_usable'],False)

    def test_high_address_first_write_failure_never_retries(self):
        f,mem,ctl,journal=self.high_controller(); f.trap_mutation=8
        with self.assertRaises(c.Refusal): ctl.run()
        self.assertEqual(f.hw,[(0x280688004,2)])
        with self.assertRaisesRegex(c.Refusal,'already_used'): ctl.run()

    def test_new_receipt_exclusive_and_does_not_reset_old(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(c,'ROOT',Path(tmp)):
            old=Path(tmp)/'build/native-intake/attempt31b/consumed.jsonl'
            old.parent.mkdir(parents=True); old.write_text('preserve')
            path=Path(tmp)/'build/native-intake/attempt31c/consumed.jsonl'
            stream,journal=c.reserve(path); stream.close()
            self.assertEqual(json.loads(path.read_text())['experiment'],'smp31c')
            with self.assertRaises(FileExistsError): c.reserve(path)
            self.assertEqual(old.read_text(),'preserve')
            (path.parent/'link').symlink_to(path.parent)
            with self.assertRaisesRegex(c.Refusal,'symlink'): c.reserve(path.parent/'link/other')


if __name__ == '__main__': unittest.main()
