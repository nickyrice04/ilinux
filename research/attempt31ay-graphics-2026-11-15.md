# 31AY: reproduce the exact J716c graphics foundation

Status on November 16: both Aura configurations, the LLVM 22 translator and the
complete selected Mesa driver build pass in the offline ARM64 VM. The untouched
Asahi suite retains 175 passes and four failures; a separate original test-only
derivative passes all 179. Native GPU, installation, power and performance
remain NOT RUN. No restart is proposed by this component job.

The reference is Cameron Cooper's [J716c bring-up record and pins](https://github.com/cameroncooper/linux/tree/5e11068a1c6d8fccb155bc6e0159cc16107e53ec/Documentation/arch/arm64/apple-j716c-bringup),
which identify Aura graphics Stage 2 `9da61857f9d9262bd64c023fbc1b18315b12d0af`
and Mesa `10161a78e60e4057257e116d404a92bd9b78bb3c`. These replace the older
generic GPU-source experiment as the build inputs. This job adopts their public
J716c/G17C implementation rather than rewriting those drivers.

All four complete source archives are bound by SHA-256 and reconstructed Git
trees before extraction. Aura matches tree
`65cc228925b90e0af8439d8ad4ff5b4f65bbbcec`; Mesa matches
`dc9cfffcb188a4fae9f04fded513b940ccd1499e`; the additional LLVM 22 translator
matches `944880f9e9900e4f64384589c40cd8596391a0ca`. Its explicitly required
SPIR-V header source revision `cb42dec3830d3ac67fa449ecdc0c0f73d5e74498`
matches tree `1e1f5974d8b3ed73a937d5e43506b1fd3233aff3`. Mesa's published
[EOL attributes](https://github.com/aurora-silicon/mesa/blob/10161a78e60e4057257e116d404a92bd9b78bb3c/.gitattributes)
and nested AMD attributes account for 33 CRLF-exported files. Only those explicit
patterns normalize for Git hashing; original codeload bytes remain unchanged for
the build. Eleven host tests pass, including four independent Git-CLI fixture
comparisons and seven archive-boundary tests. No downloaded source ran on macOS.

Two fresh Aura configurations are required. The pinned
[T6050 guide](https://github.com/cameroncooper/aura/blob/9da61857f9d9262bd64c023fbc1b18315b12d0af/docs/t6050-linux.md)
uses `USE_CLANG=1 BUILDSTD=1 CHAINLOADING=1 ESP_STAGE2=1 DEBUGUSB_PROXY=1`.
`ESP_STAGE2` is necessary to link the J716c GPU handoff object. The separate
generic Stage 1 follows the pinned
[release recipe](https://github.com/cameroncooper/aura/blob/9da61857f9d9262bd64c023fbc1b18315b12d0af/docs/RELEASING.md):
`RELEASE=1 CHAINLOADING=1 ESP_STAGE2=0`. Its public Mach-O wrapper is checked
with the existing reviewed 128 MiB execute-window padding utility, preserving
entry and raw bytes. This produces a new generic candidate; it does not recover
the historical publisher's installed Stage 1 or prove enrollment.

The LLVM 22.1.8 and Rust 1.96.1 inputs come from the kernel lane's version-bound
cache. Actual VM GPG checks pass for six ALARM compiler packages, the official
Rust release manifest and two support packages, with current selected signing
and primary keys and full ALARM trust. No weak-digest, clock or trust override
is used. Official Cargo 1.96.1 is separately bound to the same signed Rust
manifest. A credential-free offline vendor closure contains 54 SHA-bound crates
and the exact public fatfs Git object revision. No user's Cargo configuration,
tokens, Git configuration or hooks enter this closure. Runtime license notices
come from the actual official Rust 1.96.1 archives, avoiding the older collector's
installed-Arch-Rust assumptions.

Mesa explicitly requires an LLVM/SPIR-V translator matching LLVM's major and
minor versions. The cached version-23 translator cannot serve LLVM 22. The job
therefore source-builds Khronos'
[release-22 translator](https://github.com/KhronosGroup/SPIRV-LLVM-Translator/tree/ae707ecba4b0c64d85f4f7bdcabeb1fa152c0ab2)
with an explicit local SPIR-V header path and no dependency downloads. A generated
original OpenCL kernel exercises translation, validation and reverse translation
using CPU tools only. This is an additional build dependency, not a claim about
the community package's unpublished compiler recipe.

The complete selected Mesa build enables Asahi Gallium, Asahi Vulkan, Wayland,
EGL, GBM and GLES, with the no-op DRM shim and upstream Asahi tests. X11/GLX and
GLVND packaging are excluded from this first source-build recipe and remain
separate desktop-package integration requirements. Build products and package
reference hashes are kept distinct; no byte-identical community-package rebuild
is claimed. A successful CPU/no-op-shim test cannot prove physical GPU operation.

Job 097 uses the retained ARM64 VM, eight CPUs, 52 GiB RAM and a bounded 32 GiB
guest tmpfs. Both repositories' VM/quiet locks protect the one shared disk. The
VM has no network; only curated public input directories are shared read-only.
No frozen VM startup job is changed, and full source/build trees stay on the
case-sensitive guest filesystem. Only artifacts, notices and receipts leave it.
No host package, policy, boot object, firmware or macOS installation is changed.

Actual results are retained in the ignored job-097 build workspace and indexed
by the companion finite JSON. The final run uses Linux `7.1.6-vzrun2`, Clang/LLVM
22.1.8, Rust/Cargo 1.96.1, Meson 1.12.1, Ninja 1.13.2, libdrm 2.4.134 and
SPIR-V Tools 2026.4.1. Source-built LLVMSPIRVLib reports 22.1.0.0. The complete
Mesa build finishes 2,356 Ninja actions. Linux checks additionally pass 39 stack/
package/lease methods, 11 provenance methods, 24 padding methods and six test
transform/refusal methods, with zero skips. All 15 Aura artifact size/hash maps
are identical across three fresh VM builds.

The four baseline failures share one stale assertion: they require accelerated
BLIT texture-transfer advertising on AGX3. The same pinned
[production driver](https://github.com/aurora-silicon/mesa/blob/10161a78e60e4057257e116d404a92bd9b78bb3c/src/gallium/drivers/asahi/agx_pipe.c#L2639)
deliberately retains CPU transfer conversion until its GPU BGRA/RGBA conversion
path is hardware-qualified. Changing that driver to satisfy these assertions
would remove a correctness protection. The original suite and complete raw
JSON/text receipts stay 175 PASS / four FAIL.

The independently reviewed original test-only derivative preserves existing
render/encode/compression assertions, checks generation-specific advertising,
and exercises CPU upload/map and BGRA/RGBA conversion in two formats over 64
pixels with padded rows. Its separately recorded full suite passes 179/179.
The original test C is restored afterward. The shipping driver and already
exported baseline artifact remain unchanged. This qualifies the CPU fallback
contract in the no-op environment; it does not qualify GPU pixel conversion.

The exported DESTDIR archive is 73,897,453 bytes, SHA-256
`1ea6478304790a3f6ed1d5fcce142904bdd6f02d8700109dc47630340a7ce6a2`.
It contains the actual Mesa 26 unified `libgallium-26.3.0-devel.so`, the Asahi
Vulkan ICD and EGL/GBM/GLES libraries. An obsolete per-driver DRI-path assertion
caused the second harness run to stop after successful installation; the final
harness checks the actual pinned-source layout and exports the archive before
individual assertions. Full baseline and derivative receipts survive failures.
The first harness run's test-stop/export gap is retained in the finite record.
Normal VM shutdown returns zero while the final guest deliberately returns one
to retain the four unmodified baseline failures; these are distinct results.

The archive is a debugoptimized research build with no-op-shim tooling. Native
distribution packaging must separately admit its runtime dependencies and
desktop integration. It is not installed by this job. The new generic padded
Stage 1 is 153,190,400 bytes, SHA-256
`c4d3d52decadc850474eb9d4509abf8c1b330117c9a338c2dd197b7856f9d01c`.
Its verified `kcbz=0`, entry and raw-byte preservation are layout evidence only.
Published firmware matching, enrollment, actual secondary startup, physical GPU
operation, the usable Omarchy root and guardian qualification remain separate
deployment gates. The reference's external hardware success does not convert
these VM builds into a native or macOS-parity result.

Implementation and explicit configure flags are in
`virtualization/jobs/097-j716c-community-graphics/`.
