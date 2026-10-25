# 31AB — the retained monitor's cold OS exit

Checked 2026-10-25. **The retained monitor does not force the OS entry to EL1.**
Its common exit derives the saved return mode from its own `CurrentEL`, preserves
four incoming argument words, and supplies a monitor-owned entry address. This
supports an original entry observer with explicit EL1 and EL2 handling. It removes
an unsupported EL1 assumption without requiring a complete 848-byte decoder or
all XNU helper initialization.

This finding supplements the [31AB public software contract](native31ab-public-contract.md)
and frozen [31AA local evidence](native31aa-handoff.md). It contains behavioral
findings only. Apple bytes, instructions and decompiler output remain private.
No native operation, monitor call, installed-object change or outreach occurred.

## Input and bounded verification

The unchanged retained decoded SPTM Mach-O is 1,376,288 bytes, SHA256
`da2ad8d4ecbf3e29fbaaa07e8c7d291ed20d296044494e00303c7a780d190666`.
Its October 19 association with macOS 26.6.2/25G83 is inherited through
[31W's provenance](../reverse-engineering/findings/cpu-startup31w/validation.json).
This pass did not re-extract it, match installed firmware, or establish that the
historical raw lab boot loaded it. The query copy is byte-identical; no analysis
wrapper was introduced.

The root-owned isolated REA VM completed setup and job with exit 0. Both fresh
queries completed within their 100-second bounds; the guest had loopback only
and no physical USB.

| Fresh target | Result | Qualification |
| --- | --- | --- |
| Common OS exit `0xfffffff0270a5220` | CLI 0, 22.189 s; provider body 80 bytes / 20 instructions; 8 P-code operations, 2 outside the body; bad-instruction warning. | **Whole-function pseudocode refused.** The provider excludes the final 4-byte guarded transition. The complete 84-byte boundary was independently checked. |
| Cold OS-entry producer `0xfffffff0270bf76c` | CLI 0, 22.222 s;492 bytes / 123 instructions; 250 P-code operations, 0 outside; no truncation or decompiler warning. | Bounded argument and producer facts only. Three terminal-call annotations are provider assumptions, not independent proof of the callees' behavior. Whole-function pseudocode was not used. |

Neither native value-flow result reports truncation. That does not override the
first query's boundary failure. The retained image has no `LC_FUNCTION_STARTS`;
provider bodies and entry markers are therefore qualified against actual mapped
words, without inventing source function boundaries.

LLVM/source comparisons cover **150 instruction-sized words / 600 bytes in four
bounded ranges, zero mismatches**: the complete 84-byte exit, the 492-byte cold
producer, and two 12-byte reason/call comparisons. The provider bodies account
for 143 words; the guarded-transition boundary adds one and the two comparisons
add six. The final transition matches the pinned public GEXIT encoding. This
comparison supports its interpretation; it is not a hardware execution test.
Exact mappings, body warnings and hashes are in the
[validation record](../reverse-engineering/findings/cpu-startup31ab/validation.json).

## The producer supplies owned entry records

**Confirmed within the checked cold caller:** the final common-exit call at
`0xfffffff0270bf950` supplies reason 0, an ordinary boot-record address, a
monitor-to-OS record address, and zero as the fourth argument. The records are
owned by the monitor image/context; they are not invented by a raw payload.
Their roles agree with the separately checked kernel consumer and public cold
entry convention. The cold label follows reason 0 and that contract; this pass
did not retrace the complete path from the monitor's declared primary entry to
this caller. This does not identify the entire 848-byte producer layout,
its incoming runtime contents, or the mappings and lifetime available to a new
host.

The common exit forwards x0–x3 unchanged. Its next-PC value comes from a
monitor-owned entry-address global. The observation therefore identifies a real
OS-entry producer/consumer boundary; it does not authorize calling an arbitrary
monitor address or substituting fabricated state.

Two separately bounded callers supply reason 1 and a zero fourth argument to the
same exit. These are a comparison with the secondary-entry reason convention,
not proof that those paths physically release a core. Their earlier setup and
argument records were not qualified in this pass.

## Return state follows the monitor's execution level

**Confirmed bounded state construction:** the saved status combines fixed bits
`0x3c1` with sampled `CurrentEL`. An EL1 sample yields `0x3c5`; an EL2 sample
yields `0x3c9`. These cases mask all DAIF classes and select the destination
level's own stack. The saved auxiliary status is zero. The routine does not
force EL1 or establish the relevant HCR_EL2/VHE configuration.

The pinned public register definitions name the relevant fields SPSR_GL1,
ASPSR_GL1 and ELR_GL1, and identify the auxiliary guarded bit. Combined with the
public guarded-exit model, zero auxiliary state supports an unguarded-return
interpretation. The register suffix alone does not determine the destination
execution level. These names/model are comparison evidence, not a measured
native entry.
[Register definitions](https://github.com/AsahiLinux/m1n1/blob/51b747dced07a58eacf5dabc31ed6f00bcfa20fd/src/cpu_regs.h#L722).

Before transition the routine prepares SP from a 64-bit pointer in its current
private context at offset 2640. **This does not qualify the incoming normal-world
SP, its ownership or its extent.** Guarded exit can change the active stack bank;
the public emulator model explicitly saves and restores banks around that state
change. An original entry should capture the incoming SP without dereferencing
it and establish its own qualified stack.
[Guarded-exit comparison](https://github.com/jprx/qemu-sptm/blob/bad6336fb24211f8c4e8e946c259bd5b12417340/target/arm/tcg/translate-gxf.c).

## Concrete implementation and next observation

The supported original implementation is a small observer: preserve entry words,
SP, `CurrentEL` and DAIF before using a caller stack; branch explicitly for EL1 or
EL2; establish owned storage, stack and fatal vectors under that branch's
assumptions. Read HCR_EL2 only from a qualified EL2 branch. Capture actual state
instead of treating an EL1-only refusal as a firmware contract. A privileged
observer cannot promise to record an unexpected EL0 entry before faulting.

This is a useful step toward a native host even though it does not call the
monitor. It does not need unused helper globals or complete outer-record
semantics. The separate SDK/AAPCS contract supplies a basis for original fixed
out-of-line transport; this exit analysis does not itself establish call
preservation or exception-resume semantics. Fatal vectors provide an observation
boundary, not a resumable exception implementation.

The next test should discriminate **whether a normally accepted original image
actually reaches this boundary with usable owned memory**. Its entry and fault
records need a qualified readback path; a RAM marker followed by an unobservable
permanent stop is insufficient. Successful entry would expose the actual level,
argument words and fault state before adding fixed calls. A failure before the
marker would require loader/entry evidence, not another blind CPU power attempt.
An ordinary ARM emulator can test the original observer's software behavior,
but cannot establish this firmware handoff or physical acceptance by itself.

No result here proves an SMP workaround or Apple-only necessity. The software
route now has a more concrete entry contract; the remaining first discriminator
is observable accepted entry and mapping, followed by a separately bounded
monitor-call/exception path and then physical secondary startup. No complete
native bridge is claimed by these static findings.
