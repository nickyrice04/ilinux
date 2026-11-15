# 31AM conditional read-only Preboot page

This original MIT renderer prepares inert text and a single-box HTML page for
the conditional Preboot companion. It performs no staging, service, mount,
Recovery command, installation, security change or native boot on import or
render. Physical execution requires independent review and explicit authorization
for the conditional mount and Recovery visit.

`render(value)` and `page(value)` retain the strict existing profile format. The
candidate and rollback entries remain identity metadata; this workflow reads
only the new diagnostic helper and public profile. The fixed new kit is
`/Volumes/iLinux Boot Lab - Data/Users/Shared/iLinuxBoot/31am-diagnostic`.
The unchanged profile loader requires the helper basename `ilinux31aj-reader`;
its new size and hash must match the separately pinned companion build.

## Frozen flow and changed entrypoints

The renderer reads and SHA-256-verifies the frozen 31AL renderer through bounded
no-follow descriptors before compiling it. That renderer verifies its own
frozen 31AK/31AJ dependencies. The original canonical work-directory and held-CWD
identity flow is retained byte-for-byte, with only the new `ilinux31am` scratch
prefix. Existing source pins, kit, page and transaction state are untouched.

The new single block checks root, exact kit/profile/helper pins and distinct
System mounts, creates and binds private scratch, and copies only the helper and
profile. It invokes these two companion modes, once each:

```text
--preboot-diagnose --target-volume LAB --original-volume ORIGINAL --profile P --scratch WORK
--validate-result WORK/diagnostic.json --profile P
```

Only the native companion can decide whether a mount is needed, issue its fixed
read-only mount command, verify the resulting identity and read-only state,
run the existing guarded diagnostic, and attempt cleanup of its own mount. An
already mounted valid volume stays mounted. Other unsafe or inconsistent state
is a refusal. These native behaviors require the companion's independent C
fixture tests; the renderer does not duplicate or broaden the native checks.

The shell captures helper stdout with noclobber semantics and suppresses stderr
and shell signal/exec diagnostics. It never prints a raw capture. It checks the
held work directory and then displays only the companion's strictly validated,
bounded outer result before cleanup. A valid structured refusal validates with
exit0 but remains a refusal. Diagnosis exit0 requires the native success
conditions; exit2 is a structured stop. Any other child exit remains a stop
even if a finite result can be displayed.

The outer `ilinux31am-preboot-result-v1` record reports the explicit mount,
read-only verification, uncertainty and cleanup fields plus the existing nested
diagnostic or null. A read-only mount changes mount-table state, so the shell
does not label the whole operation with the old generic `read_only` or
`writes_authorized` flags. Its separate finite
`ilinux31am-shell-result-v1` record reports stage/child exit, no requested
Preboot filesystem writes, unchanged boot/security settings, and false readiness and
private-value-return flags. It is not evidence that native mount cleanup passed.
Its `preboot_write_requested` flag does not deny the private scratch copies,
permission changes and fixed-file cleanup performed by the shell.

## Cleanup and failures

The native companion owns `WORK/preboot`. The shell never mounts, unmounts,
recursively removes a directory, or tries to repair failed native cleanup. Its
existing fixed cleanup removes only `profile.json`, `ilinux31aj-reader` and
`diagnostic.json` while work identity still matches; `rmdir WORK` then succeeds
only if no native child remains. A replacement work directory stays untouched.

If the helper is interrupted, the result is missing/invalid or native cleanup is
refused, a mount may remain and its read-only verification may be incomplete.
The message says to stop and report rather than claim cleanup succeeded or
automatically retry. Never print a rejected capture, manually alter the mount,
use another volume or infer installation permission from a passing result.
Return through the separately authorized Macintosh HD/default procedure.

No baseline, comparison key, persistent transaction state, candidate/rollback
file, `kmutil`, policy-writing command or default-selection operation appears
in this block. It grants no native boot, installation or restoration permission.
Boot021 restoration is unaffected by this diagnostic workflow.

## Focused offline controls

```bash
python3 -I tools/recovery31am/test_render.py
```

The new focused tests create only disposable workspace fixtures and synthetic
helper processes. They cover the new exact CLI/scratch binding, existing-mount
and owned-cleanup display models, retention of a leftover child, killed-helper
and unexpected exits, private/extra/oversized/symbolic output refusal, immutable
source/transitive bindings, exact WORK projection, Bash syntax and one inert
textarea. No diskutil, mount, policy command or native live mode runs. The fake
validator models the shell display boundary only; it does not qualify the real
native 20-key validator. The old 19 renderer methods and unchanged 86-method
review are reused rather than rerun.

November 14 result: all **12 focused methods PASS** in 14.215 seconds. No live
operation ran and no frozen source was edited.

The parent package controller owns source admission, offline kit/page preparation,
socket-free checking and any separately authorized future Data staging or page
serving. Neither `render(value)` nor `page(value)` performs those actions.
