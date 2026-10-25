#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Render reviewed, pinned read-only Recovery paste blocks; never run them."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import shlex
from urllib.parse import urlsplit

ROLES = ("flat31ac", "nested31ad", "rawboot021")
ORIGINAL = (180224, "261d44447442f32ba6c41bbf0f69179e8c9eb4c33507b60762f0ea8c2e54ab72")
ROLLBACK = (3932160, "ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664")


def validate(profile: dict) -> dict:
    if set(profile) != {"schema", "images"} or profile["schema"] != "ilinux31ad-diagnose-v1":
        raise ValueError("unsupported or extra profile fields")
    if set(profile["images"]) != set(ROLES):
        raise ValueError("all three named original-image controls are required")
    for role in ROLES:
        item = profile["images"][role]
        if set(item) != {"bytes", "sha256", "url"}:
            raise ValueError("every image needs exact bytes, sha256 and URL only")
        if type(item["bytes"]) is not int or not 0 < item["bytes"] <= 8 * 1024 * 1024:
            raise ValueError("invalid or excessive image length")
        if not isinstance(item["sha256"], str) or not re.fullmatch("[0-9a-f]{64}", item["sha256"]):
            raise ValueError("invalid SHA-256")
        if not isinstance(item["url"], str) or any(ord(c) < 32 for c in item["url"]):
            raise ValueError("invalid URL")
        u = urlsplit(item["url"])
        if u.scheme not in ("http", "https") or not u.hostname or u.username or u.password or u.fragment:
            raise ValueError("URL must be HTTP(S), without credentials or fragment")
    for role, fixed in (("flat31ac", ORIGINAL), ("rawboot021", ROLLBACK)):
        p = profile["images"][role]
        if (p["bytes"], p["sha256"]) != fixed:
            raise ValueError("historical control pin changed")
    return profile


def render(profile: dict) -> str:
    p = validate(profile)
    calls = "\n".join("    inspect_one " + " ".join(shlex.quote(str(x)) for x in
        (role, p["images"][role]["bytes"], p["images"][role]["sha256"], p["images"][role]["url"]))
        + " || return $?" for role in ROLES)
    script = r'''# READ-ONLY FILE PARSING ONLY. No installation, policy or Startup Disk operation.
/bin/bash <<'ILINUX31AD_DIAGNOSE_END'
set -u
umask 077
PATH=/usr/bin:/bin:/usr/sbin:/sbin
export PATH
hash_file() {
    if test -x /sbin/sha256; then /sbin/sha256 -q "$1"
    else /usr/bin/shasum -a 256 "$1" | /usr/bin/awk '{print $1}'; fi
}
inspect_one() {
    local label="$1" bytes="$2" expected="$3" url="$4" image actual rc
    image="$ILINUX31AD_DIR/$label.macho"
    /usr/bin/curl --fail --location --max-time 90 --proto '=http,https' \
        --output "$image" "$url" >"$ILINUX31AD_DIR/$label.transfer.stdout" \
        2>"$ILINUX31AD_DIR/$label.transfer.stderr" || {
        printf '%s: transfer failed; no image parsed.\n' "$label"; return 1; }
    test ! -L "$image" && test -f "$image" || return 1
    test "$(/usr/bin/stat -f %z "$image")" = "$bytes" || {
        printf '%s: size mismatch; no image parsed.\n' "$label"; return 1; }
    actual=$(hash_file "$image") || return 1
    test "$actual" = "$expected" || {
        printf '%s: hash mismatch; no image parsed.\n' "$label"; return 1; }
    # This exact resolved literal pathname is pinned and is the one passed below.
    printf 'image=%s\nbytes=%s\nsha256=%s\n' "$image" "$bytes" "$actual" \
        >"$ILINUX31AD_DIR/$label.input.txt" || return 1
    printf '%s\n' '/usr/bin/kmutil' 'inspect' '-B' "$image" \
        '-S' "$ILINUX31AD_DIR/absent-system.kc" \
        '-A' "$ILINUX31AD_DIR/absent-aux.kc" \
        '--allow-missing-collections' '--show-mach-boot-properties' \
        >"$ILINUX31AD_DIR/$label.argv.txt" || return 1
    /usr/bin/kmutil inspect -B "$image" \
        -S "$ILINUX31AD_DIR/absent-system.kc" \
        -A "$ILINUX31AD_DIR/absent-aux.kc" \
        --allow-missing-collections --show-mach-boot-properties \
        </dev/null >"$ILINUX31AD_DIR/$label.stdout" \
        2>"$ILINUX31AD_DIR/$label.stderr"
    rc=$?
    printf '%s\n' "$rc" >"$ILINUX31AD_DIR/$label.exit"
    printf '%s: inspector exit %s (not an acceptance or boot result).\n' "$label" "$rc"
    # A parser rejection is data, so continue to the other controls.
    return 0
}
main() {
    ILINUX31AD_DIR=$(/usr/bin/mktemp -d /tmp/ilinux31ad-diagnose.XXXXXX) || return 1
    ILINUX31AD_DIR=$(cd "$ILINUX31AD_DIR" && /bin/pwd -P) || return 1
    readonly ILINUX31AD_DIR
    hash_file /usr/bin/kmutil >"$ILINUX31AD_DIR/kmutil.sha256" || return 1
    /usr/bin/sw_vers -productVersion >"$ILINUX31AD_DIR/recovery-version.txt" || return 1
    /usr/bin/sw_vers -buildVersion >"$ILINUX31AD_DIR/recovery-build.txt" || return 1
''' + calls + r'''
    printf 'Diagnosis complete. Private evidence directory: %s\n' "$ILINUX31AD_DIR"
    printf '%s\n' 'Keep all raw logs local. No configure-boot, disk/policy query or boot occurred.'
}
main
ILINUX31AD_RC=$?
printf '31AD diagnosis block exit: %s\n' "$ILINUX31AD_RC"
exit "$ILINUX31AD_RC"
ILINUX31AD_DIAGNOSE_END
'''
    return script


