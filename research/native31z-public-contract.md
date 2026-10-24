# 31Z: SDK bootstrap ABI and resident-monitor prerequisites

Checked 2026-10-24, following M1 review `776b54f` and the frozen
[31Y host-source comparison](native31y-host-source.md).

**New evidence:** the installed Apple SDKs contain the complete client bootstrap
type and documented monitor-service contract. They supply concrete comparison
profiles, but none of the measured profiles matches the retained 25G83 consumer's
848-byte monitor-argument copy. They also document a real secondary-start prerequisite:
the boot CPU registers the system's CPUs with the already resident monitor before
lockdown. Neither finding creates a monitor after raw entry, establishes the
complete 25G83 ABI, or proves physical secondary startup.

No installed object, policy, firmware or hardware was changed. Sources were read
as data. Original constant-query translation units were compiled to textual LLVM
IR only; no resulting program was linked or executed. SDK header source and
compiler output remain under ignored build storage.

## Provenance and version boundary

The earlier public-XNU-tree search did not locate `sptm_xnu.h`. That limited result
must not be read as absence from Apple's SDK distribution. The installed headers
are beneath the SDK-relative directory
`System/Library/Frameworks/Kernel.framework/Versions/A/Headers/platform/sptm/`.
The original Steffin/Classen research independently identifies SDK-distributed
SPTM headers, beginning with MacOSX15.5.sdk; its version is not the local firmware.
Apple also publishes a documentation entry for the helper-state type.
[Original research, section 16.4](https://arxiv.org/html/2510.09272v1),
[Apple helper-state documentation](https://developer.apple.com/documentation/kernel/libsptm_state_t).

| Inspected SDK | SDK product build | `sptm_xnu.h` SHA-256 | `sptm_common.h` SHA-256 |
| --- | --- | --- | --- |
| Command Line Tools macOS26.5 | 25F70 | `8930a33944a12e1da79980636756c794a97b6c58f30ae39b6a3b38b56372189e` | `080e752a4cd640b0456b6f57cc70f109f3336d70cb70e56805de669b53555697` |
| Xcode macOS27.0 | 26A425 | `37dd5c425112bd36e594df6d41d7fefdcbc90ac661964a7ed09821bdad367d83` | `aa7355ba3bfad80fe8855d3ac5bfdb5ef187f8244e8665adad7216b659a56f42` |

The fresh official XNU tag check located `xnu-12377.121.6`, pinned at
`ac9718fb1af618d5ce8678d0dc6e8a58f252216f`; its entry, initialization and topology
sources were retained and compared. This public source version and both SDK
versions remain distinct from the target's 25G83 firmware. No default SDK is
silently selected as that firmware's ABI.
[Pinned official source](https://github.com/apple-oss-distributions/xnu/tree/ac9718fb1af618d5ce8678d0dc6e8a58f252216f).

## Compile-derived profile facts

The original queries used arm64 targets, explicit virtual-platform/MTE switches,
and an empty analysis shim for the SDK's missing XNU `board_config.h` include.
That shim does not select a real board or supply a hardware configuration. These
are measured **conditional header layouts**, not a complete T6050 kernel build.
The four baseline compilations succeeded, emitted zero function definitions and
reported the same three constant-array-folding warnings in SDK declarations.
Two initial 27.0 queries rejected the old dispatch macro name; those diagnostics
are retained, and the corrected queries use that header's declared macro.
An additional twelve compile-only configurations checked the actual conditional
dimensions and arm64e/VBT comparisons; all succeeded with zero function definitions.

| Explicit profile | Bootstrap bytes / alignment | Helper-state bytes | `LIBSPTM_VERSION` |
| --- | --- | --- | --- |
|26.5, nonvirtual, MTE switch either value|832 /8|312|10|
|26.5, virtual, MTE switch either value|840 /8|312|10|
|27.0, nonvirtual, MTE disabled|856 /8|312|12|
|27.0, nonvirtual, MTE enabled|872 /8|312|12|
|27.0, virtual, MTE disabled|864 /8|312|12|
|27.0, virtual, MTE enabled|880 /8|312|12|

Inside the outer 26.5 definition, the only conditional is
`APPLEVIRTUALPLATFORM`. Inside 27.0, the conditionals are `HAS_MTE` and
`APPLEVIRTUALPLATFORM`. The nested 26.5 helper definition has no conditional;
27.0 adds `defined(SPTM_VBT) || defined(VBT_COMPONENT)`, substituting an eight-byte
pointer for eight reserved bytes on LP64. Each VBT alternative was compiled and
left the nonvirtual, MTE-disabled 27.0 total at 856. The arm64e nonvirtual,
MTE-disabled queries also measured 832/856 respectively. These are measured LP64
configurations with the stated shim, not a claim about every compiler, board,
SDK release or unpublished header.

The separate [local 25G83 consumer analysis](native31z-handoff.md) observes an
**848-byte** monitor-record copy. No measured configuration above equals 848.
That local copy length establishes neither a complete structure nor its version;
nearby header fields, added padding or a different SDK must not be substituted
without independent qualification. The installed SDK inventory resolved to 15.4,
26.5 and 27.0, with no installed 26.6 SDK. This is an inventory result, not evidence
that a matching declaration cannot be obtained elsewhere.

All queried targets are little-endian. The reason type occupies one byte and
compiler-evaluated constants are cold 0, secondary 1, warm 2, hibernation 3 and panic 4
in both SDKs. A captured 64-bit register still requires validation of its complete
value; the type's width is not permission to truncate unknown high bits.
The 27.0 enum also adds an exception-entry reason, another reason not to treat the
26.5 reason set as a universal ABI.

The 26.5 outer record has **no standalone version member**. At offset 0 it contains
the previous-PTE page reference. In 27.0 that field is replaced by an outer version
value, declared as `0xD00F000000000000`; later timestamp fields and an MTE-dependent
section also affect layout. The helper's size stays 312 while its internal version
and use of reserved storage change. Equal helper size therefore does not establish
ABI compatibility.

Selected 26.5 nonvirtual fields provide an explicitly selected comparison profile;
they do not constitute a complete layout for the observed 848-byte record:

| Offset | Bytes | Meaning and address domain |
| ---: | ---: | --- |
|8 /16|8 each|Physical-aperture bounds expressed as PAPT virtual addresses; not physical RAM addresses.|
|24|8|First available physical address after monitor/component allocations.|
|64 /72|8 each|Monitor/dispatch/per-CPU TXM stack virtual bounds; inclusive start, exclusive end.|
|80 /88|8 each|Executable virtual bounds in the kernel TTBR1 space; inclusive start, exclusive end.|
|408|8|Pointer to the monitor-maintained XNU panic Boolean.|
|416|312|Opaque helper state; retain without interpreting its internal fields.|

The nested helper version is an `int` at its own offset 0, but the bootstrap header
explicitly directs consumers to use helper interfaces rather than inspect that
state. An original decoder should select the outer profile using external,
qualified provenance, not use this opaque field as an autodetection oracle.
The whole record also contains random-seed material: synthetic fixtures contain
no live seed, and a future native snapshot cannot be treated as public diagnostic
data merely because its structure is understood. These observations come from
the hash-pinned SDK declarations, not a live monitor record.

The local consumer independently reads the argument at +24, reads +408, and passes
the subobject at +416 to library initialization. The official public consumer
assigns `first_avail_phys`, assigns `sptm_xnu_triggered_panic_ptr`, and initializes
the helper from `libsptm_state` at the corresponding source-level steps. Both SDK
profiles place those members at those offsets. This selected agreement can
coexist with the total-size mismatch; it does not establish the remaining layout
or justify parsing a live 848-byte record wholesale.
[Public consumer](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/sptm/arm_init_sptm.c#L773).

## Registration is a real prerequisite, not physical-release proof

The 26.5 SDK's `sptm_register_cpu` documentation (lines 1756–1773) states that the
**boot CPU** calls it for the CPUs supported by the system, before machine
lockdown. The boot CPU must be registered first; registration order assigns
logical IDs; the physical ID must correspond to MPIDR. The monitor brings up only
registered CPUs. This corrects any inference from guest-emulator registration
that the real API must be invoked by an already running secondary.
The declaration accepts one 64-bit physical ID and returns no value; CPU-data
addresses and exception-stack addresses are not additional registration arguments.

The public XNU implementation independently corroborates the call placement:
`arm_init` calls `ml_parse_cpu_topology`; that routine walks `/cpus`, reads each
selected entry's `reg` property as its physical ID, and calls `sptm_register_cpu`.
The inspected routine follows device-tree order; it does not implement an explicit
boot-CPU-first sort. The header's required ordering and the producer's topology
ordering must therefore both be qualified.
[Cold initialization call](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/sptm/arm_init_sptm.c#L891),
[topology and registration](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/machine_routines.c#L1144).

SDK 26.5 constructs dispatch identifiers from domain, table and endpoint fields.
The XNU bootstrap table in the SPTM domain yields identifiers 14 for registration,
15 for fixups completion, and 18 for exception-return registration. These are
interface identities, not proposed monitor calls from raw mode. The 27.0 header
changes the dispatch-construction API to include a command class, although these
three ordinary-call values remain equal in the compiled query.

## Entry, fixups and memory obligations

The public XNU entry comment describes x0 as the reason. For nonpanic reasons it
documents x1 as iBoot arguments and x2 as monitor arguments; panic gives those
registers different meanings. The actual cold path preserves and consumes both
argument pointers. The common warm/secondary/hibernation path preserves x3 and
reuses x1/x2 while locating already prepared per-CPU state. Consequently, exposing
typed boot-argument access only for cold entry in an original prototype is a
conservative local qualification rule; it must not be justified by incorrectly
claiming that Apple's comment only covers cold entry.
[Public entry contract and paths](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/sptm/start_sptm.s#L34).

The SDK and public consumer distinguish several separate obligations:

- **Fixups completion:** initially only the boot-executable subregion can execute;
  completion changes the full code region's type. The public cold consumer sets
  its final vector base before that boundary. This is distinct from later
  read-only-region lockdown.
- **Exception return:** XNU registers a return-handler address so exceptions from
  monitored execution can return through the monitor's expected continuation.
  A vector address alone does not implement that lifecycle.
- **Memory ownership:** XNU uses the monitor's first-available physical address,
  copies the supplied argument records, and initializes its helper state. iBoot's
  allocation high-water mark is insufficient because other components allocated
  memory before OS entry.
- **Local helper initialization:** the SDK explicitly says `libsptm_init` is a
  utility-library operation that does not enter SPTM. It consumes state supplied
  through monitor bootstrap arguments; it does not launch an absent monitor.
  Its state carries virtual addresses under an explicit shared-TTBR1 assumption;
  copying the record does not make those addresses valid in a new address space.

The SDK declarations provide these semantics; the public consumer shows the
corresponding call ordering. Full helper implementation source was not located.
The SDK-relative library directories checked from the public build recipe were
absent in both installed SDKs; that limited check does not prove no compatible
library exists elsewhere.
[Fixups consumer](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/sptm/start_sptm.s#L135),
[argument and helper consumer](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/sptm/arm_init_sptm.c#L752),
[later lockdown](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/machine_routines.c#L589).

## Original public comparator and remaining gate

The independently published `niklassheth/bootloader` guest-emulator implementation
at `98412d670862a6d1cd29c5e8f33439839ae3c7e6` allocates an 832-byte bootstrap record,
places helper version 10 at nested offset 416, and populates the selected outer
offsets above. Its synthesized cold/secondary register arrangement is useful
independent layout corroboration. Its role remains a guest XNU boot contract;
agreement with the SDK does not convert it into a physical resident-monitor
bootstrap or prove firmware acceptance.
[Pinned record producer](https://github.com/niklassheth/bootloader/blob/98412d670862a6d1cd29c5e8f33439839ae3c7e6/src/hv_sptm_boot.c#L566).

The original [entry snapshot and memory planner](../kernel/experiments/sptm31z-adapter/README.md)
therefore preserves 848 caller-supplied bytes privately and extracts only the
independently checked little-endian physical value at +24. All other fields remain
opaque. It requires separately qualified RAM bounds, page size, iBoot allocation
mark and reservations for allocation planning. It does not import the 832-byte SDK
layout or inspect opaque helper state.
Its explicit observation selector does not authenticate entry state, source
identity or a real monitor handoff.

The practical next input is a matching 25G83 producer/consumer declaration or
independently bounded evidence resolving the actual 848-byte record and helper
contract. Selected entry/registration/fixups facts can be compared now, while
original software validation remains offline.
Acceptance of an image, the real monitor-to-host transition, monitor-owned memory,
helper/exception lifecycle and physical-secondary observations remain separate
gates. These new interface facts support continued software investigation; they
establish neither a ready native workaround nor a requirement to wait for Apple.
