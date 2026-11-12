# M5 Max boot route review — November 12, 2026

## Decision and scope

Resume offline integration around the public **direct Mach-O/CTXR execution-window
route**, while keeping the newly repaired raw route as an alternative. Both have
more useful evidence now than another variant of the silent 31AF resident-entry
observer. Neither route is ready to install on this machine from this review.

The user identified the November 9 Gravity discussion about moving from the raw
path to a Mach-O path without resident SPTM, partly for power-management work.
Public code and a later J716c report support investigating that distinction.
This document records a design and qualification plan; it authorizes no firmware,
volume, boot-policy, Startup Disk or installed-boot-object change.

This would still be a **native Linux boot alongside macOS**. After Linux starts,
macOS is not running behind the desktop. Returning to macOS uses the existing boot
selection. A boot format does not itself determine whether two operating systems
are installed. A normal macOS-hosted VM remains a different option with different
hardware access and performance limits.

## What changed since the pause

### Apple has published a raw-boot fix

Apple's macOS 27.3 beta notes identify the M5 Pro/Max/Ultra single-core limitation
for third-party systems loaded from a custom raw object as resolved under mBoot,
issue **182898702 / FB23916610**. Apple's release feed identifies the first beta
as **26C5035r**, released **November 3, 2026**. These are vendor statements, not a
physical result from this project.

