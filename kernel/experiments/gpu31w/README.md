# Mapping queue pressure-note composition

This original C component composes the frozen
[31V mapping producer](../gpu31v/README.md) with the selected host-side
near-full notification order established by
[31W research](../../../research/native31w-gpu-firmware.md). It supplies no
native transport and does not enable G17C hardware.

The captured 256-slot queue has one free entry when its consumer is two slots
ahead of its producer. In that case the checked host path sends the opaque word
`0x0085000000000000`, with Boolean argument false, through numeric provider role
0 and endpoint selector `0x21`, **before** copying the new 24-byte record and
publishing its producer index. A note sent before the record exists cannot be
an acknowledgment of that record. The Boolean has no assigned priority meaning.
The lower endpoint send uses a separate true argument; a future adapter must
qualify that lower interface rather than forwarding the outer Boolean blindly.

Do not call this message a harmless kick or flush. A public implementation for
different firmware labels the same word “halt”; this pass has not recovered the
local firmware's interpretation. Numeric role0 is a software role, not an ADT
GFX/GFX1 identity. The provider must have a non-null endpoint and its direct-send
guard must admit the send. Caller-supplied role/selector values do not prove
these facts. Hardware use still needs version/role/address binding, actual
transport and message semantics, coherent indices/memory and completion evidence.

## Original bounded behavior

`gpu31w_prepare` validates the binding, delegates record/index/extent validation
to31V, and captures a single operation without callbacks. `gpu31w_submit` applies
the pressure condition to that snapshot, issues at most one note, then delegates
the existing write-before-publication sequence to31V.

- An empty/non-pressure position skips the note.
- A full queue refuses without a note or wait. This deliberately differs from
  the observed full-ring wait.
- An uncertain or suppressed note stops before record writes and retains the
  word, attempted/accepted flags and opaque status. Even a zero status is not
  proof the provider actually sent. The adapter must report acceptance explicitly.
- After an accepted note, any record-write or publication uncertainty retains
  the31V receipt. There is no retry, reset or reuse API. Replacing the object
  cannot bypass external reconciliation of possible effects.
- Acceptance does not establish delivery, consumption, completion or readiness.
  This implementation deliberately checks acceptance where the observed host
  insertion does not branch on the note's returned status.

The caller owns serialization and sole-producer ownership across preparation,
note and publication, an acquired stable index snapshot, correct role/firmware,
mapping/coherence and callback lifetime. Consumers may only advance through
published entries. All31V input bounds and native DMA-ordering duties remain.
Inputs and state must not overlap. Callbacks are synchronous, bounded and may
inspect but not modify state or drive the embedded31V object independently.
Only this outer API drives that object; its fields expose diagnostic receipts.
Reentrant outer submission is refused while any callback executes.

## Tests and limits

Eight original C groups check binding/input refusal, all256 empty, all256
one-free-entry and all256 full positions, exact note word/selector/Boolean,
note-before-write-before-publication order, false acceptance with zero status,
errors after effects, reentrancy and one-attempt lifetime. They use synthetic
callbacks; they do not simulate firmware, DMA coherence or actual GPU progress.
Parent integration metadata records actual test executions and sanitizer results.

From the repository root:

```sh
cc -std=c11 -Wall -Wextra -Werror -pedantic -O2 \
  kernel/experiments/gpu31v/mapping.c \
  kernel/experiments/gpu31w/pressure.c \
  kernel/experiments/gpu31w/test_pressure.c -o build/test-gpu31w-pressure
build/test-gpu31w-pressure
```

No Apple code, pseudocode or instruction bytes are included. The existing31V
sources and consumed native evidence are unchanged. Native acceleration and
performance improvement remain NOT RUN / UNMEASURED.
