# Progress Log

Newest first. Each milestone lists: discovered, implemented, tested,
measured, still unsupported, and next.

---

## 2026-10-13 · Agent B: dedicated M5 entry procedure, no host changes

* Prepared `kernel/native-enablement/boot-entry-setup.md` at the user's request.
  Read-only checks found about 1.017 TB free, no lab entry, original FileVault
  enabled and the exact 26.6.2 / 25G83 Apple installer available (~18.4 GB).
* Proposed a second full macOS installation named `iLinux Boot Lab` in the
  current APFS container, then a lab-only custom m1n1 boot object. Described
  shared metadata/possible installer firmware effects and explicit approval.
* Checked local kmutil/bputil help, Apple pairing/volume instructions and Asahi
  stage-two source. The Recovery preflight checks separate System/Data group
  identity, payload/build and paired 1TR without saving identifiers.
* Validation: five shell blocks parse; a simulated valid preflight passes and
  eleven mismatch/error cases fail. Rehashed the actual 3,932,160-byte m1n1.
  No claim of actual Recovery, installer or native hardware validation.
* No installer downloaded; no volume, boot policy, startup setting or reboot
  changed. Next: M1 receipt, then separate authorization for the reviewed
  installation procedure, Stage A and eventually Stage B.

## 2026-10-13 · Agent B: first-boot package and corrected controller launcher

* User authorized preparation, launcher/instruction fixes and GitHub handoff,
  explicitly stopping before boot settings. Work is in the published checkout.
* Exported the three existing job-020 artifacts and matched every original
  checksum. Clean-linked unmodified pinned m1n1 in the Linux VM; prepared a
  Stage-B DT with NVMe/cpufreq disabled and a static diagnostic initramfs.
* Added an offline-default, checksummed launcher with no SMP-start, cpufreq-init,
  setup.py/PMU reset or shell. It checks chip/build/board, secondary state,
  framebuffer and the final DT before a separately approved handoff.
* Validation: 17 tests on macOS and ARM64 Linux, one real-proxy-serializer test,
  zero Stage-B schema diagnostics; diskless VM reaches PID 1 and sustains one
  CPU/heartbeats for 60 seconds. No native M5 compatibility result.
* Corrected the APFS boot-entry prerequisite, unsupported persistent USB/log
  assumptions, and HID provenance (object-tested separately, not in Image).
* Integrated M1 commit `33d99f7`, preserving its receipt tools. Seven intake
  regressions pass; its verifier accepts the actual package with boot approval
  still false. Sender manifest digest and revision metadata are included.
* Handoff: `native/boot/README.md`; job-021 results and manifest. Payload is a
  private prerelease asset, not a Git blob. M1 verifies offline and stops.
* Remaining: separately reviewed OS-entry provisioning and user approval,
  then physical P_NOP and RAM diagnostic. No boot/security/partition change.

## 2026-10-13 · Second-machine agent: native package intake ready, boot on hold

* Created ignored inbox/receipt/result directories under `build/native-intake/`.
  Added a streaming SHA-256 verifier using the sender's separately supplied
  manifest digest; checks required payloads and declared target revision.
* Recorded `57a9339ffd1876e78297b17d34dece8cff8fa1ba` as the client pin. The
  shared runner checks the revision and clean checkout before invocation.
* Seven synthetic intake regressions pass (valid receipt, corruption,
  manifest mismatch, revision mismatch, missing/extra content, links and
  traversal); both existing USB fake-transport tests pass with the pin guard.
* Added an approved-boot result template with provenance, observations,
  timeout/recovery and explicit NOT RUN defaults. No real package or result
  has been received, and no USB connection or boot command was attempted.
* Per user: wait for corrected single-core launcher and boot-entry procedure;
  upstream linux.py stays on hold. First live action is bounded handshake,
  followed only by approved diagnostic boots and recorded observations.

## 2026-10-13 · Second-machine agent: LLVM and non-mutating USB checker

* Installed a minimal official LLVM 23.1.3 macOS ARM64 toolchain inside ignored
  `third_party/`; SHA-256 matches GitHub's release asset digest. The archive
  is removed after extraction. No global install or PATH changes.
* Actual upstream ARMAsm builds `nop; ret` for ARM64 ELF: clang, lld,
  objcopy, nm and objdump pass, including exact expected instruction bytes.
* Added an explicit USB connection checker: only P_NOP, 10-second bound,
  no setup.py, feature negotiation, memory/register access or boot request.
  Fake-serial tests verify the serialized request and close-on-timeout.
* Default discovery opens nothing; no device is detected. Explicit serial
  opening can interrupt target autoboot into proxy mode. No M5 session run.
* Remaining: verified backup (user reports in progress), cable, approved
  target entry/version, physical check and checksummed Stage-B artifacts.

## 2026-10-13 · Second-machine agent: proxy client prepared offline

* Prepared ignored m1n1 checkout at the plan's `57a9339ffd1876e78297b17d34dece8cff8fa1ba`
  and a workspace venv with upstream-pinned construct/pyserial wheels.
* Python 3.9.6 imports proxy/proxyutils/shell/HV successfully; pip dependency
  check passes. The local offline checker opens no devices. No USB modem
  path is currently present, and no hardware session was attempted.
* User reports the M5 backup is in progress. Remaining: verified backup,
  data cable, target m1n1 entry/version, physical handshake, checksummed
  job-020 payload transfer, and LLVM tools for assembly-dependent operations.
* Flagged upstream shell's startup panic-counter reset and home-directory
  history, and `linux.py`'s need for `--compression none` with raw `Image`.
* Handoff/check command: `tools/m1n1-client/README.md`. No target boot,
  security change, host-wide package installation or upstream edit.

## 2026-10-13 · Second-machine agent: GitHub checkout setup

* Downloaded the private `nickyrice04/ilinux` repository on the user-designated
  second macOS machine; local `main` tracks `origin/main`.
* Git 2.50.1 is installed; GitHub CLI 2.102.0 authenticated as `nickyrice04`
  with credentials in the OS keyring. Git fetch and push dry-run succeeded;
  GitHub reports push permission. This entry is the real push verification.
* Set repository-local commit identity to the account's GitHub noreply
  address, fast-forward-only pulls and simple pushes.
* Recorded user authorization for GitHub handoffs and cross-machine
  coordination limits. No native boot, USB proxy test or build performed.
* Next: prepare/check the second-machine m1n1 proxy environment and cable
  before the separately authorized native gates. Ignored build artifacts
  and VM disks are absent from this checkout.

## 2026-10-13 · Agent B: native CPU dispatch, idle hooks and startup guard

