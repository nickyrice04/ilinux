# 31AI: self-contained Aura/Linux RAM diagnostic

**M1 offline review only. No restart, installation or firmware/policy change.**
This follows the [independent 31AH review](../attempt31ah-m1-offline-2026-11-13.md).
It preserves the frozen 31AH package and selects its unchanged baseline Aura
code, rather than the optional experimental USB2 delta.

## Result

A new normal Mach-O candidate contains the exact tested kernel, sanitized J716c
DT and diagnostic RAM root. Aura's native payload selection does not require an
M1 proxy upload or a Linux gadget. The compiled public parser/policy passed
eight controls in a no-NIC VM; real hardware operations and final cleanup were
mocked or excluded. This closes a concrete data-delivery gap, not native entry.

The kernel and collector remain unchanged from the tested 31AH build: sixteen-KiB
pages, SMP, source-defined eighteen M/M/P CPU nodes and CTXR execution-pool support.
The RAM root contains only `/init` and four empty mount directories. It checks
actual online/permitted CPU work, timer observations, RAM checksum and sixty
seconds of liveness. Static DT nodes are not physical CPU execution evidence.

The old formatter refused input larger than its sixteen-MiB runtime slot. The
new builder separates **3,997,696 bytes of unchanged Aura runtime** from temporary
compressed input. Total inline raw input is **19,639,230 bytes**. The selected DT
stays below the earliest pool start; Image and tagged initrd are heap-staged
before the kernel reuses the **128 MiB execution pool**. Existing runtime overlap,
firmware/read-only-range and pending-secondary guards remain intact.

A separate strict extender verifies entry/vector, nested headers, canonical
UUID/prelink identity, segment geometry and zero padding. Apple’s current trusted
read-only inspector accepts the final **153,190,400-byte** object, deriving fourteen
properties including `kcbz=0`. It does not establish actual Recovery enrollment,
protection profile, kernel entry or physical SMP. See
[inline-layout.json](inline-layout.json), [apple-inspection.json](apple-inspection.json)
and [public-parser-controls.json](public-parser-controls.json).

## Two-file private delivery

Copy the single ignored folder `build/ilinux-31ai-review/` between the user's Macs.
It contains exactly:

| File | Bytes | Role |
|---|---:|---|
| `aura-inline-128m.macho.gz` | 15,984,123 | Compressed transport of the self-contained candidate; not an installation command |
| `ilinux-direct31ai-diagnostic.tar.gz` | 16,031,305 | Nineteen-file exact diagnostic/reference/relink review bundle |

[Candidate manifest](candidate-manifest.json) binds both files through the
[diagnostic manifest](diagnostic-manifest.json). The original read-only intake
verifies all bytes and semantic payload relationships in memory, without
extracting, executing, opening devices or invoking `kmutil`. Its actual local
result is [candidate-review.json](candidate-review.json). Receiving a file through
Universal Clipboard, iCloud or a USB drive changes none of these integrity gates.

The diagnostic bundle supplies the previously omitted exact static executable
and RAM root. A fresh object relinks **byte-for-byte to the tested executable**;
normal and intentional-stall controls pass. [Relink receipt](relink.json). Common
SPDX texts and the installed GCC exception are explicitly labelled; complete
runtime attribution/public corresponding-source delivery remains incomplete.
Both binaries stay in ignored local-user handoff folders. **No public binary
Release or automatic external transfer.** No Apple firmware, decompiled code,
private keys, raw diagnostic logs or media are in the handoff.

## Firmware and current-state observations

Original and lab version plists still read **26.6.2/25G83**. Current host Boot ROM
is **20457.1.29**, while the running OS loader is **18000.161.10**. The retained
generic REA input matches that OS-loader version; this does not establish the
actual selected lab firmware image. The exact public Aura source recognizes the
current version, and its real propertyless-J716c DT selection passes at rank one
in both tested profile modes. Firmware compatibility and physical entry remain
unqualified. A version difference from the reported 27.2.1 stack does not alone
justify an update. [Research and REA limits](../../../research/direct31ai/findings.md).

The human confirms running Macintosh HD. After the optional-field fix, the
separate lab-object reader reports **`payload_relation:EXACT_31AF`**: all
442,368 payload bytes equal the hash-verified 31AF reference. The selected lab
payload is therefore identified; boot021 is not the selected payload at this
observation. The IMG4 file is 445,430 bytes, without an outer trailer. Its
final 300-byte IM4P context-[0] field remains opaque, so full-container `match`
deliberately remains UNKNOWN. The earlier refusal was a reader limitation,
not an observed malformed outer frame. This does not establish wrapper
authenticity, effective policy, bootability, default selection or completed
restoration. Keep these distinct from return to the original desktop.
[Observation](selected-object-observation.json).

Offline validation: **221 new unit methods**, eight real public-parser controls,
exact relink, actual two-file intake and trusted read-only Apple inspection PASS.
The [consolidated record](offline-validation.json) separates fresh checks,
reused generic-VM evidence and every native limitation.

## Conditions before any future physical sequence

1. M1 independently verifies the exact source inventory and both files.
2. Reconcile the now-identified current 31AF lab payload with the unfinished
   prior restoration and baseline policy/default state. Exact payload identity
   does not authenticate its wrapper or establish policy/restoration.
3. Qualify or explicitly scope the actual firmware/loader/kernel pairing. Do not
   update firmware or either macOS installation as an automatic preparation step.
4. Review one lab-only enrollment/observation/complete restoration procedure.
   Public source says Mach-O enrollment enables lab Kernel CTRR; copying raw
   boot021 bytes back does not restore that policy. Raw restoration needs its
   own owner-authorized policy preparation, object enrollment and postconditions.
   The new offline state model audits assertions; it does not perform or verify
   these operations. Failed/timeout configure never implies an unchanged object.
5. Obtain separate authorization for that concrete sequence. Preserve original
   Macintosh HD Full Security and default return. No new volumes are proposed.

The proposed meaningful next test is one bounded RAM diagnostic, not an Omarchy
performance claim. A human-operated M1 camera can record Aura/kernel/PID1 and
repeated CPU/timer/RAM summaries; USB absence is an explicit outcome. A future
plan must define its measured start and at most ninety-second external stop,
allow partial evidence, permit no automatic retry, and provide a human recovery
path independent of M1. Camera availability is inventoried only; recording,
framing, permissions and readability have not been tested.

Loader NVMe shutdown, CPU setup and PCIe/DAPF handling are real controller work
on a native machine. The RAM-root allowlist does not prove absence of firmware
side effects or make these operations safe solely because the parser mock passed.
Physical entry/EL, memory guards, all eighteen cores, CPU/memory performance,
USB/N1/NVMe/GPU and efficiency remain **NOT RUN / NOT MEASURED** for 31AI.

M1 next: [offline instructions](../../../tools/m1n1-client/attempt31ai-instructions.md).
