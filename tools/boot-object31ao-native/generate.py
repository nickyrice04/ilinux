#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reversible finite policy-schema extension; old source remains immutable."""
import hashlib
from pathlib import Path
import types

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GENERATOR = 'tools/boot-object31al-native/generate.py'
GENERATOR_SHA = 'f6d4b336b0f95f3793cf849618e6fe1b9542da3421b53787436304e7bfb1adca'

# Exact, once-only patches to the frozen instrumented state source. They do
# change acceptance for the documented catalog extension; all remaining
# predicates and the original header, core, JSON and Preboot engine stay exact.
PATCHES = (
    ('#include "reader.h"\n', '#include "reader.h"\n#include "extra_policy.h"\n'),
    ('unsigned metadata_seen[4];} Policy;',
     'unsigned metadata_seen[4];PolicyExtras extras;} Policy;'),
    ('"ilinux31aj-private-policy-v2"', '"ilinux31ao-private-policy-v3"'),
    ('    uint8_t digest[32];CCHmacFinal(&ctx,digest);',
     '    policy_extra_commit(&policy->extras,&ctx);\n    uint8_t digest[32];CCHmacFinal(&ctx,digest);'),
    ('after=trim(after+1);if(D_TEST((!tag_list(tags)),',
     'after=trim(after+1);'
     'if(!strcmp(tags,"smb0 && smb1")){char conjunction[24];'
     'if(!value_string(after,false,conjunction)||strcmp(conjunction,"true"))goto done;'
     'strcpy(tags,"smb0,smb1");}'
     'if(D_TEST((!tag_list(tags)),'),
    ('            const char *auth[]={',
     '            int extra=policy_extra_set(&out->extras,tag,after);'
     'if(extra){if(extra<0)goto done;continue;}\n            const char *auth[]={'),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def frozen_generator():
    path = ROOT / GENERATOR
    blob = path.read_bytes()
    if sha(blob) != GENERATOR_SHA:
        raise ValueError('frozen generator mismatch')
    module = types.ModuleType('frozen31al_for31ao')
    module.__file__ = str(path)
    exec(compile(blob, str(path), 'exec'), module.__dict__)
    return module


def apply(source):
    for before, after in PATCHES:
        if source.count(before) != 1:
            raise ValueError('extension anchor mismatch')
        source = source.replace(before, after, 1)
    return source


def reverse(source):
    for before, after in reversed(PATCHES):
        if source.count(after) != 1:
            raise ValueError('reverse extension anchor mismatch')
        source = source.replace(after, before, 1)
    return source


def generate(output):
    generator = frozen_generator()
    proof = generator.generate(output)
    path = Path(output) / 'state.c'
    before = path.read_text()
    after = apply(before)
    if reverse(after) != before:
        raise ValueError('extension reversal mismatch')
    original = (ROOT / 'tools/boot-object31aj-native/state.c').read_text()
    if generator.strip(reverse(after)) != original:
        raise ValueError('original source reversal mismatch')
    path.write_text(after)
    for name in ('extra_policy.c', 'extra_policy.h'):
        (Path(output) / name).write_bytes((HERE / name).read_bytes())
    return {'base_observation_proof': proof,
            'extension_reverses_to_frozen_observed_source': True,
            'stripped_reversed_source_equals_original': True,
            'acceptance_extension': 'FINITE_EXTRA_CATALOG_AND_TRUE_SMB_CONJUNCTION',
            'comparison_extension': 'PRIVATE_STRUCT_AND_TAGGED_V3_HMAC',
            'reader_header_unchanged': True, 'native_ready': False}


def parser_source(source):
    """Extract exact pure parser regions; no capture/disk/host API is compiled."""
    declaration = source[source.index('static const char *semantic_keys[]='):
                         source.index('typedef struct {CFDictionaryRef fixture;} Backend;')]
    functions = source[source.index('static char *trim('):
                       source.index('static bool policy_commitment(')]
    policy = source[source.index('static bool tag_list('):
                    source.index('static bool policy_for(')]
    return declaration + functions + policy
