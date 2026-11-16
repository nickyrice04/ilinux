# 31AU: Kernel CTRR enrollment qualification

November 15, 2026. This is an offline investigation of the recorded 31AS
postcondition. It runs no policy query, install, security or firmware operation,
and reads no actual private transaction state. Raw Apple inputs, instructions
and decompiler output remain in ignored analysis storage. Published material is
original behavioral findings and finite validation facts.

## What is established

The owner's audited saved-state observation records candidate `UNKNOWN` and
lab Kernel CTRR **disabled**, while baseline, parser, profile, key/role bindings,
Original Full/CTRR enabled, and both roles' preservation predicates pass. The
saved restored capture passes exact boot021/disabled-CTRR validation. These are
captured observations, not a fresh current-policy check or proof of native entry.
See the [owner-output review](../native/boot/attempt31at-postcondition-2026-11-15.json).

Disabled is not merely inferred from a failed enabled comparison. The qualified
parser accepts that class only with a recognized `Kernel CTRR Status` row and an
explicit true SIP2 value. Missing status text would have produced `unknown`;
contradictory or malformed recognized text would prevent collection.

The recorded Apple output includes successful Mach-O validation, compression,
wrapping, installation and completion, together with exit zero. The exact
selected-byte readback remains unverified. A declined confirmation is therefore
a weak generic control for this recorded run, not a diagnosed cause.

## Public contract and version boundary

