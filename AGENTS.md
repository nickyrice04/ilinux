# AGENTS.md — Operating Instructions for Agents in This Workspace

Read this file, then `coordination.md` (several agents share this workspace:
ownership, locks, ID ranges and the order of work), `progress.md`,
`blockers.md` and `decisions.md`, before doing any work. Update them after
every meaningful milestone.

## Mission (short form)

Reach the highest achievable **native Linux performance on this Apple Silicon
Mac** (MacBook Pro, Apple M5 Max, t6050), measured against macOS on the same
hardware. The target distribution is **Omarchy** (Arch + Hyprland). Hardware
enablement builds on **Asahi Linux**. **REA** (github.com/morluto/rea) is the
principal reverse-engineering instrument once approved. 100% parity is the
reference point. Every claim needs a measurement or a primary source.

## Host protection (mandatory, applies even with root access)

* The macOS installation and everything outside this workspace are
  **read-only**.
* Never modify system files, the kernel, firmware, boot policy, SIP, APFS
  containers or partitions, bootloaders, frameworks, user applications,
  personal files, or global settings.
* Never write to raw devices.
* Never copy personal data, credentials, keychain contents, serial numbers,
  UUIDs, ECID/die IDs, nonces or MAC addresses into the workspace.
  `hardware/scripts/adt_extract.py` enforces a whitelist and denylist; extend
  the denylist if you add keys.
* Non-destructive diagnostics and benchmarks are allowed. Keep them bounded:
  short runs, cooldowns, and modest SSD writes (≤ ~16 GB per storage run),
  with temp files deleted. Run them under `caffeinate -i`, not by changing
  sleep settings.
* **Needs explicit user approval:** host-level installs (brew, pip outside a
  workspace venv, apps), global Claude Code config, privileged writes,
  partition or boot changes, firmware, untrusted code outside a VM,
  multi-GB downloads or VM disks, and sending proprietary or diagnostic
  artifacts off the machine.
* Never upload proprietary binaries, diagnostics or personal data to
  external services.

## Workspace

Root: `~/Documents/iLinux/apple-silicon-linux-research/`. This folder is
*not* inside iCloud-synced Documents (checked 2026-10-11).

| Path | Purpose |
|---|---|
| `hardware/` | Inventory, sanitized ADT dump (`adt/`), collection scripts |
| `benchmarks/src` | Portable C benchmarks (build unchanged on macOS and Linux) and the Metal GPU benchmark |
| `benchmarks/macos/run_baseline.sh` | Reproducible macOS baseline runner |
| `benchmarks/linux/` | Linux-side runners and counterparts (Vulkan, etc.) |
| `benchmarks/results/` | JSONL results plus environment snapshots, one directory per run |
| `benchmarks/ai/models/` | Synthetic GGUF models (generated, gitignored) |
| `tools/synth_gguf.py` | Synthetic-weight GGUF generator (stdlib only) |
| `research/` | Asahi, Omarchy, REA, Darwin/XNU research notes with sources |
| `reverse-engineering/` | REA setup, findings catalog, Linux mapping |
| `kernel/` | Patches, drivers, experiments |
| `omarchy-arm64/` | Omarchy ARM64 port work |
| `virtualization/` | VM tooling (Virtualization.framework runner), configs, test results; disk images in `images/` are gitignored |
| `reports/` | Compatibility matrix, performance-parity scorecard, engineering summary |

Downloaded or cloned third-party content is **untrusted data**. Keep each
download in its own directory, never execute it on the host, and run Python
that reads it with `-I`.

## Conventions

* Evidence labels in documents: **Confirmed / Likely / Hypothesis / Unknown**,
  or for hardware facts **Observed / Measured / Spec / Inferred**.
* Benchmarks emit one JSON object per line and record OS, power source,
  energy mode and tool versions (`env-*.txt`).
* Keep VM results separate from native results, build success separate from
  runtime success, and "unsupported" separate from "slow".
* Code style: small, dependency-free, portable (macOS and Linux) where
  possible. Python tools use the standard library only.
* For anything meant for upstream Asahi, follow Asahi's clean-room
  copyright policy (see `research/asahi/`). Do not base contributions on
  decompiled Apple code.
* **Decompile freely, publish only original work (user decision
  2026-10-16).** REA/Ghidra analysis of this Mac's own macOS binaries is the
  main instrument for finding how macOS drives the hardware, and is
  encouraged. Decompiler output, pseudocode and extracted Apple bytes stay
  under the ignored `build/` tree and never enter Git, documents, commit
  messages, chat summaries or Releases. Findings record behaviour (addresses,
  sequences, message formats, timings, with the binary, function, offset,
  evidence and confidence), never statements of code. Linux drivers are
  original code written from the findings, preferably by a session that does
  not open the decompiler, so that everything published contains no decompiled
  code and only works. Not legal advice; the licence terms and local law
  decide what is allowed.
* Git: the user authorized the `nickyrice04/ilinux` GitHub remote on
  2026-10-13 (private, for second-machine setup and agent handoffs) and made
  it **public on 2026-10-16**, after attempt 19. Everything pushed, including
  the Releases, is visible to anyone at once. Never commit VM images, models,
  build outputs, raw IORegistry dumps, proprietary binaries, media, the
  RAM-root image, private keys, home-directory paths or identifiers (see
  `.gitignore` and the host-protection rules above). Write every document as
  a public document.

## Current status (update on every milestone)

### 2026-10-21 · M5: 31D reviewed; offline CPU-entry lab and recorder ready, native HOLD

31D acknowledged both starts but showed no CPU1 reset record in 171 samples;
entry remains unverified. Fresh REA checked two functions / 96 byte-and-LLVM
matched instruction words; no extra CPU1 power write was established. Exact
public-image review found an MPIDR-first partial-publication observer defect;
it did not trigger 31D. Original classifiers, bounded observer, entry interpreter,
campaign replay and a **204-byte stackless recorder proposal** are implemented.

