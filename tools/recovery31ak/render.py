# SPDX-License-Identifier: MIT
"""Original 31AK path correction around the frozen 31AJ transaction renderer.

No live operation runs here. The helper, profile and enrollment arguments stay
unchanged. Only a new private work directory is physically canonicalized, bound
to the subshell's kernel-held working directory and checked before paths are used.
"""
import hashlib
import html
import os
from pathlib import Path
import stat
import types

ROOT = Path(__file__).resolve().parents[2]
FROZEN = {
    'tools/recovery31aj/profile.py': '3fa5fb251bee45bbf8fa352589c5fa0aba1acc64e073e318cbee175f90f68827',
    'tools/recovery31aj/render.py': 'cf291cbd705d5e5449da8cb9d9337a7321d1e2016d3d19ef9ed418170378be5a',
    'tools/recovery31aj_portable/adapter.py': 'd47b2151e263f392e1741f913641c15dae9f244eec566e481a6520ad107a836a',
}


def frozen_sources(root):
    """Read fixed original paths through no-follow descriptors, then hash bytes."""
    root = Path(root).resolve()
    result = {}
    for name, digest in FROZEN.items():
        current = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            parts = Path(name).parts
            for index, part in enumerate(parts):
                flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
                if index < len(parts) - 1:
                    flags |= os.O_DIRECTORY
                child = os.open(part, flags, dir_fd=current)
                os.close(current)
                current = child
            before = os.fstat(current)
            if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= 65536:
                raise ValueError('frozen source bound')
            data = bytearray()
            while len(data) <= 65536:
                piece = os.read(current, min(16384, 65537 - len(data)))
                if not piece:
                    break
                data.extend(piece)
            after = os.fstat(current)
            fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
            if (len(data) != before.st_size or
                    any(getattr(before, k) != getattr(after, k) for k in fields) or
                    hashlib.sha256(data).hexdigest() != digest):
                raise ValueError('frozen source identity')
            result[name] = bytes(data)
        finally:
            os.close(current)
    return result


def load_original(root=ROOT):
    root = Path(root).resolve()
    sources = frozen_sources(root)
    adapter = types.ModuleType('recovery31ak_frozen_loader')
    name = 'tools/recovery31aj_portable/adapter.py'
    adapter.__file__ = str(root / name)
    exec(compile(sources[name], adapter.__file__, 'exec'), adapter.__dict__)
    loader = adapter.SnapshotImports(root, sources)
    spec = loader.spec_from_file_location('recovery31ak_frozen_renderer',
                                          root / 'tools/recovery31aj/render.py')
    module = loader.module_from_spec(spec)
    loader.exec_module(module)
    return module


original = load_original()
profile = original.profile
LAB, ORIGINAL, DATA, KIT, STATE = (
    getattr(original, name) for name in ('LAB', 'ORIGINAL', 'DATA', 'KIT', 'STATE'))


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('frozen renderer anchor')
    return text.replace(old, new, 1)


WORK_BLOCK = r'''WORK_RAW=$(/usr/bin/mktemp -d /private/tmp/ilinux31ak.XXXXXX) || fail "private work directory"
WORK_ID=$(/usr/bin/stat -f %d:%i:%u:%Lp "$WORK_RAW") || fail "new work identity"
case "$WORK_ID" in *:*:0:700) ;; *) fail "new work ownership or mode";; esac
WORK=$(cd -P "$WORK_RAW" && /bin/pwd -P) || fail "physical work directory"
test -n "$WORK" && test "$WORK" != / && safe_path "$WORK" || fail "physical work path"
test "${WORK##*/}" = "${WORK_RAW##*/}" || fail "physical work name"
test "$(/usr/bin/stat -f %d:%i:%u:%Lp "$WORK_RAW")" = "$WORK_ID" && test "$(/usr/bin/stat -f %d:%i:%u:%Lp "$WORK")" = "$WORK_ID" || fail "work identity changed during canonicalization"
cd -P "$WORK" || fail "enter held work directory"
work_binding() { safe_path "$WORK" && test -d "$WORK" && test "$(/usr/bin/stat -f %d:%i:%u:%Lp "$WORK")" = "$WORK_ID" && test "$(/usr/bin/stat -f %d:%i:%u:%Lp .)" = "$WORK_ID" && test "$(/bin/pwd -P)" = "$WORK" && safe_path "$WORK" && test "$(/usr/bin/stat -f %d:%i:%u:%Lp "$WORK")" = "$WORK_ID"; }
work_binding || fail "entered work identity"
WORK_READY=1
cleanup() { if test "${WORK_READY:-0}" = 1 && work_binding; then /bin/rm -f ./profile.json ./candidate.macho ./m1n1-boot021.bin ./ilinux31aj-reader ./snapshot.json; work_binding && /bin/rmdir "$WORK"; fi; }
trap cleanup EXIT'''


