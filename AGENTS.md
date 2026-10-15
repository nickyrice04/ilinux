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
* Git: the user authorized the private `nickyrice04/ilinux` GitHub remote
  on 2026-10-13 for second-machine setup and agent handoffs. This supersedes
  the former local-only rule. Never commit VM images, models,
  build outputs, raw IORegistry dumps or proprietary binaries (see
  `.gitignore`).

## Current status (update on every milestone)

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

Latest M1 milestone: boot035 / attempt 16 offline readiness PASS on handoff `4debc28`
(102 tests, controller hashes, DT delta exactly the seven `smc_i2cm` nodes, clean pin).
One filmed RAM attempt (M1 freshly restarted, 180 s bound) and Macintosh HD return next;
native/live NOT RUN at readiness.

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
