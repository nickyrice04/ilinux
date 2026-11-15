# After 31AP: Preboot lifecycle for a complete lab transaction

November 15, 2026. Original offline design only. No command, mount, staging,
security/default change or installation was performed. `31AQ` is a proposed
new transaction name, not an authorized or physically ready attempt.

## Evidence and the remaining integration gap

M1 result `459161d` establishes one actual 31AP conditional read-only collection,
initial-admission validation and owned mount cleanup. Its final state is
`UNMOUNTED`. It does not establish comparison-key enrollment, installation,
boot021 restoration, Aura/Linux entry or multicore execution.

The original full collector in `tools/boot-object31aj-native/state.c` still
requires the role-selected Preboot volume to have a safe mounted path, then
derives the selected lab object from private lab-group, NSIH and COIH fields.
The 31AP executable deliberately exposes only conditional diagnosis and result
validation. Chaining that diagnostic and the old full shell is insufficient:
the diagnostic releases its mount before the first full snapshot, and its
binary lacks the full transaction CLI.

The next implementation should therefore compose the successful identity and
mount primitives with a **new full transaction executable**, retaining the
qualified 31AO parser and the original phase validators. Do not broaden the
31AP diagnostic CLI or edit a frozen source to make an old package appear new.

## What the public implementation actually establishes

