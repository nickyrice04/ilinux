# 31AX: the lab policy reconstruction request

November 15, 2026. Static qualification for the proposed offline reconstruction
and rescue controller. No policy operation or Bootability API was invoked, no live policy,
private state or selected object was read, and no mount, security, firmware,
Startup Disk or boot change occurred. Generic Apple bytes and REA/LLVM output
remain in ignored analysis storage. This note does not authorize a future writer.

## The documented operation is reconstruction

The installed Apple `bputil(1)` manual explicitly describes `-n` as rebuilding
LocalPolicy without retaining existing security options; only options specified
in the invocation are requested. `-c` is separately documented as disabling
Kernel CTRR. The manual is 14,064 bytes, SHA-256
`dacc771e3c49f0ec86feb582ba64e23b0e71c4ee49b1da647ec7f0f77d0a5a1b`.

That supports a narrowly targeted **whole-policy reconstruction request** in
paired Recovery, rather than an enable-only CTRR operation. It does not promise
that an existing custom boot reference survives, nor that arbitrary existing
Lab metadata will remain unchanged. The proposed writer must remain the fixed
`-n` operation with the independently bound Lab target and no extra downgrade
option; observed destination state must decide whether a candidate phase is
admissible.

## Generic inputs and evidence limits

The current generic `/usr/bin/bputil` is 196,320 bytes, SHA-256
`dcd2d73fbeb18d6ce3092605c151790d4a01ac9caeeb99fa23a4098e9559f545`.
Its arm64e slice is 147,168 bytes, SHA-256
`80c9ae8b7536d0ee923a034198d201fe8773d71eea7b9f4bcb3244a2a2a630c2`.
An independent fat-header extraction exactly matches the Apple thin-tool output
and the retained input for the existing REA entry dossier.

The current generic Bootability framework's original TEXT is 35,936 bytes,
SHA-256 `854b2dcf180a7ced5783168c8c0464de2329e9b3b96cc9ef226fb6e864e97b99`.
The original bounded cache reader copied its segments and compacted analysis
metadata into a 72,770-byte static derivative, SHA-256
`8ce589ebb40fa577eea27ac17877bc42ca9606b3ca64bcadbe1ae1bb205c4938`.
Code bytes and virtual addresses are preserved; cached pointers are not rebased.
It is never executed. These generic desktop inputs do **not** identify the
actual future Recovery framework, service or SEP application.

REA 6.4.0/Ghidra 12.1.4 queried two concrete framework methods. The accepted
bodies are 576 and 748 bytes, with 223 and 405 high-pcode operations respectively.
Both are untruncated and numerically within the accepted body, but every
operation is marked dead. The reused bputil entry dossier has 3,000 dead,
truncated high-pcode operations. **Whole-function pseudocode is not admitted.**

Independent original-byte/derivative/LLVM comparisons instead cover **1,127
distinct instruction words** across three nonoverlapping ranges, with zero
mismatch. A separate 104-byte dispatch table is verified as data and excluded
from that instruction count. The first framework range includes its separately
checked exception tail beyond the REA body's ordinary return; that tail is not
silently counted as part of the 576-byte provider body.

Both fresh queries and the existing diskless VM exited zero. Explicit
`--no-net`, a loopback-only guest assertion, no disks and no physical USB were
retained. The coordinated quiet lock was released and the prior lab job restored
byte for byte. Original verification tools and raw evidence remain under ignored
`build/rea-lab/rea31ax-reconstruction` in the analysis checkout.

## Qualified caller behavior

**Confirmed for these generic inputs:** the bputil dispatch table maps `-n` to
`0x100005650`; its distinct `-c` branch is `0x10000563c`. The `-n` path selects
the integer mode literal 2. At `0x100005d14`, bputil installs that value under
the imported `BYBootOptionSecurityMode` key. At `0x100005d30`, it supplies
`kCFBooleanTrue` for imported `BYBootOptionForceCreateLocalPolicy`.

