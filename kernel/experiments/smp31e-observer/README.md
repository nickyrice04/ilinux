# Acquisition-neutral CPU1 observer prototype

**OFFLINE ONLY — live deployment remains HOLD.** This is original Python code
for collecting a small, bounded set of observations from an injected reader.
It has no USB, native adapter, writes, CPU start, automatic polling, retries,
reset, shell execution or live CLI. It cannot authorize a CPU start, callback,
MMU transition or Linux handoff.

The proposal uses a **48 KiB** diagnostic stack at image-relative
`[0x94000, 0xa0000)`. Its actual entry SP would be `image + 0xa0000`; the
installed code still publishes **`image + 0x178000`** in CPU1's reset record.
These are different quantities. The adjacent `smp31e-entry` audit describes
the pinned public boot021 image and unresolved stack/mapping assumptions.
This collector neither prepares that stack nor verifies those assumptions.

## Interface

Import `collector.py` and construct:

```python
observer = Collector(read64, image_base, max_samples=64)
report = observer.sample()
```

`read64(offset)` receives one **image-relative**, aligned, fixed offset and
returns an unsigned 64-bit Python integer. `True` is not accepted as an
integer. It must not dereference an arbitrary address supplied by a report.
The injected function is trusted acquisition code; this module cannot enforce
its side effects, source authenticity, coherency or execution deadline.

There are eleven allowed offsets, acquired in this exact order:

| Observation | Image-relative offset |
|---|---:|
| CPU1 arrival flag | `0x90258` |
| CPU1 spin MPIDR | `0x90250` |
| CPU1 reset MPIDR | `0x90020` |
| CPU1 reset stack | `0x90028` |
| Two lower stack canaries | `0x94000`, `0x94008` |
| Five saved-LR slots | `0x9ffe8`, `0x9ffc8`, `0x9ffb8`, `0x9fd48`, `0x9fd18` |

The proposed two lower canaries must already contain
`0xd1a631e0d1a631e0`. They detect an observed change, not every stack overflow
or out-of-bounds write. This module does not initialize any memory.

Reading the flag first prevents a later flag publication from being combined
with earlier, incomplete identity reads. The shared classifiers accept either
partial reset-record publication order. A nonzero flag with incomplete
identity is refused. This initial-arrival observer also refuses flag counts
above one; it is not the observer for a CPU1 callback campaign.

Successful samples consume eleven reads. Invalid identity, damaged canary or
failed acquisition stops earlier, with no retry or extra diagnostic reads.
The constructor permits 1–256 sample attempts, default 64. Each attempted
read counts before acquisition, so the absolute ceiling is **2,816 reads**.
Sampling is caller-driven; no sleeps, background work or automatic polls occur.
Once arrival is observed, an error occurs or the sample limit is exhausted,
further `sample()` calls return the same closed result without acquisition.

**A call-count bound is not a time bound.** A blocked injected reader cannot be
preempted by this collector. Any future native integration needs its own
reviewed per-read deadline and independent controller/supervisor/human return
budgets. It also needs exact source/image pins and fresh machine, mapping and
RAM checks. No native integration exists here.

## Evidence semantics

`reset_stage()` and `stack_markers()` come from the sibling public-source audit
in `../smp31e-entry/observe.py`. No classifier is copied or independently
reconstructed here. Five recognized saved-return-address slots are matched
to fixed compiled call sites, converted to named booleans and retained across
samples. A positive match survives reuse of that slot and a later read error.
The output never contains the image base, raw stack words or target pointers.
Reader exceptions are reduced to fixed reasons; their messages are discarded.

These sequential observations are **not an atomic snapshot, current PC,
chronological trace, proof that a function returned, or evidence that no
instructions executed when a marker is absent**. An injected reader can
fabricate every value. Even `arrival_observed: true` is therefore only the
classification of supplied reads, not native compatibility evidence or
permission to continue. Every report explicitly keeps
`entry_authorized: false`, `native_deployment_ready: false`,
`current_pc_known: false` and `hardware_compatibility_claim: "NONE"`.

There is no persisted-state import or resume API. Reports may support later
diagnosis; a new collector starts with no observations. Higher-level adapters
must separately bind provenance and fresh-boot identity, and preserve the
one-start/no-retry rule.

## Tests

From the repository root:

```sh
python3 -I kernel/experiments/smp31e-observer/test_collector.py
```

2026-10-21: **18 test methods PASS** on the macOS host. No native controller,
USB connection, CPU start or VM was run by this component's author.

Tests use original synthetic RAM dictionaries and independently scheduled
producer writes. They cover all **140** monotonic publication interleavings
around the first four reads for both reset-store orders; late flag visibility;
incomplete/bad identity; corrupt canaries; errors at each read; malformed read
values; sticky frame evidence; budget exhaustion; reentrant calls; interrupts;
and no raw-value/exception-message disclosure. Passing them demonstrates
collector behavior under those supplied schedules. It is not firmware
emulation or a successful native CPU1 boot.
