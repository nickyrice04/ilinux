# 31AI: normal-entry research and a self-contained RAM diagnostic

2026-11-13. **Offline implementation and qualification only. Native NOT RUN.**
M1's [31AH review](../../native/boot/attempt31ah-m1-offline-2026-11-13.md) passed
integrity and static geometry, then requested firmware pairing, exact runtime
delivery/control and a complete lab restoration design. This work addresses
those separately instead of treating a version difference as a diagnosed cause.

## Firmware identities are separate observations

Fresh read-only version plists still show original and lab macOS **26.6.2 / 25G83**.
The running host's System Profiler reports **Boot ROM 20457.1.29** and **OS loader
18000.161.10**. The retained generic J716c firmware used for REA identifies as
**mBoot-18000.161.10**, matching the latter version. This does not identify the
actual policy-selected paired lab image. The two historical generic copies were
identical when originally retained; no personalized object or private path is
published here.

Aura's exact pinned [firmware table](https://github.com/aurora-silicon/aura/blob/bd9f3e8273dc79ae9095c19c2c4f32218446ad4e/src/firmware.c)
recognizes both 18000.161.10 as 26.6.2 and 20457.1.29 as 27.0. The public
[payload-profile function](https://github.com/aurora-silicon/aura/blob/bd9f3e8273dc79ae9095c19c2c4f32218446ad4e/src/payload_profile.h)
selects an ordinary propertyless J716c DT at rank one for either profile; its
special 25G83 J613/J615 display profile does not apply. Real public C parser
controls confirm that narrow rule. Recognition and DT selection are not proof
of firmware entry, effective permissions or physical CPU behavior.

The [external J716c report](https://github.com/aurora-silicon/linux/discussions/142)
uses 27.2.1/26B131 and mBoot 20457.41.3, with all eighteen CPUs and a local USB
patch. No matching physical test occurred here. That difference alone establishes
neither a required update nor compatibility. Apple's separate
[27.3 beta raw-boot correction](https://developer.apple.com/documentation/macos-release-notes/macos-27_3-release-notes)
is another route; it is not authorization to update this machine.

**Engineering decision:** preserve the current installations, identify paired
firmware separately, and keep runtime pairing unqualified. Do not substitute a
global Boot ROM version for the paired loader or declare that Apple must supply
another fix. [Sanitized identity record](firmware-identity.json).

## Fresh REA pass and its actual limits

Two new REA 6.4.0/Ghidra 12.1.4 function dossiers inspect small helpers referenced
by the previously investigated firmware finalization path. Each completed in
about 67 seconds in the existing diskless, no-NIC VM. Their query names were
hypotheses, not recovered symbols or established functional roles.

The 160-byte body at analysis address `0x100c1ae51d8` and 132-byte body at
`0x100c1ae5334` cover 73 instruction words. All match the retained raw/ELF mapping
and independent Apple LLVM 21 decoding. Their 84 P-code operations have no
out-of-body PCs, truncation or removed-block warning. These bodies have no
direct MRS/MSR/ERET/HVC/SMC instructions; their calls remain separate dependencies.
Consequently this pass does **not** establish entry EL, transitive hardware
behavior, monitor residency, the active lab path or secondary CPU execution.
No helper is promoted into a new firmware command or missing startup step.
Whole-function semantic qualification remains false.

The prior 31AG selector/range facts retain their bounded scope and refusal gates.
No old refused decompilation was revived. The present code does not replay Apple
firmware, modify its checks, force private selectors or use decompiler statements
as Linux source. The implementation uses public Aura/Linux interfaces and original
data builders. Raw Apple results/bytes/disassembly remain ignored and local.

The [original audit](audit_rea.py) emits only hashes, extents and consistency
counts. Its [sanitized record](rea-validation.json) records these two fresh
queries; 73 checked words do not imply a complete firmware handoff reconstruction.

## Concrete implementation decision

The unchanged baseline Aura already has a native inline-payload path. Its real
parser can select an exact DT, decompress Image and retain a tagged compressed
initramfs in heap before handing off. Its pure policy accepts a valid native
payload even without CDC or KIS. Thus the initial RAM diagnostic can avoid the
unpublished proxy patch and the pinned Linux T6050 gadget gap. A camera observes
screen output; it does not provide remote recovery/control.

The encoded input totals 19,639,230 bytes, exceeding the old 16 MiB loader slot.
Aura's actual runtime remains 3,997,696 bytes. Original new tools distinguish
runtime from transient compressed inputs, stage the retained kernel/initrd in
heap and preserve the DT below the earliest OS pool start. A new bounded extender
retains the same 128 MiB execution pool and the unchanged baseline code/entry;
it does not relax a locked execution window or change frozen 31AH tools.

The real public parser/tinf/libfdt/profile and policy code ran in eight VM
controls, including missing transport, corruption and handoff refusals. CPU,
NVMe, actual heap addresses, firmware identity, runtime DT fixups and physical
kernel entry were mocked. Aura's later pending-call/NVMe/USB/exception/display
cleanup was not executed. Loader controller operations are real on hardware;
a RAM-root file allowlist does not prove absence of firmware side effects.

The unchanged tested diagnostic now has a fresh relocatable object which links
byte-for-byte to its tested executable. Normal and intentional-stall controls
pass. A strict separate local-user bundle supplies the exact Image, DT and RAM
root omitted from 31AH. Common SPDX texts and the installed GCC exception are
included with explicit attribution/public-source limits; no public binary Release.

The new compressed candidate, exact diagnostic bundle, original tools and
refusal tests are ready for independent M1 **offline review**. All native entry,
CTXR behavior, eighteen online/concurrent physical cores, GPU/N1/NVMe and parity
remain untested. The complete current artifact record and next gates are in
[attempt31AI](../../native/boot/attempt31ai/README.md).

## Current selected-object framing

The human's first frozen-reader result was UNKNOWN. The new metadata reader
initially also refused; its bounded shallow diagnostic then located the failure
in optional IM4P metadata. The 445,430-byte file is a complete IMG4 container,
with a 442,368-byte payload, one final IM4P context-[0] field of 300 bytes and
an outer context-[0] field of 2,680 bytes. All reported direct headers are
canonical and fit their parent. No outer trailer was observed. No manifest,
payload-property contents, keybag or payload bytes were returned.

Public [img4tool's IM4P implementation](https://github.com/tihmstar/img4tool/blob/381f5f755bdafe73eddec4eb83c25d21488621ab/img4tool/img4tool.cpp#L408-L450)
handles payload-scoped PAYP properties in an optional context-[0] field. That
is a format hypothesis for this field, not a validation of its unseen contents.
An independent [PyIMG4 implementation](https://github.com/m1stadev/PyIMG4/blob/3c857e03ccfbaca503fcd8dcc3693fbf101b233e/pyimg4/parser.py#L1015-L1062)
also separates context-[0] properties from compression SEQUENCE metadata.
The original reader treated every non-keybag extra as compression metadata and
therefore rejected this form. Extending our original metadata reader to skip
one bounded final opaque context field permits payload comparison without
parsing or authenticating that field. It must keep envelope/restoration/default
claims separate from a possible exact known-payload relation.

The final human-run updated reader returns **`payload_relation:EXACT_31AF`**.
Its entire 442,368-byte OCTET payload equals the already hash-verified reference;
this is a byte comparison rather than identification by length. Boot021 is not
the current selected lab payload. The separate full-wrapper `match` remains
UNKNOWN because the A0 contents are opaque. Wrapper authenticity, property
effects, effective CTRR/policy, default selection and completed restoration
remain unverified. No further metadata query is needed to establish this
contained-payload identity. No compressed or encrypted payload has been decoded,
no Apple bytes have been copied into the implementation, and no boot or policy
change follows.
