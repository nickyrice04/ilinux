# 31T: separating physical CPU startup from SPTM guest initialization

Checked 2026-10-23 after the independent M1 review of 31S. Public source was
read as data only. No third-party source was executed, no upstream message was
sent, and no boot, firmware, protection or hardware operation was performed.
The earlier [31S review](native31s-upstream.md) remains frozen.

## Result

**No verified T6050/M5 Max secondary-start software fix was found.** The deeper
search did find useful evidence beyond the firmware diagnosis: another exact-
SoC experiment, newer upstream hypervisor mode separation, and actual source
for the proposed XNU-compatible handoff. Inspection narrows what each can prove.

The most actionable result is an evidence correction. A primary-core register
dump does not establish secondary-core effective state. Emulated guest register
initialization does not initialize a physical CPU. An available SPTM firmware
file does not prove that the raw custom-image boot loaded it. These distinctions
matter to the now-resolved local range handlers in
[31S CPU research](native31s-firmware.md); none supplies their historical inputs
or CPU1's first executed instruction. An Apple-only remedy remains unproven.

## A newly inspected T6050 experiment: useful measurements, excessive conclusions

[betizzel/omarchy-m5](https://github.com/betizzel/omarchy-m5/tree/15cd70c1fad65322b85be4de4362cbed816a11c1)
is pinned at `15cd70c1fad65322b85be4de4362cbed816a11c1`. Its
[CPU findings](https://github.com/betizzel/omarchy-m5/blob/15cd70c1fad65322b85be4de4362cbed816a11c1/docs/smp-t6050-findings.md)
describe a **15-core J714s M5 Pro, 26.5/25F71, mBoot-18000.120.36**. This is
T6050 evidence, but not this M5 Max or its retained 25G83 boot environment.
The author reports power/state changes without an early execution marker and
an unsuccessful SPTM-guest attempt. No working CPU-start workaround is supplied.

The strongest new comparison is the actual
[register-probe source](https://github.com/betizzel/omarchy-m5/blob/264c683c9416903aa96fdae5cda7bdf5487234ec/scripts/probes/smp-ctrr-dump.py):

| Probe operation | What the source actually measures | Inference it cannot support |
|---|---|---|
| Loop over CTRR/CTXR/ACC system-register encodings | Calls `u.mrs` on the running boot CPU. There is no dispatch to a secondary in this loop. | That every physical CPU has the same effective range/protection state. |
| Loop over ADT CPU nodes | Reads each CPU's `cpu-impl-reg+0` MMIO field. | That CPU's architectural `RVBAR_EL2`, first PC, exception level, or successful instruction fetch. |
| Print lower/upper range registers and compare with the loader base | A boot-CPU address comparison under the source's chosen endpoint convention. | The effective access permissions of a secondary, or a complete range-semantics qualification. |

Consequently, the report's conclusion that the range explanation has been
eliminated is not justified by this probe. It also retains incompatible claims
about whether its raw boot loads SPTM. Its proposed SPTM registration remedy is
an interpretation, not a demonstrated active-path dependency. These limitations
are established by comparing its own source and report; no Apple disassembly or
pseudocode is reproduced here.

The source's description of guarded reads as nonfatal is also not a general
access guarantee. No probe is adopted. The previously reported T6050 debug/MMIO
access failures in [31O](native31o-upstream.md) remain relevant.

## Upstream explicitly distinguishes boot and secondary protection effects

[Asahi commit `a735ea29aed4843c301d8d9665949b30a84d25df`](https://github.com/AsahiLinux/m1n1/commit/a735ea29aed4843c301d8d9665949b30a84d25df)
adds a reserved-memory region because a CTRR instance remains enabled on
secondary cores and Linux must not allocate writable memory there. Its reported
successful scope is M4/M4 Pro, combined with avoiding inappropriate WFI/WFIT
behavior; the identified region is 48 KiB on M4/M4 Pro/A18 Pro.
[Commit `00b881435286527a0bfb0be41bece0302e697098`](https://github.com/AsahiLinux/m1n1/commit/00b881435286527a0bfb0be41bece0302e697098)
then changes the queried register bank from EL2-named to EL1-named bounds to
fix M4-family boot under the hypervisor.

This is concrete public support for keeping **bounds, register bank, CPU and
effective enforcement** separate. It is not proof that this range blocks our
CPU1, and reserving memory for Linux does not supply the missing first fetch.
The fix addresses a later allocator/write failure on its qualified targets.

The older cache failures are similarly distinguishable. In
[Asahi issue463](https://github.com/AsahiLinux/m1n1/issues/463), secondary cores
already reported startup before an EL2 exception on their own MPIDRs; the
investigation attributed the bad return address to stale same-core stack data.
[Issue480](https://github.com/AsahiLinux/m1n1/issues/480) also contains a secondary
exception report during guest initialization. The corresponding
[MMU-transition fix](https://github.com/AsahiLinux/m1n1/commit/954f80c62a44badbb4e6eefb3267cb693876ac5a)
is useful after execution reaches that transition. Neither issue demonstrates
the same failure phase as a missing earliest-entry observation on T6050.

## Current SPTM hypervisor code is useful, but does not release a physical CPU

The external report references then-unmerged work. Fresh checks show
[PR695](https://github.com/AsahiLinux/m1n1/pull/695) merged October 13 and
[PR698](https://github.com/AsahiLinux/m1n1/pull/698) merged October 15. PR698 reports
M2 testing with macOS 26.3, 26.5 and 27 beta 4, and requires accessible hardware
SPRR/GXF for its nested-virtualization route. M4-and-newer emulation is a separate
route, introduced by [PR643](https://github.com/AsahiLinux/m1n1/pull/643).

Current upstream is pinned at **`7cde7d1a784d851ebfee5579fa363c38b14150c0`**.
The inspected implementation resolves three potentially misleading claims:

| Pinned implementation | Actual behavior | Relevance |
|---|---|---|
| [`hv.c`, initialization](https://github.com/AsahiLinux/m1n1/blob/7cde7d1a784d851ebfee5579fa363c38b14150c0/src/hv/hv.c#L140-L174) | Calls host `smp_start_secondaries()` before guest setup. The `AVNCR_EL2` write is conditional on nested mode. | A failure at that write in an older combined path does not establish that today's emulation route is unusable. The host physical-start dependency remains. |
| [`hv_sprr.c`, per-CPU initialization](https://github.com/AsahiLinux/m1n1/blob/7cde7d1a784d851ebfee5579fa363c38b14150c0/src/hv/hv_sprr.c#L102-L150) | Copies CTRR/CTXR values between guest `shadow` arrays. | This is virtual state, not writes to the physical secondary's protection registers. PR695's earlier `hv_sptm_init_secondary()` has the same distinction. |
| [`hv.c`, guest secondary entry](https://github.com/AsahiLinux/m1n1/blob/7cde7d1a784d851ebfee5579fa363c38b14150c0/src/hv/hv.c#L376-L395) | Uses host `mmu_init_secondary()`, `smp_call4()` and `smp_wait()`. | Guest CPU startup presupposes a functioning host secondary. It cannot serve as the missing physical release operation. |
| [`run_guest.py`, mode selection](https://github.com/AsahiLinux/m1n1/blob/7cde7d1a784d851ebfee5579fa363c38b14150c0/proxyclient/tools/run_guest.py#L26-L44) | Exposes separate none/emulation/nested modes and checks the required SPTM/TXM argument pairing. | Source comparison must name the actual mode. This is not a command recommendation or a qualified T6050 run. |

Asahi's [Linux 7.2 progress report](https://asahilinux.org/2026/08/progress-report-7-2/)
describes successfully restoring a tracing approach by emulating SPRR/GXF. It
therefore contradicts a blanket architectural claim that SPTM makes hypervisor
research impossible. However, the current
[hypervisor documentation](https://asahilinux.org/docs/sw/m1n1-hypervisor/)
still says no M4-and-newer target has been pinned. Neither source demonstrates
the exact T6050/25G83 secondary-start observation we need.

## Could the XNU-conditioned firmware path supply missing initialization?

**Potentially a different initialization path; not an established fix.** The
official [Asahi explanation](https://asahilinux.org/2026/08/progress-report-7-2/)
says firmware detects an XNU payload and loads SPTM first. It also explains why
ordinary m1n1 cannot simply be presented as XNU: the resulting memory-management
contract conflicts with what m1n1 expects. This supports comparing conditional
handoff state, not assuming there is one omitted call that ordinary Linux can
make and then ignore the monitor.

The specific public shim lead,
[antiapplefox/m5-linux](https://github.com/antiapplefox/m5-linux/tree/35695e2a91feaff53e9df7b62bd1ab030bc58be0),
remains at `35695e2a91feaff53e9df7b62bd1ab030bc58be0`. Its own status explicitly
says no hardware bring-up, no working shim and no working Linux MMU port.
Actual source supports those limitations:

- The [draft boot-handoff patch](https://github.com/antiapplefox/m5-linux/blob/35695e2a91feaff53e9df7b62bd1ab030bc58be0/m1n1-patches/0004-sptm-add-xnu-shim-boot-handoff.patch)
  selects by SoC and assumes a resident monitor. Required entry state and
  ordering remain marked open; it logs the monitor return and then returns
  success without a qualified acceptance check. That is not monitor-presence
  detection or a tested handoff contract.
- The [Linux scaffold](https://github.com/antiapplefox/m5-linux/blob/35695e2a91feaff53e9df7b62bd1ab030bc58be0/linux-sptm/arch/arm64/mm/sptm.c)
  uses a configuration option as its presence predicate and retains missing
  state-lifecycle and TLB-maintenance implementation. The
  [integration README](https://github.com/antiapplefox/m5-linux/blob/35695e2a91feaff53e9df7b62bd1ab030bc58be0/linux-sptm/README.md)
  describes adding scaffold files/Kconfig/Makefile entries, not a completed
  replacement for Linux's memory-management call sites.

A viable implementation would need a permitted and accepted image/handoff,
positive monitor residency and state evidence, a qualified calling contract,
continuing compatible memory management, and an actual secondary-entry result.
The inspected code establishes none of those together on T6050. No protection
change, payload substitution, alternate installation or monitor call is proposed.

## Next discriminator

The next useful evidence must distinguish **an actual secondary entry state**
from **boot-CPU state and modeled guest state**. A candidate fix should make a
specific prediction about CPU1's first-fetch path or the effective permissions
needed by its earliest observable instruction. A CPU0 MRS dump, an ADT memory
range, a CPU-implementation RVBAR value, or another zero marker alone cannot
decide that prediction.

For the ongoing offline work, compare the retained raw-image and XNU-conditioned
handoff branches with explicit source/version/CPU/phase labels. Treat an
SPTM-specific prerequisite as applicable only if there is positive evidence that
the exact path activates the monitor; a firmware file's presence and chip-family
name are insufficient. Likewise, a static range setter or a boot-core read must
not be promoted to effective secondary state. If retained material cannot supply
that state, keep it UNKNOWN rather than infer it from the neighboring path.
This review does not justify another equivalent native experiment.

Fresh issue/commit searches, actual probe-source inspection, upstream mode/order
inspection and the shim-source check exhausted the focused public leads in this
pass. PR610's review and Gravity's FAQ still provide the attributed firmware
diagnosis recorded in 31S; no additional public Apple root-cause explanation or
tested T6050 correction was located. Snapshots, pins, timestamps and hashes stay
under ignored `build/research31t/public/`. Native readiness remains HOLD.
