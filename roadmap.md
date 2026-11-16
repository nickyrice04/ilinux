# Roadmap

Ordered by the mission's prioritization rules: enablement dependencies first,
then feasibility, impact, evidence, safe testability, reuse and
maintainability. Status: ✅ done · 🔄 in progress · ⏳ blocked or awaiting
approval · ⬜ not started.

## Current direction — reuse the matched J716c stack; AX safety layer tested, 2026-11-15

The owner's direction is to build directly on working community enablement.
The [new adoption audit](research/attempt31ax-reuse-first-2026-11-15.md) identifies
an exact-board 18-core/GPU/N1 baseline and the missing enrollment, firmware and
runtime safety pieces. Use that as our foundation. The ready J714s Pro image is
not a drop-in installer for this J716c Max, but its packaging and boot mechanisms
are reusable with explicit board admission. Do not rewrite working drivers or
keep patching an obsolete minimal stack by default.

1. **M1 reviews the completed AX safety component offline.** The new
   [reset/rescue controller](tools/boot-object31ax-native/README.md) passes 76 normal
   and 76 sanitizer methods; pure typed-policy checks pass 18 per mode. Independent
   and root-focused tests verify missing-baseline rescue, anchor authentication,
   repeated-invocation freezing and honest functional-only scope. Follow the
   [handoff](tools/m1n1-client/attempt31ax-instructions.md). No restart/server/stage.
2. **Freeze and reproduce one coherent exact-board stack.** Use the pinned
   J716c full 16K kernel config, Image/modules/DT, Aura graphics handoff and Mesa
   combination. Bring in existing Omarchy Mac packages with a real J716c update
   guard. Keep alternative branch/firmware pins separate; newest recipe code is
   not automatically hardware-tested release code. Existing source/config
   validators are useful; actual matching full builds remain to be completed.
3. **Settle firmware, Stage1 and guardian deployment concretely.** Current
   recorded 26.6.2 inputs differ from the working 27.2.1 reference. An update alone
   does not automatically refresh the Lab's stub. Plan the matching transition
   and backup/compatibility implications for owner approval; do not silently
   update Original or re-run a Pro partitioner. Package update guards are distinct
   from the reference's separately deployed physical watchdog guardian.
4. **Choose one informative native window after those comparisons and reviews.**
   AX offers a new supported Lab-baseline reset/readback with conditional exact
   candidate/enabled-CTRR admission and independent functional boot021 rescue.
   It remains optional for the chosen public boot route, not a reason to delay
   adopting that route. No candidate boot after refusal; all host/firmware/boot
   changes need a concrete separately authorized kit and return plan.
5. **Measure the accelerated Omarchy environment.** Check all physical core
   types, GPU-rendered app/input latency, N1/control access and thermal behavior;
   then compare CPU/RAM/network/storage throughput and energy with macOS. Keep
   bounded reference clocks/guardian behavior until real telemetry validates
   changes. Working all-core boot or device-up reports are not parity evidence.

[AX plan and evidence](native/boot/attempt31ax-plan.md). All old inputs and consumed
state remain unchanged. No actual reset, boot, OS/firmware/volume/security/default
change ran. Native Linux/SMP/GPU/performance NOT RUN in this work. Macintosh HD
remains protected at Full Security; no restart is ready now.

## Historical direction — 31AW integrated; review a supported baseline experiment, 2026-11-15

M1's 31AV review is accepted with its explicit coverage accounting. The new
[AW controller](tools/boot-object31aw-native/README.md) integrates the corrected
bounded decoder, runtime controls and finite subreasons. Root's 52 normal and
52 sanitizer methods pass, zero skips; independent review passes five decisive
controls and the pure capability command. Original/candidate/preservation and
candidate-independent boot021 restore guards remain. No new kit is staged.

1. **M1 reviews the integrated helper offline.** Follow the
   [AW handoff](tools/m1n1-client/attempt31aw-instructions.md); no restart, server,
   proxy or live transaction. Existing artifacts suffice, fresh carriers are
   generated from genuine own input, and the legacy reference is optional with
   explicit per-method missing-input accounting. All 190 AU/10 AV pins remain.
