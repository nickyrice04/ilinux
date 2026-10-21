# Attempt30 — native desktop-latency attribution

**Observed, 2026-10-20 local / 2026-10-21 UTC:** one authorized native boot,
one root send and one userspace diagnostic-bundle delivery completed. Final
**`LATENCY_OBSERVED`**, helper exit 0; `frequency_writes:false`,
`renderer_changes:false`, `modules_loaded:false`. Both 20-callback controls and
the 45-second human observation completed, with no partial/stop event. The
human reports prompt response to the cue, accurate typing and continued delay.
Macintosh HD return confirmed at **+223.531/ 600 s**. Attempt30 is consumed;
no retry or additional live operation is selected.

Both controlled workloads were expensive: **small-damage median 256–257 ms,
full-damage median 513–516 ms**, compositor process CPU about 97% of phase wall,
and median IPC round trip about 408 ms. Main-thread software samples were mostly
anonymous executable mappings. This is evidence to investigate the expensive
draw/event-loop path; it does not identify those mappings as LLVM/Mesa raster
code or establish that every application delay has this single cause.

All callbacks, warm-ups, IPC values, CPU profiles, options and short clock
estimates are preserved in [native-observation.json](attempt30/native-observation.json).
Human action timing and M1 restart freshness have limits documented below.

## Provenance and one-use execution

M5 handoff **`cfebfb7`**, execution/readiness
**`6e49687b5dea78e597951f2a0d1fe4686ddb25e3`**. Independent
[M1 offline intake](attempt30-m1-offline-2026-10-20.md): **127 methods PASS,
2 absent legacy-fixture SKIPS**. Boot042 thirteen files, whole retained image
hashes/embedded pair, 37 source/procedure pins, eleven helper pins, exact SSH
config, operator public-key equality and offline no-forwarding checks passed.
No production/test source, reviewed guard or source-pinned checklist changed.

| Input | SHA-256 / pin |
|---|---|
| Installed boot021 / clean client |`57a9339ffd1876e78297b17d34dece8cff8fa1ba` |
| Boot042 package SHA256SUMS |`60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd` |
| Unchanged Image |`0b6df39566f12bcd5957e649946125a7bb0f42f31690933dc9896a2565b9b69c` |
| Retained stage one, 60,671,683 bytes |`65ea381524f266c78da0f98d42451f46fd48c94455d0734f1f6022c1d8f08c39` |
| Retained root, 2,469,319,544 bytes |`59a7383e4b6cd47712e5dc05998ab34a58d511edc0b7ee016b267a15d4fb2b78` |
| Unchanged CPU/memory/desktop candidate DT |`aa9731d1ba8246a9441a85dcbf59bf65cfe82c7a8d33439e9d2cdc40cb0ee725` |
| Desktop-latency launcher |`77846bc7ecd1a73aca92f031d377be800314d5b1b9e9ceebbe3fa452daf018e1` |
| Userspace bundle, 163,840 bytes |`26a36600de24360b744728aef2af1cf0b8176be172fd51b0b58f48a8bbee1f07` |
| Frame client |`985db443f7dc3a62a0f5ea524bcd8ba5c19ac3440d3ae38e13cdfb936f7f2d86` |
| Software CPU-clock sampler |`b72096d8a8c7d323417d19cd8aec37d7750b15df765a6e36a8e6f5c320df593e` |
| Collector source, byte-identical to Git |`47e3c827d597aa2b619c29a7cc1e936eabfea434a6cca42387a792c34f964c7b` |

The human reported M1 restart/Running proxy and confirmed direct cable reseat,
power, unlocked/open lid, recording and timer. **Measured reader-start M1 uptime
was 20,933 s**; a fresh restart is not independently established by that value.
Retain the human statement and observed uptime separately. No video was supplied
for independent review. Offline readiness was published before the launch.

One discovery found one primary/two modem interfaces without opening a port.
Only current lab known-host stores were cleared. The desktop-latency controller
exited **0 in 21.879 s**, handoff **03:21:24.843 UTC / 11:21:24 PM Eastern**.
Live target/boot021/no secondaries, GPIO geometry/exclusions/effective DT,
hardware DT, both DAPF checkpoints and early framebuffer checks PASS. Same
one-core, userspace-governor argument, `idle=nop arm64.nowfxt` and disabled NVMe.
No operator overlay, CPU28/memory29 load, network relay or clock step.

