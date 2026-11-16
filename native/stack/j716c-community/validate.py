#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate pinned stack data; never build, install, probe or authorize a boot."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat

SCHEMA = 'ilinux-j716c-community-stack-v1'
REFERENCE_DIGEST = 'c9edc854672e27347f58b58c4d2098e0df86d545bd33b144c8a3160aca16cc00'
PUBLICATION = '5e11068a1c6d8fccb155bc6e0159cc16107e53ec'
KERNEL = 'a59e709c737777495c84541c6afb6c862bb79227'
TREE = '5960d8ab03fef0f87e91e84fe1a8d969173da8de'
CONFIG = '3c11e751cb6d6e0358429230d28121c7f383aa5437a2e0b7d181b85f6dd7dbe8'
AURA = '9da61857f9d9262bd64c023fbc1b18315b12d0af'
MESA = '10161a78e60e4057257e116d404a92bd9b78bb3c'
TARGET = dict(model='Mac17,6', board='J716c', soc='T6050', gpu='G17C', physical_cpus=18)
FIRMWARE = dict(os_version='27.2.1', os_build='26B131', mboot='20457.41.3')
BUILD_STATES = {'PENDING', 'INPUTS_VERIFIED', 'BUILD_PASS_OFFLINE',
                'BUILD_FAILED', 'PARTIAL_BUILD_OFFLINE', 'BLOCKED_TOOLCHAIN', 'BLOCKED_INPUTS'}
REQUIRED_OUTPUTS = {
    'kernel': {'Image', 'Image.gz', 'kernel.config', 'modules.PRIVATE.tar.gz',
               't6050-j716c.PRIVATE.dtb'},
    'aura_graphics_stage2': {'graphics-stage2.aura.bin', 'graphics-stage2.aura-boot.macho'},
    'mesa': {'mesa-destdir.tar.gz', 'mesa-testlog.json'},
    'generic_stage1_candidate': {'stage1.aura-boot-128m.macho', 'stage1.aura-boot.macho',
                                 'stage1.padding.json'},
}
GATES = {'exact_board_source_stack', 'matched_offline_build_and_modules',
         'firmware_transition_and_lab_refresh_plan', 'matched_installed_stage1_identity_and_recipe',
         'host_watchdog_guardian_and_recovery', 'j716c_userland_and_package_update_guards',
         'concrete_kit_manual_rescue_and_owner_approval', 'native_cpu_gpu_network_and_storage_validation'}
SHA256 = re.compile(r'[0-9a-f]{64}')
MAX_JSON = 2 * 1024 * 1024


class StackError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise StackError(reason)


def unique(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, 'DUPLICATE_JSON_KEY')
        out[key] = value
    return out


def read_json(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= MAX_JSON, 'JSON_BOUND')
        chunks = []
        remaining = MAX_JSON + 1
        while remaining:
            data = os.read(fd, min(65536, remaining))
            if not data:
                break
            chunks.append(data)
            remaining -= len(data)
        raw = b''.join(chunks)
        after = os.fstat(fd)
        require(len(raw) == before.st_size and len(raw) <= MAX_JSON, 'JSON_CHANGED')
        require((before.st_mtime_ns, before.st_ctime_ns, before.st_size) ==
                (after.st_mtime_ns, after.st_ctime_ns, after.st_size), 'JSON_CHANGED')
        return json.loads(raw, object_pairs_hook=unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(StackError('JSON_NONFINITE')))
    finally:
        os.close(fd)


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def open_artifact(root, name):
    """Open relative components without following symlinks, including parents."""
    base = Path(root).resolve(strict=True)
    directory = os.open(base, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        parts = name.split('/')
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=directory)
            os.close(directory)
            directory = child
        return os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                       dir_fd=directory)
    finally:
        os.close(directory)


