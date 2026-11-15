# 31AT: bounded Mach-O compression and payload construction investigation

November 15, 2026. This pass investigates the installation/readback boundary,
not secondary CPU execution. The owner-authenticated saved-state observer found
an unrecognized selected payload and explicitly disabled lab Kernel CTRR after
the 31AS writer returned zero. All captured role-preservation checks passed.
Those facts do not establish an Apple firmware rejection.

## Input, tools and isolation

The input was the retained, generic local `kmutil` arm64e slice, SHA-256
`13827d7242e4550f3d45994f9849ce3a84dbb14d3bb6de21601c4488287582fb`.
It is an existing analysis input; this pass does not establish the identity of
the actual Recovery executable used during 31AS. No personalized boot object,
private policy, credential or firmware state was copied for this analysis.

REA 6.4.0 with Ghidra 12.1.4 ran in the existing diskless Linux VM, with two
vCPUs, 8 GiB RAM, no attached disk, no physical USB and explicit `--no-net`.
The successful jobs asserted that the guest had only the loopback interface.
The original lab job was restored byte for byte and the quiet lock released.
An initial sandbox launch was unavailable; a subsequent preflight rejected the
runner's default network interface before target analysis. Both successful
analysis jobs used explicit network exclusion. No global tools were installed.

Raw Apple inputs, assembly, pseudocode and provider output remain in ignored
workspace build storage. Only original findings and finite validation facts
are published here.

## Independently checked facts

REA completed procedure and string inventories, followed by two targeted
function dossiers. A separate Mach-O/function-start and A64 branch-immediate
calculation identified call sites. Installed LLVM disassembly then matched
**785 instruction words** against their original file bytes and independently
confirmed the two direct branch targets:

| Function start | Provider body bytes | Checked words | Bounded observation |
| --- | ---: | ---: | --- |
| `0x1000f6b60` | 860 | 215 | Call at `0x1000f6d04` targets the `compression_encode_buffer` import stub at `0x1001648cc`. |
| `0x1000f79f8` | 2,280 | 570 | Call at `0x1000f7e5c` targets the IMG4 payload-with-properties import stub at `0x100163ddc`. |

These establish relevant compression and IMG4 construction boundaries in the
retained executable. They do not establish that a particular branch ran in
Recovery, which destination received the candidate, or what carrier bytes were
written. The generic compression wrapper does not by itself identify the
algorithm selected by its caller.

Neither whole-function decompilation is admitted as verified behavior. The
first dossier has 394 high-pcode operations marked dead; the second reaches the
3,000-operation limit and reports truncation. No pcode PC lies outside the
reported body, but that alone does not repair the incomplete Swift semantics.
No Linux implementation or acceptance rule is derived from those pseudocode
statements. The independently checked instruction/call boundaries remain useful
anchors for a later, narrower trace.

## Engineering consequence

Removing `--compress` is not an evidenced fix. The corrected public J714s
report confirms that a compressed enrollment later reached Aura and booted
after a distinct Stage2 NVMe repair; see the
[primary-source comparison](../../../research/attempt31at-public-enrollment-recipes-2026-11-15.md).
Its informal CTRR wording conflicts with the documented expectation and does
not qualify a policy-guard relaxation on this machine.

The immediate implementation is therefore diagnostic: preserve the original
recognizer's exact acceptance decision while reporting finite read/framing/
codec/declaration/decoded-match stages. A future reviewed controller must record
those facts at the already-bound selected path before rollback. A read of the
current boot021 object cannot reconstruct the historical candidate's carrier.
Keep the existing policy and exact-object checks, and never reset the spent
31AR transaction to obtain another observation.

Native firmware acceptance, Linux boot, physical SMP, GPU acceleration and
performance/efficiency comparison were **NOT RUN** in this pass.
