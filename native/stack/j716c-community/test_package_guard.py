# SPDX-License-Identifier: MIT
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('guard', HERE / 'package_guard.py')
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)
J716C = b'apple,j716c\0apple,t6050\0apple,arm-platform\0'


class GuardTests(unittest.TestCase):
    def test_ordinary_software_transaction_remains_available(self):
        self.assertTrue(guard.evaluate('packages', b'git\nfirefox\npython\n', J716C)[0])
        self.assertTrue(guard.evaluate('paths', b'usr/bin/git\netc/gitconfig\n', J716C)[0])

    def test_critical_package_replacements_and_removals_refuse(self):
        for name in ('linux-aurora', 'linux', 'm1n1-aurora', 'aura', 'uboot-aurora',
                     'u-boot-aurora', 'limine', 'mkinitcpio', 'dracut', 'linux-firmware',
                     'asahi-firmware', 'asahi-scripts', 'omarchy-aurora-firmware', 'mesa-aurora',
                     'vulkan-aurora', 'vulkan-icd-loader', 'hyprland'):
            with self.subTest(name=name):
                self.assertEqual(guard.evaluate('packages', (name+'\n').encode(), J716C),
                                 (False, 'MATCHED_STACK_FROZEN_REPLACEMENT_REQUIRES_REVIEW'))

    def test_renamed_packages_cannot_replace_protected_files(self):
        for name in ('boot/m1n1/boot-ctxr.bin', 'boot/Image.gz',
                     'usr/lib/modules/7.3.0-j716c/kernel/drivers/gpu/asahi.ko',
                     'usr/lib/firmware/apple/gpu.bin', 'usr/lib/dri/asahi_dri.so',
                     'usr/lib/asahi-boot/m1n1.bin',
                     'usr/share/vulkan/icd.d/asahi_icd.aarch64.json',
                     'usr/share/glvnd/egl_vendor.d/50_mesa.json',
                     'usr/lib/libEGL.so.1', 'usr/lib/libGLX.so', 'usr/lib/libgbm.so.1',
                     'usr/lib/libvulkan.so.1', 'usr/lib/libgallium-26.3.so',
                     'usr/bin/Hyprland', 'usr/bin/update-m1n1'):
            with self.subTest(name=name):
                self.assertFalse(guard.evaluate('paths', (name+'\n').encode(), J716C)[0])

    def test_unreadable_pro_or_ambiguous_board_never_falls_back_to_max(self):
        for raw in (b'', b'apple,j714s\0apple,t6050\0', b'apple,j716c\0',
                    b'apple,j716c\0apple,t6050\0apple,j714s\0', J716C+J716C,
                    J716C[:-1], J716C+b'\0', b'x'*8193):
            with self.subTest(raw=raw[:40]):
                self.assertFalse(guard.board_qualified(raw))
                self.assertEqual(guard.evaluate('packages', b'linux-aurora\n', raw),
                                 (False, 'EXACT_J716C_BOARD_NOT_QUALIFIED'))

    def test_empty_transaction_does_not_require_device_tree(self):
        self.assertEqual(guard.evaluate('packages', b'', b''), (True, 'NO_PINNED_STACK_CHANGE'))

    def test_malformed_or_oversized_hook_input_refuses(self):
        for raw in (b'linux-aurora\0', b'\xff', b'\n', b'x'*1025, b'x'*(1024*1024+1)):
            self.assertFalse(guard.evaluate('packages', raw, J716C)[0])
        for raw in (b'/boot/Image.gz\n', b'boot/../Image.gz\n', b'boot//Image.gz\n'):
            self.assertFalse(guard.evaluate('paths', raw, J716C)[0])

    def test_environment_cannot_supply_test_board_or_override(self):
        env = {**os.environ, 'M5_GUARD_TEST': '1', 'M5_DT_COMPATIBLE': 'apple,j716c',
               'M5_ROOT': '/tmp', 'ILINUX_ALLOW_UPDATE': '1'}
        run = subprocess.run([sys.executable, '-I', str(HERE/'package_guard.py'), 'packages'],
                             input=b'linux-aurora\n', capture_output=True, env=env)
        self.assertEqual(run.returncode, 1)
        self.assertNotIn(b'"allowed": true', run.stderr)

    def test_invalid_invocation_refuses_before_board_read(self):
        run = subprocess.run([sys.executable, '-I', str(HERE/'package_guard.py'), '--allow'],
                             input=b'', capture_output=True)
        self.assertEqual(run.returncode, 1)
        self.assertIn(b'INVALID_INVOCATION', run.stderr)


if __name__ == '__main__':
    unittest.main()
