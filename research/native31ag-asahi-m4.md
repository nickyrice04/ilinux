# 31AG: reuse Asahi and compare the working M4 boot contract

2026-10-26 Eastern. Public-source and repository review only: no Apple binary
analysis, downloaded-code execution, VM, installation, partition or security
operation was performed by this review. The 31AF restoration remains unconfirmed;
this document does not prepare a native restart.

## We already extend the Asahi foundation

The current native platform is an Asahi-derived Linux build with an Omarchy
userspace. Omarchy does not replace the Apple hardware drivers. The repository
records the following concrete foundation:

| Layer | Existing project provenance | Practical consequence |
| --- | --- | --- |
| Installed/raw bootstrap | Unpatched Asahi m1n1 `57a9339ffd1876e78297b17d34dece8cff8fa1ba`, boot021 | Preserve the known working raw path and its exact rollback object. |
| Linux | AsahiLinux/linux `77cb8f24c2381a8abb7272d7bbdec548d6426a8a` plus local t6050 series 0001–0007 and later bring-up fixes | Continue adding local driver/DT changes to this tree rather than designing a separate kernel. |
| Native desktop baseline | boot042 Image and two-stage Omarchy root; attempt 27 reached the desktop, USB control and keyboard | Native Linux already works on one core. The current experiment addresses an alternate route toward the remaining CPU problem. |
| Graphics boundary | Attempt 27 used software rendering on the boot framebuffer | A Linux desktop or a Mesa package alone does not establish native G17C acceleration. |

Sources: [boot021 manifest](../native/boot/boot021-package-manifest.json),
[current package manifest](../native/boot/package-manifest.json),
[kernel build](../virtualization/jobs/020-t6050-full-build/RESULTS.md),
[attempt 27 result](../native/boot/stage-b-2026-10-20-attempt27-result.md).
Old preparation-time `native_tested:false` fields are frozen records; the later
native result owns what was actually observed.

