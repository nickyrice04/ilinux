# Attempt 28 — native CPU observation, no frequency writes

**Observed, 2026-10-20:** one authorized two-stage boot and one root send PASS.
The CPU collector initialized its explicitly no-write policy, observed CPU0's
command state, and completed both short measurement sets. Its result is
**`OBSERVED_WITH_POLICY`, `frequency_writes:false`**. Desktop checks completed:
typing is accurate, but the human still calls application response massively
delayed and unusable. The human returned to Macintosh HD within the fixed
600-second observation window. No retry, extra module load, frequency/voltage
request, new core, storage test or boot/settings change occurred.

**M5 handoff priority:** the human explicitly asks that **memory be considered
as a possible contributor to slowness**. Keep CPU state, cache/memory behavior
and software drawing as separate investigation targets. This run supplies a
controlled short pointer chase; it does not establish which causes app latency
or establish a macOS performance/efficiency gap.

## Provenance and launch

Execution commit **`f5f11c1c5d85a7692186087110bd384d1f7c8e4d`**, readiness on
handoff `7c757eb`: [independent M1 intake](attempt28-m1-offline-2026-10-20.md),
**154 methods PASS / 2 absent legacy-fixture SKIPS**. All 15 published source
pins, helper binaries/config and both whole-image hashes were rechecked before
launch; all production source pins still match after the run. The M1 restarted
(uptime 332 s before preparation). Recording and timer readiness were confirmed.
Read-only discovery found one primary and two modem interfaces, without opening
a port. Only the two documented lab known-host files were cleared.

| Input | SHA-256 / pin |
|---|---|
| boot021 installed m1n1 / clean client | `57a9339ffd1876e78297b17d34dece8cff8fa1ba` |
| boot042 package SHA256SUMS | `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd` |
| Unchanged Image | `0b6df39566f12bcd5957e649946125a7bb0f42f31690933dc9896a2565b9b69c` |
| Stage one, 60,671,683 bytes | `65ea381524f266c78da0f98d42451f46fd48c94455d0734f1f6022c1d8f08c39` |
| Root, 2,469,319,544 bytes | `59a7383e4b6cd47712e5dc05998ab34a58d511edc0b7ee016b267a15d4fb2b78` |
| CPU candidate DT | `aa9731d1ba8246a9441a85dcbf59bf65cfe82c7a8d33439e9d2cdc40cb0ee725` |
| Reviewed launcher | `a2b085ddb09fe5cd1931ef4c508210426d4d0a9b508e970afc00a742abe27097` |
| CPU module, 84,824 bytes | `67faac4a459a6af68923f8974f95b696226941126fb0a0d713377cc0071c0d17` |
| Exact short chase | `7c880b2af9f0b89befea66badb08306298c3f0563c249279e86ddc77fa618bb6` |

All six CPU assets passed the native collector's own hash check before loading
the module. Full remaining asset pins and compiler metadata are in
[assets.json](attempt28/assets.json). Benchmark flags: **`-O3 -march=armv8.4-a`**;
the existing CPU/memory programs use pthread. These are shipping VM-built
artifacts, not binaries rebuilt or executed on the M1.

The `cpu-observe` controller exited **0 in 22.179 s**. Live target boot021/no
secondaries, GPIO ADT, final Hardware DT, both DAPF checkpoints and the early
framebuffer descriptor checks PASS. Handoff **21:40:13.930 UTC / 5:40:13 PM
Eastern**. Fixed arguments retain one core, `idle=nop arm64.nowfxt`, userspace
governor and disabled NVMe. No operator overlay, relay, clock step or forwarding.

## Delivery, second link and deadline

* Stage one showed `WAITING FOR STAGE TWO` within the gate. Human panel/journal
  comparison and sender known-host/journal comparison PASS; fingerprints private.
* One root send: **2,469,319,544 bytes**, **84.9 s** as M1 wrote, receiver
  **85.0 s / 29.1 MB/s**. Exact size/hash verified remotely; **215,521 entries,
  about 10.3 GiB** unpacked into RAM in **19.5 s**. Sender exit **0**, reporting
  the switch after **105.6 s** (host process interval 107.268 s including setup).
* Switching requested at kernel **255.111943 s**, soft-reboot at **257.890695 s**,
  automatic keyboard PASS at **261.592775 s**, Hyprland readiness at
  **269.668015 s** (14.556 s after switch request). Human confirmed Omarchy
  desktop and left it idle for CPU collection. No module autoload preceded it.
* A local supervisor detected the sender's switch record and immediately armed
  the reviewed monotonic window once, before review or observation SSH.
  Deadline **21:54:29.622 UTC / 5:54:29 PM Eastern**; human timer instructed.
  An independent bounded local guard was also armed to stop the reader at expiry.
* First reader exit **0**, **59,672 bytes**, disappearance at
  **21:44:31.420 UTC** during the switch. Second link first observed by the new
  reader at **21:44:59.777 UTC**; this is an observation time, not an exact
  re-enumeration timestamp. Two interfaces; root's new key in journal.
* One no-forwarding `true` bootstrap exited **0**. The reviewed helper verified
  the distinct root journal key against its exact known-host entry **before
  CPU and both desktop SSH collections**. Each collector exited **0**; sessions
  were sequential. No key-parser workaround, manual SSH observation or retry.
* Second reader exit **0**, **206,798 raw bytes / 2,231 lines**. It disconnected
  at **21:51:38.456 UTC** during the instructed power-off/return. The stop check
  found it already ended; this run's caffeine assertion was stopped. Last
  captured journal event: kernel **631.492637 s**. No kernel fault preceded it.
