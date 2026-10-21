import importlib.util,json
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('tracker',Path(__file__).with_name('tracker.py'))
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)


class Tracker(unittest.TestCase):
    def test_full_bounded_sequence(self):
        obj=t.Tracker();log=[]
        for phase in t.p.PHASES: obj.sample(phase,lambda cpu:0xff,lambda row:log.append(json.loads(json.dumps(row))))
        self.assertEqual(obj.reads_attempted,8);self.assertEqual(obj.reads_completed,8)
        self.assertEqual(log[0]['reads_attempted'],1);self.assertEqual(log[0]['reads_completed'],0)
        self.assertEqual(obj.report()['entry_execution'],'NOT_ESTABLISHED')
        with self.assertRaises(ValueError):obj.sample('final',lambda _:0,lambda _:None)
    def test_every_partial_failure_is_retained_and_terminal(self):
        for fail in range(1,9):
            obj=t.Tracker()
            def reader(cpu):
                if obj.reads_attempted==fail:raise TimeoutError('private')
                return 0xff
            with self.assertRaises(TimeoutError):
                for phase in t.p.PHASES:obj.sample(phase,reader,lambda _:None)
            self.assertEqual(obj.reads_attempted,fail);self.assertEqual(obj.reads_completed,fail-1)
            self.assertFalse(obj.rows[-1]['complete'])
            self.assertNotIn('private',json.dumps(obj.report()))
            with self.assertRaises(ValueError):obj.sample('final',reader,lambda _:None)
    def test_wrong_order_refused_before_io(self):
        obj=t.Tracker()
        with self.assertRaises(ValueError):obj.sample('final',lambda _:self.fail('read'),lambda _:None)
    def test_overwide_or_boolean_read_refused(self):
        for value in (1<<32,-1,True,None):
            obj=t.Tracker()
            with self.assertRaises(ValueError):obj.sample('before_start',lambda _:value,lambda _:None)
            self.assertEqual(obj.reads_completed,0)
    def test_keyboard_interrupt_retains_intent(self):
        obj=t.Tracker()
        def interrupt(_):raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):obj.sample('before_start',interrupt,lambda _:None)
        self.assertEqual(obj.reads_attempted,1);self.assertIsNotNone(obj.error)


if __name__=='__main__':unittest.main()
