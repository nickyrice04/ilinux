# Coordination: agents working in this workspace

Created 2026-10-13. Read this together with `AGENTS.md`, `progress.md`,
`blockers.md` and `decisions.md` before starting work. If this file and an
older plan disagree, this file wins for ownership and order of work.

## Roles

### Current authorization: create the lab macOS entry, preserve boot security

The user now authorizes the dedicated **iLinux Boot Lab** entry using the
matching macOS installer, preserving the original macOS. B owns this stage.
This supersedes the earlier volume/installer-launch hold below, but **does not
authorize changing boot security, installing a custom boot object or running
native m1n1/Linux**. Stop at the installer/restart handoff to the human; record
the actual destination and result before describing the entry as bootable.
M1 keeps the offline boot021 package ready and performs no live USB actions.

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
Post-return **boot-policy mode** checks still need an administrator-only read;
computer-use safety review blocked Terminal automation. No mode is inferred
from the pre-install baseline. The m1n1 binary hash still matches and it is
not staged in the lab yet. No security/custom-boot change occurred.
Boot021 and the existing client pin are unchanged.
Live USB/P_NOP, live target-version check, native m1n1/Linux/Omarchy remain
**NOT RUN**. Current handoff: `kernel/native-enablement/boot-entry-setup.md`.

**Next staged session:** finish read-only policy checks, stage/hash the exact
boot object, then request authorization for lab-only Permissive Security and
custom boot installation. Stage A tests only m1n1/P_NOP; Stage B separately
tests one-core Linux PID 1 and 60-second liveness. The result template now
separates controller output, screen observations, timing and macOS return.
No persistent USB Linux console or SSH is present. Blank screen means output
not observed; establish logging before another blind attempt.

### Current boot-package assignment (user authorized 2026-10-13)

B now owns preparing/exporting the boot package, correcting the single-core
launcher and first-boot instructions, testing them in isolation and pushing
the M1 handoff. Work is in `native/boot/` and job 021; A's QEMU/latency work
is untouched. The M1 agent downloads/verifies and reports offline readiness.
**Explicit stop: no boot settings, entry installation, partition changes or
physical boot.** Payload publication is authorized; these are open-source
build outputs, not Apple artifacts. Follow the corrected first-boot plan;
older statements about an empty APFS stub or persistent proxy console are
superseded. No native hardware success is claimed by this handoff.

B's next preparation milestone is complete: the user requested exact dedicated
entry steps while M1 verifies. `kernel/native-enablement/boot-entry-setup.md`
selects a second full macOS installation named `iLinux Boot Lab`, matching the
available 26.6.2 / 25G83 installer. It documents paired-Recovery checks,
lab-only policy/boot-object commands and macOS return. No volume creation,
policy change or reboot has run; an offline receipt does not authorize those
host changes.

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
earlier installer-launch hold; boot-security and native-test holds remain.

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
