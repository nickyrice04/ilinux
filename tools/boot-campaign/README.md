# Offline boot-campaign planner and report replay

This original standard-library tool helps review a larger test session before
spending another physical reboot on it. It has **no USB, shell execution,
native adapter, firmware loader, reset/retry or hardware-resume function**.
Its output is a design and evidence report, never a replacement for the
source-pinned native controller or its human start/return procedure.

## Use

From the repository root, on macOS or Linux:

```sh
python3 -I tools/boot-campaign/campaign.py plan
python3 -I tools/boot-campaign/campaign.py history \
  native/boot/attempt31d-controller-2026-10-21.json
python3 -I tools/boot-campaign/campaign.py replay \
  tools/boot-campaign/fixtures/synthetic-partial-entry.json
python3 -I tools/boot-campaign/campaign.py --format json replay \
  tools/boot-campaign/fixtures/synthetic-success.json
python3 -I tools/boot-campaign/test_campaign.py
```

The tool only reads bounded JSON files and writes its result to stdout. Invalid
input returns exit 2 with a fixed error, without reflecting private input or
file paths into the output. JSON output is suitable for a later report
aggregator. A new instance always starts at fresh identity; importing a prior
report cannot continue a powered-on hardware session.

## The higher-information session it models

The current CPU1 design budgets at most 49 seconds for nine stages, with a
5-second controller-exit margin inside a 60-second controller budget. This
margin is not an estimate or guarantee of the time to reboot into macOS. These are
**planning limits**, not measured latency predictions or guaranteed native
execution times. The existing independent human return timer remains separate.

1. Check this machine, installed image, fresh CPU state and USB transport.
2. Capture the allowed RAM and reset-mirror observations before changing state.
3. Prepare and verify a bounded earlier-entry observer.
4. If implemented and reviewed, capture CPU0 features, timer baseline and RAM
   layout in the same pre-start session.
5. Dispatch one CPU1 start transition, retaining intended/attempted/acknowledged
   counts separately. Two acknowledged writes do not establish execution.
6. Read entry progress and verify CPU1 identity/arrival.
7. Only after arrival, complete the bounded timer-request pair.
8. If implemented and reviewed, exchange a bounded RAM payload and check it.
9. Observe the agreed parked state and return to macOS.

Optional measurements can be skipped only as **unsupported**, before executing
an unimplemented operation. Fault, timeout, missing mandatory checks or lost
transport closes the campaign and skips dependent stages. A late success is
still a timeout. Absolute elapsed time must be monotonic and include gaps
between stages; those gaps count toward the controller budget. There is no second CPU-start transition or automatic retry.
A payload echo is not proof of all cache-coherency cases; timer reads do not
prove timer interrupts or Linux scheduler/IPI behavior.

This allows one eventual session to collect several compatible measurements
before the risky transition, and several bounded checks after a verified
arrival. It does not combine unknown hardware operations merely to increase
the test count. A `read_only` stage label is a workflow classification, not
proof that an arbitrary register is safe to read. Each native observation
still needs an allowlisted implementation and review of its side effects.

## What exists and what does not

Implemented:

* A deterministic bounded state machine with stage prerequisites and one
  CPU1 transition.
* Provenance on every recorded capability: synthetic, native report, VM report
  or static analysis; boot labels cannot be mixed.
* Safe history summaries for the published 31B, 31C and 31D final records.
* Synthetic success and early-marker timeout scenarios, plus failure injection
  at every stage and tests for lost/late replies, skipped optional checks,
  invalid input and attempts to reuse evidence from another boot.

Not implemented: native stage adapters, the early-entry observer, hardware
emulation, CPU start beyond the current controller, Linux continuation or
all-core scheduling. Every proposed stage is marked
`requires_separate_native_review`. No physical restart should be requested
on the strength of this tool's `MODEL_OR_RECORD_COMPLETE` output.

Before connecting a future controller, bind each stage to a fixed reviewed
operation and exact artifact digests. Record entry markers, exception data and
start intent in that controller; never infer them from a model. Persist the
reported evidence for diagnosis, but perform fresh identity/state checks on
any new boot. Future two-core Linux testing should batch CPU/memory correctness,
timer IRQ/IPI behavior and renderer measurements only after its separate
handoff contract is ready. That is outside this CPU1 campaign's transition
budget.

## Why this is useful without claiming firmware emulation

The existing controller models can prove that our code refuses the wrong
machine, handles partial progress and bounds its waits. A general ARM64 VM can
compile and execute Linux/user-space code. Neither tells us what the t6050
reset logic, PMGR, Apple-specific system registers, physical interconnect or
UART FIFO will actually do. Modeling an unknown response as “success” simply
bakes the desired answer into the test.

The useful loop is: capture a reviewed native observation, preserve its exact
meaning and uncertainty, add it as a replay/model constraint, and move more
failure-handling checks offline. Keep the few unresolved hardware questions
for a separately instrumented physical run. This reduces avoidable attempts;
it does not eliminate the need for hardware validation.

## Evidence fixtures and test results

The three `fixtures/31*-controller.json` files are byte-for-byte copies of the
already public final controller records under `native/boot/`, not raw private
receipts. `fixtures/sha256.json` records their and the synthetic fixtures'
digests. No per-stage timing was reconstructed from the native final summaries:
they lack those measurements. The history importer keeps CPU1 execution
**unknown**, even for the two attempts that acknowledged both start writes.
31D's 171 sequential samples are not an atomic snapshot or program counter.

The history importer checks the known manifest and outcome fields to catch
accidental fixture drift. These ordinary JSON checks are not cryptographic
attestation that the hardware executed a stage; the public native report is
the source of the historical claim.

2026-10-21: **21 standard-library tests PASS** on the macOS host, including
27 failure injections (three failure classes at each of nine stages).
No VM, native controller, USB connection or hardware operation was run by this
work. The synthetic success fixture is not a native CPU1 success record.
