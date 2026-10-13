# Native Omarchy configuration handoff kit (for agent C)

Prepared 2026-10-13 by agent A (goal 7). This kit is for the **configuration
agent (C)** that takes over **after** a native Linux desktop boots on this Mac
(coordination.md gate N4). It does not itself boot anything. Read
[`../../coordination.md`](../../coordination.md), the
[first-boot plan](../../kernel/native-enablement/first-boot-plan.md) and the
[native-enablement plan](../../kernel/native-enablement/plan.md) first.

Agent C's job: bring the booted native system up to a usable Omarchy desktop,
reusing what the project already built, substituting fallbacks for hardware
that has no driver yet, and recording every change as a package or config file
in this repo. **C does not do reverse engineering** — agent B owns that; C
consumes B's findings (section 3).

## 1. VM-only files — do NOT apply natively

These make Omarchy work *inside the QEMU/HVF VM* by borrowing macOS. On real
hardware they are wrong (they point at a host that isn't there, or disable
things the hardware needs). **Do not install any of them on the native
system:**

| File (under `omarchy-arm64/configuration/vm-integration/`) | Why it is VM-only |
|---|---|
| `bin/ilinux-host-bridge`, `systemd/ilinux-host-bridge.service` | battery/clock/timezone over a virtio-serial port to the macOS host agent — no host natively |
| `bin/ilinux-timezone-sync`, `systemd/ilinux-timezone-sync.service` | timezone from the host kernel cmdline |
| `bin/ilinux-clipboard-agent`, `systemd/user/ilinux-clipboard.service`, `etc/udev/rules.d/70-ilinux-vdagent.rules` | SPICE vdagent clipboard to QEMU |
| `etc/environment.d/60-ilinux-vm-vulkan.conf` | `MESA_VK_WSI_DEBUG=nowlts` — a VM FIFO-pacing workaround; native has real vblank |
| `etc/environment.d/70-ilinux-vm-video.conf`, `etc/mpv/mpv.conf` | VA-API on VideoToolbox-backed virgl — native video is the M5 AVD via V4L2, a different path |
| `etc/systemd/resolved.conf.d/30-ilinux-vm-dns.conf`, `etc/NetworkManager/conf.d/90-ilinux-vm-dns.conf` | work around QEMU NAT DNS |
| `etc/sddm.conf.d/20-ilinux-vm-autologin.conf` | test-VM autologin (a native machine should not autologin) |
| The VM kernel package `linux-ilinux-vm` and the `cpuidle-vmpoll` module | tuned for QEMU/HVF (vCPU wakeup, virtio); native uses the t6050 kernel from job 020 |

## 2. What carries over to native

* **`omarchy-qos` and the QoS tiers** — scheduler/cgroup policy, hardware-
  independent. Keep.
* **Kernel options:** 16 KiB pages and `uclamp` (`CONFIG_UCLAMP_TASK*`). The
  native kernel (job 020) already builds 16 KiB pages; confirm uclamp is set
  for the native config too.
* **The t6050 energy-model and OPP drafts** (`kernel/native-enablement/`,
  generated from the ADT DVFS tables) — **unvalidated**. Use only after the
  native cpufreq/EAS mechanism is proven (plan §3(f,g)); do not assume the
  numbers are correct on hardware.
* **The `aarch64-apple` package choices** (`omarchy-arm64/`), minus the VM
  package set in section 1.
* **The native kernel, DT and diagnostic initramfs** from job 020
  (`virtualization/jobs/020-t6050-full-build/out/`).

## 3. Hardware matrix (consume B's research; do not redo RE)

Status as of first native boot. Sources: the
[gap matrix](../../reverse-engineering/macos-hardware-services.md) (23 rows,
priorities, the macOS component behind each block), B's
[driver-interface findings](../../reverse-engineering/findings/driver-interfaces-2026-10-13/handoff.md),
and the [native plan](../../kernel/native-enablement/plan.md). **Agent C uses
these; it does not re-analyze binaries.**

| Device | Native status at first boot | Fallback for C |
|---|---|---|
| CPU (18 cores) | single-core Likely; **SMP unresolved** (plan §1.2) | run on available cores; do not assume 18 |
| Memory, timers, AIC | expected working (upstream + DT) | — |
| **GPU (G17)** | **no driver** | **llvmpipe** software rendering; expect a slow desktop |
| Display | framebuffer only (simpledrm on mBoot fb); no DCP/modeset | fixed-resolution framebuffer; no brightness/VRR |
| Storage (NVMe) | SARTv4 + M4+ split drafted (patches 0001–0005), **unvalidated** | read-only identify first (first-boot plan Stage D); a separate Linux partition only after gate N3 |
| **Wi-Fi / BT (Apple N1)** | **no driver** (B analyzed the AirshipDK ring arithmetic only, not a driver) | **USB Ethernet dongle or USB tethering** for all networking |
| Keyboard / trackpad | `dockchannel-hid` parser hardened (B); transport/DART/MTP firmware not up | use a **USB keyboard** until MTP works |
| Audio / mic | not up (B mapped transport interfaces only) | none; expect no audio |
| Camera (ISP) | not up (B mapped command IDs only) | none |
| Neural Engine | no driver (exclave-mediated) | CPU/GPU for any ML; no ANE |
| Touch ID | out of scope (Secure Enclave, B-014) | **USB fingerprint reader (libfprint)** or a **FIDO2 key** for login/sudo |
| USB-C / Thunderbolt | ATC PHY / XHCI not brought up | needed for the dongles above — bring-up is a prerequisite, verify early |

## 4. How agent C reaches the system (it needs its own network)

N1 Wi-Fi has no driver, so plan C's own connectivity before handoff:

1. **USB Ethernet dongle** (or USB-C tethering from a phone), once USB host is
   up. This is the primary path.
2. **The second machine** can continue coordinating tests, but m1n1's
   pre-Linux USB proxy does not survive a native handoff as a Linux console.
   A serial/SSH bridge is usable only after that distinct transport is
   implemented and tested; none is supplied by the initial RAM diagnostic.

C must confirm one of these works before it depends on fetching packages.

## 5. Acceptance checks

Run [`acceptance-checks.sh`](acceptance-checks.sh) on the native system and
record its output into this repo. It checks, and flags as pass / degraded /
fail:

* all CPUs online and their `cpu_capacity` values;
* storage: controller identify, SMART/health, **no writes to macOS volumes**;
* display: a framebuffer console is present;
* input: a keyboard device exists (native MTP or USB);
* audio: a card is present (expected absent → degraded, not fail);
* **idle power** with the WFI workaround (`idle=nop`) in place;
* **suspend**: expected **not** to work yet — the check records the state, it
  does not attempt a suspend that could hang the machine;
* the Omarchy shell test suite where it applies on this hardware.

Degraded (expected-absent hardware) is not a failure; an unexpected absence or
a regression against the matrix is.

## 6. Guardrails (mandatory, same as the rest of the project)

* **Never** touch the macOS volumes or the APFS container; never write to the
  macOS NVMe namespaces. Storage work is read-only until gate N3 gives Linux
  its own partition.
* **No** firmware, SEP, boot-policy, SIP or security-setting changes.
* **No** credential handling (no passwords/keys typed or stored).
* **Record every change** as a package (`omarchy-arm64/packages/…`) or a
  config file in this repo, never as an unrecorded edit on the live system, so
  the native build stays reproducible.
* Heavy work coordinates through `tools/lock.sh`; C uses its own `AGENT_ID`.
