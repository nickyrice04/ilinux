# 31AH independent M1 offline review — 2026-11-13

**OFFLINE_REVIEW_PASS_NATIVE_HOLD.** Reviewed Git
`ba3687c0504e68971756ecb342e6095410e5c98f`. No actionable integrity or static
layout failure was found. This is not readiness for a physical boot.

## Fresh M1 evidence

The 41-entry source inventory passes; inventory SHA-256:
`67b9d70018498cb4bacbbe05081e6a233b838af89d8c722983f804f2c14dc3a5`.
The actual local-user archive is 34,099,303 bytes, SHA-256:
`0abee654af377a8c299b57cc4709da1f3a9f7ae340a024e79fac286f81bf3298`.
The strict reader verifies all 64 members, 368,421,402 expanded bytes and the
complete gzip/USTAR stream. No extraction or downloaded executable execution.

| Fresh host-safe suite | Methods | Result |
|---|---:|---|
| Strict intake reader | 46 | PASS |
| Camera/timeline helper | 24 | PASS |
| Kernel/configuration/DT tooling | 26 | PASS |
| Generic-VM receipt validator | 18 | PASS |
| Total | 114 | PASS |

Separately inspected actual artifact bytes in memory after archive verification:

* Both 153,190,400-byte Aura alternatives pass the narrow nested Mach-O
  inspector. Six expected segments, entry offset 67,584 and code offset 65,536
  agree. Each preserved raw slot matches its archived digest; inserted padding
  is all zero. Unpadded original images were not independently available, so a
  full original-image reconstruction is not claimed.
* Actual Linux Image is 43,694,592 bytes, with 44,498,944-byte declared memory,
  16 KiB page header and static fit in the 128 MiB execution pool. This does not
  qualify runtime allocation or native executable confinement.
* All 8,833 parsed config symbols pass the reconstructed diagnostic policy;
  NR_CPUS=64, SMP/CTXR enabled, SEP disabled, NVMe/SART modules. This is not the
  external operator's exact configuration. Module archive is hashed only,
  not unpacked or loaded; exclusion from the private root is reviewed M5 evidence.
* Actual sanitized DT has eighteen distinct expected MPIDRs, M/M/P clusters of
  six, spin-table release declarations, no DROM properties and nine matching
  SEP/ISP/USB4 nodes disabled. These are static nodes, not online CPU evidence;
  runtime memory/framebuffer/release/CTXR fields still require Aura fixups.
* All eleven transferred kernel recipe/helper source bindings match this Git
  checkout. Baseline and original USB2-delta alternatives stay separately pinned.

Baseline Aura digest:
`f73b8feea8f05a67408fb1a7e86b679ce33e9f2ff9ae97746549a126bf07cace`.
Original USB2 alternative:
`b45375b3bedeca66354b858d909c5b05dca7acd6bb76002eea824b8f528ac53f`.
Linux Image:
`c01483f230aa64013b395291f8a5b8e38ed6c467b61e8a141c621938fda3a56f`.

## Reviewed evidence and limits

The [public J716c operator report](https://github.com/aurora-silicon/linux/discussions/142)
names Aura `bd9f3e8273dc79ae9095c19c2c4f32218446ad4e` and Linux
`dc8f6f77934b471a13c91e7780e2d91ebc904b3d`, matching this handoff.
It reports eighteen CPUs, N1/SSH and NVMe enumeration on macOS 27.2.1/26B131,
mBoot 20457.41.3, with an unpublished local USB2 patch. Treat these as external
operator observations, not measurements on this user's machine or a complete
reproducible artifact/configuration closure.

M5's padding24/six C assertions, full builds, fourteen-property Apple read-only
inspection (both kcbz=0) and four-vCPU diskless/no-NIC VM result are reviewed
records, not rerun on M1. The VM's actual new kernel/private root demonstrates
workers, RAM checksum and 60.498751570-second liveness in a generic environment;
it executes neither Aura nor Apple firmware. No native CTXR/SMP/performance proof.
The diagnostic executable/initramfs is absent from the transferred tar. Its M5
pins and source/relink plan are not a delivered M1 runtime package. Public binary
redistribution remains incomplete; private local builds/VM evidence keep their scope.

Read-only capability inventory lists an M1 built-in camera and an existing
QuickTime recorder. Neither was opened; permissions, audio-off capability,
framing/readability, recording and capture performance remain NOT RUN/Unknown.
A camera can corroborate screen checkpoints but cannot replace USB control or
independently survive an M1 failure.

## Decision and next work

**Continue the direct Aura/CTXR route offline; do not restart either Mac yet.**
This is a concrete next engineering route, not proof that a firmware update is
mandatory or that the old resident observer can be reused unchanged.

1. Reconcile the unfinished 31AF restoration. Current evidence confirms macOS
   return but not exact boot021 rollback or Macintosh HD default. Human
   confirmation was requested; no answer received at this report's publication.
   Do not infer completion from an older attempt's successful restoration.
2. M5 qualifies the local 26.6.2/25G83 pairing against the external 26B131 route
   and proposes the smallest justified boot environment. Do not update firmware
   or macOS on the strength of a version difference alone.
3. M5 selects one exact Aura alternative and publishes a bounded transfer/control
   design plus exact diagnostic RAM root binding. The original downstream USB2
   scheduling delta is not the reporter's patch or a proven USB fix. Pinned
   Linux T6050 DWC3 is host-only; the existing Linux-to-M1 gadget route is not
   reproduced. Camera-only observation needs an explicit bounded failure/return
   plan and must not silently imply remote control.
4. M5 supplies the complete lab-only install/observation/restore plan, including
   the direct Mach-O Kernel CTRR requirements and recovery to the raw boot021
   policy/object state. Byte replacement alone is not a qualified restoration.
   Preserve original Macintosh HD Full Security; no additional volume changes.
5. After independent review and separate concrete human authorization, run one
   bounded RAM diagnostic before another Omarchy desktop/performance session:
   capture kernel entry/PID1, actual online CPU set, per-CPU concurrent work,
   RAM checksum/timers and sixty-second liveness, then restore/return/default.
   Exact deadline, stop conditions and no-retry behavior belong in that later
   approved plan. No new physical authorization is inferred here.

## Preservation and actual actions

Fast-forward pull in the original checkout refused because five unfinished
31AF status notes overlap upstream. No reset/stash/automatic resolution was
performed. Reviewed fetched main in a separate detached workspace checkout;
original notes and unrelated untracked `review-result.json` were preserved.
No producer/source repair, frozen inventory edit, consumed receipt reset,
new toolchain install or old-suite replay. Prior historical closures were not
reverified during this review and are not claimed as fresh results.

31AH native entry, USB handshake, physical CPUs, Linux runtime, N1/GPU/NVMe,
performance, camera recording, new policy checks and restoration operations:
**NOT RUN**. Old 31AF rollback/default: **UNCONFIRMED**. No reboot, installer,
Recovery page, proxy, VM start or security/firmware/volume/default change occurred.
