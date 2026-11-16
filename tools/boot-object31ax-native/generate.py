#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reversible AX typed-policy additions to an exact verified AW source copy."""
import re


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('AX source anchor differs')
    return text.replace(old, new)


def namespace(text):
    text = text.replace('31AW', '31AX').replace('31aw', '31ax')
    return re.sub(r'_aw\b', '_ax', re.sub(r'\baw_', 'ax_', text))


def state_transform(original):
    state = namespace(original)
    patches = [
        ('#include "extra_policy.h"', '#include "extra_policy.h"\n#include "policy_contract.h"'),
        ('PolicyExtras extras;} Policy;', 'PolicyExtras extras;PolicyIdentity31AX identity;} Policy;'),
        ('ax_object_reset();memset(out,0,sizeof(*out));', 'ax_object_reset();policy_view_reset31ax();memset(out,0,sizeof(*out));'),
        ('            int extra=policy_extra_set(',
         '            int ax_tracked=policy_identity_set31ax(&out->identity,tag,after);if(ax_tracked){if(ax_tracked<0)goto done;continue;}\n            int extra=policy_extra_set('),
        ('    ok=true;\ndone:free(copy);return ok;',
         '    if(!policy_identity_complete31ax(&out->identity))goto done;\n    ok=true;\ndone:free(copy);return ok;'),
        ('    out->synthetic=b.fixture!=NULL;',
         '    if(!policy_view_capture31ax(&lp.identity,&op.identity,&lp.extras,&op.extras,lp.nsih,op.nsih,op.coih,group,ogroup,profile,key))goto done;\n    out->synthetic=b.fixture!=NULL;'),
    ]
    changed = state
    for old, new in patches:
        changed = once(changed, old, new)
    reverse = changed
    for old, new in reversed(patches):
        reverse = once(reverse, new, old)
    if reverse != state:
        raise ValueError('AX state reversal differs')
    return changed, len(patches)


def json_transform(original):
    state = namespace(original)
    return once(state, 'json_get(&j,0,"raw_policy_strategy"),"ctrr_only"',
                'json_get(&j,0,"raw_policy_strategy"),"reconstruct_lab_then_boot021_rescue"')


SAFETY = ('interactive_child','acquire_mount','release_mount','mount_command','mounted_source',
          'target_metadata','same_target','mount_binding_ar','prepare_state','persist','read_state',
          'file_matches','observe','cleanup','identity_commitment','work_binding','state_binding',
          'trusted_parent','private_fd','ar_secure_open','underlying_child_ar')


def safety_proof(old, new, aw):
    for name in SAFETY:
        if namespace(aw.function(old,name)) != aw.function(new,name):
            raise ValueError('AX unchanged body differs: '+name)
    writer = once(aw.function(new,'run_writer_aw31ax'),'run_writer_aw31ax(', 'run_writer(')
    if writer != namespace(aw.function(old,'run_writer')):
        raise ValueError('AX legacy writer body differs')
    return {'unchanged_aw_safety_bodies':list(SAFETY),'legacy_writer_argv_body_identical':True,
            'interactive_transport_unchanged':True,'new_fixed_operation':'bputil -n -v BOUND_LAB_GROUP',
            'reset_uses_ctrr_disable_option':False}
