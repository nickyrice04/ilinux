# 31AA: minimum monitor bridge contract

Checked 2026-10-24, continuing the frozen
[31Z public comparison](native31z-public-contract.md) and
[local consumer findings](native31z-handoff.md).

**The complete 848-byte record is not a blanket prerequisite for original host
work.** A host must qualify every field and service it consumes, preserve memory
that remains owned by other components, and leave unused fields opaque. Decoding
the entire structure is necessary only if the implementation actually requires
it. This narrows the earlier “complete matching ABI” gate; it does not establish
a deployable image or permission to call an unqualified monitor interface.

The most useful new public result is that Apple's image-fixup helper explicitly
permits no chained-fixup command. That supports an original image with no runtime
pointer fixups as a concrete design candidate, while image acceptance, execution
state and the monitor's fixups-completion transition remain separate obligations.

No external contact, installation, firmware operation, native execution or
settings change occurred. Public source was retained as data. One original
constant-only translation unit was compiled to textual LLVM IR; it emitted zero
functions and was not linked or executed. SDK source and analysis output remain
under ignored build storage.

## What is and is not version matched

A fresh official tag listing still identifies `xnu-12377.121.6`, commit
`ac9718fb1af618d5ce8678d0dc6e8a58f252216f`, as its newest displayed release. An
exact API lookup for `xnu-12377.161.14` returned404. This is a bounded result for
Apple's repository, not proof that matching source cannot exist elsewhere.
[Official tags](https://github.com/apple-oss-distributions/xnu/tags),
[pinned source](https://github.com/apple-oss-distributions/xnu/tree/ac9718fb1af618d5ce8678d0dc6e8a58f252216f).

The installed SDK search found SPTM headers in 15.4, 26.5 and 27.0. The older 15.4
header declares helper version 7; it is not a 25G match. The 26.5 and 27.0 header
hashes and measured conditional layouts remain the 31Z comparators. No newly
located header qualifies the complete local 848-byte record. In particular, a
16-byte difference must not be assigned guessed field meanings merely because
another SDK has a 16-byte optional section.

The official public source does not include the helper-library implementation in
its SPTM source directory. Its SDK documentation declares `libsptm_init` as a
local utility accepting a monitor-supplied state pointer. The original research
by DFF independently describes that library as outside the public source; its
device and version examples are not this T6050 firmware.
[Public directory](https://github.com/apple-oss-distributions/xnu/tree/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/sptm),
[DFF's original analysis](https://df-f.com/blog/sptm4).

## Empty fixup work is a supported public case

Apple's `kernel_collection_slide` validates load-command boundaries, then returns
success if `LC_DYLD_CHAINED_FIXUPS` is absent. If that command is present, the
walker also skips segments without chains and pages explicitly marked as having
none. Therefore nonempty rebasing work is not intrinsically required by this
public helper.
[No-command case](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/mach/dyld_kernel_fixups.h#L273),
[empty segment/page cases](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/mach/dyld_kernel_fixups.h#L298).

This does **not** prove that deleting the load command makes an arbitrary image
relocation-free. An original image must be constructed and audited so that its
code, data references, absolute pointers, authenticated pointers and any runtime
dependencies remain correct at the actual placement. A position-independent
early section can be investigated without importing Apple's image-fixup routine.
The conclusion is an engineering inference from the helper's supported empty
case, not a firmware acceptance result.

The containing image contract remains significant. Public XNU's own fixup wrapper
expects the kernel inside an `MH_FILESET`, a first kernel segment describing
`__TEXT`, and a collection header at its specified link base plus slide. It also
adjusts image metadata after sliding because iBoot leaves those load-command
addresses unslid. A statically linked inner component and the old “static
kernelcache” format are different propositions: this source explicitly excludes
the latter on SPTM systems. The31Y parser fixtures do not establish the former's
firmware acceptance.
[Image-context assumptions](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/sptm/arm_init_sptm.c#L328),
[static-kernelcache distinction](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/sptm/arm_init_sptm.c#L110).

## Dependencies before and after the first monitor boundary

The public cold path prepares its own stacks, preserves x1/x2, applies image
fixups and static configuration, installs the final vector base, synchronizes,
and performs fixups completion. It enters the C consumer only afterward. Argument
copying, helper initialization and topology registration are later operations.
The image-fixup wrapper takes no monitor-record argument; its static-configuration
neighbor consumes the iBoot command line. Those XNU-specific implementations are
not automatically requirements for an original host that has no such features.
[Cold-path ordering](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/sptm/start_sptm.s#L122),
[later C initialization](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/sptm/arm_init_sptm.c#L752).

In particular, `libsptm_init` is **not a universal dependency of fixed bootstrap
dispatch**. The SDK's static stub constructs the dispatch identifier in x16 and
uses XNU-client GENTER selector 0; this macro itself does not read helper state.
Its optional entry/exit hooks serve the calling kernel. Public XNU's hooks
preserve argument/result registers, maintain a thread preemption counter when a
thread pointer exists, check that entry is not already in guarded mode, and may
process deferred scheduling work on return. They do not make opaque library
initialization an intrinsic prerequisite for the transfer. An original host must
qualify its own scheduling and exception obligations instead of importing those
XNU-specific dependencies.
[Public hook implementation](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/locore.s#L2681).

| Bridge purpose | Minimum qualified dependency | Work that can remain offline now |
| --- | --- | --- |
| Preserve cold entry | Full reason word; correct x1/x2 roles; readable, stable argument buffers; reserved destination storage. | Existing explicit848-byte snapshot and selected-field tests. No raw pointer dereference. |
| Allocate physical memory | Qualified RAM, page size, live reservations and the locally checked physical boundary at+24. | Existing interval planner. No requirement to interpret unrelated auxiliary-image, hibernation or timestamp fields. |
| Finish early image preparation | Initially executable boot region; valid mapped stacks/vectors; correct image placement and any actual relocation/PAC obligations. | Original image inspection and rejection of unsupported dependencies; no invented claim of monitor success. |
| Use helper utilities | Matching helper initialization behavior and the lifetime/mapping of every referenced table actually used. | Version-scoped behavioral comparison; unused services may be omitted. Do not parse opaque state merely to select a profile. |
| Handle monitored exceptions | A qualified handler/return continuation for each reachable domain and its preserved state. | Explicit dependency/phase checks; native continuation remains unresolved. |
| Register CPUs | Resident-monitor identity, cold-boot phase, boot CPU first and correctly sourced physical IDs. | Original ordered-plan validation. Predicted ordinals are not observed monitor-assigned results. |
| Start physical secondaries | Qualified per-CPU entry, stacks, state publication and actual physical release/observation. | Source comparisons and bounded plans; registration alone does not establish this result. |

## Exact service distinctions

These are declarations and constants from the hash-pinned26.5 SDK, compared with
public XNU use; identical constants in another release do not qualify its full ABI.

| Operation | Declared arguments/result | Boundary |
| --- | --- | --- |
| `libsptm_init` | One constant helper-state pointer; byte-sized utility result. | Local library initialization; no monitor call. Documentation names success0 and invalid-argument2 for a null input. |
| Fixups completion | No arguments; no C return value; bootstrap dispatch15. | Changes executable-region typing and validates/locks vector state in the public cold sequence. |
| Exception-return registration | One64-bit virtual handler address; no C return value; bootstrap dispatch18. | Supplies the monitored exception-return continuation, not just a vector base. |
| CPU registration | One64-bit physical identity; no C return value; bootstrap dispatch14. | Boot-CPU operation before lockdown; source input is the zero-extended32-bit ADT `reg` value in the checked consumer. |
| Resume interrupted SPTM | No arguments; declared non-returning. | A distinct resume mechanism; its named GENTER selector1 is not ordinary bootstrap endpoint1. |

The void declarations provide no portable numeric “success” result. An original
offline plan must not turn a caller Boolean into evidence that the monitor
accepted any transition.

For a bounded encoding cross-check, pinned Asahi m1n1 identifies the GENTER word
as `0x00201420` and names the system-register tuple `(3, 6, 15, 8, 0)` as guarded
execution status. This does not import its direct GXF initialization path into a
resident-monitor host. The SDK documents AAPCS return behavior and FP/LR handling
around optional hooks; the inspected material does not independently enumerate
every monitor clobber or establish all permitted interrupt/entry states for these
two endpoints. Therefore these facts support inspection of a proposed transport,
not a claim that a new native wrapper is fully qualified.
[Instruction definition](https://github.com/AsahiLinux/m1n1/blob/51b747dced07a58eacf5dabc31ed6f00bcfa20fd/src/gxf_asm.S#L7),
[register definition](https://github.com/AsahiLinux/m1n1/blob/51b747dced07a58eacf5dabc31ed6f00bcfa20fd/src/cpu_regs.h#L704).

Public XNU's return continuation distinguishes interrupted TXM, secure-kernel and
SPTM execution using XNU thread state. A custom host cannot borrow those
assumptions merely by registering an address. If it omits services, it must
qualify which exception paths remain reachable and how those paths preserve and
resume the correct context.
[Exception-return routing](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/locore.s#L1696).

The new compile-only26.5 query measures the helper's version10 fields ending at
offset224, followed by88 reserved bytes in a312-byte object. The later fields
include trace/per-CPU pointers, counts and tables. This provides names and widths
for comparison with the independent local initializer; it is not evidence of
the actual incoming version. Header comments require shared TTBR1 mappings for
the state's virtual addresses and direct clients to helper interfaces. Preserving
the outer bytes cannot by itself preserve the referenced objects' lifetime.

The next practical bridge work is consequently bounded: prove an original
image's actual early dependencies, qualify only the helper/exception services
it uses, and retain all unconsumed monitor state and owned memory. No whole-record
guess, arbitrary SDK substitution, ready native host or Apple-only dependency
follows from these findings.