* **Investigated:** REA/Ghidra completed six CPU/idle queries; 872 instruction
  words match original bytes and LLVM. `enableCluster` pseudocode is rejected;
  two bounded idle hooks and selected mapping/writer paths were reviewed.
* **Implemented:** an original read-only kernel-collection reference parser.
  Twelve PMGR dispatch entries resolve to exact symbols; eleven stored
  call-site discriminators agree. Seventeen synthetic parser tests pass on
  ARM64 Linux; all 43 analysis-tool Python tests pass on the host.
* **Corroborated:** a further 51-instruction slice connects the literal
  `clusters` property to the descriptor pointer read by the startup routine.
  This strengthens H2 but does not prove live branch/register semantics.
* **Implemented/tested:** a conservative public-m1n1 startup guard and
  actual-function harness: one baseline regression reproduced; eight patched
  cases pass under GCC and Clang ASan/UBSan. Mismatch has zero startup writes
  or shared-state changes. Complete patched `smp.c` compiles to ARM64 `smp.o`.
  The first object attempt exposed a missing copied header; setup fixed and
  the final batch passed. No boot image linked or deployed.
* **Next:** A can use the optional guard after testing the unmodified native
  baseline. B's remaining question is live branch/register-map selection,
  followed by GPU/display and idle/context restore. A owns native builds,
  DT validation and C's handoff. The analysis VM is stopped; B's lock released.
* **Handoff:** `reverse-engineering/findings/cpu-startup-2026-10-13/handoff.md`
  (F-076/F-077, D-042). No native compatibility or performance gain claimed.

## 2026-10-13 · Agent B: driver-interface REA and Linux input robustness

* **Investigated:** GPU/display, N1 network/Bluetooth, ANE host API, ISP,
  audio/mic and HID/shared transports. REA/Ghidra completed 17 functions;
  Apple LLVM and original bytes agree on 1,107 instruction words. Four
  whole-function pseudocode results are rejected; others remain reviewed
  static evidence with explicit unresolved dispatch/ownership.
* **Implemented/tested:** local DockChannel HID bounds/cleanup/rearm patch,
  against pinned Asahi source; seven actual extracted driver functions in
  ARM64 Linux. Ten baseline regressions reproduce, all pass after patch,
  plus three valid cases (Clang ASan/UBSan). Full kernel-object/native tests
  remain pending; the VM virtio-input driver is unchanged.
* **Measured:** synthetic parser median 29.581 → 29.868 ns/packet (+0.97%),
  six 10-million-packet runs. This is software overhead, not physical input
  latency or power. No hardware performance gain claimed.
* **Implemented:** original ACIPC geometry/span helpers and strict N1
  operational-config extraction; 8,525,654 arithmetic cases and 18 Python
  tests pass in Linux. Real AirshipDK ring functions were located behind
  DriverKit stubs and analyzed through a narrowly extracted ELF carrier.
* **Next:** A's native build can consume the standalone HID patch; B's
  next REA questions are N1 descriptors/ordering and ISP firmware startup.
  The tested ISP pool/scaler command IDs and sizes match existing Linux.
  C still configures a native installation only after the existing gates.
* **Handoff:** `reverse-engineering/findings/driver-interfaces-2026-10-13/handoff.md`
  (F-073–F-075, D-041). No macOS, boot, firmware or live-VM changes.

## 2026-10-13 · Agent B: isolated REA/Ghidra and native SMP evidence

* **Implemented:** diskless Linux analysis lab, Ghidra 12.1.4 ARM64 native
  decompiler build with JDK 21 and REA 6.4.0; safe kernel-payload/member
  extraction and provenance checks. No live Omarchy disk or A-owned changes.
* **Observed:** the actual ARM64e carrier includes PMGR/CLPC/SoCTuner/NVMe;
  the visible `.kc` files are Intel. Four REA driver dossiers obtained;
  all 554 instruction words independently cross-checked with LLVM and the
  original carrier. Three pseudocode results fail function-boundary checks.
* **Implemented/tested:** original evidence gate, sanitized ADT layout audit
  and portable C startup-mask prototype. The latter exercises existing SMP
  hypothesis H2 without MMIO. 24 Python tests pass on macOS and ARM64 Linux;
  C tests pass with Linux GCC and macOS ASan/UBSan, including 18-core
  uniqueness and 5,984 valid single-cluster masks.
* **Limits:** experimental Alpine provider environment; unknown collection
  fixups/cross-member dispatch; candidate mask semantics, RVBAR and physical
  SMP remain unverified. No native performance or compatibility gain claimed.
* **Handoff:** `reverse-engineering/findings/rea-native-2026-10-13/handoff.md`
  (F-070–F-072, D-040). Analysis VM stopped and `quiet` released. A continues
  vmpoll/F-050; agent C's native configuration role stays behind native gates.

## 2026-10-13 · Agent A, goal 4: fixed VA-API driver is the VM default

The user assigned agent A goals 4–7. Goal 4 done:

* **Shipped** `vm-integration/etc/environment.d/70-ilinux-vm-video.conf`, so
  desktop-launched `mpv`/FFmpeg use `mesa-virgl-video-ilinux` by default
  (lossless-download fix + NV12 decode), no `ilinux-video` wrapper (D-032).
* **Verified** after a fresh boot: a session-launched `mpv r2160.mp4` loads
  `/usr/lib/ilinux-va/virtio_gpu_drv_video.so`, `Using hardware decoding
  (vaapi)`, `VO: [gpu] 3840x2160 vaapi[nv12]`; download regression 0/180
  mismatched; GL and Vulkan unchanged (F-055).
* **Gotcha recorded:** `sudo -u omarchy` bypasses `environment.d`, so VM
  session tests must launch through the session (`systemd-run --user`).
* **Not done:** on-screen visual capture (hyprlock idle-lock blocked grim;
  decode is frame-exact and the zero-copy display path was validated earlier,
  F-048/F-051). A fresh floating-window power run is offered, not taken.
* **Goals 5–7 note:** A owns them per the user. B's RE/driver-interface work
  feeds A as evidence; A owns the native build/validation (5), backup prep
  (6) and the handoff kit (7). Confirm with the user if B expects to own any.

## 2026-10-13 · Agent A: DT compatible audit (and a correction)

Audited the draft t6050 DT's compatibles for probe-readiness. **Result: the
DT is already correct — schema-clean and probe-ready; no change needed.**

* **Correction:** my job-020 report of "248 DT schema warnings" was a grep
  error. The filter matched any log line containing `t6050`, which caught
  warnings for *other* Apple SoC DTBs whose allowed-enum text lists
  `apple,t6050-*`. Attributed by dtb-path prefix, **`t6050-j716c.dtb` has 0
  dtbs_check warnings.** Fixed the filter in `run.sh`; corrected F-056,
  RESULTS.md and AGENTS.md.