Stage one showed `WAITING FOR STAGE TWO`; the human compared its panel key with
the privately captured journal key. Sender known-host/journal equality PASS.
One root send: M1 **85.8 s / 28.8 MB/s**, receiver **85.9 s / 28.7 MB/s**; exact size/
SHA verified, **215,521 entries / 10.3 GiB unpacked in 19.9 s**. Sender exit 0 after
106.9 s (host supervisor interval 108.445 s including setup). No second send.

The root-switch record armed the fixed monotonic window once before review:
**03:25:08.006 UTC**, return deadline **03:35:08.006 UTC / 11:35:08 PM Eastern**.
The human was told to start the timer. First reader exit 0, 58,022 raw bytes /
679 lines; disappearance 03:25:09.831 UTC. The new reader observed the second
link 03:25:27.547 UTC (observation, not precise re-enumeration timing). Automatic
keyboard steps 0–5 PASS at kernel 228.985323 s. Hyprland ready 236.420825 s, about
13.9 s after the switch request 222.507587 s. Human confirmed Omarchy and idle.

One no-forwarding `true` bootstrap exited 0. The root key was unique, distinct
from stage one's, and matched the exact known-host entry before the reviewed
helper connected. One 163,840-byte bundle delivery into verified `/run` tmpfs;
receiver size/hash/member and source pins precede execution. One local
supervisor watched only complete local JSONL lines for the human cue, every 50 ms;
no parallel SSH or collector. Optional desktop snapshots were not invoked.

## Native identity, configuration and complete measurements

Linux CPU0: **MPIDR `0x40000`, part `0x068`, one online CPU**, kernel
`7.1.9-g863199d8b4a3-dirty`. Native identity, CPU28 asset checks, one uid1000
Hyprland/session, exact compositor digest and geometry guards passed. Display
**3456×2160, scale 1, XRGB8888**. Unchanged options: color management enabled,
damage tracking 2, repeat delay 1000 ms, animations enabled. Collector's final
option equality check passed. Both snapshots have no cpufreq policy, and thermal
zones/energy/power are null. No CPU-frequency or memory module was loaded.

Shipping VM-built client/sampler: GCC 16.1.1, `-O2 -Wall -Wextra -Werror`.
Exact Hyprland binary
`a9e57097798b2e815c8e91a0a4472d287573c4f7ce177b72a5b0907562a68da9`,
upstream `efb50993780079460b0cbed1363e2166a2de1d9f`; retained root userspace.
No VM-only seat/display configuration or color-management A/B change shipped.

Collector observed interval **65.916 s**, both controls 20 callbacks each: 4 warm-ups,
8 small-damage and 8 full-damage. All 40 callbacks including 8 warm-ups are retained.
Native callbacks span the same 3456×2160 geometry; all frames validated.

| Control |Small n / min / median / max,ms |Full n / min / median / max,ms |Phase wall,s |Compositor process CPU,s |
|---|---|---|---:|---:|
|1 |8 /256.404 /256.940 /270.557 |8 /504.457 /513.491 /520.280 |8.369 |8.14 |
|2 |8 /255.711 /256.346 /264.489 |8 /500.540 /516.029 /520.098 |8.497 |8.24 |

Warm-ups are excluded only from these summaries, never from the JSON. Both
small and full controls are slow; full damage is about twice the small median.
Do not relabel this as a fast tiny-damage native path on the VM's evidence.
Compositor process CPU/wall was **97.26% /96.97%**, including all its threads.

| Phase |IPC samples |Median,ms |p95,ms (nearest rank) |Maximum,ms |Compositor CPU,s / phase wall,s |
|---|---:|---:|---:|---:|---|
|Control1 |21 |407.639 |452.710 |502.906 |8.14 /8.369 |
|Control2 |21 |407.789 |419.909 |421.129 |8.24 /8.497 |
|Human desktop |372 |0.027759 |0.633203 |897.094 |7.88 /45.008 |

All **414 IPC round-trip samples**, including human-phase long-tail delays, are
retained. A near-idle human median does not erase its 897 ms maximum or measure
complete application-launch latency. Heartbeat period 100 ms adds work; sampling
and IPC are fixed across the three phases. No IPC error or incomplete phase.

