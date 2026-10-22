# 31M firmware investigation: close two misleading startup leads

2026-10-22. **Offline static investigation; no native operation performed.**
The consumed 31L result still does not establish CPU1's first instruction or
incoming execution state. This pass identifies what two tempting firmware
paths actually observe, so they do not become speculative additions to the
next native experiment.

The first path captures CPU/cluster error information after an exception. It
does not provide a CPU1 running/reset status contract. The second path selects
peripheral hardware descriptors; its locked reset-address operation is not
application-CPU reset programming. **Neither justifies a new native MMIO read
or write.** CPU1's existing power and opaque-byte transitions remain separate
from proof of instruction execution.

## Artifacts and independent validation

The input is the retained generic, unpersonalized `iBoot.j716c.RELEASE`,
identified as `mBoot-18000.161.10` in the earlier firmware investigation.

| Artifact | SHA-256 |
|---|---|
| Decoded firmware, 4,266,536 bytes | `b4822fc8902c3693ee590c544011603423a75291edd60afd31210d068a4ca120` |
| Byte-preserving analysis ELF | `f89169923c17be829c6b31c3c04c5695d06d42a42cea7390f61214202400dcee` |

The header-derived analysis base is `0x100c1aa4000`, **not a measured live
address**. The ELF carries the original bytes at file offset 4096. Its global
addresses do not establish runtime contents.

Three fresh REA 6.4.0 / Ghidra 12.1.4 dossiers completed in the existing
isolated analysis VM, with exit 0: 57.979, 57.263 and 56.954 seconds. Their
reported bodies total 100 instructions / 400 bytes; all 113 high-pcode
operations are inside those bodies, with no truncation or reported removed
blocks. Behavioral interpretation nevertheless relies on original bytes and
independent decoding, not on treating generated pseudocode as source.

Fresh bounded Apple LLVM decoding checked the three bodies and 12 additional
helper/caller blocks: **378 distinct instruction words / 1,512 code bytes**,
zero source, ELF or decoded-word mismatches. Separately, 37,200 bytes of the
descriptor table were checked. These are static validation totals, not native
execution or coverage results. The
[validation record](../reverse-engineering/findings/cpu-startup31m/validation.json)
retains ranges, hashes, query outcomes and limits. Raw Apple bytes, assembly,
pcode and pseudocode stay in ignored local build storage. The previous VM job
was restored and the shared locks released after analysis.

## The CPU/cluster snapshot is error capture

**Confirmed static, bounded.** REA target `0x100c1ae86d0` has a 212-byte body.
It fills a caller-supplied record from seven 64-bit hardware reads, followed by
a 32-bit cluster field. Its caller allocates/serializes a 64-byte record.

| Analysis location | Observed behavior | Limit for CPU1 startup |
|---|---|---|
| `0x100c1ada800`–`0x100c1ada868` | Obtains a cached affinity value, or obtains MPIDR through the direct helper / service path, then selects affinity bits 15:8. The direct helper at `0x100c1cafea0` reads MPIDR_EL1. | This is cluster selection, not the local CPU index. A cached firmware global is not a current target measurement. |
| `0x100c1ae86d0`–`0x100c1ae87a4` | Reads three CPM locations, another cluster location, and three CPU-implementation locations. For cluster 0, the latter are `0x210052048`, `0x210052028` and `0x210050020`, all 64-bit accesses. | The routine never adds CPU1's local-core stride. It does not establish provenance for corresponding `0x21015xxxx` addresses. |
| Same snapshot body | For a nonzero cluster selector, the three CPU-implementation record slots use the same cluster-shifted address derived from `0x210052048`. | Do not generalize the cluster-0 three-register layout to another cluster or core type. |
| `0x100c1cafff4`–`0x100c1cb002c` | Captures ESR/FAR and conditionally calls wrapper `0x100c1ae87a4` when the masked ESR equals `0xbc000000`: the SError exception class, with the other selected mask bits clear. | This is an exception diagnostic route, not a startup-completion waiter. EL1 accessor names alone do not establish the live EL because the firmware uses VHE. |
| `0x100c1ca5d5c`–`0x100c1ca5de4` | A second caller obtains this snapshot and writes a 64-byte record into its diagnostic serialization path. | Serialization does not provide register field meanings or a read-side-effect contract. |

The complete hardware meaning of the captured fields remains **Unknown**.
Their presence in an error report is not proof that they are harmless status
reads, clear-on-read, live PC samples, or reset-release indicators. No new
CPU1 probe follows from their addresses. In particular, this route does not
resolve the meaning of the already observed CPU-implementation byte at
offset `0x100`.

## The earlier locked-address path selects peripheral descriptors

**Confirmed static, bounded.** The earlier lead at `0x100c1aaa664` performs a
locked, masked-address check and therefore superficially resembles the
application-CPU reset-address programmer. Its actual address construction
must be followed before interpreting that resemblance.

The `+0x50000` window thunk at `0x100c1aab970` reaches the freshly queried
getter `0x100c1aa9ddc`. The getter selects a context descriptor through
`0x100c1aab93c`, `0x100c1aabaa8` and the freshly queried selector
`0x100c1aaba28`. It obtains the window base from descriptor offset `0x18`,
then combines the supplied window offset and the context's die component.

The selector bounds the low 16-bit context ID to 0–74, uses a stride of
`0x1f0`, and checks the type field at `+0x190`. The table starts at
`0x100c1e253b0`, contains 75 entries / 37,200 bytes, and has 46 nonzero-type
entries. Its SHA-256 is
`ff095382036fd15b9c5ea8405f63e98a2d7e3ac5883b6774852fe209f66ca611`.

None of those valid entries supplies the application CPU0 or CPU1 window
base needed to produce `0x210050000` or `0x210150000` through this path.
An independent sanitized ADT match identifies descriptor 3's window base,
`0x28c000000`, within `/arm-io/apr0`. Other entries supply different
peripheral windows; this pass does not assign every entry a device name.

This closes the proposed application-CPU interpretation of this bounded
descriptor path. It does **not** establish that no other firmware path can
affect CPU1. The separate retained application-CPU programmer at
`0x100c1c2e398`, its CPU-window enumeration, and its existing readback findings
remain unchanged. The peripheral path's additional transactions must not be
transplanted into application-CPU startup.

## Decision for the next experiment

These findings remove two proposed shortcuts: error-capture reads are not a
qualified CPU1 execution observer, and peripheral reset setup is not missing
application-CPU initialization. They provide no basis for adding cluster-wide
restoration writes, changing locked reset state or touching debug controls.

The next original experiment must distinguish a named entry/visibility
hypothesis using its own reviewed observation contract. A positive CPU1
identity can establish a reached prefix; another all-negative outcome cannot
prove that CPU1 executed nothing. Full cooperation between the machine's
12 Performance and 6 Super cores still depends on establishing secondary
entry first, followed by native coherence, interrupts, timing, frequency,
idle and scheduling measurements. This static investigation claims none of
those results or macOS performance parity.
