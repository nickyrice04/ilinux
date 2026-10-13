# Isolated Mesa VA-API driver for the Omarchy VM

Built and installed in the existing VM on 2026-10-12 as
`mesa-virgl-video-ilinux 26.2.4-1`. It adds two Linux-side changes:

* `0001`: optional NV12-only surface negotiation for 8-bit H.264 decode.
  VideoToolbox already produces NV12, so this avoids its per-frame planar
  conversion. Set `VIRGL_VIDEO_DECODE_NV12=1` on this host. The option defaults
  off, and does not alter other codecs, encoding, or image-format queries.
* `0002`: lossless CPU rearrangement between NV12, I420 and YV12 when
  downloading progressive, even-sized images with even crop coordinates.
  This bypasses the failing GPU conversion path and uses Mesa's existing
  copy helpers. Other conversions and scaling keep their existing path.

The package owns `/usr/lib/ilinux-va/virtio_gpu_drv_video.so` and the
`ilinux-video` wrapper. It does not replace the installed Mesa, OpenGL, or
Vulkan packages. Use it inside this VM:

```sh
ilinux-video mpv video.mp4
ilinux-video ffmpeg -hwaccel vaapi -hwaccel_device /dev/dri/renderD128 \
  -hwaccel_output_format vaapi -i video.mp4 \
  -vf hwdownload,format=nv12,format=yuv420p -f framemd5 -
```

Regular applications keep their current driver selection. Opting in through
the wrapper requires no desktop restart. Remove the guest package with
`pacman -R mesa-virgl-video-ilinux` to remove the opt-in path.

**Session default (D-032).** The VM also makes this driver the default for
desktop-launched apps through
`omarchy-arm64/configuration/vm-integration/etc/environment.d/70-ilinux-vm-video.conf`,
so plain `mpv`/FFmpeg use it without the wrapper. The wrapper remains for
explicit, per-process use (e.g. from a bare `sudo -u`, which does not import
`environment.d`).

## Rebuild

From the repository root, stage the source recipe and patch checksums:

```sh
python3 -I omarchy-arm64/packages/mesa-virgl-video/prepare-package.py \
  build/mesa-virgl-video-package
```

Copy that directory into Linux, install the dependencies listed in the
generated PKGBUILD, and run `makepkg` as a regular user there. Install the
result using `pacman -U`. Do not execute the Mesa build on macOS.

`PKGBUILD.in` is a template; the staging script replaces the checksum tokens.
The Mesa archive SHA-256 matches the official
[26.2.4 release notes](https://docs.mesa3d.org/relnotes/26.2.4.html).
The package uses GCC 16.1.1 and Meson release mode, with Arch's later
`-march=armv8-a -O2` and hardening flags. It enables Gallium virgl and
H.264 decode, without LLVM, EGL, GLX, GBM or Vulkan. Build commands and
dependency versions are retained in the package build log and `.BUILDINFO`.

## Validation and limitations

See [the experiment record](../../../reports/video-download-and-nv12-2026-10-12.md).
The installed package passed 18 texture/image round trips and all eight
180-frame hardware-download comparisons against software decode, including
1080p and 4K, plus 240 frames of Baseline/Main-profile comparisons. mpv also
completed a 120-frame hardware-decode/EGL smoke test.

Paced 4K60 decode used 41.3% less QEMU CPU time with NV12 selected, over two
ABBA blocks. This is neither a display benchmark nor a native Linux result.
Whole-SoC energy was noisy and is not used to claim a power improvement.

Odd crop coordinates, odd sizes, scaling, interlacing, higher bit depths,
other codecs, other hosts and other GPUs are not validated by this series.
The pre-existing shader-based conversion problem outside the new lossless
path is still open. Native M5 AVD support and asynchronous decode fencing
remain separate work.
