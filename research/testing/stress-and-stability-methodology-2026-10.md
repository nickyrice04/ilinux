# Sustained performance and stability test methodology: Apple Silicon (M5 Max), macOS vs Linux

Prepared 2026-10-12 for the iLinux performance-parity project. The target is the owner's MacBook Pro (M5 Max, macOS 26). Linux currently runs as an Omarchy guest under QEMU/HVF, and a native boot is planned later.

This report is based on read-only web research. There were no sign-ins or downloads, and every page was treated as untrusted data.

**Evidence labels used throughout**

- **[C] Confirmed.** I read it directly at the cited URL during this session.
- **[L] Likely.** It comes from a search-result summary I did not open, a single user or forum report, or an inference from confirmed facts.
- **[U] Unknown.** I could not find or verify it.
- **[P] Proposed.** This is my own recommendation (for example a pass threshold), derived from the sources but not itself a sourced fact.

---

## Summary

### How reviewers test sustained performance on M-series Max laptops

Reviewers converge on a small set of methods:

- **CPU loops.** Notebookcheck runs Cinebench 2024 multi-core as a 30-minute stress loop. It reports the percentage drop and peak-to-sustained SoC power, read from `powermetrics` [C]. Tom's Hardware runs a ten-run Cinebench 2026 loop and reports the scores run by run [C].
- **GPU loops.** On macOS, 3DMark stress tests loop the benchmark 20 times over about 20 minutes [C]. UL defines Frame Rate Stability as the worst loop's average FPS divided by the best loop's average FPS, times 100. A pass requires at least 97% and all loops completed [C].
- **Combined CPU+GPU stress.** On Macs, Notebookcheck runs Cinebench R23 multi together with the 3DMark Wild Life Extreme stress test. It plots CPU, GPU and package watts over time [C].
- **Wall power and comfort.** Notebookcheck measures wall power with a true-RMS meter on the primary side [C]. Surface temperature is taken on a 9-zone grid after 60 minutes of load [C], and fan noise in dB(A) at 15 cm [C].
- **Battery.** Notebookcheck uses a Wi-Fi browsing script at about 150 cd/m², an H.264 1080p video loop at 150 cd/m², and a full-load rundown [C]. Tom's Hardware runs web, video streaming and OpenGL together at 150 nits [C].

### M5 Max behaviour that will dominate any comparison

**Chassis size.** The 14-inch M5 Max throttles hard [C]:

- In a 30-minute Cinebench 2024 loop, performance fell 24%.
- Single Cinebench 2024 runs ranged from about 1,400 to 2,073 points under near-identical conditions.
- Steel Nomad stress-test stability was 92.6% in High Power mode and 74.99% in Automatic.

The 16-inch M5 Max is stable. In High Power its CPU holds 75 W briefly and then about 70 W, and its Steel Nomad stability is 98.4% [C].

**macOS version.** On the 16-inch in Automatic mode, Steel Nomad stability fell from 98.5% on macOS 26.3.1 to 87.3% on 26.6.2. High Power on 26.6.2 is now required to stay above 97% [C].

**Power delivery.** Apple caps power input at about 97 W on the 14-inch and about 150 W on the 16-inch, so the battery drains under load even on AC [C]:

- The 14-inch lost about 15% of its battery during the stress test.
- The 16-inch lost about 12% per hour under combined load, even on a 180 W charger.

Any soak test longer than a few hours must log battery level.

**Power mode may not apply.** An Apple Developer Forums thread reports that High Power mode is not actually applied on some M5 Max units. Users detected it with `system_profiler SPPowerDataType` and `pmset -g custom` [C, as a user report]. Verify the mode before every run.

### Telemetry

- On the macOS host, use `powermetrics` (needs sudo) or `macmon pipe` (no sudo, JSON output). Together they cover CPU, GPU and ANE power, frequency and residency, thermal pressure, and temperatures [C].
- `powermetrics` no longer reports package power on Apple Silicon [C, per the asitop README].
- Fan RPM requires third-party SMC readers [L].
- For the current QEMU/HVF guest, all power and thermal data must come from the host. The guest can only supply throughput, errors and timestamps [L, inferred from the HVF and virtio architecture].

### Identical-code workloads that exist on both sides

These run the same upstream code on macOS and Linux [C unless noted]:

- 7-Zip 26.04, which ships macOS and Linux arm64 builds.
- Geekbench 6.7 (the Linux/ARM build is a preview [L]).
- stress-ng [L].
- ffmpeg with x265, SVT-AV1 and dav1d [P].
- An LLVM toolchain via Homebrew `llvm@22`, with bottles for both platforms [L].
- llama.cpp at a pinned commit, using either its CPU backend or its Vulkan backend.
- fio with `posixaio`, and memtester.
- The Phoronix Test Suite, which supports macOS.

Some workloads have no Linux counterpart [C]:

- Cinebench and 3DMark have no Linux builds.
- Blender has no official Linux ARM64 build, so Linux needs a distro or source build.
- MLX on Linux is CPU or CUDA only.

### GPU and media are structural gaps for the VM

- The guest has no access to Apple's media engine.
- GPU work passes through virtio-gpu (virgl or Venus) to MoltenVK or KosmicKrisp on the host.
- Precedent from llama.cpp on an M2 Max [C]:
  - In a Venus (krunkit) container, it reached about 57% of native Metal on pp512 and about 50% on tg128.
  - Native Asahi Vulkan (Dec 2024) reached about 16% (pp512) and 36% (tg128) of macOS Metal.

### Asahi evidence

- **CPU-bound benchmarks.** Phoronix found Asahi in the same ballpark as macOS on M1 and M2 in 2022. Gaps came from missing boost states, power management, and Java [C].
- **Battery.** Energy-aware scheduling (EAS) took M2 Air desktop battery life from about 6 hours to 12–15 hours [C].
- **Hardware support.** Asahi officially supports M3 as of 2026-09-06, without performant 3D [C]. M4/M5 bring-up is still in progress, M5 is not in the installer, and a WFI state-loss problem affects M4 and later [C].
- **No sustained-load study.** I found no published sustained-load comparison of Asahi vs macOS, meaning a 30-minute loop with thermal logging [U].

### Reference video

The video is "M5 Max MacBook Pro Stress Test - This is INSANE!" by Mark Ellis Reviews, published 2026-04-03 and 21:29 long [C].

- **What it is.** A qualitative concurrency test, trying to overwhelm a 16-inch M5 Max with an 18-core CPU, 40-core GPU, 128 GB of memory and 4 TB of storage.
- **Workloads.** Final Cut Pro and DaVinci Resolve exports, a 193-track Logic Pro project, a 70B LLM in LM Studio, and every installed app opened at once.
- **What happened.** There was no crash, and one Logic Pro "System Overload" audio event. A 4-hour Final Cut export barely progressed, and memory use reached 116 of 128 GB.
- **What it lacks.** It reports no temperatures, clocks, power or tokens per second. It is not a quantitative baseline, but it is a useful template for a mixed-concurrency soak.

---

## Sources

Grouped by topic. "Read" means I opened the page in this session ([C]). "Search summary" means I only saw a search-engine summary ([L]).

