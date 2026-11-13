# 31AI independent M1 offline review — 2026-11-13

**OFFLINE_REVIEW_PASS_NATIVE_HOLD.** Reviewed Git
`8f53ebf281a7a62943b0a937a05b449e3e51f9b8`. Both local-user files arrived
intact. No actionable artifact-integrity or static transport/layout failure found.
No restart or physical test is ready from this review.

## Fresh checks

| Item | Result |
|---|---|
| Frozen 31AH inventory | 41 entries PASS, unchanged |
| New 31AI inventory | 46 entries PASS |
| Inline / extender methods | 37 / 22 PASS |
| Diagnostic-package / restoration-model methods | 40 / 40 PASS |
| Candidate-reader / selected-object methods | 33 / 49 PASS |
| Total new host-safe methods | **221 PASS** |
| Actual two-file intake | **OFFLINE_CANDIDATE_INTEGRITY_PASS** |
| Actual public Aura source files | 26 selected Git blobs PASS, read as data only |

31AI source-inventory SHA-256:
`39dbbd5795b02f61621797f86cd246a932e974c745096dd31a02687bb6b60d31`.
The unchanged 31AH inventory remains
`67b9d70018498cb4bacbbe05081e6a233b838af89d8c722983f804f2c14dc3a5`.

| Delivered data | Bytes | SHA-256 |
|---|---:|---|
| Compressed candidate | 15,984,123 | `5fef4ae42dff069e442c22963a548c86ee41347b76d6ec3cab52003860ad1bc1` |
| Diagnostic archive, 19 files | 16,031,305 | `4c04cbd098fcec92f55c91fe8bb33dc7baae2e86c7586a0ca88fac7879543019` |
| Expanded candidate, memory only | 153,190,400 | `0d43feada6d758fcfea2ce78b4fd9f21ae4b7a7450ab06ba9e8c6c06b834dc4d` |
| Raw inline input | 19,639,230 | `5f351f1f4841f0d5fcee2d16a5eed71ed6be46c95b16ba92e0295440a725f8cc` |

Files stayed compressed on disk. The readers validate complete bounded gzip/CRC,
strict nineteen-file USTAR contents and exact executable/object/source/reference/
relink/VM bindings in memory. No downloaded code executed, archive extracted,
module loaded, Apple inspector invoked, VM started or device opened on M1.

## Independent assessment

**Confirmed offline:** the candidate retains exactly the 3,997,696-byte unchanged
baseline Aura prefix, six nested Mach-O segments, fixed entry offset 67,584,
canonical metadata and zero execution padding. Its parsed payload equals the
transferred frozen Image, sanitized eighteen-node DT and diagnostic initramfs.
The exact root contains four empty directories and one static AArch64 `/init`;
no module or storage utility is delivered in that root. The formerly absent
runtime/root is now locally available and pinned. Public glibc source/notice
closure remains explicitly incomplete; no public binary release is proposed.

