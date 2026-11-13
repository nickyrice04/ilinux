# 31AJ: finish the boot transaction, then measure physical SMP

2026-11-13. **Offline development/proposal. No install, restart or new camera
session is authorized by this document.** Original Macintosh HD stays intact.

## Decision from M1's update

M1's [independent review](attempt31ai-m1-offline-2026-11-13.md) found no actionable
integrity failure: 221 methods, both source inventories, both transferred files
and the embedded kernel/DT/root relationships pass. Its subsequent
[camera handoff](../../tools/m1n1-client/camera/m5-recording-handoff.md) establishes
a recorded video-only quality clip and partially readable text. Neither result
establishes native kernel entry or eighteen physical cores.

Continue the coherent public Aura/CTXR kernel route. The next engineering work
is a complete installation/readback/restoration kit and readable diagnostics.
Do not restart another marker-only experiment, recalibrate the camera now,
restart M1, replace the current package blindly or update firmware by assumption.

Preserve frozen 31AH/31AI sources, inventories and binary pins. A changed
diagnostic root or inline stream requires a new manifest/candidate and focused
review. Calling that variant 31AJ does not change the meaning of prior results.

## Work before requesting a physical test

1. **Candidate-sized readback.** The current eight-MiB reader identified the lab
   payload as EXACT_31AF; this question is closed. It cannot verify the new
   153,190,400-byte candidate. Build a separate bounded reader for the actual
   IMG4/IM4P form, optional opaque properties and any documented compression.
   Verify complete known payload bytes; report wrapper authentication and
   effective policy separately. Never treat configure exit, matching length or
   opaque metadata as selected-byte verification. The new offline primitive in
   `tools/boot-object31aj/` is only a component: a real codec, Recovery-compatible
   adapter and target/selection guards still need integration and review.
2. **Complete lab policy and object restoration.** Prepare independently guarded
   install and restoration blocks for lab-paired Recovery. Compare unrelated lab
   policy fields against a fresh baseline; verify original Full separately.
   Apple's installed bputil manual explicitly says its `-n` operation recreates
   LocalPolicy, preserving only supplied options. Therefore the public `-nc`
   example cannot be described as changing only CTRR. Evaluate the documented
   narrower `-c` operation for the existing Permissive lab, with explicit semantic
   readback; if a full policy recreation is necessary, enumerate its intended
   final fields and obtain approval for that exact operation. Any changed custom
   object reference during policy preparation is an observed transition, never
   assumed unchanged. No policy command is executed here.
3. **Readable key results.** Reuse the collector's actual CPU, timer, checksum and
   liveness calculations. Existing kernel fonts are 8x8/8x16 and the camera has
   not qualified their native text. Prefer a small original console block-text
   layer for phase, CPU count, RAM/timer result and elapsed time, repeated at the
   existing five-second summary cadence. This can avoid a new display driver,
   backlight writes, font engine or kernel rebuild. Test layout/fallback and
   unchanged diagnostic outcomes in isolation, then repin the changed root and
   candidate. Do not equate browser CSS size with native framebuffer pixels.
4. **Bound the current firmware assumptions.** Retain global Boot ROM, running OS
   loader and lab-paired loader as distinct observations. Identify the paired
   lab version through a bounded read-only adapter or first-Recovery preflight.
   Public source recognizes the current running loader; compatibility still
   needs the actual test. Do not require proof of native entry before the
   experiment intended to test entry, or infer an update requirement from a
   different operator's OS version alone. Revisit REA for a specific unexplained
   handoff if source contracts and resulting observations leave that question.
5. **Review only the changed material.** M1 reviews the new source, focused tests,
   target/selection/policy guards, exact final artifact pins and independent
   rollback block. Reuse its completed integrity review for unchanged inputs.
   Finish the one-paste Recovery page before requesting concrete authorization.
   Each phase must be one complete copyable block: copy in the browser, switch
   to Terminal, paste once. Do not require simultaneous windows or a separate
   clipboard smoke test. Authentication stays in the system/Terminal prompt.

The live adapter must work in the actual Recovery environment, rather than
assuming the current desktop Python exists there. Test capability/admission in
the first already-planned Recovery visit before writes; use offline command
stubs for workflow failures and the real system codecs on synthetic fixtures.
Those tests cannot prove owner authentication or physical enrollment succeeds.

## Proposed single physical sequence

Subject to a separately reviewed and authorized exact kit:

1. Enter **lab-paired Recovery**. Freshly identify the distinct lab target,
   current contained 31AF payload, policy fields and candidate/rollback bytes.
   Preserve original Full and record the intended final selector separately.
   Refuse an unexpected lab security mode before any write; a command that can
   automatically downgrade must not become an implicit repair action.
   Start from this actual state; do not fabricate an already restored boot021
   baseline or add a separate raw-boot experiment merely to satisfy the old
   assertion model. A new transaction profile must express the real transition.
   The old model's forty tests do not validate this new starting state; add
   focused refusal tests for it without changing frozen 31AI.