**Reviewer methodology and M-series results**

1. Notebookcheck, MacBook Pro 14 M5 Max review, 2026-03-11 (read) [C]. Mode table, 30-minute Cinebench drop, Steel Nomad stability, wall power, battery assist, battery runtimes. https://www.notebookcheck.net/M5-Max-with-inconsistent-performance-and-throttling-issues-Apple-MacBook-Pro-14-Review.1246064.0.html
2. Notebookcheck, MacBook Pro 16 M5 Max first results, 2026-03-16 (read) [C]. https://www.notebookcheck.net/Apple-s-M5-Max-in-the-MacBook-Pro-16-is-around-15-faster-compared-to-the-MacBook-Pro-14.1250872.0.html
3. Notebookcheck, MacBook Pro 16 M5 Max full review, 2026-08-27 (read) [C]. https://www.notebookcheck.net/Apple-s-fastest-laptop-starts-to-show-its-age-Apple-MacBook-Pro-16-2026-M5-Max-Review.1250821.0.html
4. Notebookcheck, "Did Apple reduce the performance of the M5 Max via software update?", 2026-08-25 (read) [C]. https://www.notebookcheck.net/Did-Apple-reduce-the-performance-of-the-M5-Max-via-software-update-Yes-and-no.1376940.0.html
5. Notebookcheck, 140 W adapter insufficient on MBP 16 M5 Max, 2026-08-30 (read) [C]. https://www.notebookcheck.net/The-140W-power-adapter-of-the-Apple-MacBook-Pro-16-is-insufficient-but-there-is-nothing-you-can-do-about-it.1381512.0.html
6. Notebookcheck, M5 Pro/M5 Max CPU analysis (read) [C]. https://www.notebookcheck.net/Apple-M5-Pro-M5-Max-CPU-Analysis-M5-Max-is-not-much-faster-than-the-M4-Max.1246054.0.html
7. Notebookcheck, M5 Pro/M5 Max GPU analysis (read) [C]. https://www.notebookcheck.net/Apple-M5-Pro-M5-Max-GPU-Analysis-M5-Max-GPU-on-par-with-the-GeForce-RTX-5070-and-faster-than-Strix-Halo.1246060.0.html
8. Notebookcheck, PugetBench results for M5 Pro/Max, 2026-03-25 (read) [C]. https://www.notebookcheck.net/Apple-s-M5-Pro-M5-Max-easily-beat-the-RTX-5090-in-PugetBench-creator-benchmarks.1252582.0.html
9. Notebookcheck, MacBook Pro 16 M4 Max review, 2024-12-11 (read) [C]. https://www.notebookcheck.net/Apple-MacBook-Pro-16-M4-Max-review-The-M4-Max-is-one-of-the-fastest-mobile-processors.929593.0.html
10. Notebookcheck, M4 Pro (12-core) page, with powermetrics-based power readings (read) [C]. https://www.notebookcheck.net/Apple-M4-Pro-12-cores-Processor-Benchmarks-and-Specs.922301.0.html
11. Notebookcheck, test criteria and methods (read) [C]. https://www.notebookcheck.net/How-does-Notebookcheck-test-laptops-and-smartphones-A-behind-the-scenes-look-into-our-review-process.15394.0.html
12. Tom's Hardware, MacBook Pro 14 M5 Max review, 2026-03-09 (read) [C]. https://www.tomshardware.com/laptops/macbooks/apple-macbook-pro-14-inch-m5-max-2026-review
13. TweakTown, summary of The Verge's 30-minute Cinebench R23 loop on M2 Air vs M2 Pro (search summary) [L]. https://www.tweaktown.com/news/87417/apple-m2-macbook-air-throttles-bad-cooled-pro-doesnt/index.html

**Benchmark tools and definitions**

14. UL, 3DMark on macOS, 2026-04-22 (read) [C]. Covers Wild Life Extreme, Solar Bay, Solar Bay Extreme, Steel Nomad and Steel Nomad Light. https://benchmarks.ul.com/en-sc/news/3dmark-on-macos-now-available-directly-from-ul-solutions
15. UL support, running 3DMark for macOS (read) [C]. Stress tests run 20 loops over 20 minutes. https://support.benchmarks.ul.com/support/solutions/articles/44002569553-how-to-run-a-benchmark-using-3dmark-for-macos
16. UL support, stress-test result screen (read) [C]. Frame Rate Stability formula and the 97% pass rule. https://support.benchmarks.ul.com/support/solutions/articles/44002134931-stress-test-result-screen
17. UL news, 3DMark stress tests launch, 2016 (read) [C]. Gives a throttling example of 59 to 51 FPS. https://benchmarks.ul.com/en/news/check-your-pcs-stability-with-new-3dmark-stress-tests
18. UL hardware page, MacBook Pro 16 M2 Max (read) [C]. Crowd-sourced median stability: Wild Life Extreme 99%, Steel Nomad Light 98%, Solar Bay 90%. https://benchmarks.ul.com/hardware/tablet/MacBook+Pro+16%E2%80%9D+(M2+Max,+2023)+review
19. Maxon, Cinebench tech info (read) [C]. Lists `g_CinebenchCpuXTest` and `g_CinebenchMinimumTestDuration`, with Windows and macOS only. The default 10-minute minimum comes from search summaries of TechSpot, heise and KitGuru [L]. https://www.maxon.net/tech-info-cinebench
20. Geekbench 6 release notes (read) [C]. Version 6.6.0 added Vulkan on Linux/ARM, and 6.7.0 improved Linux/ARM stability. https://www.primatelabs.com/release/geekbench6/
21. Arm Learning Path for Geekbench on Arm Linux (search summary) [L]. The Linux/ARM build is a preview. https://learn.arm.com/learning-paths/servers-and-cloud-computing/geekbench/geekbench/
22. Blender download page (read) [C]. Version 5.2.2 LTS, with no Linux ARM64 build. https://www.blender.org/download/
23. 7-Zip downloads (read) [C]. Version 26.04, with Linux arm64 and macOS builds. https://www.7-zip.org/download.html
24. Homebrew `llvm@22` formula (search summary) [L]. Bottles exist for macOS Apple Silicon and Linux ARM64. https://formulae.brew.sh/formula/llvm@22
25. Phoronix Test Suite documentation (read) [C]. Covers `stress-run`, `TOTAL_LOOP_TIME`, `FORCE_MIN_DURATION_PER_TEST`, `PTS_CONCURRENT_TEST_RUNS` and `MONITOR`, and states that macOS is fully supported. https://raw.githubusercontent.com/phoronix-test-suite/phoronix-test-suite/master/documentation/phoronix-test-suite.md
26. stress-ng manual and Homebrew bottle (search summary) [L]. Covers `--verify` and `--metrics-brief`, notes `--tz` is Linux-only, and shows macOS bottles. https://manpages.org/stress-ng and https://formulae.brew.sh/formula/stress-ng
27. fio documentation (read) [C]. Covers `time_based`, `runtime`, `verify=crc32c`, `verify_fatal`, `verify_backlog`, `do_verify`, `posixaio` and `io_uring`. https://fio.readthedocs.io/en/latest/fio_doc.html
28. glmark2 man page (read) [C]. Covers `--run-forever` and `--results-file`. https://www.mankier.com/1/glmark2
29. vkmark README (read) [C]. Covers `-b scene:duration=` and `--winsys`. https://github.com/vkmark/vkmark
30. memtester (read) [C]. A userspace tester that runs on Mac OS X. https://pyropus.ca./software/memtester/
31. stressapptest README (search summary) [L]. Flags `-s`, `-M`, `-m` and `-W`. https://android.googlesource.com/platform/external/stressapptest/+/refs/heads/android12-d1-release/README.md
32. Sascha Willems Vulkan examples, benchmark flags from a snap listing (search summary) [L]. Flags `-b`, `-bw`, `-br`, `-bf`, `-bt` and `-bfs`, plus the macOS support blog. https://snapcraft.io/install/vulkan-examples/ubuntu and https://saschawillems.de/blog/2017/07/01/ios-and-macos-support-added-to-the-vulkan-examples/

