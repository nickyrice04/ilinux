# Boot031: bounded GPIO cache and interrupt handover on t6050

Attempt 11 (`f35efa5`) supplies the first decoded device-specific boundary:
`P05 S09 W04 H02 D0059 B63 C0059`. D/C identify `/soc/pinctrl@29c000000`.
The earlier `/soc/pinctrl@2881e4000` returned 0. This is **observed callback
entry**, not an exact blocked PC. The first watchdog's kdevtmpfs stack is not
attributed to that final callback. Native PID 1/liveness remain unobserved.

## Findings and decisions

* **Confirmed, static:** the retained boot030 Apple GPIO driver reads 512 pin
  defaults irrespective of `apple,npins`. The public/sanitized DT identifies
  NUB=61, AOP=85, AP=221; their resource addresses, lengths and seven interrupt
  routes agree with the saved hardware inventory. Reading undeclared pin
  registers is unnecessary. Whether one causes this native stall is unknown.
* **Confirmed, static:** the driver has no `gpio_irq_chip.init_hw` hook. Gpiolib
  supports that hook before creating/enabling chained parent IRQs. The existing
  GPIO handler calls `generic_handle_domain_irq` without handling an unmapped
  result; its ACK is in the mapped child's flow. An inherited pending source
  can therefore remain asserted before a child exists. An actual IRQ storm on
  this Mac is a **hypothesis**, not measured evidence.
* **REA + independent instructions:** the exact Linux probe/IRQ objects cover
  392 instruction words, no REA omissions. 331 nonrelocated words match the
  linked boot030 Image; 61 relocation words have separate GNU relocation/target
  inspection. AppleGPIOICController's two selected routines cover another 222
  words, checked against original carrier bytes and Apple LLVM.
* **Decompiler limitation:** Apple's `initPinsAndGroups` pseudocode crosses
  into the following function (9 p-code operations at three outside addresses).
  Its whole-function pseudocode is **rejected**. Independently bounded ARM64
  instructions at +0x12c/+0x148 and +0x15c/+0x1b4–0x1e4 establish a pin-count-
  bounded status-word loop writing all ones at base+0x800+group*0x40+word*4.
  Those addresses lie inside the verified 564-byte body. They corroborate the
  existing Linux ACK layout; they do not establish every Apple initialization
  step or resolve external calls. The separate masking routine's verified
  +0xf4–0x108 instructions clear bits 3:1, update its cache and write the pin
  register. Linux already defines this field; this change uses Linux's existing
  IRQ-off mode 7, **not** Apple's observed mode 0. No proprietary implementation
  or pseudocode is copied into Linux or Git.

## Original Linux change

`apply.py` requires the exact retained driver digest before edits. It installs
`irq-init.h`; `driver.patch` is its reviewable driver delta (apply.py also copies
that header). Functional changes apply only to `apple,t6050-pinctrl`:

1. Check 1–512 declared pins, at most seven parents, and sufficient MMIO resource
   length before register access. Cache exactly the declared pin registers;
   legacy compatibles retain the original cache configuration.
2. Register an `init_hw` callback. Before parents are enabled, change only the
   mode field of inherited interrupt-input modes 2–6 to Linux IRQ-off mode 7.
   Outputs and already-disabled modes, mux/pull/group/data/pad fields stay as
   read. Errors propagate. A locked active pin returns EPERM; it is never
   overridden. Read back changed modes from MMIO rather than trusting the cache.
3. After all active inputs are masked, clear valid pending bits using the
   driver's existing W1C ACK layout. Final partial words exclude nonexistent
   pins. Later normal Linux IRQ startup still selects/enables requested lines.

Failures can leave earlier input IRQs masked; no parent is enabled by this
callback on error. Device registration then fails visibly. That is a failure,
not functional peripheral support. No new driver/initcall skip is added.

Seventeen B markers (70–7B, 80–84) distinguish mapping/cache, pinctrl registration,
groups, GPIO registration and IRQ initialization. D/C IDs remain unchanged.
They use the existing opt-in, task-gated panel. There is no IRQ-handler logging
or new MMIO probe solely for diagnostics. Rendering perturbs timing, so this
build is unsuitable for performance/energy claims.

## Validation and reproduction

`virtualization/jobs/031-gpio-handoff/run.sh` copies retained boot030 inside the
existing build VM, applies the digest-pinned change, tests the actual installed
IRQ helper and extracted geometry/config block with ASan/UBSan, then links the
full Image and compares an ELF-to-binary roundtrip. See `validation.json` for
actual outputs, toolchain, hashes and limitations. The one-CPU diskless generic
VM checks kernel/userspace integration, **not t6050 GPIO hardware**.

Regression fixtures cover 1/31/32/33/61/85/221/512 pins, partial W1C words,
field preservation, a simulated pending-parent condition, read/write/readback
failures, a locked active pin, invalid geometry/resources and unchanged legacy
configuration. They reproduce the old cache over-read and uncleared status.
No claim that these synthetic conditions were observed on the physical Mac.

`audit-linux.py` replays exact ELF/REA/LLVM/Image comparison against retained
local artifacts. `audit-apple.py` replays source-carrier/derived-member/LLVM
checks using `apple-plan.json`; raw inputs and full decompilation stay ignored.
`apple-evidence.json` deliberately retains the rejected pseudocode gate.

Only RAM **Image** changes in boot031. Preserve installed boot021/client pin,
DT, args, initramfs, config, single CPU and all existing hardware gates. The next
step is one filmed attempt 12 under `tools/m1n1-client/stage-b-instructions.md`.
Capture the IRQ handoff counts, probe return/errors, D/C/B and later userspace.
A successful diagnostic boot precedes Linux-side input/control and Omarchy.

Public foundations: [Asahi GPIO documentation](https://asahilinux.org/docs/hw/soc/gpio/)
and [Asahi GPIO driver](https://github.com/AsahiLinux/linux/blob/asahi/drivers/pinctrl/pinctrl-apple-gpio.c).
The local digest-pinned source, not changing online branch contents, governs this build.