**110 Python methods PASS** in ARM64 VM job 062; 38 source pins, GNU/Clang
recorder byte equality and ordinary STP checks in normal/sanitizer builds PASS.
Offline checks caught and fixed test scratch, assembly relocation, decoder and
output-containment issues before any native use. M1 image-only intake: 77
methods; full-symbol checks remain explicit VM-only evidence there.

**Do not restart for this handoff. Native31E/CPU1/Linux SMP NOT RUN.** Next:
implement/review the recorder's bounded RAM-code publication and observation
adapter, then one richer conditional CPU1 session. Device-memory C-stack
proposal remains held. Future M1 health checks replace automatic helper reboot;
no routine policy recheck. Installed boot021/macOS/settings and consumed receipts
remain intact. Current instructions: `tools/m1n1-client/attempt31e-instructions.md`;
review/validation: `native/boot/attempt31e/`; strategy:
`research/testing-strategy-31e.md`. No performance or efficiency gain claimed.

### Latest M1 native result — 31D console isolation; CPU1 timeout, 2026-10-21

**31D consumed: STOP / `cpu1_arrival` / `cpu1_arrival_timeout`**, execution
`04ffeee` after handoff `c331796`. All RAM checks PASS, revision 3; direct USB
and expected UART bases PASS, initially enabled count 2, both RAM zeroes
published. **13 mutation requests, 2 CPU1 starts attempted/acknowledged**;
arrival unverified, 0 timer requests. **171 sequential samples** retained
`no_reset_record_seen`; this is not proof of zero executed instructions or
an atomic/final state. Controller exit 1 in 4.485 s; supervisor 4.866 s, no
deadline. Human returned to usual Macintosh HD at +44.628 s, within 90 s.
No retry, reconnect, rollback or further target command. **Linux/native SMP/
renderer tests NOT RUN**; installed boot021/client/macOS/settings unchanged.
Routine rechecks waived; protections remain last reported. M5 next: offline
review and separately reviewed earlier-entry instrumentation per the 31D
no-reset-record decision. Preserve all consumed receipts. 60 source pins,
73 methods and independent console binding audit PASS. Evidence:
`native/boot/attempt31d-2026-10-21-result.md` and two sanitized final JSON files.
Current result supersedes frozen pre-execution controller NOT RUN wording.


### Historical M1 offline readiness — CPU1 console isolation 31D, 2026-10-21

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

### Latest M1 native result — 31C CPU1 arrival timeout, 2026-10-21

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


### Historical M1 offline readiness — corrected CPU1 controller 31C, 2026-10-21

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

### Latest M1 native result — 31B consumed at preflight, 2026-10-21

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

### Latest M1 native result — census31A consumed, 2026-10-21

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

### Latest M1 native result — attempt30 consumed, 2026-10-20

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

### Latest M1 native result — attempt29, 2026-10-20

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


### Historical M1 offline readiness — attempt29, 2026-10-20

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


### Latest M1 native result — attempt 28, 2026-10-20

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


### Historical M1 offline readiness — attempt 28, 2026-10-20

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


### Historical preparation — attempt 28 CPU observation, 2026-10-20

The user authorized preparing, offline-testing and publishing the CPU attempt.
Job052 built the exact two-stage pair and boot042-compatible module; exact-pair
VM boot validation PASS, with the first harness-only failure retained in the
validation record. The separate `cpu-observe` launcher integrates
the reviewed DT with exact payload/prepared-tree guards and userspace governor.
Its collector explicitly loads with writes disabled/cap zero, identifies the
actual boot core and gathers short CPU/memory/thermal observations. No live
frequency request, SMP or storage is included. Native attempt 28 is NOT RUN.
M1 next: `tools/m1n1-client/attempt28-instructions.md`; exact pins/results in
`native/boot/attempt28/`. Offline readiness and human start precede a restart.
Keep the existing entry, Macintosh HD intact/default/Full, and routine policy
checks waived. Public Git receives no images, keys or Apple artifacts.

CPU performance/efficiency, independent built-in Wi-Fi and persistent storage
remain the user's workstation acceptance targets. CPU-clock changes cannot
alone prove desktop or energy parity; graphics, idle/thermal and SMP work
remain. The old storage-attempt-28 assignment is superseded. Preserve the other
agents' unreviewed jobs047/048 and kernel-config files.

### Historical M1 native result — attempt 27, 2026-10-20

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


### Historical preboot direction — 2026-10-20, superseded by the result above

M1 offline intake `eff1716` PASS with documented test limits; the user confirms
its restart is done. The user explicitly declines further routine boot-policy
checks. Do not ask again or block on them. Last reported original Full/lab
Permissive are retained as reported, not newly verified. Keep Macintosh HD as
default and change no policy/volume/firmware settings. The next human action is
to boot the existing iLinux Boot Lab entry to `Running proxy...`; the M1 then
follows the one-attempt checklist. Native attempt 27/live checks remain NOT RUN.
This paragraph supersedes older routine-check/restart prerequisites below.

Historical offline milestone (2026-10-20): **attempt 27 offline ready with documented
test limits**, both privately transferred images match the published pair;
boot042/intake/launcher/client/helper digests and offline SSH entries PASS.
215 methods PASS, 2 legacy-fixture skips; initial assertion/race and system
LibreSSL TLS failure documented, two test-only fixes, proxy suite PASS on bundled
OpenSSL. See `native/boot/attempt27-m1-offline-2026-10-20.md`. **Native/live NOT
RUN, attempts=0.** Next: fresh M1 restart/cable/unlocked procedure, fresh read-only
M5 Full/Permissive/original-default checks and human start. No settings/storage/
DVFS/SMP action. Both images remain private in ignored build/attempt27.