**macOS power and telemetry**

33. Apple, MacBook Pro tech specs (read) [C]. M5 Max core layout, media engines, batteries and adapters. https://www.apple.com/macbook-pro/specs/
34. Apple Support, About Power Modes (read) [C]. https://support.apple.com/101613
35. Apple Developer Forums, "High Power Mode not applied by powerd" (read) [C, as user reports]. https://developer.apple.com/forums/thread/835131
36. Eclectic Light, Power Modes and Apple Silicon GPUs, 2025-01-06 (read) [C]. https://eclecticlight.co/2025/01/06/power-modes-and-apple-silicon-gpus/
37. Firefox docs on powermetrics (read) [C]. https://firefox-source-docs.mozilla.org/performance/powermetrics.html
38. asitop README (read) [C]. Package power was removed from powermetrics, and the tool needs sudo. https://github.com/tlkh/asitop
39. macmon README (read) [C]. Runs without sudo, offers JSON via `pipe`, and reads IOReport. https://github.com/vladkens/macmon
40. Thermal pressure levels and `powermetrics -s thermal` (search summaries) [L]. https://stanislas.blog/2025/12/macos-thermal-throttling-app/ and https://news.hada.io/topic?id=25416
41. Fan RPM via third-party SMC tools such as smctl (search summary) [L]. https://www.raycast.com/samuelbelo/fan-control and https://pkg.go.dev/github.com/caseymrm/go-smc
42. Apple battery-test footnote method (search summary of reproduced footnotes) [L]. Wi-Fi browsing of 25 sites, 1080p streaming in Safari, brightness 8 clicks from the bottom. https://www.wearesync.co.uk/product-category/pro/page/12/

**Media engine**

43. Jellyfin, Apple VideoToolbox hardware acceleration (read) [C]. AV1 decode on M3 and later, and silent software fallback when capacity is exceeded. https://jellyfin.org/docs/general/post-install/transcoding/hardware-acceleration/apple

**ML and LLM**

44. llama.cpp discussion #4167, Apple Silicon performance (read) [C]. https://github.com/ggml-org/llama.cpp/discussions/4167
45. llama.cpp issue #10982, Asahi Vulkan vs macOS Metal on M2 Max (read) [C]. https://github.com/ggml-org/llama.cpp/issues/10982
46. llama.cpp discussion #12985, containerised Vulkan (Venus/krunkit) vs native Metal (read) [C]. https://github.com/ggml-org/llama.cpp/discussions/12985
47. LM Studio bug tracker #2040 on the M5 Metal tensor path and `GGML_METAL_TENSOR_DISABLE` (search summary) [L]. https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/2040
48. MLX install docs (read) [C]. Metal on macOS only; Linux is CPU or CUDA. https://ml-explore.github.io/mlx/build/html/install.html
49. mlx-lm README (read) [C]. https://github.com/ml-explore/mlx-lm

**Linux, Asahi and virtualization**

50. Phoronix, Apple M1 Linux performance (Asahi alpha vs macOS 12.3), 2022-03-23 (read) [C]. https://www.phoronix.com/review/apple-m1-linux-perf and /2
51. Phoronix, Apple M2 Linux benchmarks (macOS 12.5 vs Asahi), 2022-08-09 (read) [C]. https://www.phoronix.com/review/apple-m2-linux and /2
52. Phoronix, Asahi EAS and battery progress, 2024-01-14 (read) [C]. https://www.phoronix.com/news/Asahi-Linux-January-2024
53. Phoronix, Asahi M3 release soon and M4/M5 bring-up, 2026-08-26 (read) [C]. https://www.phoronix.com/news/Asahi-Linux-M3-Release-Soon
54. Asahi blog, Progress Report for Linux 7.2, 2026-08-26 (read) [C]. https://asahilinux.org/2026/08/progress-report-7-2/
55. Asahi blog, M3 support, 2026-09-06 (read) [C]. https://asahilinux.org/2026/09/m2-episode-1/
56. Asahi blog, Progress Report for Linux 6.18, covering SMC hwmon (read) [C]. https://asahilinux.org/2025/12/progress-report-6-18/
57. Asahi docs, M2 feature support (read) [C]. https://asahilinux.org/docs/platform/feature-support/m2/
58. Alyssa Rosenzweig, "AAA gaming on Asahi Linux", 2024-10-10 (read) [C]. https://alyssarosenzweig.ca/blog/aaa-gaming-on-m1.html
59. Phoronix, Apple Video Decode (AVD) driver posted upstream, 2026-09 (search summary) [L]. https://www.phoronix.com/news/Apple-Video-Decode-AVD-Linux
60. Eclectic Light, "Virtualisation on Apple silicon Macs is different", 2026-04-29 (read) [C]. https://eclecticlight.co/2026/04/29/virtualisation-on-apple-silicon-macs-is-different/
61. Lemmy, Geekbench 6 on M1 Max: native macOS vs Fedora in UTM and Parallels (search summary) [L]. https://lemmy.linuxuserspace.show/post/29541
62. QEMU RFC, "virtio-gpu-virgl: introduce Venus support for macOS", 2025-12 (search summary) [L]. https://patchew.org/QEMU/20251203040754.94487-1-j@getutm.app
63. LunarG KosmicKrisp (Vulkan on Metal) conformance (search summary) [L]. https://www.lunarg.com/lunarg-achieves-vulkan-1-3-conformance-with-kosmickrisp-on-apple-silicon/ and https://www.phoronix.com/news/KosmicKrisp-Vulkan-1.4-2026
64. LKML, "Enable build system on macOS hosts" kernel patches (search summary) [L]. https://lkml.iu.edu/hypermail/linux/kernel/2409.0/08660.html

**Reference video**

65. YouTube, "M5 Max MacBook Pro Stress Test - This is INSANE!" by Mark Ellis Reviews (page, description, chapters and auto-generated captions read) [C]. https://www.youtube.com/watch?v=fdqlUQO181E

---

## Methodology table

### A. Common protocol for every test

**1. Record the machine state [P].** Log the following for every run:

