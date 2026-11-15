#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Focused original synthetic controls; no live policy, disk or boot queries.

Build the production pure parser once with build.py, then pass --compiled here.
The second small executable uses exact generated Policy/parser/commitment C and
the frozen real type header. It returns comparison booleans, never private data.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
COMPILED = None
HARNESS_OUTPUT = None
SANITIZE = False
EXTRAS = {'CEPO': '0x1', 'SDOM': '0x1', 'CPRO': '1', 'CSEC': '1',
          'lobo': '1', 'love': '26.1.0.1.2,3'}


def load_generator():
    spec = importlib.util.spec_from_file_location('native31ao_test_generator', HERE / 'generate.py')
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    return generator


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def policy(*, mode='Permissive', conjunction=False, extras=None):
    permissive = mode == 'Permissive'
    lines = ['Security Mode: ' + mode,
             'Current OS environment: one true recoveryOS',
             'Recovery pairing: Paired',
             'Kernel CTRR Status: ' + ('Disabled' if permissive else 'Enabled')]
    if conjunction:
        lines += ['Permissive Security (smb0 && smb1): TRUE']
    else:
        lines += ['Reduced security (smb0): ' + ('TRUE' if permissive else 'FALSE'),
                  'Permissive security (smb1): ' + ('TRUE' if permissive else 'FALSE')]
    for tag in ('smb2', 'smb3', 'smb4', 'sip0', 'sip1', 'sip3'):
        lines.append('(' + tag + '): absent')
    lines += ['(sip2): ' + ('TRUE' if permissive else 'FALSE'),
              '(coih): ' + 'a' * 64, '(nsih): ' + 'b' * 96,
              '(rpnh): ' + 'c' * 96, '(rpnh): ' + 'd' * 96,
              '(ronh): ' + 'e' * 96, '(spih): ' + 'f' * 96, '(stng): 42',
              '(lpnh): ' + '1' * 96]
    for tag in ('auxp', 'auxi', 'auxr', 'prot', 'hrlp', 'losv'):
        lines.append('(' + tag + '): absent')
    for tag, value in (extras or {}).items():
        lines.append('(' + tag + '): ' + value)
    return ('\n'.join(lines) + '\n').encode()


def replace_value(raw, tag, value, occurrence=0):
    marker = ('(' + tag + '): ').encode()
    seen = 0
    lines = raw.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if marker in line:
            if seen == occurrence:
                lines[i] = line[:line.index(marker) + len(marker)] + value.encode() + b'\n'
                return b''.join(lines)
            seen += 1
    raise AssertionError('synthetic fixture field missing')


def remove_field(raw, tag):
    marker = ('(' + tag + '):').encode()
    return b''.join(line for line in raw.splitlines(keepends=True) if marker not in line)


def run_parser(raw, args=None):
    completed = subprocess.run([str(COMPILED)] + (args if args is not None else ['--stdin']),
        input=raw, capture_output=True, timeout=5)
    if completed.stderr:
        raise AssertionError('synthetic pure parser emitted stderr')
    return completed.returncode, json.loads(completed.stdout), completed.stdout


