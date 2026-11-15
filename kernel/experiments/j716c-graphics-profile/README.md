# Frozen J716c graphics configuration admission

**Confirmed offline:** this original, dependency-free tool admits the exact
published J716c configuration and compares it with our existing 31AH diagnostic
configuration. It neither enables a driver nor installs a kernel. Runtime safety,
boot readiness and performance remain unverified.

This makes the useful part of the external work reproducible: a precisely pinned
full configuration and a checked, deterministic list of what our diagnostic
build omits. Enabling one option called “M5” would not reproduce that stack.

## Inputs and attribution

The reference is Cameron Cooper's
[J716c publication at 5e11068a](https://github.com/cameroncooper/linux/tree/5e11068a1c6d8fccb155bc6e0159cc16107e53ec/Documentation/arch/arm64/apple-j716c-bringup),
covering Mac17,6 / J716c / T6050 / G17C. Its full `kernel.config` is
330,809 bytes, SHA-256
`3c11e751cb6d6e0358429230d28121c7f383aa5437a2e0b7d181b85f6dd7dbe8`.
We retrieved the public config and source through the GitHub connector as data;
the complete third-party files stay in the ignored build tree. No third-party
code or proprietary artifact is embedded in this tool.

The corresponding kernel is
[`a59e709c7377`](https://github.com/cameroncooper/linux/commit/a59e709c737777495c84541c6afb6c862bb79227),
source tree `5960d8ab03fef0f87e91e84fe1a8d969173da8de`, and the graphics Stage2 is
[Aura `9da61857f9d9`](https://github.com/cameroncooper/aura/commit/9da61857f9d9262bd64c023fbc1b18315b12d0af).
The latter is **not** the complete installed Stage1/recovery configuration.

The publication preserves the work of Rolando Trevino (M5 layout), Erik Bourget
(GPU/panel DT), Jeff Queisser (DCP method table), and the Asahi/Aurora contributors.
`provenance.json` records their source references, file SPDX licenses, Git blobs,
toolchain, firmware and comparison hashes. Our new Python and test code use MIT.

The reference reports 18 CPUs online, native panel/GLES/Vulkan and N1 Wi-Fi in a
bounded Arch engineering RAM root. That is valuable evidence of a software route;
it is not an Omarchy installation, unrestricted power qualification, suspend
qualification, or measured macOS parity.

## What the tool checks

`profile.py` reads bounded regular files without executing them. Duplicate symbols,
partial records, malformed values, invalid encoding, final-path symlinks and oversized inputs
fail. A reviewed subset locates SMP, 16 KB page, CTXR executable-confinement,
ACTLR, Rust, GPU/provider, mailbox, CPU frequency and public-input mistakes. Full
admission additionally requires the exact published file size and SHA-256: passing
the subset alone does not admit a changed configuration.

Two details prevent misleading results:

* The real Max reference has `DRM_ASAHI=m`, `DRM_APPLE=m`, and
  `DRM_ASAHI_M5` **unset**. The pinned
  [Asahi Kconfig](https://github.com/cameroncooper/linux/blob/a59e709c737777495c84541c6afb6c862bb79227/drivers/gpu/drm/asahi/Kconfig)
  gives the named M5 option a base T8142/G17G firmware profile; it is not a universal
  gate for every M5 GPU. This tool preserves the actual tested Max choices.
* `NR_CPUS=512` is the configured CPU capacity. The pinned
  [arm64 Kconfig](https://github.com/cameroncooper/linux/blob/a59e709c737777495c84541c6afb6c862bb79227/arch/arm64/Kconfig)
  allows 2–4096. It does not make 512 cores online or justify 512 benchmark workers.
  The report leaves measured online count and worker count null; actual topology,
  core types, IPIs and coherency need native checks.

The baseline is the actual 31AH resolved config identified in
`native/boot/attempt31ah/manifest.json`, SHA-256
`bba7ce251238c3cb6779d884a3442373443f7eed97e19f638afc08fdb9779fd8`.
The existing diagnostic validator remains unchanged: it intentionally forbids
graphics/PMP/Rust and constrains the collector to a smaller configured capacity.
That restriction is useful for the diagnostic profile and is not a hardware limit.

The real full-config comparison found **1,376 changed symbol records**:
1,292 additions, 17 removals and 67 changed existing entries. Missing symbols are
reported as missing, rather than falsely presented as disabled. Important changes:

| Component | Existing 31AH | Published J716c graphics |
|---|---|---|
| Rust | disabled | enabled, matching Rust/LLVM/bindgen required |
| AGX rendering | not present | modular `DRM_ASAHI` + Rust DRM helpers |
| Native display | disabled | modular Apple DCP/fabric support |
| GPU power chain | not present | modular PMP + CLPC/report support |
| CPU frequency driver | built in | module |
| NVMe / SART | modules | built in |
| CPU capacity | 64 | 512; still 18 reported online on reference board |

These are data differences, **not** a fragment to apply to the old tree. The new
source, toolchain and complete configuration must be kept together. A config diff
does not prove module dependency resolution, firmware compatibility or safe access
to storage.

## Reproduce the offline checks

From the repository root, obtain the exact
[public config](https://github.com/cameroncooper/linux/blob/5e11068a1c6d8fccb155bc6e0159cc16107e53ec/Documentation/arch/arm64/apple-j716c-bringup/kernel.config)
as data and save it under the ignored build directory. No host install is needed.
The following paths name the reviewed local data used for the recorded run:

```sh
python3 -I kernel/experiments/j716c-graphics-profile/profile.py \
  --config build/j716c-graphics-profile/reference-v1/third-party/kernel.config \
  --diagnostic-config build/direct31ah-kernel/job/out/kernel.config

python3 -I kernel/experiments/j716c-graphics-profile/test_profile.py \
  --reference build/j716c-graphics-profile/reference-v1/third-party/kernel.config \
  --diagnostic-config build/direct31ah-kernel/job/out/kernel.config -v
```

`--all-differences` adds every sorted symbol difference to the JSON report. Exit
status 0 admits only the exact full reference configuration. A mutation, invalid
input or different configuration returns 1. No output or input path is installed
or modified. The tests create and remove only their own temporary files; they
require the genuine downloaded reference and actual baseline, and do not silently
skip those integration checks.

Sixteen tests passed on 2026-11-15: real config admission and exact baseline delta;
SMP/page/confinement/Rust/provider mutations; module-mode mismatches; capacity vs
topology; accidental embedded inputs; benign hash changes; duplicate/malformed
records; file bounds/symlinks; deterministic output; and CLI refusal/success. The
existing diagnostic validator also continued to pass its unchanged config.
`offline-validation.json` is the actual generated report, not hardware evidence.

## Next build and native gates

**Not run:** matching-source Kconfig resolution, compilation, linking, DT checks,
module install, kernel boot and benchmarks. The recorded external build used
arm64 clang/lld 22.1.8, Rust 1.96.1 and bindgen 0.73.2, with matching Rust library
sources and libclang. A next isolated build should resolve the frozen full config
against `a59e709c7377`, review any Kconfig delta, then build `Image.gz`, `modules`
and `apple/t6050-j716c.dtb`. No byte-identical rebuild claim is made by the source
publication or this tool.

Config admission intentionally leaves these conditions **NOT VERIFIED BY CONFIG**:
matching board/loader properties and firmware, RTC and external ATC2 runtime DT
exclusions, valid SMC telemetry before raising the bounded CPU ceiling, firmware
fan ownership, default-off shallow WFI, physical-watchdog/host-guardian recovery,
and a matching graphics Stage2/modules/Mesa/RAM root. RTC support is compiled by
the reference but its runtime DT node remains disabled. The guardian and installed
Stage1/root/Apple payloads are not supplied by the public source pins.

Do not enable the GPU or unrestricted clocks by copying only this config into the
current boot package. First finish the existing lab transaction/rollback work,
reproduce the matched build offline, and independently qualify the missing runtime
inputs. This directory supplies no enrollment, firmware-update, Startup Disk or
boot-object command. `native_ready` and `restart_ready` stay false even on PASS.
