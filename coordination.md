# Coordination: agents working in this workspace

Created 2026-10-13. Read this together with `AGENTS.md`, `progress.md`,
`blockers.md` and `decisions.md` before starting work. If this file and an
older plan disagree, this file wins for ownership and order of work.

## Roles

### Current M1 offline readiness — 31D, 2026-10-21

M1 pulled **`c331796`**; all **60** source pins, boot042's **13** package
files, existing boot021/helper and clean client `57a9339` PASS. **73 Python
methods PASS**, all 11 required subprocesses exit 0, no skips/fixes; additional
independent console image/source audit equals the Git binding. No USB, target
allocation/start or real 31D receipt; prior 31B/31C evidence digests unchanged.
Human reports both computers ready. Publish before fresh human 31D start and
90 s timer confirmation. **Native31D/hardware writes/CPU1/Linux SMP NOT RUN;
live attempts 0.** Existing image/client/macOS/settings unchanged; routine
policy rechecks waived and protections remain last reported. No Linux
continuation or retry. Evidence: `native/boot/attempt31d-m1-offline-2026-10-21.md`.


### 2026-10-21 · M5: 31C reviewed; 31D console-isolation experiment ready offline

31C passed the actual RAM gate and acknowledged both CPU1 starts, then timed
out before verified arrival. Return to usual macOS confirmed. CPU1 may have
stalled before its flag; zero executed instructions is not established.

Public-source and exact-image review found unbounded diagnostic UART polling
before arrival. Fresh REA/Ghidra queries plus 214 byte/LLVM-verified instruction
words did not establish a missing power write; cross-boundary pseudocode was
rejected. 31D tests the console hypothesis with two RAM base zeroes plus cache
publication before start and partial reset/spin observations. USB retained;
installed boot021, start sequence, prior controller sources and receipts frozen.

73 Python methods, real pinned-client/parser paths and 9 actual-source UART
cases in normal/ASan/UBSan builds PASS in job 061. First harness compile warning
fixed without relaxing Werror. **M1 intake pending; native31D NOT RUN.** Follow
`tools/m1n1-client/attempt31d-instructions.md`: offline readiness first, fresh
human start, one CPU1 test, immediate Macintosh HD return. No Linux continuation,
new image, power/security/volume change or routine policy recheck. Performance
and efficiency unproven. Review: `native/boot/attempt31d/review.md`.

### Current M1 result — 31C consumed; CPU1 arrival unverified, 2026-10-21

**31C consumed: STOP / `cpu1_arrival` / `cpu1_arrival_timeout`**, execution
`c48464d` after handoff `61bbe52`. All 11 RAM-check booleans true, BootArgs
revision 3. **9 mutation requests, 2 CPU1 start writes attempted/acknowledged**;
arrival unverified, 0 timer requests completed, counter progress unverified.
Controller exit 1 in 4.466 s; supervisor 4.865 s, no deadline. Human confirmed
usual Macintosh HD return +51.953 s after start, within 90 s. No retry,
reconnect, rollback or further target command. CPU1 experiment ran; **Linux
boot/native Linux SMP/renderer tests NOT RUN**. A timeout does not prove CPU1
executed no instructions. Existing boot021/client pin, macOS and settings
unchanged; routine rechecks waived and protections remain last reported.
M5 next: offline review of CPU1 entry/arrival and observation path; preserve
all once/consumed receipts. 46 source pins and 60 offline methods passed.
Evidence: `native/boot/attempt31c-2026-10-21-result.md` and its two sanitized JSON
records. This supersedes frozen checklist/readiness text for the controller.


### Historical M1 offline readiness — 31C, 2026-10-21

M1 pulled **`61bbe52`** and independently verified all **46** 31C source
pins, boot042's **13** files, existing boot021 image/helper and clean client
`57a9339`. **60 Python methods PASS** (11 new RAM/controller, 3 new supervisor,
46 prior), all nine requested subprocesses exit 0; no skips/fixes. No USB,
target allocation/start or real 31C receipt. Prior 31B evidence digests are
unchanged. Human reports M1 ready/M5 Running proxy; fresh human 31C start and
90 s timer confirmation follow publication. **Native31C, CPU1 entry and
Linux/native SMP/renderer tests NOT RUN; live attempts 0.** No installed-image,
macOS/security/default/volume change; routine rechecks waived and protections
remain last reported. No Linux continuation or retry. Evidence:
`native/boot/attempt31c-m1-offline-2026-10-21.md`.


### 2026-10-21 · M5 reviewed 31B; corrected RAM gate ready offline as 31C

31B report `4fb684c`: STOP before allocation/start, zero mutation requests,
safe Macintosh HD return. Confirmed controller defect: its <1 TiB address
ceiling excludes this machine's DRAM, observed at 1 TiB with a 128 GiB span.
Exact rejected numeric fields were not recorded in 31B; no CPU/RAM fault is
established. Read-only chosen data, earlier native evidence and pinned public
bootloader source support the correction; fresh REA was unnecessary here.

31C retains the frozen 31B CPU1 sequence, verifies BootArgs' usable interval
against this exact machine aperture and matching target ADT, and records
boolean refusal predicates. Separate receipt/confirmation; preserve 31B.
60 Python methods, real BootArgs/ADT and high-address pinned-client tests PASS
in job 060; 14 new host methods PASS. No native action or macOS/settings change.
**M1 intake pending; native31C NOT RUN.** Follow
`tools/m1n1-client/attempt31c-instructions.md`; publish offline readiness, wait
for a fresh human start, one CPU1 trial then Macintosh HD. No Linux continuation.
Review: `native/boot/attempt31c/review.md`. Successful entry precedes two-core
Linux/timer/IPI/coherence validation and renderer threading. Policy rechecks
remain waived; performance/energy parity is still unproven.

### Current M1 result — 31B consumed; M5 offline review next, 2026-10-21

**31B consumed: STOP / preflight / `ram_bounds`**, execution `a6ced17` after
handoff `7d505fd`. One supervisor run, controller exit 1 in 0.781 s; supervisor
1.192 s, no deadline. **Zero mutation requests, CPU-start writes attempted or
acknowledged, and completed requests.** No helper allocation/upload, CPU1 setup
or start. CPU1 entry and Linux/native SMP/renderer tests **NOT RUN**. Human
confirmed usual Macintosh HD return at +57.883 s, within 90 s. No retry,
reconnect or further target command. Installed boot021/client `57a9339`, macOS,
security/default/volume settings unchanged; routine rechecks waived and
protections remain last reported. All 36 source pins and 46 offline methods
passed before execution. Preserve consumed receipts. M5 next: offline review
of the RAM-bound predicate and pinned BootArgs interpretation; actual rejected
bounds were not recorded, so cause remains unknown. Do not relax the guard or
infer CPU/RAM failure. Frozen source-pinned checklists are historical; this
result supersedes their pre-execution readiness text. Evidence:
`native/boot/attempt31b-2026-10-21-result.md` and its two sanitized JSON records.

### Historical M1 offline readiness — CPU1 controller31B, 2026-10-21

M1 pulled **`7d505fd`**; all **36** new source pins, boot042's **13** files,
exact boot021/192-byte helper/offline controller and clean client `57a9339`
PASS. **46 Python methods PASS** (19 controller, 3 supervisor, 11 census, 5 audit,
8 renderer), zero skips/fixes. No live-use receipt existed before/after tests;
no USB, target allocation or start. Native31B/hardware writes/CPU1/Linux SMP
**NOT RUN**, live attempts 0. Human reports M1 restart/M5 Running proxy and
confirms cable/power/unlocked/lid/90s timer. Publish readiness before one
supervised CPU1 entry/two-request test. Existing boot021, macOS/default/security/
volumes unchanged; routine policy checks waived. No Linux continuation or retry.
Evidence: `native/boot/attempt31b-m1-offline-2026-10-21.md`.


### 2026-10-21 · CPU1 controller 31B implemented and offline validated

User authorized CPU1 controller implementation/testing and the M1 handoff.
Original controller uses installed boot021, a 192-byte RAM helper, the existing
CPU1 stack and exactly two startup-register writes. It verifies entry/identity
and two bounded timer-request completions; no Linux launch or CPU-frequency
change. Post-start reads/publication avoid global exception-guard changes and
counter clearing. Exact relocated code, topology, source pins and one-use
receipts gate execution. No chainload, reset-vector/installed-code rewrite,
boot/security/default/volume change or extra core. macOS remains intact.

46 Python methods PASS; GCC/Clang helpers byte-identical, actual ARM64 RAM
helper execution PASS, pinned-client serialization PASS, actual secondary-loop
normal/ASan/UBSan PASS, real ADT-parser fixture PASS. VM is not native proof.
See `native/boot/attempt31b/validation.md` and job 059. Fresh REA was unnecessary:
accepted PMGR behavioral evidence plus the exact public bootloader source
support this experiment; rejected decompiler pseudocode was not used.

**M5 preparation PASS; M1 intake pending; native 31B NOT RUN.** M1 follows
`tools/m1n1-client/attempt31b-instructions.md`, publishes offline readiness,
then waits for one human-started existing Boot Lab proxy session. Controller
60s/supervisor 65s/human 90s bounds; immediate Macintosh HD return after outcome.
No retry or automatic Linux continuation. Routine policy checks waived.
31A consumed and old copy-only 31 held; Linux two-core/timer/IPI/coherence and renderer
integration follow entry evidence, with performance/energy still unproven.

### 2026-10-21 · M5 reviewed 31A; select CPU1 entry/park experiment

Reviewed M1 report `527defe`: CPU0/CPU1 locked mirrors match installed vectors;
zero starts, safe Macintosh HD return. Prefer a CPU1-only RAM-state controller
using installed boot021 over a new image/chainload. Exact image/symbol/source
checks verify entry branches, shared-state placement and dedicated CPU1 stack.
Five new offline audit methods plus 11 census/eight renderer regressions PASS.
Existing SMP call waits are unbounded; WFE-mode setter sends IPIs once a core
is alive. The proposed controller must handle ordering, bounded request/return,
late arrival and partial-write failures explicitly. It is not implemented yet.

**31B is planning only; no restart/live command ready.** M1 reads
`tools/m1n1-client/attempt31b-planning-update.md`; do not replay consumed 31A.
Next: implement/test the bounded start controller, then independently review
its release before one human-started CPU1 entry/park trial. Linux two-core
handoff/DT/launcher and renderer comparison follow entry evidence. All native
SMP/performance/energy claims remain unproven. Original macOS and settings
unchanged; routine policy checks waived. Prior 31A source pins stay historical;
the current stage-b pointer intentionally now directs to the planning notice.

### Current M1 native result — census31A consumed, 2026-10-21

**Census31A consumed**, execution `f105ed0`: one command, exit 0 in 1.155 s,
**two guarded RVBAR reads / zero CPU starts**. CPU0 and CPU1 both locked,
target class `vectors`, image offset `0x0`, mirror-only evidence. Result
`CENSUS_COMPLETE_REVIEW_REQUIRED`; **native SMP, Linux boot and renderer NOT RUN**.
Human returned to usual Macintosh HD; recorded +82.036 s from command start,
within 90 s. No retries/reconnect/PMGR read/write, image transfer, chainload,
CPU/module/renderer or boot/security/default/volume change. Existing proxy
exception diagnostic counter read/cleared as documented; no hardware write.
Owned caffeine stopped. Routine policy checks waived; protections remain last
reported. Old copy31 HOLD; 31B needs separate RAM-entry/deployment review and
native validation. Mirror equality is not execution proof or authorization.
Evidence: `native/boot/attempt31a-2026-10-21-result.md`; exact sanitized JSON:
`native/boot/attempt31a-census-2026-10-21.json`.

The source-pinned stage-b/31A checklists remain unchanged for provenance.
This current result supersedes their pre-execution readiness/NOT RUN text.
Do not replay 31A or continue automatically to 31B. M5 owns the offline review.


### Historical M1 offline readiness — census31A, 2026-10-21

M1 pulled **`964aaac`** and independently verified all 31 SMP source pins,
boot042's 13 files/declared boot021 revision and clean client `57a9339`.
Boot021 image SHA-256 `ff75f4a9…72664`; census offline PASS, no USB opened.
**19 methods PASS** (11 census, 8 renderer), no skips/fixes. Native31A/live,
CPU starts, SMP, Linux and renderer tests **NOT RUN**; live attempts/MMIO reads 0.
Human has already reported M1 restart and M5 Running proxy and confirmed direct
cable/power/unlocked/lid/90s timer. Publish before executing the authorized one
census. No new image, startup candidate, CPU start, chainload or write operation.
Old copy31 remains HOLD; 31B requires separate review. Routine policy rechecks
waived; macOS/boot/security/default/volumes unchanged. Evidence:
`native/boot/attempt31a-m1-offline-2026-10-21.md`.


## Historical preparation — revised attempt31 / census31A intake

2026-10-21. User authorized native SMP and renderer-threading development.
Original guarded single-secondary startup candidate fully linked in the VM;
14 actual-function cases PASS both normally and under ASan/UBSan.11 census
and8 renderer tests PASS; real pinned ADT parser checks PASS. Linux two-CPU
shared-payload/futex smoke PASS for2,000 rounds. All are offline/VM evidence.
Fresh REA verified53 PMGR instruction words; cross-boundary pseudocode rejected.

New renderer policy uses online CPUs intersected with process affinity, cap4.
At identical3456x2160 pixels, two-CPU VM control terminal first-buffer delays
685–754ms became37–41ms with one configured worker; full callbacks221→216ms.
Six CPUs/four workers gave59ms full callbacks. Neither physical presentation,
native CPU functionality nor energy/parity is established. Code/evidence:
`kernel/experiments/smp31/README.md`, `validation.json`, and
`native/boot/attempt31/smp-vm-results.json`.

**Next authorized live step is census31A only.** M1 reads
`tools/m1n1-client/attempt31-smp-instructions.md`, verifies offline, publishes
readiness, then waits for human restart to the existing Running proxy entry.
Two guarded RVBAR reads, no CPU start, Linux launch, chainload, hardware write,
new image transfer or security/volume/default change; then return to Macintosh
HD. Reset-target/entry remains unknown. Even matching mirrors require review
before deploying the offline candidate. Native31A/SMP/renderer **NOT RUN**.

The old copy-only31 pair/profile/collector remain **HOLD**. This notice
supersedes earlier next-boot/readiness wording below. Original macOS remains
intact; routine policy rechecks remain waived.31B needs a reviewed RAM startup
path, exact two-core DT/launcher and native timer/IPI/coherency checks before
renderer integration or expansion. Other agents' jobs047/048 are untouched.

### Historical offline latency diagnosis — 2026-10-21

Attempt31 remains **HOLD**; no native images or boot instructions are released.
Original compositor tracing and CPU/RAM/pixel references are implemented and
VM-tested. In the real Omarchy VM workload, terminal first-buffer delays of
812–976ms included785–953ms inside rendering. A separately gated drain split
roughly174ms of scene work from52ms of final-pass work. Four configured renderer
workers on six VM CPUs reduced terminal first-buffer delay to about42ms and
full callbacks from250ms to60ms; clients stayed on one CPU. This is VM-only
sensitivity, not native SMP or a prediction of physical presentation/energy.

Native throughput/bandwidth and the entire physical3–5s interval remain open.
Prioritize native SMP/renderer threading and verified G17 GPU interfaces over
another copy-only trial. REA checked152 GPU instruction words; one decompiler
boundary was rejected and the other has unresolved dispatch. No guessed GPU
register sequence was deployed. Tests, references and limitations:
`native/boot/attempt31/diagnosis/README.md`. M1 reads
`tools/m1n1-client/attempt31-diagnosis-update.md` and keeps the current hold.


### Historical held M5 candidate — attempt31 final-copy experiment, 2026-10-21

Reviewed attempt30 (`45952cc`): native compositor CPU near 97%, full callbacks
about 515 ms, tiny callbacks about 256 ms; CPU estimate near 2.65 GHz. Original,
default-off Hyprland final-copy optimization built and pixel-checked. VM
headless crossover full medians 104.3 ms versus 78.3 ms (about 25% lower), no native
speed/energy/parity claim. Exact packed-root fallback, identity refusal and
independent cleanup checks PASS. Full-pair VM boot/desktop/second SSH link PASS
(373s wall);143 final host tests PASS. Native/live NOT RUN; M1 intake pending.

New matched pair: stage one 60,669,159 bytes (`6ffb37b9…91752`), root
2,472,878,772 bytes (`e600aeb3…466c8`). Derived from attempt28; only compositor,
experiment assets and stage-one pairing change. Boot042/DT, installed boot021,
client57a9339, keyboard/login and one core retained. Never mix pairs. No CPU
register/module, SMP, storage, Wi-Fi, macOS, security/default/volume change.

M1 follows `tools/m1n1-client/attempt31-instructions.md`: privately receive both
images, verify offline and publish readiness, then wait for human start. One
crossover and 45s human test within the fixed 600s switch-to-return window; both
collector and independent service reset the drawing option to0. The custom
executable remains only in RAM until shutdown. Routine policy checks waived.
See `native/boot/attempt31/validation.md` and `kernel/experiments/desktop31/PLAN.md`.

Ownership: M5 owns this isolated compositor experiment and publication. M1
owns independent intake, the human-started boot and sanitized reporting.
Other agents' unreviewed jobs047/048 and kernel-config work remain untouched.
No concurrent native experiments or replay of consumed attempts. After the
candidate result, prioritize bounded secondary-core startup and the thermal/
capacity prerequisites for CPU policy; GPU remains a separate parity blocker.

### Current M1 native result — attempt30 consumed, 2026-10-20

**Attempt30 consumed: one native desktop-latency boot/root send/userspace
bundle delivery PASS**, final `LATENCY_OBSERVED`; no frequency/renderer changes
or CPU/memory module load. Execution `6e49687`. Two 20-callback controls:
small medians 256.940/256.346 ms, full 513.491/516.029 ms; compositor process near 97%
CPU, IPC medians 407.639/407.789 ms. Software main-thread samples mostly anonymous
executable, not yet attributed to LLVM/Mesa; lost 0, unmapped retained. All 40
callbacks including warm-ups and 414 IPC samples preserved. Human reports
prompt cue, accurate typing, delay remains; individual action times unlogged.
Clock estimate 2.651/2.650 GHz; no thermal/energy data. No kernel fault/M1 panic
observed. Macintosh HD return confirmed +223.531/600 s; owned processes ended.
No retry, settings, policy/default/volume, hardware, SMP, storage or Wi-Fi change;
routine checks waived. Restart is human-reported; measured M1 reader uptime
20,933 s does not independently establish freshness. Evidence and timing limits:
`native/boot/stage-b-2026-10-20-attempt30-result.md`; full sanitized samples:
`native/boot/attempt30/native-observation.json`.


### Historical M1 offline readiness — attempt30, 2026-10-20

M1 pulled **`cfebfb7`**, verified the 163,840-byte desktop30 bundle
(`26a36600…1f07`), all four regular members, asset manifest and byte-identical
collector source without extraction/execution. Retained attempt28 images freshly
rehashed with embedded pins PASS; boot042 thirteen files and all 37 source pins
PASS. Desktop-latency eight-line offline launcher and root sender dry-run PASS;
clean client `57a9339`, eleven helper pins, SSH config/operator key and fresh
no-forwarding config checks PASS. **127 methods PASS / 2 absent legacy-fixture
SKIPS**, no source/test repairs. Native/live/latency NOT RUN; launches/root/
bundle sends 0 and no real window armed. Human confirms M1 restart and proxy,
cable/power/unlocked/lid/recording/timer. One new authorized run follows this
published readiness; no earlier collector replay or module/settings operation.
Evidence: `native/boot/attempt30-m1-offline-2026-10-20.md`.


### Historical M5 handoff — attempt30 desktop latency, 2026-10-20

**Attempt30 offline preparation PASS; M1 intake pending; native/live NOT RUN.**
Reviewed M1 attempt29 (`1b1153d`): normal sampled memory attributes and actual
huge backing did not explain persistent desktop delay. Keep the working
attempt28 pair/boot042; transfer only the new **163,840-byte desktop30.tar**
(`26a36600…1f07`). Original Wayland controls, main-thread software CPU samples,
process CPU seconds and IPC observations precede one 45s human menu/typing test.
No frequency, renderer-policy, module, extra-core, storage or boot/settings change.

Three REA CPU-policy dossiers/443 instruction words cross-checked; two whole-
function decompilations rejected. Only bounded behavioral evidence informed
original Linux measurement code. Exact retained Omarchy userspace passed VM
client/sampler sanitizers, three phases, RAM-only receiver/native-identity and
retry refusals; **129 Python methods PASS**. Full-damage callback medians
132.142/129.039ms versus small-damage 18.249/20.781ms in the VM only. No native
speedup, efficiency or parity claim. Preliminary color-management A/B gave no
useful gain; that setting change was rejected. All known limitations and failed
harness iterations retained in `native/boot/attempt30/validation.md`.

M1 next: `tools/m1n1-client/attempt30-instructions.md`, offline intake and
published readiness, then one human-started filmed boot with fixed 600s root-
switch return window. Retain both existing images; do not replay earlier
collectors. Preserve Macintosh HD/default/Full Security and current Boot Lab;
routine policy checks remain waived. Other agents' jobs047/048 untouched.

Ownership: M5 prepares code/evidence and handoff; M1 independently verifies,
then controls the one human-started boot and records sanitized results. No
concurrent hardware experiments or reuse of consumed attempt29 allowance.

### Latest completed M1 native result — attempt29 consumed, 2026-10-20

**Attempt29 consumed: one native memory-observation boot/root send/bundle load PASS.**
Execution `41e34a6`; final `MEMORY_OBSERVED`, no frequency or global VM writes,
CPU28 module unloaded, one CPU. Sampled MMU/cache/stack attributes normal;
32/128 MiB huge-advice allocations report full huge backing. Global-random
base/huge medians 335.221/331.144 ns and 350.004/339.354 ns; page-local about 90–95 ns.
All 48 samples retained with backing/fault/switch/placement counters; no matched
macOS or desktop-causality claim. CPU estimate 2.651/2.649 GHz, no thermal/energy
telemetry. Human: accurate typing, massive application delay remains; zero menu
pollers before/after. No kernel fault or M1 panic observed. Macintosh HD return
confirmed at +321.424/600 s; owned processes ended. No retry, settings, policy,
volume, frequency/controller/global-VM, SMP, Wi-Fi or storage operation. Routine
policy checks waived; last reported Full/Permissive/default retained. Evidence:
`native/boot/stage-b-2026-10-20-attempt29-result.md`; full sanitized 48-sample data:
`native/boot/attempt29/native-observation.json`.

M5 next: review normal attributes, actual huge backing and locality separately;
no live repeat or global memory policy change. Keep software rendering, actual
boot-core/SMP and memory/DCS lifecycle as distinct offline investigations.
The source-pinned attempt29 checklist is retained unchanged for provenance;
this current result supersedes its NOT RUN heading and prevents replay.


### Historical M1 offline readiness — attempt29 memory isolation, 2026-10-20

M1 pulled handoff **`b828d42`** and verified the supplied **143,360-byte**
`memory29.tar`, SHA-256 **`561b6395…4f714`**: exactly four regular members,
all member/manifest hashes PASS, collector byte-identical to Git. Verified and
moved the bundle into ignored build/attempt29; retained attempt28 pair freshly
rehashed with embedded pins PASS. Boot042 13 files, all30 new source pins,
new memory-observe offline launcher/sender, client `57a9339`, eleven helper
pins and SSH/key/no-forwarding checks PASS. **106 M1 methods PASS / 2 absent
legacy-fixture SKIPS**, no fixes needed. **Native/live/module/collection NOT
RUN; launches=0, root/bundle sends=0; no real window armed.** Next: fresh M1
restart/cable/power/unlocked/recording procedure and explicit human start.
Routine policy checks waived; no boot/settings/volume or hardware change.
Evidence: `native/boot/attempt29-m1-offline-2026-10-20.md`.

One later native memory collection only: CPU28 module remains unloaded, bundle
received only into verified tmpfs, root journal-key gate before collection,
fixed600s switch-time deadline and human return timer. No memory-controller or
frequency operation is selected. Do not replay consumed attempts27/28. The
attempt29 checklist is itself source-pinned; readiness publication leaves it
and the complete source-pin set unchanged. No live work starts from this report.


### Historical M5 handoff — attempt29 memory isolation, 2026-10-20

Attempt28 (`ee44dca`) observed CPU0/sotra-m near 2.65 GHz with no frequency
writes; memory and desktop latency remain open. The next package preserves its
exact two-stage images and boot042. A 143,360-byte original diagnostic bundle
arrives into /run over verified SSH: architectural MMU/cache/stack-PTE reads,
pre/post clock estimates, unchanged chase28 and a locality/page-advice matrix.
No CPU-frequency or memory-controller writes, extra cores, storage or settings.

Five REA driver dossiers completed; 265 instruction words cross-checked with
LLVM/carrier bytes. Three pseudocode gates rejected; only bounded instruction/
call facts retained. macOS reference results depend strongly on QoS/placement;
there is no matched OS performance/efficiency ratio. Final module W=1,
sanitizer/optimized matrices, 315 controller, 13 helper and 12 bundle/decoder
methods PASS. Exact-kernel VM shipping-module refusal and separate VM-only
snapshot positive control PASS; that control never ships. Native NOT RUN.

M1 next: `tools/m1n1-client/attempt29-instructions.md`; pins and limits in
`native/boot/attempt29/`. Privately transfer only `memory29.tar`; retain both
attempt28 images. Offline intake then human start, fixed600s switch-time window
and Macintosh HD return. Original macOS/default/security/volumes unchanged;
routine policy checks waived. Other agents' jobs047/048 remain untouched.

### Current M1 native result — attempt 28, 2026-10-20

**Attempt 28 consumed: one launch/send, no-write CPU observation PASS.**
Execution `f5f11c1`; actual CPU0 MPIDR `0x40000`, part `0x068`, DT
`apple,sotra-m`. Module load once, writes=0/cap=0, policy0 userspace; raw command
`0x0000000000400106`, requested p-state 6, mapped 2.652 GHz. Dependent-ADD estimate
2.650/2.651 GHz before/after (assumption-based, not clock telemetry). Thermal,
energy and power data unavailable. **Human asks M5 to investigate memory as a
possible slowness factor:** 32/128 MiB chase medians 331.582/333.914 ns before,
331.790/337.458 ns after; distinct protocol from attempt 20, no matched macOS
comparison. Typing accurate; massive unusable app delay remains. Menu pollers
zero before/after; no kernel fault line or M1 panic. Macintosh HD return
confirmed at window +560 s, within the fixed 600 s; all run processes stopped.
No frequency/voltage write, retry, SMP, storage, Wi-Fi or settings change.
Fresh policy checks waived; last reported Full/Permissive retained. Evidence:
`native/boot/stage-b-2026-10-20-attempt28-result.md`.

M5 next: review the exact CPU/memory protocol and rendering latency together;
the user explicitly does not want memory overlooked. Obtain a matching macOS
measurement before a gap/parity claim, retain missing thermal telemetry as
unknown, and choose any later transition/cap separately. No new live attempt is
authorized by this passing observation; do not replay consumed attempt 28.


### Historical M1 offline readiness — attempt 28 CPU observation, 2026-10-20

M1 pulled published handoff **`7c757eb`** and independently verified both new
images: stage one **60,671,683 bytes / `65ea3815…08c39`**, root
**2,469,319,544 bytes / `59a7383e…fb2b78`**, embedded pairing and byte-identical
CPU asset manifest. Boot042's 13 files, all 15 source pins, cpu-observe offline
launcher/sender, clean `57a9339` client, helper/key/no-forwarding checks PASS.
**154 M1 test methods PASS, 2 old boot035/040 fixture SKIPS**; no production or
test source changes. Native attempt 28, live target-version checks, CPU module
load and measurements **NOT RUN; attempts=0, sends=0**. No real window armed.
Offline ready with documented limits; next is the fresh M1 restart/cable/power/
unlocked/recording procedure and explicit human start. Routine policy rechecks
remain waived; Macintosh HD/default/security and all volume settings unchanged.
No frequency/voltage writes, SMP, storage, Wi-Fi or setup action. Evidence:
`native/boot/attempt28-m1-offline-2026-10-20.md`.

The module's first native command-state read and policy initialization remain
unknown; the VM refused virtual hardware before loading it. Current package
readiness does not select a live frequency cap. One boot/send only, root-key
gate before observation SSH, fixed 600-second window from switch plus human
return timer; no attempt-27 replay. Private images/evidence remain in build.


### Published M5 handoff — attempt 28 CPU observation, 2026-10-20

User authorized the CPU experiment's offline preparation and push. M5 owns
job052 image/module/benchmark build, the dedicated `cpu-observe` launcher,
no-write collector, VM validation and M1 checklist. Build and offline driver/
controller tests pass; exact-pair VM boot validation PASS;
the first harness-only failure is retained in the validation record. Exact pins and
limits: `native/boot/attempt28/validation.md`. M1 follows
`tools/m1n1-client/attempt28-instructions.md` after publication and private
transfer of both images. Record independent offline readiness with native/live
NOT RUN; human start is required for the one boot/send. Do not replay attempt27.

Attempt 28 identifies the boot core and requested state and samples short
CPU/memory/desktop behavior. Module writes are explicitly disabled; unknown
OPP/no telemetry is evidence, not permission for a live frequency request.
SMP, N1 and read-only storage remain separate tracks; storage is no longer
attempt 28. CPU/independent Wi-Fi/persistent SSD/efficiency remain the goal.
Key verification gates observation SSH, and one fixed window starts at switch.
Original macOS/boot settings remain intact; routine policy checks stay waived.
No new subagents were started. Existing unreviewed jobs047/048 and kernel-config
work are untouched. Images, test overlays and raw diagnostics remain private.

### Historical M1 result — attempt 27 native two-stage switch and return, 2026-10-20

**Attempt 27 consumed: one native two-stage boot and one root send PASS.**
On execution handoff `f4b44f0`, stage one received the 2,435,460,021-byte root
at 28.1 MB/s in 86.8 s, verified it and unpacked it in 20.7 s; Omarchy, the
second USB link, SSH and automatic keyboard startup worked. One already-loaded
keyboard rerun PASS; human typed `omarchy` without extra letters, but application
opening still has a massive delay. Effective repeat delay 1000 ms; weather
runtime JSON PASS; final menu-poller check incomplete. No kernel fault line or
M1 panic observed. Human returned to Macintosh HD. Desktop observation exceeded
the ten-minute cap by roughly one minute; overall return was within twenty
minutes. Raw video/evidence private. Fresh policy checks omitted per user:
original Full/lab Permissive remain last reported, no settings/default/volume
change. Boot042, installed boot021 and client `57a9339` unchanged. No retry;
storage, DVFS/SMP and further setup NOT RUN. Details: `native/boot/stage-b-2026-10-20-attempt27-result.md`.

M5 review next: keep desktop latency open, retain the three known failed units,
stage-one unused-port sshd noise and teardown transaction warnings. Menu-cleanup
coverage is incomplete. Read the report's local key-parser/dependency mistake
and timing overrun before planning another run. No current live process or
hardware experiment remains owned by this M1 session; a new attempt needs a new
reviewed scope and human start.


### Historical preboot handoff — M1 intake PASS and restart done; routine policy rechecks omitted

2026-10-20: M5 reviewed M1's published `eff1716` report and the two test-only
fixes in `c52b079`. Both images and boot042 match; runtime transport/launcher
unchanged. The user confirms the M1 restart and explicitly declines additional
routine policy checks. Do not block or ask again for those checks; no fresh
verification is claimed. Last reported policies are original Full/lab Permissive.
Next: human selects the existing iLinux Boot Lab entry and waits at
`Running proxy...`; M1 pulls this update and follows the attempt-27 checklist.
Keep Macintosh HD as default and make no settings/volume/firmware changes.
Native attempt 27/live checks remain NOT RUN. This supersedes older preboot
policy-check and M1-restart prerequisites in the historical entries below.

### Historical M1 offline readiness — attempt 27 two-stage pair verified, 2026-10-20

* Pulled published handoff through **`4b63b82`** (includes `37fd9b5`). Both
  files supplied at the repository root match the published size/hash before
  being moved into ignored `build/attempt27/`; prior images preserved.
  Stage one **59,630,835 bytes / `84c01f53…06ed3`**, root **2,435,460,021 bytes /
  `5eaa2fdb…6d345`**. Pair verifier PASS, embedded kernel/root/count/16-KiB-size
  pin agrees with Git: 215,513 entries / 11,012,489,216 bytes.
* Retained boot042 archive and **13-file intake PASS**. Clean client remains
  pinned `57a9339`; installed boot021 and launcher **`b14ec7a1…e0740`** unchanged.
  Exact seven-line RAM-root offline launcher and sender dry-run PASS; neither
  USB nor an M5 SSH session opened. Upload 104,310,566 bytes/300s bound is an estimate.
* **215 test methods PASS, 2 SKIPPED** after two test-only fixes: controller 102,
  pair 8, sender 18, RAM-root 43/45 (legacy boot035/040 fixtures absent), USB-pipe 15,
  proxy 16 on bundled Python/OpenSSL, clock 13. Initial source-label assertion
  and known socket-close race preserved in logs; optional-space assertion and
  deterministic device-EOF wait fix only tests, not launcher/transport behavior.
* System Python 3.9/LibreSSL proxy TLS test fails even in a direct no-proxy
  handshake; unchanged proxy suite passes on bundled Python 3.12/OpenSSL 3.5.8.
  macOS unprivileged sshd cases report handshake-only coverage; ResourceWarnings
  retained. No runtime install, TLS-policy weakening or global setting change.
* Reader/USB-pipe binaries and source/proxy/clock digests equal attempt 26;
  derived public key matches authorized_keys. Offline SSH config checks PASS:
  root/m5s and omarchy/m5o have separate known_hosts, no stage-one forwarding,
  intended stage-two loopback relay. Existing host keys retained for now.
* Sanitized report: `native/boot/attempt27-m1-offline-2026-10-20.md`.
  Private receipts/logs/readiness record under `build/native-intake/attempt27/`.
  M1 checked hashes/embedded pin, not full image extraction or native behavior;
  M5's VM/content evidence is separate.
* **Offline ready with documented test limits. Native attempt 27/live checks/
  stage-two transfer NOT RUN; attempts=0.** Next: fresh M1 restart, cable re-seat,
  power/unlocked/open lid/recording, fresh read-only M5 original Full/lab
  Permissive/original-default confirmation, then human start. Keep M5 in macOS
  until then. No storage, DVFS/SMP or settings change; storage remains attempt 28.


### Active continuation — side-session completion before attempt 27

