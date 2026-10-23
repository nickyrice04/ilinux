# Original receive-ring component

This is a bounded C11 data-path component for the **72-byte ring variant**
identified in [31U's static GPU analysis](../../../research/native31u-gpu-firmware.md).
It is not a native GPU driver or a shared-memory layout definition.

The caller supplies capacity, an acquired consumer/producer snapshot, mapped
extent, an allowed-type mask and two operations: copy one stable record and
publish the next consumer index. The code checks indices and extent, retains
all 72 raw bytes, decodes only the little-endian type field, and advances with
wraparound for arbitrary positive capacity. It consumes only up to the captured
producer. Equal indices mean empty under this protocol, not full.

Publication follows successful copying and type validation. The publication
adapter must implement the platform's actual read-before-index-store ordering;
this component intentionally supplies no C11-fence substitute for DMA/device
ordering. It cannot check visibility or qualify a GPU mapping. Asahi m1n1's
public event-ring format is a different width; do not plug this into that ABI.

Original failure policies are stricter than the observed machine operations:
an empty snapshot returns EMPTY; disallowed types stop without publishing, and
types at least 64 are refused instead of aliasing a variable shift. A copy
failure never publishes. A refused publication may already have had effects,
so it preserves the record and proposed index in PUBLICATION_UNKNOWN and refuses
further operations. No automatic retry, skip, reset, event dispatch or readiness
promotion is available. A caller must reconcile that state externally before
constructing a new view; a new object is not permission to repeat an uncertain
store. Error status is opaque and independent of explicit callback acceptance.

The caller owns sole-consumer serialization, producer protocol, acquired snapshot,
stable mapping/records, bounded truthful callbacks, runtime role/address binding,
and all lifetimes. Callbacks may inspect the ring, but cannot mutate it. Input
objects must not overlap the ring. The ring must start zero-initialized and remain
untampered. `record_valid` describes the last copy; `publication_attempted`
qualifies the proposed index and publication status. A failure after an earlier
success can leave old bytes/status in fields whose corresponding validity is false.

Native adapter details still required: actual allocation/mapping, control-field
addresses, acquisition and publication synchronization, event-type meanings,
firmware version/profile, bounded completion, and initialization integration.
The observed 72-byte stride does not establish any of those. No hardware operation
or performance gain follows from these offline tests.

Seven C test groups cover argument failures with unchanged state, all 1,785
consumer/producer pairs for capacities 1 through 17, raw-byte preservation,
non-power-of-two wraparound, type/allow-mask failures including oversized aliases,
partial copy and ambiguous publication, opaque status, reentrant callbacks,
32-bit maximum capacity with 64-bit offsets, and failure after a prior success.
Callbacks are deterministic local fixtures; they do not simulate GPU caches,
concurrency or device ordering. Integration results are recorded separately.

```sh
cc -std=c11 -Wall -Wextra -Werror -pedantic -O2 \
  kernel/experiments/gpu31u/ring.c kernel/experiments/gpu31u/test_ring.c \
  -o build/test-gpu31u-ring
build/test-gpu31u-ring
```
