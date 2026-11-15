# M1: conditional read-only Preboot fix — offline review first

November 14, 2026. User authorized preparation, offline tests and this handoff.
No new lab staging, temporary Startup Disk change, mount or physical visit has
run or is authorized by publication. Macintosh HD must remain Full Security.
Its desktop/default return after31AL is human-confirmed; boot021 restoration is
still outstanding. Do not infer a boot021 installation or boot the old lab object.

## What changes

31AL stopped at its lexical Preboot MountPoint guard, before policy/admission or
Aura/Linux. The actual path remains unknown. This new companion conditionally
prepares the shared container's Preboot and then runs the unchanged collector
and initial-admission checks. It does not install, restore or boot Linux.

The new preflight corroborates metadata with the kernel mount table. An absent
`Mounted` plist key is not false: the fresh macOS shape observation found that
key absent. Existing valid mounts are left untouched. Only an empty path plus
positively established unmounted state and repeated identity checks can reach
the single read-only mount attempt. Other unsafe/inconsistent states stop.

The proposed future mount uses Apple's fixed system mount helper with read-only,
nobrowse and nofollow options at the new private scratch child. It does not call
Disk Arbitration's normal mount frontend, fsck, repair, force or remount commands.
The helper rechecks actual source/mount point and kernel read-only state, then
runs the original diagnostic once. It releases only its own verified mount and
reports cleanup success or uncertainty. No universal guarantee about firmware,
private filesystem internals or Recovery tool availability follows from an SDK
build. Missing system tools or unsupported observations are refusals, not a
reason to fall back to a broader command.

## Focused offline review

Pull the handoff in a clean checkout, preserving unfinished work and every old
receipt/consumed state. Read `native/boot/attempt31am/findings.md`, the build,
delivery and offline verification records, and all new source under
`tools/boot-object31am-native/` and `tools/recovery31am/`.

Verify the new fixed source inventory and all retained92 bindings. Do not edit
the old inventories or rebuild the unchanged Aura/Linux/RAM-root candidate.
Reuse the old86-method review and the focused Preboot lexical regression result.

Run only the changed workspace suites with local temporary files under build:

```bash
python3 -I tools/boot-object31am-native/test_native.py
python3 -I tools/recovery31am/test_render.py
python3 -I tools/recovery31am/test_package.py
```

These compile/test original synthetic backends. Never invoke the production
`--preboot-diagnose` mode on M1 or the macOS desktop. Review partial mount failures,
mount overlay/device identity, cleanup refusals, absent metadata keys, bounded
kernel-table observations and output privacy. Only the strict new outer-result
validator may display captured output; no raw file, stderr, path or identifier.

The new local kit is `build/ilinux-31am-diagnostic/`, containing only
`ilinux31aj-reader` and `profile.json`. Verify both against `delivery.json`.
The legacy basename is required by the unchanged self/profile binding. This is
a new helper/profile pair: do not mix it with31AL or substitute a locally built
binary for the pinned producer binary. One tiny local transfer is sufficient;
no candidate, rollback, RAM root or private key needs retransmitting.

Prepare and verify an inert page in a new directory:

```bash
python3 -I tools/recovery31am/package.py --prepare --kit build/ilinux-31am-diagnostic --output build/31am-m1-pages
python3 -I tools/recovery31am/package.py --page build/31am-m1-pages/recovery.html --check-only
/bin/bash -n build/31am-m1-pages/diagnose-paste.txt
```

Compare all three output hashes to the M5 offline receipt. `--check-only` creates
no socket. Publish sanitized review results and any actionable finding; keep
actual staging, Recovery/mount/cleanup, install/restore/Linux/SMP/performance
NOT RUN. Do not start a page server, camera, proxy or restart either Mac now.

## Later physical sequence — held for review and authorization

After focused review passes, M5 can obtain one concrete combined authorization
for the new two-file lab Data copy, temporary lab default/Original return, and
one conditional read-only Preboot preparation plus diagnostic. A mount changes
mount-table state even though filesystem writes are not requested; describe it
candidly. No installation, rollback, security-mode change or Linux boot belongs
to that authorization. The container's Preboot is shared with Original.

The reviewed `package.py --stage --kit ...` mode copies only the two files into
the new fixed lab Data `31am-diagnostic` directory. It reuses31AL's unchanged
staging target guards and private modes with a new destination name. It never
overwrites31AL's kit or transaction state. Authentication stays in the human's
Terminal; never ask for credentials in chat.

M1 then serves only the exact new one-box page with the reviewed bounded server
(`--page`, explicit private `--bind`, `--port 8031`, `--seconds 1800`). The route
remains `/31aj`; the visible title must identify31AM's conditional Preboot check.
Give the complete live URL privately. M5 confirms kit/page and temporary lab
selection before the human shutdown/held-power Options/Continue cue. No M1
restart or USB proxy is needed, and the old lab object must not be booted.

In paired lab Recovery, copy the entire single box, quit the browser, open
Utilities Terminal and paste once. No clipboard exercise, second install box,
hand-edited disk number, extra command or automatic retry. Capture only emitted
safe helper/shell JSON and actual exit information before leaving. Preserve
credentials, policy text, identifiers and private paths outside any capture.

If the result reports cleanup failure or uncertainty, stop and preserve the
finite result. Do not force an unmount, delete scratch directories recursively,
weaken a guard or claim the mount is absent/read-only without verified evidence.
Report the condition before any further action. The proposed approved return
can then shut down Recovery, hold power to startup options, and select
**Macintosh HD once**, never the lab tile. Restore Macintosh HD's default in
its own System Settings after reaching its desktop. This avoids depending on
Recovery's Startup Disk UI writing through a possibly remaining read-only
Preboot mount; mount-table state belongs to that Recovery session. Do not add
manual mount commands to make the UI work. Successful admission still does not
authorize installation or Linux boot.

Finally restore Macintosh HD as default and return to its desktop through the
approved flow, camera off during credentials and personal desktop use. Confirm
desktop and default separately without another routine policy command. M5 uses
the result to decide safe deployment of the already-matched Aura/Linux stack.
