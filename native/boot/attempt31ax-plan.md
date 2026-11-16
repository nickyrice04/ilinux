# 31AX: deliberate lab reconstruction with independent functional rescue

November 15, 2026. **Preparation is offline. No live reset, installation, staging,
policy query, Startup Disk change or restart is authorized by these files.**

M1's `d679622` [AW review](attempt31aw-m1-offline-2026-11-15.md) passed all 52
methods normally and under sanitizers, with matching source bindings and no
actionable finding. The actual AU install and its boot021/Original-return
confirmations remain closed; no repeat manual security check is needed.

## Question this experiment would answer

The previous Mach-O install began with disabled lab CTRR and did not establish
an enabled state. Apple documents a separate Permissive reconstruction operation
without the CTRR-disable option. The proposed new test establishes that baseline
first, checks the result, and proceeds to a candidate only if every required
condition passes. It does not repeat the old disabled-baseline experiment or
depend on a speculative private SEP command.

This is whole-policy reconstruction rather than an enable-only change. Its
effect on this exact Recovery/runtime is a **Hypothesis** until measured.
Apple also documents global LocalPolicy nonce reissuance when a policy changes.
Original's Full Security and protected settings stay anchored; old signed policy
bytes are not the preservation contract. See the
[closed field contract](../../research/attempt31ax-policy-contract-2026-11-15.md).

## Required controller behavior

1. **Anchor before any change.** Require the correct model/SoC, distinct bound
   Lab and Original roles, exact boot021, safe Permissive lab options, disabled
   lab CTRR and Original Full/CTRR. Durably bind the fresh AX key/profile/target,
   pre-reset Original invariants and typed lab authority/protected fields. No
   earlier state, key, baseline or spent marker may be adopted or reset.
2. **Spend one lab reconstruction.** Recheck those bindings and persist the
   one-shot intent before delegating the fixed supported command to Apple's
   foreground authenticator for the bound Lab group. No passwords or owner
   credentials are collected. No timeout, interruption or refusal permits replay.
3. **Admit the new baseline strictly.** Require enabled CTRR and the approved
   narrow field contract. Reissued LocalPolicy nonce/signature and phase-specific
   lab custom-object changes do not authorize remote-policy, Recovery, cryptex,
   version, authority or Original changes. Publish the new lab baseline and its
   readiness marker durably before a candidate writer can run.
4. **Install conditionally.** Require successful codec controls, exact candidate
   bytes, enabled CTRR, both policy contracts and cleanup. A missing/refused or
   undurable baseline must never reach this writer. A rescue observation cannot
   be promoted into a candidate baseline.

The new typed authority check includes hardware fields, volume and KEK contexts,
and Original's OS/custom-object references that the older aggregate HMAC did not
cover. KUID is a key-encryption context, not proof of a particular human owner;
per-command owner authentication remains Apple's responsibility.

## Rescue must exist before the new baseline

The independent restore entry uses the pre-reset anchor and exact raw boot021.
It needs no candidate, successful compressed decode, post-reset baseline, or
successful reset readback. A first readback failure may be followed by a separate
guarded restore observation; it cannot authorize another reset.

For functional rescue only, a closed set of typed lab issuance differences may
be observed. They are **unqualified transitions**, not evidence that reset was
correct or that old settings were recovered. Bind the currently readable rescue
observation, freeze its protected values across the rescue writers, and retain
the Original/target/authority/safe-option checks. Unknown or unsafe semantics,
auxiliary trust, changed authority, changed Original, or unreadable required
policy data refuse further writers and require manual Recovery review.

Final rescue success means exact boot021 payload, disabled lab CTRR, preserved
Original requirements, correct binding and owned cleanup. It does **not** mean
old lab policy bytes or Find My/Recovery/cryptex metadata were restored. The
result must state that limitation. Existing exact-boot021/disabled-CTRR state is
a read-only no-op; spent rescue writers are never repeated.

## Offline acceptance and later hardware window

Exercise the real compiled controller against genuine own artifacts and
synthetic system/writer backends, normally and under ASan/UBSan. Required fault
cases include reset success followed by failed readback, rejected or undurable
new baseline, interrupted reset, allowed rescue-only metadata deltas, failed
codec/missing candidate, wrong identity/authority/Original state, current rescue
metadata drift, and every spent-writer/cleanup boundary. Explicitly test nonce
reissuance versus protected-field changes and malformed typed inputs.

Final producer checks pass **76 controller methods normally and 76 under
ASan/UBSan**, zero skips. Independent review passes nine decisive v4 methods;
the v5 generated-source difference is help text only. Root separately passes
five focused methods against the final sanitized v5 binary. The pure typed-field
suite passes **18 methods per mode**, with 529 C assertions over 16 cases plus
import/privacy checks; it does not link a collector or writer. Exact attribution,
source/binary bindings and limits are recorded in the
[offline receipt](attempt31ax-offline-2026-11-15.json).

M1 reviews the published controller, source bindings, evidence and failure cases
offline. A native proposal follows only after that review and a concrete
Recovery kit with independent rescue is prepared. That later owner-approved
window can run one reset, its readback, conditional enrollment/entry observation,
and functional boot021 rescue, then return Macintosh HD as default and desktop.
No candidate boot follows a refusal. The native stop deadline remains separately
bounded; no firmware, OS update or volume operation is part of this design.

The immediate milestone is a verified installation/entry path. The unchanged
candidate is a diagnostic RAM image, not an accelerated Omarchy desktop or a
performance-parity result. Physical core types, clocks, memory, GPU, networking,
storage and energy still require native measurement after entry. Macintosh HD
remains at Full Security; no hardware test is implied by an offline pass.

## Reuse the working stack before choosing the next boot

The owner's mid-task direction is to build more directly on the community's
successes. That is the default: AX is a narrow recovery tool, not a reason to
rewrite working drivers or keep an obsolete firmware/boot stack indefinitely.
Before proposing a hardware window, compare the exact J716c reference's pinned
Aura, kernel/config/modules, Mesa, firmware and runtime safety pieces with our
current inputs. Prefer reproducing that matched stack and adapting Omarchy
packaging over independent driver implementations where working code exists.

The ready-made `betizzel/omarchy-m5` image currently targets J714s Pro and explicitly
excludes Max/16-inch models. Its reusable recipes still need a J716c board profile;
its latest source recipe is not automatically the release tested on hardware.
The exact-board Max source/config/graphics references are more directly useful.
See the [reuse audit](../../research/attempt31ax-reuse-first-2026-11-15.md).

If matching the working stack needs an OS/firmware transition, prepare that
specific compatibility/backup/boot-entry plan for the owner. Do not silently
update macOS, assume updating Original also refreshes the lab stub, or spend
another boot repeating old-stack failures. The AX reset test remains a meaningful
option only if this comparison supports using it for the selected entry path.
