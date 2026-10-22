# After 31G: resolve the CPU1 reset-entry contract before another boot

2026-10-21. **31H is offline investigation only; no native controller is
ready, no restart requested, native 31H NOT RUN.** This plan supersedes old
readiness directions. Consumed 31A–31G controllers, manifests and receipts
remain unchanged, including the navigation documents pinned in 31G.

## What changed in 31G

The [M1 native report](attempt31g-2026-10-21-result.md), published in
`d99bdf3`, records all eight power-state reads completing without error:

| Observation | CPU0 actual | CPU1 actual |
|---|---:|---:|
| Before startup | 15 | 0 |
| After first start store | 15 | 0 |
| After second start store | 15 | 15 |
| Final sample | 15 | 15 |

**Observed:** CPU1's power-domain field responds after the second start
store. Both desired fields remain zero, including on the executing CPU0.
Do not change them to 15 in an attempt to correct this observation.

**Observed:** 95 complete recorder samples remained at phase zero; 95
reset/spin samples saw no reset record. CPU1 arrival, callbacks and Linux
SMP were not established. Macintosh HD return was confirmed at +56.513 s.

**Inferred:** a completely unresponsive CPU1 power domain is a weaker
explanation now. Reset release, the effective instruction destination,
incoming CPU1 memory/cache state and the first store remain unresolved.
Power state alone does not prove execution. CPU0's successful code readback
and translation checks do not establish CPU1's incoming environment.

## A concrete evidence gap found offline

The frozen [31A classifier](smp31_census.py) masks a register mirror with
bits `[47:12]` and retains lock bit 0. It discards bits 11:1 and 63:48.
Its `vectors / image_offset=0` result establishes **equal legacy bits47:12
page fields**, not an independently validated physical page or exact t6050
entry address. The classifier
already labels the register as a mirror, rather than effective reset proof.

An original synthetic regression demonstrates that `base | 1` and
`base | 0x801` produce identical frozen reports. The new offline classifier
retains the unknown fields while explicitly leaving the entry offset and
effective reset route unknown. Eight tests pass, including the actual
frozen classifier collision, input validation and unknown-bit coverage.
See [the offline experiment](../../kernel/experiments/smp31h-reset-format/README.md).

The exact installed boot021 layout has `_vectors_start` at image offset 0
and `_start` at `0x800`. Image and symbol digests were checked independently:

- boot021, 3,932,160 bytes:
  `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`
- Symbol table:
  `751a9643a2196eda44efba4789aa789465b2b75e9546be460946d2fa4c70ac11`
- Pinned m1n1 source: `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.

**Unknown:** whether bit 11 is meaningful, reserved or an address component
on t6050. The example is synthetic, not a recovered hardware value. Existing
public census results do not retain these bits; the local review found no
raw capture from which to reconstruct them. This is an information-loss
finding, **not a demonstrated wrong reset address**. Do not relocate the
recorder to `0x800` or write RVBAR based on this example.

## Work order on M5

1. **Resolve format and ownership.** Use REA/Ghidra in the existing isolated
   analysis VM to trace consumers/writers of the per-core implementation
   window and the raw boot path's secondary entry setup. Start with retained
   AppleARMPlatform/PMGR and SPTM findings, but distinguish the macOS
   XNU-to-SPTM contract from custom m1n1 startup. If iBoot/mBoot analysis is
   needed, first locate a matching, authorized artifact and establish its
   version. No matching main-CPU boot firmware was identified by the limited
   existing build-tree filename inventory; DCP `dcp_iboot` is not that artifact.
   No security-policy or boot installation change is part of this work.
2. **Repair observation precision.** In a new controller, classify the
   existing two preflight RVBAR reads without discarding unknown low fields.
   Report the legacy page relation, lock interpretation, a bounded low-bit
   class and presence of unknown upper bits, plus whether both mirrors
   match. Do not publish raw addresses/words. This can reuse existing reads
   without another target transaction. Frozen controllers remain untouched.
3. **Qualify one independent discriminator.** Public m1n1 uses CPU_IMPL
   `+0x100` in a stop-state wait, but t6050 semantics and suitable access
   width still need validation. It is not a PC or proved reset indicator.
   Add it only if source/binary evidence supports a narrowly defined read
   and interpretation. Alternatively, use a source-supported distinction
   between reset entry and cold entry. Do not scan debug registers or add
   speculative power writes merely to gather more data.
4. **Construct and review 31H.** Combine validated observations with the
   existing PS/entry evidence in one bounded session. Require a written
   outcome table showing which competing explanations each outcome resolves.
   Test bounds, access width, partial results, fault/deadline termination,
   and source/image binding offline. CPU1 alone; no automatic retries or
   Linux continuation on missing entry. A mocked controller validates
   software control flow; it does not emulate Apple's reset firmware.
5. **Publish only when informative.** M1 performs independent offline
   intake of the completed controller and publishes readiness. Only then
   ask for a fresh human lab start. No unchanged 31G rerun, longer polling
   timeout, or extra-core startup is justified by this result.

REA output and Apple bytes remain private under ignored build directories.
Publish original behavioral findings with artifact/function/offset provenance
and confidence. This review reused prior REA evidence; it made **no new REA
queries**, target calls, VM runs or firmware/security changes.

## Efficient path after CPU1 entry is proved

First establish bounded CPU1 callbacks, timer progress and a stable parked
state. Then make a separate Linux two-core test collect coherence, atomics,
IPI wakeups, per-core clocks, memory throughput and renderer latency together.
Validate one representative from each remaining cluster before all-core
operation. Use the already reviewed live topology: **12 Performance cores
(ADT M) and 6 Super cores (ADT P), three clusters of six**. Linux capacity,
frequency and energy policy must be measured, not inferred from core names.

All-core enablement is necessary but is not a guarantee that the current
software renderer will deliver macOS-class desktop latency. Keep input-to-frame
and menu-open measurements alongside CPU/memory tests; native GPU acceleration
remains a separate performance requirement. Storage and networking can follow
without reopening installation or security setup.

## M1 handoff now

Read [the offline hold instructions](../../tools/m1n1-client/attempt31h-instructions.md).
Preserve 31G evidence. Do not start another controller or restart either Mac
for this plan. No new image transfer is needed. M5 owns the next implementation;
M1 can independently review this evidence gap and report existing sanitized
evidence, without live hardware access.
