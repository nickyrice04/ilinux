# Original GPU mapping-notification component

Offline only. This is a portable C component for the checked G17X mapping
notification format, not a native GPU driver or a complete enqueue transaction.
The [31V behavioral findings](../../../research/native31v-gpu-firmware.md)
identify the evidence, version limits and unresolved adapter requirements.
No Apple code, pseudocode or instruction bytes are included here.

## Wire format and deliberate bounds

| Byte offset | Width | Value |
|---|---|---|
| 0 | 8 | Caller-converted firmware virtual address, little-endian |
| 8 | 4 | Byte length in 4KiB units |
| 12 | 4 | Zero |
| 16 | 2 | GART page size divided by firmware page size |
| 18 | 2 | Selected value 1 or 5; bit2 meaning unqualified |
| 20 | 4 | Zero |

The selected firmware page shift is 14. This implementation accepts GART shifts
14–29 so the ratio is a nonzero power of two fitting 16 bits. It rejects zero or
non-4KiB lengths, counts exceeding 32 bits and address-plus-length overflow.
These are stricter original policies; some private arithmetic narrows instead.
The firmware address is a full 64-bit field, distinct from the earlier bootstrap
message's 44-bit field. No conversion, physical-address assumption or permission
meaning is invented. Format compatibility alone does not qualify an address.

The outgoing queue has 256 slots of 24 bytes. Shared 32-bit consumer and producer
indices occur at control offsets 0 and 16. Equal indices mean empty; advancing
producer onto consumer means full. The adapter supplies an acquired snapshot
and at least 6,144 data bytes. `prepare` encodes and captures a single submission,
without callbacks; `submit` writes the record and then calls publication.
Publication must make the record visible and order its writes before the actual
producer store using the platform's required DMA/device operations.

The source has a distinct near-full helper and a full-ring wait. Their native
progress behavior is unresolved. This component deliberately never waits and
never invokes an assumed doorbell. The adapter must qualify near-full progress,
wakeup, mappings, lifetime and completion before hardware use. The earlier
72-byte incoming event ring and Asahi's 20-byte FWCtl queue are different formats.

## Failure, ownership and evidence

Caller supplies sole-producer serialization, a stable mapping, an acquired
index snapshot, and a consumer that advances only through published entries.
Maintain those conditions from prepare through submit. Copy and publication
callbacks are synchronous and bounded; they may inspect state but cannot mutate
it or retain record pointers. Inputs and state must not alias. No concurrency
or DMA model is implied by the tests.

Full or invalid input produces no callback. A write refusal can leave partial
slot contents; a publication refusal can still have advanced the shared index.
Both therefore preserve the encoded record, proposed index and opaque callback
status in terminal uncertain states. Do not construct a replacement object to
retry without external reconciliation. Accepted publication is not proof of
firmware receipt, mapping completion or readiness. There is no reset API.

Two fresh REA decompilations cross their independently checked function bounds;
their whole-function pseudocode is refused. The format and publication facts
instead come from independently matched bounded instruction ranges and synthetic
instruction-behavior checks. This distinction remains explicit in the research
and validation records. Native address translation, PTE installation, DMA mapping,
cache visibility, near-full handling and completion are not implemented here.

Eight original C test groups cover wire bytes, range policies, invalid setup,
all 65,536 index pairs, write/publication failures after effects, reentrancy and
one-attempt ownership. Golden values and failure injection are synthetic.
Run from this directory, writing the executable under an ignored build folder:

```sh
cc -std=c11 -Wall -Wextra -Werror -pedantic -O2 \
  mapping.c test_mapping.c -o ../../../build/test-gpu31v-mapping
../../../build/test-gpu31v-mapping
```

Parent integration records report actual host/Linux and sanitizer outcomes.
This component performs no device access and establishes no native GPU gain.