The pinned [Aura Mach-O guide](https://github.com/aurora-silicon/aura/blob/22b71758dfd048f6a874073db55fbe6bd1d17f44/docs/macho-boot-object.md#L63)
explicitly expects Mach-O enrollment to restore the LocalPolicy Kernel CTRR
setting to enabled. It describes a raw rollback's need to disable that setting
first. Its [enrollment script](https://github.com/aurora-silicon/aura/blob/22b71758dfd048f6a874073db55fbe6bd1d17f44/tools/recovery/enroll-stage1.sh#L121)
uses the same non-raw custom-object command form as our controller, with optional
compression. It does not provide a separately qualified enable-only policy
operation.

The guide's native results cover T8140/T6040, including a T6040 with newer system
iBoot and older OS iBoot. Its statement that 26.6.2 parses `kcbz=0` establishes
object-property parsing, not a universal LocalPolicy transition on every M5
firmware/Recovery combination. The working J714s report's informal “CTRR off”
wording lacks a full labeled post-enrollment policy transcript and conflicts
with that guide. Neither source establishes the cause on this J716c. The
[source comparison](attempt31at-public-enrollment-recipes-2026-11-15.md)
preserves the report's corrected compressed-boot success and its limits.

Root's fresh, read-only provenance check identifies the current generic tool:

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| Installed generic `kmutil`, universal | 4,265,024 | `2f435e8f872e75e7edcf0ec108f3360e18b1e4123451032062b7c28aa4106b43` |
| Its arm64e slice, identical to the retained REA target | 2,167,872 | `13827d7242e4550f3d45994f9849ce3a84dbb14d3bb6de21601c4488287582fb` |

Root observed current macOS 26.6.2/25G83. This check was of generic executable
bytes/version, not policy or personalized data. **The actual Recovery executable
used during 31AS remains unqualified.** A current desktop binary match does not
erase that boundary.

## New targeted REA result

REA 6.4.0/Ghidra 12.1.4 ran four narrowly selected queries in the existing diskless
2-vCPU/8-GiB Linux VM. Each guest asserted loopback only, with explicit `--no-net`,
no disk attachment or physical USB. The original lab job was restored byte for
byte and the quiet lock released after each VM.

The configure subcommand's late call at `0x100144b78` targets `0x1001452a8`.
The first dossier incorrectly reports only a four-byte body, with all eight
high-pcode operations outside it. Its decompilation is **rejected**. Independent
LLVM/file-byte checks show a seven-instruction forwarding wrapper, including
the call at `0x1001452b8` to `0x100144f18`.

The second query targets that actual helper. Its reported body is 912 bytes,
covering 228 instructions. All 557 high-pcode operations remain inside the body
and are untruncated, but all are marked dead; whole-function pseudocode is not
admitted as a verified policy algorithm. Further static metadata and receiver
queries establish the following narrower contract.

### The mode flag is specifically the inverse of `--raw`

The type descriptor at `0x1001a12fc` identifies `ConfigureBootOptions`, with
metadata accessor `0x100142550`, six fields and a field-offset vector beginning
at metadata word 2. Its field descriptor at `0x1001aa46c` identifies field 3 as
`_raw`. The helper stores that accessor's result at frame offset -248 and reads
the offset-vector entry at metadata byte offset 28, selecting that field.
The layout interpretation follows the
[official Swift ABI declarations](https://github.com/swiftlang/swift/blob/swift-6.0-RELEASE/include/swift/ABI/Metadata.h).

The `Flag<Bool>.wrappedValue` call at `0x1001451b8` writes the byte subsequently
loaded at `0x1001451c8`. The bounded computation at `0x1001451dc` passes its inverse
in argument register `w3`. Thus the call at `0x100145204` carries **1 for Mach-O
and 0 for raw**. It is not the earlier PageProtectionType/SPTM serializer flag.
Register `x2` independently carries the fixed value 2; this pass does not assign
an unverified meaning to that numeric argument.

### Real client and authenticated client boundaries

Swift protocol/conformance metadata identifies `BootPolicyClient` with 20
requirements. The `RealBootPolicyClient` conformance at `0x10017c8d0` has its
static witness pattern at `0x1001d7098`; slot `0x48` points to `0x10013ce54`, whose
checked forwarding call reaches `0x1000711b8`. The Null client has its own
implementation; identifying a static Real conformance does not prove which
client the historical Recovery invocation selected.

The third REA query covers that 536-byte/134-instruction Real receiver. It
captures the inverse-raw flag in a callback record at byte offset 64. The checked
callback `0x100071ef0` loads it into `w5`; worker `0x1000713d0` preserves it and
passes it as `w3` at `0x1000715b8` to authenticated-client slot `0x18`.

`AuthenticatedBootPolicyClient` has six requirements. Its Real conformance at
`0x10017c8c0` has pattern `0x1001d7060`; slot `0x18` points to `0x10013a594`, which
forwards to the concrete implementation at `0x100136e40`. The fourth query
reports a 1,204-byte/301-instruction body there. Its accepted instruction range
excludes the trailing 12 bytes before the next function-start record.

The concrete implementation selects request option **`0x80` for Mach-O**, at
`0x100137158`; the raw path uses a separate option-construction path. Its call
at `0x100137218` targets the named import
`bootpolicy_update_local_policy_for_custom_os_ex` in `/usr/lib/libbootpolicy.dylib`
(stub `0x10016475c`). This is a qualified mode-dependent **policy request**, not
merely an image-wrapper or protection-profile comparison.

**Remaining boundary:** the effect of option `0x80` inside libbootpolicy is not
qualified. In particular, this pass cannot distinguish clearing an existing
SIP2 setting from requesting a mode without newly setting it. The installed
official SDK's text stub confirms the export, but the checked SDK header paths
provide no declaration explaining that option. No API is invoked. A fresh
enabled-lab baseline is therefore still an untested hypothesis, not a qualified
repair or permission to change policy.

LLVM independently matches **835 words** against original bytes, with no mismatch:
670 words across the primary REA/caller ranges, plus 165 distinct words in the
flag-forwarding thunks/callback/worker. Counts do not double-count overlapping
ranges. The three valid dossiers' high-pcode is untruncated and inside their
bodies but marked dead; whole-function pseudocode remains unadmitted. Only the
independently checked bounded data flow and metadata relationships above inform
the engineering decision.

The earlier [31AG protection analysis](native31ag-handoff.md) independently
qualifies a PageProtectionType/SPTM comparison and property serializer selection.
Those are distinct from the LocalPolicy Kernel CTRR bit. They cannot substitute
for tracing this policy mutation or justify treating the expected enabled state
as physically observed.

Finite evidence: [validation JSON](attempt31au-ctrr-2026-11-15.json).

## Engineering decision and next discriminators

**No enable-only writer or alternate CTRR policy transition is qualified here.**
Preserve the existing candidate guard and boot021 restoration. Do not reset the
spent 31AR transaction, blindly repeat its policy command, accept `UNKNOWN`, or
claim the saved disabled flag proves Apple rejected the Mach-O or blocked SMP.
The immediate component defect is insufficient readback diagnostics; that is
addressable in original code without a policy relaxation.

A new separately reviewed transaction should record finite object open/read,
framing, codec/declaration and decoded-match stages before rollback. If practical,
also compare the lab's selected-reference pair with its prewrite pair **in
memory**, publishing only changed/unchanged, not references, names, hashes or
paths. The existing private-policy commitment intentionally omits mutable
selection fields, so its equality does not answer whether enrollment changed
the selection. Exact candidate-byte matching remains the acceptance authority.

Before treating a policy-mode difference as a software fix, qualify the actual
Recovery tool identity/runtime client and libbootpolicy option `0x80`'s effect on
existing SIP2. The exact exported receiver now makes that a bounded library
question; another broad kmutil decompilation is unnecessary. If a verified
selected candidate still reports disabled CTRR, a wrapper-format repair alone
cannot establish the policy answer. Hardware CTXR bounds/enforcement and the
LocalPolicy Kernel CTRR flag must be recorded as separate observations.

The exact-board public accelerated reference uses newer firmware and a matched
kernel/Aura/runtime stack. Matching those inputs may be a deliberate future
route, but any actual OS/firmware change requires its own concrete authorized
plan. This investigation supplies no evidence of an Apple-only dead end and no
native-ready or performance-parity claim.
