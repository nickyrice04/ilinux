# 31Y — normal image properties and the remaining host-entry contract

**The normal image-format route has a useful new discriminator: an original
fixture can make the local read-only inspector derive a nonzero `kcbz` from its
standard segment layout. This is property extraction, not boot acceptance or
secondary CPU execution.** The fresh REA query separates the analyzer that
supplies those values from the caller's choice of property serializer.

This CPU-only pass used one root-owned isolated REA VM and retained generic
tool data. No installer, native bootstrap, policy change or monitor replay was
performed. The independent original-fixture experiment and its exact outcomes
are recorded in [31Y format probe](native31y-format-probe.md); the public entry
ABI comparison is in [31Y host-source research](native31y-host-source.md).

## Bounded result

The new target is retained `kmutil` routine `0x100024e64`, queried once. It
returned its exact 464-byte body, containing 116 instructions and 136 P-code
operations, in **90.601 seconds**. Query, setup and job exits were zero. The
provider reported no removed-block warning, no P-code truncation and no P-code
operation outside the body. The guest exposed loopback only and no physical USB.

Independent LLVM/carrier checks cover **139 instruction words / 556 bytes**:
the queried body and its 64-byte and 28-byte forwarding functions. All match,
and all three spans match retained `LC_FUNCTION_STARTS` boundaries. The existing
private full-image disassembly was reused; this count is bounded verification,
not physical CPU progress or a claim that the whole tool was analyzed.
[Validation](../reverse-engineering/findings/cpu-startup31y/validation.json)
records the input, query, result and checked-range hashes.

The input is the retained31Q arm64e slice, SHA-256
`13827d7242e4550f3d45994f9849ce3a84dbb14d3bb6de21601c4488287582fb`.
Its extraction from the then-current fat executable was verified in31Q; this
pass does not independently refresh installed-tool or historical boot identity.
Addresses here are link-time addresses. All31X and earlier evidence, including
provider refusals, remains unchanged.

## What selects the property form

**Confirmed bounded static behavior:** the wrapper calls the image analyzer at
`0x100024450` from `0x100024ed0`. Its successful path then selects between the
previously identified collection and raw property serializers. The selection
tests bit0 of incoming x3, preserved by the wrapper; it does not test the
analyzer's returned image classification at that selection site. The collection
call is at `0x100025004`; the raw call is at `0x100025010`.

Two short forwarding functions form the direct chain
`0x1000f849c` → `0x1000f79b8` → `0x100024e64`. They preserve that mode argument.
**The indirect binding of this chain to both the inspector and `configure-boot`
subcommands remains unresolved.** The analyzer's complete field derivation and
installation validation were not queried. This result must not be enlarged into
proof that both subcommands accept the same images or perform identical checks.

The distinction matters for the format experiment. A collection-shaped property
dictionary can contain `kcbz=0`; its presence alone does not establish the
nonzero condition in the earlier firmware branch. Conversely, the root-owned
inspector experiment now obtains nonzero `kcbz` automatically from original
fixtures containing the public segment roles `__TEXT_BOOT_EXEC` and
`__DATA_SPTM`. It does not supply a property override. Properly formed flat
`MH_EXECUTE` and `MH_FILESET` fixtures also produce property dictionaries, so
neither the filetype nor `LC_FILESET_ENTRY` alone establishes this distinction.
The [format record](native31y-format-probe.md) owns the geometry, complete case
matrix and strict success classification; process exit zero alone was found
insufficient.

[31Q's static firmware comparison](native31q-firmware.md) associated nonzero
`kcbz` with the optional accepted-object preparation path. That is a reason to
investigate normal format compatibility. It does not prove that any31Y fixture
is bootable, accepted by the installed firmware, or sufficient to initialize the
resident monitor. Historical raw-path selection remains inferred, not observed.

## Concrete implementation boundary

The format result enables an **original offline fixture generator and strict
property-result validator**. It corrects a specific false dead end: ordinary
custom format compatibility can be tested without invoking the installer or
guessing a private activation selector. Root owns that implementation.

It does not yet enable a native host adapter. Apple's public XNU comparison
describes an OS entered by an already running monitor with an entry reason and
separate iBoot and monitor argument pointers. It also requires initial executable
segment, image-fixup, vector, allocation-boundary and monitor-library obligations.
A register shuffle alone would omit those obligations. The full applicable
monitor-argument/header version and its compatibility with J716c/T6050 build25G83
remain unqualified; the inspected public XNU build scope does not include T6050.
See the [source and version limits](native31y-host-source.md).

The next decision is finite:

1. **Can normal original layout derive the relevant properties?** The read-only
   fixture experiment now answers yes for its tested geometry. Preserve this
   as a parser result; do not substitute it for installation acceptance.
2. **Can the full matching monitor-to-host contract be supplied?** Obtain the
   applicable argument/header version and qualify entry reasons, memory ownership
   and fixups completion. If those remain unavailable, a compatible host cannot
   yet be designed from the established evidence.
3. **Only after that contract is qualified**, an original host design can be
   assessed for a separately authorized bounded boot/physical-secondary test.
   No such native image or test is prepared by this pass.

This narrows a possible software route and its next implementation dependency.
It establishes neither a working local CPU workaround nor an Apple-only
necessity.