2026-10-19, baseline `75411ec` (remote main matches). Codex parent owns job045
image completion, job049 integration and shared status records; CPU subagent
owns `kernel/experiments/cpufreq-t6050/` and job051; SMP subagent owns
`reverse-engineering/findings/cpu-startup-2026-10-19/`. Shared build VM jobs run
serially under the vm lock. Preserve inherited working changes and old images.
The user approved commit/push of the reviewed handoff and separate offline
CPU/SMP work on 2026-10-20. No launcher allowances, hardware experiments or
settings changes are part of that approval.
Completion: job045 desktop/link VM run PASS, candidate root `5eaa2fdb…6d345`
preserved with a local candidate manifest under `build/resume-2026-10-19/root-candidate/`.
Job051 compile/sanitizer/Python/narrow-schema checks PASS; CPU native NOT RUN.
SMP handoff written. Both VM jobs stopped and released the lock. Detailed
results and unresolved services: `native/boot/subagent-review-2026-10-19.md`.
Job049 pairing and both new-pair VM runs are now PASS. Current stage one
`84c01f53…06ed3`, root `5eaa2fdb…6d345`; both records updated together. Exact
results: `native/boot/attempt27-two-stage-validation.md`; current M1 checklist:
`tools/m1n1-client/stage-b-instructions.md`. Two private transfer files are in
ignored `build/attempt27-transfer/`. All VM runs are stopped; no lock held.
Published on 2026-10-20: CPU/SMP `3483816`, attempt-27 handoff `37fd9b5`;
GitHub main matched after push. Next: M1 pulls the published
handoff, privately receives and verifies both images, and records offline
readiness. Then a fresh M1 restart, cable re-seat and unlocked/open-lid procedure,
fresh read-only M5 policy/default confirmation and the human's start. Keep the
M5 in macOS until readiness. Native attempt 27/live checks NOT RUN. No settings
change or hardware experiment. Storage stays 28; CPU/SMP work stays separate.


### Historical M1 result — attempt 26 (the M5's keyboard, on boot042): the keyboard switches on over SSH and types on the M5; every screen update costs the one CPU about half a second, which is the lag and, reproduced on demand, the repeated letters

* **One RAM attempt consumed, controller PASS** (exit 0 in 476.856 s, upload 473.4 s at 5.24 MB/s, handoff 2026-10-20T00:39:17.261Z =
  8:39:17 PM Eastern 2026-10-19; no M1 panic). No film of the run; the human sent a 33.6 s phone clip of the M5's screen (the slow
  response) and a photo of the early boot lines, both kept local. The M5 ran **63 min 34 s** until the human powered it off or restarted
  it (confirmed in chat); a macOS "Mac" device enumerated 31.5 s later.
* **Go/no-go PASS:** `Hardware DT PASS` for the MTP nodes; the MTP DART probed at kernel 0.070 s (v2.4, unlocked, initialized) with no
  freeze, reset or fault line.
* **M1 side:** enumerated +19.67 s, configuration 1 five ms later with no "transport restrictions" line; both interfaces, no driver
  bound; the reader (two runs, 205,394 bytes, 2,222 records) and 22 `usb-pipe` sessions (303 KB to the M5, 212 KB from it) over
  **63 min 14 s with no kernel fault line**; the host log's 730 device lines are read timeouts, the enumeration, Chrome's refused open
  and the final disconnect.
* **The keyboard (the headline):** `sudo ilinux-keyboard` steps 0 to 5 PASS in 1.4 s (kernel 114.09 to 115.47 s): RTKit wake (firmware
  `AppleMTPFirmwareMac-5340.61.4~502`), the DockChannel FIFO, `hid-apple`, the ring transport (2 MiB at iova `0x100ffc00000`), five
  interfaces, `/dev/input/event0` "Apple MTP keyboard", Hyprland sees it; step 6 with the human: 49 presses, Enter, `omarchy` as on a
  US layout. No trackpad device (no driver on `multi-touch`, `actuator`, `tp-accel`). A rerun of the script fails at step 4 (it reads
  only new kernel lines; nothing was unloaded).
* **Attempt-25 fixes verified:** `BROWSER` no-op, `archlinux-keyring-wkd-sync` masked (0 lines), no Chromium (0 lines; no Google CDN at the
  proxy), the unused ports' sshd quiet; clock step 25.0 days to 2.3 ms; web through the M1 (the proxy also carried the weather widget
  every 30 minutes).
* **Human-reported:** the keyboard works but everything is so slow it would be unusable: the Super+Space and Super+K menus take about
  2 s, Super+Return opens a terminal slowly, `omarchy` came out as "ooooooomarchy", `hello` repeated letters; Hyprland's tiling works. They
  ask whether CPU optimization should come before using an agent on the device, and asked that this be stated to the M5 agent.
* **Measured** (read-only kernel key timing and `/proc` for 20 presses; then two A/B runs the human approved, runtime-only and
  restored): every tap reached the kernel once (44 to 88 ms, no kernel repeat on any letter, read within 5.2 ms); the CPU then stays at
  91 to 100% for 0.8 to 6 s after almost every key (user 86 to 95%), Hyprland's main thread 19 s of 250 s, the terminal 0.11 s in its
  whole life; Hyprland has libLLVM and Mesa gallium mapped (software) and draws a full-screen wallpaper, a full-screen notification
  overlay, a bar and a dock; **a screen update costs about 0.47 s and the key release waits behind it, longer than the 250 ms repeat
  delay, so the terminal repeats about 14 times per tap: 134 to 152 characters for 10 taps (seven runs)**; **`repeat_delay` 1000 ms: exactly
  10 of 10 (two runs) and half the CPU per tap (0.53 s against 1.12 s)**; animations off: no change; stopping three leaked
  `omarchy-menu-select` pollers (7 to 12% idle CPU): frames about 9% faster; a 600×400 floating terminal: frame 0.2 s but about 0.55 s of
  CPU per tap.
* **Reading:** Confirmed: the MTP keyboard path works end to end; the keyboard is not the cause of the lag or the repeats; the repeated
  letters are reproduced and explained; animations are not the cost. Likely: software rendering at 3456×2160 on the boot CPU; the `cs`
  always-on guess (the human's photo; unchanged since attempt 19) matters for the GPU later. Hypothesis: the fixed per-frame cost is the
  full-screen layers or the present to `simpledrm`; the boot CPU is efficiency-class. Not established: `render:cm_enabled`, a solid
  background or removing the overlay; the trackpad; why the keybindings selector never finishes; sustained load; ports 2 and 3.
* **For the M5 (proposals, not authorization), in order:** (1) ship `input.repeat_delay` 800 to 1000 ms (verified); (2) fix the leaked
  `omarchy-menu-select` pollers; (3) cut the cost of a frame (the overlay and wallpaper layers, `render:cm_enabled`, window sizes, damage
  on the `simpledrm` path; animations are not it); (4) the structural work the human's question points at: SMP, the CPU's speed state, a
  display/GPU driver (agents over SSH work now but share the same slow CPU); (5) `ilinux-keyboard` rerun at step 4, the idle sshd restart
  on the cabled port, `ufw`; (6) revisit the `cs` always-on flag and the `kvm_arch_timer` line; (7) the measurement scripts are in
  `tools/m1n1-client/m5-probes/` (README, offline test `test_m5_probes.py`; small edits after the run, not re-run on the M5).
* Report: `native/boot/stage-b-2026-10-19-attempt26-result.md`. Fresh policy/default checks **NOT CHECKED**. The fixed E1 probe is
  still **NOT RUN**. Attempt 26 is consumed; no retry.

### Historical M1 readiness — attempt 26 (the M5's keyboard, switched on over SSH, on boot042) offline PASS (consumed: attempt 26 ran), 2026-10-19

* **Intake (M5 handoff `b8c877c`, release target `a1cc21a`).** Public prerelease `native-j716c-boot042`: archive 18,877,362 bytes,
  SHA-256 `a2e57c0c…a781`, checked against Git **before extraction** (GitHub's asset digest equal); 14 regular members, no unsafe
  path or special entry. The `verify-package` receipt (SHA256SUMS digest `60299703…3ccd`, 13 files, clean client pin `57a9339`) PASS.
* **Independent delta against the M1's own boot041 download:** byte-identical: both initramfs, `diag-init.c`, m1n1 and its
  records, the generic DT; different: `Image` (`0b6df395…b69c`), `kernel.config` and the Stage-B DT. **The M1's own property-level
  diff of the two Stage-B DTs** (361 to 371 nodes): ten new nodes (`/soc/mtp@294600000`, `/soc/mbox@294608000`,
  `/soc/fifo@294b14000`, its `input@8000` and six interface nodes) and two changed (`/soc/iommu@294800000`: `status` removed,
  `phandle` and `apple,dma-range` added; `/aliases`: `keyboard`); `/soc/nvme@45dcc0000` is still disabled and every USB node is
  unchanged. `kernel.config` differs by exactly the report's nine symbols, plus `HID_CP2112` and `HID_FT260` as "not set".
* **The image** (AirDropped; it arrived in the repository root and was moved into the ignored `build/ramroot045-boot042/`):
  2,435,320,732 bytes, SHA-256 `565644be…bf6f`, equal to the pin, and **read from the image itself**: no private key, credentials,
  history or Wi-Fi secret; passwords locked; the authorized key equal to the M1's; **exactly four kernel modules**
  (apple-rtkit-helper, apple-dockchannel, hid-apple, dockchannel-hid; vermagic equal to the kernel release; digests equal to the
  image's own list, which `ilinux-keyboard` checks) and **no storage module** (the only nvme-named files are Arch's userland
  libraries and an Omarchy script); eighteen lab files **byte-identical to Git**, including the new `ilinux-keyboard`, the modprobe
  blacklist, the `ssh-browser` and `wait-usb-host` helpers and the Chromium policy; `archlinux-keyring-wkd-sync` masked. The four
  modules' digests have no independent source in Git: they are the image's own.
* **`ilinux-keyboard` read in full** (222 lines, root over SSH): step 0 only checks (kernel, digests, the MTP nodes, the MTP DART
  bound, unlocked, no fault); steps 1 to 4 `modprobe` the four modules by name and check the kernel log after each, stopping at the
  first failure; step 5 reads the input devices; step 6 reads key presses (no grab) and prints counts only. It writes nothing but
  the module loads and never unloads anything.
* **Offline.** The launcher with `--profile omarchy --ramroot …` exits 0 with exactly the seven expected lines (`RAM root PASS:
  2,435,320,732 bytes`, upload estimate 2,480,000,463 bytes, 496.0 s at 5 MB/s, deadline 900 s); `launch.py` (`b14ec7a1…`) and the
  other controller files are unchanged. The reviewed 102 controller cases PASS; `test_ramroot` 45 (2 skipped), `test_connect_proxy`
  16, `test_m5_clock` 13; `test_boot042_package` 9, `test_boot042_rule` 10 and `test_mtp_input` 33 pass or skip without the M5's
  `build/`. **`test_usb_pipe` passed 14 of 15 on its first run and 15 of 15 on a rerun:** `test_device_end_closes_the_session` is
  timing-sensitive (3 of 25 isolated runs fail on the label "the device ended", because the test closes ssh's side at once and the
  end can read "ssh closed the session"); the sources and the test are unchanged since attempt 25, and both outcomes exit 0 with the
  same data. `usb-pipe`, the reader, the proxy, the clock tool and the SSH config are attempt 25's files and binaries.
* **New and untested on this hardware:** m1n1's handling of the MTP nodes (the launcher's `Hardware DT PASS`, go/no-go 1); the MTP
  DART's reset at boot (go/no-go 2: a freeze, a reset or a fault line for `294800000.iommu` is a no-go, recovered by power-cycling
  the M5); then, over SSH only, the MTP's RTKit wake, the DockChannel FIFO, hid-apple, the ring transport, the keyboard and typing on
  the M5. No storage anywhere.
* **What the run needs from the human:** a fresh M1 restart (**done**), the cable re-seated, and a **recording**, since the headline
  result is typing visible on the M5's screen (the checklist asks for 30 minutes; at least the keyboard steps), and the human's
  start; accept the macOS USB accessory prompt. Step 6 needs the human at the M5's own keyboard within 90 s once the M1 says go; the
  Claude sign-in is optional. **The m1n1 screen shows the Mac's serial-number line before the handoff: never transcribe or share it.**
* **NOT RUN:** native attempt 26 and every live check, and the fresh policy checks.

### Consumed M5 handoff — attempt 26: the M5's keyboard, switched on over SSH, on boot042 (ran 2026-10-19; see the M1 result above)

* **Attempt 25 consumed:** SSH, the clock step, web access through the M1 and a signed-in Claude Code worked on the M5
  over the USB link (see the M1 result below). The machine still has no input of its own.
* **Attempt 26 = boot042** (prerelease `native-j716c-boot042`, 18,877,362 bytes, SHA-256 `a2e57c0c…a781`, its
  `SHA256SUMS` `60299703…3ccd`) **with the launcher's `omarchy` profile** (unchanged, `b14ec7a1…`) **and the Omarchy root
  for boot042's Image** (VM job 045 with `LINK=1 CLAUDE=1 NOPASSWD=1`: attempt 25's root, its four fixes and the keyboard
  modules; 2,435,320,732 bytes, SHA-256 `565644bed5aa2d2c7ab594868447c74a33fd9317c6269c3c52570eef86d3bf6f`, pinned in
  `native/boot/omarchy-root-manifest.json`). boot042 is boot041 with three files changed (`Image`, `kernel.config`, the
  Stage-B DT): the MTP keyboard path and the storage drivers are modules, and the DT gains the MTP nodes and the MTP's DART.
* **One hardware change at boot:** the built-in DART driver probes the MTP's DART and resets it. Everything else waits for
  the SSH session: `sudo ilinux-keyboard` loads four modules one at a time, each with its own go/no-go, and the human types
  on the M5.
* **No storage in this attempt** (user decision, 2026-10-19; `decisions.md`): the launcher's guard refuses an enabled NVMe
  node, and the package keeps it disabled with no storage code in its Image. Read-only storage is attempt 27, behind a
  separate launcher change the user reviews before it is applied.
* **Offline:** the committed launcher passes boot042 with the image; 265 tests in 17 suites pass; the packager's boot042
  entry has a package test (9) and a mutation check (25 of 25).
* **The image travels privately:** the human AirDrops it to the M1 (`build/ramroot045-boot042/`, ignored). Never commit or
  publish it.
* **M1 next:** `tools/m1n1-client/stage-b-instructions.md` (attempt 26): the offline intake (package, delta, image, launcher
  run), then one filmed boot with the reader on the journal, the SSH session and the keyboard steps.

### Current M1 result — attempt 25 (Omarchy itself with the USB link and Claude Code, on boot041): the first data from the M1 to the M5 works; SSH, the clock step, web access through the M1 and a signed-in Claude Code on the M5 all ran