- Chassis size (14 or 16 inch); this matters greatly per Notebookcheck [C].
- SoC configuration and macOS build (`sw_vers`).
- Power mode, checked three ways: System Settings, `pmset -g custom` (`powermode`), and `system_profiler SPPowerDataType` ("High Power Mode") [L, per the forum report].
- Adapter model and wattage, battery % and cycle count.
- Ambient temperature, lid and display state, and measured brightness.
- Any third-party fan-control tool. Disable these: a forum report shows a custom fan curve changing sustained Steel Nomad results [C, as a report].

**2. Record the VM configuration [P].** Log the QEMU version and full command line: HVF acceleration, `-smp`, `-m`, the GPU device, the virglrenderer mode (virgl or Venus), and the MoltenVK or KosmicKrisp version. Also log the guest kernel and Mesa versions.

**3. Start cold [P].** Before each run, idle until host thermal pressure is Nominal and SoC power has returned to idle for at least 5 minutes. For comparison, Notebookcheck measures temperatures after 60 minutes idle and 60 minutes under load [C].

**4. Repeat [P].** Do at least 3 independent cold runs per condition and report median, minimum, maximum and coefficient of variation (CV). Notebookcheck saw roughly 1,400 to 2,073 points between single Cinebench runs on the 14-inch M5 Max [C].

**5. Control power delivery [P, with sourced drain figures].**

- Run on the stock adapter and log battery % every minute. Any decline means the battery is assisting.
- Expect about 12% per hour of drain on the 16-inch under combined CPU+GPU load, and about 15% across the 14-inch stress test [C].
- Schedule long combined soaks so the battery stays above 20%, or use CPU-only loads that fit within the adapter budget.
- Run battery-only variants as a separate condition. Notebookcheck found all three power modes perform the same on battery for the M5 Max [C]. The M4 Max stayed stable on battery until about 4% charge [C].

**6. Keep the code identical [P].**

- Pin versions and commits.
- Use the same compiler version and flags on both sides; Homebrew `llvm@22` has bottles for both [L].
- Use the same thread counts.
- Save binary hashes and full command lines.

**7. Thread placement.** The M5 Max has 6 super cores plus 12 performance cores and no efficiency cores [C]. On macOS, QEMU vCPU threads cannot be pinned; only QoS hints are available [L]. Eclectic Light reports that VM vCPUs run mainly on performance cores [C].

**8. Time-align the logs [P].** Log host and guest series at 1 Hz with UTC timestamps, and run NTP/chrony in the guest. This lets guest throughput dips be matched to host power or thermal events.

**9. Re-baseline after any macOS update [P].** Notebookcheck showed a point update changing sustained behaviour [C].

### B. Telemetry recipe

**macOS host.** These apply to both native macOS runs and Linux-VM runs.

- `sudo powermetrics -i 1000 --samplers cpu_power,gpu_power,ane_power,thermal -f plist -o run.plist`
  - Reports CPU, GPU and ANE power, per-cluster frequency and residency, GPU frequency and residency, and the thermal pressure level.
  - `powermetrics` is the data source for asitop and for Notebookcheck's Mac power figures, and Eclectic Light used its `gpu_power` sampler for GPU frequency and power [C].
  - Confirm the exact sampler names and flag spellings on your build with `powermetrics -h` [L].
  - Package power is no longer reported [C].
- `macmon pipe -i 1000 > run.jsonl`: JSON with power, temperatures and frequencies, no sudo needed [C].
- `pmset -g therm` and `pmset -g batt` once a minute [L]. `ioreg -rn AppleSmartBattery` exposes the charge/discharge current; a discharge while on AC means battery assist [L].
- Fan RPM: there is no Apple CLI, so use a third-party SMC reader such as `smctl sensors --json` [L].
- External instruments, following Notebookcheck practice [C]:
  - a USB-C PD inline meter or a true-RMS AC meter for wall power;
  - an IR thermometer on a 9-zone grid, top and bottom, after 60 minutes;
  - a sound level meter at 15 cm.

**Linux guest (VM).**

- Per loop: start and end timestamps, score or throughput, exit code, and output hashes [P].
- `journalctl -k -f`, watching for oops, WARN, soft lockups, RCU stalls, hung tasks, virtio or virtio-gpu timeouts, and Vulkan device-lost errors [P].
- `vmstat 1` and `/proc/pressure/{cpu,memory,io}` [P].
- The guest cannot see host clocks, power or thermals [L].

**Native Linux later (Asahi, once M5 is supported).**

- SMC hwmon sensors for voltage, current, temperature and power are upstream for 6.19 [C].
- Battery info landed in 7.1 for M2 Pro/Max MacBook Pros [C].
- cpufreq has been upstream since 6.2 [C].
- Use the cpufreq sysfs files [L] and the PTS `MONITOR=cpu.temp,cpu.power,sys.power,gpu.freq` option [C].

### C. Derived metrics

- **First-to-last drop** = 1 − (last loop ÷ first loop).
- **Sustained ratio** = median of the final 20% of loops (or the last 5 minutes) ÷ first loop [P].
- **UL stability** = lowest loop average FPS ÷ highest loop average FPS × 100. A pass needs at least 97% and all loops completed [C].
- **Run-to-run CV** across at least 3 cold runs [P].
- **Parity** = Linux result ÷ macOS result, on the same machine, mode and code [P].
- **Energy per task** = host joules per loop [P].

### D. Test tables

Every pass criterion in these tables is [P] unless it is marked [C].

**CPU**

| ID | macOS-side reference (how reviewers run it) | Linux counterpart (identical code where possible) | Metric(s) | Duration / loops | What to log | Suggested pass criterion | Evidence |
|---|---|---|---|---|---|---|---|
| CPU-1 | Cinebench 2024/2026 multi-core with Minimum Test Duration set to 30 min (Notebookcheck). Tom's Hardware instead runs 10 consecutive runs. CLI form: `g_CinebenchCpuXTest=true g_CinebenchMinimumTestDuration=1800`. | None; Cinebench has no Linux build. Use CPU-2 and CPU-3 as the cross-OS counterpart and keep CPU-1 as the macOS anchor. | Score per pass; first-to-last drop | 30 min (or 10 runs) | Cluster frequencies, CPU W, thermal pressure, fan RPM, battery % | 0 errors. A drop of at most 5% is plausible on the 16-inch in High Power, where Notebookcheck saw a stable ~70 W plateau [C]. The 14-inch fails (−24% [C]), so judge Linux against the macOS baseline measured on that machine. | Maxon CLI [C]; Notebookcheck and Tom's loops [C] |
| CPU-2 | 7-Zip `7zz b` built-in benchmark | Same 7-Zip 26.04 release (macOS universal, Linux arm64) | Compress/decompress MIPS per pass | 30-min loop plus 10 consecutive passes | As CPU-1, plus guest per-pass timestamps | Drop ≤5%; CV ≤2%; VM ≥95% of macOS sustained; native ≥98% | 7-Zip builds [C] |
| CPU-3 | Blender CPU render (Notebookcheck uses Classroom v3.3 and Barbershop v4.3 CPU) | Same Blender version: official build on macOS, distro or source build on Linux arm64 (no official build) | Seconds per render | 30-min loop | As CPU-1 | Drop ≤5%; CV ≤2%; rendered frame hash stable across loops on the same OS | Notebookcheck [C]; Blender downloads [C] |
| CPU-4 | Geekbench 6 CPU, a burst test (Notebookcheck notes it loads the CPU only briefly [C]) | Geekbench 6.7.x Linux/ARM preview | Single-core and multi-core score | 5 back-to-back runs | As CPU-1 | CV ≤2%; VM multi-core ≥92% of macOS (an M1 Max VM ran 6–8% below native [L]); native ≥97% | GB release notes [C]; Lemmy VM data [L] |
| CPU-5 | Large compile. XcodeBenchmark is Mac-only [L]. | LLVM/Clang Ninja build of a pinned source tree, using the same `llvm@22` toolchain on both sides. Linux kernel `defconfig` builds on Linux (kernel builds on macOS hosts are experimental [L]). | Wall time per clean build | 5 clean builds (about 1 h) | As CPU-1, plus RSS and swap | 0 compiler crashes or ICEs; CV ≤2%; Linux ≥95% of macOS | [L]/[P] |
| CPU-6 | CPU video encode. Tom's runs HandBrake 4K→1080p; the encoder is not stated [C]. | ffmpeg with libx265 or libsvtav1 (pinned), or HandBrakeCLI with an x265 preset, on the same source clip | fps; seconds per encode | 5 encodes or a 30-min loop | As CPU-1 | Drop ≤5%; output hash identical across loops on the same OS; identical PSNR/VMAF across OSes | Tom's [C] |
| CPU-7 | stress-ng (not a reviewer test, but it builds on macOS) | Same stress-ng version: `--cpu 0 --cpu-method matrixprod --verify --metrics-brief --timeout 30m` | Verify failures; bogo-ops drift (regression only) | 30 min | As CPU-1 | 0 verify failures. Do not use bogo-ops as a performance metric; the manual warns against it [L]. | [L] |