* Human return was confirmed and durably recorded at **21:53:49.633 UTC**,
  about **560 s of 600** from window start. **Deadline met, no extension.**
  Deadline guard stopped after confirmation; no run reader, SSH, relay or clock
  process remains. Routine policy rechecks were waived: Full/Permissive/default
  remain last reported; no fresh policy or default-disk claim.

## Actual boot core and command state

Linux CPU0's actual DT node reports **MPIDR `0x40000`, cluster 0/core 0**;
implementer **`0x61`**, part **`0x068`**, variant **`0x1`**, revision **1**.
Its association in the exact package DT is **`apple,sotra-m`**. This identifies
the observed core without relying on the old efficiency-core hypothesis.
Online CPUs remained **`0`**, kernel **`7.1.9-g863199d8b4a3-dirty`**.

Before module: no cpufreq policy. The sole load used immutable
**`ilinux_enable_writes=0 ilinux_max_pstate=0`**. The command-only observation:

```text
DVFS command 0x0000000000400106
requested p-state 6; writes 0; cap 0
```

Initialization PASS: **policy0**, `apple-cpufreq`, **userspace**, related CPU `0`.
Requested-state fields stayed **2,652,000 kHz** after registration and at final
snapshot. The advertised OPP table spans 1,344,000–4,380,000 kHz; its maximum
is **not** a selected live transition cap or proof of attainable frequency.
The module's target callback remains write-disabled regardless of that table.
No unknown STATUS register, PLL, voltage or secondary-start operation ran.

## Short CPU and cache/memory observations

The native collector completed in about **20.50 s**, pinned to CPU0, with
one-second gaps and the documented child/180 s internal/190 s systemd/210 s
M1 bounds. The second set follows policy registration with writes still off;
it is not a frequency-change experiment. Three CPU repetitions per summary.

| One-core measurement | Before module | After no-write module |
|---|---:|---:|
| Dependent-ADD clock estimate, GHz | 2.650 | 2.651 |
| FMA assembly median, GFLOP/s | 60.460 | 60.526 |
| Integer-mix median, Gop/s | 10.068 | 10.067 |
| STREAM copy, reported median GB/s | 48.12 | 48.44 |
| STREAM scale, reported median GB/s | 47.84 | 48.00 |
| STREAM add, reported median GB/s | 49.83 | 49.21 |
| STREAM triad, reported median GB/s | 49.32 | 49.94 |

The estimate assumes one cycle per dependent ADD. Its agreement with the OPP
mapping supports a clock near 2.65 GHz during this short work, not independent
hardware frequency telemetry or a parity claim. STREAM used 128 MiB **per
array**, three requested repetitions; output retains **two** measured samples
after warmup. Do not relabel them as three retained samples.

Pointer chase: fixed-seed full-cycle permutation, 128-byte links, full warmup,
three samples per size; at least 262,144 dependent loads, 1,048,576 at 128 MiB.

| Working set | Before, median ns/load | After, median ns/load |
|---|---:|---:|
| 16 KiB | 1.142 | 1.144 |
| 4 MiB | 9.287 | 8.922 |
| 32 MiB | 331.582 | 331.790 |
| 128 MiB | 333.914 | 337.458 |

**Measured:** the larger working sets cost much more per dependent load than
the small ones. **Hypothesis:** cache/memory/translation behavior could
contribute to application delay, as the human requests M5 consider. These
numbers do not attribute that delay or compare like-for-like with macOS.
The old attempt-20 604–617 ns result used a different protocol; do not claim a
memory improvement by subtracting it from this run. M5 should inspect the
protocol, core/affinity and memory/cache configuration, and obtain a matching
macOS baseline before choosing or attributing the next hardware change.

**Unavailable:** thermal zones **null**, energy **null**, power **null** in
every snapshot. This was short work, not a thermal soak. Idle percentages or a
frequency mapping do not establish power efficiency, headroom or safety of an
increase. Native DVFS transitions and a defensible thermal/cap plan remain open.

## Desktop, faults and limits

Both key-gated desktop snapshots completed. **Zero menu pollers before and
after** the human's menu/terminal/file-manager sequence; repeat delay **1000 ms**,
rate 40. Six-second idle samples **0% / 1% busy**, with `idle=nop` still set;
this does not measure energy. Display **3456×2160**, scale 1, XRGB8888,
reported 60 Hz; no GPU or rendering-setting change. Human: typing accurate,
application opening still massively delayed and unusable. No instrumented
application/frame-time distribution or new controlled input-injection test.

Kernel-only fault scan: **zero BUSERR, translation-fault, nobody-cared,
kernel-panic or unhandled-fault lines**; no M1 panic observed. Early `cs` PMGR
state failure / `pm_genpd_init` / probe `-22` remain. Three gadget teardown
udev transaction conflicts and the known UFW, hardware-provisioning and user
document-portal start failures are present in the capture. Loading the experimental
out-of-tree module taints the kernel as expected. A fresh `systemctl --failed`
census was not part of this collector; do not infer all service failures are
resolved. Recording was confirmed, but no new video was available for review
when this report was written; screen outcomes here are human/journal evidence.

One local preparation error was contained before launch: discovery succeeded
but the local harness expected JSON from its text receipt. The same successful
receipt was parsed correctly; discovery was not rerun, no target request was
sent by it, and only one launcher was invoked. No production source was edited.

**Consumed:** one launch, one send, one CPU load/collection, two desktop
collections, confirmed return. All private evidence remains in ignored
`build/native-intake/attempt28/`; no image, key, raw diagnostic or media pushed.
No frequency/voltage writes, retry, reboot loop, SMP, storage, Wi-Fi, renderer
change, agent setup or boot/security/default/volume modification. Next is M5's
offline review, explicitly including memory; another live attempt needs its
own reviewed scope and human start.
