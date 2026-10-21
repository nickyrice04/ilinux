# 31E preparation: improve observation before another native attempt

> Historical offline-proposal milestone. Current native-controller scope and validation: [controller-review.md](controller-review.md) and [controller-validation.md](controller-validation.md).

2026-10-21. **Offline work; native launch HOLD.** This is not a new executable
native allowance. Preserve 31B, 31C and 31D sources, manifests and receipts.

## Decision from 31D

The M1's `37f25cb` report records both startup writes acknowledged, the two
diagnostic UART RAM bases cleared and published, and 171 sequential samples
without a CPU1 reset-table record. Controller elapsed 4.485 s; return to usual
Macintosh HD was recorded at +44.628 s. CPU1 arrival, timer requests and Linux
SMP were not established. This does **not** establish zero executed
instructions, the CPU's current PC, or the absence of a visibility problem.

Do not repeat the same start with a longer timeout. The next experiment must
separate earlier entry stages and have useful conditional work prepared if
arrival succeeds. The user's request to reduce reboot overhead is the reason
for finishing these tools before another native session.

## Confirmed observation defect

The exact boot021 image's `smp_secondary_entry` publishes its reset MPIDR
before its stack field, despite the opposite assignment order in C. The 31D
observer accepts stack-only publication but rejects MPIDR-only publication.
That defect did not trigger the reported 31D timeout: its samples remained
fresh. A future observer must accept both partial orders and still require a
complete matching identity once it observes the arrival flag.

The new pure classifiers and image audit are under
[`smp31e-entry`](../../../kernel/experiments/smp31e-entry/). The installed
image and consumed controller remain unchanged. Sequential samples must read
the arrival flag before the identities it validates; software may otherwise
misclassify a publication crossing the sample as corruption.

## Earlier observation candidate

The first C entry frame is stored before the UART calls, CPU initialization,
exception setup and reset-table publication. Exact compiled return addresses
can therefore identify remnants of several earlier frames without an Apple
binary modification or proprietary implementation.

The candidate uses the unused, already Device-nGnRnE-mapped shared-section
padding as a temporary diagnostic stack, with a proposed 48 KiB extent from
image offsets `0x94000` to `0xa0000`. That is a **layout change needing a
complete review**, not an approved native configuration. A normal cached stack
cannot simply be invalidated while another core might own dirty lines.

Required gates before integrating a native controller:

- Exact-image/source proof of ownership, mapping attributes, call-frame
  offsets, relevant memory-access alignment and reachable normal-path depth.
- Check actual entry-state assumptions separately from modeled inputs. A
  known normal-path bound does not bound recursive exceptions or unknown
  MMU-on console behavior.
- Independent lower-bound canaries and fixed read allowlists. Canaries can
  reveal damage after the fact; they cannot prove an unbounded path safe.
- Keep actual temporary SP distinct from the reset table's compiled normal
  stack value. The installed code still publishes the original dedicated
  stack top; that record does not prove which stack entry used.
- No MMU initialization, deep-idle reset/re-entry or Linux continuation on
  the temporary stack. Those paths still refer to the original stack and
  require their own transition design.

A matched frame remnant is not a current PC, a unique chronological trace or
proof a callee returned. No match does not exclude execution: frames are reused
and overwritten. An unknown register access or memory type is a reason to
stop the offline model, not to fabricate a successful response.

## Fresh REA evidence

REA 6.4.0 / Ghidra 12.1.4 ran in the existing diskless Linux lab. Both bounded
function bodies matched original carrier bytes and Apple LLVM instruction
words: **96 words total**, zero unknown LLVM instructions and no p-code outside
the bounded bodies. Raw binaries, decompilation and disassembly remain private
under the ignored build tree. These are static consistency results, not
runtime or whole-call-graph verification.

Carrier SHA-256:
`26ddfbe95c7e6ac9a76aedac424576bf00467e7c13da49dd82f8010efdb75093`.

| Function | Address | Bounded body | Original behavioral finding and limit |
|---|---|---:|---|
| `AppleARMCPU::startCPU` | `0xfffffe0008a51100` | 92 bytes / 23 words | This layer conditionally delegates through a platform object and returns success. Its indirect destination remains unresolved by this query; the method alone cannot establish the complete reset contract. |
| `AppleT6050PMGR::writeReg32` | `0xfffffe0009884dc4` | 292 bytes / 73 words | A special case filters map 2 / offset `0x298` for a nonzero die. A separate power-state validation path depends on a zero low nibble and a recognized power-state register; an eventual indirect dispatch remains. The existing CPU1 value `2` does not select that zero-low-nibble validation path. |