Sources: [Apple release notes](https://developer.apple.com/documentation/macos-release-notes/macos-27_3-release-notes),
[Apple developer releases](https://developer.apple.com/news/releases/).

The old Gravity About statement about waiting for Apple, qualified to macOS 27
beta 5, must not override that newer evidence. It remains historical context.

### A report now matches this board

The November 11 comment by cameroncooper in
[Aurora's M5 MacBook Pro hardware discussion](https://github.com/aurora-silicon/linux/discussions/142)
reports a J716c / Mac17,6 / T6050 RAM boot with:

| Component | Reported working value |
| --- | --- |
| macOS / loader | 27.2.1, `26B131`; `mBoot-20457.41.3` |
| Aura | `bd9f3e8273dc79ae9095c19c2c4f32218446ad4e` |
| Linux | `dc8f6f77934b471a13c91e7780e2d91ebc904b3d` |
| Entry | Padded Mach-O Stage 1; 128 MiB CTXR window |
| Local difference | USB2 CDC initialization in proxy mode |

The operator reports CPUs 0–17 online, reading the NVMe partition table, and
N1/DHCP/SSH returning after a tethered reboot. The panel uses simpledrm. Both
source commits resolve publicly. The comment supplies no exact image digest,
complete configuration, local CDC diff or raw console capture. It is a useful
named-board report; it is not a reproducible released package or a memory-speed
benchmark. CPU-online reporting does not replace concurrent per-core work tests.

The discussion's November 8 summary predates this comment. Its older statement
that no public loader can start T6050 is not the current source state.

### Current firmware on this project machine

The parent session's read-only November 12 checks found **both the running macOS
and iLinux Boot Lab at 26.6.2 / 25G83**. That does not match either newer working
firmware comparison above. The public wrapper being parseable by a 25G83 utility
does not prove that 25G83 firmware executes it successfully on J716c.

Do not describe a lab macOS update as isolated from all machine firmware. Apple
Silicon has system-global firmware as well as per-OS loader/firmware components.
Preserving Macintosh HD's files and Full Security is compatible with the project
goal, but a firmware update can still affect the machine as a whole. Such an
update requires separate review and authorization.

Sources: [Apple boot modes](https://support.apple.com/en-gu/guide/security-pdf/sec10869885b/1/web/1),
[Asahi boot architecture](https://asahilinux.org/docs/platform/introduction/).

## The alternate entry contract

At the reported Aura revision, the public
[Mach-O guide](https://github.com/aurora-silicon/aura/blob/bd9f3e8273dc79ae9095c19c2c4f32218446ad4e/docs/macho-boot-object.md)
and [wrapper](https://github.com/aurora-silicon/aura/blob/bd9f3e8273dc79ae9095c19c2c4f32218446ad4e/tools/macho_boot_object.py)
describe an object whose segment layout produces `kcbz=0`. It enters the loader
directly, leaving secondary execution restrictions to be accommodated. The loader
places Linux in a 128 MiB executable window, releases cores through spin-table,
and relinquishes control to Linux at EL2. Kernel runtime executable allocations
must use the same pool. This is distinct from retaining a privileged SPTM host or
running Linux under macOS.

The matching Linux
[configuration](https://github.com/aurora-silicon/linux/blob/dc8f6f77934b471a13c91e7780e2d91ebc904b3d/arch/arm64/Kconfig)
provides `CONFIG_ARM64_CTXR_EXECMEM`: executable allocation confinement and a
verifier, covering modules and runtime-generated kernel code. A kernel carrying
only our earlier platform patches does not satisfy this contract.

Padding also has a public implementation: `aurora-installer` revision
`2d5c44e37d04173cb7085120b34862b75a609934`,
[`AuraStage1.swift`](https://github.com/aurora-silicon/aurora-installer/blob/2d5c44e37d04173cb7085120b34862b75a609934/macOS/Recovery/Sources/Account/AuraStage1.swift),
`MachOBootObject.expandExecuteWindow()`. The ordinary wrapper alone does not
supply the OS execution window. The exact padding revision used by the November
11 operator is still unknown; this newer source is an implementation comparator.

The guide also reports that Mach-O enrollment enables the lab's Kernel CTRR
policy again. Therefore restoring the old raw boot021 bytes alone is not a
qualified rollback for this new route. Review policy restoration explicitly
before asking for a new physical sequence. Do not run generic upstream Recovery
scripts as if they were this project's already reviewed restoration procedure.

Our 31AF observer instead attempted a resident handoff with a different entry
ABI and required monitor metadata. Its logo-only result never established entry.
Reusing that package or treating its reservations as interchangeable would hide
the very distinction the new public implementation supplies. Preserve its frozen
source and result records.

## Compare the two candidates

| Route | Strong evidence | Main integration question |
| --- | --- | --- |
| Raw object with 27.3 beta boot firmware | Official Apple fix; separately reported J716s boots | Obtain the correct lab-paired loader and compatible platform stack without assuming that updating only the running OS changes the selected boot environment. |
| Direct Mach-O with executable confinement | Public implementation; matching J716c report on 27.2.1 | Reproduce padded Stage 1, CDC difference, secondary vectors and the complete loader/kernel executable-window contract. |

Neither option establishes compatibility with our current 25G83 environment.
Select the route after source/build qualification and a concrete firmware plan.
Neither is authorization to install a beta, recreate a volume or replace boot021.

## Proposed system and reuse

```text
Existing dedicated lab boot entry
  -> reviewed, enrolled Stage 1 with validated execution-window geometry
  -> pinned RAM-chainloaded Aura / direct Linux handoff
  -> matching J716c kernel + device tree + diagnostic initramfs
  -> existing authenticated two-stage transfer
  -> rebuilt Omarchy RAM root with matching kernel modules
```

Reuse the M1 transport, digest/size intake, two-stage root transfer, failure
recording and Omarchy overlay work. Keep the Macintosh HD path and known restore
artifact independently available. Reconcile the previously unconfirmed 31AF
restoration before another physical test; this note does not reset that state.

Replace the platform layer coherently: loader, kernel, J716c DT, kernel
configuration, modules and firmware handoff records. Keep 16 KiB pages, which our
earlier kernel already used. Preserve real ADT/MPIDR core identities; do not infer
base-M5 compatibility from the marketing family name or a website's SoC label.

For the Mach-O candidate, use the public executable pool and verifier throughout
the module and generated-code lifecycle. Start with direct Linux loading to avoid
adding an EFI loader relocation dependency to the first proof. A later U-Boot/GRUB
path needs its matching executable-window integration. Validate every payload,
DT, initrd and retained firmware reservation against the window before handoff.

For both routes, adopt the current CPU idle implementation only after reviewing
its exact platform prerequisites. The direct route's power-management motivation
is not evidence of working suspend-to-RAM on this machine. Keep ordinary idle,
suspend-to-idle, deep suspend, CPU hotplug and reboot as separate qualification
items. Existing `idle=nop` was a bring-up restriction, not a power-efficiency goal.

## GPU and device evidence boundaries

[J716c GPU/internal-panel PR #1276](https://github.com/aurora-silicon/linux/pull/1276)
merged on **November 12** as `c31d5805ae72283319538a282fc88080706801ff`;
head `8e41d777dc2140dd17d5528cba4c5104f34ad671`. It describes a matching
loader/DT/GPU handoff and a reported Hyprland panel test, plus a CLPC connection
for memory/fabric demand. It is no longer an open prerequisite. The source and
the tested combinations must still be traced before selecting our GPU stack.

The [device catalogue](https://aurorasilicon.org/devices/) source at
`aurora-silicon.github.io@4acd0eed38d1c248ed070f4f79d873b1d8bc6896`
predates that merge. Several J716c cells explicitly rely on expected Pro parity,
including input/backlight, HDMI, battery/fans and Bluetooth. These are not
independent board tests. The catalogue still marks the installer untested for
J716c. No native performance parity follows from a working desktop or partial
graphics conformance sample.

## Bounded offline qualification before a restart

1. **Close provenance gaps.** Retain the exact public source pins, licenses and
   toolchain. Obtain or independently reproduce the CDC diff, padded-object
   recipe, kernel configuration and artifact hashes behind the J716c report.
   Do not substitute an unreviewed installer or an arbitrary branch head.
2. **Audit the handoff.** Compare direct entry with our old resident assumptions.
   Check final segment ordering, entry/vector selection, padding bounds, CTXR
   geometry, release addresses and all reserved-memory overlaps. Derive the
   expected properties from the actual candidate; do not override a private
   selector or weaken a validator to force acceptance.
3. **Build in isolation.** Build pinned loader variants, the exact J716c DT,
   kernel, modules and diagnostic initramfs in the existing Linux VM. Keep
   stage-specific flags and outputs separate. Rebuild Omarchy with the matching
   modules only after the diagnostic set compiles and validates.
4. **Exercise failure cases.** Check undersized padding, out-of-window executable
   pages, oversized kernel/module allocations, missing CPU release addresses,
   overlapping initrd/firmware ranges and wrong-board metadata. Exercise the
   existing transfer's interruption/hash refusals only if its code changes.
   VM results prove the model and generic code, not Apple CTXR enforcement.
5. **Prepare one measured RAM campaign.** A first physical candidate should
   distinguish loader entry, every secondary's arrival, Linux online CPUs and
   concurrent per-core work. Record timings, topology, timers/IPIs, a bounded
   memory benchmark, USB/N1/SSH, and only read-only storage observations. Use a
   minimal display first; add GPU work only when its separate prerequisites and
   recovery are qualified. A console saying 18 CPUs is one measurement, not the
   complete performance result.
6. **Present the concrete gate.** Supply M1 with hashes, build/VM evidence,
   expected checkpoints, collection script, stop conditions and the exact
   restoration path. Separately explain any required lab/firmware operation and
   its machine-wide effect. Request authorization only for that reviewed
   physical sequence. No restart is ready merely because this design exists.

## Publication and attribution

### First bounded offline result

The parent ran the exact public wrapper in the existing isolated Linux VM,
checking its source hash before import. Three non-executable synthetic inputs
passed structural/roundtrip/entry checks, and two invalid inputs refused.
The VM had only loopback, shut down normally, and both workspace locks were
released. A separate read-only `kmutil inspect` on macOS 26.6.2 returned exit 0
and derived `kcbz=0` for the small synthetic fixture. This validates parser
behavior, not native acceptance, actual firmware entry or the padded window.
No Apple firmware ran in the experiment, and no actual boot candidate was built.

Original harness:
[`093-mach-o-route-format`](../virtualization/jobs/093-mach-o-route-format/README.md).
Sanitized results:
[`m5-route-2026-11-12-format-check.json`](m5-route-2026-11-12-format-check.json).

### Source provenance

This is an original synthesis of public implementation and operator reports.
It contains no extracted Apple instructions, decompiler output, personalized
boot objects, credentials or private hardware identifiers. Preserve the upstream
file-specific MIT/GPL notices when integrating Aura and the Linux/Mesa code;
publication in this downstream does not imply upstream acceptance. No source
from this review has been submitted to another project, and no Discord message
has been sent.

**Current outcome:** a specific, source-backed route worth offline integration;
no new native image, installation, firmware update or physical test is qualified
by this document. Parent-session offline experiments are recorded separately.
