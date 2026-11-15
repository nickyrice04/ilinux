# SPDX-License-Identifier: MIT
"""Render the complete native-controller invocation; this module never runs it."""
import hashlib
import html
from pathlib import Path
import types

ROOT = Path(__file__).resolve().parents[2]
PROFILE_SOURCE = 'tools/recovery31aj/profile.py'
PROFILE_SHA = '3fa5fb251bee45bbf8fa352589c5fa0aba1acc64e073e318cbee175f90f68827'
data = (ROOT / PROFILE_SOURCE).read_bytes()
if hashlib.sha256(data).hexdigest() != PROFILE_SHA:
    raise ValueError('profile source refused')
profile = types.ModuleType('verified31ar_profile')
profile.__file__ = str(ROOT / PROFILE_SOURCE)
exec(compile(data, profile.__file__, 'exec'), profile.__dict__)

KIT = '/Volumes/iLinux Boot Lab - Data/Users/Shared/iLinuxBoot/31ar-kit'
STATE = '/Volumes/iLinux Boot Lab - Data/private/var/db/ilinux31ar-state'


def render(value, operation):
    profile.validate(value)
    if operation not in ('install', 'restore'):
        raise ValueError('operation refused')
    expected = profile.canonical(value).decode('ascii')
    files = {item['name']: item for role, item in value['files'].items()
             if operation == 'install' or role != 'candidate'}
    header = r'''(
set +x
set -eu
umask 077
export LC_ALL=C
PATH=/usr/bin:/bin:/usr/sbin:/sbin
export PATH
fail() { printf '%s\n' 'STOP: 31AR refused. Preserve scratch and transaction state; no boot or retry. Report the finite result and use the independent restore only if its guards admit the state.' >&2; exit 2; }
test "$(/usr/bin/id -u)" = 0 || fail
safe_path() { case "$1" in /*) ;; *) return 1;; esac; case "$1" in */../*|*/./*|*//*|*/..|*/.|*/) return 1;; esac; p="$1"; while test "$p" != /; do test ! -L "$p" || return 1; p="${p%/*}"; test -n "$p" || p=/; done; }
WORK_RAW=$(/usr/bin/mktemp -d /private/tmp/ilinux31ar.XXXXXX) || fail
WORK_ID=$(/usr/bin/stat -f %d:%i:%u:%Lp "$WORK_RAW") || fail
case "$WORK_ID" in *:*:0:700) ;; *) fail;; esac
WORK=$(cd -P "$WORK_RAW" && /bin/pwd -P) || fail
test -n "$WORK" && test "$WORK" != / && safe_path "$WORK" || fail
test "${WORK##*/}" = "${WORK_RAW##*/}" || fail
test "$(/usr/bin/stat -f %d:%i:%u:%Lp "$WORK_RAW")" = "$WORK_ID" || fail
cd -P "$WORK" || fail
work_binding() { safe_path "$WORK" && test -d "$WORK" && test "$(/usr/bin/stat -f %d:%i:%u:%Lp "$WORK")" = "$WORK_ID" && test "$(/usr/bin/stat -f %d:%i:%u:%Lp .)" = "$WORK_ID" && test "$(/bin/pwd -P)" = "$WORK" && safe_path "$WORK" && test "$(/usr/bin/stat -f %d:%i:%u:%Lp "$WORK")" = "$WORK_ID"; }
work_binding || fail
trap 'printf "%s\n" "STOP: interrupted. Preserve scratch/state and report; no boot or retry." >&2; exit 130' INT TERM HUP
hash_file() { if test -x /sbin/sha256; then /sbin/sha256 -q "$1"; elif test -x /usr/bin/shasum; then /usr/bin/shasum -a 256 "$1" | /usr/bin/awk '{print $1}'; elif test -x /usr/bin/openssl; then /usr/bin/openssl dgst -sha256 "$1" | /usr/bin/awk '{print $NF}'; else return 1; fi; }
'''
    text = header + 'KIT=' + "'" + KIT + "'\n"
    text += 'safe_path "$KIT" && test -d "$KIT" && test "$(/usr/bin/stat -f %u:%Lp "$KIT")" = 0:700 || fail\n'
    text += 'work_binding && /bin/cat > ./expected-profile.json <<\'ILINUX31AR_PUBLIC_PROFILE\'\n'
    text += expected + 'ILINUX31AR_PUBLIC_PROFILE\n'
    text += ('safe_path "$KIT/profile.json" && test -f "$KIT/profile.json" && '
             'test "$(/usr/bin/stat -f %u:%Lp "$KIT/profile.json")" = 0:600 && '
             '/usr/bin/cmp -s ./expected-profile.json "$KIT/profile.json" || fail\n')
    text += ('check_file() { work_binding && safe_path "$1" && test -f "$1" && '
             'test "$(/usr/bin/stat -f %u:%Lp "$1")" = "0:$4" && '
             'test "$(/usr/bin/stat -f %z "$1")" = "$2" && '
             'test "$(hash_file "$1")" = "$3"; }\n')
    for name, item in files.items():
        mode = '700' if name == 'ilinux31aj-reader' else '600'
        text += f'check_file "$KIT/{name}" {item["bytes"]} {item["sha256"]} {mode} || fail\n'
    text += 'work_binding && /bin/cp "$KIT/profile.json" ./profile.json || fail\n'
    for name, item in files.items():
        mode = '700' if name == 'ilinux31aj-reader' else '600'
        text += f'work_binding && /bin/cp "$KIT/{name}" ./{name} || fail\n'
        text += f'/bin/chmod {mode} ./{name} || fail\n'
        text += f'check_file "$WORK/{name}" {item["bytes"]} {item["sha256"]} {mode} || fail\n'
    text += 'work_binding && /usr/bin/cmp -s ./expected-profile.json ./profile.json || fail\n'
    text += 'H="$WORK/ilinux31aj-reader"\nHELPER_EXIT=0\n'
    text += (f'work_binding && "$H" --transaction {operation} --profile "$WORK/profile.json" '
             '--scratch "$WORK" > ./result.json || HELPER_EXIT=$?\n')
    text += 'work_binding || fail\n'
    text += (f'"$H" --validate-transaction-result "$WORK/result.json" '
             f'--operation {operation} || fail\n')
    text += 'test "$HELPER_EXIT" = 0 || fail\n'
    for name in (*files, 'profile.json', 'expected-profile.json', 'result.json'):
        text += f'work_binding && /bin/rm -f ./{name} || fail\n'
    text += 'work_binding && /bin/rmdir "$WORK" || fail\n'
    text += ('printf \'%s\\n\' \'{"schema":"ilinux31ar-shell-result-v1",'
             f'"operation":"{operation}","helper_exit":0,"cleanup_verified":true,'
             '"default_changed":false,"restart_performed":false,"native_ready":false}\'\n')
    if operation == 'install':
        text += "printf '%s\\n' 'Lab installation and cleanup verified. No restart was performed. Follow the approved single native-test cue only after M1 is ready; independent boot021 restore is mandatory.'\n"
    else:
        text += "printf '%s\\n' 'boot021 restoration and cleanup verified. Restore Macintosh HD as Startup Disk separately, then return to Macintosh HD. Default restoration is not proven by this result.'\n"
    return text + ')\n'


