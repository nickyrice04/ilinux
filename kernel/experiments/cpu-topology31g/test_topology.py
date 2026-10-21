import importlib.util,json
from pathlib import Path
import struct,unittest
spec=importlib.util.spec_from_file_location('topology',Path(__file__).with_name('topology.py'))
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)


def inputs():
    cpus=[dict(zip(t.KEYS,(i,((i//6)<<8)|(i%6),i//6,i//6,i%6))) for i in range(18)]
    acc=b''.join(struct.pack('<IBBBB',i+1,0,i,i%6,i//6) for i in range(18))
    return cpus,acc,2


class Topology(unittest.TestCase):
    def test_all_types_and_distinct_masks(self):
        rows=t.plan(*inputs())
        self.assertEqual([r['macos_class'] for r in rows].count('Performance'),12)
        self.assertEqual([r['macos_class'] for r in rows].count('Super'),6)
        self.assertEqual([r['die_start_mask'] for r in rows],[1<<i for i in range(18)])
        self.assertEqual(rows[1]['cluster_start_offset'],8)
        self.assertEqual([r['cpu_id'] for r in rows if not r['legacy_die_mask_matches']],list(range(6,18)))
    def test_cpu_order_does_not_select_wrong_core(self):
        cpus,acc,v=inputs();self.assertEqual(t.plan(cpus[::-1],acc,v),t.plan(cpus,acc,v))
    def test_no_fallback_for_missing_die_cluster(self):
        cpus,acc,v=inputs();del cpus[1]['die-cluster-id']
        with self.assertRaises(ValueError):t.plan(cpus,acc,v)
    def test_unique_die_id_rejected(self):
        cpus,acc,v=inputs();cpus[0]['die-id']=0
        with self.assertRaises(ValueError):t.plan(cpus,acc,v)
    def test_mutated_mapping_every_byte_refused(self):
        cpus,acc,v=inputs()
        for at in range(len(acc)):
            bad=bytearray(acc);bad[at]^=1
            with self.subTest(at=at),self.assertRaises(ValueError):t.plan(cpus,bytes(bad),v)
    def test_bad_count_types_and_version(self):
        cpus,acc,v=inputs()
        for args in ((cpus[:-1],acc,v),(cpus,acc[:-1],v),(cpus,acc,1),(cpus,acc,True)):
            with self.assertRaises(ValueError):t.plan(*args)
    def test_live_observation_agrees_with_model(self):
        data=json.loads((Path(__file__).resolve().parents[3]/'native/boot/attempt31g/topology-observation.json').read_text())
        self.assertEqual(data['startup_plan'],t.plan(*inputs()))


if __name__=='__main__':unittest.main()
