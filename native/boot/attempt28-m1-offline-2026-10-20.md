# M1 offline readiness — attempt 28 CPU observation

2026-10-20. Fast-forwarded main to
**`7c757ebe300591a5d0addeb13a5cf5b145b68b76`**, preserving local files.
Read the current coordination/checklist, validation record, changed launcher
and DT guard, `cpu_observe.py`, native `observe28.py`, driver patch and M1
collector. **Offline ready with the test limits below.**

**Native attempt 28, live target-version checks, CPU module initialization and
native measurements: NOT RUN. Attempts=0; stage-two sends=0.** No live USB or
M5 SSH session opened, real observation window armed, CPU request, restart or
boot/settings/volume change occurred. Routine policy checks remain waived;
original Full/lab Permissive are last reported, not freshly checked.

## Verified private pair and assets

Both images arrived at the repository root. Hashed both against the new Git
records before reading an embedded member, then moved the verified files into
ignored `build/attempt28/`. All older images and attempt-27 evidence remain.

| File | Bytes | SHA-256 |
|---|---:|---|
| Stage one | 60,671,683 | `65ea381524f266c78da0f98d42451f46fd48c94455d0734f1f6022c1d8f08c39` |
| Omarchy root | 2,469,319,544 | `59a7383e4b6cd47712e5dc05998ab34a58d511edc0b7ee016b267a15d4fb2b78` |
| Recorded CPU module | 84,824 | `67faac4a459a6af68923f8974f95b696226941126fb0a0d713377cc0071c0d17` |

Pair verifier **PASS**: embedded root/kernel/size/hash agree with both records;
**215,521 entries**, **11,012,784,128 bytes** in the recorded 16 KiB page budget.
The embedded CPU `assets.json`, read from the verified root using macOS tar,
is **byte-identical** to Git. It names six hashed assets, attempt 28 and
`frequency_writes:false`; compiler flags are **`-O3 -march=armv8.4-a`**, pthread
for the existing CPU/memory benchmarks. The module digest above is the asset
record's pin, not an independently rebuilt M1 artifact. No image was unpacked
to disk or executed, and the M1 did not repeat M5's full content/VM inspection
or independently hash every embedded asset member.

## Package, launcher and controller

* **13-file boot042 intake PASS**, including checksums and declared m1n1
  revision; SHA256SUMS digest
  `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd`.
  Unchanged Image
  `0b6df39566f12bcd5957e649946125a7bb0f42f31690933dc9896a2565b9b69c`.
  Installed boot021 unchanged; clean client remains pinned to
  **`57a9339ffd1876e78297b17d34dece8cff8fa1ba`**.
* All **15 source digests PASS** against `attempt28/source-sha256.txt`.
  New reviewed launcher:
  **`a2b085ddb09fe5cd1931ef4c508210426d4d0a9b508e970afc00a742abe27097`**.
  Pinned input Stage-B DT
  `17c55af9eb39ea799e254335176e9748193237dce3735f59cd286a63ea0a0405`;
  CPU candidate
  `aa9731d1ba8246a9441a85dcbf59bf65cfe82c7a8d33439e9d2cdc40cb0ee725`.
* Offline **`cpu-observe`** launcher PASS: exact payload/DT guards,
  userspace governor, no operator-key overlay, one-core arguments, required
  `idle=nop arm64.nowfxt` append, NVMe still disabled, **OFFLINE ONLY**.
  Estimate **105,351,258 upload bytes**, **21.1 s at 5 MB/s**, deadline **300 s**;
  these are estimates, not native timing. Old profiles retain their guards.
* New-root sender dry-run verifies size/hash and reports **no session opened**.
  Eleven retained helper binary/source pins match attempt 27. Derived operator
  public key matches authorized_keys. Offline `ssh -G`: stage one root/m5s and
  root-Omarchy user/m5o have separate known-host files, no connection sharing
  or agent forwarding; attempt-28 forwarding-disabled overrides verified.
  Existing host-key files were retained; clear only the two lab files at the
  later authorized boot. No relay or clock step started.

## Independent M1 test results

| Suite | PASS | SKIPPED |
|---|---:|---:|
| CPU profile / exact payload and fake handoff | 19 | 0 |
| Earlier RAM-root profiles | 43 | 2 |
| Native collector, synthetic fixtures | 12 | 0 |
| M1 key/deadline collector | 11 | 0 |
| Pair verifier | 8 | 0 |
| Sender, fake transport | 18 | 0 |
| Launcher and launcher ADT via pinned client | 43 | 0 |
| **Total methods** | **154** | **2** |

All seven suite processes exited 0. The two skipped tests require boot035's
Image and boot040's Image/DT at absent legacy fixture paths; they were not
executed or counted as passes. Current boot042/new-stage-one payload cases
executed without skips. No source or test repair was needed for this intake.
Unchanged USB/proxy/clock suites retain their earlier results and limitations;
they were not rerun or counted again, and proxy/clock are not used in this run.

A local receipt-handling assertion initially expected the literal string
`PASS`; the package verifier's successful status is instead
`checksums_and_declared_revision_verified`. It prevented moving the files, and
a following tar command failed on the not-yet-moved path. Corrected only the
local harness, then moved the already verified images and read the member.
This was not a checksum mismatch; no unverified image was read, live action
performed or production code changed. The local note remains with receipts.

M5's separate evidence remains qualified: its first full-pair VM harness failed
on QEMU's four-byte CPU `reg` exception after transfer/desktop/second SSH passed;
the fresh normal-path VM run passed after correcting that probe. Neither run
loaded the native module or emulated t6050 command MMIO. See
[validation and original failure](attempt28/validation.md). No M1 claim of
native CPU mapping, measured frequency, thermal safety or efficiency follows.

## Ready for the human-started procedure

Follow [the attempt-28 checklist](../../tools/m1n1-client/attempt28-instructions.md).
Before live work: established fresh-M1-restart/cable-reseat, unlocked/open lid,
power and private recording procedure, then the human selects the existing
iLinux Boot Lab entry and explicitly starts the one boot/send. No restart or
live authorization is inferred from this offline report.

At the root switch, arm the single **600-second monotonic observation window**
and human-visible return timer before evidence review; do not rearm. Root key
verification gates measurement SSH. CPU collection is bounded at 180 s internally,
190 s in systemd and 210 s on M1; desktop collection at 40/45 s. Explicit
immutable module parameters **writes=0 / cap=0**; no module autoload or reload.
Missing/unknown OPP or telemetry is recorded literally and permits no frequency
increase. Any STOP ends the attempt; no retry. Return to Macintosh HD by the
fixed timer, with no security/default/volume change or repeated routine policy
check. No storage, SMP, N1/Wi-Fi, graphics-setting or agent-setup work is included.

Private receipts, logs, image pins and readiness state are under ignored
`build/native-intake/attempt28/`; images remain private. No live observation
deadline has been armed. **Offline blockers: none for this documented scope.**