The Asahi installer selects unique APFS role volumes, mounts Preboot before
collecting OS metadata, and uses the refreshed mount point. Its normal mount
wrapper invokes `diskutil mount`, followed by `diskutil info -plist`. These
support selection, preparation and re-observation; they do not qualify our
private read-only mount as a writable installation mount. Sources:
[OS enumeration](https://raw.githubusercontent.com/AsahiLinux/asahi-installer/main/src/osenum.py),
[mount wrapper, revision e93743d5](https://github.com/AsahiLinux/asahi-installer/blob/e93743d52178b3e26e428fa05174ef549abf30cb/src/diskutil.py).

At pinned revision `e93743d52178b3e26e428fa05174ef549abf30cb`, step two checks
paired 1TR, invokes lab-targeted `bputil`, then raw `kmutil configure-boot`.
Its external-volume branch explicitly mounts Preboot and copies administrative
support data into iSCPreboot. Its later writable remount targets the stub
System volume for installer housekeeping. Neither operation should be copied
into this internal full-macOS lab. Source:
[step2.sh](https://github.com/AsahiLinux/asahi-installer/blob/e93743d52178b3e26e428fa05174ef549abf30cb/src/step2/step2.sh).

**Unknown:** whether this target Recovery's `kmutil configure-boot` mounts an
unmounted Preboot volume itself, or promotes an existing read-only mount. The
public script does not establish either behavior. It normally arrives with
Preboot mounted already. Do not claim that omission of an explicit internal
mount proves automount support.

The installed SDK's `mount(8)` documents that `rdonly` prevents even root writes,
and `mount_apfs(8)` accepts the generic options except its documented exclusions.
Thus a successful RO observer mount alone is not evidence that a subsequent
filesystem writer can use it. The design below removes that dependency rather
than testing an unqualified automatic upgrade during installation.

## Proposed implementation boundary

Build a new original controller that includes byte-identical frozen 31AM
identity/mount helpers and the exact 31AO-generated collector. Add a small
session manager and explicit full transaction CLI. A useful private API is:

```
begin_observation -> owned RO or verified borrowed mount
validate_initial / validate_before_restore
begin_authorized_mutation -> verified RW capability
run_one_fixed_apple_operation -> bounded result
collect_and_validate_postcondition
finish_session -> owned cleanup verified or explicit uncertainty
```

The public output should contain only fixed phase/ownership/mode/outcome labels,
exit classes, verified-postcondition booleans and `native_ready=false` until the
separate reviewed handoff admits a boot. Private identities and paths remain
in memory. Existing finite snapshots and the original random comparison key
remain private on lab Data, outside Git.

For the first implementation, handle the actual observed unmounted/empty state.
Accept a borrowed existing RW mount only if that branch receives equivalent
identity tests; never unmount it. Refuse a borrowed RO mount for mutation rather
than upgrading or removing a mount the controller does not own. Do not turn a
foreign-mount case into a force, repair, global unmount or guessed pathname.

## First Recovery visit: install once

1. Verify exact kit/profile/helper/candidate/rollback pins and the current
   Recovery/root/model, unique APFS roles, lab/original System groups, common
   container, lab Data and Preboot identities. Retain all previous guards.
2. In a new canonical held scratch directory, prepare and verify an owned RO
   mount using the successful 31AM sequence. Collect a fresh keyless snapshot
   and validate initial admission. The previous photo is not an enrollment
   snapshot for this new executable/profile.
3. Create a **new** transaction state directory and system-random 32-byte key;
   retain root ownership/modes and no-overwrite checks. Collect the key-bound
   initial snapshot and persist its baseline/profile. Never reset old state,
   adopt an old comparison key, or erase a spent attempt marker.
   Persist the files and containing directory with explicitly checked durability
   operations before admitting a writer. Atomic `mkdir`/`rename` visibility alone
   does not prove power-loss durability. A failed or incomplete durable marker
   must remain spent; a timeout must not become permission to repeat the writer.
4. After these guards and the separate write authorization, release only the
   owned RO mount, verify actual disappearance and unchanged volume identity,
   then create an owned RW mount at the bound scratch child. Verify the APFS
   source, role/UUID/container, mount-root identity and actual `MNT_RDONLY`
   clearance. No probe file needs to be written. Recollect and validate the
   initial state against the private baseline before the writer marker.
5. Persist the one-shot candidate marker, then run only the fixed lab-targeted
   Mach-O `kmutil configure-boot` operation. Credentials stay on `/dev/tty`;
   recording stays off for authentication. Do not borrow Asahi's retry loop.
6. Reobserve the mount after the child returns, then collect and persist the
   key-bound post-write snapshot. Require exact candidate identity, enabled lab
   CTRR and the original semantic/private-metadata preservation comparisons.
   The collector only reads, so it can run on the verified owned RW mount;
   another RO/RW cycle is unnecessary for this readback.
7. Release only the owned mount nonforcibly and verify actual unmounted state.
   The candidate boot cue requires **both** validated postcondition and known
   cleanup. A zero `kmutil` exit alone is insufficient. No restart is automated.

Hold the parent scratch/underlying-child descriptors across the session. Close
temporary descriptors referring to the mounted filesystem before unmounting;
otherwise the observer itself can make a nonforced cleanup busy. Recheck the
mount through fresh descriptors and kernel metadata before every Apple command
and cleanup. A mount moved or replaced by an Apple tool is uncertainty, not
permission to clean up an unrelated mount.

## One native window and independent restoration

Use the already reviewed external observation deadline and at most one boot.
M1 may record the M5 screen after authentication is over. Distinguish an Aura
entry marker, Linux entry, CPU census and concurrent work; the Apple logo alone
proves none of them. The independently accessible restore page must exist
before installation, without depending on USB proxy or the native guest.

On the second paired Recovery visit, start a new ephemeral mount session, but
reuse **the same new transaction's** persisted profile, key and baseline:

1. Obtain an owned RO observation mount and validate `before-restore`.
2. If exact boot021 plus disabled lab CTRR already validate, perform no writer;
   finish owned cleanup and report the separate default-restoration step.
3. Otherwise obtain the authorized, identity-verified RW capability as above.
   If lab CTRR is enabled, bind the lab group privately, persist its one-shot
   marker, invoke only lab-targeted `bputil -c`, and validate/persist `raw-policy`.
   If disabled, skip that command and validate the same phase. Unknown refuses.
4. Persist the boot021 marker, run the fixed raw boot021 `kmutil` operation,
   then require exact boot021, disabled lab CTRR and preserved Original policy
   through `restored` validation. Finish owned cleanup before success.
5. Restore/confirm Macintosh HD as default through the separately authorized
   Startup Disk procedure. That is not established by a payload snapshot.

Every nonzero exit, interruption or ambiguous command result preserves state
and the spent marker. A guarded readback may still be collected; it does not
authorize a retry. Independent restoration proceeds only if its existing
baseline/security/identity validators admit the observed state.

## Authority and limits

31AP's read-only authorization does not cover this write phase. The concrete
later authorization must name temporary writable access to the **shared**
Preboot volume, one lab-only candidate installation, one visible boot, the
conditional lab-only CTRR preparation and one boot021 restoration, plus the
temporary lab/default return. The helper itself writes no Preboot files; only
the exact Apple commands receive that capability. No Original System write,
Original security change, raw device write, partition change, external-volume
workaround, firmware replacement or security-check bypass is part of this plan.

The retained comparisons establish their documented Original Full/CTRR and
semantic/protected-metadata properties, not a hash of every Original file.
The new controller must add a profile/key/domain-bound private commitment to
the exact lab/Original group and volume UUIDs, lab Data and Preboot identities,
and stable container identity across visits. Keep those values only in memory;
persist only the keyed commitment. Derive current device names afresh because
enumeration may change across boots. Do not publish IDs or silently claim the
old boolean `target_binding_verified` supplies this cross-visit binding.

## Focused offline acceptance controls

Implement the composition now using fixtures and original code, then review:

- Full real-parser initial admission, key baseline, candidate postcondition and
  rollback phases, including the actual rendered scratch name and all copied
  input identities. Preserve every old pin, artifact and spent-state directory.
- Owned RO release/RW acquisition and cleanup; missing/contradictory mount
  state, wrong source/UUID/role/container, symlinks, replaced scratch/overlay,
  unexpected RO after RW request and every partial command outcome.
- No writer before complete admission, durable markers and fresh keyed
  validation; no cleanup of borrowed mounts; no automatic retries or boot.
- Original policy or protected metadata changes, lab metadata changes outside
  permitted CTRR/selected-object transitions, wrong selected objects and
  unavailable post-write readback all refuse readiness.
- Restore idempotence, unknown CTRR refusal, conditional `bputil` skipping,
  retained comparison-key binding, interrupts and secret-free finite output.
- Default/help and package preparation remain inert; exact production package
  and independent install/restore boxes validate from a clean Git checkout.

Offline fixtures cannot prove the target APFS RW transition or Apple's actual
mutation behavior. Those become explicit measured stages of the later one-shot
authorized transaction, with known cleanup required before the native cue.
