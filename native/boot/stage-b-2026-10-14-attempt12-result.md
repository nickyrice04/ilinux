# Stage B attempt 12 — boot031 GPIO cache boundary and successful macOS return

2026-10-14. **One RAM attempt consumed; no retry authorized by this result.**
Controller PASS. Native Linux reaches GPIO/deferred-probe diagnostics, with the
first controller's IRQ handoff and successful probe return observed. The final
panel places the main pin controller at **B=73, bounded register-cache
initialization**. Diagnostic PID 1, userspace `online_cpus=1`, and 60-second
userspace liveness remain **NOT OBSERVED**. The human confirms return to the
usual Macintosh HD desktop. Fresh post-attempt-12 policy/default checks are
**NOT CHECKED**; no settings or volume changes were made by M1.

## Provenance and offline readiness

* M5 handoff: `cd9ac3f85db6fe6d0ca6dc6880d9e5cd975bd845`.
* Published M1 readiness and execution: `83f0f208eb92cecb421453df94fcfd5fbf90d502`.
* Release: `native-j716c-boot031`, archive 16,724,870 bytes, SHA-256
  `73ad67d17c78da9ef2eeec63122e52271e8a9521120add8d60588a6585ab9246`; verified against Git **before extraction**.
* Image: 44,534,272 bytes, SHA-256 `09d3cc302da20ef53c41bec3324d702b249a729a55e3799b5676618034bff37d`.
* SHA256SUMS digest: `f4b76d8750c5dceb99d03819f457942581540b8f8b6dd546f6153c36ae1de885`.
* **13-file intake and offline launcher PASS.** Only Image and package-manifest
  metadata differ from retained boot030; DT/config/initramfs/m1n1 unchanged.
* **90 M1 offline tests PASS**: 37 launcher, 6 entry, 16 DAPF, 5 framebuffer,
  19 hardware, 2 pinned ADT/DAPF, 4 root ADT, 1 real proxy serializer; exit 0.
* Client clean/pinned at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
  Installed boot021 marker remains correct. Source/controller/procedure hashes
  and receipt were rechecked unchanged after the single invocation.
* Initial extraction hit the system Python's unsupported `filter` parameter,
  before extraction occurred. Revalidated archive/path/type restrictions,
  extracted regular files/directories only, then intake/offline launcher PASS.
* Ignored receipt: `build/native-intake/receipts/boot031-attempt12.json`; SHA-256 `540de0ce78254be703dda63b158b9c70dd57552cba7540821fc6840b9109ab2a`.
  Full sanitized local record: `build/native-intake/results/boot031-stage-b-attempt12.json`
  and `.md`. Prior packages, receipts and results retained.
* M5 post-attempt-11 protection prerequisite already PASS: human Full/Permissive
  JSON exits 0; independent original root/build/FileVault/SIP/staged-m1n1 checks.
  Default/installed object/authenticated-root were not separately re-queried.
* Human requested current M5 instructions and confirmed proxy running plus video
  recording. Readiness was published and explicitly announced before launch.
  M5 generic VM success is separate from this native outcome.

## Single controller invocation

Reviewed launcher `main(argv)` invoked once by a local sanitized wrapper with
exact documented arguments, fixed output checkpoints, a zero-attempt guard and
readiness/source-hash checks. No separate handshake, shell/setup, reconnect or
retry. Raw target output was discarded rather than retained in the workspace.

```sh
tools/m1n1-client/run.sh native/boot/launch.py \
  --package build/native-boot031-download/ilinux-j716c-boot031 \
  --launch --device auto --confirm BOOT-J716C-RAM-DIAGNOSTIC
```

| Controller item | Result |
|---|---|
| Invocation count | 1 |
| Start UTC | 2026-10-14T16:19:37.850798+00:00 |
| Handoff UTC | 2026-10-14T16:19:48.168614+00:00 |
| End UTC | 2026-10-14T16:19:48.396252+00:00 |
| Elapsed / exit | **10.545 seconds / 0** |
| Target identity/marker/secondary guard | PASS: t6050, boot021 marker, no started secondaries |
| Board/framebuffer prerequisite | PASS |
| Final Hardware DT | PASS: J716c/t6050 topology, AIC3 and timer routes |
| First DAPF layout check | PASS: reviewed AOP DART/GAPF-only case |
| Final DAPF correction/readback | PASS: bounded 96-byte RAM table |
| Early framebuffer descriptor/readback | PASS: bounded 16-byte kernel RAM descriptor |
| kboot reply and USB close | PASS |
| Screen deadline | 16:21:48.168614 UTC / **12:21:48 p.m. Eastern** |

