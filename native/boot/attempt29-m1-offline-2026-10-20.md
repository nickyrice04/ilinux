# M1 offline readiness — attempt29 memory isolation

2026-10-20. Pulled main with `git pull --ff-only` to
**`b828d42`**, preserving the supplied file and all earlier images/evidence.
Read current coordination, the complete attempt29 checklist and validation,
memory README, changed launcher, receiver, module, benchmark and collectors.
**Offline ready with the qualifications below; no blocker for this scope.**

**Native attempt29, live target-version checks, architectural module load and
memory collection: NOT RUN. Launches=0, root sends=0, bundle sends=0.** No live
USB or M5 SSH connection, real observation window, restart or settings change.

## Supplied bundle and retained pair

Verified the root-directory `memory29.tar` before moving it into ignored
`build/attempt29/`. No archive member was extracted to disk or executed.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| New memory29 bundle | 143,360 | `561b6395d1ef9b6fcd2e8bfd8fcadaac0d449b2f952acd50d8d56913ff04f714` |
| Retained attempt28 stage one | 60,671,683 | `65ea381524f266c78da0f98d42451f46fd48c94455d0734f1f6022c1d8f08c39` |
| Retained attempt28 root | 2,469,319,544 | `59a7383e4b6cd47712e5dc05998ab34a58d511edc0b7ee016b267a15d4fb2b78` |

Bundle verifier **PASS**: exactly four regular members, no extra/duplicate/
link/path/device member, total expansion bounded. All member hashes agree
with the embedded manifest, which agrees with the public asset record.
Embedded `collect.py` is also byte-identical to Git source. Members are
`ilinux_mem29.ko`, `memory29`, `collect.py`, `assets.json`; no VM-only control
module is in the accepted member set. Module pin
`730bdfe809dd7a7de58bab8f707db5ee593549a9c2e711d8a8e17f9727b54f7c`;
benchmark pin `9460ce6bfb053d508387688f979c7e48913e031df95a3e69a76270b2c4782b57`.
The M1 did not rebuild these Linux artifacts.

Retained pair verifier **PASS** after fresh whole-file hashing and embedded
root/kernel pin comparison: **215,521 paths**, recorded 16 KiB page budget
**11,012,784,128 bytes**. Neither image changed or needed another transfer to
the M1. They remain under ignored `build/attempt28/`.

## Package, source and controller checks

* Boot042 **13-file intake PASS**; SHA256SUMS digest
  `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd`.
  Image remains `0b6df39566f12bcd5957e649946125a7bb0f42f31690933dc9896a2565b9b69c`.
  Installed boot021 is unchanged; client clean and pinned to
  **`57a9339ffd1876e78297b17d34dece8cff8fa1ba`**.
* All **30 source pins PASS** against the new attempt29 record. Historical
  attempt28 pins were preserved. The reviewed launcher changed intentionally:
  **`9867e619b9d6cbb340c80e6d145fef92ceeb2efbeb7b968690ac14540a92582a`**.
* `memory-observe` offline launcher **PASS**: exact existing pair/candidate DT,
  no operator overlay, no automatic module load, userspace governor, one core,
  disabled NVMe, required `idle=nop arm64.nowfxt`, **OFFLINE ONLY**.
  Estimate **105,351,258 upload bytes**, 21.1 s at 5 MB/s; **300 s** deadline.
  These are estimates, not attempt29 native timing. Existing CPU and memory
  profiles both execute their exact-payload/fake-handoff and refusal tests.
* Sender dry-run verifies the retained root and reports **no session opened**.
  Eleven reader/pipe/source/helper pins match attempt28, as does SSH config;
  derived public key matches authorized_keys. Offline `ssh -G` confirms m5s
  root and m5o omarchy, distinct known-host files, no multiplexing/agent
  forwarding, and forwarding-disabled overrides. No key files were cleared.

## Independent M1 tests

| Suite | PASS | SKIPPED |
|---|---:|---:|
| CPU + memory observation profiles | 38 | 0 |
| Earlier RAM-root profiles | 43 | 2 |
| Bundle validation and attribute decoder | 12 | 0 |
| M1 key/window/bundle collector | 13 | 0 |
| **Total methods** | **106** | **2** |

All four suite processes exited 0. No source/test fixes or failed test reruns
were needed. Skips are the absent old boot035 Image and boot040 Image/DT
fixtures; not executed or counted as passes. Current boot042 and retained
stage-one cases executed without skips. Inherited transport tests were not
rerun or counted again because those inputs are unchanged.

M5's separate W=1/sanitizer/optimized-matrix, exact-kernel VM refusal/positive
control, macOS and REA results remain **M5 evidence**, not independent M1
repetitions or native attempt29 results. Its earlier compile/harness failures
and rejected pseudocode gates remain documented in
[validation](attempt29/validation.md). The M1 did not open private decompiler
output or execute either the bundle or VM-only control. No OS parity ratio or
desktop improvement follows from this readiness result.

## Scope and next step

The one later human-started attempt follows
[attempt29-instructions.md](../../tools/m1n1-client/attempt29-instructions.md).
It reuses the working boot and transfers only this small diagnostic into `/run`
after verifying the new root's SSH key. CPU28's cpufreq module must remain
unloaded. One memory module load reads architectural cache/MMU registers and
attributes of its loader's stack page; no addresses/contents are published.
The benchmark's base/huge advice affects only its own temporary allocations,
with actual backing/fault/context-switch/placement observations recorded.
An accepted hint does not prove huge backing; page-local traversal is not a
pure TLB test. Unknown attributes, missing telemetry or a refusal ends in
recorded evidence, not permission for a new hardware operation.

Fresh M1 restart, direct cable re-seat, power/unlocked/open lid and private
recording precede explicit human start of the existing Boot Lab entry.
Arm the single **600 s** monotonic switch-time window plus human return timer;
memory bounds **160 s internal / 170 s systemd plus 5 s cleanup / 190 s M1**,
desktop snapshots **40/45 s**. No real window is armed at readiness.
One boot/root send/collection, no retry; return to Macintosh HD by the timer.

Original macOS/default/security/volumes remain unchanged. Routine policy
rechecks remain waived; Full/Permissive values are last reported. No frequency,
voltage, memory-controller, global VM, idle, rendering, extra-core, storage,
Wi-Fi or agent-setup operation is included. Private receipts/logs/readiness are
retained under ignored `build/native-intake/attempt29/`.
