# 31AW: BootPolicy receiver and the remaining CTRR boundary

November 15, 2026. This extends [31AV's client trace](attempt31av-ctrr-2026-11-15.md)
into the generic ARM64 kernel receiver. It performs static analysis only: no
policy query, selected-object/private-state read, SEP request, mount, install,
security change or boot. Extracted Apple code, listings and decompiler output
remain in ignored analysis storage. Published material is original behavioral
findings and finite validation evidence.

## Inputs and version limits

The installed generic KernelCollections checked for this investigation are
x86_64 and do not contain this ARM64 member; they are not treated as the running
M5 kernel. The existing authorized, generic T6050 collection does contain
`com.apple.security.BootPolicy`. It is 115,163,136 bytes, SHA-256
`26ddfbe95c7e6ac9a76aedac424576bf00467e7c13da49dd82f8010efdb75093`.
Its embedded version identifies Darwin 25.6.0, XNU `12377.161.14~5`,
`RELEASE_ARM64_T6050`; the member identifies BootPolicy project `289.160.2`.

The existing original member parser, unchanged, produces a 57,872-byte static
derivative with 423 symbol records and 47 function starts. SHA-256:
`849bf35dcf5ef735bf44b36a2de49c43c78e4e89b6ab2b3adfa6482db1bd79b2`.
Its complete executable segment is 9,144 bytes, SHA-256
`4ca548c4f50260f179184c6741f005011f7cdeeaf8b6b47805914158dbf2560a`.
Only analysis file offsets/member metadata are rewritten; retained payload bytes
and virtual addresses remain unchanged. No collection fixups are applied and
the derivative is never executed. A separate original fixup reader verifies
actual pointer-chain membership for the selected dispatch reference.

**Important limit:** these retained generic bytes are not an identification of
31AU's actual Recovery kernel, userland libraries or SEP application. The current
desktop libbootpolicy examined in 31AV and this collection must not be presented
as a verified matching Recovery stack.

## REA and independent checks

REA 6.4.0/Ghidra 12.1.4 queried `validateSEPCommand`, `performCommandGated` and
`sendSEPCommand`. The three queries exited zero and reported the correct
680-, 980- and 824-byte function bodies. Their high-pcode contains 87, 117 and
128 operations respectively, without truncation or out-of-range operations.
Every operation is marked dead: whole-function pseudocode remains **unadmitted**.

Independent LLVM/original-collection/derivative checks cover **1,226 distinct
instruction words in ten nonoverlapping ranges**, with zero mismatch. The
dispatch reference is authenticated format 8, cache level zero, and is accepted
only after its original chain membership is established. No signing or runtime
pointer-authentication operation is performed.

The existing diskless 2-vCPU/8-GiB VM used explicit `--no-net`; its guest asserted
loopback only. No disks or physical USB were attached. VM exit was zero, the
prior lab job was restored byte for byte, and the coordinated quiet lock was
released. Original extraction/query/verification tools and raw evidence are
retained under ignored `build/rea-lab/rea31aw-ctrr` in the analysis checkout.

## What the host receiver actually does

**Confirmed for this input:** `BootPolicyUserClient::externalMethod`,
`0xfffffe0009b9498c`, supplies one dispatch entry at `0xfffffe0008286178`.
That entry's verified chained target is `extPerform`, `0xfffffe0009b94368`.
It validates the input descriptor at `0xfffffe0009b943d0`, then passes it to
`performCommand` at `0xfffffe0009b94424`.

`validateSEPCommand`, `0xfffffe0009b949ec`, checks descriptor/header validity
and admission. Its command classification helper treats `0x2f` as a mutating
request; this is not a read-only operation. Existing access checks remain intact.
There is no SIP2/Kernel CTRR policy transformation in the checked validator path.

`performCommand` selects gated callback `0xfffffe0009b95150`.
`performCommandGated` obtains the input mapping's address and length, then passes
that whole buffer to `sendSEPCommand` at `0xfffffe0009b95370`. This pass does not
interpret or alter the mode byte at request offset `0x22` identified in 31AV.

`sendSEPCommand`, `0xfffffe0009b95524`, calls `writeToSEPBuffer` at
`0xfffffe0009b955a0`. The buffer helper copies the request using the original
kernel copy routine; the sender checks that the requested length was copied.
It then sends a message at `0xfffffe0009b955e8`, waits for the endpoint response,
checks response status/length and copies the returned data. These are transport
and completion operations, rather than a host-side LocalPolicy field editor.

**A more precise boundary is now identified:** `getSEPEndpoint`,
`0xfffffe0009b95f2c`, selects registry service **`sep-endpoint,pnon`**. The
cross-member call at `0xfffffe0009b9603c` is independently symbol-qualified as
`AppleSEPDeviceService::getEndpoint`. SEP-visible memory allocation and adjusted
endpoint timeout calls are also identified from original collection symbols.
The subsequent endpoint send remains an indirect method call; no unqualified
vtable target or firmware implementation is invented.

Thus the interpretation of command `0x2f` and its `0x22` mode byte lies beyond
this checked host path, at the **pnon SEP application request handler**. We have
not qualified that application's matching image/version or implementation.
The host trace does not prove whether that mode clears an existing disabled
Kernel CTRR flag, preserves it, or depends on another supported baseline.
Nothing here establishes that a CPU-start hardware fix requires Apple.

## A bounded next discriminator

Keep exact candidate recognition, enabled candidate CTRR, Original Full and
independent boot021 rollback as separate requirements. Integrating the reviewed
codec repair can resolve an original-code defect; it cannot establish the
separate secure-policy result. Do not replay the spent AU transaction or infer
success from an Apple writer's exit zero.

A useful new combined diagnostic can bind the actual Recovery tool/runtime
identity and run the corrected decoder's own controlled tests before any writer.
It can then separate exact decoded candidate identity from the actual CTRR
readback. This avoids another ambiguous `UNKNOWN`/policy refusal. A caller or
kernel version match alone still does not qualify the SEP application's effect.

The installed Apple `bputil(1)` manual supplies a supported but materially
different **hypothesis**: choosing Permissive with `-n` recreates LocalPolicy
from scratch and retains only explicitly requested security options; `-c`
separately disables Kernel CTRR. Therefore a newly established lab Permissive
baseline without the disable option could be tested as an enabled-CTRR baseline.
It is **not an enable-only operation**, does not promise preservation of the
existing lab policy/private metadata or custom-object selection, and is not
authorized or executed by this investigation. It needs an explicit new lab
policy-recreation contract, review and owner approval; the current preservation
contract cannot simply be waived. Macintosh HD must remain untouched at Full.

The [independent public-contract review](attempt31aw-public-contract-2026-11-15.md)
records the current Aura guide, enrollment/installer recipes and exact-board
version evidence separately. Its expectation that Mach-O enrollment enables
CTRR is useful as a test oracle, not a verified pnon protocol specification. The other bounded route
is a deliberately matched, newer firmware/Aura/kernel stack supported by an
exact-board working report; any actual OS/firmware update needs its own reviewed,
owner-approved plan. There is no qualified enable-only writer, firmware bypass,
Apple-only dead-end conclusion or native-ready claim here. Native Linux, SMP,
GPU and performance parity remain **NOT RUN** for this attempt.
