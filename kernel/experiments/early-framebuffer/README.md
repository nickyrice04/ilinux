# Boot024: make the native handoff observable

## Problem and evidence

Attempt 4 (`d4209d3`, M1 report `4b1a5b9`) passed the DAPF correction,
prepared-DT gates and kboot request/reply. The human saw the logo and fast text;
Linux/PID 1/liveness were **not observed**. This does not locate a kernel fault.

**Confirmed, static:** REA 6.4.0 / Ghidra 12.1.4 queried `fb_shutdown` and
`m1n1_main` in the exact retained ELF corresponding to the installed boot021
image. The first clears the framebuffer console; the second calls framebuffer
shutdown and MMU shutdown before its indirect next-stage call. Kboot selects
`restore_logo=false`, which still clears console text. Thus a remaining logo
can be stale scanout during a silent handoff. A successful proxy reply precedes
that final transition; it is not proof of Linux execution.

`audit.py` verifies exact-image/ELF provenance, REA's rebasing and function
boundaries, all 144 instruction positions against the two bodies, high-pcode
bounds, and the exact instruction words with the existing Apple LLVM decoder.
The pinned public source independently matches the teardown order. See
`evidence.json`. REA pseudocode is supporting evidence, not verified source.
Raw analysis remains in ignored local lab storage; no Apple binaries were needed.

**Confirmed, design:** boot022 uses `console=tty0` and simpledrm/fbcon. Those
are later than the initial CPU/MMU and architecture setup. The standard EFI
framebuffer early console requires EFI screen metadata; our direct m1n1 boot
is not an EFI boot. Adding `earlycon=efifb` alone would not supply that metadata.
See the pinned kernel's `drivers/firmware/efi/earlycon.c` and
[Linux's earlycon documentation](https://docs.kernel.org/6.15/admin-guide/kernel-parameters.html).

**Unknown:** whether attempt 4 stopped in final bootloader cleanup, CPU/MMU
setup, a later kernel subsystem, or only failed to display Linux output. No
basis yet to blame AIC, GPU, SMP or to repeat the previous DAPF diagnosis.

## Original implementation

`apply.py` modifies an isolated copy of the retained job-020 kernel; the
original build stays intact. Configuration and every other boot022 payload
stay byte-identical. It adds:

* Three inline AArch64 checkpoints in `primary_entry`: entry, return from
  `init_kernel_el`, and return from `__cpu_setup`, all before MMU enable.
  They draw 64x32 white rectangles near the top left, at x=16/96/176, y=16.
  Only x9–x14 and condition flags are clobbered, at sites where those are dead;
  x0–x3, x19–x21, stack and LR are preserved. They do not enable CPUs or touch
  controller registers. Zero descriptor means no framebuffer access.
* A 16-byte, zero-initialized kernel data descriptor, preceded by a unique
  16-byte marker. The launcher fills base and stride **in RAM only**, from
  the already validated prepared DT. It checks the zero value and readback.
  Both formats use 32-bit pixels; all RGB bits set works for 8- and 10-bit RGB.
  The descriptor lies at relative Image offset `0x217d790`, checked against
  the actual linked symbol. The controller changes no kernel instructions.
* `ilinux_earlycon.c`, a flat-DT early console requested by `earlycon=ilinuxfb`.
  It checks J716c, one enabled direct `/chosen` framebuffer, 64-bit identity
  addressing, supported formats and bounded dimensions/stride/range.
  It uses Linux's existing early-memory mappings and built-in font, scaled 2x,
  before IRQ/device probing. A circular text layout avoids full-screen copies
  on each line. It maps the framebuffer permanently at early initcall time,
  stops safely on mapping failure, and yields to a registered real console.
* `initcall_debug` records each later initializer's call/return. This is a
  diagnostic kernel, **not a performance benchmark or deployment default**.

The early console accesses only the existing framebuffer allocation; it does
not implement DCP/GPU acceleration. A missing rectangle remains ambiguous:
execution might not have reached it, or the display write may not be visible.
Three rectangles plus no text narrows investigation but does not independently
prove that the MMU transition failed. Film the screen before handoff, then use
observable milestones rather than assumptions.

## Validation (2026-10-13 local / 2026-10-14 UTC)

* Full incremental ARM64 `Image` link PASS, no build warnings/errors. Linux
  7.1.9, base `77cb8f24c2381a8abb7272d7bbdec548d6426a8a` + t6050 0001–0007,
  retained tree `863199d8b4a3`, GCC 16.1.1, binutils 2.46.0, original 16-KiB config.
* Actual driver C parser/renderer with real libfdt and checked synthetic RAM:
  PASS with AddressSanitizer/UBSan. Covers 8-/10-bit RGB, wrong board/status/
  format/dimensions/stride/reg, horizontal/vertical wrapping, remapping and
  failed mappings. Kernel mapping APIs are stubbed in this test.
* Actual assembly macros executed on ARM64 Linux: PASS under C harness with
  sanitizers; zero-pointer no-op, preservation of x0–x3 and exhaustive pixel
  comparison of each bounded rectangle. This tests ordinary RAM, not scanout.
* Launcher 31, descriptor guard 6, DAPF guard 16, pinned DAPF parser 2,
  pinned root-ADT 4, real proxy serializer 1, framebuffer 5 cases PASS in Linux.
* Exact packaged Image + unchanged initramfs booted in a **diskless generic
  VZ VM**, one vCPU, 4 GiB, no network/disk: PID 1, `online_cpus=1` and 60-second
  heartbeat PASS. The descriptor remains zero, and the J716c-only early
  console does not activate on VZ. This is not a native framebuffer test.
* Package intake checks all 13 receipt files; only Image changed relative to
  boot022. Boot024 archive and all artifacts have pinned SHA-256 manifests.
* **Native boot024/checkpoints/early console: NOT RUN.** Native Linux remains
  NOT OBSERVED. No performance or efficiency improvement is claimed.

During development a unit test caught a 17-byte marker/alignment error; it
was corrected to 16 bytes before the final build, symbol audit and package.
An initial idle VM lacked an executable job script and was stopped/restarted;
subsequent jobs completed and shut down. Neither affected native boot state.

## Reproduce

Run `virtualization/jobs/024-early-framebuffer/run.sh` in the existing isolated
build VM with this repo shared read-only as `ilinux`, the job shared writable
as `job`, and retained `/var/tmp/t6050-build/linux`. It copies/reflinks the
baseline to `/var/tmp/ilinux-boot024/linux`, applies the diagnostic changes,
runs C/assembly tests and links Image. `out/` is ignored; no build occurs on
macOS. Job output includes disassembly, symbols, build and test logs.

Host packaging (own stdlib script, no target execution):

```sh
python3 -I native/boot/make-package.py \
  --out virtualization/jobs/024-early-framebuffer/out \
  --destination build/native-boot024 --name ilinux-j716c-boot024
```

Do not overwrite an existing archive; preserve the tested artifact. Rebuilding
can change compiler timestamps/build counts and therefore its digest. The
released artifact's manifest is authoritative. The installed m1n1 stays boot021;
source DAPF guard build023 remains an uninstalled proof build.

Next physical procedure: `tools/m1n1-client/stage-b-instructions.md`.
