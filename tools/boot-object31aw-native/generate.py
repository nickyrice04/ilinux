#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Small reversible AW derivations; never modify a retained input."""
import re

CAPABILITY_BLOCK = ''' /* Pure bounded runtime controls precede every writer. A failed compressed
  * capability blocks install only; candidate-independent raw restoration stays
  * available under its unchanged exact-BOOT021 and preservation contracts. */
 t->codec_capability=codec_capability31aw();
 if(failpoint(t,"codec_positive")){t->codec_capability.positive_exact=false;t->codec_capability.passed=false;t->codec_capability.reason="POSITIVE_CONTROL_FAILED";}
 if(failpoint(t,"codec_negative")){t->codec_capability.negative_refused=false;t->codec_capability.passed=false;t->codec_capability.reason=t->codec_capability.positive_exact?"NEGATIVE_CONTROL_FAILED":"POSITIVE_CONTROL_FAILED";}
 if(t->install&&!t->codec_capability.passed)return refused_at(t,"CODEC","CAPABILITY_FAILED");
'''


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('AW derivation source mismatch')
    return text.replace(old, new)


def state_transform(pure, au):
    state, reversal, count = au.state_transform(pure)
    if reversal != pure or count != 5:
        raise ValueError('AU state provenance differs')
    changed = re.sub(r'\bau_', 'aw_', state)
    changed = once(changed, 'object_diagnostics31at(', 'object_diagnostics31aw(')
    reverse = re.sub(r'\baw_', 'au_', once(changed, 'object_diagnostics31aw(', 'object_diagnostics31at('))
    if reverse != state:
        raise ValueError('AW state reversal differs')
    return changed, state


def json_transform(original, au):
    state = au.json_transform(original)
    changed = state.replace('ilinux31au-', 'ilinux31aw-')
    if changed.replace('ilinux31aw-', 'ilinux31au-') != state:
        raise ValueError('AW profile reversal differs')
    # The original result formatter/validator uses numeric -1 before a writer,
    # but its shared parser did not recognize that token. Admit ONLY -1 here;
    # unchanged profile uint/range/exact-value contracts still reject negatives.
    at = "    if(p->p[p->at]>='0'&&p->p[p->at]<='9'){"
    negative = '''    if(p->p[p->at]=='-'&&p->n-p->at>=2&&p->p[p->at+1]=='1'){
        p->at+=2;strcpy(node->value,"-1");node->type=J_NUMBER;return index;}
'''
    result = once(changed, at, negative + at)
    if once(result, negative + at, at) != changed:
        raise ValueError('AW negative-one token reversal differs')
    return result


def buffer_transform(original):
    old = '*reason=ok?"DECODED":"DECODE_REJECTED";'
    new = '*reason=ok?"DECODED":decoded==0?"DECODE_RETURN_ZERO":"DECODE_OUTPUT_MISMATCH";'
    changed = once(original, old, new)
    if once(changed, new, old) != original:
        raise ValueError('buffer failure-label reversal differs')
    return changed


def normalize(text):
    text = text.replace('31AW', '31AU').replace('31aw', '31au')
    text = re.sub(r'_aw\b', '_au', text)
    return re.sub(r'\baw_', 'au_', text)


def function(text, name):
    match = re.search(r'(?m)^static [^\n(]*\b' + re.escape(name) + r'\(', text)
    if not match:
        raise ValueError('missing safety function')
    start = text.index('{', match.start())
    depth = 0
    quote = None
    line_comment = block_comment = False
    i = start
    while i < len(text):
        char = text[i]
        following = text[i:i+2]
        if line_comment:
            line_comment = char != '\n'
        elif block_comment:
            if following == '*/':
                block_comment = False
                i += 1
        elif quote:
            if char == '\\':
                i += 1
            elif char == quote:
                quote = None
        elif following == '//':
            line_comment = True
            i += 1
        elif following == '/*':
            block_comment = True
            i += 1
        elif char in ('"', "'"):
            quote = char
        elif char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return text[match.start():i+1]
        i += 1
    raise ValueError('unterminated safety function')


SAFETY_FUNCTIONS = (
    'interactive_child', 'run_writer', 'mutate', 'acquire_mount', 'release_mount',
    'mount_command', 'mounted_source', 'target_metadata', 'same_target',
    'mount_binding_ar', 'prewrite', 'prepare_state', 'load_enrollment', 'enroll',
    'persist', 'read_state', 'file_matches', 'observe', 'cleanup',
    'identity_commitment', 'work_binding', 'state_binding', 'trusted_parent',
    'private_fd', 'ar_secure_open', 'underlying_child_ar',
)


def safety_proof(old, new):
    normalized = normalize(new)
    for name in SAFETY_FUNCTIONS:
        if function(old, name) != function(normalized, name):
            raise ValueError('safety body differs: ' + name)
    old_run = function(old, 'run_transaction')
    new_run = function(normalized, 'run_transaction')
    normalized_block = normalize(CAPABILITY_BLOCK)
    if once(new_run, normalized_block, '') != old_run:
        raise ValueError('transaction changes exceed capability preflight')
    return {'namespace_normalized_body_equal': list(SAFETY_FUNCTIONS),
            'transaction_exact_after_capability_block_reversal': True,
            'candidate_independent_restore_preserved': True}
