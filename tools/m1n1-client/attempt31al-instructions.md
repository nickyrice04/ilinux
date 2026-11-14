# M1: 31AL diagnostic-only offline review

Read `native/boot/attempt31ak-recovery-2026-11-14-result.md` and
`native/boot/attempt31al/findings.md`. The 31AK capability check passed; the
initial snapshot stopped before enrollment. Its failed branch is unknown.
Original desktop/default return is human-confirmed for that visit. Boot021
restoration is outstanding; do not relabel the prior 31AF observation as a
current query or a successful rollback.

## Review now; no restart

Use a clean checkout of this pushed revision, preserving unfinished work and all
old receipts. Review the new source under `tools/boot-object31al-native/` and
`tools/recovery31al/`, the new source inventory, SDK build receipt, delivery
manifest and offline verification. Verify every new inventory entry and that
all 72 retained 31AK source bindings remain exact. Do not edit older inventories,
rebuild the candidate, rerun unchanged suites, re-arm state or start a service.

Run the focused workspace-only tests from the checkout:

```bash
python3 -I tools/boot-object31al-native/test_native.py
python3 -I tools/recovery31al/test_render.py
python3 -I tools/recovery31al/test_package.py
python3 -I tools/recovery31al/test_stage.py
```

The native tests compile synthetic controls with the installed Apple SDK; they
must not use `--diagnose-snapshot`, root, diskutil or bputil against the host.
The production kit is a separate local two-file transfer, not a GitHub asset:
`build/ilinux-31al-diagnostic/{ilinux31aj-reader,profile.json}`. Compare its exact
bytes and SHA-256 to `native/boot/attempt31al/delivery.json`. No candidate,
rollback, RAM root or private key needs transferring again. Do not substitute a
newly compiled M1 binary for the pinned delivered helper.

With that exact local kit, prepare and check the inert page only:

```bash
python3 -I tools/recovery31al/package.py --prepare --kit build/ilinux-31al-diagnostic --output build/31al-m1-pages
python3 -I tools/recovery31al/package.py --page build/31al-m1-pages/recovery.html --check-only
/bin/bash -n build/31al-m1-pages/diagnose-paste.txt
```

The output directory must be new. Compare generated page/paste/profile hashes
against M5's offline receipt. No socket is created by `--check-only`. Report any
actionable finding and publish only sanitized review results. Keep native
Linux/SMP/performance and live Recovery checks marked NOT RUN.

## Later diagnostic visit — not authorized by this handoff

After review and explicit authorization, M5 can stage only the new helper and
public profile into the lab Data `31al-diagnostic` directory with the new
`--stage` mode. The mode cannot overwrite old state or boot objects. Staging is
not installation permission. Any authentication stays in the user's Terminal.

The bounded reviewed page server can then serve the new one-box page through
the retained `/31aj` route. Its title must say **31AL read-only diagnosis**.
Supply the complete private URL directly to the user; keep it out of Git. There
is no need to restart M1 or start a USB proxy. Keep recording off during all
authentication; a human photo of the finite safe JSON is sufficient. Do not
capture raw policy, identifiers, credentials or unrelated Terminal contents.

The user enters the lab's paired Recovery, copies the whole diagnostic box,
quits the browser, opens Terminal and pastes once. No clipboard test and no
second install box. Capture the safe helper JSON and shell-stage JSON displayed
before cleanup, including exit/status/stage/reason, then return to Macintosh HD
and its default selection. Never paste raw `diagnostic.json` or a private
snapshot. A validation error means stop, not print the rejected file.

This visit cannot install, restore, change policy/default or boot Linux.
`INITIAL_ADMISSION_PASS` would be evidence only, not write permission. A real
pairing/security/identity guard refusal stays a stop; no retry, broadening or
parser workaround without evidence and review. Wait for M5 to interpret the
result before proposing any new native attempt.
