# 31Q GPU user-VA planner and typed format groundwork

Original, dependency-free software. No device opens, ioctls, MMIO, firmware loads,
page-table construction, driver installation or native deployment. **Native G17C
HOLD / NOT RUN.** This code does not turn a descriptor or compiler test into a
working GPU driver.

## User GPU VA planning

`planner.c` / `planner.h` validate one ordered batch of Asahi userspace GPU VA
binding operations. `reference.py` provides an independent Python reference.
Inputs are an explicit page size and VA window, a kernel reservation inside that
window, actual accessible object extents keyed by handle, and binding operations.
The planner preserves 64-bit addresses and offsets. It protects the kernel's
reservation from both binding and unbinding; checks alignment, containment,
permissions, object bounds and overflow; and computes the object bytes accessed
by regular versus repeated-single-page bindings. It does not round values.

The API takes only **userspace GPU VA and object offsets**. It has no conversion
from the retained GFX/GFX1 descriptors, CPU physical addresses, ASC-local
addresses or GPTBAT base values. Two calls describe independent spaces; identical
addresses in them are not a global collision. The page size is supplied explicitly
and never inferred from the macOS host, sanitized descriptors or a generation
name. The public driver's generic `pgtable.rs` 16 KiB / 39-bit / three-level path
is not installed as a G17C profile here; separate G16 code has different widths.

An ordered batch may bind, unbind and rebind the same span. No deduplication,
overlap rejection, sorting or merging changes those operations. All validation
finishes before the C output array/count changes; rejection leaves both untouched.
This is a property of the local planner. The pinned kernel executes its bind
operations sequentially and can have partial effects before a later failure.
A successful plan does not make that ioctl atomic or guarantee it will succeed.

Local planning policy is intentionally explicit:

- At most 64 operations and 64 unique nonzero object handles per call. These are
  local memory/work bounds, not kernel or firmware limits.
- Zero operations are accepted. Zero-byte operations, empty/reversed VM windows,
  empty reservations, zero minimum reservation size and zero-sized objects are
  refused. The planner is not a complete emulator of kernel edge cases.
- A repeated-single-page binding requires a complete accessible page, including
  its final byte. The current public kernel's preliminary bound expression uses
  a page mask, but this tool does not reproduce that expression; the documented
  UAPI operation is a full-page repetition. It does not claim an exploitable
  kernel bug or observable failure with real GEM objects.
- The caller supplies actual object extents and must preserve ownership/lifetime.
  No object lookup, reservation lock, memory mapping, synchronization, cache
  operation, device readiness or completion is performed.
- Arrays must be accessible for their stated counts/capacities. Output and
  output-count storage must not overlap input storage or each other. C structs
  are internal native representations, not wire formats; never send their memory
  directly to an ioctl or firmware endpoint.

## GPTBAT format domain

`gptbat.c` / `gptbat.h` implement only the static format established by the 31Q
behavioral finding: 32 meaningful page-number bits and 14 page-offset bits give an
aligned 46-bit base. This was observed in a retained AGXG17X PI_300 X SecureMonitor
member; runtime selection and register contents were not observed. The separate
research session used REA and independently checked the full 17-instruction range.
See [`research/native31q-gpu-firmware.md`](../../../research/native31q-gpu-firmware.md)
for evidence and the REA function-body reporting limitation. The completed query
still receives `rejected_cross_boundary` from the unchanged whole-function
evidence gate. The format claim rests on independently checked instructions;
high P-code corroborates it, but does not override that gate refusal. The retained
collection was not independently matched to the currently running kernel.
The inverse conversion is an original format check, not an observed write path.

C and Python use distinct page-number/base wrapper types. Decode refuses a page
number wider than 32 bits; encode refuses bases at or above 2^46 or not 16 KiB aligned.
No high bits are silently discarded. Zero round-trips as a format value and does
not mean initialized, valid or ready. A base is **GPTBAT_BASE_DOMAIN_UNQUALIFIED**,
not a qualified CPU physical address, user GPU VA, firmware descriptor address
or PTE. It is never passed automatically to the VA planner. Inputs are format
values, not live register reads; the library contains no register address.

Failure leaves C outputs untouched. These small conversion functions prepare a
future checked decode boundary; they do not decide table ownership, layout,
contents, permissions, cache policy or invalidation. They do not allocate tables,
program hardware, load firmware or enable G17C.

Run from the repository root:

```sh
mkdir -p build/gpu31q-check
cc -std=c11 -Wall -Wextra -Werror -pedantic -O2 \
  kernel/experiments/gpu31q/planner.c kernel/experiments/gpu31q/test_planner.c \
  -o build/gpu31q-check/test-planner
build/gpu31q-check/test-planner
cc -std=c11 -Wall -Wextra -Werror -pedantic -O2 \
  kernel/experiments/gpu31q/gptbat.c kernel/experiments/gpu31q/test_gptbat.c \
  -o build/gpu31q-check/test-gptbat
build/gpu31q-check/test-gptbat
python3 -I kernel/experiments/gpu31q/test_reference.py
```

The C program emits exactly `GPU31Q_PLANNER_PASS` when its 20 groups pass. It
includes 139,392 independent page-grid acceptance decisions, high-address and
64-bit overflow boundaries, all permissions, repeated-page extents, kernel-span
protection, ordered replacements and transactional rejection. The Python planner
suite has 28 methods, including that grid and 500 deterministic high-VA translation
checks. The GPTBAT C suite emits exactly `GPU31Q_GPTBAT_PASS` on success in its 7
groups; 8 additional Python methods cover the codec. Both codec suites test every
nonzero 16 KiB page offset, high-bit/zero literal vectors, width boundaries and
10,000 seeded roundtrips. Python also tests domain/type rejection. Total: 36 Python
methods and 27 C groups. All fixtures are synthetic, not captured Apple payloads.

Public-source mapping and limits are in
[`research/native31q-gpu-planner.md`](../../../research/native31q-gpu-planner.md).