* **One RAM attempt consumed, controller PASS** (exit 0 in 476.492 s, upload 473.0 s at 5.24 MB/s, handoff 2026-10-19T04:52:29.303Z,
  12:52:29 AM Eastern; no M1 panic). No film of the run (the human's choice); a 6.6 s phone clip of both screens at +7.5 min arrived afterwards. The link ended at +958.2 s when the human
  powered the M5 off or restarted it (confirmed in chat); a macOS "Mac" device enumerated at +1005.7 s.
* **M1 side:** the gadget enumerated at +19.45 s (`1d6b:0104`, `bcdDevice 0x0039`) behind macOS's "transport restrictions" until the
  human accepted the accessory prompt (configuration 1 at +22.66 s). **Both interfaces were published and no driver bound**; the
  reader on interface 0 (642,026 bytes, 5,349 records, no gap) and `usb-pipe` on interface 1 ran at the same time. **No `BUSERR`,
  `translation fault`, `nobody cared`, oops or out-of-memory line in the journal.**
* **First M1-to-M5 data:** the **clock step PASSED** (24.2 days behind, then 1.3 ms ahead; round trip 5.7 ms); SSH as `omarchy` (host
  key equal to the journal's), `sudo -n` 0, `claude --version` 2.1.303, **HTTP 200 through the M1's proxy**; about **25 to 27 MB/s
  each way** (16.8 MB in 0.63 s and 0.66 s, one run each); the human's session ran 12 minutes (72.1 MB in, 1.9 MB out). **Claude Code
  was signed in by the human and answered a prompt on the M5**; the proxy saw 118 connections, all `ok`.
* **Seen in the journal:** the desktop up 27 to 31 s after the handoff; `claude` started from SSH launched **Chromium on the M5** with
  its sign-in page (which confused the sign-in); `archlinux-keyring-wkd-sync` fails and retries every 300 s (75% of the journal);
  the idle sshd on the unused ports restarts every 47 s; the VM's failed units.
* **Reading:** Confirmed: SSH, the clock step, web access and a signed-in Claude Code on the M5 over the USB pipe, both directions,
  with no kernel fault line in 15 min 39 s of link (two passing runs against two stalls). Likely: mise's lookups and Chromium's
  updater used the proxy at first run. Not established: the time to answer, how the sign-in was done, the M5's screen beyond a six-second clip, stability
  beyond 16 minutes, sustained throughput, more than one port.
* **For the M5 (proposals, not authorization):** stop `claude` from opening the M5's browser (or say the link is in the terminal);
  mask `archlinux-keyring-wkd-sync`; silence the idle sshd restarts; disable Chromium's component updater; and consider using the
  link (about 25 MB/s, against m1n1's 5.2 MB/s upload) for the root: your design.
* Report: `native/boot/stage-b-2026-10-19-attempt25-result.md`. Fresh policy/default checks **NOT CHECKED**. The fixed E1 probe is
  still **NOT RUN**. Attempt 25 is consumed; no retry.

### Historical M1 readiness — attempt 25 (Omarchy itself with the USB link and Claude Code, on boot041) offline PASS (consumed: attempt 25 ran), 2026-10-19

* **Intake (M5 handoff `38e91fb`, image work `33c37c8`).** The boot041 package is attempt 24's, unchanged: its archive checks against
  `archive-sha256.txt` (`shasum -a 256 -c` OK), the pinned package records and the six controller files are unchanged since attempt 24
  (empty `git diff`), launcher `b14ec7a1…`. **The AirDropped image** arrived untracked in the repository root and was moved into the
  ignored `build/ramroot045-link/` before any commit: 2,434,354,327 bytes, SHA-256 `b8eae454…66c1`, equal to
  `omarchy-root-manifest.json` by size and digest.
* **The image was read from itself, which the earlier Omarchy images could not be** (this Mac's own `tar` reads zstd): the listing
  (215,472 entries) and 28 small members read in a scratch directory that was deleted. **No** SSH host key, user key or `.ssh` file
  (`/root/.ssh` is an empty directory), no GPG or pacman keyring, no `.credentials.json` or `~/.claude.json`, no history file, no Wi-Fi
  secret; `~/.claude` holds only Omarchy's skill symlinks, the one keyring file is an empty default keyring, there is no git identity,
  and root and `omarchy` have locked passwords. `/etc/ssh/authorized_keys.d/omarchy` (0644, one key) is the key of
  `kernel/experiments/usb-gadget/authorized_keys` and the public half of the M1's `build/control/m1-control`. The lab's eleven files
  (`set-clock`, `usb-gadget.sh`, the sudoers rule, the host-key, sshd-tty and gadget units, both sshd drop-ins, `/etc/environment`,
  the udev rule, `/etc/default/ilinux-usb-gadget`) are **byte-identical to Git**. Sudo: Omarchy's permanent grant (`omarchy
  ALL=(ALL) NOPASSWD: ALL`, user-approved 2026-10-18) and the clock rule, plus Omarchy's stock narrow rules; sshd is key-only and runs
  in inetd mode on the pipe only, with no socket and no network function. Claude Code 2.1.303 (285,335,616 bytes) is installed,
  signed out. The M5 has no network interface for Omarchy's usual services (NetworkManager, avahi, cups, docker, ufw) to listen on.
* **Independent review of the M1's new tools, read in full.** `usb-pipe` (about 1,000 lines): a fixed-identity match field by field,
  only interface 1 opened with no capture or seize, no control request, stall clearing, reset or power change, and nothing written
  before sshd's banner. `connect-proxy.py`: loopback only, CONNECT and `http://`, ports 443 and 80, loopback, private and special
  destinations refused after resolving; **by design any program on the M5, including a signed-in agent with passwordless sudo, can
  reach any public host on 80 and 443 through the M1's network**. `m5-clock.py` and `set-clock`: one time line, 2025 to 2099, a fake
  `date` in the tests, so the M1's clock is never touched. `m5-ssh-config`'s `m5o` entry (`ssh -G` checked): `omarchy`, its own
  `known_hosts-omarchy`, the M1's key (`0600`, `IdentitiesOnly`), no agent forwarding, the reverse forward of `127.0.0.1:3128`.
  `usb-pipe` builds from the SDK alone into the ignored `build/control` (SHA-256 `94b33396…bffe`); its dry run with no gadget exits 2
  with nothing opened. **The reader** is the unchanged attempt 21 to 24 binary (`77677ee3…`); it accepts `bcdDevice 0x0039` and a
  two-interface configuration.
* **Offline.** The launcher with `--profile omarchy --ramroot …` exits 0 with exactly the seven expected lines (`RAM root PASS`, upload
  estimate 2,479,098,050 bytes, 495.8 s at 5 MB/s, deadline 900 s). The reviewed 102 controller cases PASS, `test_ramroot` 45 (2
  skipped), `test_usb_pipe` 15 (86 s: a real ssh through the tool to an unprivileged `sshd -i` on a pseudo-terminal, ending at the
  authenticated handshake as documented for macOS), `test_connect_proxy` 16, `test_m5_clock` 13, `test_control_channel` 16 (4
  skipped), `test_kconfig_guard` 7 (1 skipped); `test_usb_dt` and `test_boot041_package` skip without the M5's `build/`.
* **New and untested on this hardware:** the first data from the M1 to the M5 (bulk OUT, which SSH needs; the reader never wrote); two
  interfaces per port (a second IN and OUT endpoint); what macOS does with a two-interface vendor device (Unknown: both nubs
  published, no driver bound); the reader and `usb-pipe` open different interfaces of one device at once (Likely fine); the web relay;
  the human's Claude sign-in through it.
* **What the run needs from the human:** a fresh M1 restart (unlocked, lid open; about 8 minutes of upload plus the session, so 20
  minutes or more), the cable re-seated (the M5 booted into the Boot Lab again if the read-only gate sees nothing), a **30-minute**
  recording started before the launch, and the human's start; accept the macOS USB accessory prompt if it appears. After the handoff
  the M1 starts the reader (interface 0) and the proxy, sets the clock and opens the SSH session; **the human signs in to Claude in
  the M1's browser and pastes the code into the session, and the M1 records nothing about the link, the code or the account.** **The
  m1n1 screen shows the Mac's serial-number line before the handoff: never transcribe or share it.**
* **NOT RUN:** native attempt 25 and every live check, and the fresh policy checks.

### Consumed M5 handoff — attempt 25: Omarchy itself with the USB link and Claude Code, on boot041 (ran 2026-10-19; see the M1 result above)

* **Attempt 24 consumed:** with both DART instances per dwc3 core, the USB log streamed from the M5
  to the M1 for the full ten minutes with no fault. Data from the M1 to the M5 is still untested.
* **Attempt 25 = boot041's package** (unchanged, the same archive as attempt 24) **with the launcher's
  `omarchy` profile and the Omarchy root built with the link** (VM job 045 with `LINK=1 CLAUDE=1
  NOPASSWD=1`, committed at `33c37c8`): 2,434,354,327 bytes, SHA-256
  `b8eae454809839abcf6e3279e028576fa8e47b835f211968dd198a33a18c66c1`, pinned in
  `native/boot/omarchy-root-manifest.json` for boot040's Image, which boot041 shares byte for byte.
  The root carries two `gser` interfaces per port (the journal, and a byte pipe with sshd for the
  desktop user `omarchy`, key-only, the M1's key), the M1's web relay in the session environment, a
  clock helper, Claude Code installed signed out through Omarchy's own wrapper, and Omarchy's own
  passwordless-sudo grant for `omarchy` (user-approved 2026-10-18). Deviations 16-24 of job 045.
* **Offline:** the committed launcher (`b14ec7a1…`, unchanged) passes boot041 with this image
  (upload 2,479,098,050 bytes, about 8 minutes, deadline 900 s); `test_ramroot.py` (45),
  `test_m5_clock.py` (13), `test_usb_pipe.py` (15), `test_connect_proxy.py` (16) and the native/boot
  suites PASS. VM: SSH as `omarchy` over the pipe, the clock step, HTTPS through the relay,
  `claude --version` without a download, `sudo -n`, a keyless login refused.
* **The image travels privately:** the human AirDrops it to the M1 (`build/ramroot045-link/`,
  ignored). Never commit or publish it.
* **M1 next:** `tools/m1n1-client/stage-b-instructions.md` (attempt 25): build and review
  `usb-pipe`, the first M1 tool that writes to the M5; the offline launcher run; then one filmed boot
  with the reader on the journal, the relay, the clock step, the SSH session and the human's Claude
  sign-in in the M1's browser.

### Current M1 result — attempt 24 (boot041): both DART instances per dwc3 core remove the stall; the USB log streams for the full ten minutes

* **One RAM attempt consumed, controller PASS** (exit 0 in 11.197 s, handoff 2026-10-19T03:38:34.430Z, 11:38:34 PM Eastern; no M1
  panic). The panel was filmed in portrait for 600.8 s (to +594 s); the human powered the M5 off at +11 min 12 s.
* **M1 side (read-only):** enumerated at +3.87 s, configuration 1 selected at once, the reader opened the interface at +4.05 s and
  captured **218,079 bytes (2,580 intact records, kernel 0.065 to 604.261 s, heartbeats 000 to 119 with no gap)**; it stopped
  itself at its 600 s limit (exit 0) with the device still enumerated. Seven 5 s read timeouts, all its own. No endpoint-0 error
  on the iLinux device.
* **M5 (capture and video):** all six DART instances are v2.4; both instances of every port were reset and bound to one table
  (`both set up`; instance 0 now `en ffff`), and each shared fault line (IRQ 43, 44, 45) carries two handlers (screen). **Fault
  count 0 and `pend 0/0` on all 357 port heartbeat lines; no `BUSERR`, no `translation fault`, no `nobody cared`, no oops.** Port 1's
  queue read `q0` from 10 s on and the M5's byte counter matches the capture at all 117 later status lines (0 or 56 bytes, the
  heartbeat line before it): nothing lost. Linux: PID 1 at 3.27 s, the 50-domain ladder at 45.056 s, heartbeats every 5.048 s to
  119. The new risk (Linux programming instance 0 for the first time) did not freeze the SoC.
* **Reading:** the Image is byte-identical to boot040's and the gadget unchanged, so the six-node DT change removed the stall
  (**Confirmed as a comparison, one passing run**); the cause is **Likely** candidate A, the unprogrammed sibling instance.
  Hypothesis: attempt 18's ACM + ECM stop may share it.
* **Not established:** bulk OUT (the reader never writes), a console, ECM, NCM or SSH, throughput, stability beyond ten minutes or
  under load, more than one attached controller.
* **For the M5 (proposals, not authorization):** the Omarchy root with the SSH link, or a bulk-OUT test first (a read/write client
  is new M1 code, on request with the M5's brief); reconsider ECM or NCM on boot041's DT; keep `pend a/b` and `dart<N>`; write the
  `/proc/interrupts` table through `/dev/kmsg` so the capture has it too.
* Report: `native/boot/stage-b-2026-10-18-attempt24-result.md`. Fresh policy/default checks **NOT CHECKED**. The fixed E1 probe
  is still **NOT RUN**. Attempt 24 is consumed; no retry.

### Historical M1 readiness — attempt 24 / boot041 (both DART instances per dwc3 core) offline PASS (consumed: attempt 24 ran), 2026-10-19

* **Intake (M5 handoff `b5ef90d`, release target `88d392c`).** Public prerelease `native-j716c-boot041`: archive 18,926,067
  bytes, SHA-256 `ab49e307…4d28`, checked against Git **before extraction** (GitHub's asset digest equal); 14 regular members, no
  unsafe path. The `verify-package` receipt (SHA256SUMS digest `593c4492…80a1`, 13 files, clean client pin `57a9339`) PASS.
  `Image` `a53d1d47…` (44,681,728 bytes, equal to boot040's), `kernel.config`, `initramfs-stage-b` `27314880…`, `diag-init.c`
  `2e2e9923…` and the Stage-B DT `b053f248…` (61,995 bytes) match the checklist's table.
* **Independent review.** The checklist's own delta command, run against the M1's attempt-23 boot040 download, passes:
  *boot041 = boot040 + the two-DART DT delta + /init only* (Image, config, m1n1, the generic DT and initramfs, `toolchain.txt`
  byte-identical). **The M1's own property-level diff of the two Stage-B DTs** (361 entries each): exactly six nodes differ. The
  three DART instance-0 nodes (`/soc/iommu@2a2f00000`, `@2aaf00000`, `@382f00000`) lose `status = "disabled"` and
  `power-domains` and gain a phandle (`0x6b`, `0x6c`, `0x6d`); the three controllers (`/soc/usb@2a2280000`, `@2aa280000`,
  `@382280000`) change `iommus` from `<dartN 1>` to `<dart0 0>, <dartN 1>`; every other property is equal. The shipped
  `diag-init.c` equals `init.c` at HEAD; its new code reads only: `/sys/bus/platform/devices` for the DART phandles, and
  `/dev/mem` with `O_RDONLY`, `PROT_READ` and 32-bit loads (PARAMS3 and the pending word of each confirmed instance, now at each
  heartbeat); every write is as in boot040 (kmsg, configfs, mounts, `SIGKILL` of the streamer at the first bus error).
* **The one new hardware-facing change** is that Linux now probes, resets and programs DART instance 0 (reset at probe: TCR and
  TTBR zero on all 16 streams, all streams enabled, error, pending and protection state cleared, a TLB invalidate; later the
  TTBR/TCR of stream 0 and TLB flushes on every map and unmap). Instance 0 shares instance 1's clock gate and power, answered
  `/dev/mem` reads in attempt 23 and reported `prot 0` (unlocked); **untested on this chip**. The M5's stop rule: a freeze around
  the DART probe lines (about 2-3 s, before any UDC binds) points at instance 0's reset.
* **The reader** is attempt 21's binary (`77677ee3…`), unchanged: its 15 tests PASS and its dry run exits 2 with nothing matched.
* **Offline.** The launcher with the default `stage-b` profile exits 0 (`Package PASS`, `Mode: OFFLINE ONLY`). The reviewed 102
  controller cases PASS, `test_ramroot.py` 44 (1 skipped), `test_usb_dt` 12 (all skipped), `test_control_channel` 16 (4 skipped),
  `test_kconfig_guard` 7 (1 skipped), `test_boot041_package` 11 (all skipped: they need the M5's `build/` directories). The
  packaged authorized key equals the repository's.
* **What the run needs from the human:** a fresh M1 restart (kept unlocked), the cable re-seated (and the M5 booted into the Boot
  Lab again if the read-only gate sees nothing), a recording started before the launch (portrait with the left two thirds of the
  console framed worked in attempt 23; the first minute carries most of it), and the human's start; accept the macOS USB
  accessory prompt if it appears. The reader starts right after the handoff; stop 10 minutes after it, or earlier on a reset, a
  kernel panic or an M1 panic. **The m1n1 screen shows the Mac's serial-number line before the handoff: never transcribe or share it.**
* **NOT RUN:** native boot041 / attempt 24, and the fresh policy checks.

### Consumed M5 handoff — attempt 24 / boot041: boot040 with both DART instances per dwc3 core (ran 2026-10-18; see the M1 result above)

* **Attempt 23 consumed:** the USB DART is version 2.4; at the first bus error the fault was
  pending on instance 0, which the Stage-B DT left out, so Linux had never set it up and had no
  handler for it on the shared fault interrupt.
* **Attempt 24 = boot041**, with the launcher's default `stage-b` profile, the diagnostic
  initramfs and the M1's existing reader, as in attempts 21 and 23. The Stage-B DT gives each of
  the three dwc3 cores both instances (`<dart0 0>, <dart1 1>`, as Asahi's device trees do) and
  enables instance 0; `/init` adds both instances to the identity line, a setup line at bind and
  both instances' pending-fault state in the short line. The kernel Image, config and m1n1 are
  boot040's byte for byte (packager-enforced), so the Omarchy root pinned to that Image stays
  usable.
* **Release:** prerelease `native-j716c-boot041` at `88d392c`: archive 18,926,067 bytes, SHA-256
  `ab49e307239a600f0652ea180ee15aa2b153ddf3c28e910bf8b5f97317944d28` (GitHub's asset digest and a
  fresh download equal it); SHA256SUMS digest `593c4492…80a1`. The handoff records in
  `native/boot/` point at boot041.
* **Offline:** the committed launcher (`b14ec7a1…`, unchanged) passes the package; the
  boot040-to-boot041 delta check passes; VM job 041, generic-VM liveness, the dummy_hcd self-test
  (1,928 log lines over bulk IN) and all suites PASS on a clean copy of main.
* **What decides it:** `: both set up` at bind, then whether the bulk log keeps flowing with
  `pend 0/0` and no bus error for ten minutes. If it does, the next attempt is the Omarchy root
  with the SSH link on boot041's package.
* **M1 next:** `tools/m1n1-client/stage-b-instructions.md` (attempt 24): download and verify
  boot041, the delta check against attempt 23's boot040 download, the reader re-check, then one
  filmed boot with the reader started right after the handoff.

### Current M1 result — attempt 23 (boot040): the USB DART is version 2.4, instance 1's fault line finds nothing pending, and at the first bus error the sibling instance the DT omits holds the fault (candidate A)

* **One RAM attempt consumed, controller PASS** (exit 0 in 10.965 s, handoff 2026-10-19T02:17:46.781Z, 10:17:47 PM Eastern; no M1
  panic). The panel was filmed in portrait for 130 s (to +122 s); the human stopped filming because the screen repeated
  attempt 21's pattern and powered the M5 off at +3 min 36 s.
* **M1 side (read-only):** enumerated at +3.89 s, configuration 1 selected at once (no `transport restrictions` line this time),
  the reader opened the interface at +4.0 s and captured **25,911 bytes** (325 intact records, kernel 0.0645-0.0731 s), then
  nothing; 41 read timeouts, all its own; it stopped itself when the M5 was powered off (+215.7 s, exit 0). No endpoint-0 error
  on the iLinux device.
* **Video (short lines legible):** every DART instance line reads `p3 2a2a0204`: **version 2.4**, so part 2 (the v2.2 layout)
  was active. Port 1's DART fault interrupt is **Linux IRQ 43** (hwirq `0x58f`; DT instance `2a2f80000`, stream 1; the sibling
  `2a2f00000` is not in the DT and answered the `/dev/mem` reads). A fault-interrupt storm began at kernel **3.9288 s**; every
  reported interrupt (#1-#4, then #25000 to #100000) found **nothing pending** on instance 1 (`PENDING 0 MASK 0 PROT_STATUS 0
  CTRL 0 TLB_CMD 0x07000101`) until `irq 43: nobody cared` and `Disabling IRQ #43` at 5.8 s. **At the first bus error (8.64 s;
  `BUSERR@0`) the snapshot shows instance 0 with `pend 1` and a stream block `00000000@3ffff35800`, instance 1 with `pend 0`.**
  Linux stayed healthy (ladder of 50 domains at 45.0 s, heartbeats to at least 023).
* **Reading (Likely, not tested):** the controller's DMA also goes through the sibling DART instance, which Linux never
  programs (`en 0`); the fault is recorded there and raises the shared fault line, and the only handler reads instance 1: **candidate
  A** (Asahi's two-DART wiring), the M5's own decision-table row. The v2.2 layout's pending word and stream block read as the REA
  described, on instance 0.
* **For the M5 (proposals, not authorization):** try candidate A (both instances per dwc3 in the Stage-B DT; the variant is in
  `kernel/experiments/usb-gadget-dt/`), keep the reporting, short lines and snapshot, and show both instances' pending bitmaps
  in the short line; `BUSERR@` read 0, so the DART's address is the lead.
* Report: `native/boot/stage-b-2026-10-18-attempt23-result.md`. Fresh policy/default checks **NOT CHECKED**. The fixed E1 probe
  is still **NOT RUN**. Attempt 23 is consumed; no retry.

### Historical M1 readiness — attempt 23 / boot040 (the apple-dart fault made visible) offline PASS (consumed: attempt 23 ran), 2026-10-18

* **Intake (M5 handoff `c5ae860`, release target `d125b61`).** Public prerelease `native-j716c-boot040`: archive 18,921,232
  bytes, SHA-256 `1d7f5c8d…66cf`, checked against Git **before extraction** (GitHub's asset digest equal); 14 regular members,
  no unsafe path. The `verify-package` receipt (SHA256SUMS digest `4ee2f1f3…e4c9`, 13 files, clean client pin `57a9339`)
  PASS. `Image` `a53d1d47…` (44,681,728 bytes), `kernel.config`, both DTBs and the generic files match the checklist's table.
* **Independent review.** The Stage-B initramfs has 422 entries like boot039's and **only `/init` differs** (the M1's own
  newc parse); `/init` (857,112 bytes) is a static aarch64 `EXEC` ELF with no `PT_INTERP` or `PT_DYNAMIC`, names `gser` and
  `0x0139`, and none of `acm.`, `ecm.`, `eem.`, `ncm.`, `rndis.` nor the debugfs files whose reads write a select register.
  The shipped `diag-init.c` (`58c68268…`) equals `init.c` at HEAD. **The two apple-dart patches were read in full** (107 and
  256 lines). Part 1 reports and acknowledges an interrupt that arrives without the error flag, writing the same two
  registers the unpatched handler writes on a recognised fault. Part 2 is gated on the DART's own version (PARAMS3 ≥ 2.2) and a
  register window large enough for its blocks; it then writes the pending words, the protection status (all ones), the mask
  (0) and one flush-unlock TLB command, and disables the line itself after 256 acknowledged interrupts. Translation, bypass,
  TTBR and protection settings are untouched in both. **Every v2.2 behaviour comes from REA of the macOS driver and is
  untested on hardware** (the M5 says so). In `/init`, the new code reads the DART registers through `/dev/mem` with
  `O_RDONLY`, `PROT_READ` and 32-bit loads only, never a write, only for bases the kernel's own iommu link confirmed (plus
  the table's sibling instance); the bus-error handler kills the log streamer (no restart) and repeats the snapshot; the other
  writes are kmsg, configfs and mounts as in boot039. **Residual risk (the M5's own note):** a read of an unclocked sibling
  register could stall the bus; the line before the read names it.
* **The reader** is attempt 21's binary (`77677ee3…`), unchanged: its 15 tests PASS and its dry run exits 2 with nothing matched.
* **Offline.** The launcher with the default `stage-b` profile exits 0 (`Package PASS`, `Mode: OFFLINE ONLY`). The reviewed 102
  controller cases PASS (37 + 10 + 6 + 16 + 5 + 19 + 2 + 6 + 1), `test_ramroot.py` 44 (1 skipped), `test_usb_dt` 6 (all
  skipped), `test_control_channel` 13 (3 skipped), `test_kconfig_guard` 7 (1 skipped), `test_boot040_package` 10 (all skipped:
  they need the M5's `build/` directories). `test_dart_diag.py` needs the patched Asahi tree, which the M1 does not have, and
  was not run. The packaged authorized key equals the repository's `authorized_keys`.
* **What the run needs from the human:** a fresh M1 restart (kept unlocked), the cable re-seated (and the M5 booted into the
  Boot Lab again if the read-only gate sees nothing), a recording started before the launch (4K if possible, or 1080p framed
  so that the left two thirds of the console are as large as possible, because the evidence is in short lines), and the
  human's start. **A macOS USB accessory prompt appears within seconds of the enumeration: accept it.** The reader starts
  right after the handoff; stop 10 minutes after it, or earlier on a reset, a kernel panic or an M1 panic.
* **NOT RUN:** native boot040 / attempt 23, and the fresh policy checks.

### Consumed M5 handoff — attempt 23 / boot040: attempt 21's bulk-only log port with the DART fault made visible (ran 2026-10-18; see the M1 result above; superseded by attempt 24)

* **Attempt 22 consumed:** the installer-built Omarchy desktop came up on boot035 and stayed up
  for the filmed ten minutes, view-only. Agents on the machine need the USB link next.
* **Attempt 23 = boot040** with the launcher's default `stage-b` profile and the diagnostic
  initramfs, read by the M1's existing reader, exactly as attempt 21 apart from three files: the
  Image (the apple-dart fault-report patches: part 1 reports an unrecognised fault interrupt
  with its raw registers and names each DART at probe; part 2 reports and acknowledges a DART of
  version 2.2 or later in that version's fault layout, which Linux did not read, per the REA of
  this Mac's DART driver; bounded, inert below 2.2; translation and protection unchanged),
  `diag-init.c` and the Stage-B initramfs (the failing DMA address at a bus error, the DART and
  fault IRQ per port, a read-only register snapshot, short per-port lines, the streamer stopped
  at the first bus error). The DT, config, m1n1 and gadget are boot039's (packager-enforced).
* **Release:** prerelease `native-j716c-boot040` at `d125b61`: archive 18,921,232 bytes,
  SHA-256 `1d7f5c8de17608b21eb9d047d4ee8470c785e3d2ba252fc7b156b4aee46166cf` (GitHub's asset
  digest and a fresh download equal it); SHA256SUMS digest `4ee2f1f3…e4c9`. The handoff records
  in `native/boot/` point at boot040.
* **Offline:** the committed launcher (`b14ec7a1…`, unchanged) passes the package; VM job 041,
  generic-VM liveness, the dummy_hcd self-test (1,929 log lines over bulk IN) and the package,
  control-channel, kconfig, USB, MTP and native/boot suites PASS on a clean copy of main.
* **The first question is on the screen at about 2-3 s:** the DART version on the probe lines.
  Version 2.2 or later means Linux was blind to this DART's faults and part 2 is active.
* **M1 next:** `tools/m1n1-client/stage-b-instructions.md` (attempt 23): download and verify
  boot040, re-check the reader, then one filmed boot with the reader started right after the
  handoff; expect macOS's prompt to allow the USB accessory and accept it.

### Current M1 result — attempt 22 (Omarchy itself, job 045, `--profile omarchy`): the first installer-built Omarchy desktop on the M5, up about 39 s after the handoff and stable for the filmed 10 minutes

* **One RAM attempt consumed, controller PASS** (exit 0 in 460.186 s, handoff 2026-10-18T22:26:29.937Z; the 2,382,558,042-byte
  upload took 456.5 s, 5.22 MB/s; every gate PASS including the 3 GiB heap allocation; no M1 panic). The recording started
  before the launch; the clip (1084.0 s, 1080p, 2.16 GB) holds the whole upload, the handoff and the desktop to +628 s.
* **As intended (video):** the same five early error-level kernel lines as attempts 19 and 20; systemd's `[ OK ]` console at
  +17.5 to +26.5 s (no `[FAILED]` in the frames read); black seconds; then **Omarchy's own session at +39.5 s**: the default
  wallpaper (a rocket launch), the thin top bar with a wrong-time clock (`Thursday 23:46`) and the two notifications, `Setup
  Wi-Fi` and `Learn Keybindings`. The VM needed 194.8 s under TCG (a ratio of about 4.9).
* **Stable:** the panel stayed lit and the desktop stayed up to the end of the clip (+628 s): a one-second brightness trace
  of 590 samples stays within 77-106 (106 only on the first frame), so no blackout and no Hyprland or SDDM restart; the clock
  advanced `23:46` → `23:56` (the human also notes that the clock kept increasing while its time and day were wrong).
* **Memory placement:** m1n1's heap limit reads `0x10010150000 (128 MiB)` (three clean OCR reads), so the 2.39 GB went in
  between about DRAM + 0.25 and + 2.5 GiB, overlapping the span (DRAM + 0.56 to 1.79 GiB) where the macOS boot's carveout map
  lists regions, with no reset: consistent with those regions not being live in this boot (Likely, not proven). m1n1's `FDT:`
  memory lines were not legible (they scroll past on the screen that also prints the Mac's serial number, which was never opened
  by eye). The kernel unpacked the 2.34 GB into 8.56 GB of tmpfs and reached systemd within about 17 s (the checklist guessed 30 s).
* **No USB, by design:** the host log shows m1n1's device destroyed at +0.23 s and no event for 13 minutes; the M5 shut down at
  +13.3 min and came back as a `Mac` device (the human's return to Macintosh HD, reported).
* **Not established:** performance, power, GPU acceleration, input (no driver), the first run's later steps, anything beyond
  +628 s, and the image's content (not inspected on the M1: no zstd tool).
* **For the M5 (proposals, not authorization):** the combined boot of this root on the USB kernel with the SSH-over-bulk link,
  once boot040 fixes attempt 21's DMA fault (expect systemd within about 20 s and the desktop about 40 s after the handoff); if
  the `FDT:` memory lines are wanted, the human can read `DRAM at`, `Usable memory` and `initrd at` from video 453-455 s, never
  the serial-number line; a larger console font or a 4K recording would help the early console text.
* Report: `native/boot/stage-b-2026-10-18-attempt22-result.md`. Fresh policy/default checks **NOT CHECKED**. The fixed E1 probe is
  still **NOT RUN**. Attempt 22 is consumed; no retry.

### Historical M1 readiness — attempt 22 (Omarchy itself, VM job 045, `--profile omarchy`) offline PASS (consumed: attempt 22 ran), 2026-10-18

* **Intake (M5 handoff `7eb2aad`, root rebuild `b520330`).** The boot035 package, re-verified and not re-downloaded: archive
  16,723,179 bytes, SHA-256 `81cbbd1c…`, checked against the Git pin; the `verify-package` receipt (SHA256SUMS digest
  `7635c5e4…`, 13 files, clean client pin `57a9339`) PASS. **The image:** the human AirDropped it; it arrived untracked in the
  repository root and was moved into the ignored `build/ramroot045/`. Its size, 2,337,897,871 bytes, and SHA-256 `d00ba156…578a`
  equal `native/boot/omarchy-root-manifest.json`. Its zstd frame header was read (magic OK, window 128 MiB, declared content
  size 8,561,316,352 bytes, the 8.56 GB of tmpfs the checklist names; the manifest's 8,525,249,287 is file content without cpio
  headers). **Its content was not decompressed or inspected on the M1** (no zstd tool, nothing installed); the build script
  `virtualization/jobs/045-omarchy-installer-root/ramroot.sh` (93 lines) was read in full instead: a snapshot of the installed
  root, job 039's `/init`, zram-generator masked, Omarchy's Stay Awake toggle and the frame-callback toggle (deviation 15), and
  nothing that touches a network, a device or storage. The report says the image holds no SSH host key, keyring or password,
  but does hold the build's machine-id; it stays local.
* **Launcher review.** `launch.py` is `b14ec7a1…` (new: the `omarchy` profile). The diff against the reviewed `4d55f0c9…` (39
  lines, `git diff 4d53cff`) was read in full: a third `Profile` with a `heap` field (`None` for `stage-b` and `ramroot`, 3 GiB
  for `omarchy`), a 900 s deadline, the confirmation `BOOT-J716C-OMARCHY-ROOT`, `verify_ramroot` taking its record file, the heap
  passed to `ProxyUtils` (the pinned client takes `heap_size`, default 1 GiB, with `heap_top = heap_base + heap_size` and m1n1's
  own limit set to `heap_base`, so the size is the client's bookkeeping), and parser and message changes. The gates, the DT
  checks and the handoff are untouched. The other five controller digests equal the checklist; client pin `57a9339`.
* **Offline.** The launcher with `--profile omarchy` exits 0 with exactly the seven expected lines (`RAM root PASS`, upload
  estimate 2,382,558,042 bytes: 476.5 s at 5 MB/s, 595.6 s at 4 MB/s, deadline 900 s). The suites PASS: launcher 37, ramroot 44
  (1 skipped), gpio 10, entry 6, DAPF 16, framebuffer 5, hardware 19, DAPF ADT 2, launcher ADT 6, protocol 1 (the reviewed 102
  plus the 44). The M1 has 16 GiB of RAM (about 6.8 GiB free and inactive now); the launcher holds the image in RAM (2.41 GB
  peak on the M5's offline run).
* **What the run needs from the human:** a fresh M1 restart, kept unlocked with its lid open and awake for the whole upload
  (about 7.5 minutes, 6-10 plausible) plus 10 minutes; the cable re-seated, and if the read-only gate still sees nothing, the M5
  booted into the Boot Lab again (as in attempt 21); the recording started before the launch (about 20 minutes, at least 25
  minutes of storage, phone charging); then the human's explicit start. The m1n1 heap and memory lines are copied from the video;
  **the `FDT: reporting device serial number` line is never transcribed or shared.**
* **Risks, read from the checklist and not tested:** where the 2.39 GB lands in the M5's RAM relative to live carveouts is
  Unknown (a reset during the upload would be the evidence); the upload is CPU-bound in Python on the M1; the kernel unpacks
  2.34 GB on one CPU, so the panel may stay black for tens of seconds and must not be stopped early.
* **NOT RUN:** the native attempt and every native check. No retry.

### Consumed M5 handoff — attempt 22: Omarchy itself (VM job 045) as a RAM root on boot035 (ran 2026-10-18; see the M1 result above)

* **Attempt 21 consumed:** the bulk-only port kept EP0 healthy and the M1's reader streamed
  36,909 bytes, then the M5's dwc3 flagged a DMA bus error and the stream stopped. boot040
  investigates that in its own track. **This attempt has no USB link**: the boot035 package's DT
  has no USB controllers.
* **Attempt 22 = the boot035 package launched with the launcher's new `omarchy` profile and the
  root Omarchy's own installer built** (VM job 045, 2,337,897,871 bytes, SHA-256
  `d00ba1563312e69ce366b316dab245ea76226c4f0399a6e32d36932aaa63578a`, pinned in
  `native/boot/omarchy-root-manifest.json`): 865 packages, Omarchy's session (SDDM → uwsm →
  Hyprland 0.56.2 → Quickshell), its first run and menu, Chromium and Obsidian, 20 agent
  launchers installed and signed out, with deviation 15 (`QT_WAYLAND_FRAME_CALLBACK_TIMEOUT=0`)
  from VM job 048. View-only, offline. Report:
  `omarchy-arm64/omarchy-root-report-2026-10-17.md`.
* **The launcher changed** (first time since attempt 18): a third profile, `omarchy`, with a
  3 GiB proxy-client heap (the 1 GiB default refuses this image), a 900 s deadline, its own
  confirmation `BOOT-J716C-OMARCHY-ROOT` and its own pin. `launch.py` is now `b14ec7a1…`; the
  `stage-b` and `ramroot` profiles behave exactly as before (`test_ramroot.py`, 44 cases), and
  the other five controller files are unchanged. The handoff records point at boot035 again
  (archive `81cbbd1c…`, SHA256SUMS `7635c5e4…`).
* **Offline:** against `build/native-boot035/verified` and the job 045 image the launcher prints
  `Package PASS`, `RAM root PASS`, upload 2,382,558,042 bytes (476.5 s at 5 MB/s, deadline
  900 s); the `native/boot` suites PASS. VM (QEMU TCG, one vCPU, the boot035 Image): desktop
  ready 194.8 s after kernel start, 0 Hyprland restarts, Chromium's window in 17 s.
* **The image travels privately:** the human AirDrops it to the M1 (`build/ramroot045/`,
  ignored; keep run 33's file in `build/ramroot/`). Never commit or publish it (machine-id).
* **M1 next:** `tools/m1n1-client/stage-b-instructions.md` (attempt 22): offline intake, the
  launcher diff review, then one filmed boot of about 20 minutes (about 7.5 min of upload, then
  10 min), the recording started before the launch; copy m1n1's heap and memory lines from the
  video, never the serial-number line.

### Current M1 result — attempt 21 (boot039): macOS publishes the bulk interface, the reader streams 36,909 bytes, then the M5's dwc3 flags BUSERR and an apple-dart interrupt storm stalls the stream

* **One RAM attempt consumed, controller PASS** (exit 0 in 10.95 s, handoff 2026-10-18T19:23:32.987Z, upload 8.89 s; no M1
  panic). The recording started before the launch; the clip (601.0 s, 1080p) runs to kernel ≈ 591 s. The reader and a
  read-only capture script were started by a watcher the moment the controller printed the handoff line.
* **M1 side (read-only):** the gadget enumerated at +3.88 s, `AppleUSBHostCompositeDevice` selected configuration 1 at +8.05 s
  (the human accepted a macOS permission prompt early in the run), the vendor interface was published with **no driver bound**,
  and **the reader opened it** (interface only, IN pipe only, no entitlement) at +8.1 s. **36,909 bytes** of the M5's kernel log
  arrived (476 intact records, kernel 0.064-0.076 s), then nothing for 10 minutes: 119 of the reader's 5 s reads timed out, never
  a STALL. **Host log: zero EP0 timeouts, zero transaction errors** (attempt 18: four and one). The device went away at +614.8 s,
  3 s after the reader finished, when the human rebooted the M5 at the ten-minute mark.
* **M5 screen (video; small text, digits good to about one):** the first dwc3 debugfs reads ran without a fault. Each port:
  `core 0x33313130, 32 endpoints (16 IN), MDWIDTH 128; TX FIFO words 0:35 1:199 … 15:199; RX FIFO words 1000` (**the FIFOs are
  sane**). From heartbeat 001 (kernel 8.49 s) to the last visible heartbeat (116 at 587.3 s) port 1 reads `configured … dwc3 On …
  ev0 BUSERR irq146 … 1out bulk h17 d0 1in bulk h17 d105` with `q8192`, only `f` changing; ports 2 and 3 `not attached`. At 9.956 s:
  `irq 43: nobody cared`, `handlers: apple_dart_irq`, `Disabling IRQ #43` (the digit is the weakest reading; 43 is the first of the
  three `apple-dart fault handler` IRQs 43/44/45 listed at 3.3 s). Linux itself stayed healthy: ladder complete (50 domains) at
  ≈ 45.0 s, the 60 s milestone, heartbeats 000-116, no reset. The attempt-17 and 18 videos show no such trace.
* **Reading:** with no interrupt endpoint, attempt 18's EP0 wedge does **not** recur, so it needed something only ACM/ECM had; the
  bulk path fails for a different reason: a DMA bus error on port 1's dwc3 and an unhandled apple-dart interrupt (Likely: the DART
  mapping, window or stream; Hypothesis: the Linux DART handler does not recognise t6050's error status). Not established: which
  DART, the faulting address, bulk OUT, a stream that survives.
* **For the M5 (proposals, not authorization):** confirm the IRQ number and which DART serves each dwc3 core; print GBUSERRADDR and
  the DART's error status once at the first fault; compare the USB DART setup with macOS using REA (behaviours only); put the key
  fields on a short line (the 432-column `[ctl]` line is about 3 px per character on film); stop the streamer at the first `BUSERR`.
* **Procedure:** after the fresh M1 restart the gate saw no device through two re-seats until the human booted the M5 into the Boot
  Lab again; a macOS permission prompt appears within seconds of the enumeration (the human accepted it).
* Report: `native/boot/stage-b-2026-10-18-attempt21-result.md`. Fresh policy/default checks **NOT CHECKED**. The fixed E1 probe is
  still **NOT RUN**. Attempt 21 is consumed; no retry.

### Historical M1 readiness — attempt 21 / boot039 offline PASS; the bulk-log reader built and tested (consumed: attempt 21 ran), 2026-10-18

* **Intake (M5 handoff `7905adb`, package tag on `713989c`).** Public prerelease `native-j716c-boot039`: archive 18,915,359
  bytes, SHA-256 `b85c8d45…7d51`, checked against Git **before extraction** (GitHub's asset digest equal, release target
  `713989c`); 14 regular members. The `verify-package` receipt (manifest digest `88346489…4df5`, 13 files) and the committed
  launcher's offline verification PASS. The 102 reviewed cases PASS (37 + 10 + 6 + 16 + 5 + 19 + 2 + 6 + 1); the USB suites
  `test_usb_dt` (6, all skipped), `test_control_channel` (10, 2 skipped), `test_kconfig_guard` (7, 1 skipped),
  `test_boot039_package` (8, all skipped: they need the M5's build directories) and `test_ramroot` (30) PASS. Launcher
  `4d55f0c9…` and the other five controller digests unchanged; client pin clean `57a9339`; the packaged key equals the M1's.
* **Independent review.** Image, `kernel.config`, both DTBs (Stage-B `a676087b…`), `m1n1.bin`, the generic initramfs and
  `toolchain.txt` are byte-identical to the boot036 package. The Stage-B initramfs differs only in `/init` (423 entries
  each), whose `authorized_keys` is the M1's key and which carries no self-test overlay. `/init` (sha `c012ed68…`) is a static
  aarch64 ELF; its strings name `functions/gser.GS0` and `0x0139` and none of `acm.`, `ecm.`, `eem.`, `ncm.`, `rndis.`,
  `obex.`, `subset.`, nor the debugfs files whose reads write a select register (`*_fifo_size`, `*_queue`, `lsp_dump`,
  `GDBGEPINFO`). The shipped `diag-init.c` (`8ba20c93…`) equals `init.c` at the tag commit and at HEAD. The whole
  `init.c` diff was read: one function (`gser`), a raw-tty streamer with shared counters, debugfs mounted, and the dwc3 state
  read per heartbeat in a forked child (regdump, `link_state`, endpoint `transfer_type` and `trb_ring`) with a 2 s wait, so
  a stuck read costs a status line and never the heartbeat. **Residual hardware risk (the M5's own note, confirmed by
  reading):** those register reads have never been done on this hardware; the first is at heartbeat 000 (≈ 3.5 s), before
  any USB traffic, so a fault would show at once.
* **The reader (built here, from the brief, with only what this Mac has: Command Line Tools, no install).**
  `tools/m1n1-client/bulk-log-reader.m` (Objective-C, IOUSBHost): fixed identity `1d6b:0104`, interface 0, configuration 1,
  class `0xff`, `bcdDevice` from a fixed two-entry table (`0x0139` boot039, `0x0039` RAM root) and the product string
  `iLinux J716c control channel, port N`; it opens the **interface only**, with no options, checks the cached descriptors
  (exactly one bulk IN, one bulk OUT, no interrupt endpoint), copies **only the IN pipe** and reads it into an `O_EXCL`
  capture with a sidecar, never writes to the device, and follows the brief's fail-safe table. Built with
  `clang -fobjc-arc -O2 -Wall -Wextra` with no warnings. **Deviation from the brief:** the SDK's pipe class has no
  `destroy`, so the pipe is released and only the interface is destroyed.
  * `test_bulk_log_reader.py` (15 tests PASS): ten static checks (forbidden calls and constants, the fixed identity, only the
    five documented options, `O_EXCL` files, refusals before any IOKit call, the IN address checked before the pipe is
    copied); four refusal tests on the binary; and `test_bulk_log_reader_loop.m`, which runs the shipped `read_loop()` against
    a fake pipe (11 scenarios: bytes kept on timeouts, stall, device gone with and without data, three errors, the 64 MiB cap,
    a write error, service termination, a signal, the `--seconds` limit). The static check was mutation-tested: 10 of 10
    forbidden-call mutants are caught.
  * Offline runs of the binary: `--dry-run` with no iLinux device exits 2 after `--wait` and writes only the sidecar (its
    diagnostic says no `1d6b:0104` device is in the USB plane); SIGINT and SIGTERM during the wait exit cleanly and remove the
    lock; a second instance and an existing `--out` are refused before any IOKit call. **Not done offline:** `--dry-run` with
    m1n1's device attached (it needs the M5 at the proxy; done at pre-flight) and any real read (the first is the attempt).
* **Tools (ignored, M1 local):** `run-attempt21.py` (the attempt-18 wrapper, only names changed), `capture-attempt21.sh`
  (read-only registry dumps at ≈ +5 s and ≈ +60 s) and the pre-flight and USB gate from earlier attempts.
* **State.** Attempt 21: live **NOT RUN**. Needs the human's fresh M1 restart (kept unlocked), cable re-seat, a recording started
  before the launch (whole screen, the bottom status lines legible), the M5 at Running proxy, then the go. The fixed E1 probe is
  still NOT RUN.

### Consumed M5 handoff — attempt 21 / boot039: a bulk-only USB log port with the dwc3 state on screen (ran 2026-10-18; see the M1 result above)

* **Attempt 20 consumed:** the run-33 RAM root ran ten stable minutes with its
  benchmarks on screen (the M1 result below). Attempt 21 goes back to the USB link
  with the diagnostic Stage-B initramfs (the launcher's default `stage-b` profile)
  and asks attempt 18's question with one variable.
* **boot039 = boot036 with only `/init` changed**
  (`native/boot/boot039-bulk-log-2026-10-16.md`):
  * one `gser` function per controller (vendor class `0xff`, bulk IN + bulk OUT, **no
    interrupt endpoint**, no class requests), which carries the kernel log, written
    only by the M5 on a raw port;
  * `bcdDevice 0x0139` (configfs accepts only BCD);
  * no network function (dropbear on loopback only);
  * debugfs is mounted, and every `[ctl]` line carries each dwc3 core's link, SOF
    frame, pending events, interrupt count, EP0 OUT/IN commands and endpoint TRB
    rings, plus a one-time line per core with its TX FIFO sizes (for the FIFO
    alternative).
* **Release `native-j716c-boot039`** (prerelease, public, tag on `713989c`): archive
  18,915,359 bytes, SHA-256 `b85c8d45552f21de475e46009599a06b3d723b44e66cbc0087ff5fdf00b57d51`,
  equal to GitHub's asset digest and to a fresh download; SHA256SUMS digest
  `883464897e2e…4df5`. Image `e0e53113…` and Stage-B DT `a676087b…` are boot036's;
  the initramfs `19e5e366…` differs from boot036's in `/init` only. The handoff
  records in `native/boot/` now point at boot039.
* **Offline:**
  * VM job 041 PASS: kernel facts checked against the exact tree, and the status line
    on fixture trees, plain and under ASan+UBSan;
  * generic-VM liveness and the dummy_hcd self-test PASS (one vendor interface, two
    bulk endpoints, no interrupt endpoint; 1,926 kernel-log lines over bulk IN; no
    echo);
  * packager tests (8) and all `native/boot` suites PASS;
  * the committed launcher `4d55f0c9…` verifies boot039 (`Package PASS`); the six
    controller digests are unchanged.
* **M1 next:** `tools/m1n1-client/stage-b-instructions.md` (attempt 21):
  * offline intake;
  * build and offline-test the read-only bulk-log reader
    (`tools/m1n1-client/bulk-log-reader-brief.md`; IOUSBHost, the interface and its
    bulk-IN pipe only, never a write) with only what macOS provides, installing
    nothing;
  * then one filmed boot: M1 freshly restarted, cable re-seated, recording started
    before the launch, the reader started right after the handoff, the host USB log
    captured as in attempt 18. Stop at 10 minutes from the handoff or on a reset or
    panic. The checklist's table says what each outcome means.

### Current M1 result — attempt 20 (boot035 RAM root, run 33): a stable ten-minute desktop with on-screen benchmarks

* **One RAM attempt consumed, controller PASS** (exit 0 in 44.553 s, handoff 2026-10-17T01:50:36Z; the 227,080,994-byte
  upload took 42.38 s, 5.36 MB/s; no M1 panic). The recording started before the launch, so the clip holds the proxy
  screen, the upload and the handoff, and runs to kernel ≈ 601 s.
* **As intended:** the status screen appears about 7 s after the handoff flash; `desktop ready 8.50 s after kernel start`;
  `Hyprland 0.56.2 under start-hyprland (its watchdog)`; **no red notice** in any sampled frame. The counter reads
  `0:09:59` at the end; the waybar clock ran `Thursday 23:46` → `23:56` at real-time rate; memory in use stayed at
  1.83-1.88 GiB; the kernel-log pane did not change after `ladder complete: 74 domains released` at kernel 55.268 s, and the
  display kept updating after `dispext0-3_sys` were released (52-55 s). The M1's host log shows no USB event for 13 minutes
  after the handoff.
* **On-screen numbers (native, attempt 20; one CPU, software rendering beside them, gcc 16.1.1; no parity claim):**
  `freq 2.65 GHz est`, `fma_asm 29.8` / `fma 28.5 GFLOP/s`, `intmix 5.00 Gop/s`, `sort 4.94 Melem/s`, `sgemm 11.6 GFLOP/s`,
  `syscall 352 ns`, `pingpong 3.99 us`, STREAM `28.2 / 19.9 / 25.0 / 24.7 GB/s`, chase `2.37 ns` (16 KiB), `15.3` (4 MiB),
  **`604` (32 MiB), `617` (128 MiB)**, first touch `42.7 GB/s`. All eleven steps finished in **348 s** (expected ≈ 75 s):
  steps 1-10 took 16 s, the chase about 332 s.
* **Observed, cause unknown:** DRAM-sized chases read 604-617 ns (this machine's macOS baseline: 51 and 106 ns); compute
  and STREAM rows are about a fifth of the baseline's. *Hypothesis:* CPU 0 is an efficiency-class core near 2.65 GHz with no
  frequency scaling; the STREAM gap follows from the long DRAM latency. The STREAM rows ran before most of the 74 ladder
  steps; the 32/128 MiB chase rows after all of them. Idle desktop CPU after the benchmark: 38-40%.
* **No USB device appeared on the M1** after the handoff (the boot035 DT has no controllers). The RAM-root image content was
  **not inspected** on the M1 (no zstd tool); the overlay source in Git was reviewed.
* **For the M5 (proposals, not authorization):** print the CPU's implementer/part (and cluster) on the status screen and
  decide whether to measure on a performance core; run one 128 MiB chase before the ladder (kernel < 18 s) and one after
  (> 60 s); shorten or reorder the long chase step and slow the redraw during long runs; the USB link (boot039) stays the
  route to SSH.
* Report: `native/boot/stage-b-2026-10-16-attempt20-result.md`. Fresh policy/default checks **NOT CHECKED**. The fixed E1
  probe is still **NOT RUN**.

### Historical M1 readiness — attempt 20 (boot035 RAM root, run 33) offline PASS (consumed: attempt 20 ran), 2026-10-16

* **Intake (M5 handoff `3f7b24d`).** The boot035 package was re-verified, not re-downloaded: archive 16,723,179 bytes,
  SHA-256 `81cbbd1c…`, checked against the Git pin; the `verify-package` receipt (manifest digest `7635c5e4…`, 13
  files) PASS; client pin clean `57a9339`.
* **RAM root (run 33).** `ramroot.cpio.zst` arrived by AirDrop into the repository root again (untracked, **not
  ignored**; the checklist's `~/Downloads` path was not used) and the M1 moved it into the ignored `build/ramroot/`
  before any commit, keeping run 30 beside it. Size 182,420,823 and SHA-256 `67f25732…d3f7` equal
  `ramroot-manifest.json`. **The image content was not decompressed or inspected** (no zstd tool, nothing installed):
  it is pinned by size, digest and the launcher's zstd frame check. The overlay **source** in Git was read instead:
  `ilinux-bench` writes only under `/run/ilinux/bench` and runs the benchmark steps under `timeout` (largest
  allocations 3 × 128 MiB, a 128 MiB chase buffer and a 1 GiB first-touch mapping, one at a time); `ilinux-status`
  reads `/proc` and the kernel journal and writes only under `/run/ilinux`; `ilinux-desktop.service` starts
  `start-hyprland` as the unprivileged user with `Restart=on-failure`, `RestartSec=3` and no start-limit change, so a
  persistent crash would restart every 3 s. No network, disk, mount or reboot commands.
* **Offline launcher, `--profile ramroot`:** `Package PASS`, `RAM root PASS` (run 33), `Operator key: none`, the fixed
  arguments, `m1n1 must append: idle=nop arm64.nowfxt`, upload estimate 227,080,994 bytes (45.4 s at 5 MB/s, 56.8 s
  at 4 MB/s), deadline 300 s. The 102 reviewed cases plus the 30 RAM-root tests (132) PASS. Launcher `4d55f0c9…` and
  the other five controller digests are unchanged.
* **Tools (ignored, M1 local):** `run-attempt20.py` is the attempt-19 wrapper with only the record path and title
  changed; an offline dry run against a scratch record captured every RAM-root line. Pre-flight and the read-only
  USB gate are reused.
* **State.** Attempt 20: live **NOT RUN**. Needs the human's fresh M1 restart, cable re-seat, a recording started
  **before** the launch command (phone fixed, whole screen, about 10 minutes), the M5 at Running proxy, then the go.
  The fixed E1 probe is still NOT RUN.

### Consumed M5 handoff — attempt 20: the boot035 RAM root with the live status screen (ran 2026-10-16; see the M1 result above)

* **Attempt 19 consumed:** the first native Omarchy desktop came up on the M5 and
  stayed up. Its two RAM-root findings are fixed in a new image; the kernel,
  DT, m1n1, launcher and profile are **unchanged** (boot035, `--profile ramroot`,
  `launch.py` `4d55f0c9…`).
* **The new image, VM job 039 run 33:** 182,420,823 bytes, SHA-256
  `67f257327ce308531b0c338babb8b644928cae8148bb34467042cca13cbad3f7`, pinned in `native/boot/ramroot-manifest.json`
  (`test_ramroot.py` 30 PASS; the committed launcher verifies boot035 + run 33
  offline: `Package PASS`, `RAM root PASS`, upload 227,080,994 bytes).
  Changes: (1) `ilinux-desktop.service` starts Hyprland through its own
  `start-hyprland` supervisor, so the red "started without start-hyprland"
  notice is gone (VM: 0 warning lines); (2) the status terminal is a live
  screen (`ilinux-status`): seconds since kernel start in block digits,
  CPU use, memory, the kernel-log tail (`quiet` hides the release ladder on the
  console; it shows here) and the single-thread results of the repository's
  `cpubench`/`membench`, built into the image with `gcc -O3 -march=armv8.4-a`
  and run once by `ilinux-bench` after the desktop is ready: eleven bounded
  steps under `timeout`, about 75 s natively; a failing step is reported and
  skipped, nothing waits on it. The user is in `systemd-journal` for the log.
* **VM (QEMU TCG, one vCPU, the boot035 Image):** desktop with wallpaper
  82.7 s after kernel start, 0 failed units, no warning,
  the counter advanced between two framebuffer captures 30 s apart, all eleven
  benchmark steps finished at 224 s (emulated timings, not hardware
  numbers). Report: `omarchy-arm64/ram-root-report-2026-10-16.md`.
* **The image travels privately:** the human AirDrops run 33's
  `ramroot.cpio.zst` to the M1 (`build/ramroot/`, ignored; replace run 30's
  file). Never commit or publish it (SSH host key).
* **M1 next:** `tools/m1n1-client/stage-b-instructions.md` (attempt 20):
  offline intake, then one filmed boot with the recording started **before**
  the launch command, the phone fixed, the whole screen in frame; stop at 10
  minutes from the handoff or on a reset; report the counter, the benchmark
  rows and the kernel-log lines read from the video. No parity claim from the
  on-screen numbers (one CPU, gcc build, the desktop running beside them).

### Current M1 result — attempt 19 (Omarchy RAM root on boot035): the first native Omarchy desktop on the M5

* **One RAM attempt consumed, controller PASS** (exit 0 in 44.441 s, handoff 2026-10-16T23:21:09Z; the
  226,753,047-byte upload took 42.28 s, 5.36 MB/s; the M1 did not panic). Launched once, after the pre-flight
  and read-only gate passed on the first try (cable re-seated, M5 booted into the Boot Lab last) and a 4.5 min wait
  for the M1's boot-time load to fall.
* **The Hyprland desktop came up and stayed up.** Video (39.5 s, starting at kernel ≈ 0.07 s, so no upload or
  handoff in it): wallpaper first visible at 6.9 s; the RAM root's status terminal reads `desktop ready 7.79 s
  after kernel start`; waybar is live (CPU 100% → 28% → 1%, memory 2.3G → 2.4G); `display card0 on
  simple-framebuffer`, kernel `7.1.9-g863199d8b4a3-dirty`, 16384-byte pages, 1 CPU; a foot terminal with a
  prompt. The human reports the desktop still up a few minutes after the handoff and at a later clock check
  (after more than 8 minutes), **with the clock advanced** (human-reported; not filmed). View-only, as designed.
* **Cosmetic warning:** a red notification, "Hyprland was started without start-hyprland. This is strongly
  discouraged unless you are in a debugging environment.", visible at 12 s, gone by 24 s: the session script runs
  `Hyprland` directly.
* **Early error lines seen in the first frame (effect unknown):** `kvm_arch_timer: Invalid virtual timer IRQ: 0`;
  `apple-pmgr-pwrstate 2300e80000 … power-controller@108: PS cs: Failed to reach power state 0xf`,
  `PM: always-on PM domain cs is not on`, `pm_genpd_init failed`, probe error -22.
* **No USB device appeared on the M1** after the handoff (the boot035 DT has no controllers); the host log shows only
  m1n1's device disconnecting 0.2 s after the handoff. The RAM-root image content was **not inspected** on the M1 (no
  zstd tool); it is pinned by size and digest.
* **Not established:** performance (frame rate, load), power and thermals, stability beyond what the human watched,
  failed units, input, storage, USB, SMP, GPU acceleration. No parity claim.
* **For the M5 (proposals, not authorization):** start Hyprland through `start-hyprland`; let the RAM root print its
  own measurements on the terminal (a single-thread run of the portable benchmarks, an uptime counter, the kernel
  log tail, since `quiet` hides the ladder) so a filmed run carries numbers; the USB link (boot039, bulk-only) stays the
  route to SSH; keep the phone fixed and start recording before the launch.
* Report: `native/boot/stage-b-2026-10-16-attempt19-result.md`. Fresh policy/default checks **NOT CHECKED**. The fixed
  E1 probe is still **NOT RUN**.

### Historical M1 readiness — attempt 19 (Omarchy RAM root on boot035) offline PASS (consumed: attempt 19 ran), 2026-10-16

* **Intake (M5 handoff `59b12a0`).** The boot035 package was re-verified, not re-downloaded:
  archive 16,723,179 bytes, SHA-256 `81cbbd1c…`, checked against the Git pin; the `verify-package`
  receipt (manifest digest `7635c5e4…`, 13 files) PASS; client pin clean `57a9339`.
* **RAM root.** `ramroot.cpio.zst` arrived by AirDrop into the repository root (untracked and **not
  ignored**); the M1 moved it into the ignored `build/ramroot/` before any commit. Size 182,092,876 and
  SHA-256 `58bdc6ce…a27e` equal `ramroot-manifest.json`; the launcher also checks the zstd frame magic
  and the Image pairing. **The content was not decompressed or inspected:** this Mac has no zstd tool and
  nothing was installed, so the image is pinned by digest only (an install would need the human's approval).
* **Offline launcher, `--profile ramroot`:** `Package PASS`, `RAM root PASS`, `Operator key: none`, the
  fixed arguments, `m1n1 must append: idle=nop arm64.nowfxt`, upload estimate 226,753,047 bytes
  (45.4 s at 5 MB/s, 56.7 s at 4 MB/s), deadline 300 s. The 102 reviewed cases plus the 30 RAM-root
  tests (132) PASS. Launcher `4d55f0c9…` and the other five controller digests are unchanged. boot035's
  config has `RD_ZSTD`, `DRM_SIMPLEDRM`, `SYSFB_SIMPLEFB` and `FRAMEBUFFER_CONSOLE` built in.
* **Tools (ignored, M1 local):** `run-attempt19.py` is the attempt-18 wrapper with the RAM-root output
  lines whitelisted and a new record path; an offline dry run against a scratch record captured every
  RAM-root line. The pre-flight and the read-only USB gate are reused.
* **What to expect on the M1:** no USB device after the handoff (the boot035 DT has no controllers), so
  the video is the evidence; the M1 will only save the host log. Same host precautions as before (fresh
  restart, cable re-seat, `caffeinate -i`, fsync'd records).
* **State.** Attempt 19: live **NOT RUN**. Needs the human's fresh M1 restart, cable re-seat, whole-screen
  filming, the M5 at Running proxy, then the go. The fixed E1 probe is still NOT RUN.

### Consumed M5 handoff — attempt 19: the Omarchy RAM root on boot035 (ran 2026-10-16; see the M1 result above)

* **Attempt 18 consumed:** boot038's ACM + ECM gadget was enumerated and
  configured, then its control endpoint stopped answering (interrupt-IN
  notification endpoint suspected). Only the USB link is affected; a bulk-only
  candidate (boot039) is being prepared by a side session.
* **Attempt 19 = the boot035 package (attempt 16's proven kernel and DT, no USB
  controllers) launched with `--profile ramroot`**: the Arch RAM root from VM job
  039 run 30 (182,092,876 bytes, SHA-256
  `58bdc6cee4e2a9d0b1fd2a800f2549c7e3ea300e0a6e76d3d17db3b08dd5a27e`, pinned in
  `native/boot/ramroot-manifest.json`, commit `02c8ff1`) instead of the
  diagnostic initramfs: systemd, seatd, Hyprland on simpledrm with llvmpipe,
  Omarchy's configuration, waybar, foot. View-only (no input yet). The handoff
  records in `native/boot/` point at boot035 again (archive `81cbbd1c…`,
  SHA256SUMS digest `7635c5e4…`).
* **Offline:** the committed launcher (`4d55f0c9…`) verifies boot035 + the run-30
  RAM root (`Package PASS`, `RAM root PASS`, upload ≈ 226.8 MB, 45–57 s, 300 s
  deadline); all `native/boot` suites PASS. VM: desktop with wallpaper 68.4 s
  after kernel start under QEMU TCG, 0 failed units.
* **The image travels privately:** the human AirDrops `ramroot.cpio.zst` to the
  M1 (`build/ramroot/`, ignored). Never commit or publish it (SSH host key).
* **M1 next:** `tools/m1n1-client/stage-b-instructions.md` (attempt 19). Re-seat
  the cable after the M1's restart; film the whole screen; stop when the desktop
  has been steady 2 minutes, or at 10 minutes.

### Current M1 result — attempt 18 (boot038): macOS configures the ACM + ECM gadget, then control transfers time out; no serial, no network

* **One RAM attempt consumed, controller PASS** (exit 0 in 10.958 s, handoff
  2026-10-16T20:22:28Z, M1 did not panic). Launched once, after the read-only USB gate
  had failed for about six minutes following the fresh M1 restart (no device visible until
  the cable was re-seated; nothing opened or sent). **Second fresh restart in a row with
  this symptom** (attempt 17's first launch was the other): re-seat the cable after the
  restart, then run the gate (Hypothesis, n = 2).
* **Linux side unchanged from attempt 17:** release ladder complete (50 domains) at
  45.024 s, 60 s milestone at 63.60 s, heartbeats 000-022 to 113.70 s, no reset. The human
  reports the screen still updating minutes after the clip.
* **Host side:** the M1 enumerated the gadget 3.95 s after the handoff (`1d6b:0104`,
  `bcdDevice 0x0038`) and macOS selected configuration 1 at +8.45 s, as in attempt 17. Then
  **control-endpoint transfers timed out** (+9.57, +10.77, +11.99, +14.34 s, then a transaction
  error); attempt 17's host log has none. **No interface node, no ACM or ECM driver, no
  `cu.usbmodem*`, no new `enX`** (30 s and 60 s waits), so no serial log and no SSH.
* **M5 screen:** port 1 `configured` from heartbeat 001 (8.51 s) but **`usb0 down rx=0 tx=0
  no-ll`** throughout (attempt 17 with EEM: `usb0 up` and a link-local address at the same
  point; ECM raises its link only when the host selects the data interface's alternate setting
  1, which never came); ports 2-3 `not attached`; no `dwc3`, `apple-dart` or streamer line read.
* **Reading (Likely, not tested):** the interrupt-IN notification endpoints that ACM and ECM add
  (EEM was bulk only; the ADT flags `ncm-interrupt-ep-disabled`) are what the device could not
  service once the host configured it. Not excluded: a macOS composite-driver request the
  two-IAD device does not answer; a Linux function's setup handler that never completes.
* **For the M5 (proposals, not authorization):** a next gadget with **no interrupt endpoint**
  (a bulk-only vendor function such as `gser` or FunctionFS) that macOS leaves unbound and the
  M1 reads from user space (libusb or IOUSBHost; the M1 can build and offline-test the reader);
  controller state in the heartbeat (mount debugfs, `CONFIG_DEBUG_FS=y`, print the dwc3
  `ep0state`, `link_state` and endpoint states) so the screen alone names it.
* Report: `native/boot/stage-b-2026-10-16-attempt18-result.md`. Fresh policy/default checks
  **NOT CHECKED**. The fixed E1 probe (re-verified offline) is still **NOT RUN**.

### Historical M1 readiness — boot038 / attempt 18 offline PASS; E1 probe re-verified (consumed: attempt 18 ran), 2026-10-16

* **Intake (M5 handoff `bd814ad`, published `5105c58`).** Private prerelease
  `native-j716c-boot038` (target `bd814ad`): archive 18,904,584 bytes, SHA-256
  `09f5a5d7…5f70`, checked against Git **before extraction** (GitHub's asset
  digest equal); 14 regular members, no links. The `verify-package` receipt
  (manifest digest `efba5795…a186`, 13 files) and the committed launcher's offline
  verification PASS. The 102 reviewed cases PASS (37 + 10 + 6 + 16 + 5 + 19 + 2 + 6 + 1)
  plus the boot036 suites (`usb_dt` 6 skipped, `control_channel` 6 with 1 skipped,
  `kconfig_guard` 7 with 1 skipped, `ramroot` 30). Launcher `4d55f0c9…` and the other five
  controller digests unchanged; client pin clean `57a9339`; the packaged key equals the
  M1's, and its private half is present with mode 600.
* **Independent review.** Image, `kernel.config`, both DTBs (Stage-B `a676087b…`),
  `m1n1.bin` and the generic initramfs are **byte-identical** to the boot036 package
  the M1 verified for attempt 17. The Stage-B initramfs differs only in `/init` (423
  entries each, extracted and compared); its `authorized_keys` is exactly the M1's key,
  mode 600; no self-test overlay. `/init` is a static aarch64 ELF (64 KiB segment
  alignment), its strings name `acm.GS0`, `ecm.usb` and `bcdDevice 0x0038` and contain no
  EEM; the repository `init.c` equals the shipped `diag-init.c`. The shipped config has
  the ACM, ECM, EEM, NCM, serial, RNDIS and FunctionFS functions built in (`=y`), none as
  a module. The whole `init.c` diff was read: the log streamer is a forked child with a
  non-blocking write that retries the same record, so PID 1 and the heartbeats never wait
  on the port.
* **Review notes for the M5 (none blocks the attempt).**
  1. `CONFIG_LOG_BUF_SHIFT=17` (128 KiB): with `initcall_debug` the oldest records may
     be gone when the streamer first reads `/dev/kmsg`, so the serial capture may not
     start at `Linux version`, and gaps show in its timestamps. SSH `dmesg` has the same
     ring limit.
  2. A streamer restart (after a hangup) replays from the oldest surviving record, so
     duplicates are expected after a host-side close and reopen.
  3. The gadget tty keeps the default N_TTY line discipline with ECHO on, so any data the
     host sends is echoed back into the log stream. The checklist's `cat` would be safe
     only if the host tty has echo off. **Observed:** on an unrelated macOS serial port
     (`cu.Bluetooth-Incoming-Port`) the default is raw with echo off; not yet observed on
     the CDC-ACM port. In a pty test, plain `cat` with echo on wrote 130 bytes back; the
     M1's reader wrote 0.
  4. New for the M1 host: a Linux composite device makes macOS bind its ACM and ECM
     drivers together, a different path from attempts 15–17. Attempt 15's M1 panic was in
     the Apple CDC driver at the handoff (none in attempts 16 and 17). The precautions are
     unchanged (fresh restart, `caffeinate -i`, fsync'd records); the human should save work
     on the M1.
* **Method deviation (reader only).** The M1 reads the ACM port with
  `serial_read.py`: `O_RDONLY`, never writes, checks the terminal flags and clears local
  echo only if it is on, fsync every second. What the checklist touches is unchanged.
  The driver report comes from the registry (`ioreg`, which opens no port); the network and
  SSH steps run only if a **new** `enX` has an `inet6` link-local address, with no setting
  changed.
* **Loaded-driver check (before the fresh restart):** `kmutil showloaded` finds
  `com.apple.driver.usb.cdc.acm`, `…cdc.ecm` and `…cdc` loaded (1 line each). It is
  repeated after the fresh restart by the pre-flight script, which also records
  `ifconfig -l` and passes the read-only USB gate.
* **E1 probe re-verified (separate lab boot, not started).** The fix is the intended alias
  of the function-local imports in `mtp_probe.py` and `pmgr_probe.py` (diff read);
  `test_mtp_probe.py` 27 and `test_pmgr_probe.py` 86 PASS; `plan` output identical to the
  first readiness (66 reads, same hash); the real E1 path, run under the pinned client with
  the only function that opens the port replaced in-process by a raising stub, now passes the
  former `NameError` site and stops at the stub (no port opened, no file written). Needs the
  human's go and the read-only USB gate first.
* **State.** Attempt 18 and E1 session 2: live **NOT RUN**. Needs the human's fresh M1
  restart, filming (1080p or better, fixed stand, original file afterwards), the M5 at
  Running proxy, then the go. Order: attempt 18 first; E1 as its own lab boot later.

### Historical M5 handoff — boot038 / attempt 18 (consumed: configured, then EP0 timeouts)

* **Attempt 17 consumed:** the Linux side of boot036's link works on hardware
  (three dwc3 cores, gadget bound, enumerated in 8 s, no faults, baseline held);
  macOS 26.0.1 on the M1 has no CDC-EEM driver, so no interface appeared.
* **boot038 = boot036 with only the gadget's functions changed:** CDC-ACM (a
  serial port carrying the kernel log, written only by the M5; macOS creates
  `/dev/cu.usbmodem*`) + CDC-ECM (network, same MACs and link-local addresses,
  key-only dropbear for the M1's key `a6717b0`). `bcdDevice` 0x0038. Image,
  config, Stage-B DT, m1n1 and launcher byte-identical to boot036.
* **Release:** `native-j716c-boot038`, private prerelease published 2026-10-16
  on `bd814ad`; archive 18,904,584 bytes, SHA-256
  `09f5a5d723461bccfba3c29aacb084c3318203d074e522c1527d650186e05f70` (GitHub's
  asset digest and a fresh download both match), SHA256SUMS
  digest `efba5795…a186`; initramfs `30800bdd…`. Offline: job 041, packager,
  committed launcher (`4d55f0c9…`), generic-VM liveness and the dummy_hcd
  self-test (ACM log port, ECM, SSH) all PASS.
* **M1 next:** `tools/m1n1-client/stage-b-instructions.md` (attempt 18): the
  loaded-driver check with `kmutil showloaded`, the serial capture first, then
  ECM. Report: `native/boot/boot038-control-channel-2026-10-16.md`.
* **E1 probe fixed (M5):** `mtp_probe.py` and `pmgr_probe.py` alias their
  function-local imports before the class body; new tests cover the live
  wiring. The E1 plan is unchanged (66 reads). A rerun needs M1 re-verification
  (`test_mtp_probe.py` now 27 tests) and the human's go; it can share the lab
  boot with nothing else, as before.

### Current M1 note — E1 failure is independent of the USB port; run the read-only gate first, 2026-10-16

* **E1 cause re-verified after the human reported the cable had first been in the
  wrong USB port.** The real E1 code path was run with device access blocked
  **inside the process** (`pmgr_probe.open_primary`, the only function that opens
  the serial port, replaced by a stub that raises; the M1 test could not open any
  port). It stops with the identical `STOP: NameError name 'M1N1Proxy' is not
  defined`, before device access. With **only** the class-scope fix applied in
  memory (repo file untouched) it proceeds to the device-access step (the
  sentinel stops it there). So the NameError is a code bug that does not depend on
  the port; **the published E1 diagnosis stands**.
* A wrong port would only have shown **after** the fix, at the USB identity gate:
  attempt 17's first launch stopped there (`InvalidFileException`, empty USB
  registry) before the cable was moved. Whether the port was wrong at E1 time is
  unknown and irrelevant to that failure, but it is a live risk for the next E1
  session.
* **Lesson for every live tool:** run the read-only gate (`usb_identity.discover()`
  plus `select_primary`, which opens no port) before the live command, so a wrong
  port or stale proxy is caught before a tool consumes its session. M1 did this
  before attempt 17's second launch. Suggest adding it to the E1 and PMGR runbooks.
* At review time the M1 saw the M5's m1n1 USB device again (proxy up). Nothing was
  run against it.


### Current M1 result — attempt 17: Linux USB gadget enumerates on the M1; macOS has no EEM driver

* **Launch 1** (18:26:32Z) stopped at the USB identity gate: the freshly restarted M1
  saw no USB device at all; no port opened, no request sent. The human moved the
  cable to another port and asked for the rerun. **Launch 2** (handoff
  2026-10-16T18:29:14Z): **exit 0 in 10.975 s**, all gates PASS; the M1 did not
  panic.
* **First Linux USB on this M5 Max.** All three device-mode `dwc3` controllers
  probed (26-31 ms), three CDC-EEM gadgets bound, dropbear started key-only
  (pid 55), and the **M1 enumerated the cabled port 8 s after the handoff**
  (`1d6b:0104`, `bcdDevice 0x0036`, high speed, configuration 1 set by macOS).
  The M5 reports port 1 `configured`, `usb0 up`, link-local address assigned
  (tentative at 8.5 s, final from 13.5 s), `rx=0 tx=0` to the end; ports 2-3
  `not attached`.
* **The channel did not come up: macOS has no EEM driver.** `AppleUSBCDCCompositeDevice`
  bound the device, nothing bound the EEM interface, no `enX` appeared, no SSH.
  `com.apple.driver.usb.cdc.eem` is **not in this Mac's kernel collection in any
  state** (macOS 26.0.1); the `AppleUSBEEM.kext` on disk is a stub. ECM is loaded,
  NCM is available, the serial (ACM) driver is loaded.
* **Correction:** the M1's 2026-10-15 EEM check proved only the stub bundle exists.
* Baseline held: PID 1, 60 s milestone (63.6 s), heartbeats 000-019 to 98.7 s,
  ladder complete at 45.02 s (**50 domains**, none from atc0-2 or smc_i2cm), no
  reset, no error line on screen, DART fault counters 0 early.
* Return to Macintosh HD reported; fresh policy/default NOT CHECKED. No retry or
  settings change. Report: `native/boot/stage-b-2026-10-16-attempt17-result.md`.
  M5 to pick a function macOS can bind (ECM, NCM or ACM serial).


### Current M1 result — MTP E1 probe stopped before any device contact: NameError in its live wiring, 2026-10-16

* **E1 session 1 stopped before any device contact.** Human-started proxy; the
  probe was invoked once at **18:18:00 UTC** (HEAD `9a3e002`) and printed
  `STOP: NameError name 'M1N1Proxy' is not defined`, exit 1. **No serial port
  was opened and no request was sent to the M5**: the error is raised while the
  probe builds its API object, before `open_primary`. `mtp-probe.txt` holds only
  the pin-check line and the STOP line; no JSON was written.
* **Cause (Confirmed, reproduced in isolation under the client's Python 3.9.6):**
  `mtp_probe.py:426` has `M1N1Proxy = staticmethod(M1N1Proxy)` inside class `Api`,
  nested in `connect_and_run`, where `M1N1Proxy` is a function-local import
  (line 418). A class body that assigns a name resolves the right-hand side in
  class, global and builtin scope only, so the enclosing function's import is not
  visible. The same shape is at `native/probe/pmgr_probe.py:808-809` (`M1N1Proxy`
  and `load_adt`): **the PMGR probe would stop the same way.** No other tracked
  file has it.
* **Why the tests passed:** neither suite builds that class. The PMGR test
  exits earlier at the m1n1 pin check, and the E1 tests never call
  `connect_and_run`.
* **Suggested fix (M5-owned code; not applied by M1):** alias before the class
  (`_proxy_cls = M1N1Proxy`, then `M1N1Proxy = staticmethod(_proxy_cls)`, and the
  same for `load_adt`), or build the API with `types.SimpleNamespace`; add an
  offline test that runs `connect_and_run` through the API construction with
  the real `m1n1.proxy` imports and a stub transport.
* **M1 did not edit the probe or retry.** E1's approval covers the reviewed
  probe and the procedure says stop on any `STOP:` line. A rerun needs M5's
  patch, M1's re-verification and the human's go. The M5 stays at
  `Running proxy...` at the human's discretion; nothing needs cleaning up.
  Attempt 17 is unaffected (its launcher path is separate and was exercised
  live in attempts 14-16).


### Current M1 readiness — MTP E1 probe and attempt 17 (boot036) offline PASS, 2026-10-16

* Pulled `0363bd5` (13 commits). Both items are queued in `coordination.md`:
  E1 (read-only, human-started, no retries, E1 only) and attempt 17 (no
  network-settings change on the M1). Order: **E1 first, then attempt 17**, as
  two separate human-started lab boots.

**MTP E1 read-only register probe** (`kernel/experiments/mtp-input/m1-instructions.md`)
* E0 offline PASS: `test_mtp_probe.py` Ran **26** tests OK; `mtp_probe.py plan`
  `PLAN: 66 reads, all 32-bit, none with a side effect; nothing was written`;
  `read --help` rc 0 under the pinned client.
* **M1 independent review:** the probe's proxy wrapper exposes only `read32`
  inside ADT-declared regions (any other attribute raises `Forbidden`); the code
  calls only `read32`, `faulted`, `get_exc_count`, `get_bootargs_rev` and
  read-only memory fetches; no write, mask, call, reload or chainload anywhere;
  it reuses `pmgr_probe`'s gates (USB identity, chip t6050, boot021 marker, no
  secondaries), needs `--confirm MTP-PROBE-J716C-READ`, and refuses an existing
  JSON output file.
* **Residual risk, not removed by reading:** a read of an unpowered block could
  raise an asynchronous SError that hangs m1n1. Recovery is a power-off; the
  probe writes nothing persistent.
* Record: ignored `build/native-intake/results/mtp-probe-readiness.json`.

**Attempt 17 / boot036 (USB control channel)**
* Archive **18,902,541 bytes**, SHA-256
  `f09a00000925aea64a6ea7ab6dace05958d779d2367fc6aec233becc58ca71a3`, verified
  against Git before extraction; 14 regular members, no absolute or parent
  paths. **13-file intake and offline launcher PASS.**
* **102 reviewed M1 cases PASS** (37+10+6+16+5+19+2+6+1). Boot036 suites:
  `test_ramroot` 30 PASS; `test_usb_dt` 6 tests (all 6 skipped), `test_control_channel`
  6 (1 skipped), `test_kconfig_guard` 7 (1 skipped): the skips are the
  real-package cases that need the M5's build directories, as the checklist says.
* Payload: Image `e0e53113…f3f7` (44,681,728 B), Stage-B DT `a676087b…efa5`,
  Stage-B initramfs `5f4b478b…b248` (2,392,627 B), SHA256SUMS `4fbd64d4…442f`.
  Client pinned clean at `57a9339`; installed boot021 unchanged.
* **Controller:** `launch.py` `4d55f0c9…840b` matches; the other five digests are
  unchanged. M1 read the `9ee6b2f` diff: the default `stage-b` profile behaves
  as in attempt 16 (initramfs, fixed arguments, confirmation string, 180 s
  deadline, append check); the `ramroot` profile is new code attempt 17 does
  not use.
* **M1 independent package review** (because it adds a network-reachable SSH
  server to the M5):
  * DT versus boot035: 358 to 361 nodes; exactly three `snps,dwc3` controllers
    added, three USB DARTs enabled, **39** power domains disabled (13 each for
    `atc0`-`atc2`); nothing else changed.
  * initramfs: `/init` is built from the committed `init.c`; dropbear (Arch Linux
    ARM 2026.94-1) starts with `-F -E -s -R -j -k -K 15 -p 22` (no password
    logins, no port forwarding); root's password is locked (`*`);
    `root/.ssh/authorized_keys` is **byte-identical to the M1 public key**
    (`SHA256:o7wtpNY0RUOIIGTyIJvspZFOetYFFG2oeMw5ecZc3yI`), one line, no other
    key; `/init` strings show IPv6 link-local only, no DHCP or `ifconfig`.
  * The checklist's key grep prints the M1 key; the private half is present at
    mode 600.
* **Wrapper note:** `launch.py` now formats `Board/framebuffer PASS; allocating
  RAM for … payloads.`, so a literal-print scan would drop that checkpoint.
  `run-attempt17.py` adds it explicitly (checked against all 16 attempt-16
  checkpoints), saves each record with `fsync`, and prints a 10-minute deadline.
* Records: ignored `build/native-intake/receipts/boot036-attempt17.json`,
  `…/results/boot036-stage-b-attempt17.json`, `…/run-attempt17.py`.

**Live checks NOT RUN for either item.** Before attempt 17 the M1 should be
restarted fresh and kept awake with `caffeinate -i`; `ifconfig -l` is recorded
immediately before the handoff; the original video file (AirDrop or cable, not
Messages) is needed. No M1 network setting changes; if the new interface has no
`inet6` address M1 stops and asks.


### Current M5 handoff — MTP input: E1 read-only register probe queued for the M1 (NOT RUN)

* **User approval, 2026-10-15:** "queue the read-only E1 probe
  (kernel/experiments/mtp-input/probe/mtp_probe.py) for the M1 agent,
  human-started, no retries." **Scope is E1 only.** Not approved: any write
  request, E2 (booting a kernel with the MTP input patch), E3 (trackpad
  firmware, SMC functions), a new boot package (a separate proposal exists for
  the packaging, offline only).
* **What it is:** 66 32-bit register reads through the m1n1 proxy, at offsets
  derived from the target's own ADT and inside the regions that ADT declares,
  never at a register whose read has a side effect (mailbox RECV, DockChannel RX
  data). Its proxy object has no write method. It reuses the reviewed gates of
  `native/probe/pmgr_probe.py` (USB identity, chip t6050, installed boot021
  marker, no started secondaries). Installed boot021 and the clean pin `57a9339`
  stay unchanged; RAM-only; no volume, security, `bputil` or `kmutil` change.
* **M1 next, offline (no device):**
  `python3 -I kernel/experiments/mtp-input/probe/test_mtp_probe.py` (expect
  `Ran 26 tests ... OK`), `python3 -I kernel/experiments/mtp-input/probe/mtp_probe.py plan`
  (expect `PLAN: 66 reads`), and
  `tools/m1n1-client/run.sh kernel/experiments/mtp-input/probe/mtp_probe.py read --help`.
  Publish readiness here with live checks **NOT RUN**, then tell the human.
* **Live, human-started, one session, no automatic retries:** iLinux Boot Lab →
  Continue → `Running proxy...`, both Macs on power, same direct cable; then the
  E1 command in `kernel/experiments/mtp-input/m1-instructions.md` (writes
  `build/native-intake/mtp-probe.{json,txt}`). Stop on any `STOP:` line; return
  to Macintosh HD.
* **Report back:** the whole text output and the JSON (addresses and register
  values only); the table in `m1-instructions.md` says what each line decides
  (DART register base, which SID iBoot left translating, ASC state, mailbox
  layout, DockChannel FIFO depth).
* **Delivery:** committed on `main` by the M5 side ("Add the MTP input path
  analysis, offline preparation and the queued E1 probe", user-authorized
  2026-10-15); the M1 gets it with `git pull --ff-only` once the remote's
  `main` carries that commit.

### Historical M5 handoff — boot036 / attempt 17 (consumed: Linux USB works; macOS lacks EEM)

* **Attempt 16 consumed** (first stable baseline). boot036 = boot035 plus a
  CDC-EEM USB network link and key-only SSH into native Linux over the M1
  cable: the gadget stack built in (`USB_LIBCOMPOSITE=y`, `USB_CONFIGFS=y`, 14
  lines m to y), three dwc3 device-mode cores on the PHY state m1n1 leaves
  (DART instance 1, stream 1), all 39 ATC 0–2 power domains disabled, and an
  `/init` with one gadget per controller plus dropbear for root, **key-only, the
  M1's key** from `a6717b0` (`SHA256:o7wtpNY0RUOIIGTyIJvspZFOetYFFG2oeMw5ecZc3yI`).
  Port N's Linux end is `fe80::69:6cff:fe69:6e0N`.
* **Release:** `native-j716c-boot036`, private prerelease published 2026-10-15
  on `0fbbf82`; archive 18,902,541 bytes, SHA-256
  `f09a00000925aea64a6ea7ab6dace05958d779d2367fc6aec233becc58ca71a3` (GitHub's
  asset digest and a fresh download both match), SHA256SUMS
  digest `4fbd64d4…442f`. Image `e0e53113…` (reproducible: two VM builds gave the
  same bytes), DT `a676087b…`, initramfs `5f4b478b…`; m1n1, full DT and generic
  initramfs identical to boot035. Controller digests unchanged.
* **Offline:** VM job 041 PASS; the packager's exact DT/config/init/initramfs and
  kernel.config-provenance checks PASS; the committed launcher's offline
  verification PASS; generic-VM liveness and the dummy_hcd USB self-test PASS.
* **M1 next:** `tools/m1n1-client/stage-b-instructions.md` (attempt 17) with the
  network steps in `tools/m1n1-client/control-channel-draft.md`. Restart the M1
  fresh, film at 1080p or better (portrait allowed, phone fixed), stop at 10
  minutes or once the SSH captures are saved. No network-settings changes.

### Current M1 note — boot036 control key published; macOS EEM driver checked, 2026-10-15

* **Public key published** for boot036's USB gadget: commit `a6717b0` adds only
  `kernel/experiments/usb-gadget/authorized_keys` (one line, ed25519, comment
  `ilinux-m1-control`). Fingerprint for M5 to confirm:
  `SHA256:o7wtpNY0RUOIIGTyIJvspZFOetYFFG2oeMw5ecZc3yI`.
* **Private half** is `build/control/m1-control` (mode 600, git-ignored, not
  tracked; the folder carries no iCloud sync markers). It was created without a
  passphrase, as requested, and stays on this Mac. `kernel/experiments/
  usb-gadget/` did not exist before this commit; M5 gets it on its next pull.
* **Read-only M1 facts for M5:**
  * `sw_vers`: macOS **26.0.1**, build **25A362**.
  * `/System/Library/Extensions/AppleUSBEEM.kext`: `CFBundleVersion` **5.0.0**;
    `bInterfaceClass` **2**, `bInterfaceSubClass` **12**, `bInterfaceProtocol`
    **7**. This is exactly the expected CDC-EEM triple, so the built-in driver
    can bind a gadget that presents it.
* **Not done and not authorized:** no network, sharing or security setting was
  changed; no interface exists yet (boot036 NOT RUN). If a new network
  interface appears, M1 will not alter network settings without the human's
  approval; prefer addressing that needs no system configuration change.
* **Host precautions retained** from attempt 15 (the M1 panicked in the
  CDC-ACM serial driver, a different USB driver): fresh restart, `caffeinate
  -i`, durable `fsync` records. A panic in the EEM path is not ruled out.
* **Next:** M5 builds boot036 with this key; M1 then runs offline intake and
  publishes readiness before any live attempt.


### Current M1 result — attempt 16: boot035 runs the whole release ladder; first stable native baseline

* One boot035 RAM attempt at readiness `7a37fb6`, M5 handoff `4debc28`.
  **Controller exit 0, 10.493 s**; handoff 2026-10-15T20:28:25.611598Z. All gates
  PASS. **No M1 host panic** (uptime continuous since 11:09 EDT, no new panic
  report).
* **First stable native baseline.** PID 1 alive, one CPU, `online_cpus=1`
  heartbeats 000-021 every 5.0 s to kernel 108.4 s; `60s elapsed; still alive`
  at 63.36 s. Clip (120.5 s, 320x568) ends at kernel ~110.7 s, no restart.
* **Release ladder completed:** first release 19.43 s (`atc?_usb_aon`, **no
  `smc_i2cm`**), step 11 `atc?_common_dp_3` at 24.55 s passed,
  `ladder complete: 74 domains released` at 57.31 s (M5 had predicted 145; only
  74 were powered on at boot). A `dispext*` domain was released and the console
  kept rendering.
* **Refuted:** attempt 15's step-17-immediate explanation. **Not separated:**
  SMC domains versus the M1's post-panic reset for attempt 15's second reset,
  because this run changed both (SMC nodes removed, no M1 panic). Attempt 14
  (no M1 event) still needs the SMC or simultaneity explanation.
* Domain-name digits and the panel/GPIO lines were not readable at this
  resolution. User reports no M5 or M1 crash afterwards (not filmed).
* Fresh policy/default NOT CHECKED. No retry or settings change. Report:
  `native/boot/stage-b-2026-10-15-attempt16-result.md`.


### Historical M1 readiness — boot035 / attempt 16 offline PASS, 2026-10-15

* Pulled/read M5 handoff `4debc28` (boot035 / attempt 16; published as
  `9815dd7`), the Stage-B checklist and `native/boot/attempt15-review-2026-10-15.md`.
  Archive **16,723,179 bytes**, SHA-256
  `81cbbd1ca09ec53bbfe8f616e578c07d7f878a26a7629c2d1de40d969be966e7`, verified
  against Git before extraction; 14 regular members, no absolute or parent paths.
  **13-file intake and offline launcher PASS.**
* **102 M1 offline cases PASS** (37+10+6+16+5+19+2+6+1), all exit 0; synthetic
  transport only. Image SHA-256 unchanged from boot034
  `1131a1af5e4d5cfa3206c5eb0afe1a6d72d86a2761a8d906b592e33556882579`; Stage-B DT
  `b1105bbf2c207c8c816c4b9cc0231ecc1d49543e05fe4b772bcb153019e186db`;
  SHA256SUMS `7635c5e4a25b051fa933ad969e2407c3f6a63cea876570f58052a474cf162f8d`.
* **M1 independent DT diff (boot034 vs boot035):** 365 -> 358 nodes; exactly
  `smc_i2cm0`-`6` (`power-controller@8028`-`@8058`) removed; none added; no
  property changed on any surviving node; nothing references the removed nodes;
  188 -> 181 pwrstate domains; GPIO reserved ranges kept. Image, initramfs, m1n1
  and config identical to boot034. All six controller digests match; client
  pinned clean at `57a9339`; installed boot021 unchanged.
* Ignored receipt `build/native-intake/receipts/boot035-attempt16.json`, record
  `build/native-intake/results/boot035-stage-b-attempt16.json` and wrapper
  `build/native-intake/run-attempt16.py` retain the hashes. The wrapper differs
  from attempt 15's only in names and an `fsync` after every record save, so a
  host crash cannot lose checkpoints again.
* **Reading of the experiment:** survives the whole ladder (about 94 s) and
  stays alive to 180 s -> SMC domains were the trigger, and the attempt-15 host
  reset was not. Reset again -> record the step ~5.6 s earlier. If the M1
  panics again at handoff the run is still informative: a surviving M5 refutes
  the host-reset explanation.
* **Ready for Stage B attempt 16** after publication. Human plans portrait
  framing filling the frame vertically, phone fixed. **Native boot035 and live
  checks NOT RUN at readiness.** hv003 and the PMGR probe remain unchecked by M1.
* Next: M1 freshly restarted and kept awake with `caffeinate -i`; one filmed RAM
  launch; film to reset or **180 s from handoff** (the ladder alone runs to
  ~94 s); then Macintosh HD. No retry/reinstall/settings/volume change.


### Historical M5 handoff — boot035 / attempt 16: Stage-B DT without the SMC-owned domains (consumed: first stable baseline)

* **Review of attempt 15** (`native/boot/attempt15-review-2026-10-15.md`): no
  Asahi PMGR DT (M1–M3) exposes any `smc_*` domain; our generated t6050 draft
  carried seven (`smc_i2cm0`–`6`), the SMC's own I2C masters, with no ADT
  consumer. Attempt 14 reset 5.55–5.69 s after the bulk power-off, attempt 15
  5.70–5.88 s after the last SMC release. **Likely:** cutting an SMC I2C master
  makes the SMC reset the SoC ≈ 5.6 s later. Not hardware-confirmed.
* **boot035** = boot034 with those seven nodes removed from the Stage-B DT (job
  038: `fdtput -r`, decompiled diff shows nothing else, schema clean; the
  packager refuses any other DT delta). Image, initramfs, m1n1, config, fixed
  arguments and the reviewed controller are byte-identical. The ladder now walks
  145 domains, ≈ 19–94 s kernel time.
* **Release:** `native-j716c-boot035`, private prerelease published 2026-10-15
  on `4debc28`; archive SHA-256 `81cbbd1ca09ec53bbfe8f616e578c07d7f878a26a7629c2d1de40d969be966e7`
  (16,723,179 bytes; GitHub's asset digest and a fresh download both match),
  DT `b1105bbf…86db`, SHA256SUMS digest `7635c5e4…2f8d`. Offline: launcher
  verification and all suites that run without the client venv PASS.
* **M1 next:** `tools/m1n1-client/stage-b-instructions.md` (attempt 16).
  Restart the M1 fresh first and keep it awake; film fixed, landscape,
  bottom-left quarter; keep filming to **180 s** even after `ladder complete`.
* **Platform hurdles** (SPTM, WFI state loss, locked RVBAR, secondary
  watchdog) are mapped in the review: none blocks a one-CPU baseline or a first
  visual Omarchy boot; SMP, deep idle and the GPU remain research tracks.

### Historical M5 preparation — boot036 prepared offline (superseded by the attempt-17 handoff above)

* **M1: nothing to do for boot036 yet.** Attempt 16 (boot035) above stays the
  current task. boot036 runs only after attempt 16 reports a stable baseline,
  with a handoff of its own.
* boot036 adds a CDC-EEM USB network link and key-only SSH into native Linux.
  The Linux end of port N is `fe80::69:6cff:fe69:6e0N`. Report:
  `native/boot/boot036-control-channel-2026-10-15.md`. Draft M1 steps:
  `tools/m1n1-client/control-channel-draft.md` (including a read-only check
  that the M1's macOS has `AppleUSBEEM.kext`).
* VM job 041 is the M5's; job 040 (`040-usb-gadget-dt`) is the USB-DT side
  session's. `tools/vm-job.sh` now exits when the `vm` lock is held by someone
  else.

### Current M1 result — attempt 15: outlives attempt 14's reset, resets at ~27.7 s; M1 host panic at handoff

* One boot034 RAM attempt at readiness `a57837b`, M5 handoff `9499bd0`, started
  2026-10-15T15:08:37.154Z. **The M1 host kernel-panicked at 15:08:47Z, within
  ~0.5 s of the expected handoff** (NULL dereference in Apple's `usb.cdc` driver,
  reached from the launcher's Python process through IOSerialFamily/usb.serial/
  cdc.acm). The controller record stops at "Uploading DT, initramfs and kernel";
  later checkpoints and the exit status are **NOT RECORDED**. The M5 nevertheless
  booted Linux from the handoff with the expected GPIO counts.
* `Take15.mov` (49.9 s) reviewed. Kernel `ladder armed` 1.370 s; **sync_state
  kept domains on** at 3.236/3.237 s (call 1.4 ms vs 5.0 ms in attempt 14);
  PID 1 at 3.254 s; heartbeats 000-004 to 23.34 s. Ladder from 19.42 s, one
  release per 0.512 s; **17 releases visible** (six `smc_i2cm*`, then `atc*`
  usb_aon/phymxwrap/usb, then `atc?_common_dp_3` at 27.614 s).
* **Confirmed (single variable):** attempt 14's reset at ~8.77 s did **not**
  recur; Linux ran >= 27.6 s with the sync_state bulk power-off removed.
* **Silent reset at kernel ~27.7-27.85 s**, 0.07-0.24 s after the 17th
  power-off line; no message of any kind; Apple logo, then macOS login (11:09).
  `ladder complete` not reached.
* **Confounded:** candidates are ladder step 6 (`smc_i2cm?`, 21.98 s, +~5.7 s,
  matches attempt 14's 5.55-5.69 s latency but is a weak fit among 17 steps),
  step 17 (immediate), or the **M1's own post-panic hard reset**, which fell in
  the same seconds. Display domains were **not** reached (earlier DT-order
  estimate retracted; the ladder is newest-registered first).
* Video was rotated 90 deg after ~19 s: domain-name digits unreadable.
* Both machines restarted; fresh policy/default NOT CHECKED. No retry or
  settings change. Report: `native/boot/stage-b-2026-10-15-attempt15-result.md`.
  Recommend one clean rerun of unchanged boot034 on a freshly restarted M1.


### Historical M1 readiness — boot034 / attempt 15 offline PASS, 2026-10-15

* Pulled/read M5 handoff `9499bd0` (boot034 / attempt 15), the Stage-B checklist
  and `kernel/experiments/genpd-sync-state/`. Archive **16,723,189 bytes**,
  SHA-256 `a856a9b8c6b7fdafeeb68da8dddbc9c82f7e9b5cddf1dc691512f63c0803f5ff`,
  verified against Git before extraction; 14 regular members, no absolute or
  parent paths. **13-file intake and offline launcher PASS.**
* **102 M1 offline cases PASS** (37+10+6+16+5+19+2+6+1), all exit 0; synthetic
  transport only. Image SHA-256
  `1131a1af5e4d5cfa3206c5eb0afe1a6d72d86a2761a8d906b592e33556882579`
  (44,599,808 bytes); Stage-B DT unchanged
  `4b3adee52465b809e9c8a1946b7610c63f1ae3c0b24f7334cd485260da84adce`.
* Versus boot033 only the Image and package-manifest metadata differ. All six
  reviewed controller digests match; client pinned clean at `57a9339`.
  Installed boot021 unchanged.
* **M1 independent review of the Image change:**
  * `apply.py` read in full: both sync_state paths return early under
    `pd_ignore_unused`; one trace line before each real power-off; a bounded
    delayed-work ladder (17 s start, 500 ms step) that releases only
    boot-on, `stay_on`, non-always-on domains, name logged first.
  * `test_genpd.py`: the 2 tests that can run here pass (exact ladder block
    under ASan/UBSan, 5 mutations caught). 3 skip because M1 has no Linux tree
    (by design; M5 ran them in VM job 036).
  * Static count reproduced independently from the Stage-B DT:
    **152** unclaimed, non-always-on domains.
* **Observation for M5 (not a blocker):** the prepared framebuffer node claims
  no power domains, so the ladder also releases the display domains. In DT
  order (estimate; runtime order may differ): `dispext0..3_*` at ~20-34 s
  kernel time and the built-in panel's `disp_adma`/`disp_cpu` at ~49 s. A black
  screen during the ladder is therefore **ambiguous**: a reset is followed by
  the Apple logo and macOS login; a display power-off stays black. M1 will keep
  filming to the 120 s bound either way and report both cases.
* Ignored receipt `build/native-intake/receipts/boot034-attempt15.json`,
  record `build/native-intake/results/boot034-stage-b-attempt15.json` and
  wrapper `build/native-intake/run-attempt15.py` retain the hashes.
* **Ready for Stage B attempt 15** after publication. **Native boot034 and
  live checks NOT RUN at readiness.** hv003 and the PMGR probe are separate
  tracks: M1 offline readiness for them is not yet done.
* Next: one filmed RAM launch; keep filming to reset, `ladder complete` or
  120 s from handoff; then Macintosh HD. No retry/reinstall/settings change.


### Current M5 handoff — PMGR probe: per-domain power-off question via the proxy (NOT RUN)

* **Why:** attempt 14's silent reset came about 5.6 s after Linux's genpd
  `sync_state` powered off the unclaimed boot-on PMGR domains. Boot034 tests that
  inside Linux; the m1n1 proxy can ask the same question one domain at a time, in
  seconds, with no kernel boot.
* **Tool:** `native/probe/pmgr_probe.py` (private; new files only). `read` is
  strictly read-only (it sends no write request, not even ProxyUtils' heap
  bookkeeping); `plan` shows what stage 2 would accept or refuse, offline from a
  stage-1 JSON file; `cycle` powers named domains off in order and back on in
  reverse, announcing each write first so a lost link names the domain.
* **Real table:** the sanitized macOS ADT export has 661 PMGR device records (338
  virtual, 323 with a power-state register, 118 critical, 205 not, 33 of those
  `notify_pmp`). CPU cores, cluster managers and the interrupt controller are
  **not** flagged critical there, so the tool refuses them by name, plus the
  link closure (UART0 and every ATC USB device with all parents, 19 domains).
* **Verified offline:** 85 tests (fake ADT and proxy, the real 661-record table,
  22 planted-bug mutants all caught); end-to-end CLI run against a real-shaped
  stage-1 file. **No live run.**
* **M1 next:** `tools/m1n1-client/pmgr-probe-instructions.md`: offline
  readiness, then stage 1 (read-only, one short lab session); stage 2 only after
  separate human approval. First experiments: one non-`notify_pmp` leaf (control)
  and one `notify_pmp` leaf (Hypothesis: unreported PMP state changes matter).
  * RAM-only; no retries; no security, volume or installed-m1n1 change.
  * Never contribute any of it upstream.

### Current M5 handoff — hv003: hardened chainload with breadcrumbs (NOT RUN)

* **Why:** hv002's hypervisor change set has still never executed; its session
  stopped at the m1n1→m1n1 chainload (restored logo, no USB). The M5 review
  (`native/hv/hv002-chainload-analysis-2026-10-14.md`) ranks: a misaligned
  literal in our copy stub (Likely, not hardware-confirmed), the Python
  six-blob/whole-ADT flow that Asahi's own chainload does not use, overlapping
  regions, early re-initialization on t6050.
* **hv003** (patches 0001 unchanged + `0002-ilinux-hv-t6050-hv003-crumbs.patch`,
  VM job 037, `m1n1-hv.bin` `369b104a…42c8`):
  * padded-literal copy stub; SEPFW-only relocation with a 16-byte in-place ADT
    patch applied last and reverted on failure; `top_of_kernel_data` never
    below the live heap;
  * read-only layout gate and a raw ADT parser (`adt_patch.py`);
  * breadcrumb strip on the M5 screen: host marks, a stub entry mark and bar,
    16 early m1n1 steps (the M5 has no reachable UART);
  * ladder: `--layout-only`, `--chainload-only`, `--control stock`, full run;
    new-instance proof by `boot_args` pointer;
  * launcher no longer echoes the target's console (it carried the device
    serial); open errors carry no device paths.
* **Verified offline:** 168 chainload, 76 launcher, 10 ADT and 13 crumb tests
  (267 under `discover -s native/hv`), 37 native launcher tests; stubs
  assembled with clang and emulated; a 71-bug mutation sweep (2 survivors, now
  covered). Final-binary call order checked; DAPF guard passes on the image.
  **No rung has run.**
* **Release:** `native-j716c-hv003`, archive `ilinux-j716c-hv003.tar.gz`
  SHA-256 `392433747cb23dbd44df92b7b24279fb559f243ece30ba6e29efc0b842722c05`.
  Guests: boot033 and boot034 (selected by Image digest). hv001 and hv002 are
  superseded; do not run them.
* **M1 next:** `tools/m1n1-client/hv-instructions.md`: offline readiness, then
  rung 1 `--layout-only`, rung 2 `--chainload-only`, rung 3 (only if 2 fails)
  `--control stock`, rung 4 the full run. One human-started rung per boot; power
  off between rungs; film the top-left corner of the M5 screen; stop at the
  first failing rung. Independent of boot034 / attempt 15 (either order).
  * RAM-only; no retries; no security, volume or installed-m1n1 change.
  * Never contribute any of it upstream.

### Current M5 handoff — boot034 / attempt 15 ready for M1 intake

Boot034 / attempt 15 prepared after reviewing M1 attempt 14 (`a4269bb`) and the
hv002 chainload stop (`fd473b1`). The hypervisor is blocked at the chainload, so
this attempt does not use it. Exact source shows genpd **sync_state powers off
every unclaimed boot-on PMGR domain without honoring `pd_ignore_unused`** (the
flag guards only the later sweep that attempt 14 printed). In the Stage-B DT,
152 of 188 domains are unclaimed and not always-on; `of_platform_sync_state_init`
did 5 ms of work 5.6 s before the reset. Boot034 makes sync_state honor the flag,
logs every real power-off, and after ≈ 20 s kernel time releases the unclaimed
domains one per 500 ms, naming each first, so any reset is attributable.
Only Image changes. Exact-source ASan/UBSan model (5 mutations caught), VM build
with identical config and ELF/Image roundtrip, linked-code review and exact-image
generic one-CPU PID1/60s liveness PASS. **Native boot034/live checks NOT RUN.**
No launcher or reviewed-digest change. M1 next: `tools/m1n1-client/stage-b-instructions.md`,
offline readiness, one human-started filmed attempt 15 (keep filming past 60 s:
stop on reset, `ladder complete` or 120 s) and return to Macintosh HD.
Evidence/code: `kernel/experiments/genpd-sync-state/`.

### Current M1 result — hv002: census v2 PASS, Session 2 stopped at chainload, 2026-10-14

* Census v2 PASS for hv002 at 22:58:05 UTC: all 19 registers readable, ECV=1,
  `VM_TMR_FIQ_ENA_EL2` ENA_V=1 ENA_P=1 (expected), PMCR0/IPI_SR readable.
  Returned to Macintosh HD.
* **Session 2 (hv002) stopped at the chainload.** Package, target, register
  preflight, ADT/boot-blob copy and `Preparing to run next stage` all passed.
  Then `Waiting for reconnection...` for about 80 s and
  **`STOP: UartTimeout Reconnection timed out`**.
* No m1n1 USB device on the M1 afterwards; the vUART never returned (log
  empty). The M5 sat at a black screen with the Apple logo (the restored iBoot
  logo) until powered off.
* **Hypervisor and guest NOT STARTED.** hv002 likely stopped before its
  framebuffer init, in early m1n1 re-initialization; cause unknown. Report and
  suggestions (stock boot021 chainload as a discriminating test, early
  on-screen progress codes): `native/hv/hv002-session2-2026-10-14-result.md`.
* User confirms return to Macintosh HD; fresh policy/default NOT CHECKED.
  No retry.


### Historical M1 readiness — hv002 sessions offline PASS, 2026-10-14

* Pulled/read M5 handoff `6e58ccd`, `native/hv/README.md` and
  `tools/m1n1-client/hv-instructions.md`. README file hashes 8/8 match.
* Release `native-j716c-hv002`: archive 2,134,659 bytes, SHA-256
  `c79ffded48bebc580734918c1540fd589937d5440e2a385a65186c801f2c4254`, verified
  before extraction. Four regular members; `m1n1-hv.bin`, `System.map` and the
  symbol list match `hv-manifest.json`. Guest Image is unchanged boot033.
* **Offline PASS:**
  * 33 hv tests, none skipped; `TimerModelTests` compiled with cc
    (ASan/UBSan) on M1, and four `PackageTests` ran on the real packages;
  * 37 launcher tests;
  * client-venv imports;
  * offline `hv_launch.py`: Package PASS (boot033 guest + hv002 m1n1),
    OFFLINE ONLY, exit 0.
  * Client pin clean at `57a9339`.
* **M1 independent review:**
  * census v2 (`hv_regs.py`) does guarded reads only;
  * the patch source-masks expired guest timers (`CNTx_CTL_EL02.IMASK`),
    injects HCR_VF, and hides the mask from guest CTL reads; guest CTL writes
    and CVAL/TVAL re-arms lift it;
  * both guest timers are zeroed before entry;
  * the UPMCR0/UPMSR block is gated on `uncore_version`.
* Ignored record `build/native-intake/results/hv002-readiness.json`.
* **Ready for Session 1 (census v2)** after publication. Session 2 (hv002)
  only after a census PASS and a separate human start. **Live checks NOT RUN
  at readiness.**


### Current M5 handoff — hv002 replaces hv001 (NOT RUN)

* **Why:**
  * The H1 census correctly blocked hv001. `VM_TMR_FIQ_ENA_EL2` has both
    guest-timer FIQ enables set and cannot be written at EL2, while hv001 only
    polled guest timers.
  * An M5 review also found that the HV FIQ handler read the uncore PMU
    registers `UPMCR0`/`UPMSR` unconditionally. m1n1's own code skips them on
    M4/M5, so the census could not cover them.
* **hv002** (patch `native/hv/0001-ilinux-hv-t6050-hv002.patch`, +155/−7,
  pin `57a9339`, VM job 035):
  * guest timers are masked at their source (`CNTx_CTL_EL02.IMASK`) and
    delivered as virtual FIQs;
  * the mask is hidden from the guest through the ECV timer traps;
  * the HV refuses to start only without ECV;
  * both guest timers are turned off before entry;
  * uncore reads are gated on `cpu_features->uncore_version`.
* **Verified offline:**
  * disassembly of `hv_exc.o` and of `hv_init`/`hv_start` in the final binary;
  * a timer model test that compiles the exact patch code with ASan/UBSan
    against simulated stuck-on FIQ enables (8 scenarios, and 3 deliberate
    mutations are caught);
  * 33 hv tests PASS.
* **Census v2:** 19 registers; set enables no longer block, while missing
  ECV or a trapped `PMCR0`/`IPI_SR` does. `hv_launch.py` repeats it in-boot
  before the chainload.
* **Release:** `native-j716c-hv002`, archive
  `c79ffded48bebc580734918c1540fd589937d5440e2a385a65186c801f2c4254`.
  hv001 is superseded; do not run it.
* **M1 next:** `tools/m1n1-client/hv-instructions.md`.
  1. Offline readiness.
  2. **Session 1:** census v2.
  3. **Session 2:** hv002, only after a census PASS and a separate human
     start.
  * RAM-only; no retries; no security, volume or installed-m1n1 change.
  * Never contribute any of it upstream.

### Current M1 result — H1 census BLOCKED for hv001, 2026-10-14

* One read-only census at readiness `8267222`, 22:24:14 UTC: exit 2, under
  one second. Chip, marker and no-secondaries gates passed; 15 guarded reads,
  no writes, no retry.
* **All 15 registers readable.** That includes the unguarded `hv_start()`
  reads (AMX/APVMKEY/APSTS/ACTLR/SPRR/GXF/CNTHCTL); ECV=1.
* **BLOCKED:** `VM_TMR_FIQ_ENA_EL2` reads **ENA_V=1 ENA_P=1**. The enable bits
  are already on and the register traps on write at EL2 (attempt 5), so hv001
  refuses to start. Guest timers `CNTV/CNTP_CTL_EL02` read ctl=7 (enabled,
  masked, expired).
* **hv001 Session 2 NOT RUN.** User confirms return to Macintosh HD; fresh
  policy/default checks NOT CHECKED. Report and revision direction (mask guest timers at
  the architectural source with a shadowed CTL via the ECV traps):
  `native/hv/census-2026-10-14-result.md`.


### Historical M1 readiness — hv001 sessions offline PASS, 2026-10-14

* Pulled/read M5 handoff `4814b6f` (hv001 prepared in `ee5b824`), `native/hv/README.md`
  and `tools/m1n1-client/hv-instructions.md`. All six README file hashes match.
* Release `native-j716c-hv001`: archive 2,134,653 bytes, SHA-256
  `c659462c77df8a56979aff5f5f5596cbbdb49a6bbe0eaef5d2ecfd9bd6f4ebb1`, verified
  before extraction. Four regular members; `m1n1-hv.bin` `6d031661…85ac`,
  `System.map` and the symbol list match `hv-manifest.json`. Guest Image is the
  unchanged boot033 `250d9ff5…eb15`.
* **Offline PASS:**
  * 28 hv tests; PackageTests ran against the real packages, not skipped;
  * 37 launcher tests;
  * client-venv imports (m1n1.hv, bootmem, tgtypes, proxyutils, construct,
    serial);
  * offline `hv_launch.py`: Package PASS, OFFLINE ONLY, exit 0, with bootargs
    `console=ttySAC0,115200` before `console=tty0` and
    `earlycon=s5l,0x505200000`.
  * Client pin clean at `57a9339`.
* **M1 independent review:**
  * `census.py` does reads only: 15 `ProxyUtils.mrs` calls under the
    exception guard, no `msr`, a 120 s alarm, and chip/marker/no-secondaries
    gates.
  * The m1n1 patch is limited to: no secondary start on T6050; a read-only
    `VM_TMR_FIQ_ENA_EL2` gate that refuses to start if it is enabled; polled
    guest timers in `hv_update_fiq`; and private op `0x7f0` (cache, tunables,
    clock and DAPF without USB/PCIe).
* Ignored record `build/native-intake/results/hv001-readiness.json` holds the
  hashes and results.
* **Ready for Session 1 (read-only register census)** after publication.
  Session 2 (hv001) only after a census PASS and a separate human start.
  **Census and hv001 live checks NOT RUN at readiness.**


### Reviewed M5 handoff — hv001 private hypervisor sessions (NOT RUN)

* **What:** a private m1n1 hypervisor runs the **unchanged boot033** payloads
  at EL1. The kernel log streams to the M1 on the vUART (USB interface 3), and
  Ctrl-C gives an HV shell with `System.map` backtraces and optional PMGR
  MMIO tracing. It answers attempt 14's silent reset with live evidence
  instead of photos.
* **m1n1 patch** `native/hv/0001-ilinux-hv-t6050-single-cpu.patch` (+53/−1,
  7 files, pin `57a9339`):
  * the HV starts no secondaries on t6050;
  * `VM_TMR_FIQ_ENA_EL2` is only read (the HV refuses to start if it is
    enabled), and guest timers are polled;
  * private op `0x7f0` runs kboot's clock/tunable/cache/DAPF steps without
    USB/PCIe init.
* **Build and release:** VM job 034. Release `native-j716c-hv001`, archive
  SHA-256 `c659462c77df8a56979aff5f5f5596cbbdb49a6bbe0eaef5d2ecfd9bd6f4ebb1`.
* **Validation:** reviewed twice. 28 offline hv tests PASS on M5, and
  `native/boot` is unchanged. Design, review fixes and risks:
  `native/hv/README.md`.
* **M1 next:** `tools/m1n1-client/hv-instructions.md`.
  1. Offline readiness, including the client-venv import check (not
     verifiable on M5).
  2. **Session 1:** read-only register census, one human-started boot.
  3. **Session 2:** only after a census PASS and a separate human start, one
     hv001 RAM session.
  * Each session ends with power off and return to Macintosh HD.
  * No retries; no security, volume or installed-m1n1 change.
* **Never contribute any of it upstream:** m1n1/Asahi forbid LLM-derived
  work. Private use is user-authorized.
* Attempt-14 follow-ups stay open in parallel: M5 read-only return checks,
  then boot034.

### Current M1 result — attempt 14 reaches native PID 1, then silent SoC reset

* One boot033 RAM attempt at readiness `994b62f`, M5 handoff `b76ab6b`.
  **Controller exit 0, 10.74 s**; handoff 2026-10-14T19:50:04.394670Z. Target,
  marker, no-secondaries, GPIO ADT, final hardware DT, DAPF layout/correction,
  framebuffer descriptor and kboot reply PASS.
* **Native diagnostic PID 1 reached for the first time.** `Run /init` at
  3.152165 s; `PID 1 reached` at 3.166444 s. DT model `Apple MacBook Pro
  (16-inch, M5 Max)`, MemTotal 132456096 kB, CPU online mask `0`.
  `[diag] heartbeat 000/001 online_cpus=1` at 3.230083 and 8.233382 s.
* **GPIO repair works on hardware.** `pinctrl@2881e4000`: cache 61/61/0, IRQ
  handoff 61/7 masked=1, returned 0 after 103600 us. Main `pinctrl@29c000000`:
  cache **221/216/5**, IRQ handoff 221/7 masked=0, returned 0 after 264934 us.
  ASC mailbox probe returned 0 after 4570 us. Panel D 0052 decodes to
  `mbox@419608000` and D 004C to `iommu@41dc50000` (SART); both use PMGR
  `power-controller@140`.
* Late init: `clk: Not disabling unused clocks`, `PM: genpd: Not disabling
  unused power domains`, `of_platform_sync_state_init` returned 0 after 5017 us.
* **Silent SoC reset at kernel ~8.77 s**, about 0.5 s into the second 5 s sleep.
  The screen went to black within one video frame with no kernel, panic,
  watchdog or reboot text. Apple logo about 3.4 s later, then macOS login at
  3:50 PM; the user reports the default OS. **60-second liveness NOT REACHED.**
  Cause unknown. m1n1 had disabled both watchdogs before handoff (on screen).
* Media: `IMG_2669.mov`, 34.297 s at 30 fps, reviewed locally (AVFoundation
  frames, brightness traces, upscaled crops). It stays in ignored
  `build/native-intake/inbox/`; no still photo; review images deleted.
* **Attempt 14 consumed.** Report: `native/boot/stage-b-2026-10-14-attempt14-result.md`.
  M5 next: read-only return checks, then the reset trigger. Ranked hypotheses
  in the report: PMGR power-off at sync_state despite `pd_ignore_unused`,
  ANS mailbox/SART side effects, and the second idle period. Fresh policy/
  default NOT CHECKED. No retry or settings changes.


### Historical M1 readiness — boot033 / attempt 14 offline PASS, 2026-10-14

* Pulled/read M5 handoff `b76ab6b`, the attempt-14 checklist and scheduler-RAM
  evidence. Archive **16,723,317 bytes**, SHA-256
  `6cbf5d1396ddd2b5f79255e65c6c776f8122921b06327271e1102f7b7f0d55cd`,
  verified against Git before extraction; 14 regular members, no absolute or
  parent paths. **13-file intake and offline launcher PASS.**
* **102 M1 offline cases PASS** (37+10+6+16+5+19+2+6+1), all exit 0; synthetic
  transport only. Image SHA-256
  `250d9ff58e5f5397e1bb54682f2bd8a7a679f44f2863629ef7b89ec45ad1eb15`;
  Stage-B DT SHA-256 unchanged
  `4b3adee52465b809e9c8a1946b7610c63f1ae3c0b24f7334cd485260da84adce`.
* Versus retained boot032 only Image and package-manifest metadata differ.
  Six reviewed controller digests match the checklist; client pinned clean at
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`. Installed boot021 unchanged.
* Fresh ignored receipt `build/native-intake/receipts/boot033-attempt14.json`,
  record `build/native-intake/results/boot033-stage-b-attempt14.json`/`.md`
  and one-shot wrapper `build/native-intake/run-attempt14.py` retain payload,
  source, procedure and receipt hashes.
* **Ready for Stage B attempt 14** after publication. Human reports the M5
  proxy already running; recording starts before launch and continues through
  the stop criterion. M5's post-attempt-13 protection prerequisite applies.
  **Native boot033/live checks NOT RUN at readiness.**
* Next: one documented RAM launch; capture all four panel rows (S is now
  watchdog-sampled), GPIO counts/errors, PID 1/one CPU/60-second liveness;
  stop at panic/rejection, userspace milestone or 120 seconds after handoff,
  then Macintosh HD. No reconnect/retry/reinstall/settings/volume changes.


### M1 proposals for M5 — boot034 diagnostics and hypervisor study, 2026-10-14

* User asked M1 to record these for M5. They are proposals, not authorization;
  M5 owns boot034 and decides. Evidence: boot032 `kernel.config` (unchanged in
  boot033) and attempt reports 9-13.
* **Observation gap.** `DETECT_HUNG_TASK`, `WQ_WATCHDOG`, `SOFTLOCKUP_DETECTOR`,
  `PROVE_LOCKING` and `DRM_PANIC` are not set. The text console is fbcon on
  simpledrm with `DRM_FBDEV_EMULATION`/`FB_DEFERRED_IO`, so screen text likely
  depends on a system-workqueue damage worker (Likely, not traced). A workqueue
  stall would freeze the text while the directly painted panel keeps updating,
  consistent with attempt 13. Attempt 12 reached W04/D0059/B73; attempt 13 never
  showed the worker start (W00/D0000). One run per build cannot separate a
  build effect from run-to-run variation.
* **Proposal 1, config and command line only.** Enable the hung-task detector
  (10-15 s), workqueue watchdog (~10 s) and soft-lockup detector, optionally
  lockdep for one diagnostic build. Make a detected stall panic with a blocked-
  task dump, and draw panic output without the workqueue: DRM panic `kmsg`
  screen and/or the direct-scanout early console kept registered. `panic=0`
  keeps it on screen for one photo of the stuck task's symbolic stack.
* **Proposal 2.** Build `PINCTRL_APPLE_GPIO` as a module; diagnostic init loads
  it after PID 1 and prints `/proc/<pid>/stack` and blocked tasks if loading
  stalls. That reaches the userspace gate and captures the exact GPIO stall in
  one boot. The probe moves; it is not skipped.
* **Proposal 3.** Read-only offline comparison with the community
  `betizzel/omarchy-m5` t6050 DT and GPIO handling (reported single-core
  userspace on M5 Pro; unverified, untrusted data, never executed).
* **Hypervisor study.** `research/m1n1/hv-linux-guest-feasibility-2026-10-14.md`:
  pinned m1n1's hypervisor is not usable unmodified on t6050. `hv_init()`
  starts all secondaries, and `hv_update_fiq()` writes `VM_TMR_FIQ_ENA_EL2` on
  every guest exit (the attempt-5 UNDEF). Feasible later with a private,
  RAM-chainloaded m1n1 change set; the first step would be a read-only
  register census session. Not the next step. LLM-produced under m1n1's AI
  notice: private use only, nothing upstream or to Asahi channels.


### Reviewed M5 handoff — boot033 / attempt 14 ready for M1 intake

Boot033 / attempt 14 prepared after reviewing M1 attempt 13 (`9a045cf`).
Attempt 13 has no attributed GPIO result or native PID 1; cause remains unknown.
Confirmed own-code overhead: scheduler hooks repaint all eight diagnostic lanes.
Boot033 keeps scheduler state in RAM and samples S from the bounded watchdog;
S is no longer an immediate checkpoint display. Only Image changes. Preserve
boot032 GPIO exclusions, installed boot021, all gates and the current lab entry.
Full Image/ELF roundtrip, actual-hook ASan/UBSan, 102 controller cases, 13-file
intake and 13+8 intake/evidence cases PASS. Linked hook: 14 instructions, no
calls. Exact Image/initramfs generic VM reaches PID 1/one CPU/60s liveness at
60.192455 kernel seconds (60.368s wall); native boot033/live checks NOT RUN.
User reports post-attempt-13 Full/Permissive; fresh exit codes not supplied.
M5 read-only original-root/build/FileVault/SIP/staged-m1n1 checks PASS, superseding
pending return status below; default/installed object/authenticated-root were
not rechecked. No boot/security/volume changes. M1 next: current Stage-B checklist,
offline readiness, one human-started filmed attempt 14, stop by milestone/error/
120s from handoff and return to Macintosh HD. No setup/retry or extra M5 approval
loop. Claude workflow: `native/boot/claude-workflow.md`. Evidence/code:
`kernel/experiments/scheduler-ram-only/`. Native userspace still gates Linux
control/RAM root/configuration-agent work, then Omarchy and hardware performance.


### Historical M1 result — attempt 13 (return resolved above)

* One boot032 RAM attempt at published readiness `8f2c908`, M5 handoff `f2b2c4d`.
  **Controller exit 0, 10.589 s**; UTC 17:56:51.492019–17:57:02.081153,
  handoff 17:57:01.852238. Boot021 marker, live GPIO ADT exclusions, final
  hardware/GPIO DT, both DAPF checks/readback, framebuffer/readback and kboot
  PASS. USB closed; no extra handshake, reconnect, retry or settings change.
* Reviewed **40.13-second IMG_2665.mov** and detailed **IMG_2666.jpeg**.
  Native Linux/Tux, J716c/t6050 **EL2 cpus=1**, **ticks=25**, IRQ/FIQ masks0,
  pending=1/strip=1/display=6 are readable. Timer PASS/phys/virt text, printed
  phase digits and console_setup are covered/unobserved, not copied from prior boots.
* Literal final photo: **P05 / W00 H06 / D0000 I000 / B00 C0000**;
  S mixed/repainting and **NOT CONFIRMED**. Video shows P0D at 10s then P05;
  H00/01/02/04/05 sampled at 10/15/20/30/39.98s, photo H06. W/D/I/B/C remain
  zero in these samples. S06 clearly sampled at 30s; no stable final S assigned.
* Offline decoder returns unknown device/no marked operation. I000 is numeric 0,
  not evidence of a pin 0 read without attributed D/C and B91. P05 is the first
  work-flush boundary by source; no nonzero device or GPIO checkpoint observed.
  The six-heartbeat watchdog is bounded; H06 is not userspace liveness or proof
  of a later timer failure. Exact blocked PC/task/cause remain unknown.
* GPIO cache/IRQ counts, retries/returns/errors, readable watchdog stack and
  scheduler summary **NOT OBSERVED**. Do not import attempt12 NUB success.
  **PID 1/userspace online_cpus=1/60-second liveness NOT OBSERVED**; no explicit
  panic seen. Console stays at partly covered reschedule text while panel changes.
* Reviewed video times 0/5/6/7/8/9/10/15/20/30/39.98s; no 60/90s or full 120s
  coverage. Photo adds H06/detail, not duration. Stop deadline communicated as
  **1:59:02 p.m. Eastern**, return instructed after deadline. **Macintosh HD
  return PENDING HUMAN CONFIRMATION**; fresh policy/default NOT CHECKED.
* **Attempt 13 consumed.** Detailed report:
  `native/boot/stage-b-2026-10-14-attempt13-result.md`. M5 next: read-only review
  after confirmed return and offline worker/scheduler/console analysis. No
  GPIO repair or pin-fault claim. Preserve installed boot021, pin and gates.


### Historical M1 readiness — boot032 / attempt 13 offline PASS, 2026-10-14

* Pulled/read M5 handoff `f2b2c4d`, Stage-B attempt-13 checklist and reserved-GPIO
  evidence/validation. Archive **16,723,345 bytes**, SHA-256
  `001ef39cd64d8fef7c3779c5169c00726474d6ebc56cea90b9f6f5d9c9bd0500`,
  verified against Git before safe extraction. **13-file intake and offline
  launcher PASS**; source/controller/decoder hashes and clean client pin PASS.
* **102 M1 offline cases PASS** (37+10+6+16+5+19+2+6+1), all exit 0; synthetic
  transport only. Image SHA-256
  `589c33577d1bc2ddeb2f96e544f87b9ead6bc52e774410567170a7235dd70bcb`;
  Stage-B DT SHA-256
  `4b3adee52465b809e9c8a1946b7610c63f1ae3c0b24f7334cd485260da84adce`.
* Independently compared retained boot031: only Image, Stage-B DT and manifest
  metadata differ. Semantic DT difference is exactly main GPIO reserved ranges;
  node paths and 286 public IDs retained. Installed boot021 unchanged; client
  pinned clean at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
* Fresh ignored receipt `build/native-intake/receipts/boot032-attempt13.json`
  and result `build/native-intake/results/boot032-stage-b-attempt13.json`/`.md`
  retain payload/source/procedure/receipt hashes. Sanitized one-shot wrapper
  includes the new GPIO gate checkpoint and safe error-frame handling.
* **Ready for the authorized Stage B attempt 13** after publication. Human
  reports proxy running and recording; requested entire panel including I and
  recording through stop. M5 post-attempt-12 protection prerequisite already
  PASS. **Native boot032/live checks NOT RUN at readiness.**
* Next: one documented RAM launch; capture P/S/W/H/D/I/B/C, actual GPIO
  cache/IRQ counts and errors/returns, PID 1/one CPU/60-second userspace liveness;
  stop at panic/rejection, userspace milestone or 120 seconds after handoff,
  then Macintosh HD. No reconnect/retry/reinstall/settings/volume changes.


### Reviewed M5 handoff — boot032 / attempt 13 reserved-GPIO repair prepared

* Consumed M1 attempt 12 (`f3218fd`): final P05/S09/W04/H02/D0059/B73/C0059
  places the main GPIO controller at cache initialization. NUB IRQ handoff
  61/7/1 and return 0 observed; main return and native PID 1 remain unobserved.
* Fresh user post-attempt-12 JSON PASS: original **Full**, lab **Permissive**,
  both exits 0. Independent M5 read-only root Macintosh HD/build 25G83/
  FileVault/SIP and unchanged staged m1n1 checks PASS. No host settings changed;
  default/installed boot object/authenticated-root were not independently
  re-queried. The report's pending policy check is superseded.
* Read-only GPIO metadata gives excluded pins **5,6,7,112,141**, 221 pins,
  7 groups. REA + original bytes/LLVM confirm Apple's in-body skip behavior.
  Exact boot031 Linux source/REA/linked bytes show its cache scans declared
  pins without exclusions. This is a supported **candidate cause**, not a
  native fault PC. Start pseudocode remains manual-review; prior init pcode
  remains rejected. No proprietary code or binary published.
* Boot032 adds validated DT reserved ranges, explicit permitted cache defaults,
  sparse-cache/access checks, GPIO/pinmux/IRQ exclusions, and rejection of
  initially pending excluded IRQs before parent installation. New I lane
  records pin index; B90–93 refine progress. Main expected cache is 221/216/5.
  All 286 public D/C IDs remain. Only Image and one Stage-B DT property change
  among payloads; installed boot021/config/initramfs/fixed args/gates remain.
* Full Image/ELF roundtrip and exact source-recipe reproduction PASS. Actual
  helper/callback ASan+UBSan tests: 216 allowed reads, zero forbidden MMIO,
  errors/IRQ masks/8 geometries; 8-lane renderer/3 fonts PASS. GPIO binding and
  selected Stage-B schema PASS. **102 controller tests**, **13 intake files**,
  **13 member + 8 evidence tests PASS**. Exact Image/initramfs diskless,
  networkless, one-CPU VZ reaches PID 1 and 60s liveness at **60.192890 s**.
  Native GPIO/MMIO is not exposed by VZ; no native performance/energy claim.
* **Native boot032 / attempt 13 / live checks NOT RUN.** M1 follows
  `tools/m1n1-client/stage-b-instructions.md`: verify private release
  `native-j716c-boot032`, publish offline readiness, then one filmed human-started
  attempt and Macintosh HD return. No extra approval round trip, provisioning,
  Recovery, new skip, retry or settings/volume/security changes.
* Record all panel lanes including I, actual cache/IRQ counts, errors/probe
  return and PID-1/one-CPU/60-second liveness separately. Native userspace is
  the next gate before Linux-side control/input/RAM root and the configuration
  agent's Omarchy work. Evidence: `kernel/experiments/gpio-reserved/README.md`
  and `validation.json`. All test VMs stopped before handoff.

### Historical M1 result — attempt 12 main-GPIO cache boundary; return PASS, 2026-10-14

* One boot031 RAM attempt at readiness `83f0f20`, reviewed M5 handoff `cd9ac3f`.
  **Controller exit 0, 10.545 s**; UTC 16:19:37.850798–16:19:48.396252,
  handoff 16:19:48.168614. Boot021 marker, final hardware DT, both DAPF
  checks/96-byte correction/readback, 16-byte framebuffer descriptor/readback
  and kboot reply PASS. USB closed; no retry/reconnect/settings changes.
* Reviewed **40.163333-second video** and detailed **IMG_2664.jpeg**. Native Linux
  reports **J716c/t6050 EL2 cpus=1**, timer **PASS/25 ticks**, phys=1/virt=7,
  irq_masked=0/fiq_masked=0, pending=1/strip=1/display=6 and printed phases
  **1→10→11→12→13→2→3→4→5**. Four panel rows visibly render.
* Final literal **P:05 S:09 / W:04 H:02 / D:0059 / B:73 C:0059**, at video
  25/30/40.013333 s and photo. Offline decode: **/soc/pinctrl@29c000000**,
  **GPIO bounded register-cache initialization**. This narrows the boundary
  beyond prior B63; no exact blocked instruction/register/cause established.
* Earlier **/soc/pinctrl@2881e4000** reports **pins=61 parents=7 masked=1**
  for t6050 IRQ handoff, then **returned 0 after 1918983 usecs**, retry 1 end.
  Main-controller return/counts/errors NOT OBSERVED. First GPIO success does
  not establish all GPIO/peripheral support or validate the proposed hang cause.
* Watchdog 1: phase5/worker4/device1/**ticks=1285**; scheduler7/selections1337/
  prev10/next12/current12/**kworker/u4:0**, events_power_efficient. Photo provides
  14 symbolic frames/offsets through timer softirq/IRQ exit. Later device2/
  **ticks=2565**, selections2620/prev10/next38/current38/**kworker/u4:1**.
  Lower stack/prefixes obscured; first watchdog stack is not a proven B73 stack.
* **PID 1/userspace online_cpus=1/60-second liveness NOT OBSERVED**; no explicit
  panic seen. Clip sampled at 0/5/10/15/18/20/22/25/30/40.013333 s; no 60/90s
  or full 120s coverage. Photo adds detail, not elapsed coverage. Early S digits
  remain unconfirmed. Human confirms **Macintosh HD desktop return PASS**;
  later screen changes not separately reported, fresh policy/default NOT CHECKED.
* **Attempt 12 consumed.** Stop/return instructed at **12:21:48 p.m. Eastern**.
  Detailed evidence: `native/boot/stage-b-2026-10-14-attempt12-result.md`.
  M5 next: read-only return checks and offline analysis of the exact main-GPIO
  cache path. Preserve installed boot021, client pin, gates and fixed arguments.
  No new live attempt until updated instructions and human start.


### Historical M1 readiness — boot031 / attempt 12 offline PASS, 2026-10-14

* Pulled/read M5 handoff `cd9ac3f`, Stage-B attempt-12 instructions and GPIO
  handoff evidence/validation. Archive **16,724,870 bytes**, SHA-256
  `73ad67d17c78da9ef2eeec63122e52271e8a9521120add8d60588a6585ab9246`,
  verified before extraction. **13 intake files**, offline launcher, reviewed
  controller/source hashes and public decoder tables PASS. Image SHA-256
  `09d3cc302da20ef53c41bec3324d702b249a729a55e3799b5676618034bff37d`.
* **90 M1 offline tests PASS** (37+6+16+5+19+2+4+1), all exit 0; synthetic
  transport only. Clean m1n1 client remains pinned at
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`; installed boot021 unchanged.
  Only Image/package manifest differ from retained boot030. System Python's
  unsupported tar filter option stopped initial extraction; revalidated archive
  and safe regular-file/directory paths, then extraction/intake succeeded.
* Fresh ignored receipt `build/native-intake/receipts/boot031-attempt12.json`
  and result `build/native-intake/results/boot031-stage-b-attempt12.json`/`.md`
  retain source/procedure/controller/payload/receipt hashes. Sanitized wrapper
  prepared with a zero-attempt guard and unchanged documented launcher arguments.
* **Ready for the authorized Stage B attempt 12** after publication. Human
  reports proxy running and recording. M5 post-attempt-11 return/protection
  prerequisite already PASS; no repeat approval or setup. **Native boot031 and
  live checks NOT RUN at readiness.** Generic VM results do not validate GPIO.
* Next: one filmed RAM launch; capture literal four-row panel, GPIO stages and
  actual counts/errors/returns, Linux PID 1/one CPU/60-second liveness. Stop on
  rejection/panic, userspace liveness milestone or 120 seconds from handoff;
  return to Macintosh HD. No retry/reconnect/reinstall/settings change.

### Reviewed M5 handoff — boot031 GPIO cache/IRQ handoff repair; attempt 12 prepared

* Reviewed M1 `f35efa5`: attempt 11 controller PASS and final **P05 S09 W04 H02
  D0059 B63 C0059** identify `/soc/pinctrl@29c000000` at its callback. Earlier
  NUB pinctrl returned 0. Exact blocked PC/IRQ storm/userspace remain unproven.
* Exact Linux REA/source/ELF/LLVM covers **392 instruction words**, 331 linked
  nonrelocated matches and 61 separately reviewed relocation words. Two Apple
  GPIO routines add **222 original-byte/LLVM-checked words**. Initialization
  pseudocode fails the cross-boundary gate; only bounded, independently verified
  instructions support its status-clear observation. No proprietary code copied.
* Implemented **t6050-only** geometry validation and cache length from declared
  pins (AP 221 rather than 512), plus gpiolib `init_hw` masking of inherited input
  IRQs, MMIO readback and valid-bit pending-status clears before parent enable.
  Outputs/mux/pulls/group/data preserved. Locked active pins/errors fail visibly;
  no lock override or new driver skip. Seventeen new B checkpoints distinguish
  cache/pinctrl/GPIO/handoff stages. **Candidate hang fix, native NOT RUN.**
* Full Image/ELF roundtrip and unchanged config PASS. Actual helper/geometry
  ASan/UBSan regressions cover sizes/partial words/field preservation/error paths,
  baseline over-read and pending-IRQ behavior. **90 controller cases**, 13-file
  intake and exact one-CPU/4 GiB diskless/networkless VZ boot PASS: all phases,
  PID 1, online_cpus=1 and 60s liveness at **60.189741 s**. VZ does not exercise
  t6050 GPIO/AIC/MMIO or establish native efficiency/peripheral functionality.
* Fresh post-attempt-11 user JSON original **Full** / lab **Permissive**, exits 0.
  Independent root **Macintosh HD**, build **25G83**, FileVault/SIP enabled and
  staged m1n1 checksum unchanged. This resolves the report's pending return.
  Default/installed object/authenticated-root not independently re-queried.
* Only RAM Image changes. Installed boot021/client pin, DT/config/initramfs,
  args/single skip/hardware gates/current entry stay. No boot/security/volume/
  default/firmware changes. Preserve all prior attempts and packages.
* All owned build/REA/test VMs stopped; both shared quiet locks released.
* Next: M1 verifies private **native-j716c-boot031**, publishes readiness, then
  one human-started filmed **attempt 12**. Record GPIO handoff counts/errors,
  literal panel and decoded D/C/B, probe return and PID-1/60s liveness, then
  Macintosh HD within the existing bound. No provisioning/reinstall/automatic
  retry or extra M5 approval loop. Native userspace precedes Linux control/input
  and the configuration agent's Omarchy work. See the current Stage-B checklist
  and `kernel/experiments/gpio-handoff/README.md`.

### Reviewed M1 result — attempt 11 decoded pin-controller boundary; return pending, 2026-10-14

* One boot030 RAM attempt at readiness `3c0b051`, reviewed handoff `1125c33`.
  **Controller exit 0, 10.526 s**; UTC 15:27:11.254767–15:27:21.781567,
  handoff 15:27:21.541577. Target boot021 marker, hardware DT, both DAPF
  checks/96-byte readback, 16-byte descriptor/readback and kboot reply PASS.
* Reviewed **43.43-second video** plus detailed **IMG_2662.jpeg**. Photo directly
  confirms J716c/t6050 **EL2, cpus=1**, counter **PASS/25 ticks**, timer
  **phys=1 virt=7 irq_masked=0 fiq_masked=0**, printed phases
  **1 → 10 → 11 → 12 → 13 → 2 → 3 → 4 → 5**, and **pending=1 strip=1 display=6**.
* Four-row panel changes through first and second device probes; final readable
  **P:05 S:09 / W:04 H:02 / D:0059 / B:63 C:0059** at video 30/43.28 s and photo.
  Offline public-table decode: **/soc/pinctrl@29c000000**, t6050/t8103 pinctrl,
  platform driver probe callback boundary. Earlier D=C=0057 maps to
  **/soc/pinctrl@2881e4000**; photo reads **returned 0 after 164043 usecs**, retry 1 end.
* First watchdog: **phase=5 worker=4 device=1 ticks=1304**; scheduler
  **sched=7 selections=1274 prev=52 next=20 current=20/kdevtmpfs**. Photo provides
  14 readable symbolic frames/offsets through timer softirq/IRQ exit; lower
  frames obscured. Later **device=2 ticks=2584**, selections=2550/prev=52/
  next=38/current=38/**kworker/u4:1**. First stack is not a proven final-driver
  stack. H=02 is a kernel watchdog count, not userspace liveness.
* **PID 1/userspace online_cpus=1/60-second liveness NOT OBSERVED**. No explicit
  panic observed. Video sampled at 0/10/15/20/30/43.28 s; no 60/90-second or full
  120-second coverage. Photo improves text, not duration evidence. Hidden
  fields/stack frames remain unconfirmed; no exact blocked PC/cause established.
* Return instructed at deadline **11:29:21 a.m. Eastern**; **Macintosh HD return
  PENDING HUMAN CONFIRMATION**, fresh protection/default **NOT CHECKED**.
  No retry, reconnect, reinstall or settings change. Full media remains out of Git.
* **Attempt 11 consumed.** Detailed report:
  `native/boot/stage-b-2026-10-14-attempt11-result.md`. M5 next: read-only checks
  after confirmed return and offline analysis of the decoded pin-controller
  callback/dependencies. Preserve installed boot021, clean client pin and gates.

### Historical M1 readiness — attempt 11 PASS, 2026-10-14

* Pulled/read M5 handoff `1125c33`, probe-path README/evidence/validation and
  public D/C/B decoder tables. Archive SHA-256
  `260f57106007b654a522480e3c20fb2b3630338a5b90edaa64bd067fa0ec2c16`
  and 16,724,043-byte size verified **before extraction**. All **13 intake
  files**, offline launcher and reviewed controller/decoder digests PASS.
  Image SHA-256 `190cd86d5f823326f5a44277f5efb96cc01c85b3a3f9ffbde16d9cb7abe35067`.
* **90 M1 offline cases PASS:** 37 launcher + 6 entry + 16 DAPF + 5 framebuffer
  + 19 hardware + 2 pinned ADT/DAPF + 4 root ADT + 1 real proxy serializer;
  all exit 0, synthetic transport only. Clean client remains pinned at
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`; installed boot021 unchanged.
* Only Image/package manifest differ from retained boot029. Fresh ignored
  receipt `build/native-intake/receipts/boot030-attempt11.json` and result
  `build/native-intake/results/boot030-stage-b-attempt11.json`/`.md` prepared
  with source/procedure/controller/payload/receipt/decoder hashes.
* **Ready for the authorized Stage B attempt 11** after publication. Human
  reports proxy running and video recording including all four panel rows.
  Post-attempt-10 protection prerequisite already PASS per M5; no extra restart
  or review loop. **Attempt 11 native/live checks NOT RUN at readiness.**
* Next: one reviewed RAM launch, literal P/S/W/H/D/B/C and Linux milestones,
  recording through the stop criterion with a close final frame. Decode public
  IDs offline and review video before publishing, then Macintosh HD within the
  existing bound. No retry, wider blacklist, reinstall or settings changes.

### Reviewed M5 handoff — boot030 / attempt 11, 2026-10-14

* Reviewed M1 `9d04195`: attempt 10 controller PASS (10.496 s), and paused
  video directly reads **P:05 S:09 W:04**. Three native strip lanes render;
  H/small fields/full transitions/userspace remain unobserved or unconfirmed.
  P=05 places progress at the first deferred-work flush by source inference.
  No exact driver, blocking PC or cause established. Macintosh HD return confirmed.
* Exact boot029 REA/Ghidra plus source/LLVM/linked bytes cover bus/platform
  wrappers: **81 instruction words, 69 nonrelocated matches**, 12 relocation
  words reviewed separately. Bus attach includes interface locking/callbacks;
  platform probe includes clocks/domain attachment before the driver callback.
* Boot030 adds **56 probe boundaries**, root/current device table IDs from
  286 public DT nodes, task attribution and a compact **four-row panel**.
  It repaints saved lanes and marks H before printk. The next native run can
  distinguish device locking/runtime PM/DMA/clocks/domains/driver entry.
  This improves diagnosis; **native hang unresolved, no new driver skip**.
* Only **Image** changes. Installed boot021, DT/config/initramfs/args and
  controller/hardware gates remain unchanged. Full Image/ELF roundtrip,
  actual helper/panel/identity/platform/parser sanitizer tests, **90 controller
  cases** and **13-file intake PASS**. Exact one-CPU/4 GiB diskless/networkless
  VZ reaches all phases/PID 1/one CPU and liveness at **60.190510 s**. Native
  AIC/MMIO/scanout and performance are not validated by these tests.
* Post-attempt-10 user policy JSON PASS: original Full/lab Permissive, exits 0.
  Independent root Macintosh HD/build 25G83/FileVault/SIP/staged m1n1 SHA PASS.
  Default/installed boot object/authenticated-root not re-queried. No host
  settings, volume, default, firmware or installed m1n1 changes.
* All test/REA VMs stopped; both shared quiet locks released.
* Next: M1 verifies private `native-j716c-boot030`, publishes offline readiness,
  then the human starts **one filmed attempt 11**. Record literal P/S/W/H/D/B/C,
  decode D/C/B offline and review early/final video through the stop criterion.
  **Native attempt 11/live checks NOT RUN.** Follow the current Stage-B checklist
  and `kernel/experiments/probe-path/`. No reinstall, automatic retry or extra
  M5 approval loop. Native PID 1/liveness precedes Linux control/input and the
  configuration agent's Omarchy handoff; GPU/SMP/idle/DVFS remain separate work.

### Reviewed M1 result — attempt 10 P:05 S:09 W:04; return confirmed, 2026-10-14

* One boot029 RAM attempt at readiness `8c96579`, reviewed M5 handoff `73c5e0d`.
  **Controller exit 0, 10.496 s**; UTC 14:48:59.495128–14:49:09.991426,
  handoff 14:49:09.756446. Target boot021 marker, hardware DT, both DAPF
  checkpoints/96-byte readback, 16-byte descriptor/readback and kboot reply PASS.
* **Video reviewed:** 27.197-second `IMG_2660.mov`; sampled frames/crops through
  27.05 seconds show native Linux/deferred-probe diagnostics and literal
  **`P:05 S:09 W:04`**, unchanged at 11, 12, 13.6, 20.4 and 27.05 seconds.
  Three strip lanes visibly render. H/full transition sequence **NOT OBSERVED**;
  H is not inferred zero. Small timer/display/pending fields **NOT CONFIRMED**
  because of blur/overlap; no prior attempt's values substituted.
* Source decodes P=05 as first deferred-work flush, S=09 as scheduler exit and
  W=04 as the boundary before `bus_probe_device`. Progress beyond phase 13 is
  **inferred from P=05's source path**; phase-13 text not directly observed.
  No exact blocked driver/PC, timer fault or hang fix established.
* PID 1/userspace `online_cpus=1`/60-second liveness, readable heartbeat/stack
  and retry-compatible details **NOT OBSERVED**. Video samples do not cover
  every frame or the full observation window. Full media remains out of Git.
* **Macintosh HD return CONFIRMED by human** (“back, update”). No later
  strip/message observation supplied. Fresh protection/default **NOT CHECKED**.
  No retry, reconnect, reinstall or boot/security/volume/default changes.
* **Attempt 10 consumed.** Result: `native/boot/stage-b-2026-10-14-attempt10-result.md`.
  M5 next: read-only return checks and offline deferred-worker/device-probe
  and diagnostic-visibility analysis. Preserve boot021/client pin and gates.

### Historical M1 readiness — attempt 10 PASS, 2026-10-14

* Pulled/read M5 handoff `73c5e0d`, context-display README/evidence/validation.
  Boot029 archive SHA-256
  `ebed9be8b34c3684aaf01ef06b8fc108e0c548960c1f83a25ed411c5ef42ce16`
  and 16,722,976-byte size verified **before extraction**. All **13 intake
  files**, offline launcher and reviewed controller digests PASS. Image SHA-256
  `53f5f2c5a7a2d9d0d2ae92961222090c97f0c266bb4066408acd577660e7cc32`.
* **90 M1 offline cases PASS:** 37 launcher + 6 entry + 16 DAPF + 5 framebuffer
  + 19 hardware + 2 pinned ADT/DAPF + 4 root ADT + 1 real proxy serializer;
  all exit 0, synthetic transport only. Clean client remains pinned at
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`; installed boot021 unchanged.
* Only Image/package manifest differ from retained boot028. Fresh ignored
  receipt `build/native-intake/receipts/boot029-attempt10.json` and result
  `build/native-intake/results/boot029-stage-b-attempt10.json`/`.md` prepared
  with source/procedure/controller/payload/receipt hashes; prior artifacts kept.
* **Ready for the authorized Stage B attempt 10** after publication. Human
  reports proxy running and video recording including bottom-left edge.
  Post-attempt-9 protection prerequisite already PASS per M5; no extra restart
  or review round trip. **Attempt 10 native/live checks NOT RUN at readiness.**
* Next: one reviewed RAM launch; capture display state/console_setup, literal
  enlarged P/S/W/H strip and context-switch/stack/timer/userspace evidence.
  Review recording, then Macintosh HD within existing bounds. No retry, wider
  blacklist, reinstall or settings change. Mapping success alone is not visibility.

### Reviewed M5 handoff — boot029 / attempt 10, 2026-10-14

* Reviewed M1 `29f0f8e`: attempt 9 controller PASS; paused video observes
  native J716c/t6050 EL2/one CPU, counter PASS/25 ticks, phases 1/10/11/12,
  then `reschedule pending=1 strip=0`. No literal lanes, phase 13, watchdog
  stack or diagnostic userspace/liveness observed. Macintosh HD return confirmed.
* REA/Ghidra plus exact source and an actual-function regression test confirm
  the old diagnostic mapper skips absent/retired consoles. The exact native
  strip=0 prerequisite is still unknown. REA omits 31 instruction words from
  `__switch_to`; full source/LLVM/linked-byte review accounts for those paths.
  Evidence covers 152 instruction words, 126 nonrelocated linked matches.
* Boot029 fixes independent validated-DT framebuffer initialization, adds
  display-state reporting, 4× strip glyphs and context-switch subphases. It
  changes only **Image**, with no guessed register changes or expanded skip.
  Installed boot021, DT/config/initramfs/args/hardware gates remain unchanged.
  **Native hang unresolved; this is a tested diagnostic repair.**
* Full Image/ELF roundtrip, helper/renderer/parser/mapper ASan/UBSan, **15 map
  scenarios**, old-defect reproduction, **90 controller cases** and **13-file
  intake PASS**. One-CPU/4 GiB diskless/networkless VZ reaches pending=1,
  phase 13/all later phases, PID 1/one CPU and liveness at **60.192201 s**.
  Generic strip=0/display=1 is expected. No native AIC/scanout/performance proof.
* Fresh post-attempt-9 user JSON PASS: original Full/lab Permissive, both exit 0.
  Independent root Macintosh HD/build 25G83/FileVault/SIP/staged m1n1 SHA PASS.
  Default/installed boot object/authenticated-root not separately re-queried.
  No settings, volume, default or installed m1n1 changes.
* All test/analysis VMs stopped; both shared quiet locks released.
* Next: M1 verifies private `native-j716c-boot029`, publishes offline readiness,
  then the human starts **one filmed attempt 10**. Capture display state and
  literal enlarged P/S/W/H strip; review video before reporting, then return
  within the existing bound. No extra M5 approval loop or installation restart.
  **Native attempt 10/live checks NOT RUN.** Current procedure:
  `tools/m1n1-client/stage-b-instructions.md`; engineering/provenance/tests:
  `kernel/experiments/context-display/`. Stable native diagnostic userspace
  precedes Linux control/input and the configuration agent's Omarchy work.

### Reviewed M1 result — attempt 9 phase 12; video reviewed; return confirmed, 2026-10-14

* One boot028 attempt at readiness `87a80dd`, reviewed M5 handoff `3503bf1`.
  **Controller exit 0, 10.530 s**, UTC 2026-10-14 14:11:02.041163–14:11:12.571778;
  handoff 14:11:12.342802. Hardware DT, boot021 marker, both DAPF checkpoints,
  96-byte correction/readback, 16-byte framebuffer descriptor/readback,
  prepared args and kboot reply PASS. Installed m1n1/client pin unchanged.
* **Video reviewed**: human supplied 21.598-second `IMG_2659.mov`; paused frames
  and enlarged lower-screen crops inspected from start through 21.45 seconds.
  Native Linux, clock blacklist, J716c/t6050 EL2/one CPU, counter PASS/25 ticks
  and timer status **phys=1 virt=7 irq_masked=0 fiq_masked=0 OBSERVED**.
* Printed phase sequence **1 → 10 → 11 → 12**; final visible line
  **`reschedule pending=1 strip=0 (P/S/W/H hex)`**, unchanged in reviewed later
  samples. Phase 13/2, heartbeat, scheduler summary/stack and worker/retry
  **NOT OBSERVED**. Literal P/S/W/H lanes **NOT OBSERVED**, not inferred zeros.
* Diagnostic PID 1/userspace `online_cpus=1`/60-second liveness **NOT OBSERVED**.
  Kernel one-CPU checkpoint is observed separately. No explicit panic visible;
  exact cause unknown. Sampling/clip duration do not cover every frame or the
  whole 120-second observation window. Full media stays out of workspace/Git.
* **Macintosh HD return CONFIRMED by human** after deadline/return guidance.
  No later message reported; fresh protection/default checks **NOT CHECKED**.
  No retry, reconnect, reinstall, wider skip or settings change.
* **Attempt 9 consumed.** Result: `native/boot/stage-b-2026-10-14-attempt9-result.md`.
  M5 next: read-only return checks and offline analysis after phase 12/before
  phase 13, including scheduling/visibility and strip availability. No exact
  blocking PC or confirmed root-cause repair claimed.

### Historical M1 readiness — attempt 9 PASS, 2026-10-14

* Pulled/read M5 handoff `3503bf1`, scheduling-boundary README and validation.
  Boot028 archive SHA-256
  `689fce13b00c4e59af61e5a23666509579985b89920a0477e4b107c6cf5944e9`
  and 16,722,641-byte size verified **before extraction**. All **13 intake
  files**, offline launcher and reviewed controller hashes PASS. Image SHA-256
  `514dde0c48c17d77d1979fb98b13f5ecb45096839e8b10a72d24adcf9df0778f`.
* **90 M1 offline cases PASS:** 37 launcher + 6 entry + 16 DAPF + 5 framebuffer
  + 19 hardware + 2 pinned ADT/DAPF + 4 root ADT + 1 real proxy serializer;
  all exit 0, synthetic transport only. Clean client remains pinned at
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`; installed boot021 unchanged.
* Only Image/package manifest differ from retained boot027. Fresh ignored
  receipt `build/native-intake/receipts/boot028-attempt9.json` and result
  `build/native-intake/results/boot028-stage-b-attempt9.json`/`.md` prepared
  with source/procedure/controller/payload/receipt hashes; prior artifacts kept.
* **Ready for the authorized Stage B attempt 9** after publication. Human
  confirms Running proxy and video recording including the bottom-left edge.
  Post-attempt-8 protection prerequisite already PASS per M5; no extra restart
  or M5 review needed. **Attempt 9 native/live checks NOT RUN at readiness.**
* Next: one reviewed RAM launch, capture literal P/S/W/H sequence and kernel
  timer/scheduler/stack/userspace milestones, review recording, then Macintosh HD
  under existing limits. No retry, wider blacklist, reinstall or settings change.

### Reviewed M5 handoff — boot028 / attempt 9, 2026-10-14

* Reviewed M1 `7da251d`: attempt 8 reached native J716c/t6050 EL2, one CPU,
  counter PASS/25 ticks, then timer status. Phase 2 and diagnostic userspace
  NOT OBSERVED. Video remains unreviewed; no exact hang PC or cause established.
* REA/Ghidra plus exact source/LLVM/linked bytes confirm the idle NOP branch
  already exists and boot027 can reschedule before arming its watchdog.
  Two complete bodies, 261 instruction words/163 nonrelocated linked matches;
  no new Apple binary extraction or speculative register change.
* Boot028 corrects that observation gap: watchdog armed before preemption,
  phases 10–13, bounded scheduler state/one stack and a lock-free bottom-left
  P/S/W/H status strip in existing scanout RAM. Scheduler/driver operations
  remain; only Image changes. Root cause still unknown; no wider blacklist.
* Full Image/ELF roundtrip, actual helper/renderer ASan/UBSan, **90 controller
  cases** and **13-file intake PASS**. Exact one-CPU/4-GiB diskless/networkless
  VM reports pending=1, phase 13, all remaining phases, PID 1/one CPU and
  liveness at **60.191892 s**. VM has no native AIC/framebuffer; strip visibility
  and physical scheduling remain untested. No performance improvement claimed.
* Fresh post-attempt-8 user JSON PASS: original Full/lab Permissive, both exit 0.
  Independent original root/build 25G83/FileVault/SIP/staged m1n1 checksum PASS.
  Default/installed boot object/authenticated-root not separately re-queried.
  No boot/security/volume/default changes or installed m1n1 replacement.
* Next: M1 verifies private `native-j716c-boot028`, publishes readiness, then
  the human starts **one filmed attempt 9**. Capture the strip and review the
  video; no additional M5 approval loop for unchanged verified instructions.
  Native attempt 9 **NOT RUN**. Follow `tools/m1n1-client/stage-b-instructions.md`
  and `kernel/experiments/schedule-boundary/README.md`. Preserve current setup.
  Stable diagnostic userspace precedes Linux control/input and Omarchy setup.

### Reviewed M1 result — attempt 8 timer/ticks PASS; return confirmed, 2026-10-14

* One boot027 RAM attempt at readiness `174419e`, reviewed handoff `46ad887`.
  **Controller exit 0, 10.492 s**; UTC 2026-10-14
  13:38:30.894614–13:38:41.387312; handoff 13:38:41.148275.
* Target boot021 marker, final hardware DT/arguments, both DAPF checkpoints,
  96-byte correction/readback, 16-byte framebuffer descriptor/readback and
  kboot request/reply PASS. Installed m1n1/client pin unchanged.
* Fresh `IMG_2658.jpeg` **OBSERVES** native Linux, exact clock blacklist message,
  `target=j716c-t6050 mode=EL2 cpus=1`, `phase=1 device=0`,
  **`timer counter=PASS ticks=25`**, and final visible
  `timer phys=1 virt=7 irq_masked=0 fiq_masked=0`.
* Phase 2+, worker/retry/heartbeat and diagnostic PID 1/userspace
  `online_cpus=1`/60-second liveness **NOT OBSERVED**. One CPU is independently
  visible in the kernel checkpoint. No explicit panic visible; root cause unknown.
* Video recording confirmed, but video not supplied/reviewed. Human was asked
  to review its ending; no video-review result received. Full media not copied
  or committed; the still does not exclude transient later messages.
* Return instructed under the 120-second bound; **Macintosh HD desktop return
  CONFIRMED by human**. No later message reported. Fresh security/default checks
  **NOT CHECKED**. No retry, reconnect, reinstall or settings changes.
* Result: `native/boot/stage-b-2026-10-14-attempt8-result.md`. **Attempt 8 consumed.**
  M5 next performs read-only return checks and offline investigation after timer
  status/before phase 2 (preemption/watchdog setup/visibility); no proven fault
  yet. Keep passing tick evidence separate from later scheduling progress.

### Historical M1 readiness — attempt 8 PASS, 2026-10-14

* Read handoff `46ad887` and deferred-probe evidence. Downloaded private boot027;
  archive SHA-256 **33c7ff4d1f8e93c929a5024ebb19b7dee825cb14e1c7bf93f7df8c5526bf6a8c**
  and 16,721,223-byte size PASS **before extraction**. All **13 intake files**,
  offline launcher and reviewed controller digests PASS. Image SHA-256
  **5a5ca64eaf2c3389e9fca226d7244150edbc8975738fe11a9304c0c996e29b64**.
* **90 M1 offline cases PASS:** 37 launcher, 6 entry descriptor, 16 DAPF,
  5 framebuffer, 19 hardware binding, 2 pinned ADT/DAPF, 4 root ADT and
  1 real proxy serializer. All exit 0; synthetic transport only.
* Clean client remains pinned at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
  Installed boot021 m1n1 unchanged. Only Image and package manifest differ
  from retained boot025; DT/initramfs/config/m1n1 remain byte-identical.
* Fresh ignored receipt `build/native-intake/receipts/boot027-attempt8.json`
  and `build/native-intake/results/boot027-stage-b-attempt8.json`/`.md` retain
  source/procedure/payload/receipt hashes. Previous packages/results preserved.
* **Ready for the authorized Stage B attempt 8** after this publication.
  Human reports Running proxy and video recording. M5 post-attempt-7 protection
  prerequisite already PASS. No extra restart or M5 review needed.
* **Attempt 8 native/live checks NOT RUN at readiness.** One reviewed launch;
  capture Hardware DT, both DAPF checkpoints, timer/tick/main/worker phases and
  diagnostic userspace/liveness. Review video; stop on failure or the existing
  time limit, then Macintosh HD. No retry, reinstall or settings changes.

### Reviewed M5 handoff — boot027 / attempt 8, 2026-10-14

* Reviewed M1 `a2239f9` / attempt 7: native Linux progressed to
  `deferred_probe_initcall` at 1.371769 seconds after two completed late
  initializers. No panic or diagnostic userspace observed; last line is not a
  blocking PC. Macintosh HD return confirmed.
* Exact boot025 REA/Ghidra and source analysis covers two deferred-probe bodies,
  94 LLVM instruction words and linked relocations. Debugfs, deferred worker
  locks/device probes, timer/scheduling and console visibility remain possible
  causes. **Root cause unknown; no speculative additional blacklist.**
* Boot027 adds opt-in bounded timer/tick and deferred-probe phase diagnostics,
  six maximum timer-softirq heartbeats and 32 detailed driver retries. Both
  normal triggers/flushes are preserved. Only **Image** changes; the existing
  clock-debug skip stays and `ilinux_probe_diag=1` is fixed in the launcher.
* Hardware validation now checks this J716c/t6050 CPU MPIDR/family topology,
  AIC3 geometry/phandle/translation and timer routes before handoff, retaining
  live chip/board/pin/secondary/DAPF/framebuffer guards. Corrected stale intake
  receipt instructions so M1 continues Stage B instead of repeating setup.
* Full Linux 7.1.9 Image link/ELF roundtrip, **11 actual-helper ASan/UBSan
  scenarios**, **90 controller cases** and **13-file intake PASS**. Exact
  packaged Image/initramfs in one-CPU/4-GiB diskless/networkless VZ reports
  counter PASS/25 ticks in 100 ms, phases 1–9, PID 1/one CPU and liveness at
  **60.187341 seconds**. This VM does not test native M5 AIC or reproduce the hang.
* Post-attempt-7 fresh human JSON PASS: original Full/lab Permissive, both exit
  0. Independent root Macintosh HD/build 25G83/FileVault/SIP/staged m1n1 hash
  PASS. Default/installed object/authenticated-root not separately queried.
  No boot/security/volume/default changes or installed m1n1 replacement.
* **Next:** M1 verifies private `native-j716c-boot027` and latest controller,
  publishes readiness, then the human starts one filmed attempt 8. No extra M5
  approval loop. Record timer/phase/worker checkpoints and PID 1/liveness or
  first failure, return within the existing bound. **Native attempt 8 NOT RUN.**
  Follow `tools/m1n1-client/stage-b-instructions.md` and
  `kernel/experiments/deferred-probe/README.md`. Continue the existing Boot Lab
  setup; no Recovery, reinstall, repeated Stage A, automatic retry or widened skip.


### Historical M1 result — attempt 7 later initcalls; return confirmed, 2026-10-14

* One boot025 attempt at readiness `9bda4dd`, reviewed handoff `995efd7`.
  **Controller exit 0, 10.433 s**, UTC 2026-10-14
  04:53:40.692574–04:53:51.122617; handoff 04:53:50.882694.
* Both DAPF checkpoints, 96-byte RAM correction/readback, 16-byte framebuffer
  descriptor/readback, target boot021 marker, final DT/arguments and kboot reply
  PASS. Only fixed `initcall_blacklist=clk_debug_init` added; package unchanged.
* Fresh photo **OBSERVES later native initcalls**: `boot_wait_for_devices` and
  `sync_state_resume_initcall` return 0; final visible line is
  `calling deferred_probe_initcall+0x0/0xb8 @ 1` at 1.371769 s.
  No returned line or panic/Oops visible. Exact blocking cause not established.
* Exact blacklist/AIC/timer log lines and rectangle count **NOT OBSERVED** in
  the supplied still; timestamp progress is observed. **Diagnostic PID 1 /
  online_cpus=1 / 60-second liveness NOT OBSERVED**. Initcall `@ 1` is distinct.
* Prior photo `IMG_2655.jpeg` was excluded; fresh `IMG_2657.jpeg` reviewed.
  Full photos/video not copied or committed; video has not been reviewed.
* Stop/return instructed at the 120-second limit. **Macintosh HD desktop return
  CONFIRMED by the human.** No later screen message reported. Fresh security/
  default checks NOT CHECKED.
* Result: `native/boot/stage-b-2026-10-14-attempt7-result.md`. M5 next performs
  read-only return checks, then exact-build deferred-probe /
  shared-dependency analysis offline. **Attempt 7 consumed**; no additional
  skip, reconnect, retry, reinstall or settings changes authorized.

### Historical M1 readiness — attempt 7 PASS, 2026-10-14

* Pulled/read `995efd7` and the exact-build clock-debug evidence. Retained
  boot025 archive, all **13 files**, offline launcher and reviewed controller
  hashes PASS. New ignored receipt: `build/native-intake/receipts/boot025-attempt7.json`.
  Original receipts/packages/results remain intact; no download or rebuild.
* **69 offline cases PASS:** 35 launcher + 6 descriptor + 16 DAPF + 5
  framebuffer + 2 pinned DAPF parser + 4 root ADT + 1 proxy serializer.
  All exit 0, synthetic transport only. Clean client remains pinned at
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`; installed boot021 m1n1 unchanged.
* Package unchanged: archive `908d0a9aa88c83469738f146f464bcb3815e812e56ef1615f0168cb7ce595f86`;
  Image `8849de7c2b8e529ad5895707ed26f535993cc8ff85447c450b2c13240185a0ea`.
  Only fixed argument `initcall_blacklist=clk_debug_init` is added. All existing
  guard hashes match; no broader blacklist or arbitrary arguments accepted.
* Separate ignored `boot025-stage-b-attempt7.json`/`.md` record prepared under
  `build/native-intake/results/`, with current source/procedure/receipt digests.
  Post-attempt-6 original Full/lab Permissive prerequisite already PASS per M5.
* **Ready for the authorized Stage B attempt 7** after publication. Human
  reports Running proxy and video recording; no extra restart/review needed.
  One launch, capture exact blacklist line and later initcalls/userspace/liveness,
  then Macintosh HD under existing bounds. **Attempt 7/current live checks/Linux
  NOT RUN at readiness.** No USB opened, retry, reinstall or settings changes.

### Reviewed M5 handoff — attempt 7 / unchanged boot025, 2026-10-14

* Reviewed M1 `039a17b`: boot025 attempt 6 passed controller/DAPF/descriptor
  gates and reached late native initialization. The screen stopped after
  `calling clk_debug_init` at 1.360189 s. No visible panic or diagnostic
  userspace/one-CPU/60-second heartbeat. Last line is not an exact blocking PC.
* Exact boot025 ELF/Image, two full REA/Ghidra function bodies and 195 LLVM
  instruction-word checks identify optional clock debugfs registration. Normal
  clock registration/consumer APIs are separate. Root cause remains unknown.
* Implemented one fixed controller argument: `initcall_blacklist=clk_debug_init`.
  Reuse **unchanged boot025**; no new kernel build or release asset. Prepared-DT
  validation rejects missing, expanded or appended blacklist changes.
* **69 controller cases PASS**, including four new argument-boundary tests;
  all **13 package files PASS**. Exact Image/initramfs in diskless/networkless
  one-vCPU/4-GiB VZ reports exactly one skipped initcall, reaches diagnostic
  PID 1/online_cpus=1 and passes the 60-second heartbeat. Native attempt 7
  **NOT RUN**; this generic VM does not reproduce/resolve the native hang.
* Post-attempt-6 human JSON PASS: original Full/lab Permissive, both exit 0.
  Independent read-only root Macintosh HD/build 25G83/FileVault=true/SIP enabled
  and unchanged staged boot021 m1n1 SHA. Default/installed object/authenticated-
  root not separately queried. No host boot/volume/security/default changes.
* **Next:** M1 pulls current main, rechecks the existing boot025 package and
  updated launcher, publishes readiness, then the human starts one filmed
  attempt 7. No extra M5 approval round trip. Capture the exact blacklist
  checkpoint, later initcall boundary and userspace/liveness or first failure,
  then Macintosh HD within existing bounds. No retry or expanded blacklist.
  Follow `tools/m1n1-client/stage-b-instructions.md`; evidence and limits are
  in `kernel/experiments/clock-debug/README.md`.

### Historical M1 result — attempt 6 late Linux init; return confirmed, 2026-10-14

* One boot025 attempt at readiness `32f5bcf`, reviewed M5 handoff `f8e98ee`.
  **Controller exit 0, 10.391 s**, UTC 2026-10-14
  04:27:29.761928–04:27:40.153385; handoff 04:27:39.918074.
* Both **DAPF checkpoints PASS**, 96-byte correction/readback; **framebuffer
  descriptor PASS**, 16-byte data/readback. Target boot021 marker, final gates
  and kboot reply PASS. No changed pin or installed boot object.
* **Native late Linux initialization OBSERVED.** Photo shows advancing
  timestamps through 1.360189 s. Last completed visible `bert_init` returns 0;
  final line is `calling clk_debug_init+0x0/0x120 @ 1`. Human confirms screen
  stayed there until shutdown. No panic/Oops visible; exact cause not established.
* Earlier AIC profile/Initialized and `arch_timer` lines are NOT OBSERVED in
  the supplied still. Later execution supports progress beyond the prior AIC
  panic, not full interrupt/timer validation. Video was recorded but not reviewed.
* **Diagnostic PID 1 / online_cpus=1 / 60-second liveness NOT OBSERVED**.
  Initializer `@ 1` is not the diagnostic userspace milestone. Rectangle count
  not reported. Full media and raw target data not copied or committed.
* At the 120-second limit, return was instructed. **Human confirms usual
  Macintosh HD desktop return.** Fresh security/default checks NOT CHECKED.
  No reconnect, retry, reinstall or boot/volume/security/default changes.
* Result: `native/boot/stage-b-2026-10-14-attempt6-result.md`. **M5 next:**
  read-only return checks and offline exact-build clock debug initialization
  analysis. Attempt 6 consumed; no new live attempt authorized.

### Historical M1 readiness — boot025 attempt 6 PASS, 2026-10-14

* Pulled/read `f8e98ee`, current checklist and AIC evidence. Private boot025
  archive verified against Git **before extraction**; offline launcher and
  **13 receipt files PASS**. Earlier packages and receipts retained.
* **65 offline cases PASS:** 31 launcher + 6 descriptor + 16 DAPF guard +
  5 framebuffer + 2 pinned DAPF parser + 4 root ADT + 1 proxy serializer.
  All exit 0, synthetic transport only; no USB opened during readiness.
* Archive (16,720,464 bytes):
  `908d0a9aa88c83469738f146f464bcb3815e812e56ef1615f0168cb7ce595f86`.
  Image: `8849de7c2b8e529ad5895707ed26f535993cc8ff85447c450b2c13240185a0ea`.
  SHA256SUMS: `aae4c401ef45457cbd03687b4325ffd0bcbe1c15fcac9bf48a1167046c3c4d5d`.
* All five reviewed controller digests match; clean client remains pinned at
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`. Actual comparison confirms only
  Image differs from boot024. Installed boot021 m1n1/marker remain unchanged.
* New ignored `build/native-intake/receipts/boot025.json` and separate
  `build/native-intake/results/boot025-stage-b-attempt6.json`/`.md` retain exact
  source/procedure/payload digests and the one-attempt evidence plan.
* Post-attempt-5 original Full/lab Permissive prerequisite already PASS per M5.
  Human reports proxy running and video recording. **Ready for the authorized
  Stage B attempt 6** after publication; no extra restart or M5 review needed.
* Capture both DAPF checks, descriptor PASS, AIC profile/final Initialized line,
  timer progress and kernel/PID 1/CPU/liveness or first failure; then return to
  Macintosh HD within existing bounds. **Attempt 6/current live checks/Linux
  NOT RUN at readiness.** No retry, reinstall or boot/settings changes.

### Reviewed M5 handoff — boot025 / attempt 6 offline ready, 2026-10-14

* Reviewed M1 `fcf40c1`: attempt 5 reached native early Linux, then an
  undefined instruction in `aic_init_cpu+0x9c`. Exact boot024 ELF/Image mapping
  identifies `msr s3_5_c15_c1_3, x0`, the legacy guest-timer FIQ enable write.
  The fast-IPI write is not the reported fault; restriction mechanism unknown.
* Two REA/Ghidra queries, matching linked bytes, 173 LLVM instruction-word
  checks and public m1n1/Linux source support an original restricted t6050 AIC
  profile. It preserves host timers/fast IPIs, masks guest timer sources through
  architectural registers, rejects unsupported guest IRQ/KVM paths and separates
  legacy uncore handling. Older profiles retain their capabilities.
* Full Image link and 38 actual-driver scenarios with ASan/UBSan PASS. All 65
  controller cases and 13-file package intake PASS. Exact packaged Image plus
  unchanged initramfs reaches PID 1, one CPU and 60-second liveness in diskless,
  networkless generic VZ. That VM has no M5 AIC; **native boot025 NOT RUN**.
* Boot025 changes only Image from boot024. Installed boot021 m1n1, client pin,
  DT/initramfs/config, DAPF/descriptor guards and fixed arguments stay unchanged.
  Archive `908d0a9aa88c83469738f146f464bcb3815e812e56ef1615f0168cb7ce595f86`;
  Image `8849de7c2b8e529ad5895707ed26f535993cc8ff85447c450b2c13240185a0ea`.
* Fresh post-attempt-5 human JSON PASS: original Full/lab Permissive, both exit 0.
  Independent read-only root Macintosh HD, build 25G83, FileVault=true, SIP
  enabled and staged m1n1 SHA unchanged. Default/installed object/authenticated-
  root not separately queried. No boot/volume/security/default changes.
* **Next:** M1 verifies private `native-j716c-boot025` offline and publishes
  readiness. The human then starts one filmed attempt 6 under the current
  `tools/m1n1-client/stage-b-instructions.md`; no additional M5 round trip is
  needed for unchanged verified code. Record AIC profile/final Initialized,
  timer progress, PID 1/one CPU/60-second heartbeat or first failure, then return
  to Macintosh HD. No retry/reinstall. Research and limits are in
  `kernel/experiments/aic-t6050/README.md`. No native performance claim.

### Historical M1 result — attempt 5 early Linux panic; return confirmed, 2026-10-13

* One recorded boot024 attempt at readiness `e362a7f`, reviewed handoff
  `1d1be38`. **Controller exit 0, 10.421 s**, UTC 2026-10-14
  03:54:01.823993–03:54:12.246249; handoff 03:54:12.010468.
* **Both DAPF checkpoints PASS**, including the 96-byte RAM correction/readback.
  **Early framebuffer descriptor PASS** (16-byte kernel RAM data/readback),
  target boot021 marker, final preflight and kboot reply PASS.
* **Native early Linux execution/readable screen OBSERVED.** Human photo shows
  undefined-instruction Oops at `aic_init_cpu+0x9c/0x150`, then
  `Kernel panic - not syncing: Attempted to kill the idle task!`.
  IRQ initialization call trace is in the sanitized result; exact cause still
  needs matching boot024 kernel analysis. No speculative hardware diagnosis.
* Rectangle count / first chronological line / initializer pair not reported.
  **PID 1 / diagnostic online_cpus=1 / 60-second liveness NOT OBSERVED**.
  Early `nr_cpu_ids=1` is visible; it does not establish diagnostic userspace.
* Panic prompted stop/return guidance at the observation limit. **User confirms
  usual Macintosh HD desktop return.** Fresh security/default checks NOT CHECKED.
  No reconnect, retry, reinstall or boot/volume/security/default changes.
* Sanitized result: `native/boot/stage-b-2026-10-13-attempt5-result.md`.
  Full photo/video and register/address dumps not copied or committed. Phone
  video was confirmed before launch; its content has not been reviewed.
* **M5 next:** read-only return checks, then offline exact-build analysis of
  `aic_init_cpu+0x9c` and AIC feature/register handling. Attempt 5 is consumed;
  no new physical attempt authorized. Installed boot021 m1n1/client pin unchanged.

### Historical M1 readiness — boot024 attempt 5 offline PASS, 2026-10-13

* Pulled and reviewed `1d1be38`, current Stage B instructions and early-screen
  evidence. Downloaded private boot024 separately; verified the Git-tracked
  archive SHA-256 **before extraction**, then all **13 receipt files** and
  offline launcher verification PASS. Earlier packages/receipts/results retained.
* Archive (16,720,911 bytes):
  `f7cb69153adc832cae3a66fd6159e7fd41fccc2a113d3550962a7f959edd9636`.
  Image: `6b683a2f52e769d1a23474b6807d009da8ad2e19d2168e62caba6cbbae240f7d`.
  SHA256SUMS: `c9b132f08ea093667c9abb3798315e77cc6347d28897bdfa87654d14e20a2219`.
* **65 offline cases PASS:** launcher 31, entry descriptor 6, DAPF guard 16,
  framebuffer 5, real pinned DAPF parser 2, root ADT 4, proxy serializer 1.
  All exit 0; synthetic transport only. The serializer test explicitly uses
  `M1N1_SOURCE` pointing to the existing pinned checkout; no USB opened.
* All five reviewed controller digests match. Client is clean at
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`. Actual file comparison confirms
  **only Image differs from boot022**; installed boot021 m1n1/marker unchanged.
* New ignored receipt `build/native-intake/receipts/boot024.json` and separate
  `build/native-intake/results/boot024-stage-b-attempt5.json`/`.md` retain exact
  provenance, procedure/controller hashes and the one-invocation evidence plan.
* M5-reviewed post-attempt-4 policy prerequisite already PASS: original Full,
  lab Permissive, both exit 0. No duplicate query or changes to boot/settings.
* **Ready for the authorized Stage B attempt 5.** Human has started the lab and
  confirms Running proxy plus phone video recording. After publishing readiness,
  run the documented launcher once, capture both DAPF checkpoints, descriptor
  PASS and rectangle/kernel/PID 1/CPU/liveness observations, then Macintosh HD.
* **Attempt 5/current live checks/Linux NOT RUN at readiness.** Historical Linux
  remains NOT OBSERVED. No reinstall, settings changes or automatic retry.

### Reviewed M5 handoff — boot024 early observation ready for M1 intake

* Reviewed M1 `4b1a5b9`: attempt 4 passed DAPF/preflight/kboot reply but no
  readable Linux milestone. Do not label the remaining logo a proved GPU,
  AIC or kernel failure.
* REA/Ghidra on the exact boot021 ELF confirms console clearing before the
  final kernel jump. Source + 144 LLVM instruction-word checks corroborate
  two function bodies; no proprietary decompilation needed for this blocker.
* Implemented original Linux entry rectangles and a flat-DT early framebuffer
  console; added initializer tracing. Boot024 changes only Image from boot022.
  Launcher fills a bounded/readback-checked 16-byte kernel RAM descriptor;
  the tested 96-byte DAPF RAM correction and every existing gate remain.
* Full Image build, actual C/libfdt + ARM64 assembly tests with sanitizers,
  65 Python/real-parser/proxy cases, and 13-file package intake PASS.
  Exact packaged Image + unchanged initramfs reached PID 1, one CPU and
  60-second liveness in a diskless generic VZ VM. **Native early display and
  boot024 NOT RUN**; no native performance claim.
* Fresh post-attempt-4 user JSON: original Full/lab Permissive, both exit 0.
  Independent read-only checks: original root Macintosh HD, build 25G83,
  FileVault true, SIP enabled, unchanged staged m1n1 SHA. Default/installed
  object/authenticated-root not separately re-queried. No host settings writes.
* Boot024 archive `f7cb69153adc832cae3a66fd6159e7fd41fccc2a113d3550962a7f959edd9636`;
  Image `6b683a2f52e769d1a23474b6807d009da8ad2e19d2168e62caba6cbbae240f7d`.
  REA/implementation evidence: `kernel/experiments/early-framebuffer/README.md`.
* **Next:** M1 follows `tools/m1n1-client/stage-b-instructions.md`: download
  private release `native-j716c-boot024`, verify offline, publish readiness.
  Human then starts one attempt 5 with phone video already recording, selects
  existing iLinux Boot Lab, and M1 runs the reviewed launcher once. Record
  rectangle count/last readable initializer/PID 1/liveness, then return to
  Macintosh HD. No reinstall, security/volume/default changes or auto-retry.

### Historical M1 result — attempt 4 controller PASS; return confirmed, 2026-10-13

* One boot022 attempt at `d4209d3`: **controller exit 0, 10.458 s**, UTC
  2026-10-14 03:13:05.896584–03:13:16.354836. All preflight gates passed.
* **Both DAPF checkpoints PASS**: reviewed live layout/code/table matched;
  one bounded 96-byte RAM correction applied and read back, other entries
  retained. Handoff requested at 03:13:16.120938 UTC; kboot reply succeeded.
* Human reports unchanged logo and text too fast to read/photograph.
  **Linux kernel/PID 1/online_cpus=1/60-second liveness NOT OBSERVED**.
  No identifiable failure reported; controller success is not Linux success.
* At the 120-second limit, power-off/startup-picker return was instructed.
  **User confirms successful return to the usual Macintosh HD desktop.**
  Fresh protections/default checks NOT CHECKED. No reconnect, retry, reinstall
  or settings changes.
* Sanitized result: `native/boot/stage-b-2026-10-13-attempt4-result.md`.
  M5 should perform read-only return checks and establish an observable early-boot path
  offline before any separately authorized physical attempt. Keep passing
  framebuffer/DAPF/CPU/storage/version gates. This attempt is consumed.

### Historical M1 readiness — attempt 4 checks PASS, 2026-10-13

* Pulled/read `2773a73` and the DAPF evidence/current checklist. Existing
  boot022 offline launcher verification **PASS**. All **13 receipt files**,
  retained archive and Git-tracked intake manifest still match; receipt unchanged.
* **53 offline cases PASS:** 31 launcher + 16 DAPF RAM-guard + 2 real pinned
  DAPF-parser + 4 root-ADT. All suites exit 0; fake transport/synthetic memory
  only. Prior unchanged USB/framebuffer/intake results remain applicable.
* Reviewed launcher/guard/FDT/USB-selector hashes match the handoff. Client
  clean at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`. Reuse boot022 and the
  installed boot021 m1n1/marker; no download, rebuild or reinstall.
* Proposed attempt adds a verified 96-byte RAM data-table correction after
  existing final gates. Both `DAPF layout PASS` and `DAPF RAM table corrected`
  checkpoints are required in the new evidence record; real correction NOT TESTED.
* Post-attempt-3 policy prerequisite PASS per M5-reviewed user JSON: original
  Full/lab Permissive, both exit 0. No repeat query or inter-agent approval loop.
* Separate ignored `build/native-intake/results/boot022-stage-b-attempt4.json`
  and `.md` prepared with source/procedure/payload digests and checkpoint plan.
  Prior attempts/receipts retained. **Offline ready for attempt 4; wait for the
  human's explicit start and Running proxy report before one invocation.**
* **Attempt 4 and all its live checks NOT RUN.** Linux execution remains
  NOT OBSERVED historically. No USB opened, target command or settings change
  during readiness; no automatic retry. Same bounded screen observation and
  Macintosh HD return procedure after the eventual single attempt.

### Reviewed M5 handoff — DAPF correction, 2026-10-13

Latest: attempt 3 passed all boot022 preflight gates, then m1n1 raised an
SError during DAPF setup; Linux execution NOT OBSERVED. Exact-image ELF/REA/
GNU/LLVM analysis and the sanitized ADT expose a fixed-index DAPF/GAPF mismatch.
An original source guard builds/tests, and the current launcher implements a
narrow verified 96-byte RAM work-list correction for the unchanged installed
m1n1. Boot022 payload unchanged. Native correction NOT TESTED. M1 must verify
updated controller code offline before the human starts one proposed attempt 4.
Fresh user-supplied policy JSON: original Full/lab Permissive, both exit 0.
Independent original build/FileVault/SIP/authenticated-root and staged m1n1
checks pass. No host boot/settings changes. Current instructions:
`tools/m1n1-client/stage-b-instructions.md`; evidence and limits:
`kernel/experiments/dapf-handoff/README.md`.

M5 completed offline analysis/implementation; all test VMs are stopped and both
quiet locks released. M1 owns the new offline verification and sanitized result
record. Reuse boot022; no download/reinstall/Recovery. The native change is a
RAM-only data-table correction, not a new persistent boot object. Previous
attempt 3 is consumed. Do not reconnect or launch merely to verify the code;
wait for the human to start the proposed single attempt after readiness.
Preserve original Full Security, all existing gates/time bounds and macOS return.
The supplied post-attempt-3 policy result is current; no duplicate query needed.

### Historical M1 result — attempt 3 m1n1 exception; return confirmed, 2026-10-13

* One boot022 invocation at `c5f515c`: controller exit 1, **32.059 s**,
  UTC 02:34:32.733054–02:35:04.792407 on 2026-10-14.
* **All preflight checks passed**, including the corrected prepared framebuffer,
  single-core DT and disabled storage/cpufreq. Live boot021 marker PASS.
  Handoff requested at **02:34:42.905947 UTC**; `kboot_boot` reply timed out.
* Human photo shows **m1n1 SError in EL2**, followed by `Unhandled exception,
  rebooting...`, after DT preparation and PCIe messages. Safe relative code
  offset and exact text are in the result; no raw addresses/register dump saved.
  Message proximity does not establish PCIe as the cause.
* **Linux kernel/PID 1/online_cpus=1/60-second liveness NOT OBSERVED.** Handoff
  requested is distinct from kernel execution; this is not the earlier
  preflight-only NOT RUN result. No native success or performance claim.
* **User confirms usual Macintosh HD desktop return.** Fresh build/default/
  protection checks remain for M5. No settings changes, reinstall or retry;
  boot022, installed m1n1 and clean client pin unchanged.
* M5: read `native/boot/stage-b-2026-10-13-attempt3-result.md`, perform read-only
  return checks, then investigate matching-build symbols and pinned pre-kernel
  hardware setup offline. Preserve the passing observation gate. This one
  attempt is consumed; no new live session or boot-setting changes authorized.

### Historical M1 readiness — boot022 intake PASS, 2026-10-13

* Pulled `3c7eae1` (descendant of `bf79263`) and read the current handoff.
  Downloaded private boot022 to its own ignored directory; verified the
  Git-tracked archive checksum **before extraction**, then offline launcher
  verification and all **13 intake-file hashes/declared revision PASS**.
* Archive (16,717,590 bytes):
  `b59db87bee50f5a2b57f65ea54e9ecd9fc07d410251bb38175001ac056ee6862`.
  Intake manifest:
  `862391dd99ee93d07c196e502196cefc869b2549274d6139d781f564b4bc50a0`.
  New receipt: ignored `build/native-intake/receipts/boot022.json`.
* **31 launcher + 5 framebuffer + 4 actual pinned-ADT tests PASS** locally,
  all offline. Reran ADT cases because the changed FDT gate/test fixture is
  in that path. Prior 20 USB tests remain applicable to unchanged selector/
  client. M5's C/serializer/intake tests are separate reported evidence.
* Reviewed source hashes match the checklist. Clean client stays pinned at
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`. Compared actual package files:
  only the Stage-B DT differs; kernel/initramfs/m1n1 and other payloads match
  boot021. The installed **boot021 m1n1 marker is correct**; no reinstall.
* M5 policy prerequisite is already PASS per `3c7eae1`: user-supplied original
  Full/lab Permissive JSON, both exit 0, reviewed by M5. No duplicate check.
* Separate ignored `boot022-stage-b-attempt3.json`/`.md` evidence prepared;
  earlier receipts and attempts preserved. **Ready for the authorized Stage B
  attempt 3**, after the human selects the existing lab and reports proxy ready.
* **Attempt 3/Linux NOT RUN; current live checks NOT RUN.** No USB opened,
  settings changed or target commands sent during intake. One invocation only,
  then observe kernel/PID 1/online_cpus=1/60-second liveness within the documented
  limits and return to Macintosh HD. No retries or boot-setting changes.

### M5 handoff reviewed by M1 — boot022 / Stage B attempt 3, 2026-10-13

Code and checklist: `0bea8f2` or later. Download:
https://github.com/nickyrice04/ilinux/releases/tag/native-j716c-boot022
Both assets published; remote archive digest and size verified against local.

Latest: Stage B attempt 2 never handed off to Linux. Boot021 lacked m1n1's
required framebuffer placeholder. Job 022 reproduces this with the actual
pinned C function and corrects only the Stage-B DT; boot022 is verified offline.
Kernel/initramfs/installed m1n1 unchanged; the boot021 marker remains correct.
M1 must intake boot022 before one reviewed attempt 3. The user's fresh read-only
post-return JSON reports original Full/lab Permissive, both exit 0; reviewed,
not independently rerun. Native correction NOT TESTED, Linux NOT RUN. Original root/build,
FileVault/SIP/authenticated-root and staged m1n1 were independently rechecked.
No volume/security/default/boot-object changes. Current instructions:
`tools/m1n1-client/stage-b-instructions.md`; evidence:
`virtualization/jobs/022-framebuffer-handoff/RESULTS.md`.

M5 owns the completed DT-only package and regression. M1 owns offline intake,
one bounded live controller invocation after readiness and human lab selection,
sanitized screen/checkpoint evidence and original-macOS return. Do not reinstall
m1n1 or repeat Recovery. Download/verify before restart; no extra readiness
round trip through the M5 agent is required once intake and policy checks pass.
Use a separate attempt-3 record; preserve prior failures. Keep original Full
Security and the existing single-core RAM scope. No automatic retry.

Policy prerequisite is now satisfied. At this update, GitHub main still ends at
`bf79263`, with no M1 boot022 intake report visible. M1 can complete intake and
confirm readiness directly to the human; do not request the same M5 policy
check again before this attempt. No new boot or settings change was performed
while recording the supplied result.

### Historical M1 result — Stage B attempt 2 stopped; return confirmed, 2026-10-13

* One corrected attempt at `993a6af`: **exit 1, 10.202 s**, UTC
  2026-10-14 01:58:58.489367–01:59:08.692220. Package/primary/target checks
  passed; corrected ADT root access and initial board/framebuffer checks passed.
* RAM payload upload completed. Prepared-DT validation stopped with exact
  **`no enabled boot framebuffer; observation path absent`** at `fdt.py:90`,
  called by `launch.py:113`. No Linux handoff or `kboot_boot`; **Linux NOT RUN**.
  Live packaged-marker verification PASS. Missing versus disabled/mismatched
  framebuffer node remains unresolved; no raw target DT was retained.
* Human confirms return to the usual **Macintosh HD desktop**. Photo shows
  m1n1 DT preparation ending at `FDT prepared` (address omitted), consistent
  with the controller's subsequent rejection. A freeze is not established.
  Linux NOT RUN; fresh build/default/protection checks NOT CHECKED this attempt.
* Boot021, launcher and clean client pin unchanged; no volume/security/default/
  boot-object changes, no reconnect or retry. Existing offline tests remained
  valid and post-pull package verification passed. Attempt 1 evidence preserved.
* Separate sanitized result: `native/boot/stage-b-2026-10-13-attempt2-result.md`.
  Next: M5 read-only return checks and offline framebuffer investigation.
  The one corrected attempt is consumed; no further live session authorized.

### Consumed M5 handoff — corrected Stage B attempt 2, 2026-10-13

The user requests review, next-boot preparation and repository instructions
for M1 after the lab boot. B reviewed/fast-forwarded `fff8b95` and `1635ff0`:
attempt 1 failed before upload/handoff; the ADT root-lookup defect is confirmed
against the pinned source. Keep its original evidence immutable. Linux NOT RUN.

The next step is one fresh Stage B attempt with M1's corrected launcher. This
current user direction authorizes that reviewed continuation, not an automatic
retry of the consumed attempt. Original Full Security, no volume/security/
boot-object/default changes, no SMP or storage expansion. No repeat approval
or redundant readiness-message round trip is needed for this exact scope.

M1's 31+4 corrected-code tests and unchanged USB/intake readiness remain valid;
B independently reran 31 launcher cases, checked the ADT API, and verified the
real package. Launcher/payload/pin unchanged by B. Read-only M5 checks: original
Macintosh HD/build 25G83, original System/Data FileVault, SIP/authenticated-root,
AC, no project VMs, staged m1n1 hash match. The user supplied fresh read-only
original Full/lab Permissive JSON, both exit 0. Default/installed-object checks
were not rerun and are not inferred from this policy result.

Human may shut down and pick iLinux Boot Lab once. M1 then pulls/reads
`tools/m1n1-client/stage-b-instructions.md`, confirms listed source hashes/pin
and offline package verification, creates a distinct attempt-2 evidence record,
and executes the launcher once after the human reports proxy ready. Record the
new RAM-utility/ADT checkpoints as well as screen milestones, stop at the
specified bounds and return to Macintosh HD. Publish sanitized actual results.
No new native action occurred in B's review; attempt 2 remains NOT RUN.


### Historical M1 result — 2026-10-13: Stage B attempt 1 failed; return confirmed; ADT lookup fixed offline

* Single authorized launcher attempt at `fff8b95`: **exit 1, 1.135 s**, UTC
  2026-10-14 01:38:53.644283–01:38:54.779211. Package/USB identity and target
  chip/packaged-marker/secondary checks passed; **KeyError** before board/
  framebuffer confirmation, payload upload or Linux handoff. No retry.
* Live packaged m1n1 marker check is now **PASS**. **Linux remains NOT RUN**;
  kernel/PID 1/one-CPU/60-second screen milestones were not reached.
* User reported “heap limit” (normal utility setup output in pinned source)
  and confirms return to Macintosh HD. New post-attempt build/default/security
  checks are not reported. No volume/security change, no reconnect during diagnosis.
* Offline: confirmed `utils.adt["/"].compatible` misuses the pinned ADT API;
  root access is `utils.adt.compatible`. Corrected locally, retained board/CPU/
  DT gates and added real pinned-parser regressions with synthetic data.
  **31 launcher + 4 new ADT tests PASS; real package offline verification PASS**.
* The defect matches the live checkpoint/type, but the raw exception argument/
  traceback was not retained, so the precise live throw site remains uncertain.
  Boot021/client pin unchanged; fix has not been tried on hardware.
* Full sanitized result/investigation: `native/boot/stage-b-2026-10-13-result.md`.
  M5 should review and perform read-only return checks. **No retries**; current
  task is offline diagnosis/reporting, not a new boot authorization.

### Historical M1 readiness — 2026-10-13: ready for the authorized Stage B attempt

* Pulled/read authorization `b06c56e19a172771866c6e8c8c9a490db105cc84`
  and the exact Stage B checklist. User authorizes one RAM Linux attempt after
  this readiness report, then Macintosh HD return, preserving original Full
  Security with no volume/security changes, retries or additional setup.
* Documented offline launcher verification **PASS**. **31 launcher, 20 USB
  (including four upstream fake-transport cases), and 7 intake tests PASS**:
  58 cases total, each suite exit 0. No device was opened by these tests.
* Rechecked all **13 received boot021 files** against the retained receipt and
  SHA256SUMS against the tracked digest
  `9d2b9ec1ae9dad601fb25a6536e838b57ab436160ab6ceddf208b764de41f581`.
  Payload/receipt unchanged; client clean/pinned to
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
* Launcher SHA-256:
  `96af0a81b332376d5707a8e0d52aab6aca08959743d41f510b994772ed0f8364`.
  Shared USB selector SHA-256:
  `72cc8c2a916b8964b2e4b5afc4c1aac22fe8031a2c2f8658df6882b063a47137`.
* Prepared fresh ignored `build/native-intake/results/boot021-stage-b-authorized.md`
  from the current template, plus a sanitized JSON record. They retain Git/code/
  procedure/package provenance and prior Stage A PASS separately. Prior screen
  preparation is historical; this authorized-session record is current.
* **Ready for the authorized Stage B attempt.** M1 will guide one lab boot,
  execute the documented `--launch --device auto` command once after the human
  reports m1n1 running, observe checkpoints/screen milestones, then guide return.
  No separate handshake, upstream shell/launcher or secondary startup.
* At this readiness checkpoint **Stage B/Linux and live target-version checks
  remain NOT RUN**. Runtime checks occur only during the authorized attempt.
  The controller deadline is 180 seconds; screen observation ends at the
  60-second liveness message, explicit failure or 120 seconds after handoff.
  M5 read-only return verification follows the user's return report.

### Consumed authorization — one Stage B attempt after M1 readiness, 2026-10-13

The user explicitly approves one Stage B Linux RAM boot after M1 confirms
readiness, then return to Macintosh HD. Keep Macintosh HD at Full Security;
no volume/security changes. This supersedes earlier Stage B permission holds
for this exact session. No repeat permission question is needed.

M5 preparation: current root Macintosh HD, original System/Data FileVault on,
build 25G83, AC power, no project VM processes, staged m1n1 matches boot021.
The user's fresh original Full/lab Permissive result from the preceding turn
remains the policy baseline. No code/payload changed since `e2c0cc7`; the
existing M5 test results apply, with no redundant run.

At this preparation checkpoint no M1 readiness commit after `e2c0cc7` is
visible on GitHub. M1 must pull this authorization, complete/report 31 launcher,
20 USB and 7 intake cases plus package verification, and confirm ready before
the human shuts down M5. Use `tools/m1n1-client/stage-b-instructions.md` for
one `--device auto` launcher attempt with the existing boot021/client pin.
No separate P_NOP, retry, shell, SMP start, installation or Recovery operation.
Stop at success/failure/time bound, return via the held-power picker to
Macintosh HD, and publish sanitized actual results. Linux remains NOT RUN
until observed; the M5 agent has not restarted or opened USB during preparation.


### Current M5 handoff — Stage B prepared offline, 2026-10-13

B reviewed/integrated `974e894`: Stage A P_NOP PASS and user-confirmed desktop
return. Read-only M5 checks now confirm original build 26.6.2/25G83, original
System/Data FileVault, SIP/authenticated-root and unchanged staged m1n1 hash.
The user's fresh post-return JSON reports original Full/lab Permissive, both
exit 0; B reviewed that output, not an independent privileged rerun. Default
startup selection and the installed boot object were not newly inspected.

B fixed Stage B's stale P_01 filename gate by sharing M1's descriptor selector
through `tools/m1n1-client/usb_identity.py`. Use `--device auto`; no guessed
path, second-port probing or fallback. Serial-init failures close the port,
transport errors redact identifiers and safe launch checkpoints aid diagnosis.
The boot021 payloads, manifest, pin and CPU/DT restrictions remain unchanged.
31 launcher, 16 stdlib identity/CLI and 7 intake tests pass; local payload
verification PASS. No native Linux or new live USB test ran.

M1 may now pull and perform the offline checks in
`tools/m1n1-client/stage-b-instructions.md`, including all 20 USB cases with
its prepared upstream client environment. Record readiness and preserve the
completed Stage A result. Wait for the human's explicit Stage B approval and
readiness before any restart/launch. Stage B is one RAM Linux attempt, no SMP
start, disabled Linux NVMe/cpufreq, PID 1/one CPU/60-second screen liveness,
then Macintosh HD return. No Recovery/reinstallation/security change required.
B owns subsequent target-specific kernel/DT diagnosis and CPU/power REA work;
M1 owns physical-session coordination/results, C waits for tested Linux access.

### Current M1 handoff — 2026-10-13: Stage A P_NOP passed; Macintosh HD return confirmed

* User started a new Stage A attempt after checker fix `70ad452`. On M1,
  discovery and connection-time re-identification found **one primary** among
  two modem interfaces: **VID/PID 1209:316d, CDC data interface 1**. No callout
  names, serial numbers or raw registry output are retained in the handoff.
* Actual command: `tools/m1n1-client/run.sh tools/m1n1-client/usb-check.py --connect`.
  **PASS, exit 0; one P_NOP replied in 0.158 seconds**, within the 10-second
  deadline. UTC start **2026-10-14T01:13:02.764830+00:00**, end
  **2026-10-14T01:13:02.922801+00:00** (2026-10-13 evening in America/New_York).
  The port closed; no retries, feature negotiation, memory/register requests
  or boot/launcher requests were sent by M1.
* After the guided power-off/held-power picker return, the user confirmed:
  **back at the usual Macintosh HD desktop**. This is user-observed return,
  not remote M5 inspection. Current build, default selection and protection
  states have not been freshly rechecked after this attempt. Earlier original
  Full/lab Permissive and FileVault/SIP/authenticated-root results are baseline.
* Local sanitized evidence: ignored
  `build/native-intake/results/stage-a-20261014T011302Z.json`, now updated with
  user-confirmed return. Boot021, original intake receipt and clean client pin
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba` are unchanged.
* This validates descriptor-based primary selection and a responding m1n1
  proxy on this setup. **Live target-version verification, Linux/Stage B and
  native Omarchy remain NOT RUN.** No runtime-version or Linux compatibility
  claim follows from P_NOP. No new test was run for this documentation update.
* M5 agent next: review the evidence and perform the planned read-only return
  checks. Stage A handshake and desktop return succeeded; do not repeat setup
  or automatically start another boot. Stage B requires separate authorization.

### Earlier M1 handoff — 2026-10-13: Stage A stopped before handshake; USB naming fixed offline

* Controlled M5 m1n1 boot reached `Running proxy...` (user/screen observed).
  M1 discovery saw two modem callouts, but neither matched the checker's
  hard-coded `P_01` suffix. No serial port was opened and no P_NOP was sent.
  This was an identification stop, not a failed USB exchange. User confirms
  subsequent return to Macintosh HD. No fresh post-attempt protection check
  or default-selection check has been reported; the earlier checks are baseline.
* Pinned m1n1 source explains the assumption: `usb_build_serial()` uses the
  ADT serial when available; `P-0` is only the fallback. Descriptors identify
  VID/PID 1209:316d, primary CDC control/data interfaces 0/1 and secondary
  virtual UART 2/3. `usb.c` assigns the primary pipe to console/proxy. USB0,
  USB1 and USB2 screen labels do not identify the host CDC callout role.
  No actual callout names or photographs are retained in the repository.
* Fixed the local checker to walk cached macOS IORegistry USB ancestry and
  require exactly one matching primary data interface 1/class 0x0a. Missing
  metadata, unrelated devices, secondary interfaces, ambiguity and stale or
  linked/non-device paths stop before opening. There is no filename fallback.
  Bare `--connect` re-identifies the sole primary; paths/serials/raw registry
  stay in memory and are not printed or saved. Printed results include UTC
  start/end and elapsed time for the eventual single handshake.
* Validation: **20 offline tests pass**, including synthetic fallback and
  serial-derived names, secondary/wrong/missing/ambiguous identity, stale paths,
  privacy, no-open discovery and no retries. Fake transport verifies one
  serialized P_NOP with zero arguments, the 10-second alarm and closure on
  success, timeout and initialization error. M1's read-only discovery with
  M5 back in macOS finds no primary and stops without opening any port.
* Boot021, ignored intake receipt and clean client pin
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba` are unchanged. No target commands,
  security changes, installations or boots were performed during this repair.
* **NOT RUN:** live USB/P_NOP, live target-version verification, Linux and
  native Omarchy. The new metadata mapping is offline-tested, not yet verified
  with M5 in m1n1. This request prepares another Stage A attempt; do not start
  one automatically. When the user starts the next session, use the revised
  checklist, one bounded handshake without retries, then original-macOS return.

### Prior Stage A authorization — session ended before handshake, 2026-10-13

The user explicitly approved **one m1n1 boot, one USB handshake, then back to
Macintosh HD**, keeping Macintosh HD at Full Security. This supersedes earlier
Stage A approval holds; no repeat approval is needed for this exact scope.
Follow `tools/m1n1-client/stage-a-instructions.md`. Stage B/Linux, upstream
shells/launchers, register/memory requests, policy changes and reinstallations
are outside this session.

M5 checks: current root Macintosh HD/FileVault on, staged m1n1 hash/size match,
AC power, no project VM processes. Fresh original Full/lab Permissive policy
result was supplied by the user in the preceding turn. Artifacts are unchanged;
existing offline tests/receipt remain applicable, no redundant test run.

M1 pulls this handoff and confirms ready before the user shuts down the M5.
Use the held-power picker, **iLinux Boot Lab → Continue**, leaving Macintosh
HD as default. On M1 discover the actual primary port and run the existing
10-second-bounded P_NOP checker once. Record actual outcome; no retries. After
success or failure, power off M5, use the held-power picker for **Macintosh HD
→ Continue**, then verify return/protections and publish sanitized results.
All Stage A results are still **NOT RUN** until observed. The M5 agent has not
restarted this computer or opened any USB connection during preparation.

### M5 review after return — 2026-10-13

B reviewed and fast-forwarded M1 report `c6f2c6f`. Native m1n1 reached
`Running proxy...` by the screen evidence reviewed by M1; that is an actual
bootloader milestone on this unit. USB/P_NOP and Linux remain NOT RUN.

Read-only M5 checks now independently confirm original root **Macintosh HD**,
**26.6.2 / 25G83**, original System/Data FileVault enabled, SIP enabled and
original authenticated-root enabled. The csrutil installation menu changed
order between queries: choose by the name in the same live prompt, never by
a cached number. Staged m1n1 size/hash still match; the installed boot object
was not separately read. Default restoration remains the user's observation.

The user supplied the fresh post-return helper result: **original Full / exit
0; lab Permissive / exit 0; read_only true**. This completes the return-policy
check; B did not independently rerun the privileged query. The M5 local helper
now accepts `--expected-lab Permissive` so the intended lab policy is not
mistaken for a failure. No policy/startup/payload changes were made this review.

Next session is now authorized above: the existing Stage A checklist, one
bounded P_NOP on the actual primary M1 USB path, then return to Macintosh HD.
The installed entry is ready for that test; no Recovery/reinstallation
is needed for the planned boot. After Stage A, review and authorize Stage B's
one-core RAM Linux/PID-1/60-second heartbeat diagnostic. Native desktop,
peripheral functionality and performance parity remain unvalidated.

### Current M1 handoff — 2026-10-13: lab m1n1 installation and original macOS return complete

Evidence: human-entered commands on the M5, user-reported results and screen
photos reviewed by M1; no remote M5 query by M1. Only sanitized conclusions
are retained. Raw photographs, policy identifiers and credentials are not copied.

* Lab desktop build confirmed **26.6.2 / 25G83** before paired Recovery.
  Staged helper SHA-256 matched
  `e65636d03cfb7a7000f86810fdc8888e209b99bedaa1b36ca7a125de4bf72188`.
  Recovery lacked `shasum`; a temporary same-shell function accepted only
  `shasum -a 256 FILE` and delegated to `/sbin/sha256 -q`. No helper file
  or system tool was modified. The helper/payload checks then passed.
* Read-only preflight: **exit 0; original Full; lab Full; lab paired 1TR**.
  An initial mistyped readiness variable stopped the guarded operation;
  the corrected command subsequently reached authentication and succeeded.
* Authorized lab policy update succeeded: **lab Permissive, kernel CTRR
  Disabled**, with helper postcheck **original Full / lab Permissive / paired
  1TR**. The guarded installation rechecked policy and payload before kmutil.
* User reports **kmutil exit 0; Installed yes**, and final policy check
  **original Full / lab Permissive**. This completes boot-object installation.
* **Incidental m1n1 startup observed:** user released the power button early
  during the return sequence. Their photo shows m1n1 screen output/logo and
  `Running proxy...`. User reports promptly powering off, then successfully
  returning to the usual Macintosh HD desktop and selecting **Macintosh HD
  as the default startup disk**. This is screen evidence of m1n1 execution,
  not a completed Stage A test or evidence of Linux execution. Duration and
  exact running version were not verified; USB initialization text does not
  establish a controller connection or a successful P_NOP exchange.
* **NOT RUN:** live USB connection/P_NOP, live target-version check, Stage A
  controlled handshake, Stage B/native Linux and native Omarchy. No launcher
  was run by M1. No Linux boot, liveness or performance result is claimed.
* Boot021 package/ignored intake receipt are unchanged. M1 rechecked the clean
  client pin: `57a9339ffd1876e78297b17d34dece8cff8fa1ba`. No new offline
  test run was needed for this documentation-only update; prior results stand.
* Next: M5 agent reviews this handoff and can verify original macOS protections
  read-only after return. The Full/Permissive result above was observed in
  Recovery after installation; post-return policy/SIP/FileVault checks have
  not been newly reported. Do not repeat installation. Wait for explicit
  Stage A authorization before any controlled m1n1 boot or USB connection;
  Stage B requires its own approval.

<details>
<summary>Historical preparation handoff (superseded by the execution results above)</summary>

### Current authorization: lab-only Recovery policy and m1n1 installation

The user explicitly authorized lab-only Recovery setup, Permissive Security,
disabling kernel CTRR and installing the verified m1n1 boot object, while
keeping **Macintosh HD at Full Security**. This supersedes prior security and
custom-boot holds for this exact lab scope. No repeat approval is needed.
B prepared/staged a tested read-only Recovery helper and the one-operation-
at-a-time instructions. M1 guides the human on the M5 through sections 5–6 of
`kernel/native-enablement/boot-entry-setup.md`, records actual results and helps
return to original macOS. M1 must not run the M5 commands on itself.
Stage A/P_NOP and Stage B/Linux testing are still not authorized by this setup.

**Observed progress:** B created the unique empty APFS lab volume, preserving
the original volumes' names/roles/FileVault states. Original policy reports
Full Security; SIP/authenticated-root enabled. Repeated installer verification
PASS. Normal GUI launch succeeded; after the user authorized its license, B
selected and visually verified **iLinux Boot Lab** as destination.

**M1 return handoff (user-observed):** the user completed installation/setup,
reached the lab desktop and reported `sw_vers` **26.6.2 / 25G83**, then confirmed
successful return to the usual **Macintosh HD** desktop. These observations
establish lab first boot and return; M1 has not remotely inspected the M5.
B reviewed/integrated M1 report `f34970e` and independently confirmed current
Macintosh HD build 26.6.2 / 25G83, FileVault/SIP/authenticated-root enabled,
and a separate mounted lab System/Data group with the same installed build.
The user subsequently ran the read-only policy helper and supplied its JSON:
**original Full / exit 0; lab Full / exit 0; read_only true**. B reviewed this
user-provided result; it is not an independently rerun query or an inference
from the pre-install baseline. This resolves the pending policy read.
B has now staged the exact m1n1 binary at
`/Volumes/iLinux Boot Lab - Data/Users/Shared/iLinuxBoot/m1n1.bin` after
rechecking the lab System/Data roles and separate volume group. The reread
copy matches the tracked manifest: 3,932,160 bytes, SHA-256
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
Only the new staging folder, m1n1 and now the read-only `recovery-preflight.sh`
were created on lab Data; no existing file was overwritten. Helper SHA-256:
`e65636d03cfb7a7000f86810fdc8888e209b99bedaa1b36ca7a125de4bf72188`.
Its 21 preflight cases, seven documented-operation guard cases and syntax checks
pass with stand-ins; no real policy writes were tested. Current root and payload
were rechecked; AC power, no project VM processes. System Settings already
shows **iLinux Boot Lab** selected. B opened the pane but did not change its
selection or click Restart. No security/custom-boot change has run yet.
Boot021 and the existing client pin are unchanged.
Live USB/P_NOP, live target-version check, native m1n1/Linux/Omarchy remain
**NOT RUN**. Current handoff: `kernel/native-enablement/boot-entry-setup.md`.

**Next human/M1 session:** pull this handoff before restarting. Boot lab macOS,
shut down and enter its paired Recovery with one continuous power hold. Run
the helper and gated policy/install commands; verify original Full/lab
Permissive and actual kmutil exit. Stop on failures without bypass/retry loops.
Return via the picker to Macintosh HD and restore it as default. Publish only
sanitized observed outcomes. Stage A later tests only m1n1/P_NOP; Stage B separately
tests one-core Linux PID 1 and 60-second liveness. The result template now
separates controller output, screen observations, timing and macOS return.
No persistent USB Linux console or SSH is present. Blank screen means output
not observed; establish logging before another blind attempt.

**M1 offline preparation complete:** `tools/m1n1-client/stage-a-instructions.md`
contains the later authorized handshake checklist. Stage B evidence draft is
local/ignored at `build/native-intake/results/boot021-stage-b-prepared.md`,
pre-filled from the current template and verified package with provenance,
expected milestones and timing bounds. All 13 payload checksums still match;
boot021 and the clean client pin are unchanged. M1 read B's policy-result
handoff at `1607f2a`, without an independent target query. B integrated M1's
`1420572` report. Lab Recovery installation is now authorized as stated above;
live Stage A/B approvals remain pending. All live USB/target-version/native
tests are **NOT RUN**.

</details>

### Current boot-package assignment (user authorized 2026-10-13)

B now owns preparing/exporting the boot package, correcting the single-core
launcher and first-boot instructions, testing them in isolation and pushing
the M1 handoff. Work is in `native/boot/` and job 021; A's QEMU/latency work
is untouched. The M1 agent downloads/verifies and reports offline readiness.
**Earlier package-only boundary, superseded by the current lab authorization
above.** Partition changes and live native tests remain on hold.
Payload publication is authorized; these are open-source
build outputs, not Apple artifacts. Follow the corrected first-boot plan;
older statements about an empty APFS stub or persistent proxy console are
superseded. No native hardware success is claimed by this handoff.

B's next preparation milestone is complete: the user requested exact dedicated
entry steps while M1 verifies. `kernel/native-enablement/boot-entry-setup.md`
selects a second full macOS installation named `iLinux Boot Lab`, matching the
available 26.6.2 / 25G83 installer. It documents paired-Recovery checks,
lab-only policy/boot-object commands and macOS return. At that preparation
milestone no volume creation, policy change or reboot had run. The current
handoff above records subsequent installation and authorization; an offline
receipt alone does not authorize host changes.

**Download and verification result:** the matching 26.6.2 / 25G83 installer is
downloaded. User subsequently authorized resolving verification without
disabling security checks. Its original package passes Apple's signature and
Gatekeeper install assessment; all five signed entries and the installed
695 files/226 directories/26 symlinks match. Three executable signature checks
and eleven synthetic verifier regressions pass. The outer app's custom-omit-
rule rejection remains unchanged; no security exception or bypass was used.
See `native/boot/macos-installer-download.md` and D-046.
M1 has now published its observed offline results below and in `progress.md`.
USB/P_NOP, live target-version check, native m1n1, native Linux and native
Omarchy remain **NOT RUN**. The current authorization above supersedes the
earlier installer-launch and lab boot-security holds; native-test holds remain.

### M1 offline receipt: ready for coordination, physical testing on hold

Verified handoff commit: `58dc2baffceda76d546b0e6fb8f101089dfd35b8`.
Private prerelease `native-j716c-boot021` was downloaded and its archive
SHA-256 matched Git before extraction:
`b534680fc25dff78d8eaecfb96ed5b9733a3f408ae20cb4947722cb8163edc15`.
Offline launcher and intake verification passed for all 13 files; SHA256SUMS
matched tracked digest
`9d2b9ec1ae9dad601fb25a6536e838b57ab436160ab6ceddf208b764de41f581`.
Tests passed: **17 launcher, 7 intake, 2 fake-serial USB**. LLVM 23.1.3 passed
ARM64 assembly/link/objcopy/nm/disassembly. The clean client remains pinned
to `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.

M1's complete JSON receipt is local and ignored:
`build/native-intake/receipts/boot021.json` (2026-10-13 20:02:34 UTC).
It records `boot_authorized: false` and `target_version_observed_live: false`.
There are no offline verification blockers. USB discovery opened no port and
found no modem paths; it does not establish cable status. First live test is
still the separately authorized bounded handshake. Boot-entry provisioning
and explicit physical-test approval remain pending. B reviewed and integrated
this report (`dfdf8cf`) while completing installer content verification. The
subsequent normal GUI launch succeeded; installation is pending as recorded above.

### Second-machine checkout (2026-10-13)

The user designated a separate macOS computer as the second-machine agent.
Its checkout is `~/Documents/ilinux`, tracking the private
`https://github.com/nickyrice04/ilinux.git` repository. GitHub authentication
as `nickyrice04`, fetch access and account push permission are verified.
This role is distinct from research agent B and post-boot configuration
agent C. It supports the m1n1 USB proxy and cross-machine handoffs; USB
connectivity and native boot have not been tested by this setup.

The user explicitly authorized repository pushes for agent communication,
superseding the older local-only Git rule. Fetch and use `git pull --ff-only`
before work, commit explicit paths, then push without force. If another
machine advances the branch, fetch and reconcile before retrying; never
reset away another agent's work. Local advisory locks do not coordinate
separate computers: record ownership and handoffs here before shared work.
Credentials remain in the OS credential store, never in tracked files.
Ignored VM disks, build payloads and local third-party checkouts are not
downloaded by Git. Proxy-client dependencies now pass offline imports; see
`tools/m1n1-client/README.md`. LLVM 23.1.3 now passes offline ARM64 assembly,
link and disassembly. A bounded P_NOP-only USB check is prepared and fake-
transport tested. Physical connectivity and target boot-entry readiness
remain unverified; no target session has run.

**User direction (2026-10-13, package handoff):** the second-machine agent has
received B's corrected single-core package/launcher and completed offline
verification only. Keep the client pinned to the agreed target revision.
Do not run upstream `proxyclient/tools/linux.py`. First live test is the
separately authorized bounded USB handshake; thereafter record only approved
diagnostic boots. Intake requirements and the result template are in
`tools/m1n1-client/README.md`; current package instructions are in `native/boot/README.md`.

| Agent | Who | Owns |
|---|---|---|
| **A** | The session that wrote this plan (`AGENT_ID=agent-a`) | VM responsiveness: goals 2–3. QEMU source and patches (`virtualization/qemu/src/qemu`, `patches/qemu/`), the VM kernel config (`omarchy-arm64/kernel/linux-ilinux-vm/`), latency benchmarks |
| **B** | The second build agent (`AGENT_ID=agent-b`) | Goals 4–7: video default, native readiness (`kernel/`, new `virtualization/jobs/`), backup preparation, the configuration handoff kit |
| **C** | A configuration agent, later | Omarchy configuration on a natively booted install (goal 9). Starts only after gate N4 |

The user makes every gated decision (N1–N4 below). No agent changes boot
security, partitions, firmware or the macOS installation.

### Agent B scope update from the user (2026-10-13)

The user has directed B to focus on REA/backend setup and targeted macOS
binary research, with an evidence and implementation handoff for A. B will
leave A's wakeup, QEMU and display work untouched and defer live-guest video
changes while A owns that VM. B's current files are under
`reverse-engineering/rea-lab/` and
`reverse-engineering/findings/rea-native-2026-10-13/`. Analysis tools will run
in a separate diskless Linux job, never against the live Omarchy disk.
Build/analysis jobs must acquire `quiet` so A's measurements do not overlap.
The agent C configuration handoff remains required before native desktop use.

B milestone: REA/Ghidra works; original extraction/evidence tools and a
read-only startup-layout experiment pass ARM64 Linux tests. See
`reverse-engineering/findings/rea-native-2026-10-13/handoff.md` (F-070–F-072).
The analysis VM is stopped and B's locks are released. A's live VM, QEMU,
vmpoll and frame-rate work remain A-owned. The candidate native masks are
not validated MMIO semantics and must not be installed as a hardware fix.

B's next user-authorized pass covers GPU/display, network/Bluetooth, ANE's
ordinary host interface, camera, audio/microphone, HID input and shared
transports. Findings live in `reverse-engineering/findings/driver-interfaces-2026-10-13/`;
original protocol experiments live in `kernel/experiments/driver-contracts/`.
B retains the isolated lab and does not own A's live VM/video changes.
Protected services and personal sensor recordings remain excluded.

B completed F-073–F-075: 17 REA functions, independent byte/LLVM evidence,
a Linux-tested DockChannel HID patch and original offline N1 ACIPC queue
helpers. Full handoff: `reverse-engineering/findings/driver-interfaces-2026-10-13/handoff.md`.
The lab is stopped and B's `quiet` lock released. A's goal-5 native build
can apply `kernel/experiments/driver-contracts/dockchannel-hid/0001-dockchannel-hid-validate-input-bounds.patch`
to a disposable checkout and compile the full driver object. Do not install
it in the VM's virtio-input path or advertise native input as tested.

## Shared resources: rules

### Current assignment (user confirmed 2026-10-13)

A owns goals 5–7: the complete native kernel/schema build, first-boot
observation plan, backup preparation and C's configuration handoff. Goals
2–3 are checkpointed unless they block native development. B owns targeted
REA work on CPU startup, GPU/display and idle/DVFS, with original offline
experiments and findings for A. The older owner table and goal ordering
below are historical where they conflict with this assignment.

B's completed startup/idle pass is recorded in
`reverse-engineering/findings/cpu-startup-2026-10-13/`. Its optional startup
guard passed eight Linux cases with sanitizers and startup-object compilation;
the analysis VM is stopped and B's locks are released. B has not modified A's
kernel build jobs, native payloads or handoff kit. The dockchannel proxy is
not established as a Linux console; early-boot observability remains a
goal-5 prerequisite.

1. **Locks** (`tools/lock.sh`, advisory, stored in the gitignored
   `virtualization/run/locks`):
   * `vm`: hold it for any QEMU Omarchy VM console command, restart, or
     install into the guest. `tools/vm-restart.sh` refuses to restart while
     another agent holds it, so export `AGENT_ID`.
   * `quiet`: hold it for power and latency measurements. While someone holds
     it, nobody else builds, benchmarks or restarts a VM. Keep it short
     (usually 30 minutes or less); measurements are invalid without it.
   * `qemu-build`: QEMU and virglrenderer builds and `runtime/` installs.
   * `git-history`: history rewrites. Only with the user's OK, and only while
     no other agent is committing.

   Run `tools/lock.sh status` before heavy work. Release locks as soon as you
   are done. Never clear another agent's lock unless it is stale and the
   user agrees.
2. **Git:** one shared working tree and branch. Commit with explicit paths
   only: no `git add -A`, `git add .` or `git commit -a`. Never commit another
   agent's uncommitted files. Use the attribution line from your session
   instructions.
3. **Shared docs** (`progress.md`, `decisions.md`, the findings catalog,
   `blockers.md`, READMEs): re-read right before editing, make small
   targeted edits, and never rewrite a whole shared file from a stale copy.
   Each agent writes its own progress entry.
4. **ID ranges:** agent A uses F-054–F-069 and D-032–D-039. Agent B uses
   F-070–F-089 and D-040–D-049. Agent C uses F-090 and up, and D-050 and up.
5. **Native kernel builds** run in the separate job VM
   (`virtualization/jobs/`). They load the host heavily, so never run one
   during someone else's `quiet` window.
6. **The floating VM window** (`COCOA_FLOAT=1`, which keeps the VM window on
   screen) is for on-screen measurements only. Tell the user before a session
   that uses it.

## Goals, in order

| # | Goal | Owner | Done when |
|---|---|---|---|
| 1 | Commit the verified Mesa video work | A | Done: `47efd62` |
| 2 | **Cross-core wakeup latency.** Message passing between two processes takes 1.6 µs on one vCPU (macOS: 3.8 µs) but about 21 µs across vCPUs. QEMU uses Apple's hardware GIC (`kernel-irqchip=on`), so the leading suspect is an idle vCPU being parked and then woken through the macOS scheduler. Bounded spinning before parking (in QEMU's HVF idle path, and/or the guest's `cpuidle-haltpoll`, which our kernel does not build) is the candidate fix. Note: arm64 7.1.6 ignores `idle=poll` | A | Cross-vCPU pingpong and syscall improve measurably; idle power is unchanged within noise; the poll window is bounded and documented; new QEMU patch or kernel config committed |
| 3 | **F-050 frame-rate collapse:** 7–19 fps on alternating fresh boots. Re-test after goal 2, then trace DRM flips, fences and Hyprland frame callbacks during an affected boot | A | Cause identified with evidence; fixed or documented with a workaround |
| 4 | **Video fix as the default** (`mesa-virgl-video-ilinux`, now opt-in via `ilinux-video`). Do an on-screen playback and power check first | B | Plain `mpv`/FFmpeg use the fixed driver; pixel-exact and zero-copy regressions pass |
| 5 | **Native track, safe steps:** full kernel build and `dtbs_check` for `kernel/patches/t6050` in the job VM; a written first-boot plan (see gates) | B | Kernel links; schema warnings triaged; plan committed |
| 6 | **Backup preparation:** a scrub list (local paths, the test VM password), licences (GPL-2.0 for QEMU patches, MIT for virglrenderer and Mesa patches, a choice for our own code), and a plan to remove the 640 MB of Core ML weights from history or start fresh from a clean snapshot | B prepares; user approves; `git-history` lock to execute | Private repo ready to push on the user's go-ahead |
| 7 | **Configuration handoff kit for agent C** (below) | B | `native/handoff/` committed and reviewed by A |
| 8 | Native gates N1–N4 (below) | User decides; then A and B | Per gate |
| 9 | **Omarchy configuration on the native install** | C | Acceptance checks in the handoff kit pass |

Agents may pull work forward when blocked, but keep goal 2 before goal 3 (3
re-tests 2). Keep goal 4's guest changes out of the VM while agent A holds
the `vm` lock.

## Native gates (all user decisions)

* **N1. Prerequisites.**
  * A current full macOS backup (Time Machine or equivalent).
  * A second computer and a USB-C data cable for the pre-Linux m1n1 proxy.
    Native Linux output is initially attempted on the M5 framebuffer;
    no persistent USB Linux console is established.
  * A separately reviewed and authorized OS boot environment with Apple boot
    assets, paired recovery and its own custom boot policy. An empty APFS
    volume is insufficient. Exact layout and installation remain gated; see
    `kernel/native-enablement/first-boot-plan.md`.
* **N2. RAM-only boots** over USB from the second computer: kernel,
  initramfs and device tree, with nothing written to the Mac's disk. In
  order:
  1. single-core console;
  2. secondary CPU start-up (SMP);
  3. NVMe read-only identification;
  4. keyboard and trackpad;
  5. boot framebuffer.
* **N3. Linux root partition.** Resizing the APFS container is a separate
  user decision, made after another backup.
* **N4. Omarchy installed natively.** Hand over to agent C with the kit.

## Configuration handoff kit (goal 7, for agent C)

Agent B writes it in `native/handoff/`. It must cover:

1. **VM-only files that must not be applied natively:**
   * `omarchy-arm64/configuration/vm-integration/*`: host bridge, vdagent,
     NAT DNS, `MESA_VK_WSI_DEBUG=nowlts`, the VM `mpv.conf`, autologin;
   * the VM kernel package.
2. **What carries over:**
   * `omarchy-qos` and the QoS tiers;
   * kernel options (16 KiB pages, uclamp);
   * the t6050 energy-model and OPP drafts (unvalidated);
   * the aarch64-apple package choices.
3. **A hardware matrix for the boot under test:** what works, what is
   absent, and the fallback for each absent device:
   * llvmpipe instead of GPU acceleration;
   * USB Ethernet or tethering for networking, since N1 Wi-Fi has no driver;
   * an external libfprint reader or FIDO2 key instead of Touch ID;
   * no Neural Engine.
4. **Access:** how agent C reaches the system. It needs network for itself:
   USB Ethernet, or running from the second computer over the serial or
   SSH link.
5. **Acceptance checks:**
   * all 18 CPUs and their capacities;
   * storage health;
   * display and input;
   * audio;
   * idle power with the WFI workaround in place;
   * suspend (expected not to work yet);
   * Omarchy's own test suite where applicable.
6. **Guardrails:**
   * never touch macOS volumes or the APFS container;
   * no firmware, SEP or boot-policy changes;
   * no credential handling;
   * record every change as a package or config file in this repository.
