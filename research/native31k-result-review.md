# Review of native31K and the next CPU step

2026-10-22. M1 report reviewed at `b820110`; execution `db9a79d`,
handoff `7043b17`. **31K is consumed. No physical31L campaign is released.**
This review and the accompanying tools make no hardware or macOS changes.

## What the run establishes

[M1's report](../native/boot/attempt31k-2026-10-22-result.md) and its sanitized
controller/supervisor results agree:

| Observation | Conclusion and limit |
|---|---|
| Connection, reset readback, translation probes and code publication pass | The existing connection fix works in this run. These checks concern CPU0's view; they do not establish CPU1's incoming execution context. |
| CPU0 control passes: 24 reads, two acknowledged stores, marker and canaries checked, original scratch restored | CPU0 can execute the returning helper and report its Device-memory stores. Its 14.136 ms includes transport and journaling, so it is not a CPU benchmark. |
| Both CPU1 start writes acknowledged; CPU1 power actual changes 0 to 15 and opaque implementation byte 0 to 2 | The start sequence produces a hardware response. Neither field establishes reset release, instruction execution, a program counter, or successful Linux startup. |
| Cold: 183 complete samples/732 reads. Vector: 91 complete samples/455 reads. Both phase zero with no committed identity | Neither software recorder publishes an attributable CPU1 marker. This does not mean every raw word was zero, nor does it prove that CPU1 reached neither candidate entry. |
| Stop reason `cpu1_arrival_observation_deadline`; no final state pair | The in-flight observation reached its bound. This is distinct from natural arrival timeout; it provides no new cause for the startup failure. Taking more reads after that stop would invalidate the bounded procedure. |
| Controller 5.439 s, supervisor 6.035 s; usual Macintosh HD confirmed at +64.898 s | The run ended within its bounds. No retry, reconnect, cleanup command, boot-policy or volume change occurred. |

CPU1 execution, callbacks, architectural park and native Linux SMP remain
unverified. The existing single-core Omarchy result is separate evidence.

## Audit of the first fetch and store

**Confirmed from exact original project code and the pinned public m1n1 source:**
both entry hooks are aligned and reach their intended recorder bodies. The
record addresses are computed relative to the executing instruction; the
checked sequences do not truncate this machine's high DRAM addresses. Both
recorders attempt their first marker store before reading a system register.

The CPU0 publication sequence cleans the complete bodies and invalidates the
instruction aliases. The pinned proxy dispatcher supplies DSB SY and ISB after
each opcode used by this publication sequence. No missing CPU0 publication barrier or wrong first-store encoding
was found. See pinned public
[startup](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/src/start.S),
[memory](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/src/memory.c)
and [proxy](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/src/proxy.c)
source. The original vector table also has fifteen other slots: observing slot
zero does not observe every possible exception path.

**Unknown:** CPU1's effective entry, instruction visibility, EL, translation
regime, record permissions and store visibility. The two negative recorders
share address-generation and store assumptions. They are correlated evidence,
not two independent exclusions of entry paths.

**Hypothesis, not a diagnosed fault:** a CPU1 Normal-cacheable store might remain
private while CPU0 reads the record through a Device mapping. STR followed by
DSB does not itself clean a dirty cache line. Adding DC CVAC is not an established
fix: translation and execution must already work, higher-level controls can
trap the operation, and mixed memory attributes need an explicit coherence
contract. Arm documents the HCR_EL2.TPCP trap control in
[DDI0615](https://documentation-service.arm.com/static/649ae5b238511951cb799288).
The vector record also shares a 128-byte line with startup state; a future
clean-based experiment would need to own the full affected line. The machine's
128-byte line size is recorded in [the inventory](../hardware/hardware-inventory.md).

## How the offline work saves physical attempts

The new original [entry-contract checker](../kernel/experiments/smp31l-analysis/)
decodes the exact hook and first-store instructions, checks synthetic high
addresses and aliases, and compares explicitly supplied incoming-state cases
with the actual31K observation. Mutated instructions and malformed evidence
must fail. Its result states that the cause and effective entry remain unknown.

This is a software checker, **not a firmware, cache or Apple CPU emulator**.
Supplying a hypothetical translation or invisible store demonstrates ambiguity;
it cannot prove that the hardware used that state. It does let us reject bad
address calculations and overconfident interpretations without another reboot.

The fresh [REA investigation](native31l-entry.md) follows the firmware entry
value and checks whether a production-safe independent observer exists. Apple
bytes, disassembly and decompiler output remain in ignored local storage;
public records contain behavior, provenance and validation limits only.

## Decision and remaining work

Keep physical31L on hold until the experiment can separate at least one of:

1. The core was not released to the intended entry.
2. It fetched a different entry or different instruction bytes.
3. It reached our code but failed before an observable store.

A firmware-supported entry contract or an already accessible, nonintrusive
status accessor could supply that distinction. An ADT register window alone
does not. Public XNU's
[CoreSight setup](https://raw.githubusercontent.com/apple-oss-distributions/xnu/main/osfmk/arm64/cpu.c)
skips ED/UTT on production configurations unless debug is enabled, and contains
explicit unlock setup. The architectural
[EDPCSR specification](https://support.arm.com/documentation/ddi0601/2026-06/External-Registers/EDPCSR--External-Debug-Program-Counter-Sample-Register)
also makes availability, lock/power state and read side effects material. No
debug unlock, halt, authentication write or blind PC read is proposed.

Once CPU1 demonstrably enters original code, the next engineering batch is a
two-core Linux test of coherency/atomics, timers/IPIs, frequency and memory
performance, followed by renderer and input latency. Then expand through the
two Performance clusters and the Super cluster: this machine has **12
Performance and six Super cores**, not an assumed efficiency-core topology.
Networking, storage and GPU acceleration remain necessary for the usable
Omarchy target; successful SMP alone will not establish macOS parity.

M1 should follow the new [offline instructions](../tools/m1n1-client/attempt31l-instructions.md).
No fresh proxy session, image installation, M1 restart, repeated policy check
or reuse of a consumed native runner is needed for this review.