The 180-second controller/15-second transport bounds remained. Screen stop was
instructed at the 120-second handoff deadline, followed by power-off/startup
options and Macintosh HD. Human confirms desktop return. Controller exit 0
and kernel watchdog activity do not establish userspace success.

## Direct screen evidence

Detailed photo directly reads:

```text
target=j716c-t6050 mode=EL2 cpus=1
timer counter=PASS ticks=25
timer phys=1 virt=7 irq_masked=0 fiq_masked=0
reschedule pending=1 strip=1 display=6 (P/S/W/H hex)
```

Printed phases: **1 → 10 → 11 → 12 → 13 → 2 → 3 → 4 → 5**; `device=0`
on these phase lines. `clk_debug_init blacklisted` is visible, followed by
`deferred_probe_initcall+0x0/0x4e0` and diagnostic progress. Linux/Tux is visible.
The watchdog header reads `7.1.9-g863199d8b4a3-dirty #9 PREEMPT`, Not tainted.
`display=6` and all four visible rows establish this panel rendered;
`console_setup` was **NOT OBSERVED**. Kernel `cpus=1` is separate from the
unobserved userspace `online_cpus=1` milestone.

Literal panel samples (hex; video-relative times, not handoff elapsed times):

| Video seconds | P | S | W | H | D | B | C |
|---:|---|---|---|---|---|---|---|
| 15 | 05 | NOT CONFIRMED | 04 | 00 | 0057 | 20 | 0057 |
| 18 | 05 | NOT CONFIRMED | 04 | 01 | 0057 | 64 | 0057 |
| 20 | 05 | NOT CONFIRMED | 04 | 01 | 0059 | 20 | 0059 |
| 22 | 05 | NOT CONFIRMED | 04 | 02 | 0059 | 21 | 0059 |
| 25 | 05 | 09 | 04 | 02 | 0059 | 73 | 0059 |
| 30 | 05 | 09 | 04 | 02 | 0059 | 73 | 0059 |
| 40.013 | 05 | 09 | 04 | 02 | 0059 | 73 | 0059 |

The detailed photo independently confirms the final **P:05 S:09 / W:04 H:02 /
D:0059 / B:73 C:0059**. Early S digits remain unconfirmed because of
repaint/console overlap. Missing transitions are not reconstructed.

Offline decode using the checked-in public identity/phase tables:

* **0057**: `/soc/pinctrl@2881e4000`, `apple,t6050-pinctrl` /
  `apple,t8103-pinctrl`. Video samples show B20 then B64.
* **0059**: `/soc/pinctrl@29c000000`, same compatibles. Samples show B20,
  B21, then **B73: GPIO probe, initialize bounded register cache**.
* P05/W04 locate the first work flush and worker before bus-probe return.
  D/C are public table indices. Markers describe last instrumented boundaries,
  not an atomic state snapshot, a blocked PC or proof of a particular fault.

The photo supplies a concrete first-controller result:

```text
2881e4000.pinctrl: t6050 IRQ handoff: pins=61 parents=7 masked=1
2881e4000.pinctrl returned 0 after 1918983 usecs
retry=1 end compatible=apple,t6050-pinctrl
```

The retry-1 begin line is also visible. A later `compatible=apple,t6050-pinctrl`
line is readable with its prefix obscured. No IRQ-handoff counts, return or
explicit error for the main controller were observed. No locked-GPIO or
mask-readback error was seen in reviewed samples. No AP/AOP counts are inferred
from inventory. First-controller return does not establish functioning input,
all GPIOs, or a performance measurement.

## Watchdog, scheduler and symbolic stack

First watchdog at kernel time **6.628526**: `heartbeat=1 phase=5 worker=4
 device=1 ticks=1285`. First scheduler: **sched=7 selections=1337 prev=10
