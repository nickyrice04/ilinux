# 31Q: original GPU address planning before native initialization

Date: 2026-10-23. Scope: original C/Python code based on the pinned public Asahi
userspace API and a separate, bounded 31Q behavioral format finding. The implementation
session did not inspect Apple binaries,
disassembly or decompiler output. No G17C firmware ABI, UAT layout or native
initialization is claimed. macOS and prior boot packages are unchanged.

## Problem and evidence

31P preserved the full 64-bit fields of both ASC firmware descriptor lists. Their
CPU-physical address domain remains unqualified. Those addresses must not be
silently used as user GPU VAs or page-table outputs. A future original Linux/Mesa
integration also needs a reliable userspace mapping path: preserving high bits,
protecting the kernel's internal VA carveout and checking object extents before
issuing a batch. These operations can be implemented and tested without guessing
the missing G17C firmware interface.

Public sources are pinned to Gravity Linux commit
`4fc326f6c25ccceb7515e2635c22e01fde5d3bac`. The local archive is the unchanged
SHA-256-pinned input in job075's `sources.json`; it was read as data only on macOS.
The kernel and Mesa Asahi UAPI headers were already shown byte-identical in 31P.

| Public evidence | Original implementation decision |
|---|---|
| [`asahi_drm.h`, lines 143–168](https://github.com/GravityLinux/linux/blob/4fc326f6c25ccceb7515e2635c22e01fde5d3bac/include/uapi/drm/asahi_drm.h#L143-L168): driver-reported VM window and minimum kernel reservation | Require explicit input window/minimum; no fixed G17C window guessed from an older generation |
| [lines 249–269](https://github.com/GravityLinux/linux/blob/4fc326f6c25ccceb7515e2635c22e01fde5d3bac/include/uapi/drm/asahi_drm.h#L249-L269): kernel range must fit; userspace cannot bind there | Check half-open containment/minimum and reject every overlap, including a binding covering the whole reservation |
| [lines 347–405](https://github.com/GravityLinux/linux/blob/4fc326f6c25ccceb7515e2635c22e01fde5d3bac/include/uapi/drm/asahi_drm.h#L347-L405): read/write, repeated-page and unbind flags; aligned offset/range/address | Preserve the public flags, require permissions on bind, distinguish full-span object extent from a single repeated page, validate alignment without rounding |
| [`file.rs`, lines 587–745](https://github.com/GravityLinux/linux/blob/4fc326f6c25ccceb7515e2635c22e01fde5d3bac/drivers/gpu/drm/asahi/file.rs#L587-L745): bind/unbind checks | Reject unknown flags; unbind requires only its flag and zero handle/offset; protect the reservation for unbind as well as bind |
| [lines 355–417](https://github.com/GravityLinux/linux/blob/4fc326f6c25ccceb7515e2635c22e01fde5d3bac/drivers/gpu/drm/asahi/file.rs#L355-L417): internal GPU/shared-firmware allocation within the kernel range | Keep the public carveout intact rather than reclaiming space because the userspace map appears empty |
| [lines 554–570](https://github.com/GravityLinux/linux/blob/4fc326f6c25ccceb7515e2635c22e01fde5d3bac/drivers/gpu/drm/asahi/file.rs#L554-L570): operations processed sequentially | Preserve ordering and repeated addresses; promise transactional validation only, never transactional kernel execution |
| [`pgtable.rs`, lines 38–64](https://github.com/GravityLinux/linux/blob/4fc326f6c25ccceb7515e2635c22e01fde5d3bac/drivers/gpu/drm/asahi/pgtable.rs#L38-L64): generic 16 KiB/three-level/39-bit path, distinct from its separate G16 implementation | Do not install those constants as a G17C UAT profile; page size and usable VA window remain explicit inputs |

The original implementation is in `kernel/experiments/gpu31q`. C uses bounded
stack storage and has no dynamic allocation or external I/O. Both implementations
use 64-bit checked span arithmetic, accept adjacency, preserve operation order
and treat each supplied GPU space independently. Failure at the final operation
cannot publish a partially validated C plan.

The implementation is a strict planning subset, not an ioctl shim. The README
lists resource bounds, conservative zero-span refusal, full-page extent checks
and caller ownership rules. In particular, the pinned kernel uses a page-mask
expression for its preliminary single-page object-bound check; the new planner
requires the complete page described by the UAPI. Actual GEM allocation behavior
was not tested, and no kernel runtime defect is claimed.

## Typed GPTBAT conversion from a separate behavioral finding

The independent 31Q GPU research session supplied one bounded behavior without
Apple code: in the inspected retained AGXG17X PI_300 X SecureMonitor member, a
32-meaningful-bit page number is scaled by 16 KiB to form an aligned 46-bit base.
REA completed the query, and the full 17-word instruction range was independently
checked despite REA reporting a one-instruction normalized function body. The
unchanged whole-function evidence gate returns `rejected_cross_boundary`; that
refusal remains in force. Independent instruction behavior is the claim basis,
with high P-code as corroboration. A completed query is not an accepted whole-
function pseudocode result. The collection's match to the currently running
kernel was not independently established. The implementation session received
only that behavior and its confidence/limits.
Full provenance belongs to [`native31q-gpu-firmware.md`](native31q-gpu-firmware.md)
and the GPU finding's validation record.

Original C/Python functions now enforce precisely that format boundary using
separate page-number and base types. They reject width loss and misalignment;
zero is representable. Every accepted result remains in the unqualified GPTBAT
base domain. No CPU-physical/user-VA conversion, table layout, PTE, permissions,
readiness check, memory access or register address is provided. Actual runtime
selection and zero's validity are unknown. This format is neither G17C's GPU VA
width nor evidence that the generic or separate G16 page-table implementation
applies to G17C.

This is a concrete implementation response to the finding: callers can preserve
and check the field width without silently truncating a wider address or feeding
it into the unrelated userspace binding path. Whether/where to use the result
still requires qualified boot-time ownership, table semantics and address-domain
evidence. No native test is created by these conversions.

## How this helps the Linux track

When G17C address translation and firmware ownership are independently qualified,
a Linux/Mesa adapter can call this planner before issuing user-space bindings.
It preserves high address bits in the userspace VA path, refuses
kernel-reservation collisions, and exposes invalid object extents
before a partially applied kernel batch. A future adapter still needs real DRM
parameter/object discovery, locks and lifetimes, ioctl error handling, and a
strategy for recovering from partial kernel changes. None is faked here.

This is not the GPU startup solution by itself. The missing interfaces remain
firmware roles/ABI, usable address domains, UAT/GPTBAT semantics, publication and
completion. No firmware load, PTE, queue command, device-tree change or GPU ioctl
is generated. Native G17C remains **HOLD / NOT RUN**; native rendering, input
latency, performance and energy improvements remain **UNMEASURED**.

## Offline validation

Host C11/O2 compilation with `-Wall -Wextra -Werror -pedantic` passed. The 20 C
planner groups passed, including 139,392 reduced page-grid oracle cases. All 28
Python planner methods passed, including the same grid and 500 seeded high-VA
translation checks. Synthetic tests include full 64-bit arithmetic boundaries,
reserved-window adjacency/overlap, object extents, flags, repeated-page access,
unknown/duplicate handles, zero and excessive counts, and failure after valid
prefix operations. These are software validation results, not GPU measurements.

The typed GPTBAT codec separately passed 7 C groups and 8 Python methods. These
include independent literal values, all 32 single-bit vectors, all 16,383 nonzero
page offsets, width limits, null/incorrect-domain inputs, unchanged C outputs on
failure and 10,000 seeded roundtrips. Combined totals: 36 Python methods and 27 C
groups. Zero representability is tested without making a readiness assertion.

The root integration job separately records Linux VM and sanitizer results;
this component record does not claim those runs before completion.
