# SPDX-License-Identifier: MIT
"""Exercise input substitution and false deployment-admission boundaries."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('community_stack', HERE / 'validate.py')
stack = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stack)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.value = stack.read_json(HERE / 'manifest.json')
        # Tests remain independent of the producer's mutable build-result slots.
        for name in ('kernel', 'aura_graphics_stage2', 'mesa'):
            self.value['components'][name]['local_artifacts'] = []
            self.value['components'][name]['build_status'] = 'INPUTS_VERIFIED'
        self.value['components'].pop('generic_stage1_candidate', None)

    def refuse(self, value):
        with self.assertRaises((stack.StackError, KeyError, TypeError, ValueError, OSError)):
            stack.validate(value)

    def test_pinned_reference_is_offline_only(self):
        result = stack.validate(self.value)
        self.assertTrue(result['manifest_valid'])
        self.assertFalse(result['native_ready'])
        self.assertFalse(result['restart_ready'])
        self.assertEqual(set(result['unmet_deployment_gates']), stack.GATES)

    def test_other_board_and_cpu_boolean_refused(self):
        for target in ({**stack.TARGET, 'board': 'J714s'},
                       {**stack.TARGET, 'gpu': 'G17S'},
                       {**stack.TARGET, 'physical_cpus': True}):
            with self.subTest(target=target):
                value = copy.deepcopy(self.value)
                value['target'] = target
                self.refuse(value)

    def test_reference_publication_cannot_be_replaced(self):
        value = copy.deepcopy(self.value)
        value['reference']['pins']['hardware']['board'] = 'J714s'
        self.refuse(value)

    def test_kernel_aura_mesa_and_config_substitutions_refused(self):
        for name, key in [('kernel', 'source_commit'), ('kernel', 'config_sha256'),
                          ('kernel', 'source_tree'), ('aura_graphics_stage2', 'source_commit'),
                          ('mesa', 'source_commit')]:
            with self.subTest(name=name, key=key):
                value = copy.deepcopy(self.value)
                value['components'][name][key] = '0' * len(value['components'][name][key])
                self.refuse(value)

    def test_kernel_modules_and_device_tree_cannot_be_split(self):
        value = copy.deepcopy(self.value)
        value['components']['kernel']['same_build_required'].remove('modules')
        self.refuse(value)

    def test_stage2_is_not_installed_stage1_proof(self):
        for name, key in [('aura_graphics_stage2', 'installed_stage1_identity_qualified'),
                          ('installed_stage1', 'generic_recipe_is_publisher_installed_identity')]:
            value = copy.deepcopy(self.value)
            value['components'][name][key] = True
            self.refuse(value)

    def test_generic_stage1_is_new_unenrolled_candidate_with_complete_outputs(self):
        generic = dict(repository='https://github.com/cameroncooper/aura',
                       source_commit=stack.AURA, enrolled=False,
                       publisher_installed_identity=False,
                       build_status='BUILD_PASS_OFFLINE', local_artifacts=[])
        for role in stack.REQUIRED_OUTPUTS['generic_stage1_candidate']:
            row = self.record(role)
            row['role'] = role
            generic['local_artifacts'].append(row)
        self.value['components']['generic_stage1_candidate'] = generic
        self.assertFalse(stack.validate(self.value)['native_ready'])
        for field in ('enrolled', 'publisher_installed_identity',
                      'firmware_acceptance_verified', 'watchdog_arming_qualified'):
            value = copy.deepcopy(self.value)
            value['components']['generic_stage1_candidate'][field] = True
            self.refuse(value)
        self.value['components']['generic_stage1_candidate']['local_artifacts'].pop()
        self.refuse(self.value)

    def test_pro_image_and_package_guard_cannot_substitute_max_guardian(self):
        for name, key, changed in [('userland', 'ready_image_eligible', True),
                                    ('userland', 'required_package_guard_board', 'J714s'),
                                    ('host_guardian', 'required', False),
                                    ('host_guardian', 'package_update_guard_is_not_host_guardian', False)]:
            value = copy.deepcopy(self.value)
            value['components'][name][key] = changed
            self.refuse(value)

    def test_old_firmware_and_original_update_assumption_refused(self):
        value = copy.deepcopy(self.value)
        value['firmware']['required']['mboot'] = '20457.1.29'
        self.refuse(value)
        for field in ('original_update_alone_qualifies_lab',
                      'matching_version_strings_alone_qualify_deployment'):
            value = copy.deepcopy(self.value)
            value['firmware']['qualification'][field] = True
            self.refuse(value)

    def test_native_or_update_claims_refused(self):
        for flag in ('native_ready', 'restart_ready', 'update_authorized'):
            value = copy.deepcopy(self.value)
            value[flag] = True
            self.refuse(value)
        value = copy.deepcopy(self.value)
        value['firmware']['update_authorized'] = True
        self.refuse(value)

    def test_unsafe_runtime_scope_or_parity_claim_refused(self):
        for field in ('shallow_wfi_default_enabled', 'rtc_runtime_dt_enabled',
                      'external_atc2_runtime_dt_enabled', 'suspend_and_deep_idle_qualified',
                      'usb_serial_or_ssh_qualified', 'macos_performance_or_power_parity_qualified'):
            value = copy.deepcopy(self.value)
            value['runtime_contract'][field] = True
            self.refuse(value)

    def test_cpu_ceiling_and_idle_opt_in_cannot_be_replaced(self):
        for field, changed in (('cpu_ceiling_profile', 'unbounded clocks'),
                               ('shallow_wfi_opt_in', 'always')):
            value = copy.deepcopy(self.value)
            value['runtime_contract'][field] = changed
            self.refuse(value)

    def test_missing_or_successfully_deployed_gate_refused(self):
        value = copy.deepcopy(self.value)
        value['deployment_gates'].pop()
        self.refuse(value)
        value = copy.deepcopy(self.value)
        value['deployment_gates'][0]['status'] = 'NATIVE_PASS'
        self.refuse(value)

    def test_build_pass_requires_artifact_record(self):
        self.value['components']['kernel']['build_status'] = 'BUILD_PASS_OFFLINE'
        self.refuse(self.value)

    def record(self, name='output.bin'):
        return dict(role='test-output', path=name, bytes=4,
                    sha256=hashlib.sha256(b'test').hexdigest(), scope='GENERIC_OFFLINE_ONLY')

    def test_artifact_bytes_checked_without_boot_admission(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'output.bin').write_bytes(b'test')
            self.value['components']['kernel'].update(local_artifacts=[self.record()])
            result = stack.validate(self.value, directory)
            self.assertEqual(result['artifact_records'], 1)
            self.assertFalse(result['native_ready'])
            (Path(directory) / 'output.bin').write_bytes(b'bad!')
            with self.assertRaises(stack.StackError):
                stack.validate(self.value, directory)

    def test_escaping_and_duplicate_artifact_records_refused(self):
        for name in ('/etc/passwd', '../secret', 'part/../secret', 'part//file', 'part\\file'):
            with self.subTest(name=name):
                self.value['components']['kernel']['local_artifacts'] = [self.record(name)]
                self.refuse(self.value)
        self.value['components']['kernel']['local_artifacts'] = [self.record(), self.record()]
        self.refuse(self.value)

    def test_build_pass_requires_complete_component_roles(self):
        for name, required in stack.REQUIRED_OUTPUTS.items():
            if name == 'generic_stage1_candidate':
                continue
            for missing in required:
                with self.subTest(component=name, missing=missing):
                    value = copy.deepcopy(self.value)
                    records = []
                    for role in required - {missing}:
                        record = self.record(role)
                        record['role'] = role
                        if role.endswith('.dtb'):
                            record['scope'] = 'PRIVATE_NOT_DEPLOYABLE'
                        records.append(record)
                    value['components'][name].update(build_status='BUILD_PASS_OFFLINE',
                                                     local_artifacts=records)
                    self.refuse(value)

    def test_raw_dtb_cannot_be_relabelled_generic(self):
        record = self.record('t6050-j716c.PRIVATE.dtb')
        record['role'] = 't6050-j716c.PRIVATE.dtb'
        self.value['components']['kernel']['local_artifacts'] = [record]
        self.refuse(self.value)

    def test_distinct_roles_cannot_reuse_one_path(self):
        a, b = self.record(), self.record()
        b['role'] = 'second-role'
        self.value['components']['kernel']['local_artifacts'] = [a, b]
        self.refuse(self.value)

    def test_leaf_and_parent_symlinks_and_nonregular_files_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / 'real').mkdir()
            (base / 'real' / 'output.bin').write_bytes(b'test')
            (base / 'alias').symlink_to(base / 'real', target_is_directory=True)
            (base / 'leaf').symlink_to(base / 'real' / 'output.bin')
            os.mkfifo(base / 'fifo')
            for name in ('alias/output.bin', 'leaf', 'fifo'):
                with self.subTest(name=name):
                    self.value['components']['kernel']['local_artifacts'] = [self.record(name)]
                    with self.assertRaises((stack.StackError, OSError)):
                        stack.validate(self.value, directory)

    def test_json_duplicate_keys_nonfinite_and_nonregular_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'
            for raw in (b'{"schema": 1, "schema": 2}', b'{"a": NaN}', b'{"a": Infinity}'):
                path.write_bytes(raw)
                with self.assertRaises(stack.StackError):
                    stack.read_json(path)
            path.unlink()
            os.mkfifo(path)
            with self.assertRaises(stack.StackError):
                stack.read_json(path)


if __name__ == '__main__':
    unittest.main()
