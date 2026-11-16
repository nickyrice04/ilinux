#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Derive AU from pinned qualified AO state without changing frozen inputs."""
import hashlib
from pathlib import Path


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('AU transformation source mismatch')
    return text.replace(old, new)


def state_transform(pure):
    """Exact reversible edits: restored start plus same-byte diagnostic hook."""
    transforms = []

    def replace(old, new):
        nonlocal pure
        pure = once(pure, old, new)
        transforms.append((old, new))

    replace('!s->metadata_bound&&s->selected_exact&&!strcmp(s->selected,"31AF");',
            '!s->metadata_bound&&s->selected_exact&&!strcmp(s->selected,"BOOT021")&&!strcmp(s->lab_ctrr,"disabled");')
    replace('return !base&&s->selected_exact&&!strcmp(s->selected,"31AF");',
            'return !base&&s->selected_exact&&!strcmp(s->selected,"BOOT021")&&!strcmp(s->lab_ctrr,"disabled");')
    replace('memset(out,0,sizeof(*out));private_group[0]=0;Backend b={0};',
            'au_object_reset();memset(out,0,sizeof(*out));private_group[0]=0;Backend b={0};')
    replace('strcpy(out->selected,"NONE");out->selected_exact=false;',
            'strcpy(out->selected,"NONE");out->selected_exact=false;au_object_read.reference_present=lp.coih[0]!=0;au_reference_commitment(lp.coih,lp.nsih,profile,key);')
    old = 'Identity id;if(read_ok&&identify_object((Bytes){data,n},&id)&&strcmp(id.identity,"31AI")){strcpy(out->selected,id.identity);out->selected_exact=id.exact;}else strcpy(out->selected,"UNKNOWN");free(data);data=NULL;'
    new = '''au_object_read.read_attempted=true;au_object_read.read_succeeded=read_ok;
        if(read_ok)object_diagnostics31at((Bytes){data,n},&au_object_read.object);
        if(read_ok&&au_object_read.object.recognizer_completed&&strcmp(au_object_read.object.identity,"31AI")){strcpy(out->selected,au_object_read.object.identity);out->selected_exact=au_object_read.object.known_exact;}else strcpy(out->selected,"UNKNOWN");free(data);data=NULL;'''
    replace(old, new)
    reverse = pure
    for old, new in reversed(transforms):
        reverse = once(reverse, new, old)
    return pure, reverse, len(transforms)


def json_transform(original):
    changed = original
    pairs = [
        ('"ilinux31aj-recovery-profile-v1"', '"ilinux31au-recovery-profile-v1"'),
        ('json_get(&j,0,"initial_payload"),"31AF"', 'json_get(&j,0,"initial_payload"),"BOOT021"'),
        ('json_get(&j,helper,"name"),"ilinux31aj-reader"', 'json_get(&j,helper,"name"),"ilinux31au-reader"'),
    ]
    for old, new in pairs:
        changed = once(changed, old, new)
    reverse = changed
    for old, new in reversed(pairs):
        reverse = once(reverse, new, old)
    if reverse != original:
        raise ValueError('AU profile parser reversal failed')
    return changed