HARNESS_MAIN = r'''
static bool exact_read(void *out,size_t n) {
    unsigned char *p=out;
    while(n){size_t got=fread(p,1,n,stdin);if(!got)return false;p+=got;n-=got;}
    return true;
}
static size_t length32(const unsigned char *p) {
    return (size_t)p[0]|((size_t)p[1]<<8)|((size_t)p[2]<<16)|((size_t)p[3]<<24);
}
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    bool role_change=!strcmp(argv[1],"ROLE"),profile_change=!strcmp(argv[1],"PROFILE");
    bool key_change=!strcmp(argv[1],"KEY"),unloaded=!strcmp(argv[1],"UNLOADED");
    if(strcmp(argv[1],"SAME")&&!role_change&&!profile_change&&!key_change&&!unloaded)return 2;
    unsigned char header[8];if(!exact_read(header,8))return 2;
    size_t a_n=length32(header),b_n=length32(header+4);
    if(!a_n||!b_n||a_n>POLICY_LIMIT||b_n>POLICY_LIMIT)return 2;
    unsigned char *a_data=malloc(a_n),*b_data=malloc(b_n);
    if(!a_data||!b_data)return 2;
    if(!exact_read(a_data,a_n)||!exact_read(b_data,b_n)||fgetc(stdin)!=EOF)return 2;
    Policy a,b;bool a_ok=policy((Bytes){a_data,a_n},&a),b_ok=policy((Bytes){b_data,b_n},&b);
    Profile pa={0},pb={0};memset(pa.sha,'a',64);pa.sha[64]=0;pb=pa;
    if(profile_change)pb.sha[0]='b';
    ComparisonKey ka={0},kb={0};memset(ka.bytes,0x31,sizeof(ka.bytes));ka.loaded=true;kb=ka;
    if(key_change)kb.bytes[0]^=1;if(unloaded)kb.loaded=false;
    char ah[65]={0},bh[65]={0};
    bool ah_ok=a_ok&&policy_commitment(&a,&pa,&ka,"LAB",ah);
    bool bh_ok=b_ok&&policy_commitment(&b,&pb,&kb,role_change?"ORIGINAL":"LAB",bh);
    printf("{\"parsed_a\":%s,\"parsed_b\":%s,\"struct_equal\":%s,"
           "\"commit_a\":%s,\"commit_b\":%s,\"hmac_equal\":%s,"
           "\"values_returned\":false}\n",a_ok?"true":"false",b_ok?"true":"false",
           a_ok&&b_ok&&!memcmp(&a,&b,sizeof(a))?"true":"false",ah_ok?"true":"false",
           bh_ok?"true":"false",ah_ok&&bh_ok&&!strcmp(ah,bh)?"true":"false");
    memset(a_data,0,a_n);memset(b_data,0,b_n);free(a_data);free(b_data);
    memset(&a,0,sizeof(a));memset(&b,0,sizeof(b));memset(ah,0,sizeof(ah));memset(bh,0,sizeof(bh));
    return 0;
}
'''


def build_harness():
    generator = load_generator()
    generated = COMPILED.parent / 'sources'
    state = generator.frozen_generator().strip((generated / 'state.c').read_text())
    pure = generator.parser_source(state)
    begin = state.index('static bool policy_commitment(')
    end = state.index('static bool tag_list(', begin)
    commitment = state[begin:end]
    # Extraction preserves the complete function text and complete private
    # struct; it does not recreate or imitate either implementation.
    prefix = ('#include "reader.h"\n#include "extra_policy.h"\n'
              '#include <CommonCrypto/CommonHMAC.h>\n#include <ctype.h>\n'
              '#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n'
              '#include <strings.h>\nconst char *refusal_reason="synthetic";\n')
    output = HARNESS_OUTPUT.absolute()
    if ROOT / 'build' not in output.parents or output.exists() or '..' in output.parts:
        raise ValueError('fresh workspace harness output required')
    if any(parent.is_symlink() for parent in output.parents):
        raise ValueError('symlink harness output refused')
    output.mkdir(parents=True, mode=0o700)
    source = output / 'state-comparison.c'
    source.write_text(prefix + pure + '\n' + commitment + '\n' + HARNESS_MAIN)
    binary = output / 'state-comparison'
    command = ['/usr/bin/xcrun', 'clang', '-std=c11', '-O2', '-Wall', '-Wextra',
        '-Werror', '-Wno-deprecated-declarations', '-arch', 'arm64',
        '-mmacosx-version-min=13.0', '-DWORKSPACE_ROOT="/synthetic-workspace"',
        '-I', str(generated)]
    if SANITIZE:
        command += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    command += [str(source), str(generated / 'extra_policy.c'), '-o', str(binary)]
    subprocess.run(command, capture_output=True, check=True, timeout=60)
    return binary


