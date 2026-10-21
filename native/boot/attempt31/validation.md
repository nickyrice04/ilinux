# Attempt31 offline validation — 2026-10-21

Native/live **NOT RUN**. M1 intake pending. This record covers an original,
opt-in compositor optimization and a new matched RAM-boot pair. No native boot,
macOS filesystem, security, volume, default entry, firmware, frequency or
secondary-core operation occurred during preparation.

## Evidence and engineering decision

M1's attempt30 report (`45952cc`) measured about 97% compositor CPU during
controlled drawing, approximately 256 ms tiny-damage callbacks, 515 ms full
callbacks and 408 ms IPC medians. CPU0's dependent-ADD estimate remained near
2.65 GHz; it is an M core, not an established underclocked performance core.
Anonymous executable samples remain unattributed. The report supports reducing
expensive drawing and measuring event-loop delays; it does not justify blind
clock writes or identify every cause of application delay.

The existing REA/Ghidra CPU-policy evidence distinguishes scheduling feedback,
placement and performance requests. Its rejected pseudocode remains excluded.
No new Apple decompilation was performed for this change: the exact Linux
render path is available as public source. The detailed causal plan and the
SMP/GPU/network/storage priorities are in `kernel/experiments/desktop31/PLAN.md`.
The original helper replaces only an eligible final identity shader pass with
a framebuffer copy, retaining normal drawing elsewhere. No proprietary code
or algorithm was copied.

## Source, build and assets

Hyprland upstream `efb50993780079460b0cbed1363e2166a2de1d9f`, archive SHA-256
`5b05ce7ba5296fa46e666852bf108ab5af121bf577f8043787e2d2c252d8f109`.
All 1,028 regular source files were compared against the pinned archive.
`apply.py` additionally checks both source files it edits before patching.
Dependencies: udis86 `5336633af70f3917760a6d441ff02d93477b0c86`
(archive `3e9f58ca0cb1c79fcd05b84a7605dc3010ff5c0ca83f569e449a46d2d1da1af6`),
hyprland-protocols `bd153e76f751f150a09328dbdeb5e4fab9d23622`
(archive `9f4187100799155b4002ed3c7a90c3ebfee4311dccc0164816a5f600fb66f2a9`),
and glaze v7.2.0 at `b518eec7a22e56ffa238b072c07f47efa7cea97f`.

Job055 used the existing Arch ARM64 VM, GCC16.1.1, CMake4.4.4, Ninja,
Release/O3, `NO_HYPRPM=ON`, eight build jobs, then stripped the executable.
Build VM: Linux7.1.6-vzrun2, 12 vCPUs, 24 GiB; Mesa26.2.4, LLVM23.1.1,
Wayland1.26.0, hyprutils0.14.2, Aquamarine0.15.1-1.1,
hyprwayland-scanner0.4.6. Exact package/tool output is in `vm-observation.json`.
Runtime tests use the retained Omarchy root's libraries, including its
Aquamarine0.15.1-1.3. This catches ABI/startup problems independently of the
build VM's package set. Build timestamps mean rebuilding is not promised to
produce identical executable bytes; intake always uses the reviewed digest.

Candidate executable SHA-256:
`76457da85a7a073c69cbfabcb9c9c9cb66c1a0ed4f3070fc628704032134c131`.
All six shipped assets are in `assets.json`. Existing frameprobe/samplecpu and
CPU28 assets are retained. The old package database/build-info is unchanged;
the executable digest identifies this custom build. The A/B reference is the
original drawing branch in that same executable, not a different package.

## Pixel checks and compositor crossover

Original GLES3 test: **64 complete output comparisons PASS**, all zero differing
bytes. Matrix: 67x49 and 3456x2160, normal/flipped Y, RGBA/RGB destinations, eight
full/partial/empty/clipped/edge damage cases. Outside-damage pixels are checked.
Optimized and ASan/UBSan builds pass; leak detection is disabled for the external
Mesa process allocations, so this is not a leak-freedom claim. Isolated full-
screen shader samples were about 50 ms versus 0.46 ms for the copy. That isolated
operation ratio is neither an end-to-end desktop ratio nor a native prediction.

Actual candidate compositor: exact retained Omarchy userspace, uid1000,
software GL/LP_NUM_THREADS=0, compositor and clients pinned to vCPU0. A headless
3456x2160 output avoids depending on VZ virtual-DRM presentation. Startup settles
25 seconds; VM-only animations are off. Native configuration retains animations.
Four 20-callback controls use off/on/on/off order, four warm-ups followed by
eight tiny and eight full-damage callbacks per phase. All samples/outliers are
in `vm-observation.json`, including software sampling and IPC.

| Path / run | Full-damage median | Compositor CPU seconds / phase |
|---|---:|---:|
| Original / 1 |104.345 ms|1.32|
| Candidate / 1 |78.379 ms|1.19|
| Candidate / 2 |78.288 ms|0.99|
| Original / 2 |104.193 ms|1.30|

About **25% lower full-damage callback medians in this VM workload**. Small-
damage medians remain around 16.7 ms. The first candidate phase includes the
one-time pixel verification cost. Three framebuffer-pair comparisons were
bitwise equal with GLerror0; 42 copies were observed. FP16/color-conversion,
1728x1080 and rotated1080x1728 controls all completed on the original branch,
with eligibility0 and unchanged copy counts. These are offscreen results;
physical display presentation and the native256 ms tiny-damage floor remain
unresolved. No matched macOS performance or energy measurement was performed.

