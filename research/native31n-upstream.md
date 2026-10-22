# 31N: upstream and independent T6050 startup evidence

2026-10-22. Read-only public-source investigation after consumed 31M. No
downloaded code was executed, no author was contacted, and no target, installed
image, macOS setting or third-party checkout was changed. The native outcome is
in [the M1 result](../native/boot/attempt31m-2026-10-22-result.md): CPU0 controls
passed, both starts were acknowledged, and every CPU1 publication channel
remained negative. CPU1 execution is still unverified.

## Result

There is a reported working all-core M5 implementation on **T8142/J813** in an
independent fork. Its source contains useful subsequent SMP work, but its
specific reset relay does **not** explain this project's raw boot021 layout.
Two independent **T6050** investigations report a similar first-entry failure;
neither provides a demonstrated all-core fix. Their strongest new research
lead is the conditional firmware command-table path before the familiar PMGR
start writes. A separate engineering variable is our long, instrumented gap
between those two writes.

Public hardware reports are attributed observations by their authors. They
were not independently reproduced on this machine. Public repository claims,
compilation, and native execution evidence are distinguished below.

## Current Asahi source and branches

The public API still identifies upstream main as
`7cde7d1a784d851ebfee5579fa363c38b14150c0`, dated 2026-10-19. It is 32 commits
ahead of pinned `57a9339ffd1876e78297b17d34dece8cff8fa1ba`. The
[comparison](https://github.com/AsahiLinux/m1n1/compare/57a9339ffd1876e78297b17d34dece8cff8fa1ba...7cde7d1a784d851ebfee5579fa363c38b14150c0)
changes neither `src/smp.c`, `src/start.S` nor `src/chickens.c`. The listed open
pull requests expose no identified T6050 first-entry fix. This is a bounded
search, not a claim that no unpublished work exists.

[PR610](https://github.com/AsahiLinux/m1n1/pull/610) remains direct corroboration:
the original T6050 contributor reported powered secondaries without loader
execution on two firmware versions. M-core and P-core identities must remain
distinct; this machine has twelve M-type Performance and six P-type Super
cores. CPU1 is in CPU0's already active M cluster.

Two public contributor branches were also inspected:

- [`find-regs-smp`, `781752e775e1bb530e3989de7abe425d6555bd85`](https://github.com/yuyuyureka/m1n1/commit/781752e775e1bb530e3989de7abe425d6555bd85)
  adds register discovery on secondaries that are already alive. It is not a
  startup fix; indiscriminate register probing is not adopted.
- [`smp-debug`, `60cbe066dc7c82b855bf98e3f916f192983c46e3`](https://github.com/yuyuyureka/m1n1/commit/60cbe066dc7c82b855bf98e3f916f192983c46e3)
  invokes ordinary secondary startup during boot. It adds no missing release
  operation and supplies no T6050 success result.

## Working T8142 report: useful but not the same layout

[Aurora m1n1 PR12](https://github.com/aurora-silicon/m1n1/pull/12), head
`ab292d534f40d4a6477f1370a0752a248b053fa4`, merge
`757abb9d224ce032337e341ad32ca9cefed164f1`, reports expected identities and
twenty computations on each of nine secondaries. Its ten-core J813 uses a
six-E/four-P topology and boots on CPU6. The source adds dense global masks,
prepublished affinity-correct reset stacks, WFE/SEV dispatch and quiet secondary
initialization. A bounded RAM branch redirects a resident reset address within
the replacement image's consumed Mach-O header to its vector table. It refuses
addresses outside that header and checks the Mach-O magic at the image base.

**Applicability:** boot021 is a raw image with its vectors at offset zero,
cold entry at `0x800`, and no such preceding header. Existing live text checks
and mirror classification bind the observed reset address to that base. The
31L/31M vector prefix already occupies offset zero. Adding another header relay
would not remove a demonstrated mismatch here. The public validator is useful
future acceptance criteria, not evidence that this machine's CPU1 executes.

The stacked [PR10](https://github.com/aurora-silicon/m1n1/pull/10), head
`014cadf60e2c8ba3c4120ee5cec8d1eae91647ba`, preserves cold T8142 reset registers
and publishes copied code with PoC cleaning and barriers. The project's current
entry publications already use PoC cleaning. No chainload or installed-image
replacement follows from this comparison.

The companion [Linux PR160](https://github.com/aurora-silicon/linux/pull/160),
`f1d29b8afd4e364f730f666d7c247276c8ba50ca`, reports ten online J813 CPUs,
advancing per-core timer interrupts and ten pinned hash jobs after adding the
measured T8142 MIDRs to register-preserving idle. That is a **post-entry** WFI
requirement. T6050 MIDRs, idle behavior and both core types need their own
qualification; silently extending a T8142 match is not justified.

## Same-SoC evidence and firmware lead

The closed, unmerged [Asahi PR631](https://github.com/AsahiLinux/m1n1/pull/631)
was followed by public J716c research at
[`qspqww/m1n1`, `90f3be1d34a5af87e04fffead4f3cdb44d8fd046`](https://github.com/qspqww/m1n1/blob/90f3be1d34a5af87e04fffead4f3cdb44d8fd046/findings.md).
The author reports matching CPU0/CPU1 reset-address fields, no earliest marker
after a PoC copy fix, and a split-write experiment: no sampled implementation
change during a 24-microsecond interval after the first start write, then two
CPU1-specific changes within roughly five microseconds of the second. CPU0
and an unstarted peer stayed stable. This corroborates a transition after the
second write, not instruction execution or semantics of the opaque bits. The
reported direct-installed-image comparison remained a proposal. Their register
sampling and proposed installation are not adopted as permissions here.

[Sowyu's T6050/J714s investigation](https://github.com/Sowyu/m5-azahi/blob/82c90a5fd0b841d3acec4f558f9424b2cefec8bf/docs/audit-2026-09-25/smp.md),
pin `82c90a5fd0b841d3acec4f558f9424b2cefec8bf`, likewise establishes only CPU0.
Its firmware-table analysis provides concrete **static** leads in the older
J714s `mBoot-18000.161.9` Stage2:

| Raw Stage2 offset | Reported role to locate independently in our build |
|---|---|
| `0x1c5004` | Framed iBootData parser |
| `0x1c8de0` | Read-and-restore operation for per-core implementation windows |
| `0x1c63b4` | 64-bit read helper |
| `0x1c6208` | Queued register-write path |
| `0x1ce28c` | Command-buffer compiler |

The `MGP_CE0_ACC{0,1,2}_POWER_UP` and `MPMGR_D2A_IBOOT2B` sequences contain
conditional reset-address restoration and start operations. They are not flat
lists of writes. The older decoded Stage2 hash is
`fa596237671bb33aa28c12dfa3f5196595f6bb4be6a3582d1f659ddedfd0c77c`;
its data hash is
`8eee86e205591907b4edfeda6ebdcf29ec9325b4bc4b4c726fe69d8d52871352`.
These offsets and operation numbers must **not** be applied directly to this
project's J716c `18000.161.10` image. Locate and validate its own dispatcher,
record boundaries, guards, descriptor mapping and callers first. No firmware
replay or additional MMIO follows from the public analysis.

## Sources that do not supply a fix

- [PR731](https://github.com/AsahiLinux/m1n1/pull/731), merged
  `25b1d89ca50be848b136ce771ce7167244852a91`, installs software shadows for
  certain M4 CPU-power accesses in an emulated SPTM guest. It does not perform
  the real accesses or demonstrate T6050 reset initialization. The prior
  [31M source review](native31m-upstream.md) remains applicable.
- [PR613](https://github.com/AsahiLinux/m1n1/pull/613), merged
  `954f80c62a44badbb4e6eefb3267cb693876ac5a`, concerns stores and stack visibility
  before secondary MMU enable. That requires an executing secondary and does
  not explain the missing first publication by itself.
- [antiapplefox/m5-linux](https://github.com/antiapplefox/m5-linux) explicitly
  reports no hardware bring-up and no working shim/MMU port. Its static SPTM
  conclusions are research leads, not a demonstrated prerequisite for our raw
  loader, which already runs Linux on CPU0.
- [gsmll/m5-m1n1-hypervisor](https://github.com/gsmll/m5-m1n1-hypervisor/blob/main/proxyclient/api.py)
  exposes an interface scaffold whose connection and memory methods raise
  `NotImplementedError`. It is not an available secondary-start implementation.

## Ranked engineering decisions

1. **Continue matching-firmware REA at the command-table/descriptor boundary.**
   Establish exactly which pre-entry conditions apply to this raw-image path.
   Keep lifecycle and branch conditions attached to every finding. Only
   independently established behavior can justify a new startup operation.
2. **Remove host instrumentation from between the known start writes.** The
   inherited `native/boot/smp31g.py` run loop performs multiple proxy reads,
   sampling and journaling between the two retained writes. An original fixed
   CPU0 leaf can issue exactly those two addresses/values in order after all
   preflight checks, with bounded observation afterward. This is an explicit
   timing hypothesis, not a diagnosed cause. The pair must be one consumed
   operation: no retry after an uncertain reply, and no inference that both
   stores completed solely from host dispatch. Offline tests must check exact
   instruction order, address/value bounds, publication and fault handling.
3. **Preserve the subsequent all-core acceptance plan.** Once CPU1 execution
   is established, test private stacks, identity, repeated computations,
   memory visibility, timers and IPIs before other clusters; then qualify all
   twelve Performance and six Super cores and the Linux idle paths. Frequency,
   scheduler placement, throughput and energy measurements remain required.

Repeating 31M or transplanting a differently shaped T8142 image is not the next
step. The currently observed state alone does not justify arbitrary register
scans, reset-address changes, firmware substitution or claiming SMP success.
