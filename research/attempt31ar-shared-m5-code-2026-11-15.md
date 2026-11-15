# Shared M5 implementation leads for the J716c

Research date: 2026-11-15. Public source was read as data through GitHub; no
third-party recipe, installer, kernel, bootloader or hook was executed. No
message was posted. This review changes no host setting or firmware and makes
no native compatibility or performance claim.

Separately, the root agent's bounded read-only host observations on this date
confirmed `sw_vers` ProductVersion **26.6.2**, Build **25G83**. Its metadata-only
APFS shape check observed three containers: each had `APFSContainerUUID` as a
valid UUID string; none had `ContainerUUID`. No identifier values were returned
or persisted. The first sandboxed read refused with exit 1; the same whitelisted
read outside that sandbox succeeded. This qualifies the field name for the
controller's private stable-container commitment, not a mount or write path.
No policy, mount or setting change was made by these observations.

## Finding and decision

**Confirmed, source:** the user's [issue 12](https://github.com/betizzel/omarchy-m5/issues/12)
is directly useful. It connects current T6050 kernel, Aura, GPU, networking and
desktop integration work, including contributors using M5 Max boards. Its
published image is for **J714s, the 14-inch M5 Pro**, however. The README
explicitly excludes Max and 16-inch models from installer admission. Our target
is **Mac17,6 / J716c / T6050**, with eighteen cores, not that fifteen-core board.

Reuse qualified source components and their exact firmware contracts. Do not
run this image's partitioning installer against the existing iLinux lab, replace
our board tree with J714s, or infer Mac17,6 compatibility from the J714s results.
The current unchanged candidate remains an entry/SMP diagnostic, not a complete
reproduction of this newer desktop stack. After controlled entry, the next
kernel revision should incorporate current J716c/T6050 support rather than
reimplementing already published drivers.

## Exact source observations

