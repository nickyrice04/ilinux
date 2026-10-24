# 31X — context ownership and the event-wake discriminator

**The retained firmware identifies a real monitor-context initializer, but it
runs after entry has already begun. It does not supply an operation that makes
a non-executing CPU1 start. The checked wait loops also do not support a
post-start event as a fix. No native workaround or Apple-only impossibility is
established.** This is a focused CPU-only investigation; no hardware action,
security change, monitor replay or new native adapter was performed.

The useful new distinction is between **initializing an executing monitor** and
**getting a secondary to its first instruction**. The former now has an identified
owner in the retained image. Treating it as the missing latter operation would
produce an invalid experiment.

## Questions and actual results

The proposed context hypothesis was that the early monitor path needs a prepared
context before its indirect dispatch, potentially exposing a missing startup
condition. Bounded instruction checks first rejected a nearby cache-maintenance
helper as the target: it follows dispatch and does not qualify as a prerequisite.
It was not queried with REA.

Two isolated queries then ran against the byte-identical SPTM Mach-O pinned in
[31W](native31w-firmware.md), SHA-256
`da2ad8d4ecbf3e29fbaaa07e8c7d291ed20d296044494e00303c7a780d190666`:

| Query | Result | Evidence limit |
|---|---|---|
| Low-level entry `0xfffffff0270a0000` | CLI1 in22.170seconds; provider reports no procedure at that address. | Refusal retained. No invented function body or forced retry. |
| Its direct initializer `0xfffffff0270ee12c` | CLI0 in22.685seconds; returned entry matches. | Provider body8,532bytes/2,133instructions;3,000P-code operations, **truncated**, with removed-block warnings. Whole-function pseudocode is refused. |

Root-owned VM setup succeeded in both batches; job exits were1 and0 respectively.
Both guests exposed only loopback and no physical USB. This is one successful
function query and one refusal, not two successful decompilations.

Independent LLVM checks cover **474words /1,896bytes, zero mismatches** across
four bounded ranges. Of these,283 are outside earlier published checked ranges
and191 overlap them. The large returned initializer body was not independently
decoded in full. Earlier full-image private disassembly already existed; these
counts measure bounded verification, not previously unseen firmware or physical
CPU progress. [Validation](../reverse-engineering/findings/cpu-startup31x/validation.json)
records both outputs, bounds, hashes and refusal flags. All31W/prior evidence
remains frozen.

## The context owner is downstream of execution

**Confirmed bounded static facts:** the early path calls the initializer at
`0xfffffff0270a0198`. The initializer's checked prefix examines typed handoff
metadata, then installs the monitor context in `TPIDRRO_EL0` at
`0xfffffff0270ee550`. The caller later reads that context at
`0xfffffff0270a01f0`; its indirect dispatch at `0xfffffff0270a0270` obtains a
target through a pointer field at context offset24.

This resolves the owner of that context on the checked path. It does **not**
qualify the complete input layout, all validation branches, object lifetime,
permitted callable interface or the path's physical-secondary/reset role.
The low-level entry itself remains unrecognized as a provider procedure, and
the initializer's truncated P-code cannot establish those broader claims.

The initializer is reached only after instructions in the monitor have already
executed. Its context installation therefore cannot, by itself, explain how to
make CPU1 reach the first instruction of a raw payload. It is not a substitute
for the accepted native host bootstrap or evidence that this monitor was resident
in the failed raw boots. Nor is it a command that the running raw payload is
shown to be entitled or able to invoke.

The compatible alternate-route prerequisite is more precise: **an accepted host
must reach the monitor's declared entry with its valid initial context and memory
preparation, and its physical-secondary path must be identified.** The declared
entry from31W differs from this low-level internal path; jumping directly to the
latter would omit an unqualified contract. The
[31X public-source audit](native31x-upstream.md) likewise distinguishes registering
an already executing guest CPU from physically releasing a host secondary.

## Does a missing event explain the stalled core?

Root's independent launcher audit raised a concrete hypothesis: an event emitted
before power-on might be lost, leaving a firmware holding pen waiting after the
start stores. Its prediction is a reachable event-wait path whose exit condition
can lead to payload entry after a later event. This pass checks the relevant
retained code rather than assuming every wait is such a holding pen.

**Confirmed bounded negative result:** there is no event-wait instruction in the
independently checked direct-entry instruction interval before the indirect
dispatch. This does not cover every transitive callee, including the initializer
beyond its checked prefix. Three nearby/relevant waits were independently decoded:

| Image / link-time wait address | Checked behavior |
|---|---|
| SPTM `0xfffffff0270a02d4` | Unconditional back edge to the same wait, with no intervening exit test. |
| SPTM `0xfffffff0270af514` | Unconditional back edge to the same wait, with no intervening exit test. |
| mBoot final trampoline `0x100c1aeba50` | Unconditional back edge to the same wait, with no intervening exit test. |

A single event could wake one iteration but would not advance any of these loops
to payload entry. The mBoot site is the sole aligned event-wait encoding in the
retained decoded image, and its code membership is independently checked.
The SPTM site near the31W primary entry lies outside that provider's reported
body; it is separate bounded evidence, not a repair of31W's removed-block refusal.

Thus **the holding-pen explanation is falsified for these three loops**. It is
not falsified for ROM or every unobserved firmware path. CPU1's effective PC is
still unknown. This evidence neither qualifies a post-pair event as a fix nor
proves that an event has no possible effect anywhere. No event or IPI was sent.

## Implementation decision and exact missing evidence

**No established behavior in this pass enables a useful original physical-start
implementation.** The initializer is a downstream context owner, while the
checked event waits do not have the required wake-to-entry behavior. Building a
new caller or register sequence from either result would assume the missing
causal link. Synthetic tests would not supply it.

Two concrete routes remain distinguishable:

1. **Alternate accepted host:** obtain an applicable host revision and accepted
   boot-object/initial-context description, with evidence that its physical
   secondaries entered. The retained primary and internal contexts can then be
   compared against that actual bootstrap. A guest CPU count or guest-register
   table is insufficient.
2. **Raw-path repair:** identify a missing prerequisite that precedes CPU1 entry,
   with a reachable owner and observable prediction. For the event candidate,
   this specifically means evidence of a flag-tested holding pen or a qualified
   effective-PC/fault observation that places CPU1 on such a path. If the known
   unconditional waits are the alleged target, that candidate already fails.

The present result rules out misleading implementation targets without claiming
that every software route is impossible. A firmware defect remains plausible;
an Apple-only dependency would additionally require evidence that the necessary
state cannot be established through any applicable accepted software path.
Those premises have not been shown.
