# 31V: the last preparation helper is command-line handling

2026-10-23. **Offline evidence; native31V HOLD / NOT RUN.** M1's31U review
passed475 pins,225 Python methods and95 C groups without an actionable issue.
That review did not establish monitor residency or CPU1 execution.

The new trace rules out a specific apparent monitor-entry prerequisite. The
helper immediately before alternate entry publication operates on the command-
line span shared by both entry producers. It is not a monitor activation or
secondary-release step. The final common caller forwards an existing entry,
context and mode to the already identified boot-CPU handoff. This supplies no
compatible native alternate bootstrap, and does not prove that one is impossible.

## New caller and data-contract evidence

One fresh REA function query covers `0x100c1ad46c8`,332 bytes. It is reached at
`0x100c1ad2468` from producer A and at `0x100c1ad4498` from producer B. Its
location just before B's selected-entry publication was the hypothesis tested;
its actual inputs resolve that apparent significance.

Independent bounded argument tracing shows that **both callers pass the same
object-relative span: start `+0x6c`, exclusive end `+0x46c`, length1,024 bytes**.
The helper has four byte-read sites and explicit NUL/space handling. It has no
direct system-register operation, supervisor/hypervisor/secure-service operation,
or indirect call. Its tiny argument/result adapters were checked independently.
These local facts describe bounded text handling; no transitive hardware safety
claim is made for arbitrary callees or caller-supplied memory.

The span matches the command-line field in public m1n1's BootArgs revision3.
A standard-library AST size audit reads the public source as data; no third-party
module is imported or executed:

| Public BootArgs revision | Command-line offset | Bytes |
|---|---:|---:|
| 1 | `0x6c` | 256 |
| 2 | `0x6c` | 608 |
| 3 | `0x6c` | 1,024 |

The exact revision matters to an original serializer or checker. The common
field offset does not make the three extents interchangeable. The match identifies
the inspected span; it does **not** measure the revision of a historical runtime
object. Source: [m1n1 BootArgs definitions at7cde7d1](https://github.com/AsahiLinux/m1n1/blob/7cde7d1a784d851ebfee5579fa363c38b14150c0/proxyclient/m1n1/tgtypes.py).

## What reaches the final transfer

Bounded original-word checks of `0x100c1b3ef44` confirm that its final call at
`0x100c1b3f054` forwards incoming parameters1,2,0 as selected entry, context,
and mode to wrapper `0x100c1b3f058`. That wrapper invokes service7. This is the
common boot-CPU path already connected to the cleanup trampoline in
[31L](native31l-first-fetch.md); this pass does not assign it to CPU1's reset path.
The checked forwarding does not construct a new monitor-specific context.

This caller's31K whole-function P-code crossed its reported body boundary.
That refusal remains intact: the new claim uses independently checked bounded
instructions and an original private argument inventory, not the refused
pseudocode. The initially proposed repeat query was removed **before launch**;
its original list remains privately retained as superseded. It is neither an
executed query nor a query refusal.

The [31U comparison](native31u-firmware.md) still distinguishes the raw-associated
entry/fallback path from SPTM-named object entry/range inputs. The newly identified
shared command-line operation supplies no missing hardware action between those
stages and does not resolve historical accepted-image selection.

## Alternate bootstrap: the concrete remaining prerequisite

The public Asahi guest loader provides a useful original reference for serialized
data: it lays out XNU/TXM/SPTM regions, selects the SPTM entry, serializes the
chosen BootArgs revision, and starts the guest with an entry and BootArgs address.
Its virtual, physical and guest address domains remain distinct. This is a
**guest loader contract**, not the accepted native boot-object format or proof
that physical secondaries execute. Source: [guest preparation and entry at7cde7d1](https://github.com/AsahiLinux/m1n1/blob/7cde7d1a784d851ebfee5579fa363c38b14150c0/proxyclient/m1n1/hv/__init__.py).

The newly located Aura public release explicitly leaves its x1n1-derived
Mach-O/SPTM boot-object work outside that release. The public-source audit also
finds no new T6050 pre-entry release sequence: its selected WFE difference acts
after secondary arrival, while special new entry setup is for other SoCs.
See the [31V upstream audit](native31v-upstream.md) for exact pins and scopes.
Runtime monitor mediation code therefore cannot fill in the missing native host
bootstrap by assumption.

The remaining prerequisite is concrete: **an inspectable accepted native host
bootstrap and its initial monitor-context contract, qualified for the relevant
firmware/platform**. Without that, the guest reference and common firmware
forwarding are insufficient to design an executable alternate native handoff.
No image-classification change, synthesized accepted selector, monitor replay or
protection operation follows from this pass.

The next decision is finite. If that host contract becomes available, compare
its versioned BootArgs/region ownership and entry state with the retained path,
then assess an original offline implementation. If only guest-runtime APIs or
post-arrival idle changes are available, they do not answer the native-entry
question; retain HOLD. No further query of this command-line helper or unchanged
marker-only boot is warranted. No new CPU adapter is implemented here.

## Validation

The same generic J716c `mBoot-18000.161.10` input is retained. Decoded SHA-256
`b4822fc8902c3693ee590c544011603423a75291edd60afd31210d068a4ca120`; analysis ELF
SHA-256 `f89169923c17be829c6b31c3c04c5695d06d42a42cea7390f61214202400dcee`.
The header-derived base `0x100c1aa4000` is not a measured live address. Decoded
bytes match the ELF mapping at offset4096; generic-carrier provenance is unchanged.

The single fresh REA/Ghidra12.1.4 query took67.746 seconds and exited0; root's
isolated VM setup/job exited0. The batch verified loopback only and no physical
USB. Its83 instructions and69 P-code operations have no truncation, no operation
outside the reported body and no provider-removed-block warning. Its general
manual-review gate is preserved; whole-function pseudocode is not published or
accepted as implementation source.

Apple LLVM21 independently matches **189 words /756 bytes in7 bounded blocks**,
zero mismatches:93 words new beyond the prior published CPU coverage and96
rechecked. The overlap union includes both exclusive-end blocks and validated
inclusive-end body anchors, including31K's common caller. The
[validation record](../reverse-engineering/findings/cpu-startup31v/validation.json)
contains exact offsets, hashes, provider flags, caller spans and public-layout
provenance. Earlier removed blocks, truncation and cross-boundary refusals remain
unrepaired. Counts are static coverage, not execution proof.

Apple bytes, disassembly and pseudocode remain private and ignored. No native
operation, personalized-object access, installation, boot-policy change, firmware
replay or restart occurred. CPU1, native SMP/GPU and performance gains remain
unverified.