def advice(operation):
    before = ('PRE_ENROLLMENT_STOP: this invocation attempted no boot or policy command. '
              'Do not boot or retry. Preserve any state. Do not run restore blindly: it '
              'requires the persisted baseline/key and its independent guards. Return '
              'to Macintosh HD/default and report the refusal.' if operation == 'install' else
              'RESTORE_PREFLIGHT_STOP: this invocation attempted no new boot or policy '
              'command. Restoration is not confirmed. Do not boot or retry; preserve '
              'the existing baseline/key and request review of the refused guard.')
    return ("MUTATION_POSSIBLE=0\n"
            "failure_advice() { if test \"${MUTATION_POSSIBLE:-0}\" = 1; then "
            "printf '%s\\n' \"POST_COMMAND_STOP: a boot or policy command was attempted. "
            "Outcome is unconfirmed. Do not boot or retry. Preserve state and use the "
            "independent restore only when its guards admit the current state.\" >&2; "
            "else printf '%s\\n' \"" + before + "\" >&2; fi; }\n"
            "fail() { printf '%s\\n' \"STOP: $1.\" >&2; failure_advice; exit 2; }")


def render(value, operation):
    text = original.render(value, operation)
    text = once(text,
                'fail() { printf "%s\\n" "STOP: $1. No boot or retry. Use the independent restore page." >&2; exit 2; }',
                advice(operation))
    old_work = ('WORK=$(/usr/bin/mktemp -d /private/tmp/ilinux31aj.XXXXXX) || fail "private work directory"\n'
                'cleanup() { /bin/rm -rf "$WORK"; }\ntrap cleanup EXIT')
    text = once(text, old_work, WORK_BLOCK)
    for item in ('profile.json', *(value['files'][role]['name'] for role in
                                  (('helper', 'candidate', 'rollback') if operation == 'install'
                                   else ('helper', 'rollback')))):
        text = once(text, '/bin/cp "$KIT/' + item + '" "$WORK/' + item + '"',
                    'work_binding && /bin/cp "$KIT/' + item + '" ./' + item)
    text = text.replace('> "$WORK/snapshot.json"', '> ./snapshot.json')
    text = once(text,
                'check_file() { test -f "$1"',
                'check_file() { if test "${WORK_READY:-0}" = 1; then work_binding || return 1; fi; test -f "$1"')
    for name in ('observe_admission', 'observe', 'validate', 'save_snapshot', 'marker', 'record_exit'):
        text = once(text, name + '() { ', name + '() { work_binding && ')
    text = once(text,
                '"$H" --capability-check recovery-transaction-v2',
                'work_binding && "$H" --capability-check recovery-transaction-v2')
    text = text.replace('\n"$H" --validate-snapshot ',
                        '\nwork_binding && "$H" --validate-snapshot ')
    text = once(text,
                'interrupted() { trap - INT TERM HUP; if test "$IN_ATTEMPT" = 1; then observe && save_snapshot "interrupted-$PHASE"; fi; printf "%s\\n" "STOP: interrupted; mutation outcome is unconfirmed. Do not boot or retry. Use independent restore." >&2; exit 130; }',
                'interrupted() { trap - INT TERM HUP; if test "$IN_ATTEMPT" = 1; then observe && save_snapshot "interrupted-$PHASE"; fi; printf "%s\\n" "STOP: interrupted." >&2; failure_advice; exit 130; }')
    text = text.replace('; IN_ATTEMPT=1', '; MUTATION_POSSIBLE=1; IN_ATTEMPT=1')
    text = text.replace('if /usr/bin/kmutil ', 'if work_binding && /usr/bin/kmutil ')
    text = text.replace('if /usr/bin/bputil ', 'if work_binding && /usr/bin/bputil ')
    if operation == 'install':
        text = once(text, '( set -C; "$H" --generate-comparison-key',
                    '( set -C; work_binding && "$H" --generate-comparison-key')
    else:
        for variable in ('CTRR', 'LAB_GROUP'):
            text = once(text, variable + '=$("$H" ', variable + '=$(work_binding && "$H" ')
    return text


def page(value):
    text = original.page(value)
    for operation in ('install', 'restore'):
        text = once(text, html.escape(original.render(value, operation)),
                    html.escape(render(value, operation)))
    return (text.replace('<title>31AJ Recovery transaction</title>',
                         '<title>31AK Recovery path correction</title>')
            .replace('<h1>31AJ: future authorized Recovery operation</h1>',
                     '<h1>31AK: future authorized Recovery operation</h1>'))