next=12 current=12/kworker/u4:0**. Header identifies CPU0/PID12 and workqueue
`events_power_efficient`. This is the intentional timer/softirq watchdog dump,
not a panic; it occurs before the final device-2 boundary.

Readable symbolic frames/offsets from the detailed photo:

```text
show_stack+0x18/0x24 (C)
dump_stack_lvl+0x60/0x80
dump_stack+0x18/0x24
ilinux_probe_watchdog+0xe8/0xf0
call_timer_fn.isra.0+0x24/0x80
__run_timers+0x218/0x260
run_timer_softirq+0x8c/0x100
handle_softirqs+0xfc/0x240
__do_softirq+0x14/0x20
____do_softirq+0x10/0x20
call_on_irq_stack+0x30/0x48
do_softirq_own_stack+0x1c/0x40
__irq_exit_rcu+0xd4/0x10c
irq_exit_rcu+0x10/0x1c
```

Lower frames are overlapped by the panel; partial names/offsets are not filled
in from expected code. This is not a proven stack of the final main-controller
B73 operation.

Later visible text: **phase=5 worker=4 device=2 ticks=2565** and
**selections=2620 prev=10 next=38 current=38/kworker/u4:1**. The later heartbeat
and scheduler prefixes are obscured; panel H02/S09 are observed separately.
Panel H changes 00→01→02; no H03+ observed. H is kernel watchdog activity,
not diagnostic userspace liveness.

## Evidence coverage and limits

* Reviewed local **IMG_2663.mov**, **40.163333 seconds**, oriented **720×1280**.
  Paused samples at **0, 5, 10, 15, 18, 20, 22, 25, 30, 40.013333 seconds**,
  with enlarged panel crops. First samples show proxy, 10 seconds shows Linux
  initcalls, and final samples show the stopped B73 panel.
* Reviewed **IMG_2664.jpeg**, original oriented **4284×5712**, with diagnostic
  and stack crops. It resolves timer/phase/GPIO/count/return/stack details.
* Sampled review, not exhaustive frame analysis. The clip does not cover 60/90
  seconds or the full 120-second handoff window; a still photo adds no duration
  evidence. First kernel line, rectangle count and `console_setup` remain
  unobserved. Earlier transient GPIO stages may have passed between samples.
* **PID 1 / userspace online_cpus=1 / 60-second userspace liveness NOT OBSERVED**.
  No explicit panic observed. Human confirms return but did not separately
  describe changes after the photo; later screen changes remain unreported.
* Full media stays in its original local location, outside Git/workspace.
  Temporary review images are removed after review. No unique identifiers,
  raw ADT/register/memory dumps, serial paths or proprietary binaries committed.

## Outcome and next handoff

The new instrumentation narrows the last main-GPIO boundary from attempt 11's
platform callback B63 to **B73 register-cache initialization**. The first GPIO
instance visibly completed the new IRQ handoff and returned 0. The exact
blocked instruction/register, locking/IRQ behavior and cause remain **Unknown**.
Do not claim the proposed repair fixed the main controller or that IRQ storm
was proven. M5 can inspect the exact cache initialization path offline using
this boundary and the source/build evidence.

**Macintosh HD return: human-confirmed PASS.** Post-attempt-12 policy/default:
**NOT CHECKED**; M5's next read-only return review remains useful. Installed
boot021/client pin preserved; no reinstall, settings/volume changes, automatic
retry, new skip or additional live USB call. Attempt 12 is consumed. A new
attempt requires updated instructions and human start. Native diagnostic
userspace still gates Linux-side control/input and Omarchy configuration.

## Retained audit hashes

The ignored result also retains payload and receipt hashes. Source/procedure
hashes at invocation:

