# Attempt29 — native memory observations and Macintosh HD return

**Observed, 2026-10-20:** one authorized native two-stage boot, one root send,
one memory-bundle send and one architectural module load completed. The final
collector result is **`MEMORY_OBSERVED`, `frequency_writes:false`,
`global_vm_writes:false`**. All 48 matrix samples and the unchanged chase28
completed. The CPU28 frequency module remained unloaded and no cpufreq policy
was present. Typing was accurate, but the human still reports **massive delay
opening applications**. Macintosh HD return was confirmed at **+321.424/600 s**.
Attempt29 is consumed; no retry or further live operation follows this result.

The sampled memory/cache attributes are consistent with normal cached memory.
The larger huge-advice allocations obtained substantial `AnonHugePages`
backing, with little difference in this fixed-order random-access comparison.
Page-local traversal was much faster at the larger sizes. These observations
do not identify a faulty memory controller, isolate TLB costs, or establish the
cause of GUI delay. Full sanitized samples and counters:
[native-observation.json](attempt29/native-observation.json).

## Provenance and bounded execution

Execution/readiness commit **`41e34a65d62f7e937d42af6df0c5e71e28311998`**;
published M5 handoff `b828d42`. [Independent M1 intake](attempt29-m1-offline-2026-10-20.md)
passed 106 methods with two absent legacy-fixture skips. Before this launch,
main was already current; the worktree was clean and all 30 source/procedure
pins, retained helper/SSH-config pins and operator public-key equality passed.
No production/test source or reviewed gate changed. The human confirmed the
restart, cable reseat, power, unlocked/open-lid, private recording and timer
procedure. M1 reader-start uptime was 4883 s; freshness is human-confirmed, not
independently inferred from that uptime. Video was not supplied for review.

| Input | Pin |
|---|---|
| Installed boot021 / clean client | `57a9339ffd1876e78297b17d34dece8cff8fa1ba` |
| Boot042 package SHA256SUMS | `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd` |
| Unchanged Image | `0b6df39566f12bcd5957e649946125a7bb0f42f31690933dc9896a2565b9b69c` |
| Retained stage one, 60,671,683 bytes | `65ea381524f266c78da0f98d42451f46fd48c94455d0734f1f6022c1d8f08c39` |
| Retained root, 2,469,319,544 bytes | `59a7383e4b6cd47712e5dc05998ab34a58d511edc0b7ee016b267a15d4fb2b78` |
| Unchanged CPU/memory candidate DT | `aa9731d1ba8246a9441a85dcbf59bf65cfe82c7a8d33439e9d2cdc40cb0ee725` |
| Memory-observe launcher | `9867e619b9d6cbb340c80e6d145fef92ceeb2efbeb7b968690ac14540a92582a` |
| New 143,360-byte bundle | `561b6395d1ef9b6fcd2e8bfd8fcadaac0d449b2f952acd50d8d56913ff04f714` |
| Architectural module | `730bdfe809dd7a7de58bab8f707db5ee593549a9c2e711d8a8e17f9727b54f7c` |
| Memory29 benchmark | `9460ce6bfb053d508387688f979c7e48913e031df95a3e69a76270b2c4782b57` |

The `memory-observe` controller exited **0 in 21.841 s**, handoff
**22:54:01.679 UTC / 6:54:01 PM Eastern**. Live target/version/boot021 marker,
no started secondaries, GPIO ADT/effective DT, both DAPF checkpoints and early
framebuffer descriptor checks PASS. One core, userspace-governor argument,
`idle=nop arm64.nowfxt` and disabled NVMe were retained. No operator overlay,
network relay, clock step, forwarding, CPU28 load or extra probe was added.

Stage one showed `WAITING FOR STAGE TWO`. Its unique journal/panel fingerprint
matched by human comparison; sender known-host/journal equality also passed.
One root send: **85.3 s** as M1 wrote, **85.4 s / 28.9 MB/s** at the receiver.
The receiver verified the exact size/hash, unpacked **215,521 entries / 10.3 GiB
in 19.5 s**, and requested switching. Sender exit 0 after 105.9 s (host supervisor
interval 107.512 s including setup). No competing SSH session or resend.

