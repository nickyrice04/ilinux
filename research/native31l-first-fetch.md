# 31L: first fetch and firmware handoff

2026-10-22. **Offline investigation; native changes NOT RUN.** This records
behavioral findings from the matching generic firmware. No firmware sequence
is copied into Linux or replayed on hardware. Raw Apple material remains in
ignored build storage.

## What the new trace establishes

The firmware has an explicit boot-CPU handoff that prepares execution state
before calling the selected entry. It is reached through a supervisor-call
service and uses a copied cleanup trampoline. This is useful evidence about
why CPU0 reaches m1n1; it is **not evidence that CPU1 starts through the same
trampoline**, or that CPU1 inherits CPU0's EL, translation, cache or exception
state.

This distinction matters to 31K: CPU0's successful recorder control validates
that control in CPU0's environment. It does not validate the unobserved
environment that must let CPU1 execute its first instruction and first store.
The already matching reset-address mirror remains evidence about the register
value, not an observed CPU1 PC.

## Artifacts and validation

| Artifact | SHA-256 |
|---|---|
| Decoded generic `iBoot.j716c.RELEASE` | `b4822fc8902c3693ee590c544011603423a75291edd60afd31210d068a4ca120` |
| Byte-preserving analysis ELF | `f89169923c17be829c6b31c3c04c5695d06d42a42cea7390f61214202400dcee` |

The image is the same `mBoot-18000.161.10` investigated in 31H/31K. The analysis
base `0x100c1aa4000` is header-derived, not a measured live address. The wrapper
preserves raw input at file offset 4096 and does not prove runtime BSS values.

The three bounded batches produced six successful fresh REA 6.4.0 / Ghidra
12.1.4 dossiers and one explicit refusal. REA reported no procedure at the cleanup
trampoline's address; no artificial function was installed to hide that
limitation. Its bounds instead come from the original-byte copier. Independent
Apple LLVM decoding and raw/ELF comparison verified **2,206 instruction words /
8,824 code bytes**, zero mismatches. Literal/padding bytes are counted
separately. See the [validation record](../reverse-engineering/findings/cpu-startup31l-first-fetch/validation.json).

All successful dossiers have untruncated high-pcode with no operation outside
their reported bodies. The service, copier and retention-metadata function nevertheless contain
provider-removed blocks. Their whole-function pseudocode is rejected; local
claims below use bounded instructions, explicit call sites and independently
decoded table entries. A valid byte check is not proof of runtime reachability.

## Connected handoff path

| Bounded analysis location | Confirmed static behavior | Interpretation limit |
|---|---|---|
| `0x100c1b3f048`–`0x100c1b3f068` | The high-level caller passes selected entry/context/mode arguments to the final supervisor call, number 7; its fourth argument is set to 1. | This is the final OS handoff path, not a secondary reset vector. |
| `0x100c1caf400`–`0x100c1caf448`, `0x100c1caf820`–`0x100c1caf858` | The vector path recognizes the AArch64 SVC exception class, extracts its immediate, and reaches the service dispatcher. | EL1-named register accessors do not alone establish execution at EL1; see VHE below. |
| `0x100c1cb6cf0`–`0x100c1cb6d18`; table at `0x100c1cb9898` | Bounded signed table-entry decoding maps selector 7 to `0x100c1cb7d38`. | The table's checked bounds and selector matter. Unrelated selectors are not inferred from proximity. |
| `0x100c1cb7d38`–`0x100c1cb7d4c` | The selected block forwards the entry/context/mode and normalized fourth argument to `0x100c1cb9b4c`. | The surrounding dispatcher has independent validation/authorization branches; this pass does not bypass them. |
| `0x100c1cb9b4c`–`0x100c1cb9f28` | After validation and memory housekeeping, the service invokes the trampoline copier when its fourth argument is nonzero, then calls final handoff helper `0x100c1b3ee4c`. | Local call relationships are established; complete service reachability is not taken from decompiler output. |
| `0x100c1cafed8`–`0x100c1caffc0` | The copier selects the source range `0x100c1aeb740` to `0x100c1aebafc` (exclusive), 956 bytes, and prepares a destination window for execution. | It is a copying/preparation function, not the actual secondary reset implementation. |
| `0x100c1b3ee4c`–`0x100c1b3ef08`; getter `0x100c1addc18` | The final handoff retrieves the prepared entry window through a thunk/getter and performs an indirect call with the selected boot entry and context. | The getter's static window is not a newly observed hardware register or CPU1 PC. |

## Cleanup and heterogeneous cache behavior

The copied range includes 852 code bytes and 104 literal/padding bytes. Its
bounded code performs these observable categories of work:

- Masks exceptions, retains the entry/context arguments and clears selected
  temporary memory ranges.
- Writes zero through the `SCTLR_EL1` accessor, brackets that transition with
  barriers, and invalidates translations through `VMALLE1`.
- Discovers cache topology through `CLIDR_EL1` and selected `CCSIDR_EL1` values,
  performs set/way clean-and-invalidate operations for applicable cache levels,
  and checks the discovered count against a value selected by MPIDR affinity
  bits 23:16. The expected count is three when that field is 1, otherwise two.
