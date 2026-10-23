# 31V: locating the alternate host bootstrap and qualifying public G17C mapping code

Checked 2026-10-23 after M1's 31U review. Public sources were read as data;
no downloaded source, boot procedure, VM operation or hardware access was run.
Earlier research remains frozen. The local target remains J716c/T6050 M5 Max
with retained 25G83 evidence; another project's marketing labels do not change
the locally observed ADT identity.

## Result

**The missing x1n1 host path is now more precisely located, but not publicly
qualified for reuse.** Aurora's public Aura repository explicitly separates
the x1n1 Mach-O work from the published bootloader. Its release documentation
also excludes the internal Mach-O/SPTM work. This explains a concrete missing
source boundary; it does not show that the reported alternate path cannot work.

An independent comparison of Aura's physical startup code with our frozen
31N baseline found a selected WFE policy change, but no new T6050 first-entry
initialization. The conspicuous reset relays and private-stack/MMU changes are
guarded for other chips or image layouts. No ready-to-reuse correction to the
unobserved CPU1 entry follows from this comparison.

Public G17C code supplies useful mapping and ordering comparisons. Vinix's
normal driver still rejects G17 firmware startup; its complete cache-flush
transaction is explicitly G13-only. Neither that transaction nor Asahi's
20-byte firmware-control record qualifies the locally investigated G17C
24-byte mapping notification.

## What became discoverable about x1n1

