# 31AB: original entry and monitor-call boundary

Checked 2026-10-25. This continues the frozen
[31AA contract](native31aa-public-contract.md) and
[local findings](native31aa-handoff.md). Downloaded sources are data only;
installed SDKs remain read-only. No monitor call, emulator execution, installation,
native boot or external contact is performed by this review.

**The published software calling convention is sufficient to implement and
inspect an original out-of-line transport.** A separate exhaustive description of
every hardware clobber is not a blanket prerequisite for that work. Runtime
permission, monitor identity, image mapping and exception handling remain
different questions. This narrows the overly cautious transport wording in 31AA;
it does not promote an unexecuted object into a qualified native bridge.

## What the software ABI supplies

The hash-bound 26.5 SDK declares ordinary C-callable bootstrap interfaces, states
that returned values follow AAPCS64, and supplies a static stub generator. That
generator puts the destination in x16, uses XNU-client GENTER selector 0, and
offers optional caller-side hooks. The no-hook path does not read the opaque
helper state. These declarations, their actual generator and the matching local
fixed-dispatch observations provide a practical software contract; they are
stronger than identifying an instruction word alone. Header hashes and measured
scope remain in the [31Z comparison](native31z-public-contract.md).

The AAPCS64 specifies preserved x19–x29 and SP, scratch x16/x17, platform-specific
x18, and 16-byte stack alignment. Only the low 64 bits of v8–v15 must survive an
ordinary call; NZCV is not preserved. An original out-of-line function can expose
that conventional boundary to C, preserving its own frame and return address.
Avoiding x18 and SIMD simplifies this small interface. An inline assembly
fragment with an incomplete clobber list would not provide the same compiler
contract.
[Arm AAPCS64, 2025Q4](https://github.com/ARM-software/abi-aa/blob/2025Q4/aapcs64/aapcs64.rst#611-general-purpose-registers),
[stack constraints](https://github.com/ARM-software/abi-aa/blob/2025Q4/aapcs64/aapcs64.rst#6451-universal-stack-constraints).

The relevant fixed calls use domain 0/table 0: registration 14 takes one 64-bit
physical affinity, fixups completion 15 takes no argument, and exception-return
registration 18 takes one 64-bit virtual address. All three are void. Normal
return therefore provides no numeric success result to decode. The existing
registration planner supplies arguments; it does not authenticate monitor
residency or authorize replay. A future early fixups-completion stub must itself
be reachable in the initially executable boot region.

## Entry observation is smaller than a complete host

Public XNU places its entry in `__TEXT_BOOT_EXEC`, establishes its own stacks,
sets its vector base and synchronizes before fixups completion. Thus an original
early entry need not borrow an incoming stack or decode unused monitor fields.
However, successful format inspection alone does not establish executable or
writable mappings for a new image.
[Public entry and cold preparation](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/sptm/start_sptm.s#L61).

The EL1 names in that source do **not** prove an EL1 execution level: VHE can
change how those accesses are interpreted. The26.5 SDK's guest-exit description
explicitly distinguishes a guest EL0/EL1 regime from the host EL0/EL2 regime.
An observation should preserve actual `CurrentEL` and the original argument/state
words before choosing an EL-specific register bank. Reading HCR_EL2 is an EL2
operation; a prototype must not attempt it from an EL1 branch. A refusing branch
for an unsupported level is an implementation policy, not proof that the monitor
promises that level.

A fatal vector that records an exception and stops is a bounded observation
mechanism, not a resumable monitor exception implementation. It cannot observe
every exception routed to a higher or guarded level. Its record also needs a
qualified reader: a RAM marker followed by a permanent stop is not a useful
physical experiment if no observer can retrieve the RAM. An emulator debugger
could provide that observation path without asserting hardware acceptance.

## Exception return is a separate interface

The SDK describes registration 18 as supplying a continuation which the monitor
places in the kernel return address when handing an exception to OS vectors.
After ordinary exception return reaches that continuation, the SPTM resume
operation uses selector 1 and does not return normally. This selector is not
bootstrap endpoint 1. TXM and secure-kernel resume are separate operations with
different context requirements.

Public XNU selects among those continuations from thread state. An original host
may implement a smaller SPTM-only path only after bounding which domains can be
interrupted in its workload. Masking asynchronous interrupts does not eliminate
synchronous exceptions or establish monitor entry permission. The public order
also distinguishes setting the vector base before 15 from registering the
exception-return continuation later in C.
[Return-domain routing](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/locore.s#L1696),
[C-side continuation registration](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/sptm/arm_init_sptm.c#L752).

## Actual-firmware emulation: useful source, excluded stock workflow

The newly checked `jprx/qemu-sptm` implementation is a concrete firmware loader,
not merely an emulated SPTM service table. At commit
`bad6336fb24211f8c4e8e946c259bd5b12417340`, it arranges SPTM, TXM and BootKC
segments, rewrites device-tree memory-map entries, builds ordinary boot arguments,
and supplies their physical address in x0 at the SPTM image's entry. The machine
resets at EL2. This gives inspectable initial-context and placement examples; it
does not supply an authenticated native handoff or a complete T6050 profile.
[SPTM loader](https://github.com/jprx/qemu-sptm/blob/bad6336fb24211f8c4e8e946c259bd5b12417340/hw/arm/xnuboot_sptm.c),
[machine reset and inputs](https://github.com/jprx/qemu-sptm/blob/bad6336fb24211f8c4e8e946c259bd5b12417340/hw/arm/darwin.c).

**The stock workflow does not meet this project's no-security-check-bypass
constraint.** Its loader unconditionally invokes a patch routine which replaces
an AppleImage4 handler with a zero return. The project explains this as avoiding
a missing-device-model deadlock. Whatever its motivation, this alters Apple
execution, so the README's broad no-kernel-patches description is insufficient
authorization to run it. No such patched firmware execution was performed.
[Patch implementation](https://github.com/jprx/qemu-sptm/blob/bad6336fb24211f8c4e8e946c259bd5b12417340/hw/arm/xnu_patch.c),
[project description](https://github.com/jprx/darwin-vm/blob/edfc19433da8d04d5927a7b1932acce4034f307c/README.md).

Its register model initializes protection-control values and range readbacks from
the loader's constructed map. The inspected AMCC device implements register
read/write storage; it does not itself establish memory-access enforcement.
Guarded entry/exit are modeled in instruction and exception handlers. These
are useful comparisons for a model, but a successful run would not validate the
real machine's protection configuration. The generated Apple-register header
was absent from the checked source tree; its requested raw URL returned 404.
That bounded inspection is not an audit of every enforcement path.
[Register setup](https://github.com/jprx/qemu-sptm/blob/bad6336fb24211f8c4e8e946c259bd5b12417340/hw/arm/apple_regs.c),
[AMCC device](https://github.com/jprx/qemu-sptm/blob/bad6336fb24211f8c4e8e946c259bd5b12417340/hw/arm/apple_amcc.c),
[guarded instruction model](https://github.com/jprx/qemu-sptm/blob/bad6336fb24211f8c4e8e946c259bd5b12417340/target/arm/tcg/translate-gxf.c),
[exception handling](https://github.com/jprx/qemu-sptm/blob/bad6336fb24211f8c4e8e946c259bd5b12417340/target/arm/helper.c#L9396).

The machine permits one CPU. The published successful M5 configuration is
T8142/Mac17,4; no listed T6050/M5 Max result qualifies this machine. Retained SPTM
alone also does not satisfy this loader's inputs: it uses TXM, BootKC, a compatible
modified device tree, trust cache and RAM disk. Its geometry contains asserted
placement assumptions. A reproducible, unmodified-firmware experiment would
therefore require a separately reviewed loader/model path and matching inputs;
this review has not established one.
[Machine CPU limit](https://github.com/jprx/qemu-sptm/blob/bad6336fb24211f8c4e8e946c259bd5b12417340/hw/arm/darwin.c),
[published tested configurations](https://github.com/jprx/darwin-vm/blob/edfc19433da8d04d5927a7b1932acce4034f307c/README.md#tested-configurations).

Source reuse also needs attribution and license review: the repository identifies
the emulator overall as GPLv2 and unmarked files as GPLv2-or-later, with separately
licensed parts. This checkpoint reads these sources as data and imports no
emulator implementation into the original adapter.
[License](https://github.com/jprx/qemu-sptm/blob/bad6336fb24211f8c4e8e946c259bd5b12417340/LICENSE).

## Public host status and the next discriminator

The refreshed public Aura README still separates x1n1 Mach-O boot-object work
from the published wrapper; its release note excludes internal Mach-O/SPTM work
and says the exact release artifacts are not hardware-qualified. The serious
historical all-core report remains the attributed lead assessed in
[31X](native31x-upstream.md), not independently reproduced evidence for this
J716c/25G83 machine. This pass did not locate its accepted native host source.
Repository-history freshness is limited: direct API reads in this agent failed
DNS, and several browser history/API views could not be fetched. Those failures
are not evidence that no newer source exists.
[Aura entry-scope statement](https://github.com/aurora-silicon/aura/blob/main/README.md),
[release exclusions](https://github.com/aurora-silicon/aura/blob/main/docs/releases/0.1.0.md#qualification-and-remaining-work).

Standard ARM emulation can already test the original entry's ordinary
instructions, owned storage, explicit EL1/EL2 branches and fatal vector behavior.
Independent RAM readback makes that result observable. It cannot model GENTER,
qualify native VHE configuration or guarded exception routing merely from those tests, or establish
the Mach-O loader's mapping and acceptance. A privileged unsupported-level
refusal also does not promise an EL0 record: privileged reads may fault first.

The useful next firmware observation is actual monitor-to-original-entry execution with
retrievable reason, argument and exception-state records, followed separately by
the minimal fixed-call/exception path. It does not require a complete 848-byte
decoder first. Physical secondary release remains a further test. No result here
establishes either a working T6050 SMP workaround or Apple-only necessity. The
software route remains plausible because the entry/call contract is concrete;
the missing evidence is a matching, permitted runtime handoff and physical-core
result, not proof that another party must change firmware.
