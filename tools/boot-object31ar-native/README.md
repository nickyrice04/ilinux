# 31AR fixed lab boot transaction controller

This is original source for a new controller around the qualified 31AO policy
collector and existing 31AJ object recognizer/phase validators. It preserves all
143 previous source pins, generates the qualified state with exact reversal
proof, and leaves every old tool, receipt and consumed transaction unchanged.

Default/help and result validation are inert. The live transaction mode is for
the exact model, distinct named lab/Original groups and paired lab Recovery;
it must not be run on the desktop. Building or testing does not authorize its
live mode. No live mode is used by the test runners.

The interface expected by the separately pinned one-paste renderer is:

```
ilinux31aj-reader --transaction install|restore \
  --profile ABSOLUTE_SCRATCH/profile.json --scratch ABSOLUTE_SCRATCH
```

Scratch is physically canonical, current working directory, private 0700 with
no extended ACL, and named `ilinux31ar.` followed by 6–32 alphanumeric bytes.
Profile binds the exact helper, unchanged matched Aura/Linux candidate and
boot021. Restore needs only helper, profile and boot021, never the candidate.

Persistent state is a new `ilinux31ar-state` child of the lab Data volume's
`private/var/db`. The existing parent is observed, never repaired or chmodded.
It must be root-owned, not group/world writable, ACL-free and bound to held
descriptors. The earlier shared project parent is user-owned on the actual lab,
so it is intentionally not used as the trusted transaction journal anchor.

Install requires exact initial 31AF admission under an owned read-only Preboot
mount. It creates fresh private state, a fresh 32-byte own random comparison
key, the keyed policy baseline and profile, and a domain/profile/key-bound
commitment to the exact stable group/volume/container UUIDs. Identifiers stay in
memory; device names are not part of the cross-visit commitment. The journal
stores only own keys, commitments and finite semantic snapshots. Files are
exclusively created with 0600/no ACL, fsynced and fully synchronized; directory
fsyncs preserve dependency order. A failed or partial name is retained, never
overwritten, adopted or reset. A private lock prevents concurrent sessions.

The controller nonforcibly releases only its owned RO mount, verifies absence,
then obtains an owned RW mount and verifies its APFS source/identity and actual
read-only flag clearance. Existing foreign mounts are refused without touching
them. The full baseline is checked again before the one-shot durable marker;
work/state/mount and artifact bindings are checked again after that marker,
immediately before the fixed Apple operation. No force, foreign mount upgrade,
unmount, retry, raw disk access, partition, firmware or Original policy writer
exists in the controller.

Only fixed lab-targeted `kmutil` candidate installation, conditional lab-targeted
`bputil -c`, and raw boot021 installation are available. The Apple child uses
the controlling `/dev/tty` for authentication and local output; the controller
neither reads credentials nor saves Apple TTY output. Recording must remain off
during the complete Recovery/authentication/Apple-command phase. Terminal
foreground ownership and termios are restored after exit, interruption and
timeout. The writer deadline is 180 seconds including local authentication;
the native observation deadline remains the unchanged profile's 90 seconds.
These are separate deadlines. No restart or Startup Disk action is automated.

Every attempted writer receives a fresh guarded readback even after nonzero,
timeout or interruption where observation is possible. Its marker stays spent.
Candidate success needs exact candidate/CTRR and preserved Original/private
metadata, zero writer exit and known mount cleanup. An independent restore
session reuses the same private profile/key/baseline/target commitment. Exact
boot021 with disabled CTRR is a read-only no-op; enabled CTRR permits one fixed
lab preparation, then one raw boot021 writer and exact final validation. A
previously spent writer is never repeated. Restoration is not confirmed by
command exit alone, and payload restoration does not establish Startup Disk.

The finite result contains only fixed labels, booleans and exit classes. Its
strict `--validate-transaction-result FILE --operation install|restore` observer
accepts both a finite refusal for safe display and a complete success. A
display pass is not transaction success. Synthetic results never qualify as
live results. The shell retains scratch on any refusal or uncertain cleanup.

## Offline tests

`test_native.py` executes the complete actual controller, collector, typed
parsers and original object/phase validators using real own 31AF/candidate/
boot021 artifacts read as data, fresh workspace state, and synthetic APFS/
policy/mount/writer backends. Both the backend guard and an independent observer
exec guard prevent synthetic data from selecting live system commands, even
when a post-write phase is missing. Fixture keys are newly generated own data.

`test_pty.py` compiles a separate test-only main against the same child-handoff
function. Only a fixed own prompt/read/sleep fragment runs: no Apple command,
mount or policy query. It checks foreground input, termios restoration on
timeout/interruption, quick nonzero exit and a child dying before the gate, plus
APFS snapshot source grammar. The system sandbox may deny foreground-terminal
ioctls; such denial must be reported and the harmless PTY runner reviewed
separately, not treated as passing authentication coverage.

Build normal and sanitizer variants into fresh ignored output directories:

```bash
python3 -I -B tools/boot-object31ar-native/build.py \
  --output build/boot-object31ar-native/production-v2
python3 -I -B tools/boot-object31ar-native/build.py \
  --output build/boot-object31ar-native/sanitized-v1 --sanitize
```

Run from the repository root with the genuine retained own artifacts below.
Every output directory must be new. The 31AF file contains the genuine project
payload inside entirely synthetic IMG4 framing, not an Apple manifest.

```bash
python3 -I -B tools/boot-object31ar-native/test_native.py \
  --compiled build/boot-object31ar-native/production-v2/ilinux31aj-reader \
  --output build/boot-object31ar-native/review-normal-v1 \
  --reference31af build/boot-object31aj-native/validation-v1/synthetic-img4-OTHER-exact31af.bin \
  --candidate build/31aj-m5-prepared-final/candidate.macho \
  --rollback build/31aj-m5-prepared-final/m1n1-boot021.bin
python3 -I -B tools/boot-object31ar-native/test_native.py \
  --compiled build/boot-object31ar-native/sanitized-v1/ilinux31aj-reader \
  --output build/boot-object31ar-native/review-sanitized-v1 --sanitize \
  --reference31af build/boot-object31aj-native/validation-v1/synthetic-img4-OTHER-exact31af.bin \
  --candidate build/31aj-m5-prepared-final/candidate.macho \
  --rollback build/31aj-m5-prepared-final/m1n1-boot021.bin
python3 -I -B tools/boot-object31ar-native/test_pty.py \
  --build build/boot-object31ar-native/production-v2 \
  --output build/boot-object31ar-native/review-pty-v1
```

Missing references are a coverage limit to report, not permission to mock an
identity, reset an old transaction or substitute a different candidate. The
test-only fresh workspace state is removed by its harness; real persistent
Recovery state is never erased or reset by these tools.

Neither synthetic execution nor Recovery admission proves actual Apple writer
behavior, APFS RW behavior on the target, Aura/Linux entry, multicore execution
or macOS performance parity. Those remain distinct physical observations.