Software **main-thread CPU-clock** sampling succeeded, requested 10 ms CPU-time
period, kernel/hypervisor excluded. All phases report lost 0:

| Phase |Compositor |Mesa |LLVM |Anonymous executable |Other executable file |Unmapped |Total |
|---|---:|---:|---:|---:|---:|---:|---:|
|Control1 |1 |28 |7 |758 |2 |16 |812 |
|Control2 |0 |26 |0 |796 |2 |0 |824 |
|Human desktop |2 |26 |11 |725 |7 |10 |781 |

Anonymous executable is an aggregate mapping category, **not established LLVM/
Mesa attribution**. New code may remain unmapped until the one-second VMA
refresh. These are main-thread user samples, not a profile of every compositor
thread or the whole machine. No raw instruction address, path, symbol or memory
content is published. No hardware PMU event or kernel feature was enabled.

Dependent-ADD clock estimate **2.651 GHz before /2.650 GHz after**, three reps,
CPU0→0 boundaries. Minima 2.598/2.602 GHz are retained with the full summaries.
Assumption: one cycle per dependent ADD. This is not clock/energy telemetry or
a simultaneous clock for each frame. VM callback controls validate functionality;
different kernel, CPU placement/frequency and display prevent a parity ratio.

## Human window and timing limits

The collector emitted `human_window` at kernel **317.600187 s**, ending the
human phase at **362.601775 s**. M1 local cue detection **03:26:42.720 UTC**;
the user-facing start instruction followed the streamed cue. The human reports
**prompt start, checks finished, accurate typing and continued application delay**.
Instructions were menu, terminal, type `omarchy` without Enter, file manager;
no settings, sign-in or setup commands. No input was injected by a tool.

Individual physical actions/completions are **not timestamped**; do not claim
every application finished inside 45 s. Nautilus-related warnings at kernel
390.465/391.800 s are after the observation and do not timestamp its keypress
or launch request. The subsequently written local notebook field
`human_cue_announced_record_utc` is 03:27:23.198 UTC, 40.478 s after detection:
it is **not the actual user-visible cue timestamp** and cannot measure cue
delivery delay. Keep that distinction; no film was available to align actions.

## Return, faults and M5 next

Final **LATENCY_OBSERVED** and helper exit 0; no `phase_incomplete` or `stop`.
170 s collector, 180 s systemd (+10 s cleanup), 220 s M1 helper (+5 s cleanup) bounds
unchanged. Root window remained 600 s; no re-arm or extension. Samplers/clients
ended as owned children, the final options equaled initial options, and no
frequency, renderer, module, idle, extra-core, storage or Wi-Fi experiment ran.

Second reader exit 0, **207,477 raw bytes /2,186 lines**, disconnecting
**03:28:28.549 UTC** during the instructed return. Last kernel timestamp
423.006747 s. Whole-token panic/Oops/BUG/SError/USB bus-error/translation-fault
scan found 0 in both journals; no M1 panic observed. Known PMGR probe error -22,
first-boot hardware/CLI Netfilter failures, teardown/udev transaction conflicts
and portal/BlueZ warnings remain unresolved. No local parser/test repair or
target retry was needed. Raw receipts/journals/keys/video/images stay private.

Human Macintosh HD desktop confirmation: **03:28:51.538 UTC / 11:28:51 PM
Eastern, +223.531 s / 600 s**, deadline met. Readers ended; only this run's caffeine
assertion and deadline guard were stopped. No SSH/relay/clock collector remains.
Routine policy/default checks stayed waived: original Full/lab Permissive and
Macintosh HD default remain last reported, not freshly verified. Existing entry,
installed m1n1, security/default/volume settings and firmware were untouched.

**M5 offline review next:** high control CPU and queued IPC support examining
the expensive draw/main-thread path, confirming generated-code attribution and
tracing damage expansion/copying. The human phase also needs precise action/
presentation timing before one cause is assigned to app delays. Do not assume
more cores automatically parallelize this event loop or select a blind clock/
renderer-policy change. Physical CPU/SMP/thermal and native GPU enablement remain
separate tracks. No native speedup, energy efficiency, macOS parity or further
live attempt is authorized by this observational result.
