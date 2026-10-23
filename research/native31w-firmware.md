# 31W — monitor primary entry and the CPU stop decision

**Native HOLD. No qualified software workaround, and no proof that only Apple
can fix CPU startup. The CPU track is practically blocked pending new evidence;
another unchanged secondary-start attempt is not justified.** M1's31V offline
PASS at `9befeb3` is incorporated. No hardware, installed image, boot policy,
volume or security setting changed. No CPU implementation or native experiment
is supplied by this pass.

The new result is a bounded check of the retained SPTM image's **declared primary
entry**, rather than another mBoot range setter. It shows that entering this
image entails an incoming context and memory/exception-level preparation. Merely
having the monitor file, knowing an entry address or issuing the existing start
stores does not supply that contract. It does not establish that the historical
raw boot loaded the monitor, that the monitor is callable from that boot, or that
this primary path releases CPU1.

## Artifact and actual entry

The decoded SPTM is the same1,376,288-byte artifact published in the
[October19 record](../reverse-engineering/findings/cpu-startup-2026-10-19/validation.json),
SHA-256 `da2ad8d4ecbf3e29fbaaa07e8c7d291ed20d296044494e00303c7a780d190666`.
That record associates it with macOS26.6.2/25G83. This pass rechecks retained bytes
and Mach-O structure; **it does not independently match an installed or running
firmware image to that build**. Extraction/decompression provenance is inherited.
The retained compressed payload occurs uniquely at offset25 in its IM4P wrapper;
the wrapper, payload and decoded hashes are recorded separately.

The arm64e executable's `LC_UNIXTHREAD` declares link-time PC
`0xfffffff0270ac388`. Its one direct branch leads to `0xfffffff0270af000`.
The previously described early range `0xfffffff0270a0000..0xfffffff0270a02c4`
is a different range. Neither address is a measurement of a physical reset PC.
No analysis wrapper or relocation of the queried Mach-O was used.

One fresh REA function query of the declared entry's branch target completed in
22.368seconds, CLI/setup/job exit0, in the root-owned isolated VM with only the
loopback interface and no physical USB. REA reports410instructions in two body
ranges,1,640bytes total, and352P-code operations. No truncation or out-of-body
P-code is reported, but **removed-block warnings prevent accepting the
whole-function pseudocode**. Earlier refusals remain unchanged.

Independent Apple LLVM decoding matches all410body words plus the single entry
branch: **411words /1,644bytes, zero mismatches**. Those checked ranges do not
overlap the older published early-entry range. Full-image disassembly already
existed privately;411 is new bounded verification of this path, not a count of
previously unseen firmware instructions or physical CPU progress. Detailed
provenance and bounds are in [validation.json](../reverse-engineering/findings/cpu-startup31w/validation.json).

## Narrow entry contract

These are direct, bounded instruction facts, independent of the removed
pseudocode blocks:

- The primary path preserves its incoming first parameter and reads the context
  at offsets0,8,16,24, with a conditional read at1152 (`0x480`). The8/16/24
  offsets match the public BootArgs virtual-base, physical-base and memory-size
  fields used in the31V comparison. The pointer must describe the actual
  prepared memory environment; knowing the executable address is insufficient.
- The context header comparison and zero-extension branch can skip the extension
  block. The1152 read is conditional, not a claim that every supported context
  requires a nonzero extension. Its format, ownership and optional semantics
  are not qualified here, and no additional BootArgs field is invented.
- A direct `CurrentEL` test selects handling of EL2 controls before later setup.
  This is evidence of exception-level-dependent preparation. It is **not** proof
  that EL2 is required, that other levels are accepted, or that the historical
  raw path had a particular incoming level. No register sequence is copied or
  proposed for replay.
- Two later direct calls are identified at `0xfffffff0270af69c` and
  `0xfffffff0270af6a8`. Their presence does not establish completed monitor
  initialization or physical secondary dispatch. This pass stops at its stated
  primary-entry boundary rather than treating adjacent helpers as a workaround.

This narrows the alternate-route prerequisite: a compatible **accepted native
host bootstrap must supply the monitor's actual initial context and memory
preparation**, then establish a physical secondary path. The public guest loader
from31V is useful for recognizing address domains, but its serialization API is
not evidence that firmware accepts an equivalent host object. No altered image
classification, bypass, protection mutation or monitor replay follows.

## Finite decision

| Route | What current evidence supports | Practical decision |
|---|---|---|
| Repeat the installed raw start | Start stores were acknowledged and no CPU1 marker was observed. Effective entry/protection and an earlier fault remain unresolved. | Stop unchanged retries. More marker absence cannot distinguish these cases. |
| Construct an alternate monitor-bearing host | The retained monitor has a context-dependent primary path. The attributed all-core guest is an alternate-path lead; its accepted host bootstrap and physical-entry chain remain unavailable here. | Block implementation pending the actual accepted host revision/object/context and physical secondary provenance. |
| Declare an Apple-only restriction | Firmware restriction remains plausible, but neither CPU1 effective state nor all compatible software paths has been established. | Do not label it proven impossible or Apple-only. |

The [31W public-source audit](native31w-upstream.md) independently reaches the
same boundary. Exact-board diagnostic/late-entry changes do not supply a new
start operation or successful physical-start result. Public Aura still excludes
the relevant alternate host work. Cross-build reports are not a controlled
firmware comparison.

**Recommendation: defer further CPU implementation and native attempts now.**
Reopen this track only when one of these concrete inputs becomes available:

1. An applicable accepted alternate-host revision and boot-object/context
   description, with evidence linking that host to physical secondary entry.
   Check its firmware/build applicability before designing an original adapter.
2. A separately qualified, safe discriminator that establishes CPU1's effective
   entry/protection state or an early fault and identifies a missing writable
   prerequisite. A boot-CPU register value, reset mirror, guest CPU count or
   another synthetic software test does not meet this condition.

If neither arrives, leaving CPU work shelved is a practical engineering decision,
not a claim of mathematical impossibility. If later evidence shows the necessary
state is immutable under the applicable accepted boot path and no compatible
alternate path exists, an Apple firmware change becomes the supported dependency.
This pass does not establish those premises.