The **actual packed root** was independently unpacked and exercised again.
It passed the same seven workloads, automated path/parity/fallback assertions,
and the shipping native collector refused the generic VM before its start
marker. Real systemd `ExecStopPost` reset the live compositor from mode1 to0
and returned the expected receipt. Timings from this packing check are retained
but not used as a benchmark: host archive verification overlapped that run.

## Controller, cleanup and intake checks

* Seven collector methods: positive path evidence, parity/error refusal,
  invalid toggles, normal crossover/human/final reset, timeout cleanup,
  foreign hardware before mutation and consumed-attempt refusal.
* Fourteen M1 helper methods: host-key attribution/refusals, fixed deadline,
  single arm, no SSH on insufficient time, exact supervisor command and
  completion followed by the independent reset receipt. The parser was also
  checked against stdout from the actual VM reset service.
* 76 CPU-profile/DT/payload/refusal methods and 45 legacy RAM-root methods pass
  in the VM, using the actual boot042 package and new stage-one image. An added
  mixed-pair refusal case brings the final host CPU-profile suite to 77 methods;
  all 143 final host collector/helper/profile/legacy methods pass.
* A real systemd RuntimeMaxSec timeout invokes ExecStopPost independently of
  its terminated main process. Shipping reset also passes against the running
  candidate. The compositor itself falls back on parity/GL errors.
* Read-only host intake hashes both entire images, checks the embedded pairing,
  all six embedded assets, byte-identical collector/baseline/reset source,
  installed executable, and unchanged CPU28 asset manifest. PASS.
* Offline `desktop-copy` launcher and root sender PASS; USB unopened. The new
  confirmation token cannot use an old attempt's token; unchanged kernel/DT,
  one core and 300s launch bound. No real observation window armed.

The fixed native return window is 600s from the root switch. The collector has
an internal 280s alarm, a 300s service limit and an independent 40s stop/reset
bound. M1 requires 380s remaining before starting it. It collects one crossover,
one 45s human phase, resets the option to0 and stops. An unsuccessful reset
requires Macintosh HD return, not another experiment.

## Images and full-pair boot

The new root is the exact attempt28 root with `/usr/bin/Hyprland` replaced and
`/usr/local/lib/ilinux-desktop31/` added. Existing login, configuration, keyboard,
USB transport and modules are preserved; no package upgrade. Stage one changes
only its root pairing pin. Image build guest/wrapper exits0, `IMAGE-BUILD-PASS`.
No SSH host private key or pacman private keyring is embedded; existing
operator public key only. Artifacts remain private in ignored workspace paths.

| Image | Bytes | SHA-256 |
|---|---:|---|
| Stage one |60,669,159|`6ffb37b98be5b207bf6922993c9c77dd145a7b7109dfafd323e8bb7e549d1752`|
| Omarchy root |2,472,878,772|`e600aeb36c11f2ea1c8bd354e9ded8be69e3c2c4314daffc7383c49494f466c8`|

**Full-pair VM boot PASS**, wrapper exit0, judge `run-qemu.sh: PASS`. Transfer
312.0s at7.9MB/s; hash verified, unpack9.6s, one root switch. Omarchy desktop
ready at342.81 kernel seconds; second link/SSH/sudo checked at369.31s; final
PASS at369.39s, total wall373.0s. The captured framebuffer was visually inspected:
wallpaper, bar and onboarding notifications render. Keyboard service is enabled
and skips absent VM MTP hardware; repeat_delay1000 and CPU28 asset/native-refusal
checks pass without module load. The two expected VM failed units remain
`omarchy-provision-hardware.service` and `ufw.service`, matching the base image.

It uses job049, one vCPU/32 GiB/HVF, test kernel
`a1ecd7f899097dc70870678281e3b99b69120412e5bad7bad01e55b43b1a6bbc`, simulated
USB and a read-only root-image disk. Its 3456x2234 10-bit framebuffer deliberately
fails the copy eligibility condition. The unchanged receiver's negative-transfer
suite passed previously; this exact-pair run uses NEGATIVES=0. Neither this
kernel nor simulated USB establishes native controller/presentation behavior.

## Failed iterations and remaining limits

Retained privately: missing source submodules/scanner; protected render-mode
access fixed by passing it from its existing caller; obsolete IPC keyword
replaced by the current Lua API; startup-notification-contaminated timings
excluded; internal logging unavailable, replaced by numeric RAM-only evidence;
VM-only resize/configure race fixed with a short settle; an obsolete desktop-
service assumption rejected before use, leading to the new image pair; missing
harness input path corrected before VM launch. The independent reset's stdout
initially conflicted with M1's JSON-only parser; the final helper explicitly
requires its receipt and has positive/refusal tests. No failed native trial
was hidden by these offline corrections.

The earlier interpretation of Aquamarine auxiliary-renderer warnings as display
commit failures was too strong. Pinned public source shows those warnings can
follow successful primary commits; see `../attempt30/vm-evidence-addendum.md`.
Callbacks still are not photon timestamps. Do not conflate these warnings,
software-rendering speed and physical presentation.

M1 follows `tools/m1n1-client/attempt31-instructions.md`, publishes offline
readiness, and waits for human start. Both new images must be privately
transferred together. Native visual correctness, menu/input/app responsiveness,
stability, thermal/energy behavior and macOS parity remain **NOT RUN**.
