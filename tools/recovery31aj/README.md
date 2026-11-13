# 31AJ guarded Recovery transaction — offline preparation

This directory is original MIT-licensed code. It prepares a future lab-only
transaction. Publishing a page, passing its tests or copying the kit does not
authorize its execution. No tool here invokes Recovery, firmware or boot commands.
`render.py` returns text; the shell text it returns is intended to change the lab
only after separate human authorization. Native readiness remains **HOLD**.

The observed initial lab payload is **31AF**, not boot021. Its historical CTRR
setting is unknown. The intended final state is exact raw boot021 with CTRR
disabled. That final state is a deliberate target, not a claim that an unknown
historical policy was restored byte for byte. Returning to the macOS desktop
does not prove either object restoration or the default Startup Disk selection.

## Components and bindings

* `profile.py`: strict canonical JSON profile, J716c/T6050 target, exact candidate,
  helper and immutable boot021 pins. Rejects the old 31AF/31AI payload as the new
  readable candidate, unexpected paths, reset-policy strategies and authority.
* `model.py`: bounded assertion model for the entire two-visit transaction,
  one native window of at most 90 seconds, and independent Macintosh HD return
  and default confirmation. Keyless admission, original-random key creation and
  the later key-bound baseline are distinct events. Synthetic assertions never
  become observations, and there are no keys or metadata tokens in model records.
* `render.py`: complete one-paste install and separate restore blocks. Recovery
  does not need Python. There is no preliminary clipboard exercise, public
  download, automatic reboot or automated Startup Disk selection.
* `prepare.py`: verifies an explicit source digest inventory and all three local
  files, then creates a new directory beneath repository `build/` containing the
  canonical profile, both full blocks, escaped HTML and an offline receipt.
* `test_recovery.py`: pure profile/model controls plus execution of whole rendered
  blocks against original fake commands in disposable directories. Absolute
  volume, write-tool, authentication and root-query references are replaced;
  tests assert no real bputil/kmutil/device/Recovery path remains. The immutable
  rollback digest is simulated only in these shell-flow controls. They are not
  real selected-object, codec, policy or hardware evidence.
* `stage_lab.py` and `test_stage_lab.py`: future fixed-target, root-only lab Data
  staging and injected-workspace controls. Default/help do no live inspection.
  No production `--stage` invocation has been performed or authorized.
* `serve.py` and `test_serve.py`: fixed, exact rendered page only, verified
  against the new inventory and canonical Git profile. `--check-only` opens no
  socket. Future explicit serving defaults to loopback; a chosen literal private
  LAN address is allowed only when supplied by the operator. Routes `/` and
  `/31aj`, no access logs or artifact/directory serving, absolute lifetime and
  short client deadlines. No production or LAN service was started in testing.
* `test_native_integration.py`: a separate explicit offline CLI connects the
  production v2 C reader to actual own31AF/candidate/boot021 bytes with synthetic
  CF volume/policy fixtures and a fixed nonsecret synthetic key. It invokes only
  the C fixture snapshot/validator modes. It exercises the whole phase sequence,
  protected-metadata/key drift refusals and guarded unknown/unreadable/NONE
  restoration inputs, while keeping initial/candidate/final exactness strict.
  Artifact identity is reported separately from the synthetic policy source.
  It never invokes a live snapshot, capability check, private group read or RNG.

The page preparation inventory must include its six original files. The staging
inventory additionally requires both staging files, the exact canonical public
recovery profile and the frozen31AG guard. A final public
source inventory and exact new candidate/helper pins are supplied by the parent
package after those components are frozen. No placeholders are install ready.

Run the original offline controls from the repository:

```sh
python3 -I tools/recovery31aj/test_recovery.py -v
```

The preparation interface is:

```text
python3 -I tools/recovery31aj/prepare.py \
  --profile build/REVIEWED/profile.json \
  --kit build/REVIEWED/kit \
  --source-inventory native/boot/attempt31aj-kit/source-sha256.txt \
  --output build/NEW-OFFLINE-PAGES
```

`REVIEWED` and `NEW-OFFLINE-PAGES` are documentation labels, not actual paths or
an instruction to run an unreviewed package. Preparation reads local artifacts
and writes new workspace files only. It does not copy into the lab Data volume.

## Future staging and two Recovery visits

After package review and separate live authorization, the future kit layout is
`/Volumes/iLinux Boot Lab - Data/Users/Shared/iLinuxBoot/31aj-kit/`:

```text
profile.json
candidate.macho
m1n1-boot021.bin
ilinux31aj-reader
```