class ProductionParser(unittest.TestCase):
    def accepted(self, raw, old, proposed):
        rc, result, _ = run_parser(raw)
        self.assertEqual(rc, 0)
        self.assertEqual((result['old_parser_accepted'], result['proposed_parser_accepted']),
                         (old, proposed))
        self.assertTrue(result['input_within_bounds'])
        return result

    def test_old_full_policies_preserved(self):
        self.accepted(policy(), True, True)
        self.accepted(policy(mode='Full'), True, True)
        self.accepted(remove_field(policy(mode='Full'), 'smb1'), True, True)

    def test_actual_true_conjunction_and_six_extras(self):
        self.accepted(policy(conjunction=True), False, True)
        self.accepted(policy(conjunction=True, extras=EXTRAS), False, True)
        self.accepted(policy(mode='Full', extras=EXTRAS), False, True)

    def test_conjunction_false_absent_or_duplicate_refused(self):
        good = policy(conjunction=True)
        for token in (b'FALSE', b'absent', b'2'):
            self.accepted(good.replace(b'smb0 && smb1): TRUE', b'smb0 && smb1): ' + token), False, False)
        self.accepted(good + b'(smb0): TRUE\n', False, False)
        self.accepted(good + b'(smb1): TRUE\n', False, False)
        self.accepted(policy(mode='Full', conjunction=True), False, False)

    def test_no_general_expression_or_json_alias_acceptance(self):
        for expression in (b'smb0&&smb1', b'smb0 || smb1', b'smb0 && smb2', b'SMB0 && SMB1'):
            self.accepted(policy(conjunction=True).replace(b'smb0 && smb1', expression), False, False)
        for tag in ('CRPO', 'smb5', 'cpro', 'LOVE', 'Z9X8'):
            self.accepted(policy(extras={tag: '1'}), False, False)

    def test_boolean_catalog_strict_types(self):
        for tag in ('CPRO', 'CSEC', 'lobo'):
            for value in ('1', '0', 'TRUE', 'false'):
                self.accepted(policy(extras={tag: value}), False, True)
            for value in ('2', '0x1', '-1', 'yes', 'true trailing', 'absent', ''):
                self.accepted(policy(extras={tag: value}), False, False)

    def test_hex_catalog_u64_bound_and_fixed_prefix(self):
        for tag in ('CEPO', 'SDOM'):
            for value in ('0x0', '0xFFFFFFFFFFFFFFFF', '0x0000000000000001'):
                self.accepted(policy(extras={tag: value}), False, True)
            for value in ('1', '0X1', '0x', '0x10000000000000000', '-0x1', '0xG', 'absent', ''):
                self.accepted(policy(extras={tag: value}), False, False)

    def test_version_is_exact_six_u32_not_arbitrary_string(self):
        for value in ('0.0.0.0.0,0', '4294967295.1.2.3.4,4294967295'):
            self.accepted(policy(extras={'love': value}), False, True)
        for value in ('true', '26.1', '26A1', '1.2.3.4.5.6', '1.2.3.4.5,6suffix',
                      '1.2.3.4.5,4294967296', '1.2.3.4.5,-1', '1.2.3.4.5,', 'absent', ''):
            self.accepted(policy(extras={'love': value}), False, False)

    def test_each_extra_duplicate_refused_even_if_absent(self):
        for tag, value in EXTRAS.items():
            for duplicate in (value, 'absent'):
                self.accepted(policy(extras={tag: value}) +
                              ('(' + tag + '): ' + duplicate + '\n').encode(), False, False)

    def test_existing_auth_and_metadata_cardinality_preserved(self):
        for tag in ('auxp', 'auxi', 'auxr', 'prot', 'hrlp', 'losv'):
            self.accepted(replace_value(policy(), tag, '1'), False, False)
        for tag in ('rpnh', 'ronh', 'spih', 'stng', 'coih', 'nsih', 'sip2'):
            self.accepted(remove_field(policy(), tag), False, False)
        self.accepted(policy() + b'(rpnh): absent\n', False, False)
        self.accepted(policy() + b'(spih): absent\n', False, False)

    def test_security_mode_ctrr_and_required_semantics_unchanged(self):
        self.accepted(policy().replace(b'Security Mode: Permissive', b'Security Mode: Full'), False, False)
        self.accepted(policy().replace(b'Kernel CTRR Status: Disabled', b'Kernel CTRR Status: Enabled'), False, False)
        for tag in ('smb0', 'smb1', 'smb2', 'smb3', 'smb4', 'sip0', 'sip1', 'sip3'):
            self.accepted(remove_field(policy(), tag), False, False)

    def test_group_limit_unmodified_and_first_label_not_skipped(self):
        grouped = remove_field(policy(), 'smb2')
        grouped = remove_field(grouped, 'smb3')
        self.accepted(grouped + b'(smb2,smb3): absent\n', True, True)
        self.accepted(policy() + b'(auxp,auxi,auxr,prot,hrlp): absent\n', False, False)
        self.accepted(policy().replace(b'(smb2): absent',
                      b'First (label) later (smb2): absent'), False, False)

    def test_bounds_nul_and_public_output_redaction(self):
        for raw in (b'', b'X' * 65537):
            rc, result, output = run_parser(raw)
            self.assertEqual(rc, 2)
            self.assertFalse(result['input_within_bounds'])
            self.assertNotIn(b'XXXXX', output)
        for raw in (policy() + b'\0PRIVATE_SENTINEL', policy() + b'X' * 2049):
            result = self.accepted(raw, False, False)
            self.assertFalse(result['policy_values_returned'])
        rc, result, output = run_parser(policy(), ['--PRIVATE_ARGUMENT'])
        self.assertEqual(rc, 2)
        self.assertNotIn(b'PRIVATE_ARGUMENT', output)
        self.assertFalse(result['native_ready'])

    def test_inert_default_does_not_consume_input(self):
        result = subprocess.run([str(COMPILED)], input=b'PRIVATE_SENTINEL',
                                capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0)
        self.assertIn(b'Inert by default', result.stdout)
        self.assertNotIn(b'PRIVATE_SENTINEL', result.stdout + result.stderr)

    def test_undefined_imports_exclude_host_capture_and_writes(self):
        result = subprocess.run(['/usr/bin/nm', '-u', str(COMPILED)],
                                capture_output=True, text=True, check=True, timeout=10)
        imports = {line.split()[-1].lstrip('_') for line in result.stdout.splitlines() if line.split()}
        forbidden = {'fork', 'vfork', 'execve', 'execv', 'execvp', 'posix_spawn',
                     'posix_spawnp', 'system', 'popen', 'open', 'openat', 'fopen',
                     'unlink', 'rename', 'mount', 'unmount', 'sysctl', 'sysctlbyname'}
        self.assertFalse(imports & forbidden)
        for name in ('old_parse.c', 'proposed_parse.c'):
            source = (COMPILED.parent / 'sources' / name).read_text()
            self.assertNotIn('static bool capture(', source)
            self.assertNotIn('/usr/bin/bputil', source)
            self.assertNotIn('/usr/sbin/diskutil', source)


