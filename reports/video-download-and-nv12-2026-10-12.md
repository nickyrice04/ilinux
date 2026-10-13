# Mesa video downloads and NV12 decode: implementation and evidence

Two original Linux-side changes are built, packaged and installed in the
existing Omarchy ARM64 VM. They fix the tested pixel-download conversions
and remove an unnecessary host conversion during H.264 decode. macOS system
files, settings, boot state and personal data were not modified.

## Problem selection

The [subsystem audit](bottleneck-priorities-2026-10-12.md) ranks native
boot/SMP, G17 GPU/DCP, and native idle/DVFS as the largest barriers. Their
runtime validation requires a separately authorized native boot session.
The current VM's video path offered an immediate experiment with an
independent pixel oracle and a source-level implementation.

Initial questions from F-042/F-045 were: are downloaded frames stale, does
planar negotiation add a conversion, and can original Linux code fix both?

## Source and binary investigation

**Confirmed:** REA 6.4.0 inspected the workspace host renderer and the
accessible AppleVideoDecoder bundle. The latter has x86_64 and arm64e
slices. Its arm64e slice was copied into the ignored
`reverse-engineering/permitted-artifacts/` directory and inspected separately.
[REA evidence summary](../reverse-engineering/findings/video-coherency-2026-10-12/rea-summary.json)
records the digest, Evidence ID and selected imports; full evidence and
proprietary artifacts stay local and ignored.

Pixel-buffer negotiation, IOSurface access, surface transformation and frame
emission are visible import boundaries. Supplemental Apple LLVM 21 ARM64
disassembly at `0xd3d98..0xd3f30`, the H.264 factory entry, shows calls to
`VTVideoDecoderGetClassID`, `CMDerivedObjectCreate`, and
`CMBaseObjectGetDerivedStorage`. This is an object-factory interface, not
evidence of an AVD firmware command protocol. Static imports do not prove
that any particular conversion executes, nor which pixel format is fastest.

**Limit:** REA's deep-analysis request returned `provider_unavailable`:
Ghidra/JDK, Hopper and IDA are not configured. The
[failed request](../reverse-engineering/findings/video-coherency-2026-10-12/rea-instructions-attempt.json)
is retained. There was no successful REA decompilation. The ARM64 instructions
above came from LLVM, guided by REA's artifact identity, rather than from a
REA backend. No proprietary pseudocode was copied into the patches.

