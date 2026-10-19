# Blockers

Status legend: 🔴 hard blocker (no path today) · 🟠 blocked pending research or
upstream work · 🟡 pending user approval or action · 🟢 resolved.

## 🟢 Resolved offline — the M1's macOS has no CDC-EEM driver (attempt 17)

boot036's gadget was CDC-EEM; macOS 26.0.1 on the M1 never claims it (stub
kext, not loadable). boot038 switches the functions to CDC-ACM (kernel-log
serial port) + CDC-ECM, whose macOS drivers are loaded on the M1; everything
else is byte-identical. Open until attempt 18: whether the dwc3 interrupt-IN
notification endpoint transmits on this hardware. See
`native/boot/boot038-control-channel-2026-10-16.md`.

## 🟢 Resolved offline — E1 MTP probe stopped on a NameError

Class-scope lookup of a function-local import in `mtp_probe.py` (and
`pmgr_probe.py`). Fixed, with tests that build the live API. Rerun needs the
M1's re-verification and the human's go.

## Current blocker — attempt 23: the DMA fault is on the DART instance the Stage-B DT omits; Linux's only handler reads the other instance

boot040 (attempt 23) repeated attempt 21's stop with the DART made visible. The USB DART is version 2.4; port 1's fault interrupt
(IRQ 43) storms from kernel 3.93 s and the handler for the DT's instance 1 finds nothing pending every time until the kernel
disables the line; at the first bus error the register snapshot shows the sibling instance 0 (not in the DT, never programmed:
`en 0`) with `pend 1` and a stream block holding address `0x3ffff35800`, instance 1 with `pend 0`. Likely, not tested: the
controller's DMA also goes through instance 0, which has no translation, so it faults there and wedges the IN endpoint (the M5's
candidate A: Asahi's two-DART wiring). The capture stopped at 25,911 bytes; no endpoint-0 error. Open: that listing both
instances fixes it, whether stream 0 carries data or descriptors, bulk OUT, and a stream that survives. See
`native/boot/stage-b-2026-10-18-attempt23-result.md`.

## Historical blocker — attempt 21: bulk-IN data stops after 36,909 bytes; the M5's dwc3 flags BUSERR and an apple-dart interrupt storm follows (explained by attempt 23)

boot039's bulk-only function enumerated (+3.88 s), macOS configured it (+8.05 s) and published its vendor interface with no driver
bound, and the M1's read-only reader opened it and read 36,909 bytes (476 intact records of the M5's early kernel log); the stream
then stopped for the remaining 10 minutes, with the link up and SOFs counting. The M5's own status line (video) shows `BUSERR` on
port 1's dwc3 from the first heartbeat after the configuration, its interrupt counter frozen (`irq146`, `ev0`), `1in` with 17
hardware TRBs and a frozen dequeue index, the log FIFO full (`q8192`); Linux printed `irq 43: nobody cared` (`handlers:
apple_dart_irq`) and disabled the IRQ at 9.956 s (the digit is the weakest reading). EP0 stayed healthy (zero timeouts in 10
minutes) and the TX FIFOs are sane (199 words each). Likely, not tested: a DMA fault through the USB DART (mapping, window or
stream) whose error interrupt the Linux handler does not recognise on t6050. Open: which DART, the faulting address, bulk OUT, and a
stream that survives. See `native/boot/stage-b-2026-10-18-attempt21-result.md`.

## Historical blocker — attempt 18: macOS configures the ACM + ECM gadget, then control transfers time out; no serial, no network (a bulk-only function did not reproduce it in attempt 21)

