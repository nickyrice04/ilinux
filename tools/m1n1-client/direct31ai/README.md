# 31AI: offline lab restoration model

**No native test, Recovery writes or restart is ready.** This original tool
checks the consistency of a proposed sequence or sanitized assertions. It does
not inspect macOS, authenticate, discover a volume, query policy, open USB or a
camera, enroll an image, select Startup Disk, or execute another program.

The [M1 review](../../../native/boot/attempt31ah-m1-offline-2026-11-13.md)
passed 31AH's offline integrity checks. It still leaves the current configured
lab object, exact 31AF restoration and Macintosh HD default unconfirmed. These
unknowns are not converted into successful restoration by this model. New work
does not renew the consumed 31AF installation/observation approval.

Subsequent M5 human-run read-only evidence now identifies the currently selected
lab **contained payload as EXACT_31AF**. Boot021 is not currently selected.
Opaque wrapper metadata, effective policy and default remain unverified; see
[the observation](../../../native/boot/attempt31ai/selected-object-observation.json).
This resolves contained-payload identity only. The initial raw-boot021 baseline
required by the model is not established by that result.

## What the public implementation establishes

**Source-confirmed, not observed on this machine:** Aura's pinned
[Mach-O guide, lines 63–68](https://github.com/aurora-silicon/aura/blob/bd9f3e8273dc79ae9095c19c2c4f32218446ad4e/docs/macho-boot-object.md#L63-L68)
says Mach-O enrollment enables the volume's Kernel CTRR policy. Enrolling raw
bytes afterward can leave secondaries confined outside their code; the guide
reports a J616s single-core result and requires policy preparation before
returning to raw. This is a restoration dependency, not proof of a T6050 result.

The pinned installer's
[BootSelection.swift](https://github.com/aurora-silicon/aurora-installer/blob/2d5c44e37d04173cb7085120b34862b75a609934/macOS/Recovery/Sources/BootSelection.swift#L40-L65)
uses Mach-O enrollment, compression for the execute-window mode, and a distinct
owner-authorized policy step. It provides no raw rollback mode. The old raw
instructions in Aura's pinned `docs/j700-install.md` are therefore insufficient
for the new direct-entry route.

In the same pinned installer,
[RecoveryActions.swift, lines 611–678](https://github.com/aurora-silicon/aurora-installer/blob/2d5c44e37d04173cb7085120b34862b75a609934/macOS/Recovery/Sources/RecoveryActions.swift#L611-L678)
separates enrollment from file recovery and explicitly warns that restoring
files does not undo an authorized LocalPolicy change.
Its [Recovery README](https://github.com/aurora-silicon/aurora-installer/blob/2d5c44e37d04173cb7085120b34862b75a609934/macOS/Recovery/README.md#L110-L112)
treats a timeout after enrollment starts as ambiguous and retains the matching
bundle and journal. Our model consequently requires fresh postconditions after
every attempted policy/object operation, regardless of the reported exit.

The public
[manual enrollment guide](https://github.com/aurora-silicon/aura/blob/bd9f3e8273dc79ae9095c19c2c4f32218446ad4e/docs/recovery-enroll.md#L61-L98)
documents paired power-button Recovery, object inspection and the raw CTRR
condition. It also states that its generalized script has not been run in
Recovery; testing used command stubs on macOS. Its script notes an absent CTRR
status rather than refusing it. We require an explicit known status. None of
that script is executed or delivered here as a qualified restoration procedure.

Apple's ordinary owner-authorized enrollment/Recovery interfaces and public
bootloader contracts are the integration boundary. No attempt to bypass locked
CTXR windows, patch firmware, defeat signatures or relax the original macOS
policy is part of this work. Public code is evidence of expected behavior;
neither its comments nor this state model prove the live postcondition.

## Evidence required for the concrete proposal

| Gate | Required evidence before proposing writes | What does not establish it |
|---|---|---|
| Existing restoration | Reconciled 31AF record and current exact lab object/CTRR state; original desktop and default separately established | Returning to a desktop, an earlier attempt's receipt |
| Original installation | Original/lab are distinct, the target resolves to the lab, original policy remains Full | A volume label alone |
| Firmware identity | Global firmware identity and selected lab's paired iBoot/stub identity separately identified | Current SystemVersion or global Boot ROM alone |
| Pair qualification | Source contract plus evidence appropriate to that actual firmware/boot-object/kernel pairing | A different reported OS version; recognition of a version string alone |
| Candidate closure | One selected loader, window geometry and exact kernel/DT/RAM-root hashes; transfer path and RAM reservations reviewed | Two alternative Aura binaries or a VM pass |
| Raw restoration | Exact boot021 bytes/size, lab policy preparation followed by raw enrollment, fresh selected-object and policy readback | Copying boot021 back; configure's process exit alone |
| Other lab policy | Qualified comparison of unrelated policy fields against the pre-test baseline, excluding the intended CTRR/object transition | Full/Permissive labels alone |
| Recovery and return | Correct lab-paired 1TR and locally authenticated owner flow; independent original return/default procedure | Assuming the current Recovery belongs to the lab |
| Observation and stop | Exact diagnostic workload, one attempt, externally measured cap and a human able to stop and return | A camera recording without an available operator |
| Authorization | Separate authorization for the reviewed concrete installation/test/restoration sequence | This model, the M1 integrity PASS or consumed approvals |

The host's global Boot ROM version can differ from its running OS loader. A
paired lab loader is a third item to identify; matching a public source's version
table is not runtime qualification. A difference from the operator's build is
not by itself a reason to update either installation or global firmware.

The initial raw boot021 bytes are pinned to 3,932,160 bytes and SHA-256
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
The model compares asserted object digests against this pin; it does not locate
or hash the installed object. Those observations need a separately reviewed
read-only adapter. No current live observation or executable Recovery write
block is generated in this directory.

## Model and refusal behavior

The accepted path is:

1. A qualified original-desktop baseline: boot021, lab Permissive/CTRR disabled,
   original Full/default, distinct lab and reconciled old restoration.
2. Fresh lab-paired Recovery observation, then one candidate enrollment attempt.
3. On successful enrollment only, fresh matching direct-object/CTRR-enabled
   observation before one optional physical diagnostic window.
4. Fresh lab-paired Recovery observation. Prepare the lab's raw policy if
   necessary; fresh CTRR-disabled readback precedes raw boot021 enrollment.
5. Fresh exact boot021/policy observation; original-desktop return with original
   Full/default and intended lab policy verified separately.

An enrollment failure/timeout can branch directly to restoration after fresh
known-state observations. It cannot branch to a native test. A reported raw
enrollment failure/timeout can establish the desired *asserted* final state only
through a fresh matching object/policy observation; its exit never supplies that
observation. Unknown object/CTRR/default, wrong Recovery, policy drift,
unrecorded object changes and out-of-order or repeated attempts refuse. A
failed audit does not instruct a person to remain in Recovery or prevent a safe
return to macOS; it means the supplied sequence does not establish the intended
restoration. Actual deviations must be retained in the incident record, not
edited into the passing model.

`native_deadline_ms` must be positive and no more than 90,000. This is an outer
model ceiling for a possible future short diagnostic, not an authorization or
an automatically enforced timer. The later proposal may choose a shorter cap.
An overrun refuses rather than silently relabelling the test as bounded.

Input is at most 64 KiB with sixteen events; duplicate keys and unknown fields
are refused without echoing their values. The schema accepts only fixed labels,
booleans/`unknown`, artifact digests and bounded numeric fields. No raw policy
output, volume paths, UUIDs, identities, usernames or credentials belong in it.
`SANITIZED_ASSERTIONS` means caller-provided assertions, not authenticated tool
receipts. The analyzer does not establish freshness or provenance. The ordered
postcondition events are an audit requirement for a future evidence collector;
the caller must not fabricate them or relabel historical data as fresh.

Even `OFFLINE_MODEL_COMPLETE` always has `native_ready:false`,
`writes_authorized:false`, `hardware_state_verified:false` and
`restoration_verified:false`. It proves only that the supplied assertions follow
the model. Actual bootability, restore success, physical secondary execution and
macOS-equivalent performance remain unproved.

## Optional camera and autonomous diagnostics

M1's review lists a built-in camera and QuickTime; activation, permissions,
audio-off support, framing and recording remain NOT RUN. Reuse the
[private camera/timeline protocol](../direct31ah/camera-protocol.md) only in a
future authorized session. Frame the M5 screen, disable audio, keep Recovery
authentication out of view and retain media under ignored `build/` locally.

A future RAM diagnostic may run independently and repeat screen summaries while
an external human timer caps the attempt at ninety seconds or less. The existing
collector can report actual online CPUs and concurrent work without a remote
shell. This reduces dependence on an unqualified Linux gadget link but does not
create remote shutdown, recovery control or an independent hardware watchdog.
Video timestamps can corroborate visible milestones, not unseen CPU entry or
SMP. An M1 failure can also lose its camera/logging; the human stop/return path
must remain available. There is no camera access or recording in these tests.

## Run the offline checks

From the checkout root, with no administrator authentication:

```sh
python3 -I tools/m1n1-client/direct31ai/test_state_model.py
python3 -I tools/m1n1-client/direct31ai/state_model.py \
  < tools/m1n1-client/direct31ai/example-hold.json
```

Expected: forty state-model test methods pass. The example is explicitly synthetic, contains
no observations and returns `OFFLINE_HOLD`; it is not a report of this Mac's
current policy or installed object. No host settings change occurs.

## Two-file candidate integrity review

`candidate_review.py` independently reads the new local diagnostic tar and the
gzip-compressed inline Aura candidate. The parent handoff supplies the exact
candidate/diagnostic manifest paths, both transfer filenames and public pins.
No candidate is delivered by this directory, and no public binary Release is
authorized. The new reader's manifest schema is
`ilinux-direct31ai-inline-candidate-v1`; it requires local-only delivery,
incomplete public libc source closure and strictly false native/restart/firmware/
public-release flags. Unknown manifest fields are refused.

The reader verifies eight specific original helper sources before importing
them, including the frozen 31AH Mach-O reader. It then reuses the strict
diagnostic-package validator and reads its exact Image, sanitized DT and RAM
root in bounded memory. The candidate gzip is bounded to 32 MiB compressed and
160 MiB expanded; one gzip member, complete checksum/EOF, regular-file identity
and both compressed/expanded hashes are required. No decompressed file is
written, binary executed or device opened.

The Mach-O check verifies six segments, the exact baseline runtime prefix,
fixed entry/vector registers, canonical UUID/prelink identity values, the
nineteen-MiB inline input pin and zero execute padding. The parsed payload must
carry those exact diagnostic bytes with the source-defined gzip/tag/config
framing. `expected_kcbz:0` is a source/layout implication; the reader performs no
Apple `kmutil` inspection and does not claim firmware acceptance or entry.

The candidate-reader test suite uses the project's independent synthetic
metadata encoder. Test-scoped small footprints/digests cannot be selected by
the production CLI. It tests CRC/concatenation/bounds, manifest scope, private
metadata refusal, helper pins, FIFO/symlink refusal, entry/UUID/padding and exact
kernel/root binding. The integration test stubs diagnostic admission; the real
two-file intake must also pass independently on the final transferred artifacts.

```sh
python3 -I tools/m1n1-client/direct31ai/test_candidate_review.py
python3 -I tools/m1n1-client/direct31ai/candidate_review.py --help
```

Expected: thirty-three candidate-reader test methods pass. The actual review
requires `--manifest`, `--candidate`, `--diagnostic-manifest` and
`--diagnostic-package`, with paths from the current parent handoff. A complete
PASS remains artifact integrity, not authorization or a restored live system.