Aura HEAD was
[`553b566f69275ff4e46ee6542a7236fb80a333a2`](https://github.com/aurora-silicon/aura/commit/553b566f69275ff4e46ee6542a7236fb80a333a2).
Its [README](https://github.com/aurora-silicon/aura/blob/553b566f69275ff4e46ee6542a7236fb80a333a2/README.md)
explicitly reserves Mach-O boot-object support from Aurora's x1n1 development
for separate review. This is stronger evidence of a missing implementation
boundary than a repository-name search alone.

The [0.1.0 release document](https://github.com/aurora-silicon/aura/blob/553b566f69275ff4e46ee6542a7236fb80a333a2/docs/releases/0.1.0.md)
names `aura-internal` as the location of Mach-O/SPTM/native-SSD development
outside that release. It lists stage1/stage2 archives containing raw and
RAM-loadable Mach-O images, plus debug archives and checksums, but says the
exact release artifacts were not hardware boot-tested. A `.macho` output or
RAM-loadable image is therefore not evidence of the missing accepted
monitor-bearing boot object.

The bounded historical and release checks were:

| Checked public material | Result and limit |
|---|---|
| [Establishment commit `ece40e3824456784be8ea03b2f90578755c3fa26`](https://github.com/aurora-silicon/aura/commit/ece40e3824456784be8ea03b2f90578755c3fa26) | Its message already reserves Mach-O boot-object support for a separate review branch. This is not just a later README omission. |
| [Tag inventory](https://api.github.com/repos/aurora-silicon/aura/tags?per_page=100) and [tagged release document](https://github.com/aurora-silicon/aura/blob/c4331a90ef324eab33d34d1515d7e42748a293ab/docs/releases/0.1.0.md) | One visible tag, `v0.1.0` at `c4331a90ef324eab33d34d1515d7e42748a293ab`; the exclusion remains in that source. |
| [Public releases endpoint](https://api.github.com/repos/aurora-silicon/aura/releases?per_page=100) | Empty response at check time. This does not inventory unpublished drafts; no binary artifact was downloaded. |
| [Public branches](https://api.github.com/repos/aurora-silicon/aura/branches?per_page=100) and [all visible PRs](https://api.github.com/repos/aurora-silicon/aura/pulls?state=all&per_page=100) | Only `main`; PRs 1, 2, 4, 5, 6 and 7 concern T6041 storage, ADT power parents, M3 display/GPU handoff, relocation and linker layout. None supplies the missing T6050 monitor bootstrap. |
| Public request for the named `aura-internal` repository | HTTP 404. This establishes only that the public request did not expose it, not whether it exists privately or under another name. |

The checked [Aurora installer](https://github.com/aurora-silicon/aurora-installer/tree/bf0f3915b637eca0f2d4931daed4712b0e634f9e)
does not close this gap. Its
[boot-chain admission](https://github.com/aurora-silicon/aurora-installer/blob/bf0f3915b637eca0f2d4931daed4712b0e634f9e/macOS/Sources/OmarchyAppleInstaller/NativeBootChain.swift#L76)
recognizes `common-raw-v1` stage1 qualifications and `board-file-v1` stage2
selection. Its [model catalog](https://github.com/aurora-silicon/aurora-installer/blob/bf0f3915b637eca0f2d4931daed4712b0e634f9e/macOS/scripts/supported-models.json)
has no J714s/J716c entry. These are the inspected code paths and catalog,
not a claim about every installer or private development branch.

### The positive CPU report retains its original scope

The [SiliconForest report](https://github.com/chriskearney/siliconforest-linux/blob/5c978948f42c44c725d621bde31d70cd3439167c/Documentation/arch/arm64/t6050-sptm-ans.rst)
attributes 18-CPU Linux operation to **J714s/M5 Pro, 26A428**, under a resident
SPTM hypervisor. Its [guest-side DART implementation](https://github.com/chriskearney/siliconforest-linux/blob/5c978948f42c44c725d621bde31d70cd3439167c/drivers/iommu/apple-dart-x1n1.c)
names the x1n1 host interface. The published material does not expose the
physical first-entry records or vCPU scheduling policy behind the count.
Aura's acknowledgment of x1n1 development does not, by itself, identify the
exact host build used in that run. These are related leads, not a verified
source-to-artifact-to-hardware chain. [31U](native31u-upstream.md) retains the
earlier report and storage/idle-code qualifications.

## Actual physical CPU startup comparison

Compared Aura's pinned
[`smp.c`](https://github.com/aurora-silicon/aura/blob/553b566f69275ff4e46ee6542a7236fb80a333a2/src/smp.c),
[`start.S`](https://github.com/aurora-silicon/aura/blob/553b566f69275ff4e46ee6542a7236fb80a333a2/src/start.S),
[`startup.c`](https://github.com/aurora-silicon/aura/blob/553b566f69275ff4e46ee6542a7236fb80a333a2/src/startup.c)
and [`chickens.c`](https://github.com/aurora-silicon/aura/blob/553b566f69275ff4e46ee6542a7236fb80a333a2/src/chickens.c)
with the same files at the frozen Asahi
[`57a9339ffd1876e78297b17d34dece8cff8fa1ba`](https://github.com/AsahiLinux/m1n1/tree/57a9339ffd1876e78297b17d34dece8cff8fa1ba/src)
baseline. This is a source comparison, not execution of either source tree.

| Mechanism | Actual selected condition | Implication for the retained T6050 CPU1 case |
|---|---|---|
| PMGR startup | T6050/T6051 select offset `0x88000`; the ordinary routine writes system-start then per-cluster start. CPU1 uses bit 1 in both. | Same two-store stimulus as the frozen baseline. General mask arithmetic still uses four-core cluster spacing; that does not change same-cluster CPU1's value 2. |
| Reset destination check | Aura refuses an unmatched destination unless its qualified relocation/relay case applies; the older routine could print a mismatch and continue. | Useful refusal behavior, but our image/reset-mirror comparison already matched. It does not explain the negative CPU1 record. |
| Retired-image relay | `T8140`, locked destination, range/ownership and branch checks. | Not selected for T6050. |
| Resident header relay and persistent prepublished stacks | `T8142`, including a guarded header-before-vectors layout. | Base M5-specific. The retained raw boot021 starts at its vectors; it has no observed consumed header at that address. |
| Local MMU, private early stack, full image/shared-state publication, distinct release mask | `T8152`, with its own board/ADT/PMGR2 admission. | Not selected for T6050; physical M6 results cannot qualify these writes for M5 Max. |
| Image movement | Explicit chainload run-base request, or M3-only stage2 relocation based on CPU parts. | No such relocation is established for our frozen raw image. |
| WFE policy | `unsafe_wfi=true` added to shared `features_m4`, also selected by the listed T6050 parts; startup enables WFE and refuses switching it off. | A real applicable difference, but it changes the idle/dispatch loop **after** the arrival flag is published. It is not evidence of a missing physical first-fetch prerequisite. |
| Secondary C entry | T6050 retains CPU initialization, exception initialization and secondary entry; new special preparation is guarded for T8152. | No selected T6050 monitor or translation setup was found in these entry files. |

The [consumed 31N result](../native/boot/attempt31n-2026-10-22-result.md)
already confirms the paired stores completed without intervening host work;
no CPU1 identity was observed. The [31N image/publication audit](native31n-result-review.md)
also establishes raw image layout and PoC publication of CPU1-fetched hooks.
Aura's source does not reverse those observations or establish CPU1's actual
first fetch, exception level, translation or effective protection state.

Aura's [release claims](https://github.com/aurora-silicon/aura/blob/553b566f69275ff4e46ee6542a7236fb80a333a2/docs/releases/0.1.0.md)
identify ten CPUs for **T8142/J813** and twelve for **T8152/J873g**. Its
[integration note](https://github.com/aurora-silicon/aura/blob/553b566f69275ff4e46ee6542a7236fb80a333a2/docs/m5-m6-integration.md)
separates modeled reset regressions from physical M6 qualification. Neither
document supplies a physical T6050 secondary-entry result for this public tree.

## An original public monitor data contract exists at guest scope

Asahi's pinned
[`load_macos_sptm`](https://github.com/AsahiLinux/m1n1/blob/7cde7d1a784d851ebfee5579fa363c38b14150c0/proxyclient/m1n1/hv/__init__.py#L1933)
parses XNU/SPTM/TXM images and constructs their guest memory-map allocations.
It selects an entry inside the loaded SPTM read-only region and constructs
revision-specific boot arguments containing memory geometry, a converted
device-tree address and the top of kernel data. Its
[`start`](https://github.com/AsahiLinux/m1n1/blob/7cde7d1a784d851ebfee5579fa363c38b14150c0/proxyclient/m1n1/hv/__init__.py#L2245)
passes the entry and guest boot-argument address together to `hv_start`;
[`tgtypes.py`](https://github.com/AsahiLinux/m1n1/blob/7cde7d1a784d851ebfee5579fa363c38b14150c0/proxyclient/m1n1/tgtypes.py)
defines those boot-argument layouts.

This is a useful original source comparison for **entry plus context transport**,
distinct from later SMC/runtime mediation. It is a guest loader, not the
implementation of iBoot image acceptance, initial resident-SPTM construction
or a physical T6050 secondary release. It therefore does not fill the missing
host bootstrap or justify a new native procedure.

## G17C mapping, publication and completion are separate contracts

Vinix remains pinned at
[`ffb1fc5b87660104de4c268804cf1fb2d8afe4bc`](https://github.com/vlang/vinix/tree/ffb1fc5b87660104de4c268804cf1fb2d8afe4bc).
Its [G17C reference](https://github.com/vlang/vinix/blob/ffb1fc5b87660104de4c268804cf1fb2d8afe4bc/tools/agx-re/G17_T6050.md)
is M5 Max/T6050, **25F71 / AGXG17X 351.2 / RTKit-3255.120.11**, not local 25G83.

| Pinned implementation | Concrete useful comparison | Qualification limit |
|---|---|---|
| [UAT page-table operations](https://github.com/vlang/vinix/blob/ffb1fc5b87660104de4c268804cf1fb2d8afe4bc/kernel/gpu/agx/pgtable/pgtable.v#L287) | Aligned 16-KiB page mappings, descriptor stores, bounded range construction and removal of an already mapped prefix on failure. | A descriptor store is not firmware notification, publication completion or safe backing-memory release. |
| [G17 PIO mapping](https://github.com/vlang/vinix/blob/ffb1fc5b87660104de4c268804cf1fb2d8afe4bc/kernel/gpu/agx/gpu/g17.v#L535) | Separates page-aligned physical mapping from firmware VA including byte offset; rejects unsupported scatter records; records mapped prefixes for rollback. | Twelve expected mappings and chosen apertures are this implementation's versioned assumptions, not local ADT-role evidence. |
| [G17 initialization](https://github.com/vlang/vinix/blob/ffb1fc5b87660104de4c268804cf1fb2d8afe4bc/kernel/gpu/agx/gpu/g17.v#L790) | Builds both root mappings before endpoint start; prepares UAT handoff before publishing root addresses; waits for its readiness condition. | This code exists behind a closed normal-driver gate. Its logging and source sequence are not proof it ran on G17C hardware. |
| [Hardware admission](https://github.com/vlang/vinix/blob/ffb1fc5b87660104de4c268804cf1fb2d8afe4bc/kernel/gpu/agx/hw/hw.v#L223) and [driver guard](https://github.com/vlang/vinix/blob/ffb1fc5b87660104de4c268804cf1fb2d8afe4bc/kernel/gpu/agx/driver/driver.v#L1103) | `can_boot_firmware` accepts G13 with enumerated ABIs; the guard precedes power/ASC writes. [T6050](https://github.com/vlang/vinix/blob/ffb1fc5b87660104de4c268804cf1fb2d8afe4bc/kernel/gpu/agx/hw/t6050.v) remains `g17_26_5_partial`. | No admitted G17C native adapter follows from the presence of initialization helpers. |
| [G13 flush transaction](https://github.com/vlang/vinix/blob/ffb1fc5b87660104de4c268804cf1fb2d8afe4bc/kernel/gpu/agx/gpu/gpu.v#L1107) | Serializes a firmware-control submission, prepares a handoff slot, obtains a queue token, signals firmware, waits for pointer progress and state 2, then completes the slot. An unpublished failure is distinct from a submitted timeout. | Explicitly requires G13; it is not a recovered G17 `notifyNewMapping` transaction. |

Asahi's [UAT dirty-table publication](https://github.com/AsahiLinux/m1n1/blob/7cde7d1a784d851ebfee5579fa363c38b14150c0/proxyclient/m1n1/hw/uat.py#L493)
writes table bytes and issues context invalidation. The file is byte-identical
to [Gravity's checked copy](https://github.com/GravityLinux/bootloader/blob/f02d4a52017915febb222539636b5b025a70407a/proxyclient/m1n1/hw/uat.py).
Asahi's [object release](https://github.com/AsahiLinux/m1n1/blob/7cde7d1a784d851ebfee5579fa363c38b14150c0/proxyclient/m1n1/agx/object.py#L239)
describes a different operation: shared remapping, table publication, a
firmware-control flush, completion wait, unmapping and eventual backing release.
Its [handoff state implementation](https://github.com/AsahiLinux/m1n1/blob/7cde7d1a784d851ebfee5579fa363c38b14150c0/proxyclient/m1n1/fw/agx/handoff.py)
makes those phases separately visible. These are useful lifetime and ordering
comparisons, with no demonstrated G17C/25G83 qualification.

The [Asahi firmware-control message](https://github.com/AsahiLinux/m1n1/blob/7cde7d1a784d851ebfee5579fa363c38b14150c0/proxyclient/m1n1/fw/agx/channels.py#L445)
is **20 bytes**: a 64-bit address, two 32-bit fields and two 16-bit fields.
Its ring has 256 entries and separate 32-bit read/write indices. This is not
layout-equivalent to the locally investigated 24-byte outbound mapping record.
The inspected Vinix G17/UAT files did not provide a matching
`notifyNewMapping`/`insertNewMappingEntry` contract; that is a bounded source
search result, not a claim of absence throughout all public code.

## Next discriminating evidence and retention

For the CPU lead, the shortest useful next provenance is **the actual host
revision and accepted boot-object description used in the reported 26A428
run, plus a record connecting at least one non-boot physical CPU's entry to
that host**. That would permit a concrete prerequisite comparison with the
retained raw branch. Guest CPU count, a runtime SMC interface, a RAM-loadable
Mach-O artifact or a fix guarded for another SoC cannot substitute for it.

For G17C, qualify the exact versioned mapping-notification layout, address
conversion, producer publication and completion/ownership conditions before
connecting any table builder or queue helper to a device. The public sources
help separate those contracts; they do not supply the missing local adapter.

Small pinned files and public API responses, URLs, UTC times and SHA-256 hashes
are retained under ignored `build/research31v/public/`; all 55 retained files
(2,334,888 bytes) pass their recorded hashes, and one failed public request
remains in the manifests. No proprietary content, private conversation or downloaded source
is published here. The result remains **unresolved host bootstrap and native
GPU adapter**, not an Apple-only impossibility claim or a ready native workaround.
