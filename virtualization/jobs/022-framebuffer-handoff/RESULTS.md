# Job 022 results — 2026-10-13 local / 2026-10-14 UTC

## Problem and evidence

**Observed:** physical Stage B attempt 2 uploaded the payloads but failed the
prepared-DT framebuffer gate before Linux handoff (exit 1, 10.202 s).
[Preserved M1 result](../../../native/boot/stage-b-2026-10-13-attempt2-result.md).

**Confirmed offline:** boot021's actual Stage-B DT has no framebuffer child of
`/chosen`. In pinned public m1n1 `src/kboot.c`, `dt_set_fb()` looks up
`/chosen/framebuffer` and returns success without creating it when absent.
The local source was inspected at clean pin
`57a9339ffd1876e78297b17d34dece8cff8fa1ba`; this explains how DT preparation
can report success and still fail our observation gate. No decompilation was
needed: this precise contract is available as public source.

**Implemented:** boot022 adds exactly one node beneath the existing `/chosen`
(which already has two address/size cells and identity `ranges`):

```dts
framebuffer@0 {
    compatible = "apple,simple-framebuffer", "simple-framebuffer";
    reg = <0 0 0 0>;
    status = "disabled";
};
```

m1n1 fills geometry/range/format, renames the node and removes disabled status.
No physical address is baked in. The existing Image already has builtin
`CONFIG_DRM_SIMPLEDRM=y`, `CONFIG_DRM_FBDEV_EMULATION=y`,
`CONFIG_FRAMEBUFFER_CONSOLE=y` and `CONFIG_VT_CONSOLE=y`; rebuilding it is
unnecessary for this correction. Original Image/DT/initramfs, diagnostic
initramfs, m1n1 and all other payloads are byte-identical to boot021. The original
full DT remains unchanged; only the DT selected by the Stage-B launcher changes.

**Observation gate retained and strengthened:** offline verification requires
the disabled zero-address placeholder before USB can open. Prepared verification
requires exactly one enabled framebuffer, correct parent encoding, supported
pixel format, nonzero geometry and a sufficient non-overflowing memory range.
No relaxed board, CPU, storage, version or transport checks.

## Reproducible validation

Actual `dt_set_fb()` is extracted verbatim from the pinned public source and
compiled with GCC/libfdt inside the ARM64 Linux VM. SHA-256 of the extracted
function: `e6152693d69bc795cebe580ca325111d0448f9c7cdd57de2709a536169b117d9`.
The harness stubs only surrounding state and `get_notchless_fb()` with synthetic
640x480 data and a 16-row crop. It does not emulate physical display hardware
or the complete m1n1 preparation/handoff sequence.

| Case | Observed result |
|---|---|
| Old DT, valid synthetic video | Actual C prints no framebuffer found; gate rejects |
| Corrected DT, 32-bit video | x8r8g8b8, correct cropped range/height; gate accepts |
| Corrected DT, 30-bit video | x2r10g10b10, correct cropped range/height; gate accepts |
| Corrected DT, 16-bit video | r5g6b5, correct cropped range/height; gate accepts |
| Unsupported 24-bit depth | Placeholder remains unusable; gate rejects |
| Zero framebuffer base | Placeholder remains unusable; gate rejects |

Six C cases PASS with ASan/UBSan; semantic DT-only assertion PASS; dtc decompile
has zero warnings. Guest: 31 launcher tests and one real pinned serializer test
PASS. Host: five new framebuffer tests, 31 launcher tests and seven intake tests
PASS. Completed archive extraction, all 13 intake file hashes and offline launcher
verification PASS. No USB port was opened by these tests.

VM: existing Virtualization.framework job runner, 2 vCPU/4 GiB, Linux
7.1.6-vzrun2 aarch64. GCC 16.1.1 20260430; DTC 1.8.1; Python 3.14.8.
C flags: `-std=c11 -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined
-fno-omit-frame-pointer`, linked with `-lfdt`. Host stdlib checks use Python 3.9.6.
Job UTC start/end: 2026-10-14T02:12:35Z–02:12:36Z, exit 0. This is test-job timing,
not a native boot/performance benchmark. VM stopped; both quiet locks released.
Raw generated test outputs stay ignored in `out/`; all inputs are synthetic.

## Package and next physical question

Archive: `ilinux-j716c-boot022.tar.gz`, **16,717,590 bytes**.
SHA-256: `b59db87bee50f5a2b57f65ea54e9ecd9fc07d410251bb38175001ac056ee6862`.
Stage-B DT: 61,510 bytes,
`7adc1364687df9c358692489f2a574241e869cf03b67538eaaaaf0233b4365a7`.
Intake SHA256SUMS digest:
`862391dd99ee93d07c196e502196cefc869b2549274d6139d781f564b4bc50a0`.
Private prerelease: `native-j716c-boot022`; boot021 remains available unchanged.
The m1n1 version marker deliberately still ends in **boot021**.

**Native correction NOT TESTED; Linux NOT RUN.** After M1 intake and the return
policy check, one reviewed RAM attempt can determine whether real m1n1 produces
a valid display description, Linux emits visible output, PID 1 runs and the
60-second heartbeat succeeds. The missing reserved-memory/unknown display/GPU
warnings are not established causes of the recorded framebuffer rejection and
were not addressed speculatively. A valid DT does not prove a working display.

For the shortest path to Omarchy: obtain observable kernel/userspace liveness,
then tested interactive input/access and a Linux rootfs; only then attempt the
already prepared ARM64 desktop. Initially a software-rendered desktop may be a
useful bring-up milestone if the display/input path works. Native GPU, SMP and
idle/DVFS need separate measured enablement for performance/efficiency parity.
Do not delay this boot correction for unrelated driver reverse engineering.
