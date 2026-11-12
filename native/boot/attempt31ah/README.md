# 31AH: direct Aura/kernel reproduction, offline review

**Offline only. No installation, firmware/security change or restart is ready.**
The public November 11 J716c report gives us a concrete software route to test;
it does not establish that this machine must wait for Apple.

## What was reproduced

The source pair is Aura `bd9f3e8273dc79ae9095c19c2c4f32218446ad4e` and
Linux `dc8f6f77934b471a13c91e7780e2d91ebc904b3d`, from the latest operator comment in
[the J716c discussion](https://github.com/aurora-silicon/linux/discussions/142).
The target is **Mac17,6 / J716c / T6050**, preserving all eighteen physical CPU
nodes and their MPIDRs. The kernel uses sixteen-KiB pages and the upstream
CTXR execution-window support. Original padding extends the ordinary Aura
Mach-O image for a **128 MiB code pool**, preserving the executable payload.
This is direct entry, distinct from the old 31AF resident-monitor ABI.

Two separately labelled Aura builds exist: unchanged upstream baseline and an
original optional J716c USB2 scheduling delta. That delta is **not** the external
operator's unpublished CDC patch and is not a demonstrated USB fix. Neither
build is a configured ESP/chainloading installation. They are alternatives.

The operator did not publish an exact kernel configuration, toolchain, complete
USB patch or artifact hashes. Our configuration is a **reconstructed RAM
diagnostic profile**, not a bit-identical reproduction of that person's build.
The source archives, build tools, configuration and final artifact hashes are
recorded separately in [manifest.json](manifest.json) and
[offline-validation.json](offline-validation.json).

## Evidence and original implementation

The completed full kernel link produces Image, modules and J716c DT. Its Image
and declared memory footprint fit the static 128 MiB pool; runtime allocation
and CTXR enforcement remain unqualified. SEP is disabled because its default
public driver contains persistent provisioning operations. Storage drivers are
modules excluded from the diagnostic RAM root. No diagnostic block device is
opened or mounted. The exported DT removes the public source's per-unit DROM
and disables SEP, ISP and unqualified USB4 nodes.

The original static diagnostic collector inventories CPU IDs, MIDRs/MPIDRs and
capacity, performs bounded concurrent work pinned to every permitted CPU,
checks compute overlap and timer observations, and verifies a small RAM buffer.
It reads frequency state without requesting changes. A shared monotonic join
deadline and a deliberate stall control cover userspace timeout handling. A
kernel-wide hang still needs an external stop. Compact results repeat on the
console every five seconds for camera capture. These are correctness and
liveness checks, **not a memory-bandwidth or macOS-parity benchmark**.

The actual new Image and local RAM image passed a diskless, networkless
four-vCPU ARM64 VM control with sixty seconds of liveness. This does not test
Aura, physical M5 secondary startup, native CTXR enforcement, N1, GPU or NVMe.
The VM was externally stopped at its declared bound; it did not reboot or
request a shutdown itself.

Public original source is under
[kernel/experiments/direct31ah](../../../kernel/experiments/direct31ah/), with
[build job094](../../../virtualization/jobs/094-direct31ah-aura/README.md) and
[build job095](../../../virtualization/jobs/095-direct31ah-kernel/README.md).
The [source inventory](source-sha256.txt) binds this handoff independently of
historic frozen attempts. Mutable shared status logs are excluded from that
inventory; the reviewed Git commit identifies their snapshot. Existing REA findings about collection/protection
selection informed the ABI distinction; **no new Apple decompilation was needed
or claimed for this public-source reproduction**. Old 25G83 findings cannot
qualify the later firmware reported by the external operator.

## Artifact delivery and source availability

The compiled review tar remains under ignored `build/direct31ah-package/` for
transfer between the user's own computers. It is **not a public binary Release**.
Git contains source, hashes, sanitized evidence and instructions. The tar has
two padded Aura alternatives, kernel Image/configuration, sanitized diagnostic
DT, an inspect-only modules archive and Aura/dependency notices. The strict
reader checks all bytes without extracting, executing or opening USB.

The diagnostic glibc executable/initramfs and unmodified upstream DT are not
in that tar. Public distribution of the static diagnostic binary awaits its
libc corresponding-source/relink closure. That does not invalidate its local
build or VM result. Public Aura/kernel binary redistribution also needs its
full corresponding-source delivery; this review does not claim that release
step is complete. Exact upstream archive origins and hashes are in the manifest.
The saved Rust dependency-source archive contains compiled-component sources,
not a reusable Cargo cache: optional locked Git dependencies must be fetched
before the recipe's networkless `--locked --offline` compilation.

## Conditions before a native proposal

1. M1 independently verifies this exact source inventory and review tar.
2. Qualify the firmware/boot-object pairing: local November 12 version reads
   found 26.6.2/25G83; the external report uses 27.2.1/26B131 and mBoot20457.41.3.
   A version difference is a qualification gap, not proof that an update is
   mandatory. Do not update anything in response to this document.
3. Resolve or explicitly bound the control path. The pinned Linux T6050 DWC3
   driver is host-only; a Linux-to-M1 USB gadget console is not reproduced.
   An M1 camera is a useful independent screen record, not a replacement for
   kernel logs or proof of unseen CPU instructions.
4. Review a lab-only installation **and complete restoration** design. The
   direct Mach-O route's Kernel CTRR requirements differ from the old raw
   boot021 path. Replacing bytes alone is not a qualified rollback. Old 31AF
   rollback and Macintosh HD default restoration remain unconfirmed.
5. Obtain separate authorization for the concrete sequence. Original
   Macintosh HD must remain Full Security. No generic upstream installer or
   Recovery block is supplied here.

M1's immediate task is [the offline checklist](../../../tools/m1n1-client/attempt31ah-instructions.md).
Physical entry, all eighteen cores, native USB/N1/storage/GPU and performance
remain **NOT RUN** for 31AH. Do not restart either computer for this review.
