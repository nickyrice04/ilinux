# 31AB: what would establish a software solution or an Apple dependency?

The evidence currently supports **continued software engineering**, not a claim
that Apple must fix the machine. There is no working local multicore solution
yet. Repeating the unsuccessful raw-start sequence would not resolve that
uncertainty.

## The concrete software route

The strongest route retains the running Secure Page Table Monitor and enters
through its OS handoff, instead of assuming that the raw m1n1 environment supplies
the same CPU lifecycle. Public T6050 reports describe physical secondaries in a
resident-host configuration, but the successful host revision and this machine's
exact firmware context have not been reproduced here. Those reports support
investigation; they are not local compatibility measurements.

31AB advances that route from argument planners to linked original code. The
entry captures the actual incoming state without trusting its stack or
dereferencing its argument pointers, establishes owned stack/vector storage and
records fatal exceptions. The code is position independent by an instruction and
relocation audit, not merely by omitting fixup metadata. Three separate monitor
transport routines are present but uncalled. The ordinary entry/fault instructions
execute successfully in nine standard ARM emulator cases. Apple firmware and
GENTER are not executed in those tests.

The original 112 KiB Mach-O image passes read-only boot-property derivation.
**That is a format result, not a successful firmware handoff.** The immediate
integration work is an observable entry: a bounded framebuffer marker using
qualified boot-video fields and a legitimate existing writable mapping. The
range-table lookup and translation tests address that specific dependency.
No complete USB stack or reconstruction of every unused monitor field is needed
for the first observation.

The next physical milestone should test the accepted host and show distinctive
entry evidence, preserving the known working boot package. It must identify what
the screen marker proves and what absence of the marker leaves ambiguous. It
must not be presented as an all-core boot. Only after that should the host use
the qualified fixups/exception protocol, register the source-identified CPU set,
and attempt one bounded secondary entry with a per-core execution record. Linux
SMP integration, both source core classes, frequency control and idle behavior
follow physical entry; they cannot be inferred from registration arguments.

## What an Apple-dependent conclusion would require

A failed raw boot, missing public source, a refused decompilation or a silent
screen is not proof of an immutable firmware barrier. Nor does one successful
physical secondary establish performance parity or prove every core class works.

A defensible Apple-dependent conclusion needs a specific identified firmware
restriction affecting the required operation, independently reproduced on this
board/firmware after satisfying its legitimate entry and lifecycle contract,
with the applicable supported software paths excluded by evidence. Any conclusion
must name its scope: a restriction on raw boot need not rule out a resident-host
implementation. We cannot prove that every conceivable software workaround is
absent merely by exhausting a list of experiments.

If progress remains incomplete, call it **unresolved**, and identify the missing
observation. Resource-driven postponement is a project decision, not proof that
an Apple update is necessary. Current unresolved points are real firmware image
acceptance, usable observable entry, monitor-call lifecycle and physical secondary
release. They are narrower than the earlier requirement to decode the complete
848-byte record.

## Relevant external work, checked as source

The [public contract review](native31ab-public-contract.md) distinguishes
SiliconForest's reported resident-host success, Aura's raw boot implementation,
public XNU/SDK contracts and an actual-SPTM QEMU project. The latter's stock loader
patches image verification, so it was not executed under this project's rules.
The useful result here is an original-instruction emulator fixture, not a claim
that a complete Apple firmware simulator has been validated.

A fresh default-branch check on 2026-10-25 found Aura at
`ec4a6ab8b4252079e78196515577d73ef0a86135`. Its three-commit difference from the
previously inspected `78b5d9d1` changes `src/kboot.c`, `src/sart.c` and `src/sart.h`;
it does not add a new resident-host entry implementation. SiliconForest m1n1's
default head remains `aca1258c2d7daad7db7079d4f89bb8217659f7ac`. A default-branch
query is not an exhaustive branch search. In particular, the current default
head of the previously inspected Niklas bootloader is an ancestor of that
research revision, not evidence that its research work disappeared.
[Aura comparison](https://github.com/aurora-silicon/aura/compare/78b5d9d17f7897ad5085c8465f0a9807a51553bb...ec4a6ab8b4252079e78196515577d73ef0a86135),
[SiliconForest source](https://github.com/chriskearney/siliconforest-m1n1/tree/aca1258c2d7daad7db7079d4f89bb8217659f7ac).

macOS, installed boot objects, security and volumes remain unchanged. No native
boot is prepared by this checkpoint. The exact implemented components, outcomes
and remaining qualifications are recorded in the
[31AB validation](../native/boot/attempt31ab/validation.json).
