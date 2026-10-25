#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Render, never execute, independently reviewed and authorized Recovery phases.

No profile or operational paste block is shipped by default. Rendering does not
authorize a write; the published pinned result requires M1 review and explicit
human approval before either phase is run in the lab's paired Recovery.
"""
from __future__ import annotations
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import shlex
from urllib.parse import urlsplit

ROLLBACK_SHA = "ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664"
HELPER_SHA = "e65636d03cfb7a7000f86810fdc8888e209b99bedaa1b36ca7a125de4bf72188"

BASE = r'''
hash_file() {
    if test -x /sbin/sha256; then /sbin/sha256 -q "$1"
    else /usr/bin/shasum -a 256 "$1" | /usr/bin/awk '{print $1}'; fi
}
base_guard() {
    ILINUX_OS='/Volumes/iLinux Boot Lab'
    ILINUX_DATA='/Volumes/iLinux Boot Lab - Data'
    ILINUX_ORIGINAL='/Volumes/Macintosh HD'
    ILINUX_BOOT="$ILINUX_DATA/Users/Shared/iLinuxBoot/m1n1.bin"
    local helper p data_group
    helper="$ILINUX_DATA/Users/Shared/iLinuxBoot/recovery-preflight.sh"
    for p in "$ILINUX_OS" "$ILINUX_DATA" "$ILINUX_ORIGINAL" \
        "$ILINUX_DATA/Users" "$ILINUX_DATA/Users/Shared" \
        "$ILINUX_DATA/Users/Shared/iLinuxBoot" "$ILINUX_BOOT" "$helper"; do
        test ! -L "$p" || return 1
    done
    test -f "$helper" || return 1
    test "$(hash_file "$helper")" = \
        e65636d03cfb7a7000f86810fdc8888e209b99bedaa1b36ca7a125de4bf72188 || return 1
    . "$helper" || return 1
    test "$(ilinux_field "$ILINUX_OS" VolumeName)" = 'iLinux Boot Lab' || return 1
    test "$(ilinux_field "$ILINUX_DATA" VolumeName)" = 'iLinux Boot Lab - Data' || return 1
    test "$(ilinux_field "$ILINUX_ORIGINAL" VolumeName)" = 'Macintosh HD' || return 1
    for p in "$ILINUX_OS" "$ILINUX_DATA" "$ILINUX_ORIGINAL"; do
        test "$(ilinux_field "$p" MountPoint)" = "$p" || return 1
        test "$(ilinux_field "$p" Internal)" = true || return 1
        test "$(ilinux_field "$p" FilesystemType)" = apfs || return 1
    done
    ILINUX_VG=$(ilinux_field "$ILINUX_OS" APFSVolumeGroupID) || return 1
    data_group=$(ilinux_field "$ILINUX_DATA" APFSVolumeGroupID) || return 1
    ILINUX_ORIGINAL_VG=$(ilinux_field "$ILINUX_ORIGINAL" APFSVolumeGroupID) || return 1
    test -n "$ILINUX_VG" && test -n "$ILINUX_ORIGINAL_VG" || return 1
    test "$ILINUX_VG" = "$data_group" || return 1
    test "$ILINUX_VG" != "$ILINUX_ORIGINAL_VG" || return 1
    test "$(ilinux_field "$ILINUX_DATA" FileVault)" = false || return 1
    test "$(/usr/bin/plutil -extract ProductBuildVersion raw -o - \
        "$ILINUX_OS/System/Library/CoreServices/SystemVersion.plist")" = 25G83 || return 1
    test -f "$ILINUX_BOOT" || return 1
    test "$(/usr/bin/stat -f %z "$ILINUX_BOOT")" = 3932160 || return 1
    test "$(hash_file "$ILINUX_BOOT")" = \
        ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664 || return 1
    ilinux_check_policies Permissive || return 1
}
'''

CAPTURE = r'''
    # /dev/tty is mandatory: confirmation must never read the pasted heredoc.
    # Keep the prompt visible and retain the full combined output privately.
    ILINUX31AD_COMMAND </dev/tty 2>&1 | /usr/bin/tee "$evidence/configure.log"
    statuses=("${PIPESTATUS[@]}")
    rc=${statuses[0]}
    capture_rc=${statuses[1]}
    printf '%s\n' "$rc" >"$evidence/configure.exit"
    printf '%s\n' "$capture_rc" >"$evidence/capture.exit"
    printf 'Configure exit: %s; capture exit: %s; private evidence: %s\n' "$rc" "$capture_rc" "$evidence"
    if test "$rc" != 0; then
        printf '%s\n' 'STOP: the lab slot may have changed. No retry, changed flags or diagnostic boot.'
        printf '%s\n' 'Use only the independent exact rollback after its fresh guard passes.'
        return "$rc"
    fi
    test "$capture_rc" = 0 || {
        printf '%s\n' 'STOP: output capture failed; no retry or boot. Preserve the private evidence.'
        return 74
    }
    ilinux_check_policies Permissive >"$evidence/postcheck.txt" 2>&1
    rc=$?
    printf '%s\n' "$rc" >"$evidence/postcheck.exit"
    test "$rc" = 0 || {
        printf '%s\n' 'STOP: postcheck failed; no retry, boot or security change.'
        return "$rc"
    }
'''


def validate(profile: dict) -> dict:
    if not isinstance(profile, dict) or set(profile) != {"schema", "candidate"}:
        raise ValueError("profile must contain schema and candidate only")
    if profile["schema"] != "ilinux31ad-write-v1":
        raise ValueError("wrong write profile schema")
    item = profile["candidate"]
    if not isinstance(item, dict) or set(item) != {"bytes", "sha256", "url"}:
        raise ValueError("exact candidate bytes/hash/URL required")
    if type(item["bytes"]) is not int or item["bytes"] != 196608:
        raise ValueError("expected reviewed nested-image geometry, 196608 bytes")
    if not isinstance(item["sha256"], str) or not re.fullmatch("[0-9a-f]{64}", item["sha256"]):
        raise ValueError("invalid SHA-256")
    if item["sha256"] == ROLLBACK_SHA:
        raise ValueError("rollback is not a candidate")
    if not isinstance(item["url"], str) or any(ord(c) < 32 for c in item["url"]):
        raise ValueError("invalid URL")
    u = urlsplit(item["url"])
    if u.scheme not in ("http", "https") or not u.hostname or u.username or u.password or u.fragment:
        raise ValueError("URL must be HTTP(S), without credentials or fragment")
    return profile


def render(profile: dict, phase: str) -> str:
    p = validate(profile)["candidate"]
    if phase not in ("install", "rollback"):
        raise ValueError("explicit install or rollback phase required")
    label = "ILINUX31AD_" + phase.upper() + "_END"
    head = "# RUN ONLY AFTER M1 REVIEW AND EXPLICIT HUMAN APPROVAL OF THIS EXACT PHASE.\n"
    head += "/bin/bash <<'" + label + "'\n"
    head += "set -u\numask 077\nPATH=/usr/bin:/bin:/usr/sbin:/sbin\nexport PATH\n"
    common = BASE + r'''
main() {
    local evidence rc capture_rc actual
    local -a statuses
    evidence=$(/usr/bin/mktemp -d /tmp/ilinux31ad-ILINUX31AD_PHASE.XXXXXX) || return 1
    evidence=$(cd "$evidence" && /bin/pwd -P) || return 1
    readonly evidence
    printf 'Private evidence directory: %s\n' "$evidence"
    base_guard >"$evidence/guard.txt" 2>&1
    rc=$?
    printf '%s\n' "$rc" >"$evidence/guard.exit"
    test "$rc" = 0 || { printf '%s\n' 'STOP: fresh lab-paired guard failed; no write.'; return "$rc"; }
    readonly ILINUX_OS ILINUX_DATA ILINUX_ORIGINAL ILINUX_BOOT
    hash_file /usr/bin/kmutil >"$evidence/kmutil.sha256" || return 1
    /usr/bin/sw_vers -buildVersion >"$evidence/recovery-build.txt" || return 1
'''
    common = common.replace("ILINUX31AD_PHASE", phase)
    if phase == "install":
        prepare = "    readonly image=\"$evidence/ilinux-31ad.macho\"\n"
        prepare += "    readonly expected_bytes=" + str(p["bytes"]) + "\n"
        prepare += "    readonly expected_hash=" + shlex.quote(p["sha256"]) + "\n"
        prepare += "    readonly source_url=" + shlex.quote(p["url"]) + "\n"
        prepare += r'''    /usr/bin/curl --fail --location --max-time 90 --proto '=http,https' \
        --output "$image" "$source_url" >"$evidence/transfer.stdout" \
        2>"$evidence/transfer.stderr" || {
        printf '%s\n' 'STOP: transfer failed; no write.'; return 1; }
'''
        command = '/usr/bin/kmutil configure-boot --custom-boot-object "$image" --volume "$ILINUX_OS"'
        argv = r'''    printf '%s\n' '/usr/bin/kmutil' 'configure-boot' '--custom-boot-object' \
        "$image" '--volume' "$ILINUX_OS" >"$evidence/argv.txt" || return 1
'''
        success = "INSTALL_SUCCESS_ENTRY_NOT_OBSERVED"
    else:
        prepare = '    readonly image="$ILINUX_BOOT"\n    readonly expected_bytes=3932160\n'
        prepare += "    readonly expected_hash=" + ROLLBACK_SHA + "\n"
        command = '/usr/bin/kmutil configure-boot --custom-boot-object "$image" --raw --entry-point 2048 --lowest-virtual-address 0 --volume "$ILINUX_OS"'
        argv = r'''    printf '%s\n' '/usr/bin/kmutil' 'configure-boot' '--custom-boot-object' \
        "$image" '--raw' '--entry-point' '2048' '--lowest-virtual-address' '0' \
        '--volume' "$ILINUX_OS" >"$evidence/argv.txt" || return 1
'''
        success = "ROLLBACK_SUCCESS_EXECUTION_NOT_OBSERVED"
    check = r'''    # Verify this same resolved, readonly pathname immediately before invocation.
    test ! -L "$image" && test -f "$image" || return 1
    test "$(/usr/bin/stat -f %z "$image")" = "$expected_bytes" || {
        printf '%s\n' 'STOP: image size mismatch; no write.'; return 1; }
    actual=$(hash_file "$image") || return 1
    test "$actual" = "$expected_hash" || {
        printf '%s\n' 'STOP: image hash mismatch; no write.'; return 1; }
    printf 'image=%s\nbytes=%s\nsha256=%s\n' "$image" "$expected_bytes" "$actual" \
        >"$evidence/input.txt" || return 1
'''
    tail = "    printf '%s\\n' '" + success + ": configure and Full/Permissive postcheck passed.'\n"
    tail += "    printf '%s\\n' 'No automatic reboot. Keep raw evidence local; follow the separately reviewed human sequence.'\n}\nmain\nILINUX31AD_RC=$?\n"
    tail += "printf '31AD " + phase + " block exit: %s\\n' \"$ILINUX31AD_RC\"\nexit \"$ILINUX31AD_RC\"\n" + label + "\n"
    return head + common + prepare + check + argv + CAPTURE.replace("ILINUX31AD_COMMAND", command) + tail


def page(install: str, rollback: str) -> str:
    out = """<!doctype html><meta charset="utf-8"><title>31AD reviewed Recovery phases</title>