At `0x100005d48`, it converts the selected group object to its UUID string and
passes that string and the constructed options to
`makeVolumeBootableWithGroupUUID:options:error:` at `0x100005d5c`. An explicitly
validated Lab group is therefore part of the request; controller-side target
binding must ensure that it is the intended group before this caller starts.

`BYManager`'s method begins at `0x1d619e044`. It retains the received group and
options, obtains its service connection, creates a synchronous remote proxy,
and forwards those same group/options arguments at `0x1d619e1f0` using
`makeVolumeBootableWithGroupUUID:options:reply:`. It does not rewrite individual
LocalPolicy hashes or preserve a supplied old custom-object reference in this
checked client path.

When constructing its authentication context, the manager passes the same
group to `_authenticationContextWithVolume:options:` at `0x1d619e0b0`. That
method supplies the group as `volumeGroupUUID` to the named context initializer
at `0x1d619f484`. This qualifies **target scope in the client request**. It does
not prove that a particular owner identifier, remote policy, boot reference,
Startup Disk selection or server-generated field will be preserved. Existing
authentication remains required; no credential value or live context was read.

## Explicit field contract for the controller

Apple distinguishes globally renewed LocalPolicy anti-replay state from remote,
Recovery and OS state. `lpnh` may change across all OS policies after one policy
mutation. `rpnh` follows remote-policy changes; `ronh` follows Recovery changes.
This does not justify treating all nonce/hash fields as freely reissuable during
a Lab reset. See [Apple's LocalPolicy field descriptions](https://support.apple.com/en-gb/guide/security/secc745a0845/web).

The following is a **conservative controller admission contract**, rather than
a claim that this client trace proves every resulting field value:

| Class | Candidate-admission requirement |
| --- | --- |
| Physical/APFS role binding | Same machine, distinct bound Original/Lab groups, same Lab Data/Preboot relationship and paired Recovery; recheck independently of LocalPolicy. |
| Original protected policy | Full Security, enabled CTRR and unchanged semantic/private protected commitments against the pre-reset anchor. Global `lpnh`/envelope renewal is distinguished from these protected fields. |
| Lab OS/remote/Recovery/Cryptex state | Preserve `rpnh`, `ronh`, `spih`, `stng`, `love` and `nsih`; do not admit their changes merely because ForceCreate was requested. |
| Lab requested security result | Require fully parsed Permissive policy, explicitly enabled CTRR and the reviewed destination semantics, with no additional unrequested downgrade. |
| Lab custom-object selection | Model any clearing and later exact candidate `coih` selection as explicit phase changes; no promise of old-reference preservation, no `UNKNOWN` acceptance. |
| Signing/anti-replay envelope | Permit only the independently justified `lpnh`/envelope renewal; no blanket mutable-field exception. |

The new phase may record a closed, typed unexpected **Lab-only** delta as
`UNQUALIFIED_TRANSITION` for rescue. Such an observation must never become a
candidate baseline. A rescue-only snapshot can freeze that observed Lab state
while retaining the pre-reset Original anchor and exact target/work bindings;
it is not evidence that the unexplained transition was correct. Unknown syntax,
ambiguous target or an Original preservation failure cannot be relabeled as
ordinary Lab reissuance.

Crucially, independent rescue eligibility must be established **before** the
reconstruction writer. It must not depend on the new Lab policy successfully
passing candidate admission. A failed baseline read, changed reference or
unexpected typed result must remain a refusal to boot, with the separately
guarded boot021 rescue route available under its own reviewed contract.

## What is still unproven

The framework ultimately delegates the group/options request to a service.
The exact resulting field changes and enabled-CTRR baseline remain runtime
questions. [31AW's secure receiver boundary](attempt31aw-ctrr-2026-11-15.md)
remains unchanged; this pass does not invent pnon semantics or qualify another
writer. The useful advance is a verified reconstruction intent and client target
binding, together with an explicit distinction between candidate admission and
rescue-only observation. All actual policy execution and native Linux/SMP/GPU
validation remain **NOT RUN**. A future Lab operation still needs its concrete
review and owner authorization; Macintosh HD must stay at Full Security.