**GPU**

| ID | macOS-side reference | Linux counterpart | Metric(s) | Duration / loops | What to log | Suggested pass criterion | Evidence |
|---|---|---|---|---|---|---|---|
| GPU-1 | 3DMark Steel Nomad / Steel Nomad Light / Solar Bay / Wild Life Extreme stress test | None; 3DMark has no Linux arm64 build. Use GPU-2. | Frame Rate Stability %; best and worst loop | 20 loops / 20 min [C] | GPU W, GPU frequency and residency, thermal pressure, fan RPM, battery % | ≥97% passes [C]. Notebookcheck results: 16-inch High Power 98.4% (pass); 16-inch Automatic on 26.6.2 87.3% (fail); 14-inch 92.6% High and 74.99% Automatic (fail) [C]. | UL [C]; Notebookcheck [C] |
| GPU-2 | The same Vulkan code on macOS through MoltenVK or KosmicKrisp | Vulkan benchmark loop: Sascha Willems examples (`-b -bw 5 -br 60 -bf out.csv -bt`) [L], or vkmark with fixed scenes (`-b :duration=60.0`) [C]. Runs via Venus in the VM or Honeykrisp natively. | Average FPS per loop; UL-style stability; p99 frame time | 20 loops × 60 s (mirrors 3DMark) | As GPU-1, plus guest Mesa and virtio logs | Stability ≥97%, or at most 2 points below the macOS same-API result in the same power mode; 0 device-lost errors or hangs; parity tracked against macOS MoltenVK/KosmicKrisp | [C]/[L] |
| GPU-3 | n/a (OpenGL is legacy on macOS) | glmark2 `--run-forever --results-file …` on virgl (VM) or Asahi GL (native) | Per-scene FPS over time | 2-hour soak | Guest kernel and Mesa logs; host GPU W | 0 GPU resets or errors; per-scene FPS drift ≤3% | glmark2 [C] |
| GPU-4 | Blender GPU on Metal (Notebookcheck: Barbershop Metal, 100 s on the 14-inch M5 Max vs 83.2 s on the 16-inch M4 Max [C]) | None. No Cycles GPU path exists for the Apple GPU on Linux [L]. Record this as a gap. | Seconds per render | 30-min loop | As GPU-1 | macOS only: drop ≤5% | Notebookcheck [C] |
| GPU-5 | Geekbench 6 GPU (Metal or OpenCL) | Geekbench 6.6+ Vulkan on Linux/ARM [C] | Score | 5 runs | As GPU-1 | CV ≤3%; parity reported per API | [C] |
| GPU-6 | Native macOS games. In Notebookcheck's Cyberpunk 2077 throttling test the 14-inch fell from 86 to 80 fps [C]. | Not identical: open-source titles with timedemos via PTS, run on both OSes where available | Average fps and 1% lows over time | 20-min session or 10 benchmark passes | As GPU-1 | 0 crashes; average over the last 5 minutes ≥95% of the first 5 minutes | [C]/[P] |

**Media engine**

| ID | macOS-side reference | Linux counterpart | Metric(s) | Duration / loops | What to log | Suggested pass criterion | Evidence |
|---|---|---|---|---|---|---|---|
| MED-1 | VideoToolbox hardware decode throughput, e.g. `ffmpeg -hwaccel videotoolbox -i clip_4K_HEVC10.mp4 -f null -` [L], with 1, 2, 4 and 8 concurrent streams. The M5 Max has 1 decode engine plus AV1 decode [C]. | The VM has no Apple media engine [L], so use software decode with the same ffmpeg build (native HEVC/H.264 decoders, dav1d for AV1). Native Asahi decodes H.264/HEVC/VP9 through AVD (V4L2 stateless), plus AV1 on M3, but only on M1–M3 today [C/L]. | Decode fps; maximum stream count that sustains real time | 10 min per stream count | CPU % (high CPU reveals software fallback [C]), host power, fps per 10 s | Hardware path: 0 fallbacks, at or above real time, drift ≤3%. Software path: report Linux/macOS parity. | Apple specs [C]; Jellyfin [C]; Asahi docs [C] |
| MED-2 | VideoToolbox encode (`hevc_videotoolbox`, `h264_videotoolbox`, ProRes) [L], plus Final Cut Pro and HandBrake VideoToolbox exports. The M5 Max has 2 encode engines and 2 ProRes engines [C]. | None. The AVE encoder and ProRes are "TBA" in Asahi [C], and the VM has no access. Compare against the CPU-6 software encodes and record the gap. | fps; output size; VMAF | 5 encodes | As MED-1 | Drop ≤5%; record the bitrate/quality trade-off | [C]/[L] |
| MED-3 | Multi-stream playback (an NLE-style test) | mpv or ffmpeg N-stream playback on both sides (hardware decode on macOS, software in the VM) | Dropped frames | 10 min | As MED-1 | 0 dropped frames at the target N | [P] |

**ML / LLM**

