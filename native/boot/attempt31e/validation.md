# 31E offline validation — native launch remains held

> Historical offline-proposal milestone. Current native-controller scope and validation: [controller-review.md](controller-review.md) and [controller-validation.md](controller-validation.md).

2026-10-21. Tested checkout: `37f25cb` plus the source snapshot pinned by
`native/boot/attempt31e/source-sha256.txt`. **38 pinned files**, manifest SHA-256
`f6cb4ff15a2ce3cebe7af1d0d6aad04678a62af0de1f42b4f2c8ef0faca9d6bc`.
No physical USB operation, CPU1 start, live code patch or installed-image,
boot-policy, volume, firmware or macOS change occurred during this work.

## Results

| Check | Result and scope |
|---|---|
| Existing 31D report | Reviewed; CPU1 entry remains unverified after 171 no-record samples. Prior evidence and controller sources preserved. |
| REA/Ghidra | Two bounded functions; 96 instruction words match original carrier bytes and Apple LLVM; raw artifacts remain private. No additional CPU1 power write established. |
| macOS image-only intake | 77 Python methods PASS; no full symbol-file or full recorder-layout claim in this mode. No native adapter exists. |
| ARM64 VM intake | **110 Python methods PASS**, including complete image/symbol checks, builder layout and recorder equivalence; 38 source pins PASS. |
| Original entry interpreter | Eight scenarios, actual pinned public instructions, explicit synthetic RAM/register state. First saved LR at entry SP minus 24. |
| Recorder equivalence | Eleven modeled scenarios; all 16 initial flag patterns across successful paths. Selected SCTLR faults stop at partial phase 2. |
| Observation interleavings | 140 monotonic publication schedules, failures at all 11 reads and malformed values; both partial reset-publication orders supported. |
| Campaign replay | 31B/C/D public summaries plus 27 stage-failure injections, late replies, lost acknowledgments and mixed-session rejection. No hardware resume. |
| Actual ordinary ARM64 STP | Four patterns/full-buffer canaries PASS in GCC, Clang and GCC ASan/UBSan builds inside Linux. No privileged reset code executes. |
| Original recorder assembly | GNU as and Clang independently produce **204 bytes**, identical to the Python encoder; linker target/replay correctness checked by byte comparison. |
| Native performance/energy | **NOT MEASURED.** No claim of CPU1 arrival, Linux SMP, all cores, hardware compatibility, speedup or efficiency gain. |

Method breakdown: campaign 21; entry classifiers 6; entry audit 4; observer 18;
original-entry interpreter 22; intake source closure 6; recorder builder 14;
recorder equivalence 19. The M1 image-only mode omits the two full-symbol suites
(14 + 19) and explicitly reports those checks as NOT RUN, rather than silently
skipping tests.

## Environment and build

Existing ARM64 Linux VM, 12 vCPUs / 24 GiB; no physical Apple-device pass-through.
Guest `Linux 7.1.6-vzrun2 aarch64`, Python 3.14.8, GCC 16.1.1 (20260430),
Clang 23.1.1. This is the project's existing isolated VM, not native Linux on
the M5's hardware interfaces.

Normal C harnesses: `-O2 -std=c11 -Wall -Wextra -Werror`.
Sanitizer harness: `-O1 -g -fsanitize=address,undefined
-fno-omit-frame-pointer`, with the same warning policy. The assembly-only
recorder uses `-march=armv8.2-a`, link VMA `0xa00`, and explicit linker symbols
for record `0x90a40` and resume `0x900`. Generated outputs remain ignored.

All three recorder byte streams have SHA-256
`9fa1f68b849a7049481cb1a83e645ccd43ca61a0d5df11d6bf7ca76dffd00335`.
The original image remains
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.

Reproduce the full VM validation with the existing quiet/VM lock procedure and
[`job 062`](../../../virtualization/jobs/062-smp31e/run.sh). Its ignored `out/`
inputs are the retained boot021 image and original pinned symbol listing.
The decisive result is the guest job exit **0** at **21:57:15 UTC**, alongside
`RECORDER-ASSEMBLER-BYTE-MATCH-PASS` and `SMP31E-OFFLINE-PASS`; the VM runner's
own exit status alone is insufficient.

## Failures caught and fixed offline

1. The first VM run refused because a test tried to create scratch files under
   the read-only source share. Test scratch now uses temporary directories;
   production output containment remains enforced.
2. Clang rejected an unaligned absolute ADRP operand. A subsequent assembly
   comparison found that both assemblers interpreted the absolute return
   operand as a displacement, producing the wrong branch despite the Python
   encoder being correct. The source now uses real linker relocations for
   both addresses. Both assemblers then match every byte.
3. Independent reviews caught an unsupported AND-to-SP decoder form and an
   output symlink/hardlink containment weakness. The former now refuses
   explicitly; the latter uses checked leaves and atomic replacement, with
   regression coverage. The actual retained reset path was unaffected.

Private logs of the three failed VM invocations and the final successful run
are retained in the ignored job output. No gate, compiler warning policy or
hardware protection was relaxed to obtain a pass.

## What is ready, and what remains

The offline tools, original recorder bytes and reproducible VM job are ready
for M1 review. The public [M1 handoff](../../../tools/m1n1-client/attempt31e-instructions.md)
contains **no native command**.

The next implementation task is a bounded native adapter for the preferred
stackless recorder: prove existing code-write alias permissions, verify exact
input bytes, order stub/branch publication and cache maintenance, add fixed
record reads, preserve partial evidence and fault counters, and integrate the
conditional timer-request sequence. It must be reviewed against the real
client serializers, exception handling and the independent deadline supervisor.
Fault models for the remaining new read/store/publication boundaries are still
required. The emulators do not model physical reset state, cache visibility,
hardware memory attributes, or asynchronous faults.

The temporary Device-memory C-stack proposal stays held; do not deploy it as
a shortcut. Do not launch Linux from an uncertain secondary state. No extra
boot-policy checks are requested. Once a reviewed live handoff exists, a helper
health gate replaces the blanket M1-restart requirement, and a fresh human
target start remains explicit.
