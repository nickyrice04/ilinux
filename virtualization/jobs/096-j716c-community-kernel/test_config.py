#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('config096',Path(__file__).with_name('check_config.py'))
config=importlib.util.module_from_spec(spec);spec.loader.exec_module(config)
BASE=b'''CONFIG_ARM64_16K_PAGES=y
CONFIG_SMP=y
CONFIG_RUST=y
CONFIG_DEBUG_INFO_NONE=y
CONFIG_LTO_NONE=y
CONFIG_LOCALVERSION="-j716c-bringup-unified"
CONFIG_PAHOLE_VERSION=131
CONFIG_DRM_ASAHI=m
'''


class Config(unittest.TestCase):
    def test_complete_identical_options_match(self):
        self.assertTrue(config.compare(BASE,BASE)['semantic_match'])

    def test_only_exact_link_and_unused_pahole_metadata_are_qualified(self):
        resolved=BASE.replace(b'CONFIG_PAHOLE_VERSION=131',b'CONFIG_PAHOLE_VERSION=132')+b'CONFIG_CC_CAN_LINK=y\n'
        result=config.compare(BASE,resolved)
        self.assertTrue(result['semantic_match']);self.assertEqual(len(result['qualified_metadata_exceptions']),2)
        self.assertFalse(result['byte_identical'])

    def test_pahole_diff_with_btf_or_dwarf_is_not_qualified(self):
        for extra in (b'CONFIG_DEBUG_INFO_BTF=y\n',b'CONFIG_DEBUG_INFO_DWARF5=y\n'):
            resolved=BASE.replace(b'CONFIG_PAHOLE_VERSION=131',b'CONFIG_PAHOLE_VERSION=132')+extra
            self.assertFalse(config.compare(BASE,resolved)['semantic_match'])

    def test_other_compiler_version_or_probe_changes_are_not_hidden(self):
        for extra in (b'CONFIG_CLANG_VERSION=230101\n',b'CONFIG_CC_CAN_LINK=n\n'):
            self.assertFalse(config.compare(BASE,BASE+extra)['semantic_match'])

    def test_missing_gpu_option_is_reported_as_substantive(self):
        result=config.compare(BASE,BASE.replace(b'CONFIG_DRM_ASAHI=m\n',b''))
        self.assertFalse(result['semantic_match']);self.assertEqual(result['substantive_differences'][0]['option'],'CONFIG_DRM_ASAHI')

    def test_duplicate_option_refuses(self):
        with self.assertRaises(ValueError):config.compare(BASE,BASE+b'CONFIG_SMP=n\n')


if __name__=='__main__':unittest.main(verbosity=2)
