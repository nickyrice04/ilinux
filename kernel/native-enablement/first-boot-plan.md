# t6050 first native boot: corrected staged plan

Updated 2026-10-13 by B at the user's request. Supersedes the earlier draft's
single-core, APFS-stub, persistent-console and power-cycle guarantees.
**Authorization: prepare/test/package/push only. Stop before boot settings,
storage changes, boot-entry installation or physical reboot.**

## 1. Current state

This Mac is Mac17,6 / J716c / t6050 M5 Max. No native Linux boot has been
observed. Job 020 built the kernel, DT and diagnostic initramfs. Job 021
exports the same bytes and adds a built, pinned m1n1 plus a conservative
Stage-B DT/initramfs. See [package instructions](../../native/boot/README.md).

The user reports a completed backup and a USB-connected M1 controller.
Controller tools pass offline tests; the physical proxy is untested. Read-only
inspection found only macOS volumes on the M5: no dedicated m1n1 OS entry.
M5 Pro boot/SMP reports are hypotheses for this M5 Max, not local results.

## 2. Dedicated OS entry: separate installation gate

The current concrete proposal, observed disk capacity, matching Apple installer,
recovery preflight and gated commands are in
[boot-entry-setup.md](boot-entry-setup.md). Preparation is complete; execution
and native validation remain pending. The alternatives below are background.

An empty APFS volume alone is not a bootable m1n1 stub. It needs an OS volume
group, Apple boot components, paired recovery and an owner-authorized custom
boot policy. Asahi's conventional layout uses a separate APFS container
partition plus an ESP and Linux storage. Sharing a container is possible;
the earlier blanket claim that a small empty volume suffices was incorrect.

The standard Asahi installer does not support this M5 Max. Do not bypass its
model checks. No installer or boot-policy command is included in job 021.
For the next separately approved task, review one concrete route:

* **Dedicated second macOS installation as a development scaffold.** Apple's
  additional-APFS-volume procedure creates a real OS volume group and paired
  recovery. It consumes more space than a stripped stub. Choose a compatible
  release and assess firmware/update implications first. Replacing only that
  new OS's boot object with m1n1 is a proposal, not a validated M5 installation.
* **Minimal stub provisioning.** Requires an independently reviewed M5-capable
  flow with correct Apple restore assets and recovery pairing. No such flow
  has been validated here. Do not improvise Preboot copying or patch out an
  installer's unsupported-model check.

Before changing anything, present the actual volume/container layout, capacity,
OS version, m1n1 checksum, recovery-pairing checks, per-entry policy change and
return-to-macOS procedure for approval. The original macOS entry retains its
policy; never use its System volume as the custom boot-object destination.
Do not disable authenticated-root or SIP on the original macOS installation.
The companion procedure targets a second full macOS 26.6.2 / 25G83 installation
named `iLinux Boot Lab`. Its commands are explicitly gated and must be checked
against the actual new volume group and paired Recovery before execution.

Sources: [Apple multiple-macOS volumes](https://support.apple.com/en-us/118282),
[Asahi OS layout](https://asahilinux.org/docs/platform/open-os-interop/),
[m1n1 installation/pairing](https://asahilinux.org/docs/sw/m1n1-user-guide/),
[M5 support](https://asahilinux.org/docs/platform/feature-support/m5/).

## 3. Observation

| Channel | Scope | Limit |
|---|---|---|
| m1n1 primary USB proxy | Pre-Linux handshake, upload, preparation | Native handoff shuts down m1n1 USB |
| M5 framebuffer, simpledrm/fbcon | Proposed kernel/userspace output | Actual native output unvalidated |
| m1n1 phram region | m1n1's own log | Not a Linux crash recorder or guaranteed post-hang retrieval path |
| Hypervisor virtual UART | Separate hypervisor execution mode | Not this native launcher; M5 support unvalidated |

No keyboard, SSH, Ethernet or serial bridge is assumed. The RAM initramfs is
non-interactive and contains no agent. The M1 agent coordinates while the human
observes the M5 screen. Record checkpoints and transcribed non-sensitive errors;
do not save raw ADT, serial numbers, MAC addresses or personal data.

A blank screen means **no observable Linux output**, not a proven AIC/SMP/display
failure. Further blind attempts should wait for an established observation path.

## 4. Stage A: m1n1 only, after separate approval

Prerequisites: dedicated entry provisioned with the packaged m1n1; matching
client; backup verified; both computers powered; direct cable; agreed macOS
return procedure. None is installed by the preparation package.

Boot only the dedicated entry. Discover the actual primary USB path on the M1,
then perform the bounded P_NOP-only check. Success proves a responding proxy,
not Linux support. Stop on timeout/mismatch. Do not open the upstream shell:
its setup resets the PMU panic counter and writes home-directory history.

## 5. Stage B: one-core RAM diagnostic, after separate approval

Use only `native/boot/launch.py` as documented in its README. Upstream
`tools/linux.py` unconditionally starts secondary cores before Linux sees
`maxcpus=1`. The replacement never issues that request, rejects already-started
secondaries reported by m1n1, and skips `cpufreq_init()` and `m1n1.setup`.

Fixed arguments select `console=tty0 fbcon=nodefer`, limit Linux to one CPU,
disable cpufreq and retain M4+ idle/unused-clock/domain workarounds. There is
no `earlycon=...` placeholder or arbitrary argument override. Those idle
workarounds do not establish efficient native idle.

The Stage-B DT keeps NVMe disabled despite its built-in driver. The initramfs
mounts no storage. m1n1 still initializes hardware; RAM-only describes payload
and rootfs placement, not an absence of register writes or firmware activity.
The launcher validates the effective DT after m1n1 fixups, in memory only.
It is never saved because m1n1 adds identifiers to it.

Pass criteria on the M5 display:

1. Kernel output followed by `PID 1 reached`.
2. J716c/t6050 diagnostics and `online_cpus=1`.
3. At least 60 seconds of five-second heartbeats.
4. Successful return to original macOS afterward.

Record package checksum, launcher commit, actual checkpoint, visible error,
elapsed time and macOS return outcome. A successful handoff request is not
proof of a Linux boot. On failure, do not retry automatically, poke CPU
registers or weaken validation. A fresh m1n1 session is needed before any
reviewed retry; RAM allocations and hardware setup are not rolled back.

## 6. Later stages

* **SMP:** separate secondary-start experiment after single-core evidence.
  Stage B has no SMP switch. B's startup guard remains an optional experiment.
* **NVMe:** separately reviewed DT/initramfs must enable it. Controller identify
  is read-only data access, but initialization writes registers/admin commands.
  Never mount or write macOS storage. Stage B cannot identify disabled storage.
* **Input/network/display/power:** validate transports before USB accessories,
  SSH or the configuration agent. GPU, DCP, N1, suspend and idle remain work.
* **Installed Omarchy:** separately approved Linux root-storage plan and
  reliable access first; then `native/handoff/`, excluding VM-only bridges.

Force-off/startup-picker return to macOS is the intended recovery path, not a
guarantee against every failure. Power cycling discards RAM; it does not undo
an OS entry, boot policy, partition changes or firmware updates.