| Path | SHA-256 |
|---|---|
| `native/boot/launch.py` | `c2d2cd0b067b78ead957463e70f8c4694cdeee5dc5b7b54bd6ebf2b7f7fc0279` |
| `native/boot/entry_guard.py` | `d1fa8ca84aa1c7032c50c8766c8571054047720df35cb7d518310167ec183713` |
| `native/boot/dapf_guard.py` | `bb33d9bebcec3a6cd925ed9e7b28dbabe3c7375c445d7e9d68ace18f4eaa7047` |
| `native/boot/fdt.py` | `d9522761837e78f7b444b936a7501fc9f847697d783b57de1f446a4b8da32b6b` |
| `tools/m1n1-client/usb_identity.py` | `72cc8c2a916b8964b2e4b5afc4c1aac22fe8031a2c2f8658df6882b063a47137` |
| `native/boot/package-manifest.json` | `d1da1efcf33e0139ea2ea40555fda1f516d7f0c4407fc1ee2feddfc71998b53c` |
| `tools/m1n1-client/stage-b-instructions.md` | `add17d4f763868433fad0e905cbb8c9caa9dc7ed949d1f745959d780c55269a1` |
| `kernel/native-enablement/boot-entry-setup.md` | `8be28ddf0246bff2abac93f67f5b6aa09eb6a4940ecf62a875a12b924681833f` |
| `kernel/experiments/probe-path/README.md` | `8762fcb9a2506d11f75dfc97f285aa191b5dc84a5273a75283d63f1fe726fe78` |
| `kernel/experiments/probe-path/evidence.json` | `55d0e968c597b76933a0f034b527c3e8b9845703a79d3d0fd0b629746a9a5b47` |
| `kernel/experiments/probe-path/validation.json` | `c1fee395446f201e0b627f0c346102063fa4005e9e034bd811ad51bc216fb7bc` |
| `kernel/experiments/probe-path/decode.py` | `61c51b18de1c9a1eb6b617fcbaad0d9e6ac39fbe316c3c9fabcd81d3417e0c1e` |
| `kernel/experiments/probe-path/device-identities.json` | `4bb4f3d0a1cf7fcd79a99729af1c342c63bc16e2e397cca2f15aa566be490e2e` |
| `kernel/experiments/probe-path/phases.json` | `eface9574f26594da7a6b9223c268e43e6c1bb6fe61c5c155ae273bac6cdfbc2` |
| `kernel/experiments/gpio-handoff/apply.py` | `8f044fb90c102b1ebb92c1e938150f5fc9a690e5f1a2dce3ae5c8c66c61fe5ef` |
| `kernel/experiments/gpio-handoff/irq-init.h` | `95e3a842570f34e5bd905d9530e31af2f0c69c360b3452df4a791c74ee7982e6` |
| `kernel/experiments/gpio-handoff/test_irq.c` | `f4b32632649493dec2fba6496f59e5945940cca6e2457433ecd7f8754374f07c` |
| `kernel/experiments/gpio-handoff/test_geometry.c` | `4be6d8fec9e7fac45254d662c95825152709061b9179bb74ffad8065d498de6a` |
| `virtualization/jobs/031-gpio-handoff/run.sh` | `4eabe94160c5d1b9e971290bf2c7c6e0c51ab744e06dbecd014ac4b191c52a24` |
| `kernel/experiments/gpio-handoff/README.md` | `f875454f97fdf89e1714671eb889f8d21da50e64d16753156346911dcc528092` |
| `kernel/experiments/gpio-handoff/validation.json` | `5b6a78cb90919775e27d67dc129a7fa3654306b94006b6836d8cef046184aa1f` |
| `kernel/experiments/gpio-handoff/linux-evidence.json` | `afd77223c5e29c518f51624507e8bd6cc07f68c8fae49b9bf1abc4b54336ed02` |
| `kernel/experiments/gpio-handoff/apple-evidence.json` | `978608fa20e3d74ccbd0d795568cc043abd839e6533e678aadbb0a3aa612d27d` |

Sanitized local wrapper SHA-256: `97fda6825830c6cbd4de6d430b1c62a476cf22e47830338f3ab080766faca3eb`.

## M5 follow-up after this report — 2026-10-14

The user supplied fresh read-only policy JSON: original Full/lab Permissive,
both exit 0. M5 independently checked original root/build/FileVault/SIP and
unchanged staged m1n1. This supersedes the pending policy/return check above;
default/installed boot object/authenticated-root were not independently
re-queried. No host settings changed. Boot032 candidate work and attempt-13
handoff are in `kernel/experiments/gpio-reserved/README.md` and the current
Stage-B checklist. Attempt 12 remains consumed; do not replay its command.