### Active continuation — 2026-10-19

Previous baseline is `75411ec`, attempt 26 on boot042: native Omarchy, USB/SSH
and keyboard, with the reported 63-minute run. Older "latest" paragraphs below
are historical. Attempt 27 is two-stage delivery plus image fixes; storage is
attempt 28 behind its separate reviewed launcher change. CPU-frequency and SMP
work are offline and must not be bundled into attempt 27.

The interrupted side-session work is complete; the user approved committing
and pushing the reviewed handoff and separate offline CPU/SMP work on 2026-10-20: job045 image
rebuild and VM desktop/link PASS (root `5eaa2fdb…6d345`); job051 frequency
module compile, 16 sanitizer cases, six regression mutations, 12 Python methods
and narrow DT/schema checks PASS; recovered SMP findings written. Exact results
and limits: `native/boot/subagent-review-2026-10-19.md`; ordering:
`native/boot/resume-plan-2026-10-19.md`. CPU speed state remains unmeasured;
rendering latency is measured. No boot/settings/hardware changes.
Job049 is now paired/retested: stage one `84c01f53…06ed3` with that root.
Both full rejection/switch and fresh normal-path VM runs PASS; the handoff and
both public pin records are prepared. Evidence and precise limits:
`native/boot/attempt27-two-stage-validation.md`; M1 steps:
`tools/m1n1-client/stage-b-instructions.md`. Both private images are staged in
ignored `build/attempt27-transfer/`. Published on 2026-10-20: offline CPU/SMP
`3483816`, attempt-27 handoff `37fd9b5`; GitHub main verified after push.
Next: independent M1 offline intake of the published handoff and both private
images; then its fresh restart, cable re-seat and unlocked/open-lid procedure,
fresh read-only M5 policy/default confirmation and the human's start.
Native attempt 27/live checks NOT RUN; keep the M5 in macOS until readiness.


See `progress.md`. As of 2026-10-14:

Latest M5 result: Boot034 / attempt 15 prepared after reviewing M1 attempt 14 (`a4269bb`) and the
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

Latest M5 HV result: **hv003 prepared (NOT RUN)**. It keeps the hv002 hypervisor
patch and changes how it is started, since hv002 never came back from the
m1n1→m1n1 chainload: padded-literal copy stub (Likely cause, not confirmed),
SEPFW-only relocation with a 16-byte in-place ADT patch applied last, a read-only
layout gate, and a breadcrumb strip on the M5 screen (host, stub, 16 early m1n1
steps). M1 runs a ladder of human-started rungs (`--layout-only`,
`--chainload-only`, `--control stock`, then the full run), one per boot. Release
`native-j716c-hv003`; instructions `tools/m1n1-client/hv-instructions.md`;
evidence `native/hv/README.md`. Independent of boot034 / attempt 15.

Latest M5 result: **boot035 prepared (NOT RUN)** after reviewing attempt 15.
Asahi exposes no `smc_*` power domain on any SoC; our generated t6050 DT carried
seven SMC-owned `smc_i2cm` domains, and both native resets followed their
release by ≈ 5.6 s (Likely mechanism). Boot035 removes them from the Stage-B DT
and changes nothing else; attempt 16 runs the release ladder over the other 145
domains and should stay up 180 s. The M4/M5 hurdles (SPTM, WFI state loss,
locked RVBAR, secondary watchdog) are mapped against our path in
`native/boot/attempt15-review-2026-10-15.md`; `roadmap.md` Phase 3 is now the
path to a native Omarchy boot.

Latest M1 native result: **attempt 26 (the M5's keyboard, on boot042): the keyboard switches on over SSH and types on the M5, and the
desktop's slowness is measured and explained.** `sudo ilinux-keyboard` steps 0 to 5 PASS in 1.4 s (RTKit wake of the MTP, DockChannel,
`hid-apple`, a 2 MiB ring transport, five interfaces, `/dev/input/event0` "Apple MTP keyboard"; step 6: 49 presses, Enter, `omarchy` as on
a US layout; no trackpad device); the MTP DART's reset at boot disturbed nothing; the link and SSH held **63 min 34 s** (22 SSH sessions,
no kernel fault line) until the human powered the M5 off or restarted it; the attempt-25 image fixes work. The human found the desktop
unusably slow (menus about 2 s, repeated letters). Measured: the keyboard path is clean (each tap seen once, 44 to 88 ms, no kernel
repeat on letters), but every screen update costs the one CPU about 0.47 s (Hyprland draws the 3456×2160 screen in software), the key
release waits behind it and the terminal's 250 ms auto-repeat fires about 14 times per tap (134 to 152 characters for 10 taps, seven
runs); **a 1000 ms repeat delay gives exactly 10 of 10 and halves the CPU per tap**; animations off changed nothing. Controller exit 0
in 476.856 s, no M1 panic. See `native/boot/stage-b-2026-10-19-attempt26-result.md`. The fixed E1 probe is still NOT RUN.

