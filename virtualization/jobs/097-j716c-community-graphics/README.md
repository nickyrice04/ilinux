# Exact J716c community graphics reproduction

This job builds public source in the retained offline ARM64 Linux VM. It does
not install or enroll a boot object, access policy data, copy Apple firmware,
load native drivers, or qualify GPU operation on the Mac.

The source authority is Cameron Cooper's J716c bring-up record at
`5e11068a1c6d8fccb155bc6e0159cc16107e53ec`, including its `pins.json`:

- Aura graphics Stage 2: `9da61857f9d9262bd64c023fbc1b18315b12d0af`.
- Mesa: `10161a78e60e4057257e116d404a92bd9b78bb3c`.
- Published package versions/digests are recorded as reference identities,
  separately from our source-build identities and signature verification.
- The reference desktop is Arch Linux ARM/systemd with Hyprland 0.57.2;
  rebuilding that compositor and its Omarchy root is a separate integration job.

`sources.json` binds complete archive sizes/digests, roots, member counts,
unpacked extents, and selected Git blob identities. `validate_sources.py`
checks these without executing archive contents. Its optional extraction
requires Linux and a case-sensitive fresh destination. `test_sources.py`
exercises generated hostile paths, duplicate names, case collisions, special
files, links and member bounds. Run readers with Python `-I`.

The host workspace is case-insensitive. Full source/build trees must stay in
a freshly mounted, bounded guest tmpfs. Export compressed tar artifacts and
finite receipts, rather than loose source/build trees. The VM uses `--no-net`,
the retained project disk, and both repositories' exclusive `quiet` and `vm`
locks; do not start it while another lane owns that disk.

Aura has two separate fresh configurations. Stage 2 follows the pinned
`docs/t6050-linux.md`: `USE_CLANG=1 BUILDSTD=1 CHAINLOADING=1 ESP_STAGE2=1
DEBUGUSB_PROXY=1`. Generic Stage 1 follows its `docs/RELEASING.md`:
`RELEASE=1 CHAINLOADING=1 ESP_STAGE2=0`, with the same Clang/build-std toolchain.
The project reuses its reviewed `pad_boot.py` for the public file-backed
128 MiB execute-window contract; this is metadata validation of a new generic
candidate, not the historical publisher's installed Stage 1 identity.

Prefer the kernel lane's authenticated LLVM 22.1.8 and official Rust 1.96.1
closure. Mesa's CLC explicitly requires an LLVM/SPIR-V translator matching
LLVM's major and minor versions. The additional small Khronos translator
source is pinned separately. Never combine the existing translator 23 package
with LLVM 22. No package manager installation or dependency bypass is needed:
tool packages are verified and unpacked into a disposable guest prefix.

The intended Mesa outputs are the Asahi Gallium OpenGL/GLES driver, Asahi
Vulkan ICD, EGL and GBM with Wayland integration, followed by its CPU/offline
Asahi test suites. A compiler-only result is recorded separately if a missing
dependency prevents the complete build. Source compilation and no-op DRM
tests cannot establish physical G17C rendering, firmware compatibility,
panel operation, speed, power or macOS parity.

The completed baseline build passes compilation and retains 175/179 Asahi
tests, with four stale AGX3 transfer-advertisement failures. A separate original
test-only derivative passes 179/179 while preserving CPU conversion coverage;
the shipping driver stays unchanged. Full receipts and the isolated DESTDIR
archive survive test failures. The final guest/launcher exit is deliberately
nonzero while the baseline suite has those four failures; inspect `mesa/result.json`
for separate source-build and test results. A normal VM poweroff exit zero is
not a guest-test success. The archive remains an experimental research artifact,
including no-op-shim tooling, rather than a reviewed native distro package.