Actual downloaded public source at Aura
`bd9f3e8273dc79ae9095c19c2c4f32218446ad4e` matches all 26 selected Git blobs.
Reading [payload.c](https://github.com/aurora-silicon/aura/blob/bd9f3e8273dc79ae9095c19c2c4f32218446ad4e/src/payload.c)
confirms the ordered DT/gzip-Image/tagged-initrd/config route, heap retention of
compressed inputs and native-payload path. The separate baseline selection avoids
the optional experimental USB2 delta and does not require an M1 proxy upload.
It does not promise a Linux USB gadget or remote shell.

Source [ctxr_exec.c](https://github.com/aurora-silicon/aura/blob/bd9f3e8273dc79ae9095c19c2c4f32218446ad4e/src/ctxr_exec.c)
checks the runtime slot, armed window, retained firmware/boot arguments and heap;
[kboot.c](https://github.com/aurora-silicon/aura/blob/bd9f3e8273dc79ae9095c19c2c4f32218446ad4e/src/kboot.c)
checks retained DT/initrd overlap and moves the kernel into the pool after parsing.
This supports the transient-input versus runtime distinction: nineteen MiB of
encoded input does not enlarge the four-MiB runtime. Actual protection, addresses,
heap availability and secondary startup remain native questions. Source review
is not an end-to-end hardware execution result.

The restoration model keeps object, CTRR, unrelated policy, default, paired
Recovery and original desktop separate. It requires postconditions after attempted
operations, including failure/timeout, allows no repeated native window and has
an at-most-90-second assertion cap. Its output always denies hardware verification
and write authorization. It supplies neither authentic observations nor an
executable lab-specific procedure or enforced physical timer.

**Current selected object:** M5's human-run read-only record identifies the
contained lab payload as EXACT_31AF by complete reference comparison. This is
reviewed M5 evidence, not a fresh M1 live read. Boot021 is not currently selected.
Opaque wrapper metadata leaves whole-container match UNKNOWN; it does not make
the identified payload unknown or prove corruption, effective policy, default or
restoration. No additional current-payload query is needed from M1.

## Reviewed evidence, not rerun here

M5's eight executed public-C parser controls use real scan/gzip/libfdt/profile
code with mocked heap/CPU/NVMe/DT/window/kernel-entry hooks; final main cleanup
was excluded. Its Apple inspector derives fourteen properties, kcbz zero.
Fresh collector relink is byte-equal to the earlier tested executable and its
normal/stall controls pass. The unchanged generic four-vCPU VM kernel/root
liveness is reused, not a new M5 result. No Linux binary or mock C translation
unit was compiled/executed on M1 for this review.

REA's two-query/73-word zero-mismatch record was reviewed as a sanitized
consistency summary; raw Apple evidence was not retrieved or re-audited here.
It does not qualify entry EL or whole-function/transitive semantics. Running OS
loader 18000.161.10, global Boot ROM 20457.1.29 and the actual selected lab loader
must remain distinct; public version recognition alone is not runtime qualification.
No firmware update is established as required by these records.

## Next steps and camera proposal

1. M5 completes the current-state reconciliation and concrete lab-only installation/
   complete restoration procedure, including object readback, CTRR preparation,
   unrelated-policy comparison and original/default return. A new direct candidate
   needs its own appropriate postcondition adapter: the existing current-object
   reader is capped at eight MiB and recognizes only boot021/31AF references.
   Do not repurpose its UNKNOWN result as verification of this 153-MiB candidate.
2. Qualify or explicitly bound the actual paired-firmware/native assumptions in
   that proposal. Define one diagnostic observation, an independent human timer
   of at most ninety seconds and safe failure return. No blind firmware update,
   raw-launcher substitution, settings change or automatic retry.
3. Review the completed procedure and obtain separate concrete authorization.
   Then the intended meaningful test is a RAM-only kernel/PID1/actual CPU-worker/
   RAM/timer/sixty-second liveness observation, before Omarchy performance work.

The human offered an external webcam. A **separate ten-second silent local
readability test** is useful: frame only a nonprivate M5 screen, inspect the
smallest intended console text and bottom edge, verify video-only capture,
and retain any media under ignored build. Camera connection/framing and a start
confirmation were requested; recording has not begun at this review milestone.
This optional camera test can occur without a native boot. It supplies visible
evidence, not remote Linux recovery or a stop path independent of M1.

Original five unfinished status notes and unrelated untracked review remain
byte-identical to the previous preservation checkpoint. Review used the clean
isolated checkout, fast-forwarded to the new main. No frozen artifact/source
inventory or consumed receipt was edited. Prior 31AH tests/results were reused
except the required inventory verification; no repeated old full suites.

**NOT RUN:** native entry/EL/CTXR, physical eighteen-core work, Linux runtime,
USB/N1/GPU/NVMe/performance, Recovery/install/restoration/new policy/default
checks, camera activation/recording. No Mac restarted or host setting changed.