def check_artifacts(component, root=None, required_roles=()):
    records = component['local_artifacts']
    require(isinstance(records, list) and len(records) <= 64, 'ARTIFACT_LIST')
    require(component['build_status'] in BUILD_STATES, 'BUILD_STATUS')
    if component['build_status'] == 'BUILD_PASS_OFFLINE':
        require(bool(records), 'BUILD_WITHOUT_ARTIFACTS')
    roles, paths = set(), set()
    for item in records:
        require(isinstance(item, dict) and set(item) ==
                {'role', 'path', 'bytes', 'sha256', 'scope'}, 'ARTIFACT_SCHEMA')
        require(isinstance(item['role'], str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', item['role'])
                and item['role'] not in roles, 'ARTIFACT_ROLE')
        roles.add(item['role'])
        require(type(item['bytes']) is int and 0 < item['bytes'] <= 16 * 1024**3, 'ARTIFACT_SIZE')
        require(isinstance(item['sha256'], str) and SHA256.fullmatch(item['sha256']), 'ARTIFACT_DIGEST')
        require(item['scope'] in ('GENERIC_OFFLINE_ONLY', 'PRIVATE_NOT_DEPLOYABLE'), 'ARTIFACT_SCOPE')
        if item['role'] == 't6050-j716c.PRIVATE.dtb':
            require(item['scope'] == 'PRIVATE_NOT_DEPLOYABLE', 'RAW_DTB_SCOPE')
        name = item['path']
        require(isinstance(name, str) and name and not name.startswith('/') and
                all(part not in ('', '.', '..') for part in name.split('/')) and '\\' not in name,
                'ARTIFACT_PATH')
        require(name not in paths, 'ARTIFACT_PATH_ALIAS')
        paths.add(name)
        if root is not None:
            fd = open_artifact(root, name)
            try:
                before = os.fstat(fd)
                require(stat.S_ISREG(before.st_mode) and before.st_size == item['bytes'], 'ARTIFACT_FILE')
                digest = hashlib.sha256()
                remaining = before.st_size + 1
                actual = 0
                while remaining:
                    block = os.read(fd, min(1024 * 1024, remaining))
                    if not block:
                        break
                    actual += len(block)
                    remaining -= len(block)
                    digest.update(block)
                after = os.fstat(fd)
                require((before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                        (after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'ARTIFACT_CHANGED')
                require(actual == item['bytes'] and digest.hexdigest() == item['sha256'],
                        'ARTIFACT_HASH_MISMATCH')
            finally:
                os.close(fd)
    if component['build_status'] == 'BUILD_PASS_OFFLINE':
        require(set(required_roles) <= roles, 'BUILD_OUTPUTS_INCOMPLETE')
    return roles


def validate(value, artifacts_root=None):
    require(isinstance(value, dict) and value['schema'] == SCHEMA, 'SCHEMA')
    require(value['target'] == TARGET and type(value['target']['physical_cpus']) is int, 'WRONG_BOARD')
    for flag in ('native_ready', 'restart_ready', 'update_authorized'):
        require(value[flag] is False, 'AUTHORIZATION_NOT_GRANTED')
    ref = value['reference']
    require(ref['publication_commit'] == PUBLICATION and
            ref['pins_blob_sha'] == '91f28b4c037c3e81110f025e4488b291b29c27f1', 'PUBLICATION_PIN')
    require(canonical_digest(ref['pins']) == REFERENCE_DIGEST, 'REFERENCE_DATA_CHANGED')
    c = value['components']
    k, a, m = c['kernel'], c['aura_graphics_stage2'], c['mesa']
    require(k['repository'] == 'https://github.com/cameroncooper/linux' and
            k['source_commit'] == KERNEL and k['source_tree'] == TREE and
            k['config_sha256'] == CONFIG and k['config_publication_commit'] == PUBLICATION and
            k['release'] == ref['pins']['kernel']['release'] and k['page_size_bytes'] == 16384 and
            type(k['page_size_bytes']) is int, 'KERNEL_PIN')
    require(k['same_build_required'] == ['Image.gz', 'modules', 'apple/t6050-j716c.dtb'], 'SPLIT_KERNEL_BUILD')
    require(a['repository'] == 'https://github.com/cameroncooper/aura' and
            a['source_commit'] == AURA and a['qualified_source_commit'] == AURA and
            a['role'] == ref['pins']['aura_graphics_stage2']['role'] and
            a['installed_stage1_identity_qualified'] is False, 'AURA_ROLE_OR_PIN')
    require(m['repository'] == 'https://github.com/aurora-silicon/mesa' and m['source_commit'] == MESA and
            m['package_pins'] == ref['pins']['native_ram_userland']['packages'], 'MESA_PIN')
    require(c['installed_stage1']['generic_recipe_is_publisher_installed_identity'] is False,
            'STAGE1_HISTORY_NOT_QUALIFIED')
    generic_stage1 = c.get('generic_stage1_candidate')
    if generic_stage1 is not None:
        require(generic_stage1['repository'] == 'https://github.com/cameroncooper/aura' and
                generic_stage1['source_commit'] == AURA and generic_stage1['enrolled'] is False and
                generic_stage1['publisher_installed_identity'] is False and
                generic_stage1.get('firmware_acceptance_verified', False) is False and
                generic_stage1.get('watchdog_arming_qualified', False) is False, 'GENERIC_STAGE1_SCOPE')
    require(c['userland']['ready_image_eligible'] is False and
            c['userland']['required_package_guard_board'] == 'J716c', 'PRO_IMAGE_NOT_MAX')
    require(c['host_guardian']['required'] is True and
            c['host_guardian']['package_update_guard_is_not_host_guardian'] is True, 'GUARDIAN_SCOPE')
    firmware = value['firmware']
    require(firmware['required'] == FIRMWARE and firmware['update_authorized'] is False and
            firmware['apple_firmware_payloads_in_repository'] is False, 'FIRMWARE_PIN_OR_AUTHORIZATION')
    q = firmware['qualification']
    require(q['original_update_alone_qualifies_lab'] is False and
            q['matching_version_strings_alone_qualify_deployment'] is False, 'FIRMWARE_SCOPE')
    rt = value['runtime_contract']
    require(rt['cpu_ceiling_profile'] == 'approximately 2 GHz with checked temperature telemetry' and
            rt['shallow_wfi_opt_in'] == 'j716c.wfi=probe', 'CPU_OR_IDLE_PROFILE')
    for name in ('shallow_wfi_default_enabled', 'rtc_runtime_dt_enabled', 'external_atc2_runtime_dt_enabled',
                 'suspend_and_deep_idle_qualified', 'usb_serial_or_ssh_qualified', 'usb_plus_wfi_tree_qualified',
                 'native_reference_is_persistent_omarchy', 'macos_performance_or_power_parity_qualified'):
        require(rt[name] is False, 'RUNTIME_SCOPE')
    require(rt['smc_fan_control'] == 'firmware-owned' and rt['apple_keep_idle_nop_overrides_wfi'] is True,
            'THERMAL_OR_IDLE_CONTRACT')
    gates = value['deployment_gates']
    require(isinstance(gates, list) and len(gates) == len(GATES) and
            {g['id'] for g in gates} == GATES and all(g['required'] is True for g in gates), 'MISSING_GATE')
    require(all(g['status'] in {'PINNED_SOURCE_ONLY', 'PENDING', 'BLOCKED', 'NOT_RUN',
                              'INPUTS_VERIFIED', 'BUILD_PASS_OFFLINE', 'OFFLINE_GUARD_TESTED'} for g in gates),
            'UNSUPPORTED_GATE_SUCCESS')
    artifact_count = 0
    names = ('kernel', 'aura_graphics_stage2', 'mesa')
    if generic_stage1 is not None:
        names += ('generic_stage1_candidate',)
    for name in names:
        artifact_count += len(check_artifacts(c[name], artifacts_root, REQUIRED_OUTPUTS[name]))
    return {'schema': 'ilinux-j716c-stack-validation-v1', 'manifest_valid': True,
            'reference_inputs_pinned': True, 'artifact_records': artifact_count,
            'artifact_files_checked': artifacts_root is not None,
            'build_status': {name: c[name]['build_status'] for name in names},
            'unmet_deployment_gates': [g['id'] for g in gates],
            'native_ready': False, 'restart_ready': False, 'update_authorized': False,
            'read_only': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--artifacts-root', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(validate(read_json(args.manifest), args.artifacts_root), sort_keys=True))
    except (StackError, KeyError, TypeError, ValueError, OSError, RecursionError) as error:
        print(json.dumps({'manifest_valid': False, 'reason': str(error) if isinstance(error, StackError)
                          else 'INVALID_OR_UNREADABLE_INPUT', 'native_ready': False, 'restart_ready': False}))
        raise SystemExit(2)