- Clears translation, exception and thread-context accessors, both stack
  selections and general/SIMD state; the final tail performs instruction-cache
  invalidation and barriers before transferring to the saved entry with the
  saved context.

These are behavioral observations, not a proposed initialization routine.
Some parts of the trampoline also touch implementation-specific state and
memory windows. Their semantics and ownership are not established here, and
the sequence must not be replayed or transplanted.

The cache distinction reinforces an existing project requirement: cache and
CPU-type assumptions must come from architectural discovery and the actual
topology. It does not justify identifying the two observed cases with arbitrary
marketing labels or applying a performance-core register set to CPU1. No
secondary-core cache state is measured by this static branch.

## VHE limits the EL inference

At the firmware's original entry, `0x100c1aa4008`–`0x100c1aa4018`, the code
sets HCR_EL2 bits 34 and 27 (E2H and TGE) and synchronizes. Under Arm's VHE
rules, accessor names shared with EL1 can refer to the EL2 host regime. Thus
the later `SCTLR_EL1`, `TTBR*_EL1`, `VBAR_EL1`, `ESR_EL1` and `SPSR_EL1`
spellings must not be read as proof of an EL1-only firmware path. See
[Arm's VHE description](https://support.arm.com/documentation/102142/0100/Virtualization-host-extensions).

The copied trampoline's final transfer uses a saved return address; no ERET is
present in that bounded final path. This constrains the inspected path, but
does not prove a live EL or exclude earlier state changes outside it. In
particular, CPU0's boot-time state cannot be assigned to CPU1.

## Quiescence leads resolved as device handoff and metadata

The two exact-string leads were checked rather than promoted into CPU-start
prerequisites:

| Lead | Bounded evidence | Result |
|---|---|---|
| `quiesced` in `0x100c1aae08c`, called by the primary handoff preparer | Path helper `0x100c1aaf464` selects `arm-io`; helper `0x100c1aaf4e8` uses the immutable bounded descriptor at `0x100c1e2eda0`, whose string is `ans/iop-ans-nub`. | This path owns ANS/storage handoff and its device-tree marker. It does not establish secondary CPU quiescence or a CPU reset-release prerequisite. Its other device operations are not proposed for replay. |
| `retention-force-quiesce` in `0x100c1c345c8` | The local branch at `0x100c1c34d24` conditionally passes `retention` and `retention-force-quiesce` to `0x100c1c5a7bc`. That wrapper forwards a property-table context to `0x100c1c5a620`. The worker finds the named entry, reduces the serialized size, shifts the remaining fixed-size entries and decrements the entry count. | These particular calls remove properties from mutable metadata. They are not direct core-stop or reset-release writes. Nearby DART/clock-protection properties support device metadata ownership, but do not by themselves identify every possible caller's device. |

The retention function has many provider-removed blocks, including this
branch. Its whole-function pseudocode is unusable for the relevant question;
the property argument construction, helper chain and array removal were
therefore checked against original bytes and independent LLVM decoding. The
remaining runtime branch conditions are not assumed. These are bounded
negative findings: they eliminate these two proposed CPU-quiesce leads, not
every possible firmware CPU-quiesce path.

The retained reset programmer also distinguishes a write value from its
readback predicate. It constructs a normalized address plus bit 0, then checks
only the documented-by-analysis mask. It does not preserve unexplained upper
readback bits when constructing the write. Equal CPU0/CPU1 mirrors therefore
cannot establish that unexplained reset-mode state is harmless: CPU0 reaches
m1n1 by the primary handoff, while CPU1 is being started through hardware. No
new upper-bit meaning or additional read consumer was established in this
pass, so no reset-register change follows.

## Implications for an original next experiment

The connected primary handoff gives no basis for running its cleanup sequence
on CPU1, modifying locked reset state, or adding unproven debug-register reads.
A useful experiment must instead test an explicit incoming-context or startup
prerequisite hypothesis, with distinct observable outcomes and bounded RAM
effects. The exact-image model can eliminate wrong register-width, address,
entry-prefix and translation assumptions; it cannot establish a firmware reset
state by simulation.

The independent public-m1n1 audit finds that the installed bare boot021 proxy
path initializes topology without starting secondaries. Therefore boot021
having already executed CPU1's original instructions is not supported as the
cause of stale instructions. Earlier firmware activity and inherited
secondary state remain unknown. Any proposed cache experiment must name that
weaker hypothesis accurately.

The next firmware question is now narrower: what state transition allows a
secondary that reports power actual 15 and opaque byte 2 to fetch from the
already matching physical base? A further trace should identify an actual
secondary startup/quiesce consumer, or an unlock-free, provenance-backed
observation with defined side effects. Repeating image-entry selection would
not answer it. Meanwhile, an original RAM-only experiment may still be useful
if it tests a precise visibility/context hypothesis and separates a positive
entry observation from another inconclusive negative marker.