boot038 enumerated (+3.95 s) and macOS selected configuration 1 (+8.45 s), but no interface node was
published, no ACM or ECM driver attached, and the device's control endpoint then timed out four times
before a transaction error (attempt 17's EEM gadget had none). On the M5 the UDC reads `configured`
while `usb0` stays down; Linux itself is healthy (ladder, 60 s milestone, heartbeats to 113.7 s).
Likely, not tested: the interrupt-IN notification endpoints ACM and ECM add (`ncm-interrupt-ep-disabled`
in the ADT). Open: a gadget with no interrupt endpoint (bulk-only vendor function, read from user space
on the M1), and dwc3 debugfs state in the heartbeat. See
`native/boot/stage-b-2026-10-16-attempt18-result.md`.

## Historical blocker — macOS 26.0.1 has no EEM driver, so the USB control channel cannot come up (attempt 17)

Attempt 17: Linux's three device-mode dwc3 controllers, three CDC-EEM gadgets and key-only dropbear all
started and the M1 enumerated the cabled port within 8 s, but macOS attached nothing to the EEM
interface (`com.apple.driver.usb.cdc.eem` is not in its kernel collection), so no interface or SSH
exists. Open: choose ECM, NCM or ACM serial (macOS loads ECM and ACM today) and resolve the
interrupt-endpoint question (`ncm-interrupt-ep-disabled`). See
`native/boot/stage-b-2026-10-16-attempt17-result.md`.

## Historical: Baseline reached — attempt 16 (boot035) ran the whole release ladder; SMC-versus-host attribution open

With the seven SMC-owned domain nodes removed from the Stage-B DT, Linux released all
74 boot-on unclaimed domains one at a time, completed the ladder at 57.3 s and kept
heartbeating to >= 108 s with PID 1, one CPU and the 60 s milestone. No reset, no M1
panic. Whether the SMC domains (or simultaneity) caused attempt 14's reset and the SMC
domains (or the M1's own reset) attempt 15's is not separated, since attempt 16 changed
both. See `native/boot/stage-b-2026-10-15-attempt16-result.md`. Remaining blockers: a
Linux control channel and RAM root, SMP, idle/DVFS, display, GPU.

## Historical Stage B blocker — SMC-owned domains in the Stage-B DT (boot035 prepared)

Both native resets followed the release of an SMC-owned `smc_i2cm` power domain
by ≈ 5.6 s (Likely mechanism; not proven). Asahi exposes no `smc_*` domain on
any SoC. Boot035 removes the seven from the Stage-B DT and keeps everything else
identical; attempt 16 (NOT RUN) should run the full release ladder and 180 s.
See `native/boot/attempt15-review-2026-10-15.md`.

## 🟢 Resolved — the SSH key for boot036 (control channel)

The M1 generated its own key and committed only the public half (`a6717b0`,
`SHA256:o7wtpNY0…`); boot036 authorizes exactly that key. Original note:

boot036 (prepared offline, NOT RUN) authorizes one SSH key for root on the
native Linux side. The built package carries a test key from job 041, whose
private half is only on the M5. Proposed: the M1 generates its own key and only
the public half is committed (`kernel/experiments/usb-gadget/authorized_keys`);
job 041 then rebuilds and only the initramfs changes. Needs the user's choice
before attempt 17. See `native/boot/boot036-control-channel-2026-10-15.md`.

## Historical Stage B blocker — attempt 15 reset at ~27.7 s is confounded by an M1 host panic

Boot034 removed attempt 14's bulk sync_state power-off and the ~8.8 s reset did
not recur; Linux ran >= 27.6 s with a 17-step release ladder. The SoC then reset
silently at ~27.7-27.85 s. The M1 host kernel-panicked (Apple USB CDC driver)
at the handoff and hard-reset in the same seconds, so the ladder, step 6 (+~5.7 s)
or step 17, and a host-side USB reset cannot be separated. The controller record
is incomplete. Recommend one clean rerun of unchanged boot034. See
`native/boot/stage-b-2026-10-15-attempt15-result.md`. No retry or settings changes.

## Historical Stage B blocker — silent SoC reset ≈ 5.6 s after sync_state (attempt 14)

Attempt 14 reached native diagnostic PID 1 and reset silently at kernel ≈ 8.77 s.
Boot034 (attempt 15, **NOT RUN**) tests whether genpd sync_state powering off the
152 unclaimed boot-on PMGR domains is the trigger. The hypervisor route is blocked
at the m1n1→m1n1 chainload (hv002 session 2); hv003 (**NOT RUN**) repairs and
instruments that chainload and adds an on-screen breadcrumb strip; see
`native/hv/hv002-chainload-analysis-2026-10-14.md` and `native/hv/README.md`.
Neither establishes native Linux, SMP, graphics or efficiency.

## Current Stage B blocker — silent SoC reset ~5.6 s after native PID 1 (attempt 14)

Boot033 reaches native diagnostic PID 1 (3.152 s) with one CPU and two
heartbeats. Both GPIO controllers probe (main cache 221/216/5). The SoC then
resets at kernel ~8.77 s with no message and reboots to Macintosh HD. The
60-second liveness milestone is not reached, and the trigger is unknown.
Attempt 14 is the first to run past the GPIO controllers: ASC mailbox and SART
probes, late initcalls including sync_state, userspace and idle. M5 next:
read-only return checks and offline review of PMGR sync_state power-off, ANS
mailbox/SART side effects and the idle path. See
`native/boot/stage-b-2026-10-14-attempt14-result.md`. No retry or settings changes.

## Historical Stage B blocker — no attributed GPIO/worker progress in attempt 13

Boot032 controller including live GPIO exclusions and final DT PASS. Native
Linux is observed; final photo P05/W00/H06/D0000/I000/B00/C0000, S unclear.
Kernel heartbeat advances but no nonzero device/GPIO boundary, actual cache/IRQ
counts, return/error, PID 1 or userspace 60s milestone observed. P05 locates the
first work-flush boundary by source; exact blocked task/PC/cause unknown.
I000 with unbound D/C and B00 is not a pin 0 fault. GPIO repair remains unvalidated.

Post-attempt-13 return is now confirmed by user Full/Permissive report plus M5
original-root/build/FileVault/SIP/staged-m1n1 read-only checks. Default/installed
object/authenticated-root not rechecked; no fresh policy exit codes supplied.
Boot033 removes confirmed scheduler framebuffer overhead without changing GPIO
or bypassing drivers. Build/regression/controller/intake and generic liveness
PASS; its effect on the native stall is unproven. M1 boot033 intake, 102 cases,
hashes and Image-only delta PASS; one bounded filmed attempt 14 is next. S is now sampled by the bounded watchdog, not immediate.
Keep full recording through the stop criterion; stop by the handoff deadline
without waiting for media transfer. No reinstall or settings changes.

## Historical Stage B attempt 1 preflight stop — 2026-10-13

The authorized attempt reached target chip/packaged-marker/secondary PASS, then
KeyError before upload/handoff. Linux NOT RUN. User confirms Macintosh HD return;
new read-only return checks now confirm build/FileVault/SIP/authenticated-root
and user-supplied original Full/lab Permissive JSON. The root-lookup API defect
is fixed offline; 35 launcher/ADT tests pass, B reran 31 and package verification.
Live throw-site detail was not retained; the fix is not hardware-verified.
User now requests next-boot preparation: one corrected Stage B attempt 2 is
ready under the same protection constraints. Follow the updated checklist;
no automatic retries after that attempt. See `native/boot/stage-b-2026-10-13-result.md`. Earlier readiness and
live-version-pending statements below are historical; packaged marker now PASS.

## Latest Stage A status — 2026-10-13

USB primary identification and P_NOP are validated after `70ad452`/`974e894`:
one primary interface, one reply, exit 0, 0.158 seconds, followed by Macintosh
HD return. M5 read-only review confirms build/FileVault/SIP/authenticated-root
and staged m1n1 hash. The user's fresh JSON reports original Full/lab
Permissive, both exit 0. Default selection was not independently rechecked.

The next launcher's stale P_01 suffix gate is now fixed with the same shared
USB descriptor selector and tested `--device auto` path. Local offline payload
verification and 54 regression cases pass; M1's full controller suite is next.
Boot021/client pin unchanged. **Native Linux and live build-marker verification
remain NOT RUN.** User now authorizes one Stage B attempt after M1 confirms
readiness, then Macintosh HD return. M1 readiness is pending; P_NOP does not
resolve CPU, power, display/GPU or Linux peripheral enablement. The historical
provisioning-pending statements below are superseded by completed installation
and this status. Current checklist: `tools/m1n1-client/stage-b-instructions.md`.

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