def page(block: str) -> str:
    return """<!doctype html><meta charset="utf-8"><title>31AD read-only Recovery diagnosis</title>
<h1>31AD read-only Recovery diagnosis — NOT a boot instruction</h1>
<p>Copy the entire block below. Quit the browser; open Utilities → Terminal; paste
once. It downloads pinned original data, parses files, and writes private logs in
Recovery /tmp only. It does not install anything or query/change policy.</p>
<p>Native execution and clipboard retention: NOT RUN. First test clipboard with
the harmless block <code>printf '%s\\n' ILINUX_CLIPBOARD_OK</code>. If that survives
quitting the browser, reopen the page and copy the complete diagnosis block.</p>
<p>Do not type missing fragments. If the block is incomplete, cancel and recopy.
Never publish raw logs. The Mac does not restart automatically.</p>
<button onclick="document.getElementById('paste').select()">Select complete block</button>
<p>After selecting, press Command-C. Quit the browser, open Terminal and press
Command-V once. Selection alone does not copy.</p>
<textarea id="paste" readonly rows="24" style="width:98%;font-family:monospace">""" + html.escape(block) + "</textarea>\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        ap.error("output directory must be new")
    profile = validate(json.loads(args.profile.read_text()))
    block = render(profile)
    args.output.mkdir(parents=True)
    (args.output / "diagnose-paste.txt").write_text(block)
    (args.output / "diagnose.html").write_text(page(block))
    (args.output / "render.json").write_text(json.dumps({
        "schema": "ilinux31ad-recovery-render-v1", "mode": "READ_ONLY_DIAGNOSE",
        "profile_sha256": hashlib.sha256(args.profile.read_bytes()).hexdigest(),
        "block_sha256": hashlib.sha256(block.encode()).hexdigest(),
        "native_execution": "NOT_RUN", "installation": "DISABLED_NOT_RENDERED",
    }, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
