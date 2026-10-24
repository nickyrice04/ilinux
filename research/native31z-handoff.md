# 31Z — local monitor handoff and boot-CPU registration

**The local kernel now qualifies a narrow cold-entry snapshot contract and the
argument source for boot-CPU registration. The implemented helpers cover the
snapshot, one physical-boundary field and physical-memory planning; CPU-registration
planning and validation are not implemented. Its 848-byte monitor argument copy
matches none of the installed SDK profiles measured in this pass.** A full native
monitor adapter is still unqualified, but the remaining work is more specific
than an unavailable third-party host.

This is offline analysis. No monitor call, secondary start, image installation,
security change or external contact occurred. The original implementation is
separate from the private Apple analysis. The
[SDK/public-source comparison](native31z-public-contract.md) owns the header
measurements and public lifecycle requirements; this note records the local
consumer evidence and its limits.

## Provenance and actual REA outcomes

The retained `kernel.release.t6050` is17,168,528bytes, SHA-256
`2bd94a6fcff6203861e46b39920c16e1b5563d9bb17405b8a42c59c2ef4486e0`.
A new read-only comparison finds it byte-identical to the current installed
standalone T6050 kernel. Current OS metadata is macOS26.6.2/build25G83; the
retained kernel's generic build metadata identifies Darwin25.6.0,
XNU12377.161.14/T6050. This strengthens **current kernel-consumer provenance**.
It does not refresh the historical lab boot chain, its accepted object, runtime
monitor identity or failed raw-boot context.

The Mach-O is arm64e `MH_EXECUTE`. Its `LC_UNIXTHREAD` entry is
`0xfffffe0007ca0000`, within `__TEXT_BOOT_EXEC`. Addresses below are link-time.

| Batch / request | Actual outcome | Qualification |
|---|---|---|
| A: cold consumer `0xfffffe00074f6114` | CLI1,100.652s; provider `cancelled` | No function dossier.100s deadline honored within cancellation overhead. |
| A: static helper `0xfffffe0007ca4a34` | CLI1,100.674s; provider `cancelled` | No function dossier. No longer timeout or forced function was used. |
| B: bounded-carrier cold consumer | CLI0,17.769s;607 instructions /2,428bytes |3,000 P-code operations, truncated;87 outside body, removed-block and bad-instruction warnings. **Whole-function pseudocode refused.** |
| B: bounded-carrier topology consumer `0xfffffe0007506f80` | CLI0,17.427s;856 instructions /3,424bytes |3,000 P-code operations, truncated; none outside body. **Whole-function pseudocode refused.** |

Root-owned VM setup succeeded twice; job exits were1 then0. Both guests exposed
loopback only and no physical USB. Four requests yielded two cancellations and
two completed, limited dossiers—not four successful analyses.

Batch B used an analysis-only carrier, SHA-256
`f694d388c82842c2b3581681392c9e6c1dddc9b606780d6249ce48dd19511cf9`.
Four copied code ranges total38,688bytes. Every copied byte, original VA and
source file offset matches the full kernel. Header, filtered function-start
metadata and analysis labels are generated; other code/data and external-call
context are absent. This carrier is neither the original kernel nor a deployable
image. Its limited context cannot justify whole-program conclusions.

Independent LLVM/source checks cover **1,672 instruction-sized words /
6,688bytes, zero mismatches**, across six explicitly bounded ranges. The full
cold `LC_FUNCTION_STARTS` span includes seven words omitted from the provider's
body; byte verification does not repair that refusal or qualify their semantics.
The [validation record](../reverse-engineering/findings/cpu-startup31z/validation.json)
retains all query outcomes, mappings, body gates and hashes.31Y and prior records
remain frozen.

## Cold entry: selected fields, not an invented full structure

The declared entry compares the **full64-bit** incoming reason with4 and0.
These select panic and cold paths respectively, consistent with the measured
SDK enum. This is not evidence that the entry validates every possible reason;
an original classifier's rejection of unknown values is its own explicit policy.
The public meaning of secondary/warm/hibernation reasons is retained separately.

On the checked cold path, incoming x1 and x2 survive the boot helpers and become
the C consumer's first and second arguments. That consumer copies **1,152bytes
from the boot-argument pointer** and **848bytes from the monitor-argument pointer**
through the exported memory-copy implementation. The copy sites are
`0xfffffe00074f6178` and `0xfffffe00074f6198`.

The straight-line prefix independently establishes these selected monitor fields:

