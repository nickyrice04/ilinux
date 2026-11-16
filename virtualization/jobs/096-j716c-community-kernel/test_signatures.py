#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import importlib.util
from pathlib import Path
import subprocess
import time
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('prepare096',Path(__file__).with_name('prepare.py'))
prepare=importlib.util.module_from_spec(spec);spec.loader.exec_module(prepare)
FPR='A'*40


def result(text,code=0):return subprocess.CompletedProcess([],code,text,'')


def status(extra='',trust='TRUST_FULLY',fingerprint=FPR,primary=None,hash_id='10'):
    return '[GNUPG:] NEWSIG\n'+extra+'[GNUPG:] GOODSIG '+fingerprint[-16:]+' PUBLIC_SYNTHETIC_SIGNER\n[GNUPG:] VALIDSIG '+fingerprint+' 2026-11-11 1794355200 0 4 0 1 '+hash_id+' 00 '+(primary or fingerprint)+'\n[GNUPG:] '+trust+'\n'


def key(fingerprint=FPR,validity='f',expires=0,kind='pub',capabilities='sc'):
    return ':'.join([kind,validity,'2048','1',fingerprint[-16:],'1600000000',str(expires),'','','','',capabilities])+':\nfpr:::::::::'+fingerprint+':\n'


class Signatures(unittest.TestCase):
    def verify(self,text,trust=True,keytext=None,code=0):
        with patch.object(prepare.subprocess,'run',side_effect=[result(text,code),result(keytext or key())]):
            return prepare.signature(Path('/OWN_SYNTHETIC_HOME'),Path('owned.sig'),Path('owned.tar'),trust)

    def test_unrelated_expired_trustdb_key_requires_current_actual_signer(self):
        observed=self.verify(status('[GNUPG:] KEYEXPIRED 1234567890\n'),keytext=key(expires=int(time.time())+3600))
        self.assertTrue(observed['selected_signer_current'])
        self.assertEqual(observed['unrelated_trustdb_expiry_notifications'],1)

    def test_expired_signature_key_status_still_refuses(self):
        with self.assertRaises(ValueError):self.verify(status('[GNUPG:] EXPKEYSIG AAAAAAAA\n'))

    def test_actual_signing_key_expiry_still_refuses(self):
        with self.assertRaises(ValueError):self.verify(status(),keytext=key(expires=1))

    def test_revoked_actual_key_still_refuses(self):
        with self.assertRaises(ValueError):self.verify(status(),keytext=key(validity='r'))

    def test_missing_full_keyring_trust_still_refuses(self):
        with self.assertRaises(ValueError):self.verify(status(trust='TRUST_UNDEFINED'))

    def test_bad_signature_or_process_failure_still_refuses(self):
        with self.assertRaises(ValueError):self.verify(status('[GNUPG:] BADSIG AAAAAAAA\n'))
        with self.assertRaises(ValueError):self.verify(status(),code=2)

    def test_nonunique_signature_still_refuses(self):
        with self.assertRaises(ValueError):self.verify(status()+'[GNUPG:] VALIDSIG '+FPR+'\n')

    def test_rust_pinned_key_is_distinct_from_existing_keyring_trust(self):
        fingerprint='108F66205EAEB0AAA8DD5E1C85AB96E6FA1BE5FE'
        observed=self.verify(status(trust='TRUST_UNDEFINED',fingerprint=fingerprint),False,key(fingerprint))
        self.assertEqual(observed['existing_keyring_trust'],'PINNED_OFFICIAL_RUST_KEY_ONLY')
        with self.assertRaises(ValueError):self.verify(status(trust='TRUST_UNDEFINED'),False)

    def test_current_signing_subkey_with_current_primary_is_valid(self):
        primary='B'*40
        observed=self.verify(status(primary=primary),keytext=key(primary)+key(kind='sub'))
        self.assertTrue(observed['selected_signer_current'])

    def test_expired_primary_or_expired_revoked_subkey_refuses(self):
        primary='B'*40
        for chain in (key(primary,expires=1)+key(kind='sub'),
                      key(primary)+key(kind='sub',expires=1),
                      key(primary)+key(kind='sub',validity='r')):
            with self.assertRaises(ValueError):self.verify(status(primary=primary),keytext=chain)

    def test_disabled_capability_flag_refuses_primary_and_subkey(self):
        with self.assertRaises(ValueError):self.verify(status(),keytext=key(capabilities='scD'))
        primary='B'*40
        with self.assertRaises(ValueError):self.verify(status(primary=primary),keytext=key(primary)+key(kind='sub',capabilities='sD'))

    def test_duplicate_selected_key_or_primary_refuses(self):
        with self.assertRaises(ValueError):self.verify(status(),keytext=key()+key())
        primary='B'*40
        with self.assertRaises(ValueError):self.verify(status(primary=primary),keytext=key(primary)+key(kind='sub')+key(kind='sub'))

    def test_weak_signature_hash_refuses(self):
        with self.assertRaises(ValueError):self.verify(status(hash_id='2'))


if __name__=='__main__':unittest.main(verbosity=2)