The repository revision read was
[`968a59612a5f0f76cf7854b8623fab0ef2d0ba6e`](https://github.com/betizzel/omarchy-m5/commit/968a59612a5f0f76cf7854b8623fab0ef2d0ba6e).
The issue and README are owner reports, not measurements independently repeated
here. Their reported J714s release 6 has fifteen CPUs at EL2, accelerated
graphics, Wi-Fi, keyboard/trackpad and an internal 120 Hz panel on Apple's 27.2
firmware. Some display/audio observations are from release 5, and cameras/ANE
being enumerated do not establish working capture/inference. Deep sleep remains
unavailable. These qualifications are part of the report, not omissions to fill
with assumptions.

The pinned recipes are:

| Component | Source pin | Inspected recipe |
| --- | --- | --- |
| Aura | `22b71758dfd048f6a874073db55fbe6bd1d17f44` plus seven local patches | [m1n1-aurora-j714s/PKGBUILD](https://github.com/betizzel/omarchy-m5/blob/968a59612a5f0f76cf7854b8623fab0ef2d0ba6e/installer/recipes/m1n1-aurora-j714s/PKGBUILD) |
| Linux | `a5ebec5fd092327b16ff26366cb3840448285578` plus local series through 0032 | [linux-aurora-j714s/PKGBUILD](https://github.com/betizzel/omarchy-m5/blob/968a59612a5f0f76cf7854b8623fab0ef2d0ba6e/installer/recipes/linux-aurora-j714s/PKGBUILD) |

GitHub's compare API reports the Aura pin is **195 commits ahead, zero behind**
our candidate's `bd9f3e8273dc79ae9095c19c2c4f32218446ad4e`. The Linux pin is
**1,156 ahead, zero behind** `dc8f6f77934b471a13c91e7780e2d91ebc904b3d`. Thus
these are later descendants, not unrelated replacements. The compare response's
commit list can be truncated; these counts are graph summaries, not a claim that
every intermediate commit was audited.

Sources: [Aura comparison](https://github.com/aurora-silicon/aura/compare/bd9f3e8273dc79ae9095c19c2c4f32218446ad4e...22b71758dfd048f6a874073db55fbe6bd1d17f44),
[Linux comparison](https://github.com/aurora-silicon/linux/compare/dc8f6f77934b471a13c91e7780e2d91ebc904b3d...a5ebec5fd092327b16ff26366cb3840448285578).

## Components worth porting or retaining

| Area | Concrete public implementation | Relevance and required qualification |
| --- | --- | --- |
| CPU interrupt state | Aura [`170e23f04a723f3635908c6a16e74f1fe9835d40`](https://github.com/aurora-silicon/aura/commit/170e23f04a723f3635908c6a16e74f1fe9835d40); [chickens.c at recipe pin](https://github.com/aurora-silicon/aura/blob/22b71758dfd048f6a874073db55fbe6bd1d17f44/src/chickens.c) | Introduces Sotra feature data and SIQ routing for every M5 Pro/Max/Ultra core. The source describes absent per-core setup as leaving only the boot CPU receiving AIC IRQs. This is interrupt acceptance after startup, not proof that our original first-fetch barrier was the same bug. Include in a newly qualified loader and test per-CPU interrupts/timers as well as concurrent arithmetic. |
| Executable window | Same Aura recipe calls `macho_boot_object.py --execute-window`; it builds separate Stage 1 and `ESP_STAGE2=1` | Same no-SPTM Mach-O family as our chosen route. Its Stage 1 carries ESP configuration and loads Stage 2; our candidate embeds a bounded RAM diagnostic. Preserve each route's loader/kernel executable-window and size contracts rather than interchanging objects. |
| MTE and EL2 | Aura's later MTE tag-storage reserve/fallback changes; Linux recipe includes T6050 EL2 errata #1724 | Required integration review when updating the pair. Treat architecture capabilities and reservation as a matched boot-chain property; do not enable a feature merely because the CPU advertises it. |
| GPU/display | [27.2/27.3 InitData patch](https://github.com/betizzel/omarchy-m5/blob/968a59612a5f0f76cf7854b8623fab0ef2d0ba6e/patches/j714s-27.2/linux/0001-drm-asahi-M5-InitData-for-the-macOS-27.2-and-27.3-fi.patch), [M5 Max firmware row](https://github.com/betizzel/omarchy-m5/blob/968a59612a5f0f76cf7854b8623fab0ef2d0ba6e/patches/j714s-27.2/aura/0003-kboot-T6050-also-admit-the-M5-Max-s-27.3-GPU-build-a.patch) | Real firmware-specific graph/layout and identity handling. Aura's Max row comes from #172, rather than pretending Pro and Max loaded bytes are identical. Keep exact identity refusals. A source label G17S/G17C is insufficient to choose the loaded firmware build or the board graph. |
| GPU latency | Kernel recipe includes merged #1844, originating in the J716c track: T6050 GPU mailbox receive by interrupt; later G17 lifetime/error patches 0029–0031 | Particularly relevant to the user's seconds-long UI delays and efficiency goal. Test accelerated rendering, input-to-frame latency, task switching and idle power. A one-core software-rendered comparison cannot establish these properties. |
| J716c board support | [t6050-j716c.dts at kernel pin](https://github.com/aurora-silicon/linux/blob/a5ebec5fd092327b16ff26366cb3840448285578/arch/arm64/boot/dts/apple/t6050-j716c.dts) | Retains J716c compatibility, Max common data, N1 aliases and J716c-specific ISP/GPU-panel/display/USB4 includes. Start from this board, not J714s's physical pin/panel/port maps. Runtime firmware and ADT observations still must match. |
| Wi-Fi/PCIe/storage | Aura [`4d6c4431c4459d6d95210684e9ef639b7b8e65d0`](https://github.com/aurora-silicon/aura/commit/4d6c4431c4459d6d95210684e9ef639b7b8e65d0), merged #203 | The storage guard previously rejected legitimate auto-PM state changes and could abort N1 port bring-up. The narrow patch admits PS_AUTO changes only while AUTO_ENABLE is set before and after; target/other changes and ANS/NVMe guards remain. This is a credible shared T6050 fix, not permission to remove storage guards or write macOS volumes. |
| CPU thermals | [0032 fast-die effort](https://github.com/betizzel/omarchy-m5/blob/968a59612a5f0f76cf7854b8623fab0ef2d0ba6e/patches/j714s-27.2/linux/0032-arm64-dts-apple-t6050-j714s-Enforce-the-PMP-s-fast-d.patch) | Corrects an important assumption: firmware retains voltage/PLL control but does not necessarily lower the OS-requested performance state. The patch wires PMP effort into cpufreq limits for J714s only; it explicitly says other T6050 boards are unqualified. Before sustained Max loads, qualify the Max ADT cluster/effort map, PMP report readiness, fallback limits, measured clock and hotspot/fans. Do not copy J714s lane assignments blindly. |
| Update reliability | [j714s-boot-guard](https://github.com/betizzel/omarchy-m5/blob/968a59612a5f0f76cf7854b8623fab0ef2d0ba6e/installer/recipes/omarchy-aurora-firmware/j714s-boot-guard) | Concrete protection against Omarchy channel changes overwriting a kernel/boot package pin. Useful after persistent Linux exists. This implementation recognizes version-name patterns and J714s package identity; adapt to our exact signed/pinned artifact set rather than treating matching version text as complete provenance. |

### Does the missing SIQ change invalidate the current diagnostic?

**Inferred from the exact source paths: no known deterministic failure follows.**
The old Aura's Sotra feature set retains fast IPIs but does not write SIQ_CFG.
The later commit describes device IRQs arriving at CPU 0 and completion work
being sent to another CPU by IPI. In the exact older kernel,
[`irq-apple-aic.c`](https://github.com/aurora-silicon/linux/blob/dc8f6f77934b471a13c91e7780e2d91ebc904b3d/drivers/irqchip/irq-apple-aic.c)
handles fast IPIs and architectural timers as per-CPU **FIQ** sources, and the
timer node in
[`t6050-base.dtsi`](https://github.com/aurora-silicon/linux/blob/dc8f6f77934b471a13c91e7780e2d91ebc904b3d/arch/arm64/boot/dts/apple/t6050-base.dtsi)
uses `AIC_FIQ`. Our PID 1 performs pinned arithmetic, checksum, overlap and 1 ms
timer sleeps; it does not require device IRQ distribution across all CPUs.

Therefore preserve the unchanged candidate for the first admitted entry and
concurrent-execution test, record IRQ balance as unqualified, and include the
new SIQ setup in a separately reviewed performance-oriented loader revision.
Do not call an eighteen-worker pass proof of macOS-like I/O interrupt routing.
This is a source-based expectation; only native observations settle execution.

## Firmware and board boundaries

Our retained [31AH qualification](../native/boot/attempt31ah/offline-validation.json)
records local original/lab **26.6.2/25G83**, whereas the matching external J716c
report uses **27.2.1/26B131 and mBoot20457.41.3**. This review has not re-read or
updated the host firmware. 31AP's successful Recovery admission does not resolve
that handoff compatibility question. The new repository's J714s stack targets
**27.2/26B123** and has explicit additional **27.3/26C5035r** rows. A running
desktop version, selected lab boot-object format and global Boot ROM number are
different observations. None substitutes for the selected boot chain's actual
firmware component identities.

The current [Aura Mach-O guide](https://github.com/aurora-silicon/aura/blob/22b71758dfd048f6a874073db55fbe6bd1d17f44/docs/macho-boot-object.md)
does explicitly report that `kmutil` from **26.6.2/25G83** parses the object and
derives zero `kcbz`. Its hardware status also records all fourteen CPUs on a
**T6040 J616s** using system iBoot 20457.1.29 and OS iBoot 18000.161.10. That
demonstrates a useful older-train precedent, not a T6050 result. No explicit
T6050/25G83 exclusion was found in this guide. A first fully admitted enrollment,
readback and visible-entry check is therefore a meaningful discriminator; neither
the newer repository nor this precedent qualifies our selected lab firmware in
advance. Capture the exact observed stopping stage and retain rollback.

This evidence does **not** support a conclusion that we must wait for Apple for
all-core Linux: multiple public software stacks describe an implemented path,
including our exact J716c source lineage. It also does not guarantee our older
lab loader can hand over the exact current candidate. The proposed short native
window is a discriminator for entry and CPU execution; preserve this uncertainty
in its outcome instead of interpreting every blank screen as a firmware veto.

## Practical sequence

1. Finish and independently review 31AR's lab-only transaction and boot021
   restoration. Retain the current candidate identity so its admission/entry
   experiment stays interpretable. No new installer or firmware change here.
2. Record actual entry, selected component train, executable-window property,
   CPU identities and concurrent checksums/timers. Collect finite screen output;
   never claim success from the Apple logo or CPU count alone.
3. Build a separate next candidate from a reviewed current Aura/Linux pair plus
   the J716c tree. Inventory exact changes from the preserved pair. Select GPU
   and display firmware rows only when loaded bytes/ADT prove them. Qualify
   CPU/PMP fallback and clock reporting before longer load tests.
4. Bring up GPU desktop, N1 networking and read-only NVMe discovery using shared
   code; measure application/input latency and CPU/memory behavior against the
   same Mac in comparable normal power mode. Persistent Linux storage and any
   macOS data access are separate reviewed work; enumeration is not safe write
   compatibility with encrypted macOS APFS.
5. Qualify power, suspend, audio/camera/ANE and updates separately. Device nodes,
   compilation and a desktop photograph do not establish macOS-level quality.

No firmware replacement, volume creation, boot enrollment, live mount, policy
change, native run or external communication was performed in this research.
