# 31AX: reuse the working J716c stack first

November 15, 2026. Bounded read-only primary-source audit. No downloaded code
was executed, no package/image/firmware was installed, no large clone or binary
download occurred, and no host setting changed. This is an adoption plan, not
an instruction to run a third-party installer.

## Decision

**Adopt existing exact-board enablement as a matched stack.** Further original
driver work should address a demonstrated gap after that baseline runs. The
public sources now contain native J716c/T6050 CPU, N1 and accelerated graphics
work; independently reconstructing those drivers is no longer the fastest path.
Retain our repository, measured comparisons, safe Lab transaction/rescue controls
and machine-specific admission checks.

Betizzel's current [README at `7df16b1b`](https://github.com/betizzel/omarchy-m5/blob/7df16b1b51469edcf7d2f2a593d9e7437a0af71d/README.md)
explicitly supports the **14-inch M5 Pro/J714s**, not M5 Max or 16-inch models.
Its image is therefore not a drop-in installer for this Mac17,6/J716c. Its
maintainers nevertheless invite exact-board work, and
[Erik Bourget identifies his J716c daily branch](https://github.com/betizzel/omarchy-m5/issues/12#issuecomment-6904255259)
as his working 16-inch M5 Max setup. This is useful source reuse, not evidence
that a J714s image can safely be relabeled J716c.

## Exact-board starting point

[Cameron's J716c report](https://github.com/cameroncooper/linux/blob/5e11068a1c6d8fccb155bc6e0159cc16107e53ec/Documentation/arch/arm64/apple-j716c-bringup/README.rst)
reports all 18 CPUs, N1/SSH, native panel rendering and Vulkan on a RAM Arch/
Hyprland engineering root. It expressly excludes a persistent Omarchy install,
the installed Stage 1/enrollment recipe and the separately deployed watchdog
guardian. CPU ceilings remain approximately 2 GHz with checked telemetry;
this is not macOS performance or efficiency parity.

Use its [machine-readable pins](https://github.com/cameroncooper/linux/blob/5e11068a1c6d8fccb155bc6e0159cc16107e53ec/Documentation/arch/arm64/apple-j716c-bringup/pins.json)
as one coherent, reproducible baseline:

| Component | Qualified published pin and adoption scope |
| --- | --- |
| Board/firmware | Mac17,6/J716c/T6050/G17C; 27.2.1 build 26B131, mBoot 20457.41.3. Our recorded 26.6.2 environment is a different baseline. |
| Kernel | `cameroncooper/linux` integration `a59e709c737777495c84541c6afb6c862bb79227`, based on Aurora `dc8f6f77934b471a13c91e7780e2d91ebc904b3d`. Build Image, modules and `apple/t6050-j716c.dtb` together. |
| Full kernel config | Published `kernel.config`, SHA-256 `3c11e751cb6d6e0358429230d28121c7f383aa5437a2e0b7d181b85f6dd7dbe8`. Reuse the complete config, not our old minimal diagnostic fragment. It enables 16K pages, SMP, CTXR executable memory, Apple NVMe and the N1/GPU/DCP modules. |
| Build toolchain | LLVM/lld 22.1.8, Rust 1.96.1, bindgen 0.73.2, matching Rust sources/libclang and the published build identity. A successful build is not byte identity with the measured binary. |
| Graphics Stage 2 | `cameroncooper/aura` `9da61857f9d9262bd64c023fbc1b18315b12d0af`. Keep its firmware handoff paired with that kernel; this pin does not identify Stage 1. |
| Renderer | Mesa/Vulkan `10161a78e60e4057257e116d404a92bd9b78bb3c`, the [native G17S/G17C Gallium merge](https://github.com/aurora-silicon/mesa/commit/10161a78e60e4057257e116d404a92bd9b78bb3c), plus the exact published package assets and Hyprland 0.57.2. |

The source contains already integrated public M5 InitData, panel/GPU and DCP
work with attribution. This replaces speculative driver translations with
known source. Preserve its safety limits initially; CPU frequency/idle, power,
storage throughput and sustained thermal behavior still need measurements here.

Erik's [`ewb/j716c-daily` at `4e1f8e6a`](https://github.com/aurora-silicon/linux/commit/4e1f8e6a13191c42b3ce1bb1519e48440c06d79a)
is a second exact-board integration lead, including a board-specific ANE pin for
27.0/26A428. It is not interchangeable with the 26B131 stack. Its per-unit DROM
must not be copied; use our independently obtained unit data. A branch called
working is also not a complete record of its owner's Stage 1, firmware and
package deployment.

## Reuse the installer and desktop integration, with board gates

The current [J714s installer recipe](https://github.com/betizzel/omarchy-m5/blob/7df16b1b51469edcf7d2f2a593d9e7437a0af71d/installer/README.md)
uses a 27.2 Apple stub and padded Aura Mach-O Stage 1, `kcbz=0`, a 128 MiB
executable window and compressed enrollment. Stage 1 selects
`m1n1/boot-ctxr.bin`; persistent boot continues through window-aware U-Boot and
Limine. Its old `docs/bringup.md` raw-boot/stub-cloning commands are historical,
not the current image's recipe. Do not rerun their partitioning scripts here.

The [Aura Mach-O contract](https://github.com/aurora-silicon/aura/blob/52af355ca2c3b814f7610003bcefda16f6bfb943/docs/macho-boot-object.md)
requires the padded window, matching CTXR-aware kernel/module placement and,
if used, compatible U-Boot. Its statement that 26.6.2 kmutil parses the object
does not establish matching firmware behavior on our present Lab. The current
J714s loader recipe pins Aura `22b71758` plus firmware/board handoff patches;
its U-Boot recipe pins `70e990818a895454780797beedc6a7bdac9e2fd6`.
Reuse the construction and validation mechanisms, not J714s-only hardware pins.

[Omarchy's Mac packages](https://github.com/omacom/omarchy-mac-pkgs/blob/76d8b7222e5c10d7b7a89803771f363c3c181b2c/README.md)
already provide desktop defaults/services, firmware/initramfs, first boot and
boot-update verification. Layer them onto our Omarchy root rather than recreate
the Mac desktop integration. Review board-specific audio/calibration and session
choices, retaining speaker protection. The J714s Hyprland recipe also records
DCP alpha-plane/direct-scanout fixes; reuse relevant fixes only with the matching
Hyprland ABI and test them on J716c.

The [shared package boot guard](https://github.com/betizzel/omarchy-m5/blob/7df16b1b51469edcf7d2f2a593d9e7437a0af71d/installer/recipes/omarchy-aurora-firmware/m5-boot-guard)
is useful update protection, but currently recognizes K114s and otherwise uses
J714s paths/profile. Add an explicit J716c profile and our kernel/loader/firmware
pins before adopting it. It is not the physical watchdog guardian omitted from
the J716c engineering report. Those are separate requirements.

Version labels also need care: the README's hardware-tested release 8 uses
v272-12, while the fetched kernel PKGBUILD already describes v272-15 based on
`6612865ee100cd266aedb55de13aaec2131ac8aa`. Current recipe code is not automatically
the tested release's code, and neither result is a J716c acceptance test.

## Concrete adoption sequence

1. **Freeze an exact-board stack manifest offline.** Prefer the fully pinned
   J716c engineering baseline for the first comparison. Record every kernel,
   config, module, DT, Aura stage, firmware compatibility and Mesa/userland input;
   keep newer Erik/Aurora deltas as separately tested alternatives.
2. **Rebuild in isolation and assemble our Omarchy root.** Use the complete
   config/modules and accelerated userspace. Import appropriate existing Mac
   packages and update protection with J716c admission. Keep firmware/unit data
   independently sourced and excluded from public Git; preserve licenses/authors.
3. **Keep AX as the safety/rollback layer.** Qualify the actual Stage 1 and
   Lab enrollment against the selected stack. Avoid endless changes to an old
   minimal kernel or relaxed policy checks merely to retain 26.6.2.
4. **Present one concrete firmware/boot transition for approval.** A matched
   newer baseline may need an Apple-supported update and a corresponding Lab
   boot-firmware refresh. Updating Macintosh HD alone must not be assumed to
   update the Lab's separate firmware inputs. No update or volume/security change
   is authorized by this audit; Macintosh HD stays protected.
5. **One informative RAM-root acceptance window.** Establish all 18 CPUs,
   hardware-rendered desktop, N1/SSH, keyboard and repeated app open/close/input
   latency, then CPU/RAM and power/thermal measurements with recorded limits.
   Reuse the M1 for bounded watchdog/return observation and optional camera
   recording. Add persistence/storage tests only under a separate reviewed plan.

The genuine unmatched pieces are a complete exact-board enrollment/deployment
record for our chosen firmware, safe independent firmware/unit inputs, our
physical rescue/guardian integration, and J716c acceptance/performance evidence.
NVMe code support does not prove SSD speed parity or safe access to macOS APFS;
device-up ANE, video, camera, sleep and audio claims remain feature-specific.
These are integration and validation tasks, not a reason to wait indefinitely
for Apple or independently rewrite already working CPU/GPU/N1 drivers.
