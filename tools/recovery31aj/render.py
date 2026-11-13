# SPDX-License-Identifier: MIT
"""Render complete, inert Recovery blocks. This module never runs shell code."""
import html
import importlib.util
from pathlib import Path
import shlex

spec=importlib.util.spec_from_file_location('recovery31aj_profile',Path(__file__).with_name('profile.py'))
profile=importlib.util.module_from_spec(spec);spec.loader.exec_module(profile)

LAB='/Volumes/iLinux Boot Lab'
ORIGINAL='/Volumes/Macintosh HD'
DATA='/Volumes/iLinux Boot Lab - Data'
KIT=DATA+'/Users/Shared/iLinuxBoot/31aj-kit'
STATE=DATA+'/Users/Shared/iLinuxBoot/31aj-state'


def render(value,operation):
    value=profile.validate(value)
    if operation not in ('install','restore'):raise ValueError('unknown operation')
    files=value['files'];rows=['(', 'set +x', 'umask 077', 'export LC_ALL=C',
       'PATH=/usr/bin:/bin:/usr/sbin:/sbin; export PATH',
       'fail() { printf "%s\\n" "STOP: $1. No boot or retry. Use the independent restore page." >&2; exit 2; }',
       'test "$(/usr/bin/id -u)" = 0 || fail "Recovery root shell required"',
       'LAB='+shlex.quote(LAB),'ORIGINAL='+shlex.quote(ORIGINAL),
       'KIT='+shlex.quote(KIT),'STATE='+shlex.quote(STATE),
       'PHASE=preflight', 'IN_ATTEMPT=0',
       'safe_path() { local p="$1"; while test "$p" != /; do test ! -L "$p" || return 1; p="${p%/*}"; test -n "$p" || p=/; done; }',
       'hash_file() { if test -x /sbin/sha256; then /sbin/sha256 -q "$1"; elif test -x /usr/bin/shasum; then /usr/bin/shasum -a 256 "$1" | /usr/bin/awk \'{print $1}\'; elif test -x /usr/bin/openssl; then /usr/bin/openssl dgst -sha256 "$1" | /usr/bin/awk \'{print $NF}\'; else return 1; fi; }',
       'check_file() { test -f "$1" && test ! -L "$1" && test "$(/usr/bin/stat -f %z "$1")" = "$2" && test "$(hash_file "$1")" = "$3"; }',
       'safe_path "$KIT" && safe_path "$STATE" && safe_path "$LAB" && safe_path "$ORIGINAL" || fail "symlink path"',
       'test -d "$KIT" && test -d "$LAB/System/Library/CoreServices" && test -d "$ORIGINAL/System/Library/CoreServices" || fail "mounted System paths missing"',
       'test "$LAB" != "$ORIGINAL" || fail "distinct volumes required"',
       'check_file "$KIT/profile.json" '+str(len(profile.canonical(value)))+' '+profile.digest(value)+' || fail "profile pin"']
    roles=('helper','candidate','rollback') if operation=='install' else ('helper','rollback')
    for role in roles:
        item=files[role]
        rows.append('check_file "$KIT/'+item['name']+'" '+str(item['bytes'])+' '+item['sha256']+' || fail "'+role+' pin"')
    rows += ['WORK=$(/usr/bin/mktemp -d /private/tmp/ilinux31aj.XXXXXX) || fail "private work directory"',
      'cleanup() { /bin/rm -rf "$WORK"; }',
      'trap cleanup EXIT',
      '/bin/cp "$KIT/profile.json" "$WORK/profile.json" || fail "copy profile"',
      'check_file "$WORK/profile.json" '+str(len(profile.canonical(value)))+' '+profile.digest(value)+' || fail "copied profile pin"']
    for role in roles:
        item=files[role];rows += ['/bin/cp "$KIT/'+item['name']+'" "$WORK/'+item['name']+'" || fail "copy '+role+'"',
            'check_file "$WORK/'+item['name']+'" '+str(item['bytes'])+' '+item['sha256']+' || fail "copied '+role+' pin"']
    rows += ['H="$WORK/ilinux31aj-reader"', 'P="$WORK/profile.json"',
      '/bin/chmod 700 "$H" || fail "helper mode"',
      '"$H" --capability-check recovery-transaction-v2 --profile "$P" || fail "helper capability"',
      'KEY="$STATE/comparison.key"',
      'check_key() { safe_path "$KEY" && test -f "$KEY" && test ! -L "$KEY" && test "$(/usr/bin/stat -f %z "$KEY")" = 32 && test "$(/usr/bin/stat -f %u:%Lp "$KEY")" = 0:600; }',
      'observe_admission() { "$H" --snapshot --target-volume "$LAB" --original-volume "$ORIGINAL" --profile "$P" > "$WORK/snapshot.json"; }',
      'observe() { check_key && "$H" --snapshot --target-volume "$LAB" --original-volume "$ORIGINAL" --profile "$P" --comparison-key "$KEY" > "$WORK/snapshot.json"; }',
      'validate() { "$H" --validate-snapshot "$WORK/snapshot.json" --phase "$1" --baseline "$STATE/baseline.json" --profile "$P" --comparison-key "$KEY"; }',
      'save_snapshot() { /bin/cp "$WORK/snapshot.json" "$STATE/$1.tmp" && /bin/chmod 600 "$STATE/$1.tmp" && /bin/mv "$STATE/$1.tmp" "$STATE/$1.json"; }',
      'interrupted() { trap - INT TERM HUP; if test "$IN_ATTEMPT" = 1; then observe && save_snapshot "interrupted-$PHASE"; fi; printf "%s\\n" "STOP: interrupted; mutation outcome is unconfirmed. Do not boot or retry. Use independent restore." >&2; exit 130; }',
      'trap interrupted INT TERM HUP',
      'marker() { /bin/mkdir "$STATE/$1-attempt" || fail "operation already spent or marker could not be persisted"; }',
      'record_exit() { printf "%s\\n" "$2" > "$STATE/$1-attempt/exit.txt" || fail "save exit status"; }']
    if operation=='install':
        rows += ['test ! -e "$STATE" && test ! -L "$STATE" || fail "transaction already exists"',
          'observe_admission || fail "initial guarded admission snapshot"',
          '"$H" --validate-snapshot "$WORK/snapshot.json" --phase initial-admission --profile "$P" || fail "initial actual31AF or security guards"',
          '/bin/mkdir "$STATE" || fail "create new transaction state"',
          '/bin/chmod 700 "$STATE" || fail "state mode"',
          '( set -C; "$H" --generate-comparison-key --profile "$P" > "$KEY" ) || fail "new private comparison key generation"',
          '/bin/chmod 600 "$KEY" && check_key || fail "comparison key ownership/mode/length"',
          'observe || fail "key-bound initial snapshot"',
          '"$H" --validate-snapshot "$WORK/snapshot.json" --phase initial --profile "$P" --comparison-key "$KEY" || fail "key-bound initial policy baseline"',
          'save_snapshot baseline || fail "persist baseline"',
          '/bin/cp "$P" "$STATE/profile.json" && /bin/chmod 600 "$STATE/profile.json" || fail "persist profile"',
          'PHASE=candidate; marker candidate; IN_ATTEMPT=1',
          'if /usr/bin/kmutil configure-boot --custom-boot-object "$WORK/candidate.macho" --volume "$LAB" --compress </dev/tty; then RC=0; else RC=$?; fi',
          'IN_ATTEMPT=0; record_exit candidate "$RC"',
          'observe || fail "candidate post-write readback unavailable"',
          'save_snapshot candidate || fail "persist candidate readback"',
          'test "$RC" = 0 || fail "candidate command failed or timed out"',
          'validate candidate || fail "candidate payload/CTRR or unrelated policy postcondition"',
          'printf "%s\\n" "CANDIDATE READBACK VERIFIED. No restart performed. Await the human boot cue and independently measured maximum '+str(value['native_deadline_ms']//1000)+'-second observation. Return to paired Recovery for restore."']
    else:
        rows += ['test -d "$STATE" && test ! -L "$STATE" || fail "persistent transaction baseline missing"',
          'test "$(/usr/bin/stat -f %u:%Lp "$STATE")" = 0:700 || fail "state ownership/mode"',
          'safe_path "$STATE/baseline.json" && safe_path "$STATE/profile.json" || fail "baseline symlink"',
          'test -f "$STATE/baseline.json" && test "$(/usr/bin/stat -f %u:%Lp "$STATE/baseline.json")" = 0:600 || fail "baseline ownership/mode"',
          'check_file "$STATE/profile.json" '+str(len(profile.canonical(value)))+' '+profile.digest(value)+' || fail "persisted profile binding"',
          'check_key || fail "persistent private comparison key missing or unsafe"',
          'observe || fail "before-restore guarded snapshot"',
          'validate before-restore || fail "baseline or unrelated security mismatch"',
          'save_snapshot before-restore || fail "persist restore observation"',
          'if validate restored; then',
          '  printf "%s\\n" "BOOT021 AND DISABLED CTRR ALREADY VERIFIED; no mutation repeated. Restore Macintosh HD as Startup Disk manually, then confirm it independently."',
          '  exit 0', 'fi',
          'CTRR=$("$H" --snapshot-value "$WORK/snapshot.json" --key lab_ctrr --profile "$P" --comparison-key "$KEY") || fail "CTRR readback"',
          'case "$CTRR" in',
          ' enabled)',
          '  LAB_GROUP=$("$H" --target-group-private --target-volume "$LAB" --original-volume "$ORIGINAL" --profile "$P" --comparison-key "$KEY") || fail "private lab target binding"',
          '  case "$LAB_GROUP" in ????????-????-????-????-????????????) ;; *) unset LAB_GROUP; fail "private lab target format";; esac',
          '  PHASE=ctrr; marker ctrr; IN_ATTEMPT=1',
          '  if /usr/bin/bputil -c -v "$LAB_GROUP" </dev/tty; then RC=0; else RC=$?; fi',
          '  unset LAB_GROUP; IN_ATTEMPT=0; record_exit ctrr "$RC"',
          '  observe || fail "policy post-write readback unavailable"',
          '  save_snapshot raw-policy || fail "persist policy readback"',
          '  test "$RC" = 0 || fail "policy command failed or timed out"',
          '  validate raw-policy || fail "disabled CTRR or unrelated-policy postcondition"',
          ' ;;',
          ' disabled) validate raw-policy || fail "raw-policy guards" ;;',
          ' *) fail "unknown CTRR; no policy change attempted" ;;',
          'esac',
          'PHASE=boot021; marker boot021; IN_ATTEMPT=1',
          'if /usr/bin/kmutil configure-boot --custom-boot-object "$WORK/m1n1-boot021.bin" --raw --entry-point 2048 --lowest-virtual-address 0 --volume "$LAB" </dev/tty; then RC=0; else RC=$?; fi',
          'IN_ATTEMPT=0; record_exit boot021 "$RC"',
          'observe || fail "boot021 post-write readback unavailable"',
          'save_snapshot restored || fail "persist final readback"',
          'test "$RC" = 0 || fail "boot021 command failed or timed out"',
          'validate restored || fail "boot021/disabled-CTRR or unrelated policy postcondition"',
          'printf "%s\\n" "BOOT021 PAYLOAD + DISABLED CTRR VERIFIED. Macintosh HD default restoration is a separate manual Startup Disk action. No restart or default selection was performed."']
    return '\n'.join(rows+[')'])+'\n'


def page(value):
    return ('<!doctype html><meta charset="utf-8"><title>31AJ Recovery transaction</title>'
      '<style>body{font:18px system-ui;max-width:80em;margin:2em auto;padding:0 1em}'
      'textarea{box-sizing:border-box;width:100%;height:28em;padding:1em;'
      'font:16px/1.5 ui-monospace,monospace;white-space:pre;resize:vertical;'
      'color:#111;background:#f6f6f6;border:1px solid #888}label{display:block;margin:.8em 0}</style>'
      '<h1>31AJ: future authorized Recovery operation</h1><p>Offline preparation only. '
      'Do not paste until the reviewed package and explicit live authorization are provided. '
      'Authenticate only in Terminal.</p><p>Click inside the appropriate box, press '
      '<strong>Command+A</strong>, then <strong>Command+C</strong>. Quit the browser, '
      'open Terminal, and paste once. Selecting inside a box copies only that complete block.</p>'
      '<h2>First visit: install once</h2><label for="install-block">Install block</label>'
      '<textarea id="install-block" readonly spellcheck="false" wrap="off">'+html.escape(render(value,'install'))+'</textarea>'
      '<h2>Independent second visit: intended boot021 restoration</h2>'
      '<label for="restore-block">Independent restore block</label>'
      '<textarea id="restore-block" readonly spellcheck="false" wrap="off">'+html.escape(render(value,'restore'))+'</textarea>')
