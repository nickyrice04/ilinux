# GPU attachment evidence lifecycle

Original portable C11 component, written from the behavioral findings in
[`native31r-gpu-firmware.md`](../../../research/native31r-gpu-firmware.md).
It is memory-only code intended for a later Linux attachment diagnostic adapter.
It is not a device driver, firmware emulator or native-readiness check.

The practical problem is asynchronous attachment: a successful payload request,
firmware preloading, notification registration, matching an endpoint and accepting
an initialized endpoint are different observations. Conflating them hides the
point where startup actually failed. A delayed termination can also erase a
replacement's state unless callback identity is retained.

`gpu31r_begin` starts a new provider epoch and clears all old observations.
`gpu31r_apply` records one sequenced event; `gpu31r_inspect` provides counts and
facts without granting permission to start hardware. A match stays unaccepted
until an explicit `ACCEPT`. `REJECT` or `TERMINATE` clears only the matching
instance. A replacement clears acceptance. A null-payload success with a nonzero
length is representable and does not set the preload observation. Callbacks may
arrive before the final subscription-registration observation.

Epochs, sequence numbers and instance tokens are our original bookkeeping, not
Apple ABI fields. Tokens must never be recycled within an epoch. The caller
must authenticate callback association, reject stale `MATCH` observations and
serialize all calls. The reducer protects against old-epoch events and delayed
acceptance/termination for a different instance; it cannot reconstruct physical
ordering from an invented sequence number. Unsupported events/invalid state do
not alter state. An ignored old-instance event consumes its ingestion sequence.

The two local array slots are **not** provider roles, ADT GFX/GFX1, firmware
endpoint selectors or queue numbers. An eventual adapter must establish these
mappings independently. Endpoint acceptance requires independent evidence for
that endpoint; one endpoint's initialization path is not assumed for the other.
Native readiness remains false even with two accepted endpoints. Firmware ABI,
address domains, shared-data publication and hardware synchronization are outside
this component and remain unqualified.

## Offline checks

Compile the original sources with an existing C compiler:

```sh
cc -std=c11 -Wall -Wextra -Werror -pedantic -O2 \
  kernel/experiments/gpu31r/lifecycle.c \
  kernel/experiments/gpu31r/test_lifecycle.c -o build/test-gpu31r
build/test-gpu31r
```

The21 C groups cover notification/callback ordering, null-payload evidence,
replacement, stale acceptance/termination, rejection, provider reset/end,
malformed state and input, unchanged state/output on refusal, full-width counters
and counter exhaustion. Exhaustive depth-five traversal covers32,768 event paths
(37,448 accepted/ignored transitions). It checks that acceptance is never created
without an explicit acceptance event and that no trace promotes native readiness.
Job078 additionally runs AddressSanitizer and UndefinedBehaviorSanitizer in the
isolated ARM64 Linux VM. Actual outcomes are recorded in
[`attempt31r/validation.json`](../../../native/boot/attempt31r/validation.json).

The next integration needs real endpoint identity and acceptance evidence,
provider incarnation ownership, and lifetime/locking rules in the actual Linux
transport. No MMIO, firmware upload, ioctl or native image change is included.
