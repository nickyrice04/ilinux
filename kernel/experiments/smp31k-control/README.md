# 31K CPU0 observer positive control

This original helper verifies one CPU0 measurement path before any CPU1 start.
It does not establish CPU1 execution, instruction visibility, reset provenance,
incoming mapping/cache state, or Linux SMP. Native use requires the separately
reviewed 31K controller; this directory has no live entrypoint or transport.

The existing 16-KiB helper allocation has used bytes below 0x190. The new returning
leaf occupies helper-relative 0x200..0x210. It performs one aligned 64-bit store,
DSB SY, returns 0x314b, and uses no stack, MMIO, SEV, MSR or mapping change.
It never calls the reset-vector recorder, which is not a returning function.

The separate scratch record is image-relative 0x90b00..0x90b40 in SMP-shared
Device-nGnRnE RAM. It does not overlap the existing recorder at 0x90a40..0x90a80
or proposed cold-entry record at 0x90a80..0x90ac0. Exact-image zero/padding and
reference ownership are independently checked by the 31K entry audit. Live
translation probes require the leaf's existing Normal-memory alias and both
ends of the scratch's identity Device-memory mapping. No remap is allowed.

## Integration API

- `verify_image_padding(image)` requires the complete pinned boot021 bytes and
  zero scratch bytes; it does not establish runtime freshness or ownership by itself.
- `layout(image_base, helper_base, ram_lo, ram_hi)` validates alignment, extents,
  existing 16-KiB allocation and no image overlap. Its runtime addresses are private.
- `translation_probes(plan)` returns five fixed requests for the controller's
  already-verified AT helper and PAR decoder; no target call occurs in this function.
- Publish `LEAF` at helper+`LEAF_OFFSET` using the existing writable mapping,
  reviewed cache publication, exact readback and immediate exception checks.
- Create `Control(plan, read64=..., store=..., journal=..., starts=...,
  clock=..., publication_verified=True)` only after those checks; call `.run()` once.
- `read64(address)` uses the existing aligned CPU0 LDR helper and immediate
  exception check. `store(value)` is a closure bound to `plan.leaf` and
  `plan.marker_address`, journals the native mutation intent before dispatch,
  and returns the checked helper result. It accepts no caller-selected address.
- `journal(report)` persists the sanitized prefix. `starts()` returns the actual
  start-intent counter, which must remain the integer zero. `clock()` is monotonic.
- On `ControlError`, preserve `.report` and unwrap a known outer controller alarm
  or interrupt from private `.cause`; never print the arbitrary underlying exception.

The normal path checks eight fresh-zero words, writes a fixed marker to the
middle word, reads all eight to verify the marker and seven unchanged canaries,
restores the original zero, then reads all eight again. Success is exactly
24 reads and two acknowledged stores inside a two-second control budget.
Raw scratch values and addresses never enter the report. Intents are journaled
before requests; dispatched and completed counters are separate. Failure stops
immediately without a retry, restoration attempt, cleanup callback or CPU1 start.
Successful restoration occurs only in the normal sequence. A late failure may
leave an owned scratch word modified until the required power-off return.

## Offline verification

```sh
python3 -I kernel/experiments/smp31k-control/test_control.py
clang --target=aarch64-none-elf -c kernel/experiments/smp31k-control/control.S -o control.o
python3 -I kernel/experiments/smp31k-control/audit.py --image boot021.bin --object control.o
```

Use the existing isolated VM/toolchain and ignored job output for build products.
The object audit requires one exact returning AArch64 function, no relocations
in its text, and independent assembly equality with the Python binding. Tests
inject before/after faults at all 26 I/O boundaries, every journal boundary,
marker/canary/restore corruption, deadline and interrupt conditions. They test
original code and synthetic RAM only, never physical memory semantics.