The actionable behavior came from public Mesa 26.2.4 source and experiments:
`virgl_screen.c`, `virgl_video.c`, `frontends/va/{surface,image,postproc}.c`,
`vl_compositor*.c` and `util/u_video.h`, compared with the existing workspace
VideoToolbox renderer. The release tarball matched the hash in
[Mesa's release notes](https://docs.mesa3d.org/relnotes/26.2.4.html).

## Corrections to previous findings

**Measured:** the unmodified guest successfully downloads the decoder's
planar output as planar YUV. Asking for NV12 instead returns zero-filled
frames. With NV12 decode selected, the reverse conversion to planar output
also fails. A format-only experimental build downloads native NV12 correctly
without changing dirty flags. Therefore F-045's broad claim that every CPU
download is stale, and its proposed dirty-flag fix as the root cause, were
too strong for the current stack.

**Confirmed in source:** `vlVaGetImage` sends different-format downloads
through a temporary surface and `vlVaPostProc`; same-format downloads map
the original planes. VA surface allocation also clears render targets,
which dirties their resources. Adding explicit decode-plane invalidation
did not repair the cross-format failure. That experimental patch was removed
from the final series. Exact failure inside the GPU shader conversion path
remains unresolved; it is not presented as a fully reconstructed root cause.

The raw protocol still has `prefered_format`, but Mesa 26.2.4 no longer
provides the old `PIPE_VIDEO_CAP_PREFERED_FORMAT` query. An attempted use
failed compilation. The final code does not depend on that stale enum or
interpret the raw protocol preference as an exhaustive support list.

## Engineering decisions

1. **Avoid the conversion at decode.** An opt-in virgl option limits the
   supported surfaces for Baseline/Constrained Baseline/Main/High H.264
   decoding to NV12. All other profiles, entrypoints and image queries keep
   existing behavior. FFmpeg then chooses NV12; the existing host renderer
   already has a two-plane IOSurface copy path.
2. **Make CPU downloads lossless.** For progressive 8-bit 4:2:0 with even
   dimensions/crops and no scaling, map the original planes and rearrange
   them into the requested NV12/I420/YV12 layout. Existing Mesa helpers
   interleave/deinterleave chroma; planar U/V order is handled explicitly.
   This avoids the failing shader path, a temporary surface and another GPU
   pass. No changes to macOS or proprietary decoder implementation are needed.
3. **Package independently.** `mesa-virgl-video-ilinux` installs a separate
   VA-API module and per-process wrapper. It is installed in the VM; system
   Mesa/GL/Vulkan stay package-owned and selectable normally.

Source, recipe, use and rollback:
[mesa-virgl-video](../omarchy-arm64/packages/mesa-virgl-video/README.md).

## Reproducible validation

Host: Apple M5 Max, 18 CPU cores, 40 GPU cores, 128 GB; macOS 26.6.2 / 25G83.
Guest: Linux 7.1.6-vzrun2, Mesa 26.2.4, FFmpeg 9.0.2-2, libva 2.24.1-1.
Compiler: GCC 16.1.1. The experimental release build uses `-O3`; the packaged
build adds Arch's later `-march=armv8-a -O2` and hardening flags, so its
effective optimization level is `-O2`. Selected full compiler commands and
the package `.BUILDINFO` are saved with the results. The pinned PKGBUILD
records Meson options. The existing QEMU/virglrenderer path was unchanged.

* **Build/package:** clean Mesa release build and `makepkg` exit 0; installed
  package passes `pacman -Qkk` (10 files, none altered). Source archive and
  local patches are SHA-256 checked. The modified files compile without
  warnings. The full package build emits GCC array-bounds warnings in
  bundled BLAKE3 and a deprecated Android-display constant warning; these
  are outside the patches and remain unaudited. No build errors occurred.
* **Image test:** `benchmarks/linux/va_image_roundtrip.c` uploads synthetic
  Y/U/V patterns, reads all 3×3 format pairs, and tests both 66×38 images and
  a 32×18 crop at (2,4). Stock: 37,008 mismatched bytes. Installed package:
  **18/18 cases, zero mismatched bytes**. This tests the actual VA driver,
  GPU texture transfers, pitches, crop offsets and U/V ordering.
* **Video correctness:** `benchmarks/linux/video_decode_validate.py`
  compares frame timestamps, byte counts and every frame MD5 with independent
  FFmpeg software decode. 180 frames each of the existing synthetic 1080p
  and 4K H.264 clips, four hardware paths per clip: default/NV12 decode ×
  planar/NV12 download. **1,440/1,440 hardware frames match** in the final
  build. The installed package repeats the same matrix and passes another
  **240/240 frames** across Constrained Baseline and Main clips (30 frames
  each, the same four hardware paths).
* **Desktop integration:** `ilinux-video mpv`, VA-API hardware decode,
  OpenGL output and `profile=fast`, completes 120 frames of the 4K clip with
  exit 0. This is a functional smoke test, not a visual-quality, pacing or
  display-power measurement.

Raw checks and logs are in
[`benchmarks/results/vm-video-coherency-2026-10-12/`](../benchmarks/results/vm-video-coherency-2026-10-12/).
Clip digests, exact commands and frame counts are in the validation JSON.
The initial pre-conversion-fix matrix includes the experimental dirty patch;
its failures show that patch did not fix format conversion. Stock image
round-trip evidence is from the unmodified release build.

Review also hardened the benchmark tools: every executed validation case
now affects the default exit status (a stock conversion failure returns 1;
the installed profile matrix returns 0). The decode benchmark now adds a
guest wall-clock timeout and cleanup restricted to its recorded process.
An intentionally sleeping test process verifies cleanup and timeout status.
The earlier successful ABBA measurements preceded that guard; all eight
decoders completed normally. `decode-ab/` contains only the environment
snapshot from an initial shell-launch error and is not used for measurements.

## Decode cost

`benchmarks/vm/video_decode_ab.py` ran **two ABBA blocks per build**, four
observations per setting, on the same running VM. Each comparison toggles
NV12 within one driver binary. Each run decodes the
same 4K60 H.264 clip with FFmpeg `-re`, keeps frames on the GPU, displays
nothing, warms up for 4 seconds, measures 8 seconds, and exits after 960
frames. Runs are bounded and only their own processes are used. Host
`caffeinate -i` prevents idle sleep. AC state and energy-mode settings are
recorded. CPU use is QEMU process CPU seconds divided by wall seconds.

| Build / setting | Mean QEMU cores | Range | Completed frames/run |
|---|---:|---:|---:|
| Installed package, planar | 0.296200 | 0.2887–0.3148 | 960 |
| Installed package, NV12 | 0.173850 | 0.1518–0.1872 | 960 |
| Earlier experimental build, planar | 0.289425 | 0.2873–0.2926 | 960 |
| Earlier experimental build, NV12 | 0.179375 | 0.1678–0.1880 | 960 |

**Installed package: 41.3% less QEMU CPU time**, or 0.12235 core at this
workload. The earlier experimental build measured 38.0% less. These are
fixed-rate CPU-cost comparisons, not faster playback: both cases sustain
the paced stream. The final download-only extension followed the earlier
benchmark; the installed-package repeat includes the final patches and
distribution compiler flags. IOReport power varied with host activity, so
no whole-SoC power saving or macOS-equivalent efficiency is claimed.

## Remaining work

* The fast download path deliberately excludes odd crops/sizes, scaling,
  interlacing, higher bit depth and other layouts. Their shader path still
  needs a separate investigation; these tests cannot validate it.
* No general decoder output-fence implementation was added. The current
  host decoder remains synchronous in command order; asynchronous decoding
  requires proper completion and surface-lifetime tracking first.
* Repeat on-screen mpv ABBA measurements under controlled host activity;
  investigate F-050's intermittent display stall independently.
* Add HEVC/VP9/encode only with codec-specific descriptor and correctness
  tests. The package currently enables only H.264 decode.
* Native AVD/G17/ANE, t6050 boot/SMP, idle/DVFS and peripherals remain
  hardware-enablement work. These VM results establish none of their native
  compatibility. A native boot session still needs explicit authorization.
