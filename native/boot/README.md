# J716c Linux boot package — Stage A passed; Stage B prepared

Target: **this Mac17,6 / J716c / t6050 M5 Max**. This package is an experimental
RAM diagnostic, not an Omarchy installer. Native m1n1 boot and USB P_NOP passed
on this machine; **native Linux remains NOT RUN**. The dedicated entry is
already installed. Do not repeat installation or security changes. The next
experiment is the [Stage B checklist](../../tools/m1n1-client/stage-b-instructions.md),
one separately authorized RAM Linux boot, followed by original macOS return.
Neither downloading nor verifying this package authorizes a physical boot.

The completed M5 entry installation is documented in
[boot-entry-setup.md](../../kernel/native-enablement/boot-entry-setup.md).
It is historical context; do not repeat those commands or run them on the M1.

## M1 agent: do these offline steps now

From the existing `~/Documents/ilinux` checkout, preserve any local changes
and update with `git pull --ff-only`. Stop on divergence; do not reset/force.
The user already authorized the prepared project-local client on this M1.

```sh
mkdir -p build/native-boot-download
gh release download native-j716c-boot021 --repo nickyrice04/ilinux \
  --pattern ilinux-j716c-boot021.tar.gz --dir build/native-boot-download
(cd build/native-boot-download && shasum -a 256 -c ../../native/boot/archive-sha256.txt)
tar -xzf build/native-boot-download/ilinux-j716c-boot021.tar.gz -C build/native-boot-download
python3 -I native/boot/launch.py --package build/native-boot-download/ilinux-j716c-boot021
python3 -I native/boot/test_launcher.py
python3 -I tools/m1n1-client/test_package.py
mkdir -p build/native-intake/receipts
tools/m1n1-client/run.sh tools/m1n1-client/verify-package.py \
  build/native-boot-download/ilinux-j716c-boot021 \
  --manifest-sha256 "$(cat native/boot/intake-manifest-sha256.txt)" \
  > build/native-intake/receipts/boot021.json
tools/m1n1-client/run.sh tools/m1n1-client/check-toolchain.py
tools/m1n1-client/run.sh tools/m1n1-client/test_usb_check.py
tools/m1n1-client/run.sh tools/m1n1-client/usb-check.py
```

Do not extract if the archive checksum fails. If the download already exists,
verify it instead of overwriting it. The trusted checksum and file manifest
come from Git; do not substitute a manifest from an unverified download.
`launch.py` without `--launch` uses only Python's standard library and local
files. It neither imports m1n1 nor opens serial ports. The last command reads
cached USB descriptors, reports counts with paths redacted, and opens no port;
absence while the M5 runs macOS is not a failed cable test.

Require exit 0 and a complete JSON receipt from the M1 agent's intake verifier;
the separately tracked manifest digest and `m1n1-revision.txt` satisfy its
existing format. A successful receipt still says `boot_authorized: false`.

Report the Git commit, archive checksum, verifier result, test counts and
client/toolchain pin. Keep the payload under ignored `build/`. Stop there.
Do not execute `--connect`, `--launch`, `tools/linux.py`, `shell.py`, an
installer, `kmutil`, `bputil`, `csrutil`, a disk command or a reboot.

## Contents and provenance

The private GitHub prerelease `native-j716c-boot021` holds the 16.7 MB archive.
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
* **Stage B initramfs:** separately compiled static `diag-init.c`, mounts only
  proc/sys/devtmpfs, prints CPU/memory/DT diagnostics and five-second
  heartbeats. No disk mounts, shell, package manager, networking or agent.
  The 60-second message correctly asks for framebuffer observation.
* **m1n1:** unmodified pinned source
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`, built in the ARM64 Linux VM with
  `M1N1_VERSION_TAG=ilinux-57a9339-boot021 make -j6 ARCH= BUILDSTD=1`.
  Raw AArch64 image, entry offset `0x800`; no release/chainloading flags,
  local startup patch or appended Linux payload. Without a payload it enters
  the proxy path. It must eventually belong to a separately approved OS entry.
* Toolchain versions, m1n1 licence and the diagnostic source are included.
  Kernel source/patch recipe is job 020; packaging/build recipe is
  `virtualization/jobs/021-native-boot-package/`. No Apple binary, firmware,
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

## Live command — one user-authorized attempt after M1 readiness

The user authorized one Stage B RAM boot on 2026-10-13 after M1 confirms
readiness, followed by Macintosh HD return. Keep original Full Security and
make no volume/security changes. No repeat approval is needed for this scope.
Read the current checklist, confirm offline readiness, then use the already
installed dedicated entry with matching m1n1 running and the M5 screen visible:

```sh
tools/m1n1-client/run.sh native/boot/launch.py \
  --package build/native-boot-download/ilinux-j716c-boot021 \
  --launch --device auto --confirm BOOT-J716C-RAM-DIAGNOSTIC
```

The launcher includes its own P_NOP; do not add a separate handshake attempt.
It discovers the actual primary immediately before opening it. The confirmation
string is an accident-prevention control, not a substitute for user permission.
Abort on mismatch or timeout; do not weaken a check or start cores to bypass it.
After any failed live attempt, return to a fresh m1n1 session before another
separately reviewed attempt; RAM allocations and hardware setup are not rolled back.

## Observation and stop points

The USB proxy is a **pre-Linux** transport. Native handoff shuts down m1n1's
USB devices. This package does not provide an ongoing USB Linux console,
SSH or an agent connection. m1n1's `phram` buffer is its own log, not a
guaranteed Linux crash dump. The hypervisor's virtual UART is a separate mode
and is not used by this native launcher.

The initial observer is the human at the **M5 display**: kernel banner,
`PID 1 reached`, `online_cpus=1`, and at least 60 seconds of heartbeats.
Framebuffer *presence* is checked, but simpledrm/fbcon actually working on
this M5 is still unvalidated. If nothing appears, record that exact result;
do not claim a particular panic or promise to retrieve a log over USB.
Return to macOS through the startup picker after stopping the test. A
power-cycle does not remove the dedicated boot entry or its security policy.

Before any live work, read the corrected
[first-boot plan](../../kernel/native-enablement/first-boot-plan.md).
The M1 agent controls the experiment; the future Linux configuration agent
starts only after real input/network access and an installed Linux environment exist.