| ID | macOS-side reference | Linux counterpart | Metric(s) | Duration / loops | What to log | Suggested pass criterion | Evidence |
|---|---|---|---|---|---|---|---|
| ML-1 | llama.cpp Metal at a pinned commit: `llama-bench -m llama-2-7b.Q4_0.gguf -p 512 -n 128 -ngl 99 -r 5 --delay 30 -o json`, following the #4167 method [C]. Record whether the M5 Metal tensor path is enabled (`GGML_METAL_TENSOR_DISABLE`) [L]. | Same commit with the Vulkan backend (Venus in the VM, Honeykrisp natively) and the CPU backend (identical code on both sides). Also run Vulkan on macOS through MoltenVK or KosmicKrisp, to separate API cost from virtualization cost. | pp512 and tg128 t/s | 5 repetitions, repeated 10 times back to back | GPU W and frequency, wired memory, thermal pressure | CV ≤3%; last repetition ≥95% of the first; report VM-Vulkan ÷ macOS-Vulkan and ÷ Metal | #4167, #10982, #12985 [C] |
| ML-2 | Sustained generation for 30 min with a large model (e.g. 70B Q4), logging t/s every 30 s | Same on Linux (Vulkan or CPU) | t/s over time | 30 min | As ML-1, plus swap | Last 5 minutes ≥95% of the first 5; 0 OOM or crashes; deterministic output at temperature 0 on the same backend | [P] |
| ML-3 | MLX: `mlx_lm.generate` with verbose output, or `mlx_lm.benchmark` [C] | Not comparable; MLX on Linux is CPU or CUDA only [C]. Use ML-1 instead. | Prompt and generation t/s | 5 runs | As ML-1 | macOS only | [C] |

**Power, thermal and battery**

| ID | macOS-side reference | Linux counterpart | Metric(s) | Duration / loops | What to log | Suggested pass criterion | Evidence |
|---|---|---|---|---|---|---|---|
| PWR-1 | Combined 60-min stress, Notebookcheck style: Cinebench R23 multi plus 3DMark Wild Life Extreme stress [C] | Identical-code combined load: CPU-2 and GPU-2 running in parallel, in the VM and natively on macOS | CPU, GPU and package W from peak to plateau; wall W; battery Δ on AC; surface temperature; dB(A) | 60 min | Everything in section B | 0 errors; record peak and plateau W; record battery Δ; host power plateau for the VM within ±5% of macOS for the same work | Notebookcheck [C] |
| PWR-2 | Idle power at 150 cd/m². Notebookcheck measured 4.63 W (14-inch) and 5.68 W (16-inch) at the wall [C]. | macOS idle vs macOS with an idle Linux VM running | Host W (powermetrics and wall); wakeups | 30 min | B | VM idle overhead ≤1–2 W | [C]/[P] |
| PWR-3 | Wi-Fi browsing rundown at 150 nits. Notebookcheck's script changes pages every 30 s [C]; Tom's combines web, video and OpenGL [C]; Apple browses 25 sites [L]. | Same browser and same local page set, run inside the VM, compared with a native macOS baseline | Hours to shutdown | Full rundown | Measured luminance; battery % per minute | VM runtime ≥85–90% of macOS | [C]/[P] |
| PWR-4 | H.264 1080p video loop (Notebookcheck: Big Buck Bunny, 150 cd/m², airplane mode, muted [C]) | mpv loop in the VM (software decode) vs macOS (VideoToolbox) | Hours | Full rundown | B | Report the gap, which reflects the missing hardware decode | [C] |
| PWR-5 | Full-load rundown. The 14-inch went from 100% to 3% in 49 min [C]. | Same identical-code combined load in the VM | Minutes; performance vs battery % | Full rundown | Performance per loop vs battery % | Performance stable down to ≤5% battery; the M4 Max held to 4% [C] | [C] |
| PWR-6 | Power-mode matrix: Low / Automatic / High, each on AC and on battery, running CPU-1/2 and GPU-1/2 | Same matrix with the VM; the host power mode governs the guest | As for each test | As for each test | Mode verification | Expected effects present and High Power verified as applied. Reference points: Low Power roughly 65–71% of GPU performance on M4 Pro [C]; Low Power caps the SoC at about 13 W on the M5 Max [C]. | Apple, Notebookcheck, Eclectic Light [C] |

**Stability and soak**

| ID | macOS-side reference | Linux counterpart | Metric(s) | Duration / loops | What to log | Suggested pass criterion | Evidence |
|---|---|---|---|---|---|---|---|
| SOAK-1 | stress-ng, same version (macOS supports a subset of stressors) [L] | `stress-ng --cpu 0 --vm 4 --vm-bytes 60% --verify --metrics-brief --timeout 8h --log-file soak.log` (`--tz` is native Linux only) [L] | Verify failures; drift | 8 h | Kernel log, PSI, host power and thermal | 0 failures; 0 kernel warnings | [L] |
| SOAK-2 | memtester | memtester (same version) plus stressapptest `-s 14400 -M <~80% RAM> -W` [L] | Errors | 4–8 h | B | 0 errors | memtester [C] |
| SOAK-3 | fio verify soak with `ioengine=posixaio` | Same job file (`posixaio`) plus an `io_uring` variant: `verify=crc32c verify_backlog=1024 verify_fatal=1 time_based=1 runtime=4h` [C] | Verify and I/O errors; bandwidth, IOPS and p99 latency over time | 4 h | SSD temperature on the host; I/O errors | 0 verify or I/O errors; ≤10% throughput drift once steady state is reached | fio docs [C] |
| SOAK-4 | Repeated XcodeBenchmark runs, as a macOS analogue [L] | Linux kernel `make -j$(nproc)` build loop | Time per build; failures | 20 iterations or 8 h | B | 0 failures; CV ≤2% | [P] |
| SOAK-5 | 3DMark stress test (20 loops per standard run; UL lists no loop-count option for macOS [C]) | GPU-2, vkmark, or glmark2 `--run-forever` | FPS drift; errors | 2–8 h | B | 0 GPU hangs or device-lost errors; drift ≤3% | [C]/[P] |
| SOAK-6 | PTS on macOS (supported [C]) | `TOTAL_LOOP_TIME=120 PTS_CONCURRENT_TEST_RUNS=3 MONITOR=all phoronix-test-suite stress-run <tests>` [C] | Completion; errors; sensors | 2 h | PTS sensor output | 0 failures | PTS docs [C] |
| SOAK-7 | Mixed creative concurrency, as in the reference video: NLE exports, a DAW, an LLM and many apps at once [C] | Linux analogue: parallel ffmpeg encodes, a real-time audio DSP load (PipeWire/JACK), llama.cpp and many browser tabs | Completion; UI latency; audio xruns; OOM events | 30–60 min | Memory pressure, PSI, swap | 0 crashes or OOMs; xruns counted and reported | Video [C]/[P] |
| SOAK-8 | Host sleep/wake while the VM runs; VM pause/resume | Same. Native suspend comes later (sleep does not work on M3 Asahi yet [C]). | Resume success | 50 cycles | Guest clock and journal | 100% successful resumes; no guest errors | [C]/[P] |

**Overall pass logic [P]**

1. **Tier 0, functional.** There must be 0 crashes, hangs, panics, oopses, WARNs, RCU stalls or GPU resets. There must also be 0 data-verification failures across stress-ng `--verify`, fio verify, memtester, stressapptest and output hashes.
2. **Tier 1, sustained behaviour.**
   - CPU: the sustained ratio is at least 95%, which is a first-to-last drop of 5% or less.
   - GPU: UL stability is at least 97% [C].
   - Exception: where macOS itself fails on this machine and mode (the 14-inch chassis, or Automatic on 26.6.2), require Linux to be no worse than macOS minus 2 points.