The parent workspace-only materializer prepares exactly these four files first.
The separate original `stage_lab.py` supplies the missing future copy into the
lab Data volume. It requires `--stage`, `--prepared` and `--inventory`, with the
inventory fixed to `native/boot/attempt31aj-kit/source-sha256.txt` in the reviewed
checkout. There is no destination option. Every source file and source inventory
entry is verified before the first target query. The prepared profile must equal
the canonical `native/boot/attempt31aj-kit/recovery-profile.json` pinned by that
inventory, so a separately supplied profile hash is insufficient. These checks
assume the human/agent has reviewed the intended Git revision; an arbitrary
self-authored inventory is not an independent trust authority.

Production staging requires the current root installation to be Macintosh HD on
Mac17,6, administrator/root execution, internal APFS lab System and Data volumes,
distinct original and lab groups, exact Data role/UUID/device/container/group
binding, FileVault explicitly false on lab Data and symlink-free paths. It uses
only read-only `sysctl` and `diskutil` for these checks; no policy query, mount,
boot-object installation, default selection or security command is issued. The
existing `Users/Shared/iLinuxBoot` parent must already be present. An existing
`31aj-kit` or any `31aj-state` entry, including a dangling symlink, refuses staging.

Only a new mode0700 directory is created. Its three data files are mode0600 and
the helper mode0700, all owned by the production root process. Source descriptors
remain open across copying; size/hash/fingerprint, target binding and written
bytes are checked again. Failures attempt cleanup of only this invocation's
new files/directory; the sanitized failure receipt leaves staging unconfirmed
rather than claiming cleanup or success. Existing kit/state entries are never
deleted or overwritten. The success receipt contains fixed filenames, public
sizes/hashes and typed flags; it contains no mount paths or private identifiers.

Run the staging controls separately:

```sh
python3 -I tools/recovery31aj/test_stage_lab.py -v
```

They use only injected temporary workspace targets and synthetic metadata,
including in-memory small rollback pins for fixture efficiency. They never run
the production `--stage` CLI or create its live backend. They cover default/help,
bad source/manifest, symlink, wrong machine/root/installation/role/group/container,
external/encrypted/unknown target, overwrite/state refusal, private modes and
source/target changes. Real lab Data staging remains **NOT RUN** and requires
separate authorization even though it does not change any boot setting.

All four are exact pinned local files. The entire path must contain no symlinks.
The shell copies required inputs to a private temporary directory and verifies
the copies again before executing the helper or any mutation. Install needs all
three artifacts. Restore needs only the helper and raw boot021; corruption or
loss of the candidate cannot prevent restoration.

The helper must independently admit the exact machine, mounted distinct lab
System and Data volumes, distinct original System, and lab-paired power-button
1TR. Original must be Full Security and lab must already be Permissive. Unknown
or unsupported policy metadata and any failed comparison stop before mutation;
the kit does not repair an unexpected mode. A hash utility and `/dev/tty` must be
available in Recovery. Failure of that admission is an outcome to record, not a
reason to loosen the checks.

On the first visit, a keyless guarded snapshot must pass `initial-admission`:
actual31AF, Original Full with enabled CTRR, lab Permissive, exact target/data
bindings and lab-paired1TR. This is admission only; it is not a comparison baseline
and cannot authorize a candidate or restoration phase. The future state directory is
`/Volumes/iLinux Boot Lab - Data/Users/Shared/iLinuxBoot/31aj-state/`, new mode
0700. A new `comparison.key` is then generated directly into a new mode0600 file
there, with shell noclobber enabled. The verified v2 native helper uses the public
system RNG to generate exactly32 original random bytes; it requires private,
empty regular-file stdout, rejects terminals/pipes and flushes the key before
success. This does not read or extract any Apple key, credential or policy value.
The key must remain private on lab Data and persist across both Recovery visits;
it must never be pasted, logged, staged from another machine or added to Git.

Only after key generation does a second guarded snapshot pass `initial` with
key-bound protected metadata. That becomes the mode0600 sanitized baseline;
the canonical profile is also saved mode0600. The directory/key/baseline/profile
are explicit future **lab Data writes**, required to carry comparisons across
reboots. They contain no raw policy, hardware identifiers or Apple nonce/hash
values. A failed key-generation/baseline step stops before candidate enrollment;
it does not fabricate an old baseline. The state directory must not be removed
to force another attempt. Unknown historical lab CTRR is recorded, not invented.

The v2 snapshot includes a random-key identifier and domain-separated HMAC-SHA256
tokens protecting the exact ordered two-value `rpnh` vector and singleton `ronh`,
`spih`, `stng` values, separately for lab and original roles and bound to the
profile. The key identifier and tokens remain private transaction evidence.
All later snapshots, phase validation, CTRR-value reads and private group reads
require the same comparison key. The eight typed semantic flags and protected
tokens must match the initial baseline. The expected globally rotated `lpnh` and
intentionally replaced custom-object reference are excluded; other metadata is
not dynamically ignored. Missing, changed, swapped, unsafe or wrong-length keys,
metadata/cardinality changes and token mismatches refuse further mutation.