The switch supervisor armed the reviewed monotonic window once immediately
on the switch record, before observation/review. Fixed return deadline:
**23:07:07.073 UTC / 7:07:07 PM Eastern**; the human was told to start the timer.
An independent local guard could stop this run's reader, not reboot the M5.
First reader exit 0, **56,390 raw bytes / 663 lines**, device disappearance
22:57:08.930 UTC. Second reader first observed the link 22:57:33.992 UTC;
this is observation time, not a precise re-enumeration measurement.
Automatic keyboard steps 0–5 passed at kernel 191.358247 s; Hyprland declared
ready at 198.725978 s, about 13.9 s after the switch request 184.866993 s.
The human confirmed Omarchy and left it idle for collection.

One no-forwarding `true` bootstrap exited 0. The root journal key was unique,
distinct from stage one's, and matched the exact root known-host entry before
each helper SSH. The 143,360-byte bundle was sent only to the reviewed tmpfs
receiver, which checks size/hash/member pins before execution. Memory helper
exit 0; collector interval **12.640 s**. Its 160 s internal, 170 s systemd (+5 s cleanup)
and 190 s M1 limits were unchanged. Both desktop snapshots also exited 0.

## Architectural evidence

Actual Linux CPU0 remained **MPIDR `0x40000`, part `0x068`, one online CPU**,
kernel `7.1.9-g863199d8b4a3-dirty`. The native identity guards and existing
CPU-asset checks passed. Exactly one `ilinux_mem29` architectural snapshot was
captured; no `apple_soc_cpufreq` load or policy initialization in this run.

| Observation | Native result |
|---|---|
| MMU, data cache, instruction cache | Enabled |
| TG0/TG1 | 2/1: 16 KiB base granules |
| Both table-walk inner/outer cacheability | 1/1: write-back, read/write allocate |
| Both table-walk shareability | 3: inner-shareable |
| Normal memory attribute index 0 |`0xff`, Normal write-back |
| Sample loader stack mapping |Valid, level 3, page_shift 14, attribute index 0/`0xff`, inner-shareable |
| Cache sysfs inventory |64 KiB L1D, 128 KiB L1I, 8 MiB unified L2; shared CPU list 0 |
| PMD huge-page size |33,554,432 bytes (32 MiB) |
| Existing THP settings (read only) |enabled `[always] madvise never`; defrag `always defer defer+madvise [madvise] never` |

These architectural readings cover the module loader's initial stack mapping,
not every application or benchmark PTE. Missing sysfs coherency-line-size
fields remain null. No MMIO, system-register write, page-table modification,
cache flush, memory-controller or global VM operation was performed.

## CPU estimate, unchanged chase, and 48-sample matrix

Dependent-ADD estimate **2.651 GHz before / 2.649 GHz after**, three repetitions
each, CPU boundary 0→0. This assumes one cycle per dependent ADD; it is not clock
telemetry, a simultaneous per-memory-sample clock or an energy measurement.
Pre/post snapshots have **no cpufreq policies**, online list `0`, and unavailable
thermal zones, energy and power (all null). No safe transition cap is inferred.

The unchanged chase28 measured medians over three samples:

| Working set |ns/load |
|---|---:|
|16 KiB |1.145 |
|4 MiB |9.305 |
|32 MiB |333.329 |
|128 MiB |341.442 |

Memory29 uses its separately documented 32 MiB-aligned allocation and local/global
layouts, 128-byte links, fixed permutation seed, full graph validation/warmup and
three samples per condition. All 48 sinks 0, all allocation-advice returns 0.
Every sample has 16 KiB base pages and CPU0 at both boundaries. Shipping VM-built
benchmark: GCC 16.1.1, `-O3 -march=armv8.4-a -Wall -Wextra -Werror`.