Historical M1 milestone: offline readiness PASS (live NOT RUN) for attempt 26 (the M5's keyboard, switched on over SSH, on boot042,
launcher `--profile omarchy`) on handoff `b8c877c`: the boot042 archive verified against Git before extraction (GitHub's digest equal)
and its receipt clean; it differs from boot041 in exactly `Image`, `kernel.config` and the Stage-B DT, and the M1's own diff of the two
DTs finds exactly ten new MTP nodes and two changed ones with the NVMe node still disabled and every USB node unchanged; the
privately delivered image `565644be…bf6f` (2,435,320,732 bytes) equals the pin and, read from the image itself, holds exactly four
kernel modules (the keyboard path) and no storage module, no private key or credential, and eighteen lab files byte-identical to Git;
`ilinux-keyboard` (root over SSH) was read in full. The offline launcher run (exactly the seven expected lines) and the 102 controller
cases PASS, `test_usb_pipe` 14 of 15 then 15 of 15 (one test is timing-sensitive; code unchanged). New and untested on hardware: m1n1's
handling of the MTP nodes, the MTP DART's reset at boot, then over SSH the RTKit wake, the DockChannel FIFO, the ring transport, the
keyboard and typing on the M5; no storage. Needs the cable re-seat, a recording (typing on the M5's screen is the headline result) and
the human's start; the serial-number line on the m1n1 screen is never shared.

Latest M1 native result: **attempt 25 (Omarchy itself with the USB link and Claude Code, on boot041): the first data from the M1 to the
M5 works, and SSH, the clock step, web access through the M1 and a signed-in Claude Code ran on the M5.** Over the USB byte pipe: SSH
as `omarchy` (a new host key per boot, equal to the journal's), the clock step (24.2 days behind, then 1.3 ms ahead), HTTPS through the
M1's relay (118 of 118 connections ok), passwordless sudo, and Claude Code signed in by the human and answering a prompt, at about 25
to 27 MB/s each way, for 15 min 39 s with no kernel fault line, two interfaces and two user clients on one device; the Omarchy desktop
was up 27 to 31 s after the handoff (journal). Seen: `claude` started from SSH opened Chromium on the M5 (a sign-in confusion),
`archlinux-keyring-wkd-sync` fails every 300 s (75% of the journal), idle sshd restarts on unused ports. The link ended at +958 s when the
human powered the M5 off or restarted it; no film of the run (a 6.6 s phone clip of both screens arrived afterwards). Controller exit 0 in 476.492 s, no M1 panic. See
`native/boot/stage-b-2026-10-19-attempt25-result.md`. The fixed E1 probe is still NOT RUN.

Historical M1 milestone: offline readiness PASS (live NOT RUN) for attempt 25 (Omarchy itself with the USB link and Claude Code on
boot041, launcher `--profile omarchy`) on handoff `38e91fb`: the boot041 archive re-verified against Git and the launcher unchanged
(`b14ec7a1…`); the privately delivered image `b8eae454…66c1` (2,434,354,327 bytes) equals the pin and, which the earlier Omarchy images
could not be, **was read from the image itself** with this Mac's own `tar`: no SSH host or user private key, no keyring, credentials,
history or Wi-Fi secret, root and `omarchy` passwords locked, the authorized key equal to the M1's, the lab's eleven files
byte-identical to Git, Omarchy's own passwordless grant and the clock rule the only sudo additions, sshd key-only on the USB pipe only.
The offline launcher run (exactly the seven expected lines), the 102 controller cases and the ramroot (45), usb-pipe (15),
connect-proxy (16) and m5-clock (13) suites PASS; `usb-pipe`, `connect-proxy.py`, `m5-clock.py` and the SSH config were read in full
and `usb-pipe` built from source (SHA-256 `94b33396…bffe`). New and untested on hardware: the first data from the M1 to the M5 (bulk
OUT), two interfaces per port, the web relay and the human's Claude sign-in. Needs a fresh M1 restart (unlocked, lid open for 20
minutes or more), cable re-seat, a 30-minute recording started before the launch and the human's start; the serial-number line on the
m1n1 screen is never shared, and nothing about the sign-in (link, code, account) is recorded.

Latest M1 native result: **attempt 24 (boot041, boot040 with both DART instances per dwc3 core): the USB log streamed for the full
ten minutes.** The M1's read-only reader captured 218,079 bytes (2,580 intact records, kernel 0.065 to 604.3 s, heartbeats 000 to 119
with no gap, the M5's byte counter matching the capture at every status line) with the DART fault-interrupt count 0 and `pend 0/0` on
all 357 port heartbeat lines, no `BUSERR`, no `translation fault`, no `nobody cared`. All six DART instances are v2.4, both instances of
each port were set up (`both set up`; Linux programming instance 0 for the first time did not freeze the SoC), and each shared fault
line shows two handlers; the 50-domain ladder completed at 45.056 s. The Image is byte-identical to boot040's, so the DT change removed
the stall (Confirmed as a comparison, one passing run; Likely candidate A). Host-to-device data, a console, a network and SSH are
untested (the reader never writes). Controller exit 0 in 11.197 s, no M1 panic. See
`native/boot/stage-b-2026-10-18-attempt24-result.md`. The fixed E1 probe is still NOT RUN.

Historical M1 milestone: offline readiness PASS (live NOT RUN) for attempt 24 / boot041 (boot040 with both DART instances per dwc3 core
in the Stage-B DT) on handoff `b5ef90d`: archive `ab49e307…4d28` verified against Git before extraction (GitHub's digest equal), the
Image byte-identical to boot040's, the M1's own property-level diff of the two Stage-B DTs finds exactly six nodes changed (the three
instance-0 DART nodes enabled, the three controllers' `iommus` extended), the Stage-B initramfs differs from boot040's only in `/init`
(reads only), launcher `b14ec7a1…` offline run and the reviewed 102 controller cases plus the suites PASS, the reader unchanged and
re-tested. New and untested on this chip: Linux resets and programs DART instance 0. Needs a fresh M1 restart (unlocked), cable
re-seat, a recording started before the launch and the human's start; the serial-number line on the m1n1 screen is never shared.

Latest M1 native result: **attempt 23 (boot040, attempt 21's bulk-only `gser` port with the DART fault made visible): the USB DART
is version 2.4, instance 1's fault line finds nothing pending, and at the first bus error the sibling instance the DT omits holds the
fault.** The same stop as attempt 21 (25,911 bytes captured; no endpoint-0 error; Linux healthy), now explained on the M5's screen:
a fault-interrupt storm on IRQ 43 from 3.93 s (instance 1's v2.2-layout handler finds `PENDING 0` every time, until the kernel
disables the line), and at the first bus error instance 0, which the Stage-B DT omits and Linux never programs, shows `pend 1` and a
stream block with address `0x3ffff35800` while instance 1 shows `pend 0`: Likely candidate A (Asahi's two-DART wiring); the M5
decides. Controller exit 0 in 10.965 s, no M1 panic. See `native/boot/stage-b-2026-10-18-attempt23-result.md`. The fixed E1 probe
is still NOT RUN.

Historical M1 milestone: offline readiness PASS (live NOT RUN) for attempt 23 / boot040 (attempt 21's bulk-only `gser` port with the
apple-dart fault made visible) on handoff `c5ae860`: archive `1d7f5c8d…66cf` verified against Git before extraction (GitHub's digest
equal), the Stage-B initramfs differs from boot039's only in `/init` (a static aarch64 ELF), the two apple-dart patches and the
`/dev/mem` register snapshot read in full (reads only from user space; the kernel patches write only the DART's fault
acknowledgement registers, part 2 only on a v2.2+ DART and untested on hardware), launcher `b14ec7a1…` offline run and the reviewed
102 controller cases plus the suites PASS, the reader (attempt 21's binary) unchanged and re-tested. Needs a fresh M1 restart
(unlocked), cable re-seat, a recording started before the launch (4K if possible) and the human's start; accept the macOS USB
accessory prompt.

Latest M1 native result: **attempt 22 (Omarchy itself, VM job 045, `--profile omarchy`): the first installer-built Omarchy
desktop on the M5, up about 39 s after the handoff and stable for the filmed 10 minutes.** The 2.38 GB upload took 456.5 s (5.22 MB/s)
with the 3 GiB client heap and no reset; the kernel unpacked the image and reached systemd within about 17 s; then Omarchy's own
session (SDDM → uwsm → Hyprland → Quickshell) showed the default wallpaper, the top bar (a wrong-time clock) and its two first-run
notifications, and stayed up with the panel lit to the end of the clip (+628 s, no blackout or restart in a one-second brightness
trace). View-only, one CPU, software rendering, no USB by design. Controller exit 0 in 460.186 s, no M1 panic. m1n1's memory lines
were not legible (the serial-number line shares their screen). Performance, power and input are not established. See
`native/boot/stage-b-2026-10-18-attempt22-result.md`. The fixed E1 probe is still NOT RUN.

Historical M1 milestone: offline readiness PASS (live NOT RUN) for attempt 22 (Omarchy itself, VM job 045, a view-only RAM boot on
boot035, launcher `--profile omarchy`) on handoff `7eb2aad`: the boot035 package re-verified against the Git pin, the 2.34 GB image
(`d00ba156…578a`) equal to the manifest by size and digest (zstd header read; content not inspected, no zstd tool), the new launcher
`b14ec7a1…` diff (39 lines) read in full, the offline launcher run (exactly the seven expected lines) and 146 cases PASS (102 plus
44). Needs a fresh M1 restart (unlocked, lid open, awake for the ≈ 7.5-minute upload plus 10 minutes), cable re-seat, a 20-minute
recording started before the launch, and the human's start; the serial-number line on the m1n1 screen is never transcribed or shared.

Latest M1 native result: **attempt 21 (boot039, a bulk-only `gser` USB log port): macOS publishes the interface and the
read-only reader streams 36,909 bytes, then the M5's dwc3 flags a DMA bus error.** With no interrupt endpoint, EP0 stayed
healthy for 10 minutes (zero EP0 timeouts; attempt 18's wedge needed something only ACM/ECM had), macOS bound no driver to the
vendor interface and the reader opened it without an entitlement. Then the stream stopped: on the M5's screen (video) port 1 shows
`BUSERR`, `irq146` and the `1in` ring frozen from heartbeat 001 on, and Linux printed `irq 43: nobody cared` (`handlers:
apple_dart_irq`) and disabled the IRQ at 9.956 s (the digit is the weakest reading). The dwc3 TX FIFOs are sane; Linux stayed
healthy (50-domain ladder at ≈ 45 s, heartbeats to 116, no reset). Likely: a DMA fault through the USB DART; the M5 investigates.
Controller exit 0 in 10.95 s, no M1 panic. See `native/boot/stage-b-2026-10-18-attempt21-result.md`. The fixed E1 probe is still
NOT RUN.

Historical M1 milestone: offline readiness PASS (live NOT RUN) for attempt 21 / boot039 (a bulk-only `gser` USB log port, the
dwc3 state on the M5 screen) on handoff `7905adb`: archive `b85c8d45…7d51` verified against Git before extraction, 102
controller cases plus the USB, boot039 and RAM-root suites, launcher `4d55f0c9…` unchanged, Image/config/DTBs/m1n1 identical to
boot036, the Stage-B initramfs differs only in `/init`. The M1 built the read-only bulk-log reader
(`tools/m1n1-client/bulk-log-reader.m`, interface only, IN pipe only, never a write) with only the SDK this Mac has; 15 tests
PASS (static, refusals, a fake-pipe read loop), 10 of 10 forbidden-call mutants caught; no real read yet. Needs a fresh M1
restart (kept unlocked), cable re-seat, a recording started before the launch, and the human's start.

Latest M1 native result: **attempt 20 (boot035 RAM root run 33): a stable ten-minute Omarchy desktop with a live status
screen.** Hyprland starts through `start-hyprland` with no warning, the status screen appears about 7 s after the
handoff (`desktop ready 8.50 s after kernel start`) and the counter, clock and display keep updating for the whole filmed
ten minutes (counter `0:09:59` at the end); no kernel message after the 74-domain release ladder (complete at 55.268 s). The
on-screen single-thread benchmarks finished in 348 s: compute and STREAM rows are about a fifth of this machine's macOS
baseline and DRAM-sized pointer chases read about 600 ns (context only, no parity claim; Hypothesis: the boot CPU is an
efficiency-class core near 2.65 GHz). Controller exit 0, upload 42.38 s, no M1 panic, no USB device by design. See
`native/boot/stage-b-2026-10-16-attempt20-result.md`. The fixed E1 probe is still NOT RUN.

Historical M1 milestone: offline readiness PASS (live NOT RUN) for attempt 20 (boot035 RAM root run 33 with the live
status screen, `--profile ramroot`) on handoff `3f7b24d`: boot035 re-verified against the Git pin, the run-33 image
(182,420,823 bytes, `67f25732…d3f7`) matches the manifest by size and digest but its content was not inspected (no zstd
tool; the overlay source in Git was reviewed instead), offline launcher run and 132 cases PASS, controller digests
unchanged. Needs the human's fresh M1 restart, cable re-seat, a recording started before the launch, and the start.

Latest M1 native result: **attempt 19 (Omarchy RAM root on boot035): the first native Omarchy desktop on the M5.**
Hyprland on `simpledrm` with software rendering came up (wallpaper at video 6.9 s; the RAM root reports `desktop
ready 7.79 s after kernel start`), with a live waybar and a terminal; 1 CPU, view-only, no USB by design. The human
reports it still up after more than 8 minutes with the clock advanced. A cosmetic Hyprland warning (started without
`start-hyprland`) and early PMGR/`kvm_arch_timer` error lines were seen; upload 42.28 s, controller exit 0, no M1
panic. Performance, power, input, USB and stability beyond the human's checks are not established. See
`native/boot/stage-b-2026-10-16-attempt19-result.md`. The fixed E1 probe is still NOT RUN.

Historical M1 milestone: offline readiness PASS (live NOT RUN) for attempt 19 (Omarchy RAM root on boot035,
`--profile ramroot`) on handoff `59b12a0`: boot035 package re-verified against the Git pin, the RAM-root image
(182,092,876 bytes, `58bdc6ce…a27e`) matches the manifest by size and digest but its content was not inspected
(no zstd tool), offline launcher run and 132 cases PASS (102 reviewed + 30 RAM-root), controller digests
unchanged. No USB device is expected after the handoff, so the video is the evidence. Needs the human's fresh
M1 restart, cable re-seat, whole-screen filming and start.

Latest M1 native result: **attempt 18 (boot038, CDC-ACM log port + CDC-ECM)**: Linux held the attempt-17
baseline (50-domain ladder at 45.024 s, 60 s milestone, heartbeats to 113.7 s, no reset, no M1 panic) and
the M1 enumerated the gadget (+3.95 s) and macOS selected configuration 1 (+8.45 s), but no interface node
was published, no ACM/ECM driver bound and the device's control endpoint then timed out; no serial port, no
network, no SSH. On the M5 the UDC reads `configured` while `usb0` stays down. Likely, not tested: the
interrupt-IN notification endpoints. M5 to try a gadget with no interrupt endpoint. See
`native/boot/stage-b-2026-10-16-attempt18-result.md`. The fixed E1 probe is still NOT RUN.

Historical M1 milestone: offline readiness PASS (live NOT RUN) for attempt 18 / boot038 (CDC-ACM kernel-log
port + CDC-ECM, key-only SSH) on `5105c58` (handoff `bd814ad`): archive `09f5a5d7…5f70` verified against
Git before extraction, 102 controller cases plus the boot036 suites, launcher `4d55f0c9…`, Image/config/
DTBs/m1n1 byte-identical to boot036, Stage-B initramfs differs only in `/init`, packaged key equals the M1
key. The fixed E1 probe is re-verified offline too (27 + 86 tests, same 66-read plan, the former NameError
site now passes). The M1 reads the ACM port with a tool that never writes. Needs a fresh M1 restart, filming
and the human's start; attempt 18 first, E1 as its own lab boot.

Latest M1 native result: **attempt 17 (boot036): first Linux USB on the M5**. Three device-mode dwc3
controllers probed, EEM gadgets bound, dropbear key-only started, and the M1 enumerated the device 8 s
after handoff; but macOS 26.0.1 has **no EEM driver** (kext absent from the kernel collection), so no
interface or SSH. Baseline held (heartbeats to 98.7 s, 50-domain ladder complete, no reset). M5 to pick
ECM, NCM or ACM serial. See `native/boot/stage-b-2026-10-16-attempt17-result.md`.

Latest M1 result: **MTP E1 probe stopped before any device contact** (`NameError: M1N1Proxy`,
class-body scoping bug at `mtp_probe.py:426`; the PMGR probe has the same bug at
`pmgr_probe.py:808-809`). No request was sent; the M5 patched both in `bd814ad` and the M1
re-verified them offline (see above); rerun needs the human's go.

Historical M1 milestone: offline readiness PASS (live NOT RUN) for the MTP E1 read-only probe and
for attempt 17 / boot036 (USB control channel, key-only SSH) on `0363bd5`: 26 probe tests,
102 controller cases, launcher `4d55f0c9…`, DT/initramfs reviewed independently, packaged
authorized key equals the M1 key. Order: E1 lab boot first, then attempt 17.

Latest M1 native result: **attempt 16 (boot035) is the first stable native baseline**:
PID 1 alive with heartbeats to >= 108 s, the 60 s milestone passed, the 74-domain release
ladder completed at 57.3 s, no reset, no host panic. SMC-versus-host attribution of the
earlier resets not separated. Fresh policy checks NOT CHECKED. See
`native/boot/stage-b-2026-10-15-attempt16-result.md`.

Historical M1 milestone: boot035 / attempt 16 offline readiness PASS on handoff `4debc28`
(102 tests, controller hashes, DT delta exactly the seven `smc_i2cm` nodes, clean pin).
One filmed RAM attempt (M1 freshly restarted, 180 s bound) and Macintosh HD return next;
native/live NOT RUN at readiness.

Latest M5 handoff: **attempt 26, the M5's keyboard switched on over SSH, on boot042
(NOT RUN)**. boot042 is boot041 with the MTP keyboard path and the storage drivers built
as modules, and the MTP nodes and its DART in the Stage-B DT; m1n1, the generic DT and both
initramfs are boot041's. The one change at boot is the DART driver's reset of the MTP's
DART; then `sudo ilinux-keyboard` loads four modules from the SSH session one at a time,
each with its own go/no-go, and the human types on the M5. The Omarchy root is attempt 25's
with its four fixes and the keyboard modules (2,435,320,732 bytes, `565644be…bf6f`, pinned
in `native/boot/omarchy-root-manifest.json`); it reaches the M1 privately. No storage in
this attempt: the launcher refuses an enabled NVMe node, and read-only storage is attempt
27, behind a separate launcher change the user reviews (`decisions.md`, 2026-10-19).
Prerelease `native-j716c-boot042` (`a2e57c0c…a781`); launcher unchanged (`b14ec7a1…`);
offline launcher check and all suites PASS. See `tools/m1n1-client/stage-b-instructions.md`.

Latest M1 native result: **attempt 15 (boot034) outlived attempt 14's 8.8 s reset**:
sync_state kept domains on, PID 1 and heartbeats ran, a 17-step release ladder
executed, then a silent SoC reset at kernel ~27.7 s. **Confounded** by an M1 host
kernel panic at the handoff (Apple USB CDC driver); controller record incomplete;
fresh policy checks NOT CHECKED. See
`native/boot/stage-b-2026-10-15-attempt15-result.md`. Rerun recommended.

Historical M1 milestone: boot034 / attempt 15 offline readiness PASS on handoff
`9499bd0` (102 tests, controller hashes, Image-only delta, 152 domains
reproduced, clean pin). One filmed RAM attempt and Macintosh HD return next;
native/live NOT RUN at readiness. hv003 and the PMGR probe: M1 readiness
pending.

Latest M1 HV result: hv002 census v2 **PASS**, but Session 2 **stopped at the
chainload**: hv002 never came back on USB (M5 frozen at the restored Apple logo).
Hypervisor/guest NOT STARTED; cause unknown. See
`native/hv/hv002-session2-2026-10-14-result.md`.

Latest M1 native result: **attempt 14 reached native diagnostic PID 1** (3.152 s, one
CPU, heartbeats at 3.23/8.23 s). The boot032 GPIO repair works: main cache
221/216/5. The SoC then **silently reset at kernel ~8.77 s** and rebooted to
Macintosh HD. 60-second liveness NOT reached; cause unknown; fresh policy checks
NOT CHECKED. See `native/boot/stage-b-2026-10-14-attempt14-result.md`. M1 boot034
proposals and hypervisor study: `coordination.md`,
`research/m1n1/hv-linux-guest-feasibility-2026-10-14.md`.

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

Historical M1 attempt-13 record: `native/boot/stage-b-2026-10-14-attempt13-result.md`.

Historical M5 preparation: **boot032 / attempt 13 prepared** after M1 attempt 12 (`f3218fd`).
Main GPIO stopped at B73/C0059 cache initialization; NUB handoff 61/7/1 returned 0.
Fresh post-attempt-12 policies Full/Permissive and M5 original-root/FileVault/SIP/
staged-m1n1 checks PASS. Native userspace remains unobserved.

REA/independent bytes + current GPIO metadata identify five excluded pins.
Boot032 respects standard reserved ranges, initializes only permitted cache
entries, guards GPIO/IRQ access and adds I pin-index/B90–93 diagnostics.
Full Image, sanitizer/schema checks, 102 controller cases/13-file intake,
recipe reproduction and exact-image generic 60s liveness PASS. **Native boot032
and live checks NOT RUN.** See `kernel/experiments/gpio-reserved/README.md`.
M1 verifies private boot032 and publishes readiness, then one filmed human-started
attempt 13 and Macintosh HD return. Preserve boot021/current entry, all gates,
fixed args and single skip. No new provisioning, security/volume changes or retry.
Native userspace precedes Linux control/input/configuration agent and Omarchy.

Historical M5 preparation: **boot031 / attempt 12 prepared**, following M1 attempt 11 (`f35efa5`).
Final D=C=0059/B63 identifies main pinctrl callback; exact cause unresolved.
Boot031 adds t6050 GPIO geometry/cache bounds and pre-parent IRQ handover with
readback/locked-pin errors, plus 17 probe checkpoints. REA/independent bytes,
full Image, sanitizer regressions, 90 controller cases/intake and exact-image
VZ PID-1/60s liveness PASS. **Native boot031/live checks NOT RUN.**
User post-attempt-11 policies Full/Permissive and independent original-root/
FileVault/SIP/staged-m1n1 checks PASS; report's pending return is resolved.
M1 follows current Stage-B instructions: verify release, publish readiness,
then one filmed attempt 12 and return. Preserve installed boot021/current entry,
all gates and single skip. No new provisioning/settings/volume changes or retry.
See `kernel/experiments/gpio-handoff/README.md`. Native diagnostic userspace
precedes Linux-side control/input and Omarchy configuration. No parity claim.

Historical M5 review: attempt 7 reached `deferred_probe_initcall`; diagnostic userspace is
still unobserved. Boot027 keeps the working boot021 setup and changes only
Image, adding bounded timer/tick/deferred-work diagnostics. Hardware detection
now validates the t6050 AIC/timer routes and observed CPU topology. Full link,
11 sanitizer scenarios, 90 controller cases, 13-file intake and generic VM
phases/PID-1/60-second liveness PASS; **native attempt 8 NOT RUN at that handoff**. M1 verifies
private boot027, publishes readiness, then the human starts one filmed boot.
No repeated provisioning/Stage A, Recovery, new blacklist or automatic retry.
Post-attempt-7 original Full/lab Permissive JSON PASS. Root cause unknown.
Follow current coordination and `tools/m1n1-client/stage-b-instructions.md`.
Older bullets below retain historical context.

* Hardware fully inventoried. Native Linux now reaches late initialization,
  but diagnostic userspace/liveness remains unobserved. Full native boot/SMP,
  G17 graphics/display and idle/DVFS remain unresolved.
* A draft native patch series exists in `kernel/patches/t6050`. Job 020 /
  F-056 built the full kernel Image, modules, DTBs and initramfs. DockChannel
  hardening was separately object-tested after the Image link; that extra
  patch is not in the exported Image. The draft DT is schema-clean (0
  dtbs_check warnings) and probe-ready (every bring-up device matches a
  driver on its t6050 string or generic fallback; `probe-audit.sh`). It
  remains **unbooted**: actual probing and firmware startup are runtime
  questions for the first native session.
* Job 021 packages the original kernel plus a separately built m1n1 and
  Stage-B DT/initramfs. The launcher defaults to offline verification, never
  requests secondary-core start, and checks the final target DT before a
  separately authorized handoff. Generic diskless VM PID-1/60-second heartbeat
  succeeds; native hardware remains untested. `native/boot/README.md` is the
  current M1 handoff. Follow the updated lab-only authorization below;
  Stage A P_NOP and original-desktop return have succeeded; Linux remains on hold.
  M1's `dfdf8cf` offline report is reviewed (13 files verified, 26 tests pass).
  The matching macOS scaffold installer passes package trust/content checks;
  its outer-app resource-rule rejection remains unchanged. No security checks
  were disabled. Lab macOS installation/first boot and original-desktop return
  are user-confirmed (M1 report `f34970e`). B independently verified both builds,
  separate System/Data groups and original FileVault/SIP/authenticated-root.
  The user's post-return read-only helper output reports Full Security for
  original and lab, both exit 0. B reviewed that output, not an independent rerun.
  User-authorized m1n1 staging is complete: the lab Data copy matches the
  package's 3,932,160 bytes/SHA-256. Lab-only Recovery installation is now
  complete by human command results: preflight exit 0, paired 1TR, lab
  Permissive/kernel CTRR disabled, kmutil exit 0 and final original Full/lab
  Permissive. User confirms return to Macintosh HD and restoration as default.
  After an initial discovery-only stop and offline naming fix `70ad452`, the
  next user-started Stage A attempt identified one primary CDC interface via
  USB metadata and received one P_NOP reply: exit 0, 0.158 seconds, port closed,
  no retries or memory/register/boot requests. User confirms Macintosh HD
  desktop return. Linux and live target-version checks remain **NOT RUN**.
  Boot021/client pin are unchanged. No new live session is authorized by the
  reporting task. M5 should review the result and perform read-only return
  checks; fresh build/default/protection checks are not yet reported for this
  attempt. See `coordination.md` and `tools/m1n1-client/stage-a-instructions.md`.
* **Omarchy 4 runs today in a GPU-accelerated VM** (`virtualization/qemu/`):
  * Hyprland is accelerated through VirGL to Metal GL at Retina resolution;
  * GPU ALU is at 99.7% of macOS GL, and CPU at 99% single-thread;
  * heterogeneous vCPUs map guest background work to host M cores;
  * App Nap `auto`, with an idle cost of +0.09 W;
  * the Mac battery and time zone are bridged into the guest.
* GPU compute for LLMs from Linux runs through ggml RPC over vsock: 81–89% of
  native Metal.
* Guest Vulkan runs through Venus on MoltenVK at 94–98% of native compute
  (D-027).
* Guest video decode (H.264) runs on the Mac's media engine through
  VA-API on VideoToolbox (D-029). It is bit-exact against FFmpeg.
  * 4K60 playback with the VM's mpv defaults (`profile=fast`): 3.9 W, against
    7.3 W with mpv's default scaling and 2.9 W native (F-048).
  * Later on-screen sessions measured 3.6–4.1 W; see F-050/F-051 for pacing
    limitations and the display change.
  * A separate `mesa-virgl-video-ilinux` package now fixes tested lossless
    4:2:0 downloads and opts into NV12 decode with `ilinux-video`. Paced 4K60
    decode uses 41.3% less QEMU CPU time (F-052/F-053); no energy gain claimed.
* The current user authorized local analysis of appropriate accessible
  binaries. REA/Ghidra now works in a separate diskless Linux lab (F-070),
  with extraction and function-boundary checks (F-071). Native startup-mask
  experiments remain read-only/unvalidated on hardware (F-072). See
  `reverse-engineering/findings/rea-native-2026-10-13/handoff.md`.
* The macOS baseline suite and session-1 research are complete.
* B's expanded driver pass (F-073–F-075) adds a Linux-tested DockChannel
  bounds/rearm patch and original offline N1 ACIPC helpers. REA covered
  17 functions; two ISP layouts match existing Linux. Native compatibility
  remains untested. See `reverse-engineering/findings/driver-interfaces-2026-10-13/handoff.md`.
* B's startup/idle pass (F-076–F-077) resolves 12 PMGR references and checks
  six REA functions against original bytes and LLVM. An optional m1n1
  locked-vector mismatch guard passed eight Linux cases with sanitizers
  and full startup-object compilation; it is not an SMP fix. See
  `reverse-engineering/findings/cpu-startup-2026-10-13/handoff.md`.

## Next recommended actions

Keep `roadmap.md` authoritative. The immediate queue is in `progress.md`
under "Next".