2. Enroll the exact reviewed candidate once. Verify selected payload and intended
   lab policy before proceeding. Failure, timeout or unknown postcondition means
   **no diagnostic boot**; reconcile and restore through the independent block.
3. M1 checks fresh framing and confirms actual RECORDING before the human boot
   cue. Use an independent human clock, capped at **90 seconds from confirming
   the diagnostic boot selection**. A longer camera clip does not extend it.
   Record partial results and stop on time even if the screen stays at a logo.
4. After one observation, stop/cover the camera before credentials. Return to
   lab-paired Recovery, apply the reviewed raw-policy preparation, then enroll
   exact boot021 with its raw geometry. Read back exact selected bytes, CTRR and
   unrelated policy. A failed process is not proof of an unchanged state.
5. Return to Macintosh HD and restore/verify the intended default independently.
   No automatic retry, no new volume and no original-volume policy change.

Final boot021 is completion of the intended old restoration, rather than a
byte-for-byte return to the actual pre-test 31AF payload. State that distinction
in the reviewed authorization and record any remaining uncertainty honestly.

This uses two Recovery visits and one diagnostic window. It needs no M1 restart
or Linux USB command channel. A camera remains an observation channel; it
cannot provide remote recovery, prove an unseen phase or replace the human stop.

## Evidence one boot should collect

| Question | Required result | What it does not prove |
|---|---|---|
| Kernel entry | Visible kernel/PID1 build milestones and separately readback-bound Image/root artifacts | Runtime hashing unless implemented, or macOS-equivalent performance |
| All CPU groups | Eighteen online/permitted CPUs and pinned work on every CPU across all three DT clusters | Correct DVFS, scheduler capacity or physical core labels from count alone |
| Concurrency/correctness | Every worker's checksum/affinity passes; recorded common work interval | Balanced heterogeneous scheduling or peak throughput |
| RAM | Existing 64-MiB allocation/checksum passes | Full memory bandwidth, VRAM or GPU coherence |
| Timers | Existing per-worker timer observations pass | Interrupt latency or idle efficiency |
| Stability | Sixty seconds of collector liveness, if reached within the external cap | Long-term stability or suspend |
| Return | Exact boot021/policy readback and original/default return | Success inferred from reaching any desktop |

Partial or unreadable evidence remains partial/unknown. Do not extend the
deadline or claim failure before a phase solely because no camera text appeared.
Only RAM/pseudo filesystems are mounted; no persistent storage filesystem is
mounted, no Linux block device is opened and no Linux storage module is added.
Aura still performs its source-defined controller handoff operations;
RAM-root contents alone do not prove the absence of firmware side effects.

## Route from this result to the actual goal

The goal remains native Omarchy with macOS-class functionality, performance and
efficiency on this specific M5 Max. Eighteen working cores are an enabling step.

1. Once SMP/RAM are observed stable, measure frequency behavior, per-cluster
   capacity, cross-core latency and memory bandwidth against the existing macOS
   baselines. Use the same portable workloads and record affinity, build, power
   state and temperature. Do not force every core to maximum speed as an
   efficiency strategy or infer bandwidth from the RAM checksum.
2. Bring up a reliable Linux control link, N1 networking and native NVMe using
   the matching public stack. Validate reads first; benchmark writes only to an
   explicitly selected Linux test filesystem. Original APFS/FileVault data and
   Linux storage performance are separate problems; no macOS write access is
   implied. A synced repository can supply the Linux agent's research inputs.
3. Integrate the matching G17C kernel/Mesa/display stack and the existing Omarchy
   root. Many cores cannot replace GPU acceleration for a responsive desktop.
   Measure menu/input latency, software versus hardware rendering, frame pacing
   and browser behavior. A Linux-side agent becomes useful once networking,
   storage and responsive interaction are actually demonstrated.
4. Qualify idle/load power, thermal control, suspend/resume and remaining devices
   including audio/camera, external displays/devices and ML/video acceleration.
   Keep support, speed and energy results distinct; no macOS-parity claim follows
   from a successful boot or a virtual-machine result.

Current decision: **continue offline implementation; no restart yet.** No
Apple-only blocker or mandatory firmware update is established by M1's review.

## Offline foundation delivered with this plan

The new payload primitive passes **36 synthetic methods** and independent
review. Actual workspace raw 31AI, 31AF and boot021 files identify exactly;
all selection/restoration/bootability/write-authority flags remain false. Its
compressed candidate remains UNKNOWN without a real injected codec. This is
not the Recovery adapter or the complete kit described above.
[Receipt](attempt31aj-offline.json); [new source pins](attempt31aj-source-sha256.txt).

M1 may review only this new component and plan, preserving its existing work:

```sh
shasum -a 256 -c native/boot/attempt31aj-source-sha256.txt
python3 -I tools/boot-object31aj/test_payload.py
```

No new binary transfer, extraction, live query, camera test or restart is needed
for that review. Report the exact reviewed commit and component limitations;
do not treat this intermediate software PASS as readiness for physical boot.
