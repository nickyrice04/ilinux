# Blockers

Status legend: 🔴 hard blocker (no path today) · 🟠 blocked pending research or
upstream work · 🟡 pending user approval or action · 🟢 resolved.

## Latest Stage A status — 2026-10-13

USB primary identification and P_NOP are now validated on this setup after
checker fix `70ad452`: one primary CDC data interface 1, one successful reply,
exit 0, 0.158 seconds, port closed. User confirms Macintosh HD desktop return.
The earlier naming/discovery blocker is resolved. No fresh post-attempt build,
default-selection or protection checks are reported yet; M5 can perform the
planned read-only checks. Boot021/client pin are unchanged. Linux and live
target-version checks remain NOT RUN; Stage B needs separate authorization.
This supersedes older provisioning/USB-pending statements below; P_NOP does
not resolve native Linux hardware-enablement blockers.

## Hardware enablement

### B-001 🔴 No Linux support for t6050 (M5 Max)

* No DT exists for t604x/t605x/t8142 in mainline or any Asahi branch.
  Mainline stops at M3. Asahi has a minimal t8132 (base M4) DT from 2026-07.
* m1n1 has **initial** T6050/T6051 support (PR #610, 2026-06-29), but
  the original test reported secondary CPUs not starting. That is historical
  evidence, not a fresh test on this unit; current behavior remains unverified.
  The checked m1n1 snapshot is `57a9339` (2026-10-11). Ranked hypotheses and read-only tests are in
  `kernel/native-enablement/plan.md` §1.2.
* A local draft DT now exists (`kernel/experiments/t6050-dt/`). It has
  MPIDR-correct CPUs and 188 PMGR domains, and has never been booted.
* Asahi's M5 support page (2026-10-03) shows no active work on any block.
  The installer accepts M1–M3 only.
* 2026-10-13: F-076 resolves selected PMGR virtual targets and connects the
  `clusters` property to the startup descriptor table. Live register/branch
  selection remains unverified. F-077 supplies an optional locked-RVBAR
  startup guard; Linux regressions/sanitizers and the full `smp.o` build pass.
  It is not an SMP fix or a native compatibility result.
* Consequence: there is no validated native Linux boot on this unit yet.
* Job 021 now supplies a checksummed controller package and tested single-core
  launcher. Generic VM boot reaches diagnostic userspace; this does not resolve
  the native blocker. The lab macOS entry is installed and has booted by user
  observation; original macOS return also succeeded (M1 report `f34970e`). B
  verified matching builds and separate System/Data groups. It is not an m1n1
  entry yet: the exact payload is now staged and hash-verified on lab Data,
  but paired-Recovery checks and execution of the now-authorized lab
  policy/custom-object installation remain. Native framebuffer is unverified.
* A concrete preparation procedure now exists in
  `kernel/native-enablement/boot-entry-setup.md`: second full macOS scaffold,
  available matching 26.6.2 / 25G83 installer, paired-Recovery preflight and
  lab-only custom boot policy. The user authorized the lab macOS installation;
  installation and first lab boot are complete. Lab-only custom boot/security
  changes are now authorized, pending human execution in paired Recovery.
  Native m1n1/Linux tests remain on hold.

### B-002 🔴 GPU (AGX G17X) unsupported

* The Asahi DRM driver and Mesa support G13/G14 (M1/M2) only. M3 (G15) is
  still being reverse-engineered after an ISA and firmware-interface break.
* The M5 GPU adds matrix "Neural Accelerators". macOS FP16 GEMM reaches
  ≈ 64 TFLOP/s, against ≈ 17.6 TFLOP/s for scalar FP16 FMA.

### B-003 🔴 Neural Engine

* The ADT marks it `ane,t8132exclave`, and macOS drives it via
  `ANEExclaveProxy` and exclave services.
* The only Linux ANE driver (eiln/ane) is M1-only, out of tree, and
  untouched since 2024-03.
* Feasibility under a non-secure kernel is unknown.

### B-004 🟠 NVMe controller generation

* macOS binds `AppleANS3CGv2Controller`, and SART is CoastGuard (m1n1 calls
  it **SARTv4**).
* m1n1 can read NVMe on T6050. Linux `nvme-apple` and `apple-sart` support
  only older revisions. The macOS-15+ ANS firmware ABI change needs the
  `b4/nvme-fwabi` series, which is already in the AsahiLinux `asahi` branch.
* 2026-10-11: the remaining Linux gaps are drafted locally (untested) in
  `kernel/patches/t6050/0001–0005`: SARTv4, the M4+ NVMMU/NVMe register
  split, and the I/O-queue base registers. Job 018 already applied all seven patches, compiled the driver objects and
  built the DTBs successfully. Remaining gates are schema/full-kernel checks
  and native hardware validation, not the already-passed object build.

### B-012 🔴 Wi-Fi / Bluetooth

* Apple's own **N1** wireless chip has no Linux driver (Asahi report).
* 2026-10-13: B located selected ACIPC operational configuration and real
  AirshipDK ring routines behind DriverKit stubs (F-075). Offline software
  helpers are Linux-tested; they do not register a network/HCI device.
  PCIe/DART, descriptors, index encoding, firmware lifecycle and physical
  packet/completion behavior remain blockers. ACIPC is distinct from RTKit.

### B-014 🔴 Touch ID (out of scope by design)

* The Touch ID sensor is paired to the Secure Enclave: fingerprint data
  goes over an encrypted channel to the SEP, which does the matching. No OS,
  macOS included, sees raw fingerprint data.
* Linux has no SEP interface, and Asahi doesn't support Touch ID.
* This project excludes SEP, keystore and biometric internals by policy
  (`reverse-engineering/macos-hardware-services.md`, method and scope).
* **Alternatives for Linux login and sudo:**
  * a USB fingerprint reader supported by `libfprint`/`fprintd`;
  * a FIDO2 security key through `pam_u2f`.
  * Both work in the VM through USB passthrough, and natively once USB works.

## Testing infrastructure

### Second-machine offline handoff complete; live testing pending (2026-10-13)

Client/LLVM and offline checks are ready. Job 021 now provides the package,
sender checksums and corrected launcher/instructions. M1's `dfdf8cf` report is
reviewed: archive/13 files verified, 26 tests and LLVM checks pass, clean client
at the agreed revision. All live USB/native tests remain **NOT RUN**.
User reports backup completed. Boot-entry provisioning now has a
current execution handoff in `kernel/native-enablement/boot-entry-setup.md`;
lab macOS boot/return succeeded, and B verified original build/FileVault/SIP/
authenticated-root plus the lab's separate installed volume group/build.
The user supplied the administrator-only read-only helper's result: original
and lab both Full Security, both exit 0. B reviewed the supplied JSON; the
pending policy read is resolved without a separate privileged rerun by B.
The m1n1 file is staged and hash-verified on lab Data, not installed as a boot
object. A tested read-only Recovery helper is also staged. The user now
authorizes the exact lab policy/custom-object procedure, preserving original
Full Security. Actual Recovery execution is pending; the desktop agent cannot
complete recovery-only operations from macOS. Native Linux remains unvalidated.
Upstream `proxyclient/tools/linux.py` is explicitly on hold. Package integrity
is not boot approval; first live test is the bounded P_NOP USB handshake.

### Matching installer content verification resolved (2026-10-13)

The downloaded 26.6.2 / 25G83 installer contains the original Apple-signed
XAR package at SharedSupport.dmg. `pkgutil` verifies signed Apple Software;
Gatekeeper's package assessment accepts it as Apple Installer. All five signed
entry checksums pass; the installed 695 files/226 directories/26 symlinks match
the signed Payload. Three executable signatures pass strict Apple-anchor checks.
The whole-app custom-omit-rule rejection remains unchanged and unsuppressed;
it is not a successful whole-app execution assessment. The independent package
and content checks resolve the authenticity/integrity investigation. Actual
normal installer GUI launch subsequently succeeded under the user's lab-setup
authorization. Installation and lab boot are now user-confirmed. Details and the repeatable verifier:
`native/boot/macos-installer-download.md`. Eleven synthetic regressions pass.
No boot-policy/custom-object change or native test has been performed. See the
current post-return handoff above.

### B-005 🟢 Isolated Linux environment (resolved 2026-10-11)

* User approved the workspace VM. `vzrun` boots a GPG-verified Arch Linux
  ARM image (`virtualization/images/alarm/`, 32 GB sparse, built via Docker
  Desktop) and runs scripted jobs via virtiofs.
* Remaining limit: Virtualization.framework gives Linux 2D graphics only.
  GPU-in-VM, e.g. krunkit/Venus, would need a host install and new approval.

### B-006 🟢 REA installation (resolved 2026-10-11, project-local)

* `rea-agents@6.4.0` is installed in `tools/rea` (`--ignore-scripts`; 144
  packages, registry signatures verified).
* `~/Documents/iLinux/.mcp.json` plus a deny-list `.claude/settings.json`
  are in place. MCP tools load in the next session launched from
  `~/Documents/iLinux`; the CLI works now.
* 2026-10-13: Ghidra 12.1.4/JDK 21 now run in B's isolated diskless Linux
  lab. REA smoke and four native dossiers succeeded (F-070). macOS has no
  new tool installation. Alpine support and incomplete collection fixups
  remain explicit limitations; three pseudocode results fail the new
  function-boundary gate (F-071).

### B-007 🟢 AI framework baselines (resolved 2026-10-11)

* Project venv `tools/venv`: mlx 0.32.3, mlx-lm 0.32.0, coremltools 9.0.

### B-008 🟢 Power and energy measurement (resolved 2026-10-11, macOS side)

* `powermon` (`benchmarks/src/powermon.c`) reads IOReport "Energy Model"
  and DVFS residency channels **without root**: CPU per core and cluster,
  GPU, ANE, DRAM, memory fabric, display, ISP, AVE, PCIe. `powermetrics`
  isn't needed.
* Remaining: a Linux-side equivalent (PMGR/SMC energy counters) for native
  parity of performance-per-watt.

### B-009 🟡 Energy mode during baseline

* On AC (plugged in), macOS still reports the AC Energy Mode as "Low Power
  Mode: Yes" (`pmset powermode 2`). That is a separate setting from the power
  source.
* Single-core peak was unaffected. Multi-core and GPU sustained limits may be
  lower than in High Power mode. The user chose to keep current settings.

### B-011 🟢 VM uclamp resolved by the packaged custom kernel

* `linux-aarch64` 7.1.6 has no `CONFIG_UCLAMP_TASK`/`UCLAMP_TASK_GROUP`, so
  `omarchy-qos` can test slices, weights and cpusets in the VM but not
  utilization clamps.
* The current `linux-ilinux-vm` kernel enables both options (D-014/D-026).
  The stock-kernel observation remains true, but it no longer blocks the VM.
  Native kernel configuration and hardware scheduling validation remain.

## Knowledge gaps

### B-010 🟠 MIDR values for SOTRA cores unknown

* macOS user space can't read `MIDR_EL1`.
* **Tested 2026-10-11:** the Virtualization.framework guest sees a masked
  MIDR, `0x610f0000` (implementer Apple, part 0x000), on all 18 vCPUs. A VM
  can't reveal it.
* m1n1 confirmed MIDRs for base M5 (T8142, PR #629). T6050 values are only
  obtainable natively.

## Policy constraints

### B-013 🟠 Upstream contribution to Asahi is not possible from this project

* Asahi's generative-AI policy (2026-09-08) forbids AI-generated material
  contributions. See decision D-007.
* This project's code, DT drafts and findings stay local. Upstream
  progress depends on human contributors working independently.


### B-015 🟠 Remaining video conversion and completion gaps

* F-052 fixes tested even/progressive NV12/I420/YV12 downloads; F-053 removes
  planar conversion through opt-in NV12 decode. Package installed in the VM.
* Shader conversions for excluded cases (odd crops/sizes, scaling,
  interlacing, higher bit depth) remain unvalidated and potentially affected.
* Missing decode completion fences still prevent safely making the host
  decoder asynchronous. HEVC/VP9/AV1 and encode are not implemented here.
* REA deep analysis is now available in the isolated lab (F-070/F-071),
  enabling further video research. This has not resolved the remaining
  video format or completion-fence gaps.
