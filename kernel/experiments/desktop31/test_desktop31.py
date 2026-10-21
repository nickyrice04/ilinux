#!/usr/bin/env python3
"""Offline refusals and cleanup contracts; no native execution."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch, Mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('copy31', HERE/'collect.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)

class EvidenceTests(unittest.TestCase):
    def test_positive(self):
        c.require_verified([{'parity':1,'gl_error':0},{'copies':42}])
    def test_missing_or_failed_evidence(self):
        for rows in ([], [{'parity':1}], [{'copies':42}], [{'parity':0},{'copies':42}],
                     [{'parity':1,'gl_error':1282},{'copies':42}],
                     [{'parity':1},{'copies':42},{'runtime_error':1282}]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                c.require_verified(rows)
    def test_mode_range(self):
        with patch.object(c.socket,'socket') as connect:
            for value in (-1,2,'1',None):
                with self.assertRaises(ValueError):c.set_mode('/unused',value)
            connect.assert_not_called()

class LifecycleTests(unittest.TestCase):
    def run_mocked(self, *, foreign=False, phase_error=False, consumed=False):
        identity = {'mpidr':'0x40000' if not foreign else '0x0','kernel':'7.1.9-g863199d8b4a3-dirty'}
        observe = types.SimpleNamespace(identity=lambda:identity,verify_assets=lambda:None)
        measurement = types.SimpleNamespace(snapshot=lambda:{'policies':[]})
        events, modes = [], []
        request = lambda ipc, cmd: ([{'width':3456,'height':2160,'scale':1,'transform':0,'currentFormat':'XRGB8888'}]
                                    if cmd=='j/monitors' else {'int':0})
        options = {'input:repeat_delay':{'int':1000},'debug:damage_tracking':{'int':2}}
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp);(home/'assets.json').write_text(json.dumps({'sha256':{'Hyprland-copy31':'a'*64}}))
            read_text = Path.read_text
            def text(p, *a, **kw):
                if str(p)=='/proc/mounts':return 'tmpfs /run tmpfs rw 0 0\n'
                return read_text(p,*a,**kw)
            with patch.dict(sys.modules, {'observe28':observe,'measurement':measurement}), \
                 patch.object(c,'HERE',home), patch.object(c,'digest',return_value='a'*64), \
                 patch.object(c.Path,'read_text',text), patch.object(c.os,'geteuid',return_value=0), \
                 patch.object(c.os,'open',side_effect=FileExistsError() if consumed else None,return_value=42) as opened, \
                 patch.object(c.os,'close'), patch.object(c.os,'sched_setaffinity',create=True), \
                 patch.object(c.signal,'signal'),patch.object(c.signal,'alarm'),patch.object(c.time,'sleep'), \
                 patch.object(c,'find_desktop',return_value=(123,Path('/fake'),{})), \
                 patch.object(c,'read_options',return_value=options),patch.object(c.base,'request',side_effect=request), \
                 patch.object(c.base,'clock_estimate'), \
                 patch.object(c.base,'phase',side_effect=TimeoutError('workload timeout') if phase_error else None) as phase, \
                 patch.object(c,'path_evidence',return_value=[{'parity':1},{'copies':42}]), \
                 patch.object(c,'set_mode',side_effect=lambda _,m:modes.append(m)), \
                 patch.object(c,'emit',side_effect=lambda event,**kw:events.append((event,kw))):
                result=c.main()
                return result,events,modes,opened.call_count,phase.call_count
    def test_success_crossover_and_restore(self):
        result,events,modes,opens,phases=self.run_mocked()
        self.assertEqual((result,opens,phases),(0,1,5))
        self.assertEqual(modes,[0,1,1,0,1,0,0])
        self.assertEqual(events[-1][1]['status'],'COPY31_OBSERVED')
    def test_timeout_restores_reference(self):
        result,events,modes,_,_=self.run_mocked(phase_error=True)
        self.assertEqual(result,3)
        self.assertEqual(modes,[0,0])
        self.assertEqual(events[-1][0],'reference_path_restored')
        self.assertFalse(any(e[0]=='done' for e in events))
    def test_foreign_identity_before_marker_or_switch(self):
        result,_,modes,opens,phases=self.run_mocked(foreign=True)
        self.assertEqual((result,modes,opens,phases),(3,[],0,0))
    def test_consumed_refuses_without_switch(self):
        result,_,modes,_,phases=self.run_mocked(consumed=True)
        self.assertEqual((result,modes,phases),(3,[],0))

if __name__=='__main__':unittest.main()