def page(value, operation=None):
    if operation not in (None, 'install', 'restore'):
        raise ValueError('operation refused')
    operations = (operation,) if operation else ('install', 'restore')
    content = []
    for item in operations:
        heading = ('Install matched Aura/Linux diagnostic once' if item == 'install'
                   else 'Restore exact boot021 independently')
        content.append('<section><h2>' + heading + '</h2><p>Click in this box, '
                       'press Command-A, then Command-C. Quit the browser and paste once '
                       'in Utilities Terminal.</p><textarea readonly spellcheck="false" '
                       'aria-label="' + item + ' complete Recovery block">' +
                       html.escape(render(value, item)) + '</textarea></section>')
    return ('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>31AR guarded native transaction</title><style>'
            'body{font:18px system-ui;max-width:1100px;margin:32px auto;padding:0 20px;line-height:1.45}'
            'textarea{box-sizing:border-box;width:100%;height:36rem;white-space:pre;'
            'border:1px solid #888;padding:20px;font:14px monospace;resize:vertical}'
            'section{margin-top:36px}</style><h1>31AR: paired Recovery transaction</h1>'
            '<p>Offline preparation is not permission to execute. Use only the operation explicitly '
            'authorized for this visit. Copy its whole box, quit the browser, open Utilities Terminal '
            'and paste once. No clipboard demonstration or simultaneous browser/Terminal is needed.</p>'
            '<p>Keep recording off during authentication. Stop on any refusal; preserve state and '
            'report. Do not repeat, delete state, force an unmount, or improvise commands. Macintosh HD '
            'must remain at Full Security. The restore box never needs the candidate file.</p>' +
            ''.join(content) + '</html>\n')