| Size |Layout |Base median ns/load |Huge-advice median ns/load |Base / huge `AnonHugePages` KiB |
|---|---|---:|---:|---:|
|16 KiB |global-random |1.145 |1.137 |0 / 0 |
|16 KiB |page-local |1.145 |1.146 |0 / 0 |
|4 MiB |global-random |9.549 |10.068 |0 / 0 |
|4 MiB |page-local |11.764 |8.920 |0 / 0 |
|32 MiB |global-random |335.221 |331.144 |0 / 32,768 |
|32 MiB |page-local |90.055 |89.909 |0 / 32,768 |
|128 MiB |global-random |350.004 |339.354 |0 / 131,072 |
|128 MiB |page-local |92.805 |94.888 |0 / 131,072 |

Backing counts above were equal before/after each timed sample and stable across
its three repetitions. The 32/128 MiB huge-advice allocations therefore obtained
substantial actual reported huge backing; the 16 KiB/4 MiB ones did not. `smaps`
is not a complete census of all mTHP sizes or a direct hardware TLB observation.
The JSON preserves every sample's backing, placement, faults and switches:
**one minor fault total** (first 16 KiB base/global sample), **zero major faults,
zero voluntary switches, 70 involuntary switches** (0–13 per sample).

**Measured:** larger page-local traversal is much faster than global random,
while huge backing changes those larger medians modestly in this run. Fixed
order, three short samples and single-core software-rendered desktop background
work limit interpretation. Page-local changes both cache and translation
locality; it does not isolate TLB cost. Do not call the small huge-advice
differences a repeatable speedup, prove memory-controller health from one
mapping, or turn an allocation hint into a global policy recommendation.

The existing macOS references differ in QoS/core/frequency/compiler and are
not a matched comparison. No macOS parity ratio, memory/DCS-clock observation,
thermal headroom, energy efficiency or explanation of GUI delay is established.

## Desktop, return, warnings and local collection limits

The human finished menu open/close, terminal typing `omarchy`, and file-manager
open/close. **Typing accurate; massive application-opening delay remains.**
Zero menu pollers before and after; repeat delay 1000 ms; mapped graphics libraries
include Mesa/Gallium/LLVM software-renderer components as before. Six-second
idle snapshots showed 8% busy before, 0% after at printed integer precision;
they measure neither frame latency nor power, particularly with `idle=nop`.
No settings change or additional rendering/clock experiment was bundled.

Second reader exit 0: **207,857 raw bytes / 2,196 lines**, ending 23:01:48.563 UTC
during the instructed power-off/return. Last captured journal timestamp
kernel 432.162981 s. No panic/Oops/BUG/SError/USB bus-error/translation-fault line
was found with whole-token matching, and no M1 panic was observed. Keep existing
PMGR probe error -22, first-boot hardware/CLI Netfilter failures, teardown
transaction/udev conflicts and portal/BlueZ D-Bus warnings
as unresolved observations; this diagnostic did not repair them.

Two local parsing mistakes are retained. An overbroad substring fault scan
matched `QDBusError` in userspace portal/BlueZ warnings; review of the same log
with token boundaries found no kernel fault. Bootstrap and observation SSH
had not started at that false alarm; the earlier launch/root transfer were
not retried. Separately, the
documented desktop probe emits sectioned text; the before file was accidentally
named `.json` and one local JSON parse failed. It was read as text without
repeating the probe. Neither changed published source, gate logic or counts.

Return requested at window +285.598 s; Macintosh HD desktop confirmed
**23:02:28.503 UTC / 7:02:28 PM Eastern, +321.424 s**. Fixed 600 s deadline met
without extension. Both readers had ended; this run's caffeine assertion and
deadline guard were stopped. No SSH/relay/clock session remains. Routine policy
and default-disk rechecks remained waived: original Full/lab Permissive and
Macintosh HD default are last reported, not freshly reverified. Installed
m1n1, volumes, boot/security/default settings and firmware were untouched.

## M5 next — offline review, no automatic live action

Use the README's **normal attributes / little verified page-size effect** branch
as a candidate direction, with the caveats above: investigate the actual core/
SMP path, profile software rendering, and keep memory/DCS request lifecycle
separate from CPU frequency. Any positive page-size/locality proposal needs a
controlled, interleaved follow-up before a product-wide change. No live retry,
frequency/voltage/controller write, SMP, storage, Wi-Fi, installation or setup
operation is authorized by this passing diagnostic. Private journals, receipts,
keys, media, images and Apple artifacts remain outside public Git.
