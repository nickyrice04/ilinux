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

See `progress.md`. As of 2026-10-13:

Latest: Stage B attempt 2 never handed off to Linux. Boot021 lacked m1n1's
required framebuffer placeholder. Job 022 reproduces this with the actual
pinned C function and corrects only the Stage-B DT; boot022 is verified offline.
Kernel/initramfs/installed m1n1 unchanged; the boot021 marker remains correct.
M1 must intake boot022 before one reviewed attempt 3; post-return policy JSON
is pending. Native correction NOT TESTED, Linux NOT RUN. Original root/build,
FileVault/SIP/authenticated-root and staged m1n1 were independently rechecked.
No volume/security/default/boot-object changes. Current instructions:
`tools/m1n1-client/stage-b-instructions.md`; evidence:
`virtualization/jobs/022-framebuffer-handoff/RESULTS.md`.

* Hardware fully inventoried. Native Linux is not boot-tested on this unit;
  t6050 boot/SMP, G17 graphics/display and idle/DVFS remain unresolved.
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