3. **Tier 2, parity on identical code.**
   - CPU in the VM should reach at least 92–95% of macOS. Expect 4–8% overhead from the anecdotal M1 Max Geekbench data [L].
   - Native Linux should reach at least 97%.
   - GPU through Venus has no fixed target yet. Start by tracking it against the macOS same-API result (MoltenVK or KosmicKrisp) and against Metal. The llama.cpp precedent suggests an initial expectation of about 50–60% of Metal [C].
4. **Tier 3, efficiency.** Host energy per task should be within 10% of macOS. Battery life with an idle VM should be at least 85–90% of macOS alone.

---

## Linux/Asahi evidence

### Asahi vs macOS on the same hardware (CPU)

**Phoronix, M1 Mac mini, 2022-03-23 [C].**

- Compared macOS 12.3 against the Asahi alpha, each using its default compiler (Clang on macOS, GCC on Asahi) with the same flags.
- Asahi was competitive, and led in some WebP tests.
- macOS was clearly faster in some tests because Linux was not reaching the M1's P-core boost states at the time.
- Phoronix cautioned that I/O results are unreliable because macOS handles fsync poorly.

**Phoronix, M2 MacBook Air (8 GB), 2022-08-09 [C].**

- Compared macOS 12.5 against Asahi.
- Asahi was competitive across many CPU tests, and macOS was much faster in OpenJDK/Java.
- Linux exposed no SoC power sensors then (no RAPL/PowerCap equivalent), so Phoronix could not compare power.

### Power management and battery

- **EAS and utilization clamping, January 2024 [C].** The M2 MacBook Air went from about 6 hours at an idle desktop to 8–10 hours of YouTube playback, or 12–15 hours of desktop use.
- **Linux 7.2 progress report, 2026-08-26 [C].**
  - The deep WFI idle state is still downstream-only, because upstream requires PSCI and Apple cores have no EL3.
  - A PSCI conduit built on UEFI runtime services is under RFC.
  - From M4 onward, mBoot locks the WFI state-retention bits, so WFI can wipe core state and crash the system.
- **M2 feature matrix [C].**
  - cpufreq is upstream since 6.2, and deep cpuidle remains downstream.
  - SMC support arrived in 6.18; hwmon sensors (voltage, current, temperature, power) were accepted for 6.19.
  - Battery info arrived in 7.1 for M2 Pro/Max MacBook Pros.
  - The AVD video decoder is downstream; the AVE encoder and ProRes are "TBA"; the ANE driver is out of tree.
  - Thermal and fan management have no entry in the matrix [U].

### Hardware coverage relevant to the M5 Max

- **M3 [C].** Asahi has officially supported M3, M3 Pro and M3 Max since 2026-09-06. GPU 3D acceleration is neither performant nor power-efficient yet, sleep does not work, and HDMI is disabled.
- **M4 and M5 [C].** NVMe works, PCIe enumerates, and a crash when multiple cores were enabled has been fixed. Neither chip is in the installer yet.
- **Implication for this project [C].** Native Linux on this M5 Max is not yet possible with Asahi. All current Linux numbers will therefore be VM numbers.

### GPU and LLM comparisons

- **Asahi vs macOS on an M2 Max, Dec 2024, same build [C].** Running Mistral 7B Q4_K_M:
  - macOS with Metal reached 580.26 t/s (pp512) and 61.18 t/s (tg128).
  - Asahi with Vulkan on Honeykrisp reached 92.16 and 21.93 t/s.
  - Later comments in that thread (2026) show Vulkan optimisation work on M1 that raised pp512 on a 3B model from about 156 to about 190 t/s.
- **Containerised Vulkan vs native, M2 Max Mac Studio, April 2025 [C].**
  - Native Metal reached 746.06 / 71.36 t/s (pp512 / tg128) with Llama 2 7B Q4_0.
  - The same model inside a Podman/krunkit container using Vulkan over Venus reached 428.47 / 35.88 t/s, roughly 57% and 50% of native.
  - Vulkan flash attention fell back to the CPU on this path.
  - This is the closest public precedent for a QEMU + virglrenderer Venus guest.
- **Asahi gaming stack, 2024-10-10 [C].** The game-playing toolkit runs x86 games through FEX, Wine, DXVK and vkd3d-proton inside a muvm micro-VM. The VM exists because x86 code expects 4K pages while Apple systems use 16K. Most games need 16 GB of memory, and the release was an alpha.
- **Vulkan on macOS for the host side [L].**
  - A QEMU RFC from December 2025 adds Venus support for macOS hosts, with most of the work going into virglrenderer.
  - LunarG's KosmicKrisp (Mesa Vulkan over Metal) is now Vulkan 1.4 conformant and targets macOS 26 and later.

### VM CPU overhead (anecdotal) [L]

On an M1 Max, Geekbench 6 under native macOS scored 2437 single-core and 12803 multi-core. Fedora 38 under UTM (QEMU) scored 2324 / 11829, about 5% and 8% lower. Under Parallels it scored 2333 / 12020.

Eclectic Light measured a macOS guest at about 6% below the host in single-core Geekbench and about 8% below for Metal GPU (paravirtual device) [C]. That guest was macOS, not Linux.

### Sustained-load comparisons [U]

I found no published, controlled sustained-load comparison of Asahi and macOS on Apple Silicon: no 30-minute loop with temperature, fan and power logging on both OSes. There are anecdotal reports of fanless M1 Airs running warmer or throttling on Asahi [L]. This is the gap this project's methodology would fill.

### Inaccessible sources

OpenBenchmarking.org test-profile pages showed a Cloudflare check, which I did not attempt to bypass. AnandTech's Apple Silicon deep-dives now redirect, and the Wayback Machine was not reachable from my tools. I therefore could not cite their methodology [U].

---

## Reference video summary

**Video.** "M5 Max MacBook Pro Stress Test - This is INSANE!" by Mark Ellis Reviews, published 2026-04-03. It runs 21:29 and had 47,323 views when read [C].

**Chapters** (marked as auto-generated) [C]:

- 0:00 Introduction to the test
- 1:26 Workstation upgrade (sponsor segment)
- 2:41 Video editing stress tests
- 10:07 Audio production workflow
- 13:17 AI and multitasking stress
- 20:30 Final conclusion

**Description** [C]. Mostly links: the 16-inch MacBook Pro (M5 Max), UGREEN docks (the sponsor), Final Cut Pro, DaVinci Resolve, Logic Pro and LM Studio. It gives no test settings.

**How I read it** [C]. YouTube's transcript panel did not load: its `get_transcript` request returned HTTP 400 in the signed-out browser. I read the auto-generated English captions that the player loads instead. Automatic speech recognition errors are possible; for example, the model name was transcribed as "Lama 3.1 Neotron", which is presumably Llama 3.1 Nemotron. No transcript text is reproduced here.

### Machine tested [C]

