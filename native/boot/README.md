# J716c Linux boot package — boot022 framebuffer correction

Target: **this Mac17,6 / J716c / t6050 M5 Max**. Boot022's corrected framebuffer
passed physical preflight in attempt 3. The launcher requested kernel handoff,
then timed out; the target photo shows **m1n1 SError in EL2** and unhandled-
exception reboot output. Linux kernel/PID 1/one-CPU/60-second liveness are
**NOT OBSERVED**. User confirms Macintosh HD return. See
[attempt 3 result](stage-b-2026-10-13-attempt3-result.md) for sanitized evidence
and M5 offline investigation steps. No retry or new live session authorized.

Kernel, initramfs and installed m1n1 remain unchanged from boot021; its version
marker is still correct and passed the live check. Keep client pin/boot022
intact during diagnosis. No reinstall, Recovery or volume/security/default
changes. Preserve [attempt 1](stage-b-2026-10-13-result.md) and
[attempt 2](stage-b-2026-10-13-attempt2-result.md). The
[Stage B checklist](../../tools/m1n1-client/stage-b-instructions.md) is consumed
history until a new reviewed/user-authorized session.

The completed M5 entry installation is documented in
[boot-entry-setup.md](../../kernel/native-enablement/boot-entry-setup.md).
It is historical context; do not repeat those commands or run them on the M1.

## M1 agent: offline intake first

Follow the commands in [the current Stage B checklist](../../tools/m1n1-client/stage-b-instructions.md).
Download boot022 into its own directory, check the Git-tracked archive digest
before extracting, and verify all files plus the new framebuffer regressions.
Keep boot021 for historical evidence. The current launcher deliberately rejects
its incomplete DT before USB opens. An intake receipt does not authorize a boot.

## Contents and provenance

The private GitHub prerelease `native-j716c-boot022` holds the 16.7 MB archive.
Binaries are release assets, not Git-history blobs. `package-manifest.json`
records every file's exact size and SHA-256, base source and m1n1 offsets.

* **Original job 020:** unchanged `Image`, `t6050-j716c.dtb`,
  `initramfs.cpio.gz`, and `kernel.config`. All three payload digests match the
  original build record. Kernel base `77cb8f24c2381a8abb7272d7bbdec548d6426a8a`
  plus local t6050 patches 0001–0007; GCC 16.1.1, 16 KiB pages.
* **Stage B:** `t6050-j716c-stage-b.dtb` disables the three experimental
  cpufreq controllers, reasserts the already-disabled NVMe node, and removes
  the inaccessible serial `stdout-path`. Original CPU enumeration is retained
  for m1n1 to prune by the actual boot CPU. It is not an SMP-enabled DT.
  Boot022 additionally inserts a disabled, zero-address
  `/chosen/framebuffer@0` placeholder. m1n1 fills it from the actual boot video
  arguments; no physical address is hardcoded. Every other payload is byte-identical
  to boot021.
* **Stage B initramfs:** separately compiled static `diag-init.c`, mounts only
  proc/sys/devtmpfs, prints CPU/memory/DT diagnostics and five-second
  heartbeats. No disk mounts, shell, package manager, networking or agent.
  The 60-second message correctly asks for framebuffer observation.
* **m1n1:** unmodified pinned source
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`, built in the ARM64 Linux VM with
  `M1N1_VERSION_TAG=ilinux-57a9339-boot021 make -j6 ARCH= BUILDSTD=1`.
  Raw AArch64 image, entry offset `0x800`; no release/chainloading flags,
  local startup patch or appended Linux payload. Without a payload it enters
  the proxy path. This exact image is already installed on the approved lab entry.
* Toolchain versions, m1n1 licence and the diagnostic source are included.
  Kernel source/patch recipe is job 020; packaging/build recipe is
  `virtualization/jobs/021-native-boot-package/`; the DT-only correction and
  its reproducible regression are `virtualization/jobs/022-framebuffer-handoff/`. No Apple binary, firmware,
  raw ADT, machine identifier, credential or personal file is in this archive.

**HID provenance correction:** job 020 compiled the hardened HID object
separately *after* linking `Image`, then reverted the source. The exported
kernel Image is the seven-patch baseline, not a kernel with that extra HID
hardening linked in. That driver is not the Stage-B input path.

## What the launcher changes

The old upstream `tools/linux.py` always starts secondaries and initializes
frequency policy; `m1n1.setup` also resets a PMU panic counter. This original
launcher does not call those paths or open an interactive shell.

For a later explicitly approved session it:

1. Verifies all payload hashes and the clean pinned controller checkout.
   Re-identifies exactly one macOS primary CDC data interface by VID/PID
   1209:316d and interface 1. The Stage-A-tested selector is shared; there is
   no filename-suffix fallback. `--device auto` avoids putting identifiers in
   command history. Explicit paths must match that same sole primary.
2. Checks chip `0x6050`, the packaged m1n1 version marker, all 32 m1n1
   secondary-state slots, J716c board compatibility and boot framebuffer.
3. Allocates RAM, uploads the uncompressed Image, Stage-B DT and initramfs,
   and uses fixed arguments with `maxcpus=1 nr_cpus=1 cpufreq.off=1`.
4. Lets m1n1 perform its standard DT fixups, then reads the effective DT
   **in memory only**. Aborts unless it exposes exactly one CPU, an enabled
   boot framebuffer, disabled NVMe/cpufreq and the expected arguments.
5. Rechecks secondary state, performs cache maintenance/DAIF setup, and
   requests the kernel handoff. No automatic retry. A 180-second deadline
   bounds the controller operation; the serial port closes on exit.

The state flags describe cores started by m1n1, not an independent probe of
every physical core's electrical state. Version matching is a consistency
check, not secure attestation. The effective DT has identifiers added by
m1n1, so it is never printed, exported or committed.

This is **not** a hardware-side-effect-free boot: m1n1 already initializes
hardware, and its DT preparation/handoff runs additional hardware setup.
Disabling a Linux DT node does not undo bootloader initialization. The test
intentionally issues no filesystem writes to the internal SSD.

## Historical live command — attempt 3 consumed

Use the command and stop/return rules in
[the current checklist](../../tools/m1n1-client/stage-b-instructions.md), once,
after M1 offline intake and the human's lab boot. No separate handshake or
automatic retry. Keep the original Macintosh HD at Full Security.

## Observation and stop points

The USB proxy is a **pre-Linux** transport. Native handoff shuts down m1n1's
USB devices. This package does not provide an ongoing USB Linux console,
SSH or an agent connection. m1n1's `phram` buffer is its own log, not a
guaranteed Linux crash dump. The hypervisor's virtual UART is a separate mode
and is not used by this native launcher.

The initial observer is the human at the **M5 display**: kernel banner,
`PID 1 reached`, `online_cpus=1`, and at least 60 seconds of heartbeats.
Framebuffer geometry, format and memory range are checked, but simpledrm/fbcon actually working on
this M5 is still unvalidated. If nothing appears, record that exact result;
do not claim a particular panic or promise to retrieve a log over USB.
Return to macOS through the startup picker after stopping the test. A
power-cycle does not remove the dedicated boot entry or its security policy.

Before any live work, read the corrected
[first-boot plan](../../kernel/native-enablement/first-boot-plan.md).
The M1 agent controls the experiment; the future Linux configuration agent
starts only after real input/network access and an installed Linux environment exist.