2. **Develop the documented policy-baseline experiment before proposing it.**
   [REA receiver findings](research/attempt31aw-ctrr-2026-11-15.md) identify whole
   request forwarding to SEP's pnon application; its matching handler remains
   unqualified. [Apple's documented reset mechanism and public-source comparison](research/attempt31aw-public-contract-2026-11-15.md)
   support testing a new Permissive baseline without the inherited CTRR-disable
   option. This is whole-policy reconstruction, not an enable-only operation.
   It needs immutable pre-reset Original invariants, explicit allowed lab
   changes, a fresh lab baseline and rescue that works before that baseline
   exists. Old lab signed metadata cannot be promised byte-exact restoration.
   AW intentionally contains no such writer; no new host operation is approved.
3. **Only then propose one informative combined Recovery window.** Qualify actual
   runtime/codec, test the deliberate lab transition, conditionally install and
   verify exact candidate/enabled CTRR, observe entry only after complete checks,
   then restore boot021 behavior and Original default/desktop. No repeated
   unchanged install, old-state reset or weaker acceptance. A separate reviewed
   controller/rollback contract and owner authorization must precede this.
4. **Continue toward a matched accelerated Omarchy stack after entry.** Reuse
   generic exact-J716c kernel/Aura/firmware/runtime work with core-type and thermal
   controls together. The newly identified daily branch adds board-specific
   firmware facts, not a complete policy/Stage1 recipe; exclude per-unit DROM.
   Measure CPU, memory, GPU/input latency, network/storage and energy per task
   against macOS before any parity claim. No Apple-only blocker is established.

[Plan and evidence](native/boot/attempt31aw-plan.md). Macintosh HD remains intact
at required Full Security. No new boot, policy, firmware or volume operation ran;
Linux/SMP/GPU/performance are NOT RUN in this work. No restart is ready now.

## Historical direction — 31AU safely closed; qualify 31AV offline, 2026-11-15

The [closed M1 report](native/boot/attempt31au-recovery-2026-11-15-result.md)
records installation refusal, human-confirmed exact boot021 restoration and
Macintosh HD desktop/default return. No Linux boot occurred. Changed selection
and a readable IMG4/LZFSE file narrow the identity failure to the decoder path;
disabled lab CTRR remains a separate failed requirement.

1. **Review the implemented verifier repair before integrating it.** The new
   [31AV component](tools/codec31av/README.md) reproduces a valid-input streaming
   rejection and supplies a bounded buffer proposal retaining complete framing,
   declarations and exact known size/SHA. Twelve normal and twelve sanitizer
   methods pass, with independent matrix and focused checks. This proves a
   software compatibility defect on controlled inputs, not the historical
   carrier's exact cause. Its up-to-160-MiB+1 allocation needs Recovery qualification.
2. **Resolve the independent policy/runtime question without replaying AU.**
   [New REA/LLVM findings](research/attempt31av-ctrr-2026-11-15.md) reach the
   BootPolicy service, not a proven SIP2-clear implementation. Qualify the
   bounded kernel receiver and actual Recovery tool/library capability next.
   A decoder repair alone cannot satisfy enabled-CTRR admission. No new policy
   writer or weaker guard follows from an unresolved service response.
3. **M1 reviews offline, with no restart or page server.** Follow the
   [new handoff](tools/m1n1-client/attempt31av-instructions.md). Keep all 190 old
   source pins, previous kits and consumed state unchanged. A new installation
   proposal needs a qualified integration and CTRR strategy, separate owner
   authorization, boot021 rollback and Original return. No restart is ready now.
4. **After entry, reproduce the matched exact-board accelerated stack.** The
   previously identified J716c reference reports all physical cores, graphics
   and networking on newer matching inputs. Retain its thermal/runtime limits;
   compare CPU/core-type work, memory, rendering/input latency, network/storage
   and energy per task with macOS before claiming parity. An OS/firmware update
   is a separate deliberate decision, not an automatic fix for a decoder error.

[Plan and attributed validation](native/boot/attempt31av-plan.md). Original
Macintosh HD remains protected at Full Security. This offline work changes no
boot, security, firmware or volume settings. Native Linux/SMP/GPU/performance
remain NOT RUN in the closed attempt.

## Historical direction — 31AU controller integrated and reviewed, 2026-11-15

M1's `5807592` component review is accepted with its recorded input limits.
The new [31AU transaction](tools/boot-object31au-native/README.md) integrates
same-read object diagnostics, an in-memory selected-reference comparison and
candidate-independent boot021 rollback. It starts from the confirmed restored
boot021/disabled-CTRR baseline in a fresh namespace. No old state is reset and
the Linux candidate is unchanged.

1. **Lab Data staging and M1 review are complete.** The V2 helper,
   four-file kit and complete one-paste install/restore pages are built. Producer
   checks passed 39 controller methods normally and under sanitizers, seven
   renderer and 26 package/bootstrap methods. Independent review reproduced and
   verified fixes for two result-display contradictions. Final source closure
   has 190 entries, preserving all 167 old inputs. Root's final focused controls
   and exact source/artifact/page checks pass. The owner's authenticated staging
   result matches all four pinned files; no repeat copy is needed. No boot or
   security setting changed. The [staging receipt](native/boot/attempt31au-staging-2026-11-15.json)
   records the owner report separately from the frozen offline delivery records.
   M1 review `9faac49` is accepted with its explicit missing-input limits; its
   six prepared outputs match V2. The [reviewed handoff](tools/m1n1-client/attempt31au-reviewed-handoff.md)
   prepares direct M1 serving and the conditional test/rollback sequence.
   The owner has now authorized the scoped window. Temporary Startup Disk LAB
   is selected and independently classified read-only; current system remains
   ORIGINAL. No restart occurred. M1 follows the
   [authorized handoff](tools/m1n1-client/attempt31au-authorized-instructions.md)
   and manages the exact page directly. Original default return is required
   after the attempt.
2. **Use the next authorized Recovery visit for decisive readback evidence.**
   Record selected-reference changed/unchanged, read and framing/codec failure
   stage, exact decoded match, CTRR class, preservation and cleanup. Never boot
   an unverified candidate. Only a complete install pass can permit the separate
   90-second RAM observation; otherwise use independent exact boot021 restore.
   This is a new diagnostic transaction, not a replay of 31AR or a claim that
   disabled CTRR has been fixed. [Plan and limits](native/boot/attempt31au-plan.md).
3. **Continue the precise policy/version investigation without an invented fix.**
   [REA and LLVM](research/attempt31au-ctrr-2026-11-15.md) trace the raw/Mach-O
   distinction to a named custom-OS LocalPolicy API. The actual effect on existing
   SIP2 and the historical Recovery tool remain unqualified. Retain exact
   candidate plus enabled-CTRR admission and the existing rollback. No new policy
   writer, Original update or firmware change is justified by those facts alone.
4. **Reproduce the exact-board accelerated stack after entry is established.**
   Keep the previously identified J716c kernel, graphics Stage2, compatible
   Stage1, toolchain/modules/Mesa/firmware/runtime gates together. The separate
   full-config admission is implemented; the accelerated kernel remains unbuilt
   here. Native all-core work, GPU/fabric behavior, networking, storage, input
   latency, thermal behavior and energy per task must be measured against a
   comparable macOS baseline before moving daily development into Linux.

There is no restart cue from the offline review or a running server alone. M1
can manage its exact new page directly; no repeated server-readiness or clipboard
calibration loop is needed. Macintosh HD remains protected, and no settings,
boot objects or firmware have been changed by this offline work.

## Historical direction — saved 31AS failure classified, 2026-11-15

The [owner-authenticated saved-state result](native/boot/attempt31at-postcondition-2026-11-15.json)
identifies two failed candidate requirements: the selected payload was
`UNKNOWN`, not absent, and lab Kernel CTRR was explicitly disabled, not
unreported. Baseline, parser, role binding, Original Full/CTRR, both roles'
semantic and private-metadata preservation passed. The saved restored snapshot
passes exact boot021/disabled-CTRR requirements. Independent restoration and
Macintosh HD desktop/default return were also human-confirmed. No candidate
boot or native Linux window occurred.

1. **Resolve installation/readback before another restart.** The new
   `tools/postcondition31at/` observer has classified the preserved evidence
   without another Recovery visit. Keep the spent transaction unchanged. Add
   finite selected-object read/framing/codec/decoded-match diagnostics while
   retaining the original recognizer as acceptance authority. Qualify the
   writer's CTRR behavior independently; neither exit zero nor a public note's
   informal “CTRR off” wording permits weakening the candidate guard. The
   [source comparison](research/attempt31at-public-enrollment-recipes-2026-11-15.md)
   finds no demonstrated argv error and retracts the earlier compression theory.
2. **Reuse the exact-board accelerated stack as a unit.** The separate
   [J716c graphics profile](kernel/experiments/j716c-graphics-profile/README.md)
   validates the genuine full reference config and its 1,376-symbol difference
   from our minimal diagnostic. Reproduce kernel `a59e709c7377`, graphics Aura
   Stage2 `9da61857f9d9`, compatible installed Stage1, toolchain, modules/Mesa,
   firmware and runtime DT together. Keep the existing diagnostic validator.
   This tool is not a built kernel or a deployment. The base-M5 config flag and
   Pro installer are not substitutes for the tested Max configuration.
3. **Settle missing firmware and runtime inputs explicitly.** The published
   J716c report uses 27.2.1/26B131, bounded CPU clocks, verified telemetry and a
   separately deployed guardian. Our retained local version observations are
   26.6.2/25G83. Do not promise isolated shared-firmware effects or silently
   update Macintosh HD. A specific authorized update plan, if needed, follows
   a backup/compatibility/restoration review and preserves Original Full.
4. **Use one reviewed native window to answer several hardware questions.**
   Only after exact candidate/policy readback and cleanup pass, collect Aura
   entry, Linux entry, all 18 physical cores with concurrent work by core type,
   IPIs/coherency/timers, GPU binding and sustained frame checks, network/control
   access and telemetry. Retain independent boot021 restoration and Original
   default return. Do not spend a boot just to rediscover a format error.
5. **Measure usability and efficiency before moving development into Linux.**
   Compare CPU/memory throughput, input-to-frame latency, several concurrent
   apps, GPU/fabric behavior, storage and networking against matched macOS power
   settings. Measure energy per task and thermal behavior as well as speed.
   Then qualify persistent Omarchy, storage writes/durability, idle/suspend and
   peripherals separately. External 18-core/GPU success is evidence of a software
   route, not proof of parity on this machine or a need to wait for Apple.

No restart, transaction replay, security change or firmware update is prepared
by this offline work. M1's next role is source/evidence review of
`tools/m1n1-client/attempt31at-instructions.md`.

## Historical direction — after the 31AR shell refusal, 2026-11-15

[31AR's actual result](native/boot/attempt31ar-recovery-2026-11-15-result.md)
stopped at the unavailable `/usr/bin/cmp` before the controller. No installation,
managed mount, native entry or rollback ran. Macintosh HD desktop and default
return are human-confirmed; boot021 restoration remains outstanding. This is
not evidence of a firmware rejection or failed CPU startup.

1. **Review the corrected 31AS page offline.** It removes `cmp` and `awk`,
   checks hash-command failures and preflights fixed utility paths. Both full
   operation blocks retain the exact 31AR helper/profile/kit/state and independent
   boot021 restoration. Use executed restricted-utility shell tests, exact
   source-only page preparation and M1 review; no native rebuild or restage.
   The [dependency review](research/attempt31as-recovery-dependencies-2026-11-15.md)
   distinguishes physical observations from fixture coverage. No restart follows
   from an offline pass alone.
2. **Use the exact J716c implementation as the next accelerated baseline.**
   Reproduce the published kernel `a59e709c7377` and paired graphics Aura Stage 2
   `9da61857f9d9`, configuration and runtime-DT gates in the isolated build
   environment. The [boot/firmware review](research/attempt31as-boot-and-firmware-2026-11-15.md)
   records reports of all 18 CPUs, N1 and accelerated Hyprland on this board
   lineage, plus missing Stage 1/root/firmware/guardian inputs. This is stronger
   than using the J714s Pro installer or an unbooted latest kernel. The reports
   use bounded frequencies and do not establish macOS parity.
3. **Choose a deliberate OS/firmware plan before changing the host.** Both local
   installations remain 26.6.2/25G83; the exact-board reference used 27.2.1/26B131.
   Updating Macintosh HD alone does not establish the lab's selected firmware.
   A lab OS update also cannot be promised to isolate shared firmware effects.
   Inventory requirements, backup and restoration first, retain Original Full,
   and obtain specific authorization for any actual OS/firmware operation. No
   update is required to repair the missing comparator.
4. **Use a reviewed native window for evidence that changes the next decision.**
   After page review and a concrete boot cue, require exact install readback and
   cleanup, then observe loader/Linux entry, distinct concurrent work across the
   12 Performance/6 Super topology, checksums, timers and liveness. Retain the
   independent boot021/default-return path. A CPU list, VM run or desktop photo
   is insufficient. Keep new loader/kernel/firmware choices separately pinned.
5. **Qualify a responsive accelerated workstation before parity claims.**
   Bring GPU/display and CLPC memory/fabric policy into the measured CPU/memory
   work; extra CPU cores alone do not eliminate software-rendered UI delays.
   Validate N1/control access, read-only NVMe, input-to-frame latency, several
   apps, clock/thermal telemetry and energy per task. Compare against the same
   Mac with matched power settings; preserve the old AC Low Power Mode baseline
   under that label. Qualify persistent Omarchy, update guards, storage writes,
   suspend and peripherals separately, then move the development agent into it.

## Historical direction — after successful 31AP Recovery admission, 2026-11-15

[31AP's physical result](native/boot/attempt31ap-recovery-2026-11-15-result.md)
confirms complete guarded Recovery collection, initial admission and owned
read-only Preboot cleanup. Macintosh HD desktop and default return are
human-confirmed. This clears the reader/admission blocker. It establishes no
new Linux entry, CPU count, GPU support or performance measurement. Boot021
restoration is still outstanding; another read-only parser-only visit is not
the next engineering objective.

1. **Complete review and delivery of the new 31AR transaction.** The original
   controller under `tools/boot-object31ar-native/` now implements the owned
   RO-to-RW Preboot session, durable private baseline and spent markers,
   cross-visit target commitment, exact readback and owned cleanup. Separate
   install and candidate-independent boot021 restore pages are under
   `tools/recovery31ar/`. M1 follows the [new review handoff](tools/m1n1-client/attempt31ar-instructions.md).
   Preserve the matched Aura/kernel/DT/root candidate and all old state.
   Offline tests and source-profile page checks do not establish delivery,
   staging, actual APFS transitions, Apple command behavior or restart readiness.
2. **One separately authorized hardware test after that integration passes.**
   Install the lab-only candidate, verify it, observe one independently timed
   RAM-only Linux window and verify boot021 restoration/Original default return.
   Capture distinct Aura entry, Linux entry, online-core census, concurrent
   checksums and timer/liveness results. The target is all 18 cores across the
   existing 12 Performance/6 Super ADT topology; do not count a firmware logo,
   VM result or online mask alone as concurrent hardware execution.
3. **Establish CPU and memory quality on this machine.** Measure per-core-type
   and all-core throughput, frequency/idle behavior, scheduler wakeup tails,
   memory bandwidth/latency, thermals and energy per fixed task. Preserve the
   historical macOS AC Low Power Mode baseline as such; collect a comparable
   normal-power reference before claiming everyday performance parity.
4. **Build a usable native workstation path.** Validate networking/control
   access and read-only internal storage, then separately authorized Linux
   persistence and writes. Continue G17C/display acceleration work early enough
   to address measured menu/input/frame latency. Retest renderer threading and
   several simultaneous apps under native load. CPU count does not establish
   a smooth high-resolution desktop or macOS-equivalent battery life.
5. **Close capability and reliability gaps with evidence.** Network reconnect,
   storage flush/durability, idle/suspend/resume, audio/camera/peripherals and
   acceleration need their own native tests. Existing encrypted macOS-data
   access remains separate from NVMe throughput; keep the reference protected.
   Move the main development agent into Linux once connectivity, persistence,
   interactive latency and recovery are reliable enough for daily work.

No restart or installation is ready from offline tests alone. M1 can review
31AR without another machine restart, an old-suite rerun or a large image
transfer. Exact helper/profile delivery, lab staging and the independently
accessible restore page must be confirmed before the later physical cue.

The [shared M5 source review](research/attempt31ar-shared-m5-code-2026-11-15.md)
identifies newer Aura/Linux descendants, J716c GPU interrupt support, per-core
interrupt routing and N1 power-management fixes worth using for the subsequent
performance build. The linked J714s installer is not admitted for this J716c.
Its reported newer firmware stack does not establish compatibility with the
current local 26.6.2/25G83 lab. The existing candidate remains useful for entry,
concurrent workers and per-core FIQ timer checks; balanced device IRQ routing
and a usable accelerated Omarchy desktop require separate validation.

## Historical direction —31H and heterogeneous CPU enablement, 2026-10-21

Native Omarchy still has one online CPU and software rendering.31G established
CPU1 power response without entry.31H combines precise reset-format, power,
opaque core-state and recorder evidence in one bounded session. This is a
startup diagnosis, not a measured performance improvement.

1. M1 independently verifies [31H](tools/m1n1-client/attempt31h-instructions.md),
   publishes readiness, then one human-started lab campaign and macOS return.
   Use the [outcome table](native/boot/attempt31h-plan.md) to choose the next fix;
   no blind replay, cold-entry redirect or guessed power/stop write.
2. After actual CPU1 entry/callback/park validation, prepare one Linux two-core
   batch combining coherence/atomics, timers/IPIs, clocks, memory throughput,
   renderer threading and input-to-frame latency.
3. Validate representatives of the remaining clusters, then all18 cores:
   12 Performance (ADT M) plus6 Super (ADT P), three clusters of six. Calibrate
   scheduler capacity, DVFS/frequency invariance and idle energy with evidence.
4. Continue N1 WLAN transport and separately reviewed read-only ANS storage.
   SSD bandwidth and shared encrypted macOS-data access remain separate tasks.
5. Native GPU acceleration remains necessary for efficient high-resolution
   rendering; CPU concurrency alone is not desktop parity.

The expandedVM tests reduce software-error reboots but do not emulate Apple's
reset firmware, power domains or cache visibility.31A–31G are consumed;
native31H NOT RUN. macOS and installed boot021 remain intact. No routine M1
restart or policy recheck; no new images are needed for31H.

## Historical direction — after 31D, superseded by 31F below

Native Omarchy still has one online CPU and software rendering. 31C and 31D
passed the corrected RAM gate and acknowledged CPU1 startup writes, but entry
remains unverified. Console isolation did not establish a fix. The
[31E review](native/boot/attempt31e/review.md) and
[testing strategy](research/testing-strategy-31e.md) supersede older assignments.

1. **Stay offline until a more informative native campaign is ready.** Use
   exact-instruction emulation, image/source audits, publication-interleaving
   tests and historical/failure replay. The new early-recorder proposal leaves
   the normal C stack intact; its native code-publication/controller path still
   needs implementation and review. No complete M5 emulator is presumed.
2. Prepare one CPU1 start session with early entry/MMU-state observations and
   conditional repeated timer requests. Preserve uncertainty and stop after
   faults; do not chain Linux from an unknown secondary state. M1 can run the
   [offline intake](tools/m1n1-client/attempt31e-instructions.md) now; no reboot
   is requested. Future M1 helper-health checks replace unconditional restarts.
3. Once entry and a valid handoff are established, combine two-core Linux
   timer/IPI/coherency tests, renderer threading, memory and USB-link measurement
   in one healthy session. Then expand within/across clusters to all 18 cores,
   with fixed-work throughput, tail latency, sustained thermals and energy per
   task measurements. Core count alone is not performance or efficiency parity.
4. Continue N1 transport/WLAN work and rebase read-only ANS storage for current
   two-stage delivery in parallel. Storage initialization runs last under its
   reviewed allowance; APFS/encryption and safe persistent Linux storage are
   separate from raw NVMe speed. USB relay supports development meanwhile.
5. Bring verified DVFS/idle behavior and native GPU acceleration into the
   measured workstation plan. GPU support remains important for smooth desktop
   operation and energy use even after CPU concurrency improves.

31A–31D are consumed; copy-only 31 and native31E are held. macOS, installed
boot021, security/default/volume state remain intact. Routine policy checks
remain waived; all new offline results are distinct from native proof.

## Historical direction — after native attempt 27, 2026-10-20

**Omarchy boots natively with USB/SSH and automatic keyboard startup.**
Two-stage delivery works; the user can type without extra letters but menus
and applications remain slow. One CPU, software graphics and a RAM root remain.
The current [workstation plan](native/boot/post-attempt27-plan-2026-10-20.md)
supersedes the historical attempt assignments below.

1. Finish intake of the prepared attempt-28 CPU observation package. Its
   separate launcher, exact pair and bounded collector keep writes disabled.
   Establish boot-state mapping/telemetry before selecting a frequency cap.
   [Validation](native/boot/attempt28/validation.md) records the offline limits;
   M1 readiness and human start precede the native attempt.
2. Resolve one-secondary entry, then cross-cluster/all-18-core operation,
   scheduling, telemetry and idle/thermal behavior. Measure desktop latency
   alongside CPU progress; CPU count is not a substitute for graphics work.
3. Continue N1 PCIe/DART/ACIPC research toward independent Wi-Fi and a browser,
   and rebase the read-only ANS experiment for two-stage delivery. Later native
   ordering follows readiness/results; do not hold ready work for full CPU parity.
4. Establish persistent Linux storage and matched CPU, networking, SSD and
   energy measurements before moving the user's main REA workflow into Omarchy.
   Access to existing encrypted macOS files is a separate dependency.

The user authorized attempt-28 preparation/publication; native/live remains
NOT RUN. Use the [M1 handoff](tools/m1n1-client/attempt28-instructions.md).
Attempt 27 is consumed. Keep the current entry and routine policy-check waiver.

## Phase 0 — Foundations (session 1)

| # | Item | Status |
|---|---|---|
| 0.1 | Exact hardware inventory plus sanitized device-tree capture | ✅ |
| 0.2 | Workspace, continuity docs, git repo | ✅ |
| 0.3 | Portable benchmark suite (CPU/SME, memory, storage) plus Metal GPU benchmark plus synthetic GGUF tool | ✅ |
| 0.4 | macOS baseline run (AC; energy mode recorded) | ✅ |
| 0.5 | Research: Asahi status for t6050, REA analysis, Omarchy ARM64 analysis | ✅ |
| 0.6 | Compatibility matrix v1 (ADT block → mainline/Asahi driver → status) | ✅ |

## Phase 1 — Linux in isolated environments (approved 2026-10-11: vzrun VM, REA project-local, MLX venv)

| # | Item | Why |
|---|---|---|
| 1.1 | ✅ `vzrun` built (ad-hoc signed) and booting a GPG-verified Arch Linux ARM image with scripted jobs | Layer 3 test bed without host installs |
| 1.2 | Run the identical C benchmarks in the VM | Quantify VM overhead (CPU, memory, storage) vs macOS. Expected near-native CPU; VM results are never "native parity" |
| 1.3 | ✅ SME2 is exposed to VZ guests (SVL 512). In-guest `sme_*` throughput ≈ 98–99% of macOS | Matrix-unit parity for CPU inference on Linux |
| 1.4 | Arch Linux ARM container or VM: resolve Omarchy package set on aarch64 (`pacman -Sp`) | Ground-truth package availability |
| 1.5 | Omarchy-arm64 installer branch: arch guards, package substitutions, bootloader abstraction | Target userspace |
| 1.6 | Hyprland in VM (virtio-gpu, software GL) smoke test | Desktop integration without GPU acceleration |
| 1.7 | ✅ QEMU/VirGL graphics, Venus/MoltenVK compute and ggml RPC implemented in the existing workspace/VM | Measured results in `reports/vm-vs-macos-parity.md`; no new host install needed for this path |
| 1.8 | ✅ Separate Mesa VA package: lossless NV12/I420/YV12 downloads and optional NV12 H.264 decode | 18 image cases pass; QEMU decode CPU cost reduced 41.3%; see `reports/video-download-and-nv12-2026-10-12.md` |

## Phase 2 — Native enablement research for t6050 (no hardware writes)

| # | Item | Notes |
|---|---|---|
| 2.1 | Per-block gap analysis: AIC3, DART t8110, ANS3 NVMe and SART "coastguard", ASC wrapper v6 / mailbox, PMGR, cpufreq, ATC/USB, DCP, MTP | Builds on compatibility matrix v1 |
| 2.2 | Draft `t6050.dtsi` / `t6050-j716c.dts` skeleton from the sanitized ADT (CPU topology, AIC3, DARTs, PMGR, UART, WDT, I2C, GPIO) | Static, reviewable; boot-testing needs native hardware and m1n1 support |
| 2.3 | CPU scheduling design for M+P clusters: EAS capacities from measured per-cluster throughput, uclamp/cgroup "QoS tiers" that mimic macOS placement | Measured macOS behaviour: background QoS → M cores at about 25% speed |
| 2.4 | GPU: track Asahi AGX (G13–G15 supported; G16/G17 not). Document the G17 matrix-unit gap | Metal FP16 GEMM ≈ 64 TFLOPS vs ≈ 17.6 TFLOPS scalar FP16 FMA |
| 2.5 | ANE: document the exclave-mediated design (`ane,t8132exclave`) and what Linux would need | Likely the hardest block |
| 2.6 | 🔄 User-authorized local REA/binary analysis for focused implementation questions; artifact identity, confidence and independent experiments recorded | Metadata and supplemental LLVM ARM64 analysis completed; REA decompilation backend unavailable. Original local implementations; no proprietary code copied |

Update, 2026-10-13: REA/Ghidra is operational in the isolated Linux lab
(F-070–F-077). CPU startup/idle and driver-interface findings already exist.
Use them against a specific observed native failure; broad repeated binary
survey is not the next dependency. No proprietary code is copied into Linux.

## Phase 3 — Native deployment (separate explicit authorization required)

Historical path, recorded 2026-10-15 after attempt 15; the current direction
above supersedes its attempt/status assignments. Native Linux reached diagnostic PID 1 on
one CPU (attempts 14–15). Attempt 14 reset 5.6 s after genpd's bulk power-off;
boot034 removed that and ran ≥ 27.6 s, then reset 5.7 s after releasing the
last of the SMC-owned `smc_i2cm` domains, which no Asahi device tree exposes.
Boot035 drops those seven domains from the Stage-B DT (one variable). See
`native/boot/attempt15-review-2026-10-15.md`. Each step below is a separate,
human-started RAM session.

### Path to a native Omarchy boot

| Order | Milestone | What it needs | Evidence to advance | Status |
|---|---|---|---|---|
| 1 | **Stable native baseline** (boot035 / attempt 16) | DT without SMC domains; the boot034 ladder releases the other 145 unclaimed domains | `ladder complete` and heartbeats to 180 s | ✅ attempt 16: ladder complete (74 domains), alive past 108 s |
| 2 | **Control channel into Linux** | USB device-mode networking over the M1 cable. boot036 (`kernel/experiments/usb-gadget/`): gadget stack built in; three dwc3 device-mode cores on the PHY state m1n1 leaves (ATC 0–2 domains disabled); a CDC-EEM gadget (bulk only; the ports flag `ncm-interrupt-ep-disabled`) with IPv6 link-local and key-only SSH | The M1 sees a USB network interface; ping and SSH into Linux | 🔄 attempt 17: Linux USB works on the M5, macOS lacks EEM; attempt 18 (ACM + ECM): control-endpoint timeouts; attempt 21 (boot039, bulk-only `gser`): EP0 healthy for 10 min, macOS publishes the interface, the M1's reader streams 36,909 bytes, then a dwc3 `BUSERR` and an unhandled DART interrupt stall it; attempt 23 (boot040): the DART is v2.4 and the fault sits on the instance the DT left out; ✅ **attempt 24 (boot041)**: both DART instances per controller, the USB log streams from the M5 to the M1 for ten minutes with no fault; 🔄 the M1 to M5 direction and SSH in attempt 25; SSH + web over the bulk pipe VM-proven (job 046) |
| 3 | **RAM root with a real Arch userspace** | Arch Linux ARM packages in a zstd initramfs delivered by the proxy (≈ 4–5 MB/s observed; 126 GiB RAM), init that starts sshd on the USB link; 16K-page-safe packages | Login and the Linux-side agent reachable over the link | 🔄 attempt 25 handoff ready: Omarchy's own root with the SSH link, the clock step and the M1's web relay |
| 4 | **Visual Omarchy boot.** *Omarchy* means: built by Omarchy's own installer from Omarchy's repositories and running Omarchy's own session (SDDM → uwsm → Hyprland → Quickshell, its menu and first run), with deviations only where the M5's hardware forces them (our kernel and DT instead of Omarchy's, no bootloader, packages for absent hardware). Anything less is *Omarchy-style* | Hyprland on `simpledrm` (built in) with Mesa llvmpipe, one CPU, in a RAM root; proven first in the VM. For Omarchy itself: the edge aarch64 ISO's runtime installed phase by phase (VM job 045, a 2.34 GB image) and a way to deliver it (a larger launcher heap and deadline, or two stages over the USB link) | Omarchy's own desktop on the M5 screen | 🔄 Omarchy-style ✅ attempt 19 (2026-10-16): desktop up, view-only, one CPU, software rendering; ✅ attempt 20: ten stable minutes with a live status screen and on-screen benchmarks (job 039: hand-picked packages, our own session). Omarchy ✅ VM only (job 045, 2026-10-17: Omarchy's session, first run, menu, Chromium and Obsidian on the boot035 Image; `omarchy-arm64/omarchy-root-report-2026-10-17.md`); ✅ **native, attempt 22 (2026-10-18)**: the job 045 root on boot035 with the launcher's `omarchy` profile, desktop about 40 s after the handoff, ten stable minutes, view-only; 🔄 attempt 25: the same root with the link, Claude Code and passwordless sudo, so agents run inside it |
| 5 | SMP, idle/DVFS, thermal | Existing REA startup findings; secondary bring-up; cpuidle/cpufreq | Stable all-core operation | ⬜ |
| 6 | Input, storage, wireless, GPU | MTP keyboard/trackpad (DockChannel): 🔄 keyboard, attempt 26 (boot042, 2026-10-19) loads the keyboard path as modules from the SSH session (NOT RUN); NVMe (patches 0004–0005): read-only storage is attempt 27, behind a reviewed launcher change; Wi-Fi, G17 GPU (no Linux driver) | Per device, measured | ⬜ |

Parallel tracks that need no Linux boot: the PMGR probe can confirm the SMC
mechanism per domain in minutes (`tools/m1n1-client/pmgr-probe-instructions.md`),
and the hv003 ladder (`tools/m1n1-client/hv-instructions.md`) is the tracing
tool if a reset ever needs register-level evidence.

## Phase 4 — Performance engineering on native Linux

Iterate per subsystem with the Observe → Investigate → Compare → Design →
Implement → Test → Benchmark → Iterate loop, scored in
`reports/performance-parity.md`.

For this exact M5, native userspace and the USB/SSH control channel now work.
Current priorities are full CPU capability/efficiency, independent built-in
Wi-Fi and persistent SSD access, with graphics latency measured alongside them.
G17 graphics/display acceleration remains important to interactive performance
and energy. Other hardware follows the user's workstation acceptance targets.
Stage B deliberately uses `idle=nop`, one CPU and no cpufreq: it tests liveness,
not efficiency. Removing those restrictions requires independent evidence.
The [current Asahi M5 table](https://asahilinux.org/docs/platform/feature-support/m5/)
still lists t6050 GPU, cpufreq, cpuidle, DCP and USB support TBA (checked
2026-10-13); our private prototypes need physical validation, not an installer toggle.

Before claiming parity, repeat matched macOS/native Linux workloads on the
same machine, with recorded build/compiler/kernel/DT, power mode/source,
brightness/resolution, thermal starting state and run count. Report throughput
and latency together with energy per completed task, idle watts and sustained
thermal behavior. Keep measurement boundaries comparable (whole-machine power
versus modeled component counters are different quantities). Record uncertainty
and missing devices explicitly. VM results and a successful boot cannot stand
in for native performance or battery-life results.