- 16-inch MacBook Pro with M5 Max: 18-core CPU, 40-core GPU, 128 GB unified memory, 4 TB SSD, nano-texture display.
- The presenter puts its price at about £/$6,000.
- Screen recording ran throughout the test.
- Activity Monitor was the only monitoring tool, used for memory pressure and per-app CPU and memory.

### Settings [U]

- **Power mode.** Low, Automatic or High Power is never mentioned.
- **AC or battery.** Not stated. At the start he briefly unplugs a cable to show the laptop. The sponsor segment shows a Thunderbolt 5 dock on his desk, but the video does not say whether the laptop was on AC during the tests.
- **Other conditions.** The macOS version, ambient temperature and elapsed times for the exports are not given. The video is edited, so timestamps cannot be used as durations.

### Workloads, in order

**1. Video editing (from 2:41) [C].**

- Final Cut Pro exported a 10-minute 4K multicam timeline (two cameras, 4K 4:2:2 10-bit footage) to uncompressed 10-bit 4:2:2. Final Cut estimated the output at about 1.2 TB.
- At the same time, DaVinci Resolve rendered the same footage to QuickTime Apple ProRes at 8K (7680×4320) with high-quality advanced options.
- A Logic Pro project played in the background throughout.
- Both exports finished on camera within a few minutes of video time. The fans became loud, and he described the chassis as only slightly warm.

**2. Longer exports [C].**

- He built 4-hour timelines in both editors.
- Final Cut exported to the "Apple Devices" preset, 4K, "better quality", with an estimated output of about 36 GB.
- Resolve exported to H.264 at UHD.
- These exports ran for the rest of the video. Final Cut stayed at 0–1% for many minutes and reached only 2% by about 18:30. Resolve progressed further but did not finish on camera.
- Activity Monitor then showed Final Cut at about 20 GB and Logic at about 8 GB, with some memory pressure.
- The App Store and Safari stayed responsive.

**3. Audio (from 10:07) [C].**

- Logic Pro ran a 193-track project of Apple Loops, AI/session drummers and the Alchemy synth, using built-in plugins only.
- He added effects and duplicated tracks; the UI paused briefly while it processed some of the copy and paste.
- He bounced the full project quickly.
- Around 13:00, Activity Monitor showed a VideoToolbox decoder service using about 22 GB. Total memory in use was 93 of 128 GB.

**4. AI and multitasking (from 13:17) [C].**

- He ran Llama 3.1 Nemotron 70B Instruct (about a 42 GB model) in LM Studio, with a long-form generation prompt for a 30,000-word game-design document. The exports and Logic playback continued in parallel.
- Activity Monitor listed Final Cut, then Logic, then the VideoToolbox decoder as the top CPU users. LM Studio showed only about 169 MB in the per-process memory list; the presenter was unsure why [C].
- He then opened every app in /Applications at once and many Safari tabs, and played a YouTube video.
- The LLM finished its generation, and he submitted a larger follow-up prompt.
- At about 20:15, memory in use was 116 of 128 GB, and he described memory pressure as still moderate.

### Results and observations

- **No crash [C].** There was no system crash, no app crash, and no forced quit.
- **One audio-engine failure [C].** Logic Pro raised a single "System Overload" error, which the presenter attributed to the combined load. After he dismissed the dialog, playback resumed.
- **Playback hitches [C].** He noted some brief jerkiness in Logic playback during the AI segment.
- **Slow Final Cut export [C].** The 4-hour Final Cut export barely advanced under contention. The video does not establish whether this was CPU, media-engine or I/O contention, deliberate background deprioritisation, or simply a very large job [U].
- **Nothing measured [C].** No temperatures, clock speeds, power, fan speeds, tokens per second or export times were reported.
- **His conclusion [C].** Realistic workloads cannot push this configuration to its limits. He acknowledged the test was deliberately unrealistic.

**Use for this project [P].** Treat the video as a qualitative template for a mixed-concurrency soak (SOAK-7), not as a baseline. To make it reproducible, fix the inputs (clips, project, model, prompt) and log the following:

- export throughput (frames per second over time) and per-stage completion times;
- audio xruns or overload events;
- LLM tokens per second;
- memory pressure and swap;
- host power, frequency and thermal data.

---

## Gaps/caveats

- **No identical-code equivalents for the reviewers' headline tools [C].** Cinebench and 3DMark run only on Windows and macOS. Cross-OS comparisons must use substitutes (7-Zip, Blender from source, Vulkan samples, llama.cpp), so absolute scores will not map onto published reviewer numbers. Anchor the macOS side with both the reviewer tool and the substitute.
- **The VM is not Linux running on the hardware [L].**
  - The macOS host still governs scheduling, power and thermals.
  - The guest's GPU path is virtio-gpu (virgl or Venus) translated to MoltenVK or KosmicKrisp.
  - The media engine is not exposed.
  - Guest results therefore measure host plus hypervisor plus translation-stack overhead, and must be re-baselined once native Linux exists.
- **No native M5 Linux yet [C].** Asahi has not enabled M4/M5. Known M4+ firmware behaviour (WFI state loss) means native idle and power results will differ from M1–M3 Asahi experience.
- **The machine's own variability [C].**
  - Chassis size (14 vs 16 inch), macOS point release (26.3.1 vs 26.6.2), power mode and adapter limits all change results by 10–25%.
  - The project's chassis size is not stated in the brief; confirm it [U].
  - macOS 27 introduced SMC firmware interface changes (per the Asahi Linux 7.2 report), and power behaviour already shifted between 26.x point releases; re-baseline after any OS upgrade [C].
- **Power mode may not apply [C, as user reports].** The forum thread reports High Power mode not applied on some M5 Max machines, and a third-party fan curve changing sustained results. Verify the mode with `system_profiler` and `pmset`, and keep fan tools off.
- **Battery assist on AC [C].** Wall-power efficiency figures can be distorted when the battery supplements an insufficient adapter; Notebookcheck flagged this for its 14-inch efficiency numbers. Always log the battery delta.
- **Telemetry limits [C/L].**
  - Package power is no longer in `powermetrics` [C].
  - Power values are estimates [L].
  - Fan RPM needs third-party SMC tools [L].
  - Tom's Hardware states that macOS does not expose clock speeds; in fact `powermetrics` and `macmon` report cluster frequencies [C], so that statement reflects their tooling.
- **Benchmark version sensitivity [C].**
  - llama.cpp M5 Max results differ about threefold in pp512 between commits (about 1,000 vs about 3,200 t/s for 7B Q4_0), probably because of the Metal tensor path [L].
  - PugetBench and 3DMark results are only comparable within the same version.
  - Pin and record versions for every run.
- **Sources of lower confidence [L].** Some items come only from search summaries or single user reports and are labelled [L]: the Lemmy VM numbers, the Sascha Willems flags, the stress-ng macOS stressor coverage, the Apple battery-test footnote, and the LM Studio tensor-path issue. Verify these before relying on them.
- **Reference video [C].** It is entertainment-oriented, with no quantitative data or test conditions, and is sponsor-integrated (UGREEN). Captions are machine-generated.
- **Proposed thresholds [P].** Apart from UL's 97% stability rule [C], all pass thresholds here are proposals. Calibrate them after the first macOS baseline runs on this exact machine.
