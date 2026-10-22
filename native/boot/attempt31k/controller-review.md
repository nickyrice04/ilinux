# 31K independent controller and entry review

**Design/code review PASS; final VM assembly and pinned-client validation
pending at this review. Native 31K, CPU1 execution and Linux SMP NOT RUN or
unverified.** This document alone does not authorize restart. The release owner
must record the final integration results and M1 readiness before the handoff.

The independent reviewer owns the new original cold-tripwire package and
reviewed the separate controller/control implementation. No Apple proprietary
bytes, pseudocode or decompiler output were used in this review or copied into
the package. Public m1n1 source and the pinned boot021 image establish the
reviewed entry/layout facts. This is an implementation provenance statement,
not legal advice or a claim to have established macOS's complete CPU1 path.

## Reviewed contract

31K preserves 31J's discovery, identity, source, receipt and deadline gates and
the same two CPU1 startup stores. No additional core, reset-vector redirect,
protection change, clock write, boot-object, policy or volume modification is
introduced. New operations are fixed RAM instrumentation and CPU0 translation
queries through the already reviewed helper regime.

The control leaf resides in the owned helper allocation and writes one marker
inside separate shared Device-nGnRnE scratch. The same CPU0 LDR observer checks
the entire 64-byte scratch before, during and after the marker, including seven
unchanged canaries. A nonzero initial word refuses without erasure. Successful
control restores the known zero marker and verifies every word. Errors stop
without speculative cleanup, retry or CPU1 start. This tests CPU0 observation
and publication through the scratch mapping; it cannot establish CPU1's
incoming mapping, fetch, first-store visibility or instruction execution.

The cold hook is a candidate tripwire on the known public primary entry at
image+`0x800`, armed only after the primary proxy is running. It does not select
that address as the effective CPU1 reset destination. The original 76-byte body
at `0xb00` records into `0x90a80..0x90ac0`, separate from both the existing vector
record and CPU0 control scratch. The first store precedes every MRS. There are
no stack/LR changes, incoming boot-argument capture, calls, MMIO accesses or
system-register writes in the tripwire. Only x0/x8/x9 and the owned record change.

Every natural late cold arrival is intercepted, even CPU0 or an unknown
identity. The body never resumes primary initialization: that path would set
the shared primary stack, reapply relocations and clear shared BSS. Instead it
ends in a B-to-self terminal spin. This is an intentional behavioral change,
not transparent tracing or verified architectural parking. Phase3 proves only
CurrentEL publication, not the next barrier or final branch. Unexpected CPU0
arrival can lose the proxy; interrupts/faults remain possible. The independent
human 90-second return bound is retained.

## Checks and corrected findings

The exact image/symbol audit found zero candidate padding, no allocated symbol
in the new stub or either new scratch region, no matching references in 1371
RELA records, and no bounded direct branch/literal/ADR/adjacent ADRP+ADD
reference. The cold hook has no matching relocation/direct reference. These
checks do not prove absence of computed or broad-range references or all future
primary reuse. Image-only intake repeats the bound checks without claiming
fresh full-symbol verification.

The controller requires live scratch freshness, distinct helper/image
allocations and existing CPU0 permissions/attributes before new operations.
Sixteen cold probes bind the hook, both code ends and both record ends; the
control has separate leaf/scratch probes. Body publication precedes the hook,
with cache publication, alias/identity readback and whole immutable-text
comparison permitting only the existing vector and new cold hook/body deltas.
The cold hook cannot arm before a successful control.

Review identified and corrected:

- Several new guarded memory reads originally shared one later exception
  check. Each now checks immediately, before another guarded read could clear
  the evidence; the final cold/vector freshness checks are also split.
- A 512-sample cold ceiling covered the arrival loop but could refuse a valid
  campaign with eight near-deadline callback loops. The ceiling is now 2048
  samples/8192 reads, with all original wall deadlines unchanged. Exhaustion is
  tested as a terminal refusal without an additional read.
- The control's initial DRAM upper bound was narrower than the inherited
  census/alias envelope. Its separate owner corrected it to the existing
  less-than `2^41` envelope while retaining exact live bounds, alignment and
  non-overlap requirements. The old check rejected the unchanged M5 fixture
  with DRAM base `2^40` and size 128 GiB. The new high-DRAM regression also
  verifies alias-bit separation and rejection at `2^41`. No new mapping or
  arbitrary address is allowed.

Cold observations occur before each startup/callback boundary and during
arrival monitoring. Any observed nonzero phase stops, including wrong identity,
invalid phase or a partial sample; callbacks cannot continue after that
observation. A zero sample is not a proof against a subsequent asynchronous
arrival. The tracker closes on the first positive/error and preserves partial
acquisition counters. Outer deadline/guard Refusal causes are retained by the
controller rather than converted into a generic telemetry failure.

## Offline evidence and remaining release gates

The cold package's 49 test methods pass on the build host in both full-symbol
and image-only modes, with zero skips. Tests cover a halt before every original
instruction, invisible stores, every store remaining inside the owned record,
all three publication phases, phase3 without loop execution, CPU0/other core
types/unknown identity, invalid EL, partial reads, reentrant observation,
interrupts, acquisition limits, static-reference mutants and exact-image
mutation refusal. The software model does not emulate Apple firmware or prove
any native mapping/coherency behavior.

The separate CPU0 control suite also passes all 24 methods on the build host.

Encoder output is 76 bytes, SHA-256
`c49763521a8ea3c7b063c16a915139b41d39cef00a48800903059f0f3f7b5f98`.
The release owner must add independent VM assembly equality, all final source
pins and pinned-client controller/wire tests here or in the validation record.
In particular those tests must include cold positives at startup/callback
boundaries, all new fault prefixes, guard/deadline/journal failures and no
continuation after a cold positive.

No unresolved code-level blocker was identified in the reviewed contract.
Physical CPU1 route, secondary fetch/store visibility, loop residence and all
native performance claims remain unknown. If both records stay at zero after a
successful CPU0 control, the result still cannot distinguish no fetch, another
entry, a fault before the first store, or CPU1 publication failure. No next
write, longer timeout or additional-core permission follows from that result.