Candidate enrollment uses normal Mach-O `--compress`, then
fresh readback must identify the exact new candidate, enabled CTRR and unchanged
unrelated policy. A successful command exit alone is insufficient.

An atomic operation marker is persisted before each candidate, CTRR or raw-object
mutation. A marker is spent even if the process fails, returns timeout status or
is interrupted. The block makes fresh sanitized readback after a returned
mutation, including nonzero status, and saves it before stopping. Its signal
handler attempts readback and exits; interrupted readback can remain unavailable.
There is no automatic authentication timeout or forced kill of security tools.
Status124 and130 are handled as ambiguous failures. Authentication stays in the
Terminal via `/dev/tty`; passwords and raw policy/authentication transcripts are
not captured to files. The separate native observation uses an external timer.

Only a verified successful candidate install may be proposed for the single
native observation. The human boot cue, camera-recording confirmation if used,
and independent maximum90-second stop timer are separate actions. No Linux USB
gadget or remote-control connection is assumed.

On the second visit, the independent restore block first validates the saved
baseline, same private comparison key, current semantic policy and protected
metadata tokens. Unknown or unreadable selected-body identity is allowed at this
pre-restoration phase because the explicit intent is replacement with known
boot021; it never counts as a successful candidate or final restoration.
If exact boot021 and disabled CTRR are
already observed, it performs no mutation. Otherwise:

1. Enabled CTRR: obtain the lab group privately into an xtrace-disabled shell
   variable, perform only documented `bputil -c -v GROUP` once, discard that
   variable, and require disabled CTRR plus unchanged unrelated policy.
2. Disabled CTRR: skip the policy mutation. Unknown CTRR: stop.
3. Enroll exact raw boot021 with entry2048 and lowest virtual address0, once,
   then require exact selected boot021, disabled CTRR and unchanged unrelated
   policy. `NONE`/unknown selected object immediately after policy preparation
   is a permitted transient state; it never counts as final restoration.

A failed mutation stops that invocation even if readback appears useful. A later
independent restore may resume only from observed state without repeating a spent
operation: for example, observe disabled CTRR after an interrupted `-c` and go
straight to the one still-unspent raw enrollment. A spent operation whose target
is not observed requires review, not replay. No further native boot follows a
failed/ambiguous install or restoration.

Finally, restoring Macintosh HD as the default Startup Disk is an independent
manual action and must be confirmed independently; no `bless` is emitted. The
two visits may require the already established temporary lab Startup Disk
selection to reach its paired Recovery. That manual change and final restoration
must be included in future human authorization. None has been performed here.

## Policy scope and remaining admission gaps

The supported v2 comparison covers typed `smb0`–`smb4`, `sip0`, `sip1`, `sip3`,
with `sip2`/CTRR separately observed, plus the private-keyed opaque metadata
comparison above. Actual read-only metadata presence showed two `rpnh` rows and
present `ronh`/`spih`/`stng` on each role; the earlier v1 helper would refuse that
schema and remains superseded evidence. Nonabsent AuxKC metadata and unqualified
`prot`/`hrlp`/`losv` are still refused, rather than silently discarded.
The native helper owns exact field grammar, paired1TR and selected-object
validation; these original shell controls cannot prove those C paths correct.
Real Recovery admission, owner authentication, firmware entry and SMP remain
untested. No claim of restored original policy is made from a policy file hash:
Apple documents that changing any LocalPolicy re-signs all policies with a new
`lpnh` nonce hash. Wrapper authentication/default selection remain separate facts.

The local public manuals document why `-n` is deliberately absent:
`bputil(1)` says Permissive Security recreates LocalPolicy from scratch, whereas
`-c` disables kernel CTRR and can downgrade only if necessary. This transaction
requires Permissive first and preserves other supported policy fields. Public
Aura's `bd9f3e8273dc79ae9095c19c2c4f32218446ad4e` Recovery source provides the
normal Mach-O versus raw enrollment arguments, but its previously observed board
behavior is not proof of our firmware's behavior.

Primary references:
[Apple LocalPolicy fields](https://support.apple.com/en-gb/guide/security/secc745a0845/web),
[Aura Recovery enrollment](https://github.com/aurora-silicon/aura/blob/bd9f3e8273dc79ae9095c19c2c4f32218446ad4e/docs/recovery-enroll.md).
The Aura URL is an immutable source identity only; package provenance binds the
actual fork and revision, rather than a similarly named upstream tree.