<h1>31AD Recovery phases — review and explicit human authorization required</h1>
<p>Copy ONE complete phase. Quit the browser, open Utilities → Terminal and paste
once. The second phase is independent and must be copied again after the reboot.
Do not run either phase because this page exists. These commands change only the
guarded lab custom boot object. Macintosh HD must remain Full Security.</p>
<p>First test clipboard retention with <code>printf '%s\\n' ILINUX_CLIPBOARD_OK</code>.
Do not manually type a truncated block. Native clipboard behavior remains NOT RUN.</p>
"""
    for name, text in (("install", install), ("rollback", rollback)):
        out += "<h2>" + name.title() + " — separately selected phase</h2>\n"
        out += '<button onclick="document.getElementById(\'' + name + '\').select()">Select COMPLETE ' + name + ' block</button>\n'
        out += '<p>Press Command-C, quit browser, open Terminal, press Command-V once.</p>\n'
        out += '<textarea id="' + name + '" readonly rows="24" style="width:98%;font-family:monospace">' + html.escape(text) + '</textarea>\n'
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        ap.error("output must be a new directory")
    p = validate(json.loads(args.profile.read_text()))
    install, rollback = render(p, "install"), render(p, "rollback")
    args.output.mkdir(parents=True)
    (args.output / "install-paste.txt").write_text(install)
    (args.output / "rollback-paste.txt").write_text(rollback)
    (args.output / "recovery.html").write_text(page(install, rollback))
    (args.output / "render.json").write_text(json.dumps({
        "schema": "ilinux31ad-write-render-v1",
        "profile_sha256": hashlib.sha256(args.profile.read_bytes()).hexdigest(),
        "install_sha256": hashlib.sha256(install.encode()).hexdigest(),
        "rollback_sha256": hashlib.sha256(rollback.encode()).hexdigest(),
        "execution": "NOT_RUN", "human_authorization_required": True,
        "independent_m1_review_required": True,
    }, sort_keys=True, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
