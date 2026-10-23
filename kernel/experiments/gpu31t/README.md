# Explicit mapping preparation and cleanup obligations

This original C11 component addresses a concrete initialization problem found
in [31T GPU research](../../../research/native31t-gpu-firmware.md): preparation
status alone does not establish cleanup ownership. A lower preparation failure
may already have rolled back, while a higher-level failure path may still call
completion. Copying an observed unwind sequence without its ownership contract
would risk a double completion or a leak.

`gpu31t_prepare` accepts up to 16 resource tokens and injected callbacks. Each
callback separately reports acceptance, cleanup obligation, opaque status and
lease token. On the first refusal, the helper stops preparing and completes all
explicit obligations, including the refused operation if it reports one.
Reverse cleanup is this component's original policy, not a reconstruction of
Apple's exact ordering. All leases must remain independently completable even
if another remains unreleased. Dependent backing-pin/mapping chains require a
separate policy; this helper must not free a parent beneath a live child.
The caller must qualify those conditions before using it.

On full acceptance, the batch remains PREPARED until `gpu31t_finish` is called.
The caller must first establish that firmware is no longer using the resources.
The helper cannot establish that condition. It attempts each cleanup once,
continues cleaning other obligations after one cannot be released, and preserves
the unresolved lease and both opaque statuses for external recovery. Subsequent
finish or prepare calls are refused. There is no reset/retry API; do not clear
an unresolved batch or drop its context and resources to bypass this state.

Callbacks must be bounded, return normally and report ownership truthfully.
Preparation must not publish resources to firmware or other consumers. Automatic
failure cleanup requires those resources to be safe to release, just as finish
does; an adapter must not silently introduce concurrent use during preparation.
All access is serialized by the caller, including callbacks; callbacks may
inspect but must not mutate the batch. Reentrant prepare/finish calls are
refused. The context, resources and callbacks must remain valid until all
obligations are discharged or externally recovered. The helper supplies no
locking or authentication boundary.

For a later Linux adapter, map the selected API's actual error and ownership
contract into these explicit results. For example, distinguish a successfully
created mapping requiring an unmap from a failed operation that already rolled
back. Do not translate proprietary status numbers directly into ownership, and
do not treat memory-descriptor completion as a firmware acknowledgment.

No DMA/cache publication, UAT update, actual allocation/map/unmap, device access,
firmware submit, address conversion or native readiness is implemented here.
All executable tests use fixture callbacks. The 31Q planner validates mapping
requests; this component manages callback-reported lifetime obligations. The
31S bootstrap encoder remains separate; PREPARED does not authorize its use.

## Reproducible tests

```sh
cc -std=c11 -Wall -Wextra -Werror -pedantic -O2 \
  kernel/experiments/gpu31t/leases.c \
  kernel/experiments/gpu31t/test_leases.c -o build/test-gpu31t
build/test-gpu31t
```

The 14 groups cover failure with/without retained obligations, borrowed
resources, multiple incomplete cleanups on success/failure, unchanged refusal state,
opaque status/token preservation, reentrancy, maximum size, independent leases
for a shared resource, and one-shot behavior. A 2,432-case matrix varies batch
size, first failure and ownership patterns. Linux job080 additionally runs
ASan/UBSan. See [validation](../../../native/boot/attempt31t/validation.json)
for actual results. Native mapping/GPU and performance tests remain NOT RUN.
