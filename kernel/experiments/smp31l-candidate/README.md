# 31L candidate review: first fetch and preparation

2026-10-22. **Original Normal-first candidate implemented; release status lives in the M1 handoff.** This review
uses public pinned m1n1 source, exact boot021 bytes, sanitized hardware results
and behavioral research notes. It does not use Apple decompiler output. No
target command, VM, firmware change or macOS write was performed.

## Boot021 does not normally start CPU1 before the proxy

The package manifest describes an unmodified m1n1 build with no appended
payload. The exact 3,932,160-byte image ends at `_payload_start = 0x3c0000`.
The installed image SHA-256 remains
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`;
symbol SHA-256 remains
`751a9643a2196eda44efba4789aa789465b2b75e9546be460946d2fa4c70ac11`.

Public source at commit `57a9339ffd1876e78297b17d34dece8cff8fa1ba` separates
initialization from starting cores:

| Path | What it does | Startup consequence |
|---|---|---|
| `m1n1_main` in `src/main.c` | Calls `smp_init` after MMU/AIC initialization, before PMGR/display setup and `run_actions`. | No direct secondary-start call. |
| `smp_init` in `src/smp.c` | Enumerates ADT topology, records the boot CPU, initializes its shared slot and derives start-register addresses. | Does not call `smp_start_cpu` or write CPU-start registers. |
| `run_actions` in `src/main.c` | Calls `payload_run`, then opens the proxy when no bootable payload succeeds. | The bare image follows the no-payload path. |
| `payload_run` in `src/payload.c` | Calls `smp_start_secondaries` only in the `kernel && fdt` branch. | A different appended-payload boot can start cores; the pinned bare image has no such appended payload. |
| `P_SMP_START_SECONDARIES` in `src/proxy.c` | Explicitly calls `smp_start_secondaries`. | Requires that proxy request; 31K's custom controller does not issue it. |

An independent bounded scan of exact boot021 direct BL instructions corroborates
the source calls: `m1n1_main` calls `smp_init` at offset `0x256dc`; `run_actions`
calls `payload_run` at `0x255d4`; the payload-only call to
`smp_start_secondaries` is at `0x29f94`. The checked function ranges were
`0x255c0..0x25620`, `0x25620..0x257c0`, `0x30f00..0x31480`, and
`0x29ea0..0x2a1e0`. A direct-call scan alone is not complete interprocedural
proof; the bounded source conditions and exact package composition are also
needed. The scan is of public m1n1 bytes, not Apple code.

The 31K wrapper constructs the transport/proxy directly and never imports the
automatic client `setup` module. Its CPU1-start accounting covers its explicit
campaign operations. It does not count arbitrary earlier Apple boot-firmware
activity. A zero spin-table flag means no completed m1n1 handshake was observed;
it is not a measurement that CPU1 has never executed any instructions.

**Consequence:** there is no evidence that boot021 previously ran CPU1 through
its original vector page and left that code in CPU1's cache before our RAM
hooks. That specific stale-code explanation is weaker than it would be if
m1n1 started and stopped secondaries before proxy. It does not exclude earlier
firmware use of CPU1, retained unknown state, incomplete reset release or
different incoming translation. Firmware's boot-CPU cleanup/handoff cannot be
assumed to be the secondary-reset path; EL1-named registers can also alias EL2
host state under VHE. See [the ongoing findings](../../../research/native31l-entry.md).

## Existing observations already precede most software prerequisites

The vector and cold recorders use only a branch, PC-relative addressing,
immediate construction and an aligned RAM store before their first marker.
They do not first call `init_cpu`, establish a stack, read MPIDR/CurrentEL,
enable the MMU, configure per-core Linux state or invoke a driver. No missing
late `init_cpu` routine explains a missing first marker **if** the instrumented
prefix was fetched and its first store was permitted and observable. Those
antecedents remain unproved.

Moving another marker into freshly owned code is not sufficient: CPU1 must
first fetch the changed branch and reach that code. Executing the new code on
CPU0 would validate CPU0 instruction publication, not CPU1's first fetch.
CPU0's existing cache-maintenance proxy operations already end with DSB SY and
ISB. Its ISB does not establish CPU1 context synchronization. There is no
demonstrated omitted CPU0 barrier to repair.

## Candidate mechanisms and their actual discrimination

| Candidate | Positive result could establish | Unresolved premise or failure | Decision now |
|---|---|---|---|
| Marker in the same page as executable entry | A store reached that page and became visible. | The executable page can be read-only; a store fault could precede all later evidence. Cache publication remains unknown. | Do not use an executable-page store as a supposedly independent first-fetch test. |
| Separate Normal-memory record followed by the existing Device record | A Normal-only committed CPU1 identity would demonstrate execution plus a difference in observation paths. | Incoming CPU1 mapping/attributes are unknown. A first Normal-store fault prevents the later Device marker; CPU0 cached polling can miss MMU-off Device-style stores. | Potentially informative only after the record mapping and observer contract are independently justified. Not currently a released change. |
| Explicit cache clean after the first store | A subsequent committed marker could support that a visibility prerequisite mattered under that run's state. | Cache-maintenance permission, translation, completion and PoC reachability are unknown; it can trap. A negative outcome remains ambiguous. | No blind clean added. Use the offline injected hypothesis only. |
| Early exception recorder | A committed CPU1 identity plus syndrome and faulting-PC classification could locate a failure before the regular marker. | Incoming VBAR/EL ownership and a safe visible record are unknown. Replacing shared CPU0 vectors can break the guarded proxy; normal exception prologues can fault on an uninitialized CPU1 stack. | Do not change VBAR or shared exception paths without attribution and safe CPU0 chaining. |
| Fresh RAM recorder reached by a changed hook | Instruction execution at that recorder if an identity commits. | Its branch and record still rely on the same unproved incoming context. | Fresh code/cache lines alone do not remove the original ambiguity. |
| Qualified passive status or documented preparation step | A read could distinguish held/reset-released state, or a preparation change could test a concrete missing prerequisite. | Requires T6050-specific register ownership, width, side effects and ordering. ADT windows and legacy meanings are insufficient. | Highest practical value if the REA/source investigation establishes the contract. |

The Normal-record candidate is deliberately not called independent hardware
proof. To make it useful, its design must specify an owned writable range,
CPU0 mapping and observation sequence, potential CPU1 attributes, freshness,
identity-commit ordering and all cache-maintenance effects. It must avoid
invalidating a potentially dirty CPU1 line through an unproved cross-core
maintenance contract. A CPU0 positive control cannot fill these gaps.

Any future exception candidate needs to preserve CPU0's original register and
exception behavior. Reading MPIDR to decide whether an exception belongs to
CPU1 already consumes a register, so a stackless hook cannot casually branch
back to CPU0's original handler with unpreserved state. The current early
shared-vector layout does not offer a proven scratch-register convention for
all sixteen entries. A terminal spin is not an architectural park, and a phase
written just before it does not prove the spin was reached.

## What should qualify the next physical campaign

Prefer one supported preparation/first-fetch distinction over accumulating
equivalent markers. A concrete proposed change needs these items before a
controller is released:

1. A behavior finding that identifies the exact prerequisite or observation,
   with bounded source/binary provenance and confidence. Do not infer CPU1
   state from the successful boot-CPU handoff.
2. An original implementation with fixed ownership and addresses derived from
   validated live topology. Keep CPU1 as the only secondary target, preserving
   the machine's twelve Performance/six Super classification.
3. Explicit outcomes: what a positive observation proves, what a negative
   observation leaves unresolved, and where every fault stops. Merely moving
   the same phase-zero timeout is not a new discriminator.
4. Exact-image/instruction checks and a fault-prefix model that includes
   unknown entry, stale fetch, translation/permission failure, private-dirty
   visibility, unexpected CPU0 arrival and bounded loss of the proxy.
5. A single supervised session with the existing connection/source gates,
   unchanged independent human deadline, no cleanup/retry after a fault, and
   immediate return to Macintosh HD on outcome. No automatic Linux launch is
   added to an unverified CPU1 experiment.

Once CPU1 entry is established, the following experiment can use its observed
contract to validate callbacks/park, then two-core Linux coherence, atomics,
timer/IPI and renderer behavior together. That is where batching can save
boots without conflating unknown first fetch with Linux scheduler problems.

For now, the actionable offline result is the elimination of an unsupported
"boot021 already started CPU1 before proxy" premise and the candidate contracts
above. This historical review did not by itself justify a startup-register patch. The bounded visibility test below is a different engineering decision.


## Implemented31L Normal-first hypothesis test

A bounded experiment does not require every incoming CPU1 state to be known.
It must distinguish a useful positive outcome and state the limits of a negative
one. The implemented candidate tests whether a record in CPU0 Normal memory can
make CPU1 execution visible when the existing Device records have not done so.
This is a hypothesis test, not a confirmed cache bug or startup fix.

Two60-byte original prefixes at image offsets0xc00 and0xd00 use x8/x9 only.
They materialize a full64-bit address, write phase1 before MRS, store low24 MPIDR
at record+8, then commit phase2 before branching to the existing vector/cold
recorder at0xa00/0xb00. x0,SP,LR,NZCV and other registers are preserved. No
MMIO/cache/system-register write is present. The existing records remain in
place; a failed Normal store can prevent reaching them.

The already owned16KiB helper allocation supplies two64-byte records at+0x1000
and+0x1080, on separate128-byte lines. The CPU0 control uses+0x1100. No new
allocation, guessed static-data ownership, remapping or reset redirect occurs.
The controller verifies CPU0 Normal write-back attributes, initializes and
cleans these ranges before any start, and runs the existing returning store
leaf against the separate Normal control. No record clean/invalidate occurs
after a start intent. The same two CPU1 start writes and bounded supervisor
remain. Every visible prefix, including an uncommitted nonzero identity, stops;
only identity preceded by phase2 is attributed to CPU1. No callback follows.

A positive committed CPU1 identity proves this prefix executed and became
visible. It does not prove reset provenance, that the subsequent branch ran,
or that Device visibility caused the historical failure. The first positive
stops before a new comparative Device sample. A negative result still permits
no fetch, another entry, an incoming mapping fault or unobserved stores. CPU0
cached polls may miss MMU-off/noncoherent writes. CPU0's control cannot prove
CPU1's attributes.

`audit.py` binds exact boot021 and optional symbols, unused padding, bounded
references and relocations. `builder.py` generates original instructions;
`model.py` tests supplied visibility/fault assumptions, not Apple firmware.
`prefix.S` is independently assembled for five synthetic helper addresses in
VM071 and compared against both generated prefixes. No proprietary code is
part of these files. Full validation and release status:
[31L handoff](../../../tools/m1n1-client/attempt31l-instructions.md).