Member digests:

- AppleARMPlatform: `f8cba09002b9aa694750fcbd53370611801cce67cb030ccb5b8413cbb8fe6932`
- AppleT6050PMGR: `45e8d9c2663bdde29b7f71f8317d782983064a0a919a94c240bd194cf2bf143e`

Body digests:

- startCPU: `4237d1ef75f8a91287576be27a5b4c75db503b7089e721f9cca0467fec9eec06`
- writeReg32: `32140fc723672481cb2d177324ef7e976e6c8cbe76971d94286c16fe16214cda`

The existing extracted vtable independently identifies the dynamic predicate
as `isPsReg` and the conditional validation as `validateDevicePSLevel`.
Pointer-authenticated indirect dispatch and superclass collection fixups still
limit full resolution. No extra CPU1 power write is established by these two
functions. This is evidence to improve observation, **not** a proof that the
entire current startup sequence is complete.

## Preferred follow-up: recorder before stack setup

The stack audit identified a better alternative. An original **204-byte**
assembly recorder fits unused padding in the same first 4 KiB page as the
existing reset entry. The offline builder checks the exact original image,
padding, symbols, relocations, direct references and the overwritten instruction.
It produces two separate byte proposals: a branch at reset entry and the
recorder body. It never modifies the input image or contacts a target.

The recorder filters for CPU1, records entry phase, CurrentEL, masked MPIDR and
the SCTLR for the selected exception level, then replays the original entry
instruction and resumes the existing code. It changes neither SP nor LR and
uses no Apple-derived code. Barriers surround phase publication; they do not
prove cross-core cache visibility. A modeled read fault leaves a partial phase,
not an invented recovery or successful register sample.

This is the preferred implementation direction because it leaves the ordinary
C stack intact. The shared Device-memory stack and its frame collector remain
tested research components, **not a configuration to deploy**. Recorder source:
[`recorder.S`](../../../kernel/experiments/smp31e-entry/recorder.S); builder:
[`build_recorder.py`](../../../kernel/experiments/smp31e-entry/build_recorder.py).
Recorder SHA-256:
`9fa1f68b849a7049481cb1a83e645ccd43ca61a0d5df11d6bf7ca76dffd00335`.

Before this can become a native package, implement and review a bounded
publication adapter: verify the effective existing write alias and unchanged
page permissions; publish the stub before the entry branch; check exact bytes
and the complete cache-maintenance/barrier sequence; then use guard-free,
fixed-range record reads after startup. The public proxy dispatcher has DSB/ISB
at request completion; the C cache helpers alone omit them. No missing-barrier
defect is established in the frozen B–D controllers.

Do not relax a hardware protection if the code write is refused. A RAM-code
permission or publication failure before CPU1 start must be reported distinctly
from a CPU1-entry failure. A separately authorized boot-object replacement is
an alternative only if the existing image cannot support the reviewed RAM
route. No boot-object change is part of this handoff.

## Conditional next native session

After the implementation and independent review close the gates above:

1. Verify the fresh target, pinned image, RAM bounds, reset mirrors, USB link
   and existing CPU0 state. Record all allowed baseline observations first.
2. Prepare and verify the bounded early observer before the single CPU1 start
   transition. Preserve the exact two startup writes unless new evidence
   specifically requires changing them.
3. Sample early frame remnants, partial reset publication, spin identity and
   arrival within the independent arrival and total deadlines.
4. Only on verified arrival, run a predeclared bounded series of the existing
   installed timer callback; record monotonic progress, identities, errors,
   host-observed request latency and final park state. This is request-loop
   stability, not CPU throughput, Linux SMP or coherence validation.
5. Preserve all evidence and return to Macintosh HD. After uncertainty, do not
   retry, reconnect, guess a recovery operation or launch Linux from that state.

The offline [campaign planner](../../../tools/boot-campaign/README.md) exercises
these dependencies and stop paths. Its optional memory-echo phase is still a
design, not an implemented native callback. An emulator/model pass cannot
authorize physical hardware operations.

Once CPU1 entry and a valid Linux handoff are demonstrated, combine two-core
correctness, renderer threading, memory measurements and USB-link measurements
in one healthy Linux session. Expand across the actual cluster topology only
after those checks; stage read-only storage initialization last under its
separately reviewed allowance. N1 Wi-Fi protocol work proceeds independently.
See the [testing strategy](../../../research/testing-strategy-31e.md).