Using licensed open-source code in this independent repository is consistent
with the intended architecture. Contributing these AI-assisted/REA-derived
changes upstream is a separate issue: Asahi broadly excludes material LLM
contributions and imposes its own reverse-engineering provenance rules. We can
maintain our licensed downstream changes without asking Asahi to accept them.
Preserve existing licenses and attribution; do not submit this work upstream.
[Asahi policy](https://asahilinux.org/llm-policy/),
[m1n1 licensing](https://github.com/AsahiLinux/m1n1/blob/51b747dced07a58eacf5dabc31ed6f00bcfa20fd/README.md#license).

## The published working M4 workflow uses the raw route

Gravity's current tethered-boot instructions compile `build/m1n1.bin` and install
it as a raw boot object with entry 2048 and lowest VA 0. They specify macOS
26.6.2 for M4/A18 Pro and 27.0 for M5. This is a published workflow, not a test we
ran. Its partition/security commands are not adopted or executed here.
[Gravity workflow](https://gravitylinux.org/docs/developers/tethered-boot/).

The public Gravity bootloader was inspected at
`f02d4a52017915febb222539636b5b025a70407a`. Its entry preserves incoming x0 for
its ordinary bootstrap, and its retained Mach-O linker has the conventional
thread entry and ordinary code/data layout, without the resident observer's
separate DATA_SPTM/BOOT_EXEC contract. The documented build output remains the
raw binary. This bounded check finds no reusable, hardware-qualified resident
entry adapter in those entry/linker files.
[Entry](https://github.com/GravityLinux/bootloader/blob/f02d4a52017915febb222539636b5b025a70407a/src/start.S#L65),
[linker](https://github.com/GravityLinux/bootloader/blob/f02d4a52017915febb222539636b5b025a70407a/m1n1.ld),
[build documentation](https://github.com/GravityLinux/bootloader/blob/f02d4a52017915febb222539636b5b025a70407a/README.md).

Asahi also documents raw stage-one installation as the normal fuOS path and
labels the older Mach-O installation route not recommended. That supports our
existing raw baseline; it does not qualify the different 31AF resident ABI.
[m1n1 user guide](https://asahilinux.org/docs/sw/m1n1-user-guide/#installation).

Asahi's Linux 7.2 report distinguishes raw m1n1 from an XNU-classified boot that
loads SPTM. Its M4 hypervisor work emulates GXF/SPRR and loads SPTM with XNU as a
guest. That enables hardware research; it is not a published native resident
host adapter or evidence that raw M5 secondaries work. The same report describes
locked M4-era CPU controls and an early idle workaround. Our launcher already
retains `idle=nop arm64.nowfxt`; those later Linux idle controls cannot identify
a failure before the custom observer's first marker.
[Asahi report](https://asahilinux.org/2026/08/progress-report-7-2/),
[local launcher](../native/boot/launch.py).

## M4/M5 similarities are real and already represented in code

Freshly fetched public Asahi m1n1 `51b747dced07a58eacf5dabc31ed6f00bcfa20fd`
was compared with our installed `57a9339` source. `src/smp.c` and
`src/chickens.c` are byte-identical. The startup dispatch already groups M4
Pro/Max T6040/T6041 and M5 Pro/Max T6050/T6051 at PMGR start offset `0x88000`.
Base M4 T8132 instead uses `0x34000`. Copying a base-M4 register address onto the
Max would undo the existing family-specific selection. Gravity's current
`src/smp.c` makes the same distinction.
[Asahi dispatch](https://github.com/AsahiLinux/m1n1/blob/51b747dced07a58eacf5dabc31ed6f00bcfa20fd/src/smp.c#L299),
[Gravity dispatch](https://github.com/GravityLinux/bootloader/blob/f02d4a52017915febb222539636b5b025a70407a/src/smp.c#L280).

The common feature table already applies `features_m4` to M4 and M5 family
parts, with locked Apple-specific register handling. M5's M cores must still be
distinguished from older E cores: Asahi's original T6050/T6051 report explicitly
documents that distinction and says secondary cores power on but do not execute
on its tested firmware versions. Sharing a generic feature table therefore does
not establish matching core-start permissions or lifecycle.
[Feature table](https://github.com/AsahiLinux/m1n1/blob/51b747dced07a58eacf5dabc31ed6f00bcfa20fd/src/chickens.c#L112),
[T6050/T6051 bring-up](https://github.com/AsahiLinux/m1n1/pull/610).

The fresh utility-header difference adds a rounding helper and Armv9.4 assembler
directives around register/system operations. It does not change the startup
sequence in the two byte-identical source files. This review identifies no new
SMP repair supplied by a blind default-branch bootloader upgrade.
[Utility header](https://github.com/AsahiLinux/m1n1/blob/51b747dced07a58eacf5dabc31ed6f00bcfa20fd/src/utils.h).

## Concrete code to reuse, without another speculative boot

* Keep the working Asahi raw bootstrap, its ADT-based hardware detection and
  M/E/P core distinction. A marketing-name substitution is not hardware
  detection. Preserve the local board/chip identity guards rather than renaming
  this target from an upstream naming table.
* Continue using Asahi's DART, RTKit, mailbox, PMGR, HID and NVMe foundations.
  M4+ NVMe register-window changes and SARTv4 were already incorporated into our
  local series. The macOS-15+ NVMe firmware-ABI series is already in base
  `77cb8f24`; do not apply it twice. Existing offline builds/read-only storage
  tests are useful foundations, not native storage-speed evidence.
  [Local implementation/provenance](../kernel/patches/t6050/README.md),
  [boot042 integration](../native/boot/boot042-keyboard-modules-2026-10-19.md).
* Reuse the public M4 raw workflow as a comparison/control for the raw contract,
  and the public SPTM-aware hypervisor machinery for future qualified tracing.
  Neither is a drop-in positive control for a native resident Mach-O observer.
  Establish the firmware producer and entry ABI first.
* Track the M5 firmware pin separately from the M4 pin. The current local
  research targets 25G83, while Gravity's public M5 instructions target 27.0.
  That is an explicit comparability limit, not authorization or a recommendation
  to update firmware during this work.

M4 support is also model-specific. Gravity advertises an early alpha for the
base-M4 Mac mini with GPU acceleration, while its other M4 models remain WIP.
Asahi's own feature table reports a different, incomplete support scope. Neither
claim should be expanded into universal M4 support or M5 parity.
[Gravity status](https://gravitylinux.org/),
[Asahi M4 matrix](https://asahilinux.org/docs/platform/feature-support/m4/).

## Read-only source comparison receipt

The public files below were fetched as data and hashed without executing them.
All comparisons use the exact current Asahi source revision named above.

| File | Bytes | SHA-256 | Equal installed-pin source? |
| --- | ---: | --- | --- |
| `src/smp.c` | 14412 | `4b000be8d4e6437fc24351a57db5277785cc2e427045fb45d1750b158f2b8766` | Yes |
| `src/chickens.c` | 10196 | `1f0413af258ec3c76ded686429e1cb50abb5f528df77a0d546795b22455e19ef` | Yes |
| `src/utils.h` | 15358 | `8a4e51a96e87b60155394df0fa1ac1b9b5dbd349cb337c2fc315877b476c1170` | No; differences summarized above |
| `README.md` | 5395 | `8a511740649191deef65929adadfc3b7f3dd42784c8e8bc0bd5cfe314fe70329` | Yes |

These facts support continued reuse and a narrower handoff investigation. They
do not qualify a new M5 physical test, resolve rollback/default uncertainty or
prove that an Apple update alone is required.

## Appendix: locating the configured custom boot object

Fresh primary Asahi installer `main` is
`e93743d52178b3e26e428fa05174ef549abf30cb`. Its `src/osenum.py` is 10014 bytes,
SHA-256 `e467caaf1516f41973ccf8e7fb0950e5d668fa87813767e0157f6c34fc594389`.
This is a public implementation comparator, not proof of every local firmware
version's contract.

The chosen OS's `vgid` comes from APFSVolumeGroupUUID (line 166). Its Preboot
mount comes from that OS's volume set (187–188). The installer queries the
chosen volume group's boot policy (235–248), extracting `coih` and `nsih`, then
constructs this path (251–257):

```text
<Preboot mount>/<vgid>/boot/<nsih>/System/Library/Caches/com.apple.kernelcaches/kernelcache.custom.<coih>
```

It inspects m1n1's version only if that policy-selected file exists. Therefore a
broad directory/prefix scan establishes candidate presence, not which custom
object is configured. Binding the selected file requires the relevant policy
keys or an independently qualified equivalent selector. A configured object for
one OS also does not establish the default Startup Disk or prove which object
executed in a previous attempt.
[Primary source](https://github.com/AsahiLinux/asahi-installer/blob/e93743d52178b3e26e428fa05174ef549abf30cb/src/osenum.py#L235).
No host policy/state query or installer execution was performed for this review.