* **Probe audit** (`kernel/experiments/t6050-dt/probe-audit.sh`, run against
  the built tree): every bring-up-critical device matches a driver on its
  t6050 string or generic fallback (AIC, DART, mailbox, PMGR, NVMe, SART,
  pinctrl, cluster-cpufreq, WDT, I²C, UART). The only non-matches are the 18
  CPU cores (`apple,sotra-m/p`) — correct, as CPUs are core-enumerated and
  both names are already in `cpus.yaml` (like M4's `apple,donan-e/p`).
* Probe *matching* is confirmed; actual *probing* and firmware startup remain
  runtime questions for the first native session.

## 2026-10-13 · Agent A, goal 5+7: native kernel build and handoff kit

Per the user, goals 5 then 7 are prioritized; goal 2 is checkpointed below
and goal 3 deferred unless they block native work.

**Goal 5 (native kernel build + first-boot plan), in progress:**

* Read the native-enablement plan and both REA handoffs. Separated this
  machine's facts from inherited M5 Pro reports: m1n1 single-core boot and
  the SMP failure are M5 Pro reports (chip-id 0x6050); this unit is an M5 Max
  (also 0x6050), so single-core boot here is Likely, not Confirmed, and the
  SMP failure is not a local observation. Recorded in the first-boot plan.
* **Reproducible full build** as job `020-t6050-full-build` (runs in the
  Linux guest toolchain, not the live-VM measurement path): fetches pinned
  AsahiLinux/linux `77cb8f24`, applies the committed t6050 series (0001-0007,
  am exit 0), configures a 16 KiB-page bring-up kernel (framebuffer console,
  initrd, Apple drivers, dockchannel), builds `Image` + modules + DTBs, runs
  `dtbs_check`, builds the **real in-tree `dockchannel-hid` driver** baseline
  vs the a351bff hardening patch (new-vs-baseline warning diff), and makes a
  static diagnostic initramfs. Build results committed separately.
* **[First-boot plan](kernel/native-enablement/first-boot-plan.md):** the
  credible early-boot observation path is the **m1n1 USB proxy** (second
  machine, pre-Linux) plus the **framebuffer console** (simpledrm on mBoot's
  framebuffer) — **not** dockchannel-UART serial, USB Ethernet, keyboard or
  SSH (each needs a missing driver or a boot-policy change). Staged tests A-E
  with expected output, failure checkpoints and uniform recovery (RAM-only;
  force-off → macOS). The exact next physical test needing user approval is
  gate N1 + Stage A (m1n1 proxy reads chip-id 0x6050).
* Fixed two build-script issues found in the first run: no `/usr/bin/time` in
  the guest (removed), and non-idempotent re-runs (now reset+clean+re-am).

**Goal 7 (config-agent handoff kit):** `native/handoff/` — VM-only files not
to apply natively, what carries over, a hardware matrix with fallbacks
(consuming B's driver-interface findings, no RE duplicated), how agent C gets
network (USB Ethernet / the second machine, since N1 Wi-Fi has no driver),
a read-only `acceptance-checks.sh`, and guardrails.

**No native boot, host-security, partition, firmware or git-history change
was made.** No native support is inferred from VM success.

## 2026-10-13 · Agent A, goal 2: cross-vCPU wakeup latency (CHECKPOINTED)

Checkpointed 2026-10-13 and deferred per the user, pending native work. The
`cpuidle-vmpoll` interim fix is committed (`f4baf47`); the `TIF_POLLING_NRFLAG`
kernel change and idle-power re-measure are **not started**. Resume only if
latency blocks native development.

* **Root cause found (F-054).** A cross-vCPU wakeup costs about 21 µs
  (one vCPU: 1.6 µs; macOS: 3.8 µs). With Apple's in-kernel GIC,
  Hypervisor.framework parks an idle vCPU inside `hv_vcpu_run`, and arm64
  always IPIs the CPU it wakes.
* **Implemented:** `omarchy-arm64/kernel/vmpoll`, a cpuidle driver with a
  bounded POLL state before WFI. A/B/A results:
  * cross-vCPU: 21.2 → 13.3 → 20.9 µs;
  * unpinned: 36.6 → 13.3 → 39.8 µs;
  * same-vCPU unchanged; idle QEMU CPU unchanged.
* **Fixed:** `cpubench pingpong` now pins each end (`-c A,B`).
* **Deferred next (not started):**
  1. Repeat the matrix plus an idle-power ABBA under the `quiet` lock.
  2. Add `TIF_POLLING_NRFLAG` to arm64 in the VM kernel, build `vmpoll` in,
     rebuild the package and validate (IPI-free wakeups of polling vCPUs).
  3. Re-test F-050 (goal 3).

## 2026-10-12 · Linux Mesa video: lossless downloads and NV12 decode

* **Root cause found (F-054).** A cross-vCPU wakeup costs about 21 µs
  (one vCPU: 1.6 µs; macOS: 3.8 µs). With Apple's in-kernel GIC,
  Hypervisor.framework parks an idle vCPU inside `hv_vcpu_run`, and arm64
  always IPIs the CPU it wakes.
* **Implemented:** `omarchy-arm64/kernel/vmpoll`, a cpuidle driver with a
  bounded POLL state before WFI. A/B/A results:
  * cross-vCPU: 21.2 → 13.3 → 20.9 µs;
  * unpinned: 36.6 → 13.3 → 39.8 µs;
  * same-vCPU unchanged; idle QEMU CPU unchanged.
* **Fixed:** `cpubench pingpong` now pins each end (`-c A,B`).
* **Next:**
  1. Repeat the matrix plus an idle-power ABBA under the `quiet` lock.
  2. Add `TIF_POLLING_NRFLAG` to arm64 in the VM kernel, build `vmpoll` in,
     rebuild the package and validate (IPI-free wakeups of polling vCPUs).
  3. Re-test F-050 (goal 3).

## 2026-10-12 · Linux Mesa video: lossless downloads and NV12 decode

* Continued from commit `4d8987e`; audited existing kernel patches, VM,
  benchmarks and current Asahi evidence. The top native gaps are boot/SMP,
  G17 GPU/DCP and idle/DVFS, with precise uncertainties in
  `reports/bottleneck-priorities-2026-10-12.md`.
* **Implemented and installed** `mesa-virgl-video-ilinux 26.2.4-1` in the VM:
  opt-in NV12 H.264 decode plus lossless NV12/I420/YV12 CPU downloads.
  Source/recipe: `omarchy-arm64/packages/mesa-virgl-video/`.
  Use `ilinux-video mpv FILE` in the guest; system Mesa/GL/Vulkan stay intact.
* **Validated:** final VA image/crop tests 18/18, zero incorrect bytes
  (stock: 37,008); 1,440/1,440 hardware-decoded 1080p/4K frames match software
  in the final matrix; installed package repeats it and passes another
  240/240 Baseline/Main frames. mpv hardware-decode/EGL
  smoke passes 120 frames. Package builds and installs; `pacman -Qkk` passes.
* **Measured:** paced 4K60 decode, two ABBA blocks, QEMU CPU use falls from
  0.2962 to 0.17385 cores (**41.3%**). Whole-SoC power is noisy; no energy or
  display-performance gain is claimed. F-052/F-053, D-031.
* **REA:** actual metadata evidence for the renderer and AppleVideoDecoder
  arm64e, plus bounded LLVM disassembly of the H.264 factory. REA deep
  analysis reports missing backends; no successful decompilation claimed.
* **Corrected F-045:** current failure is cross-format download, not every
  CPU readback. An experimental dirty-flag change failed to fix it and was
  removed. The final fix bypasses shader conversion for lossless 4:2:0.
* **Limits:** VM only; shader conversions outside the even/progressive
  fast path, decode fences, other codecs and native hardware remain open.
  Full method, evidence, build limits and next work:
  `reports/video-download-and-nv12-2026-10-12.md`.
* No macOS system, boot, firmware, partition, security or personal-data edits.

### Next

1. Investigate F-050's intermittent guest display stall using DRM fence and
   compositor timing evidence.
2. Run controlled on-screen playback/power comparisons with the NV12 driver.
3. Trace the remaining shader conversion path (odd crops, scaling, interlace)
   and add proper decode-fence lifetime handling before async host decode.
4. Prepare full native-kernel/schema validation and a reviewable, explicitly
   authorized native boot experiment; do not infer hardware support from VM tests.

## 2026-10-12 · Display path: measured stage by stage; mpv defaults; methodology fix

### Discovered

* **mpv's default scaling was most of VM video power** (F-048).
  * 4K60 hardware playback: 7.3 W with mpv's defaults (linear-light
    downscaling, wide filters, dithering), 3.9 W with `profile=fast`.
  * Decode alone is 3.0 W.
  * The guest display chain itself is cheap: a fullscreen 60 fps client that
    only clears costs about +0.8 W over idle.
* **Hidden windows are never drawn** (F-049).
  * During the VM runs the VM window was off screen, so QEMU and
    WindowServer presented nothing. The native player's window was on screen.
  * So the `COCOA_GL_NOPRESENT` A/B compared two non-presenting runs, and
    VM-vs-native playback ratios aren't like for like yet.
  * F-046 is corrected accordingly.
* **Hyprland direct scanout brings no saving in the VM.** Every flip becomes a
  scanout switch in QEMU, so it stays off.
* **mpv `--vo=dmabuf-wayland` fails.** The compositor can't import VA-API
  surfaces through virgl.
* **Intermittent vsync collapse to about 10 fps** in 3 of 6 fresh boots
  (F-050, open). Six causes were ruled out by measurement, including the
  screensaver, the notification overlay, CPU placement and App Nap.

### Implemented

* **QEMU 0012:** display-path measurement switches. `COCOA_GL_NOPRESENT=1`
  consumes guest frames without drawing them; `COCOA_GL_LATENCY=1` logs
  flush-to-draw latency.
* **Benchmark tools:**
  * `benchmarks/linux/vfill.c`: a fullscreen Wayland EGL client at a fixed
    fps, with full-frame damage and per-second frame counters.
  * `benchmarks/src/winvis.m`: reports whether a process has windows on
    screen, by PID, without reading titles.
  * `benchmarks/src/occlude.m`: covers the VM window, for App Nap tests.
* **`playback_power.py`:**
  * new `vfill-*` and mpv render-path cases;
  * a per-case `vm_window_on_screen` record;
  * refuses to run with a hidden VM window unless `--allow-hidden` is given.
* **macOS `playback_power.py`:** records whether the player window was on
  screen.
* **VM mpv defaults:** `vo=gpu` and `profile=fast`, alongside VA-API.

### Measured

* **Present vs no-present** (ABBA, 4 sessions): no difference. Invalid as a
  presentation measurement (F-049).
* **mpv render paths, 4K60 hardware decode:**
  * defaults: 7.28 W with `vo=gpu`, 5.92 W with `gpu-next`;
  * fast profile: 3.88 W with `vo=gpu`, 3.85 W with `gpu-next`;
  * decode alone: 3.03 W.
* **Unpaced FIFO steady state:** 120 fps; 205 s with no input showed no
  throttling.

### On-screen follow-up (same day, VM window floated with your OK)

* **Presentation measured with the window on screen** (`COCOA_FLOAT=1`).
  * 4K60 playback with the VM defaults: 3.60–4.14 W, against 2.91 W native
    (71–81%).
  * Presenting is about +0.3 W of that.
* **Latency: a guest frame waited 6–8 ms** (p95 11–13 ms) for QEMU's GUI
  tick, and only 70–80% of 120 fps output was drawn.
* **QEMU 0013, drawing on flush, is the new default** (D-030, F-051): p50
  0.14 ms, p95 about 2 ms, every frame drawn at 60 and 120 fps, no measured
  power change.
* **IOSurface presenter (opt-in, `COCOA_GL_PRESENT=iosurface`):**
  * p50 0.12 ms, and 0 torn frames in 1,200 alternating-colour frames;
  * but +0.8 W at 4K60 (ABBA);
  * Apple's GL crashes rendering into lossless-compressed IOSurfaces.
* **Vsync collapse (F-050) narrowed:**
  * it strikes alternating fresh boots, in every configuration tried;
  * it is not presentation, the window state or App Nap.
* **Tools:**
  * `vfill -a`: alternating colours, for tearing tests;
  * `winvis` now counts floating windows.

### Next

1. **F-050:** trace guest DRM flips and fences, and Hyprland's frame
   scheduling, in an affected boot. Affected boots alternate, so the boot
   after a healthy one should reproduce it.
2. **A Metal-side presenter** with compressed, framebuffer-only drawables.
   It may give the IOSurface path's p95 without its video cost.
3. **Then video encode, HEVC/VP9 decode, and the guest Mesa fixes**
   (dirty decode targets, NV12-only).

## 2026-10-12 · Hardware video decode in the VM: VA-API on VideoToolbox

### Discovered

* **The virgl video protocol isn't version-stable** (F-042). Mesa 26 sends
  shifted profile values (H.264 High = 11) and virgl format numbers. Its VA
  frontend offers I420, so FFmpeg-based players ask for 3-plane surfaces.
* **VA-API omits the PPS reference-index defaults** (F-043). They have to be
  learned from slice headers, or VideoToolbox rejects B-frames.
* **`kCVPixelBufferOpenGLCompatibilityKey` changes VideoToolbox's output.**
  With IOSurface-only output, decode is bit-exact (F-044).
* **Mesa's virgl decoder has no decode fence and never marks targets dirty**
  (F-045). Zero-copy consumers work; CPU readback returns stale data.
* **Apple's `glClientWaitSync` busy-polls** (F-047). virglrenderer's fence
  thread spun while waiting:
  * 17% of its samples during 4K60 playback, 3% under GPU-bound glmark2;
  * polling with sleeps saves about 0.3–0.4 W in 4K60 playback (ABBA
    A/B) at unchanged glmark2 throughput (528 fps).
* **Decode is no longer the gap to macOS** (F-046):
  * VM hardware decode alone: +1.1 W over idle at 4K60.
  * *Corrected later the same day:* the rest of the VM's +5.1 W was mpv's
    default scaling, not frame copies (F-048). Host presentation was not
    measured, because the VM window was off screen (F-049).

### Implemented

* **virglrenderer 0008:** a VideoToolbox backend for virglrenderer's video
  interface.
  * H.264 Constrained Baseline, Main and High.
  * IOSurface planes are blitted into the guest's surfaces on the GPU.
  * Pictures are fenced back to VideoToolbox's pool.
  * Planar targets go through a VTPixelTransferSession.
* **virglrenderer 0009:** shader-translation fix (TEX temporary writemask).
* **virglrenderer 0010:** GL fence waits poll and sleep on macOS.
  `VIRGL_GL_FENCE_WAIT=block` restores the old wait for A/B runs.
* **QEMU 0011:** `virtio-gpu-gl,video=on`.
* **Launcher and build:** video is on by default (`--no-video` opts out,
  D-029), and the build uses `-Dvideo=true`.
* **Benchmarks:**
  * `benchmarks/vm/playback_power.py` with the guest helpers in
    `benchmarks/vm/guest/` (playback and decode-only cases, ABBA order);
  * `benchmarks/macos/playback_power.py`, with `benchmarks/src/avplay.m`
    as the native AVFoundation reference.
* **Research:** `research/testing/stress-and-stability-methodology-2026-10.md`
  (65 sources):
  * reviewer methods (30-minute Cinebench loops, 3DMark 20-loop stability);
  * M5 Max sustained results;
  * proposed pass tiers T0–T3;
  * a summary of the reference stress-test video (no transcript).
* **VM integration:** `/etc/mpv/mpv.conf` (`hwdec=vaapi`, `gpu-api=opengl`),
  so plain `mpv file` decodes on the media engine with mpv's default
  `gpu-next` renderer.
* **Blockers:** Touch ID recorded as out of scope (B-014), with
  libfprint USB readers and FIDO2 keys as the Linux alternatives.
* **Validation:**
  * A from-scratch rebuild applies every patch (virgl 0001–0010, QEMU
    0001–0011).
  * The rebuilt source trees match the working trees file for file.
  * The rebuilt runtime decodes the 600-frame test clip bit-exact.
  * Omarchy.app was rebuilt.

### Measured

* **Function:**
  * `vainfo` lists `VAProfileH264High`, Main and Constrained Baseline.
  * A 1080p60 High-profile B-frame clip decodes bit-exact against FFmpeg:
    600/600 frames, 0 errors.
  * mpv plays 4K60 and 1080p60 in real time through zero-copy dmabuf
    interop, dropping 0–2 frames per 1,500.
* **Playback power** (SoC, AC, 25 s windows):

  | Clip | Native macOS | VM, hardware | VM, software |
  |---|---|---|---|
  | 4K60 | 2.91 W | 7.04 W | 17.34 W |
  | 1080p60 | 2.36 W | 4.33 W | 6.72 W |

  Hardware decode saves 59% at 4K60. The VM uses 2.4× native's power for
  4K60 playback.
* **Flat-out throughput, 4K60 clip:**
  * hardware 155 fps at about 1 vCPU, mostly guest kernel time waiting on
    QEMU's lock;
  * software 508 fps on 8.4 vCPUs.
* **Main-thread profile, 4K60 hardware playback:**
  * 20% blocked in VideoToolbox decode;
  * 5% CPU in the NV12→I420 conversion;
  * about 1% in GPU copies.

### Still unsupported or open

* **Decode coverage:** HEVC, VP9 and AV1 decode, and VA-API encode on
  VTCompressionSession.
* **CPU readback of decoded surfaces:** needs a guest Mesa fix (F-045).
* **The I420 conversion:** a guest Mesa change offering only NV12 for
  decode would remove it.
* **Synchronous decode on QEMU's main thread:** making it asynchronous
  needs completion tracking in vrend (F-045).
* **~~Presentation costs about 4 W at 4K60~~:** corrected. It was mpv's
  scaling (F-048). Host presentation is still unmeasured (F-049).

### Next

1. **Presentation path:**
   * QEMU's Cocoa display presenting the guest scanout as an IOSurface
     layer (zero-copy into WindowServer);
   * check Hyprland direct scanout in the VM;
   * rectangle sampling in vrend for zero-copy imports.
2. **Guest Mesa patch:** dirty decode targets and NV12-only decode
   surfaces.
3. **HEVC and VP9 decode, then encode;** test Chromium's VA-API path.
4. **Defaults:** make hardware decode the default in the VM's mpv and
   browser configuration.

---

## 2026-10-12 · Vulkan in the VM: Venus on MoltenVK, presenting at 120 Hz

### Discovered

* Venus bring-up on macOS needed six host-side fixes: proxy init,
  stream sockets, partial reads, FIFO eventfd, no `MAP_FIXED` under HVF,
  and the info-table entry (F-035).
* HVF never mapped sub-page blobs, and its data-abort handler retried the
  guest's store forever: vkcube spun in `memcpy` (F-036).
* Apple's GL binds IOSurfaces only as rectangle textures, so vrend's
  import (`GL_EXT_memory_object_fd`) failed. That put the compositor's
  context in error: a scrambled or blank desktop (F-037).
* Metal→GL IOSurface access is ordered once the Metal work is *scheduled*
  (0/300 stale frames) but not after `commit` alone (F-037).
* Vulkan FIFO lost about a quarter of its frames to Mesa's commit-timing
  targets in the VM (F-038).
* gdb can't attach in the guest (SME without SVE); `eu-stack` works (F-039).

### Implemented

* **virglrenderer 0007:** IOSurface mirror import for Venus images on native
  CGL. A Metal blit, or a swizzle pass for RGBA, feeds a GL
  rectangle→2D blit. It waits only until the copy is scheduled, and
  unsupported formats degrade instead of breaking the compositor.
* **QEMU 0010:** host-page rounding for blob subregions; HVF rejects
  unaligned host pointers instead of aborting.
* **VM session:** `MESA_VK_WSI_DEBUG=nowlts` via `environment.d` (D-028).
* **Launcher:** Venus is on by default (`--no-venus` opts out, D-027).
  Omarchy.app was rebuilt.
* **Tools:**
  * `benchmarks/vm/vkbench.sh`: vkcube fps and CPU;
  * `benchmarks/src/vkcompute.{c,comp}`;
  * guest `vkmark` and `glmark2` installed for later runs.
* **Validation:** a full from-scratch rebuild applies every patch (virgl
  0001–0007, QEMU 0001–0010) and boots.

### Measured

* **vkcube (1272×679 RGBA16F, 2592×1458@120 output):**
  * FIFO 119.5 fps (was 92.9; before 0010 it never presented);
  * mailbox about 3,000 fps;
  * mirror 0.12 ms per update (0.87 ms with a completion wait).
* **vkcompute:** 10.6–11.0 TFLOPS, 94–98% of native MoltenVK 11.24, bit-exact.
  Submit+wait p50 381–390 µs vs 204 µs native.
* **glbench with Venus/blob on vs off:** 0.99–1.17×, no regression.

### Still unsupported or open

* **Zero-copy presentation.** It needs IOSurface-backed Venus memory plus
  rectangle sampling in vrend.
* **Real vblank pacing from QEMU.** That is the root fix for F-038.
* **Venus round trips are 1.9× native.** Feedback and ring-wakeup latency.
* **Watch item.** Two guest shutdowns stalled for minutes, with 137 virtio-gpu
  commands in flight, while the fixed bugs were present: the store-retry
  loop, and the compositor in context error. They have not reproduced on the
  final build (clean 3 s shutdowns after vkcube and vkcompute).
  `tools/vm-restart.sh` samples QEMU if one recurs.

### REA gap analysis (same day)

* **Inventory:** a metadata-only REA inventory of 727 driver bundles and 887
  launchd plists, joined with the ADT and the live IORegistry.
  * Outputs: `hardware/macos/*.tsv` and
    `reverse-engineering/macos-hardware-services.md`, a 23-row gap matrix
    with priorities and VM bridges.
  * Security components were excluded before recording.
* **New findings:** F-040 (the CLPC/SOCTuner/PPM/PTD policy layer is the
  efficiency gap) and F-041 (RTKit coprocessors throughout).

### Next

1. **Host-side bridges the gap matrix points to:**
   * VideoToolbox decode/encode remoting;
   * a Core ML/ANE API for the guest;
   * camera as a UVC device;
   * paced vblank timestamps.
2. **Zero-copy Venus presentation.**
3. **Battery and Low Power Mode measurements under Vulkan load.**

---

## 2026-10-12 · Microphone, kernel package, Omarchy.app

### Implemented

* **QEMU patch 0007:** CoreAudio capture through an AudioQueue. The guest
  sees a working capture source. A live recording was not tested on the
  user's machine (privacy).
* **`linux-ilinux-vm` pacman package:** built, installed and booted, and it
  owns its modules. The limine boot integration and the stock kernel were
  removed from the VM (D-026).
* **`Omarchy.app`:** a Mach-O stub, launch script and bundled signed QEMU.
  Its window and Dock identity show as "Omarchy". LaunchServices launch from
  the agent shell is blocked by Gatekeeper (ad-hoc signed plus provenance);
  the user approves it once.

### Next

1. Vulkan in the guest: Venus via MoltenVK or KosmicKrisp. This needs new
   source downloads, so it needs approval.
2. GPU texture-upload and draw-call gaps (blob or zero-copy resources).
3. fsync-heavy storage: an ext4 data volume option, or lower virtio latency.
4. Battery and Low Power Mode measurements (the machine was on AC so far).
5. Native track: an m1n1 read-only session needs separate authorization.

---

## 2026-10-12 · Storage, clipboard, host agent, idle refresh

### Implemented

* **Host agent** (`tools/ilinux-host-agent`, launcher-managed) and guest
  `ilinux-host-bridge`: Mac battery, a clock step right after host sleep
  (tested: a 30 s lag was fixed within one cycle), and time zone. No polling
  in the guest.
* **Storage:**
  * virtio-blk runs on a dedicated iothread with 4 queues, doubling
    random-I/O scaling;
  * QEMU patch 0005 makes `cache.direct` use F_NOCACHE on macOS (it was
    O_DSYNC);
  * `storbench syncwrite` added (F-033, D-023).
* **Clipboard sharing with macOS:** QEMU built with spice-protocol
  (`qemu-vdagent`), plus a stdlib-only guest vdagent clipboard agent for
  Wayland (wl-clipboard) and a udev `uaccess` rule. Tested both directions
  (D-022).
* **QEMU patch 0006, adaptive display refresh:** a hidden window caused a
  redraw-request storm (1 guest frame vs 1832 requests in 20 s).
* **Housekeeping:** deleted the obsolete ext4 `root.img` (13 GB).

### Measured

* **Storage vs native:** warm 4K QD1 reads at 101%; 32 threads at 42% (was
  20%); cold sequential reads with F_NOCACHE at 100%; write+fsync at 22%
  (btrfs dependent-I/O chain).
* **Microphone:** QEMU's CoreAudio backend has no capture
  (`max_voices_in = 0`). A capture voice needs writing, ideally with an app
  bundle so macOS attributes the microphone prompt to it.

---

## 2026-10-12 · Efficiency pass: CPU heterogeneity, App Nap, GPU fences, power

### Discovered

* **App Nap (F-027):** a hidden QEMU window naps the whole VM, putting every
  vCPU at PRI 4 on M cores, about 4× slower.
* **macOS QoS on M5 Max (F-028):** only `background` QoS reaches the M cores.
  `utility` behaves like `default`.
* **VirGL fences (F-030):** on macOS they were polled every 1 ms, costing
  about 1.5 ms per guest GL sync. QEMU enabled the sync thread only for EGL,
  and virglrenderer needs eventfd.
* **Idle power (F-032):** an idle Omarchy VM costs only +0.09 W SoC. The
  earlier +0.38 W reading included post-login churn and a lingering test
  user manager.

### Implemented

* **Workspace QEMU and virglrenderer patches:**
  * `bg-vcpus` heterogeneous vCPUs: host QoS plus guest
    `capacity-dmips-mhz` (D-019);
  * `app-nap=on|off|auto` (D-020);
  * event-driven VirGL fences with a pipe-backed eventfd (D-021).
* **Launcher:** `--hetero`, `APP_NAP` (default `auto`), and the guest time
  zone follows the Mac (`ilinux.tz=`).
* **`omarchy-qos`:** `RESERVE_EFFICIENT_CPUS=auto` keeps system and
  foreground slices off much-slower efficient CPUs, plus a system unit
  `omarchy-qos-system.service`.
* **Tools:**
  * `benchmarks/src/glbench.c`: the same GL 4.1 code on CGL and EGL;
  * `benchmarks/vm/{vm_power_states,hetero_placement}.sh`;
  * `tools/power_{summary,table}.py`;
  * `vmconsole.py`: robust completion marker.

### Measured (`reports/vm-vs-macos-parity.md`)

* **GPU vs macOS GL:**

  | Test | Parity |
  |---|---|
  | ALU | 99.7% |
  | Blended fill | 74% (was 17%) |
  | Readback | 61% (was 23%) |
  | Draw calls | 50% |
  | Texture upload | 28% |

* **CPU:** foreground single-thread is 99% of native. The background tier
  gives 1.84× (1 thread) and 2.25× (6 threads) more work per joule than
  foreground.
* **Idle:** +0.09 W (`app-nap=auto`) and +0.14 W (`off`) over host-only
  1.713 W.

### Next

* Texture-upload and draw-call gaps: blob or zero-copy resources, and Venus
  (Vulkan) via MoltenVK or KosmicKrisp.
* Battery-mode measurements (on battery and in Low Power Mode).
* Package the kernel for pacman.

---

## 2026-10-12 · Session 2: Omarchy 4 desktop in a GPU-accelerated VM

### Implemented

* **Guest system:**
  * Omarchy 4.0.4 (aarch64 edge) on btrfs (`@`, `@home`, `@log`, `@pkg`,
    zstd) with snapper (D-013).
  * Kernel v2: 7.1.6 with 16K pages and uclamp, the full ALARM module set,
    essentials built in (D-014).
  * Network: Quad9 with DoT (D-015).
* **GPU compute from Linux:** guest llama.cpp → ggml RPC → vsock (vzrun
  `--vsock-forward`) → host Metal `ggml-rpc-server`.
* **GPU desktop:** QEMU 11.1.1 (HVF) + VirGL 1.3.0 + upstream libepoxy, all
  built from pinned sources in the workspace (D-012). The launcher is
  `virtualization/qemu/run-omarchy-gpu.sh`.
* **Fixes we wrote:**
  * libepoxy: a missing `libEGL` no longer aborts. Every GL lookup probed
    EGL first.
  * QEMU Cocoa patch: stable Retina window size, window size sent to the
    guest at launch, app name from `-name`.
  * Omarchy shell under Qt 6.12: the `QtQuick/Color` type shadowed the
    shell's `Color` singleton, leaving a black, empty bar. Fixed with a
    self-disabling pin plus a pacman hook (D-017).
* **Mac integration:**
  * the battery bridge feeds IOKit data over virtio-serial into
    `test_power`, so UPower and the bar show the Mac battery;
  * SDDM autologin (D-016);
  * opt-in full-screen Space and full keyboard grab (D-018).

### Tested / measured

* **ggml RPC:** Q4_0 8B prefill 2737 t/s (**89%** of native Metal),
  generation 85.1 t/s (**81%**). Socat `nodelay` was essential: with delayed
  ACK, generation was 23%.
* **Guest renderer:** `virgl (Apple M5 Max)`, OpenGL 4.1 core, GLES 3.0
  (Mesa 26.2.4).
* **Desktop:** Hyprland 0.56.2 at 2592×1458 at 120 Hz, scale 2. The bar,
  notifications and lock screen are themed (screenshots taken in the guest
  with `grim`).
* **Idle desktop cost:** QEMU used ≈ 3.4% of one host core with the desktop
  idle. Omarchy's idle chain works: screensaver at 150 s, lock at 300 s, then
  DPMS off, after which the guest stops rendering.
* **Native series (job 018):** `git am` on asahi 77cb8f24 is clean. `sart.o`
  and nvme `apple.o` build with 0 errors and 0 warnings, and
  `t6050-j716c.dtb` builds.

### Still unsupported / next

* No Vulkan in the guest (Venus/MoltenVK not built). No microphone capture
  with the CoreAudio backend.
* GPU benchmark (guest VirGL vs native GL) and host power: idle desktop vs
  macOS idle.
* Package the custom kernel for pacman. Guest timezone should follow the
  Mac's.

---

## 2026-10-11 · Native-enablement research pass (m1n1, Asahi Linux, PMGR/DVFS, drafts)

### Discovered

* **m1n1 (`57a9339`) on t6050:** single core plus NVMe read. SMP is still
  broken: cores power on but never run m1n1 code (PR #610). The cause is
  Unknown; ranked hypotheses are in `kernel/native-enablement/plan.md` §1.2.
* **M5 MPIDR:** M cores are 0x4XXYY and P cores 0x1XXYY (F-019). The old
  draft DT would have had every CPU node pruned by m1n1. Fixed.
* **Our ADT, decoded:**
  * the PMGR table: 661 records, 6 blocks, a second die at +0x21_0000_0000
    (F-021, F-024);
  * CPU DVFS: M 15 states up to 4.380 GHz, P 20 states up to 4.608 GHz
    (F-022);
  * SART `sart-version = 4`, the NVMe M4+ layout, and per-CPU
    `function-enable_core` (F-020, F-023).
* **AsahiLinux/linux:** `asahi` already has the NVMe firmware-ABI series.
  No branch has SARTv4 or the M4+ NVMe register split.
* **Idle:** m1n1 forces `idle=nop arm64.nowfxt` on M4+ (F-026).

### Implemented

* **`adt_extract.py`:** wider whitelist, full binary tables, and a
  content-based leak check (`--check-only`). Re-extracted: 0 problems.
* **The DT generator:** now covers PMGR power domains (188), MPIDR-correct
  CPUs, OPP and energy-model data, cpufreq, disabled DART/SART/NVMe drafts.
  `validate.sh` fixed and strict: **0 dtc warnings**.
* **Local patch series `kernel/patches/t6050/0001–0007`:** SARTv4, the NVMe
  M4+ split, bindings, and the DT. Untested; compile test pending. Not for
  upstream.
* **`kernel/native-enablement/plan.md`:** a dependency-ordered plan for items
  (a)–(j).

### Next

1. Compile-test the series and run `dtbs_check` in the VM, once it is free.
2. A native m1n1 read-only diagnostics session. This needs user
   authorization and a deployment plan.
3. Draft the SPMI gen-4 driver and a dockchannel-uart console driver.

---

## 2026-10-11 · Session 1: foundations, baselines, VM track, energy

### Discovered

* **Exact hardware:** MacBook Pro Mac17,6 (J716c), **Apple M5 Max = t6050**
  (`chip-id` 0x6050, SoC generation tag "H17", CPU family SOTRA).
  * 6 P ("Super", 16 MiB L2) + 12 M ("Performance", 2 × 8 MiB L2) cores;
    the ADT cluster type is `M`.
  * 40-core G17X GPU, H16-generation ANE (exclave-mediated), 128 GiB,
    2 TB ANS3 SSD.
* **ISA:** SME/SME2/SME2p1 (SVL 512) without non-streaming SVE. MTE present.
* **Linux status for t6050:**
  * No DT and no kernel bring-up. m1n1 has initial T6050 support with no SMP.
    GPU (G17), ANE, ANS3 NVMe, the N1 Wi-Fi chip, DCP and others have no
    Linux drivers.
  * **Asahi forbids generative-AI contributions** (2026-09-08), so this
    project's outputs stay local (D-007).
* **macOS QoS:** background work runs on M cores at ≈ 25% of P-core
  throughput, at **≈ 4× better energy per FLOP**.
* **SME:** one engine per cluster. The P-cluster engine gives 2.17 TFLOP/s
  FP32 (rail `PCPM` ≈ 9.8 W); the chip saturates at 3.23 TFLOP/s.
* **GPU:** FP16 GEMM ≈ 64 TFLOP/s (matrix units) vs 17.6 scalar. Core ML's
  planner prefers the GPU over the ANE on M5 Max.
* **ANE:** 14.0 TFLOP/s FP16 on a 1×1-conv stack at ≈ 3.6 W. Proven by the
  ANE energy counter and MLComputePlan.
* **Microarchitecture:** M5 P-core FMA throughput drops ≈ 11% when all FMLAs
  read the same two source registers (F-016). This explained a fake "112%
  VM parity".
* **Omarchy 4 already supports aarch64 upstream** (edge). Real `pacman` in
  our VM resolves the full default set: 842 packages, 0 unresolved.
* **VM facts:** SME2 is passed through. MIDR is masked. Wakeups cost 21–52 µs
  vs 3.8 µs native. Virtio storage reaches 3–30% of native.

### Implemented

* Benchmarks:
  * `cpubench` (freq, fma, **fma_asm**, intmix, sort, sgemm, SME f32/bf16/i8,
    pingpong, syscall);
  * `membench` (STREAM, latency incl. DIT/DMP-off, faults);
  * `storbench`;
  * Metal `gpubench`;
  * **`powermon`** (no-root IOReport energy and DVFS sampler).
* Model generators: `tools/synth_gguf.py` and `tools/synth_mlx.py`
  (synthetic models with identical shapes for llama.cpp and MLX).
* Analysis helpers: `tools/compare_results.py` (parity tables);
  `hardware/scripts/{adt_extract,ioreg_driver_map,kext_personalities}.py`.
* **VM track:**
  * `virtualization/vzrun` (Virtualization.framework runner: direct kernel or
    EFI boot, virtiofs, NAT, nested, NVMe and disk-mode options);
  * GPG-verified Arch Linux ARM image build;
  * the scripted job runner.
* **omarchy-qos** (QoS tiers via systemd slices, cpuset, uclamp), VM-tested
  and with one bug fixed.
* **Draft t6050 DT** (CPUs, AIC3, timer, WDT, 3 × pinctrl, 9 × I2C, UART),
  compile-checked with a workspace-built `dtc` 1.8.1. Local only.
* REA 6.4.0, project-local (`tools/rea`, `.mcp.json` and deny-list settings in
  `~/Documents/iLinux`). MLX, mlx-lm and coremltools in `tools/venv`.

### Tested and measured (highlights; see `reports/performance-parity.md`)

| What | Result |
|---|---|
| macOS CPU, 1 P core / 18 cores (asm FMA) | 140.8 GFLOP/s / 1.89 TFLOP/s |
| macOS SME f32, 1 thread / chip | 2.17 / 3.23 TFLOP/s |
| macOS STREAM, 18 threads (median) | ≈ 369 GB/s copy |
| macOS GPU FP16 GEMM / copy bandwidth | 64 TFLOP/s / 537 GB/s |
| macOS SSD seq read / write | 11.0 (13.3 at 4 threads) / 11.2 GB/s |
| llama.cpp Metal 8B Q4_0 | pp512 3090 t/s, tg128 105 t/s, ≈ 0.56 J/token |
| MLX 8B 4-bit / Gemma-3-12B bf16 | tg 100.8 / 21.7 t/s |
| ANE (Core ML conv stack) | 14.0 TFLOP/s at ≈ 3.6 W |
| **Linux VM vs macOS** (identical code and flags) | CPU compute 97–101%, SME 97–100%, STREAM 93–100%, DRAM latency 72–84%, syscalls 77%, wakeups 7%, storage 3–57% |
| omarchy-qos in VM | 5/5 pass; uclamp skipped (no `CONFIG_UCLAMP_TASK_GROUP` in the ALARM kernel) |

### Still unsupported or blocked

* Native Linux on t6050 (B-001), GPU (B-002), ANE (B-003), NVMe (B-004),
  Wi-Fi (B-012).
* GPU acceleration inside VMs needs host installs such as krunkit (new
  approval).
* No Linux-side energy counters yet.
* Strict BLAS-free llama.cpp prefill comparison on macOS needs `cmake`
  (not installed).

### Next

1. ✅ (2026-10-11) VM llama.cpp CPU comparison (F-017) and VZ storage-mode
   matrix (F-018). Follow-up: `fsync` default plus pre-allocation in `vzrun`.
2. Build a guest kernel config with `CONFIG_UCLAMP_TASK_GROUP` (and possibly
   16K pages) to test omarchy-qos clamps and the VM memory overheads.
3. Omarchy VM install: keyring, `omarchy-arm64-vm` integration package,
   Hyprland on llvmpipe smoke test.
4. Propose GPU-in-VM experiments (krunkit/Venus; llama.cpp API remoting) to
   the user for approval.
5. Decode the PMGR `devices`/`ps-regs` tables to extend the DT draft with
   power domains (local research).