class PreservationAndCommitment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = build_harness()

    def compare(self, left, right, variation='SAME'):
        packet = struct.pack('<II', len(left), len(right)) + left + right
        completed = subprocess.run([str(self.harness), variation], input=packet,
                                   capture_output=True, timeout=5)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, b'')
        result = json.loads(completed.stdout)
        self.assertFalse(result['values_returned'])
        self.assertTrue(result['parsed_a'])
        self.assertTrue(result['parsed_b'])
        return result

    def test_same_real_full_policy_is_stable(self):
        result = self.compare(policy(conjunction=True, extras=EXTRAS),
                              policy(conjunction=True, extras=EXTRAS))
        self.assertTrue(result['struct_equal'])
        self.assertTrue(result['hmac_equal'])

    def test_each_extra_mutation_changes_struct_and_hmac(self):
        base = policy(conjunction=True, extras=EXTRAS)
        replacements = {'CEPO': '0x2', 'SDOM': '0x2', 'CPRO': '0', 'CSEC': '0',
                        'lobo': '0', 'love': '26.1.0.1.2,4'}
        for tag, value in replacements.items():
            with self.subTest(tag=tag):
                result = self.compare(base, replace_value(base, tag, value))
                self.assertFalse(result['struct_equal'])
                self.assertFalse(result['hmac_equal'])

    def test_extra_unseen_absent_and_false_are_distinct(self):
        unseen = policy()
        absent = policy(extras={'lobo': 'absent'})
        false = policy(extras={'lobo': '0'})
        # The formatter never emits ABSENT for these six keys. A missing key
        # stays back-compatible, but explicit ABSENT must not gain admission.
        rc, rejected, _ = run_parser(absent)
        self.assertEqual(rc, 0)
        self.assertFalse(rejected['proposed_parser_accepted'])
        result = self.compare(unseen, false)
        self.assertFalse(result['struct_equal'])
        self.assertFalse(result['hmac_equal'])

    def test_extra_canonicalization_and_row_order_are_stable(self):
        left = policy(extras=EXTRAS)
        right_extras = dict(reversed(tuple(EXTRAS.items())))
        right_extras.update({'CEPO': '0x0000000000000001', 'CPRO': 'TRUE',
                             'CSEC': 'true', 'lobo': 'TRUE', 'love': '026.01.0.1.2,3'})
        result = self.compare(left, policy(extras=right_extras))
        self.assertTrue(result['struct_equal'])
        self.assertTrue(result['hmac_equal'])

    def test_original_metadata_mutations_and_nonce_order_bound(self):
        base = policy(extras=EXTRAS)
        for tag, value in (('rpnh', '2' * 96), ('ronh', '3' * 96),
                           ('spih', '4' * 96), ('stng', '43')):
            result = self.compare(base, replace_value(base, tag, value))
            self.assertFalse(result['struct_equal'])
            self.assertFalse(result['hmac_equal'])
        swapped = replace_value(base, 'rpnh', 'd' * 96, 0)
        swapped = replace_value(swapped, 'rpnh', 'c' * 96, 1)
        self.assertFalse(self.compare(base, swapped)['hmac_equal'])

    def test_key_role_and_profile_domain_separation(self):
        base = policy(extras=EXTRAS)
        for variation in ('KEY', 'ROLE', 'PROFILE'):
            result = self.compare(base, base, variation)
            self.assertTrue(result['struct_equal'])
            self.assertFalse(result['hmac_equal'])
        unloaded = self.compare(base, base, 'UNLOADED')
        self.assertTrue(unloaded['commit_a'])
        self.assertFalse(unloaded['commit_b'])

    def test_intentional_lpnh_coih_and_sip2_metadata_hmac_scope(self):
        base = policy(extras=EXTRAS)
        lpnh = self.compare(base, replace_value(base, 'lpnh', '5' * 96))
        self.assertTrue(lpnh['struct_equal'])  # old identity exclusion retained
        self.assertTrue(lpnh['hmac_equal'])
        coih = self.compare(base, replace_value(base, 'coih', '6' * 64))
        self.assertFalse(coih['struct_equal'])
        self.assertTrue(coih['hmac_equal'])  # selected-object gate owns this value
        changed_ctrr = replace_value(base, 'sip2', 'FALSE').replace(
            b'Kernel CTRR Status: Disabled', b'Kernel CTRR Status: Enabled')
        sip2 = self.compare(base, changed_ctrr)
        self.assertFalse(sip2['struct_equal'])
        self.assertTrue(sip2['hmac_equal'])  # explicit CTRR guard owns this state

    def test_exact_reversal_and_unchanged_header_core_json(self):
        generator = load_generator()
        generated = COMPILED.parent / 'sources'
        proposed = (generated / 'state.c').read_text()
        frozen = generator.reverse(proposed)
        original = (ROOT / 'tools/boot-object31aj-native/state.c').read_text()
        self.assertEqual(generator.frozen_generator().strip(frozen), original)
        self.assertEqual(generator.apply(frozen), proposed)
        for name in ('reader.h', 'core.c', 'json.c'):
            self.assertEqual((generated / name).read_bytes(),
                             (ROOT / 'tools/boot-object31aj-native' / name).read_bytes())
        self.assertIn('memcmp(&lp,&la,sizeof(lp))', proposed)
        self.assertIn('memcmp(&op,&oa,sizeof(op))', proposed)
        self.assertIn('PolicyExtras extras;', proposed)
        with self.assertRaises(ValueError):
            generator.apply(proposed)
        with self.assertRaises(ValueError):
            generator.reverse(frozen)

    def test_build_receipt_and_input_bindings_are_current(self):
        receipt = json.loads((COMPILED.parent / 'build-result.json').read_text())
        self.assertEqual(receipt['binary_sha256'], digest(COMPILED))
        self.assertEqual(receipt['sanitized'], SANITIZE)
        self.assertFalse(receipt['contains_host_capture_api'])
        self.assertFalse(receipt['native_ready'])
        for name, expected in receipt['source_inputs'].items():
            self.assertEqual(digest(HERE / name), expected)
        proof = receipt['guard_preservation']
        self.assertTrue(proof['extension_reverses_to_frozen_observed_source'])
        self.assertTrue(proof['stripped_reversed_source_equals_original'])


def main():
    global COMPILED, HARNESS_OUTPUT, SANITIZE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiled', type=Path, required=True)
    parser.add_argument('--harness-output', type=Path, required=True)
    parser.add_argument('--sanitize', action='store_true')
    args, test_args = parser.parse_known_args()
    COMPILED = args.compiled.absolute()
    HARNESS_OUTPUT = args.harness_output
    SANITIZE = args.sanitize
    if not COMPILED.is_file() or COMPILED.is_symlink() or ROOT / 'build' not in COMPILED.parents:
        parser.error('workspace compiled parser required')
    unittest.main(argv=[sys.argv[0]] + test_args, verbosity=2)


if __name__ == '__main__':
    main()