| Offset / width | Local observation | Narrow semantic qualification |
|---|---|---|
|24 /64bits|Read at `0xfffffe00074f61b0`, forwarded unchanged at `0xfffffe00074f61c0`.|Both measured SDK families identify this as `first_avail_phys`; pinned public XNU assigns that physical allocation boundary in the same cold sequence. |
|408 /64bits|Read and forwarded immediately before the preceding field.|SDK/public comparison identifies the monitor panic-Boolean pointer. No dereference or lifetime guarantee is inferred here. |
|416 /pointer to subobject|Passed to the local library initializer at `0xfffffe00074f6288`.|Agrees with the SDK/public library-state position. This is library initialization, not monitor activation. |

The first field can support an original **exact-kernel-bound accessor for one
unsigned64-bit physical boundary**, with caller-validated snapshot length and
address-domain constraints. It does not independently establish usable RAM,
ownership of all later addresses, alignment, the rest of the structure or safe
allocation on hardware. Copying a monitor snapshot also does not establish that
its pointers are safe to dereference.

The complete layout remains a hard gate: SDK26.5 physical/virtual profiles are
832/840bytes; measured SDK27 physical profiles are856/872bytes depending on MTE.
None is848. Selected offset agreement does not authorize padding the older
structure, importing the newer version field or extrapolating unconsumed fields.
No matching complete outer version/layout was identified. Keep the local snapshot
opaque except for separately qualified fields.

The checked cold sequence also orders image-fixup and static-interface helpers
before final vector-base installation (`0xfffffe0007ca007c`), instruction
synchronization, and dispatch identifier15 (`0xfffffe0007ca0084`), followed by
the C consumer. The SDK/public comparator identifies15 as fixups completion.
This qualifies an ordering constraint for future integration; no lifecycle
validator or privileged transition is implemented, and successful monitor
acceptance is not established.

## Registration is a boot-CPU prerequisite, not guest bookkeeping

The local direct chain is:

1. Cold C consumer calls topology routine `0xfffffe0007506f80` at
   `0xfffffe00074f6478`.
2. That routine invokes the40-byte dispatch stub `0xfffffe0007c78f94` at
   `0xfffffe0007507110`.
3. The stub selects identifier14, matching the SDK's real `REGISTER_CPU` entry.

The argument is independently bound to topology: the property-helper call at
`0xfffffe0007507290` uses the public property name `reg`; its low32-bit result
is stored in the CPU record at offset4. The registration site reloads that
32-bit field into the ABI argument. Thus the local call **zero-extends the
device-tree affinity value**. For the retained CPU2 topology this value is2,
not the diagnostic low24 MPIDR expectation `0x40002`. The local warm continuation
also masks MPIDR to `0xffff` before its CPU-data lookup, independently corroborating
the exclusion of Aff2 class bits from that identity.

The SDK contract says the real monitor's registration occurs on the **boot CPU**,
before machine lockdown, for the supported CPUs, with the boot CPU first; call
order assigns logical IDs. Its API has one64-bit physical-ID argument and no
return value. CPU-data addresses and exception-stack pointers are not arguments
to this call. Public XNU fills the32-bit field from mandatory ADT `reg` and walks
ADT order; no boot-first sorting step was found. A future original registration
planner should validate order and uniqueness rather than silently reorder evidence.
No such planner or validator is implemented in31Z. The local
cold call is established; ordering relative to every possible monitor lockdown
path is not independently proved by these bounded bodies.

This is a material correction in scope. Earlier located **guest emulator**
registration only populated an in-memory table for an already executing guest.
That evidence remains valid for those implementations. It does not describe
this real monitor API. Conversely, identifying the real API does not show that
the failed historical raw boots had a resident monitor or lacked this one call.
There is no qualified instruction to invoke it from the raw environment.

## What original work is enabled

The [original offline component](../kernel/experiments/sptm31z-adapter/README.md)
classifies and preserves raw entry arguments, retains an opaque848-byte local
snapshot, exposes the independently qualified physical-boundary field, and plans
physical-memory extents from independently qualified bounds and live reservations.
Synthetic tests validate those helpers, not firmware execution.

The boot-first registration order and explicit32-bit ADT affinity source are
qualified requirements for future work. No registration planner, registration
validator, lifecycle validator or monitor call is implemented.

A native adapter still needs the complete matching monitor handoff and memory
contract, permitted initial execution environment, fixups/exception lifecycle and
per-CPU continuation setup. The public continuation establishes stacks after
monitor entry; it is separate from CPU registration. Neither these helpers nor
the31Y parser fixtures supply that complete host. **No native image or boot test is
ready.** A software route is better specified; a working workaround and an
Apple-only necessity both remain unproved.
