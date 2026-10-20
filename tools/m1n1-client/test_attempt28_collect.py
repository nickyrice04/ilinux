import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('collector',Path(__file__).with_name('attempt28-collect.py'))
c=importlib.util.module_from_spec(spec); spec.loader.exec_module(c)


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.raw=b'synthetic public key fixture'
        self.fp='SHA256:'+base64.b64encode(hashlib.sha256(self.raw).digest()).decode().rstrip('=')
        self.root='[12] sh[123]: 256 '+self.fp+' ilinux-m5-boot (ED25519)'
        self.known='m5-omarchy ssh-ed25519 '+base64.b64encode(self.raw).decode()+'\n'
        self.stage='[2] sh[42]: 256 SHA256:'+'A'*43+' ilinux-m5-stage1 (ED25519)'

    def test_root_selected_from_retained_journal(self): c.verify_key(self.stage+'\n'+self.root,self.known)
    def test_stage_one_alone_refused(self):
        with self.assertRaises(ValueError): c.verify_key(self.stage,self.known)
    def test_ambiguous_root_refused(self):
        with self.assertRaises(ValueError): c.verify_key(self.root+'\n'+self.root.replace(self.fp,'SHA256:'+'B'*43),self.known)
    def test_wrong_known_key_refused(self):
        with self.assertRaises(ValueError): c.verify_key(self.root,self.known.replace(base64.b64encode(self.raw).decode(),base64.b64encode(b'wrong').decode()))
    def test_wrong_host_alias_refused(self):
        with self.assertRaises(ValueError): c.verify_key(self.root,self.known.replace('m5-omarchy','m5'))
    def test_reused_stage_key_refused(self):
        with self.assertRaises(ValueError): c.verify_key(self.root+'\n'+self.root.replace('ilinux-m5-boot','ilinux-m5-stage1'),self.known)
    def test_repeated_same_root_event_ok(self): c.verify_key(self.root+'\n'+self.root,self.known)
    def test_deadline_counts_from_switch(self): self.assertEqual(c.remaining({'attempt':28,'start_monotonic':100},130),570)
    def test_expired_future_and_wrong_attempt_refused(self):
        for state,now in [({'attempt':28,'start_monotonic':100},700),({'attempt':28,'start_monotonic':100},99),({'attempt':27,'start_monotonic':100},120)]:
            with self.assertRaises(ValueError): c.remaining(state,now)

    def test_key_mismatch_prevents_ssh_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); b=root/'build'; (b/'control').mkdir(parents=True)
            (b/'state').write_text(json.dumps({'attempt':28,'start_monotonic':100}))
            (b/'journal').write_text(self.root)
            (b/'control/known_hosts-omarchy').write_text(self.known.replace('m5-omarchy','wrong'))
            with patch.object(c,'ROOT',root), patch.object(c.time,'monotonic',return_value=110), patch.object(c.subprocess,'Popen') as popen:
                with self.assertRaisesRegex(ValueError,'known-host entry'):
                    c.main(['cpu','--state',str(b/'state'),'--journal',str(b/'journal'),'--output',str(b/'out')])
                popen.assert_not_called()
                self.assertFalse((b/'out').exists())

    def test_window_cannot_be_rearmed(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(c,'ROOT',Path(tmp).resolve()):
            state=str(Path(tmp)/'build/state')
            self.assertEqual(c.main(['arm','--state',state]),0)
            with self.assertRaises(FileExistsError): c.main(['arm','--state',state])


if __name__ == '__main__': unittest.main()
