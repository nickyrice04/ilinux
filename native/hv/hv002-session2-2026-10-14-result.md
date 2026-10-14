# hv002 Session 2: chainload hands off, hv002 never starts

2026-10-14 · M1. One RAM session after census v2 PASS (`d4a0607`; M5 handoff
`6e58ccd`). Private tooling: not for upstream.

**Hypervisor and guest: NOT STARTED. Cause: unknown.**

## Execution (terminal B, one invocation)

Terminal B ran `hv_launch.py --launch` once. The vUART logger in terminal A
opened interface 3 under boot021 first.

In order, the launcher printed:

* `Package PASS: boot033 guest and hv002 m1n1 match their manifests.` and
  `Mode: LIVE HV RAM LAUNCH`, with the expected HV bootargs.
* `Target PASS: t6050, installed boot021, no started secondaries.`
* `Register preflight PASS: ECV present; HV start/exception/FIQ registers readable.`
* The ADT fetch, boot-blob copies (SEPFW, SEPPatches, uStuff, preoslog,
  RTBuddySeg, TrustCache), then `Pushing ADT (755924 bytes)`.
* boot021 m1n1: `Preparing to run next stage at 0x10010db8240...`; the
  chainload `reload()` follows.
* `Waiting for reconnection...` for about 80 s (about 23:00:40 to 23:01:45
  UTC), then **`STOP: UartTimeout Reconnection timed out`**.

The vUART logger reported `vUART disconnected` at the chainload and never saw
the interface again; its log is empty. After the stop, `/dev/cu.usbmodem*`
showed **no m1n1 USB device** on the M1. No events log was created. Both tabs
were closed and nothing was retried.

## Screen (human report; video captured nothing further)

As soon as the session ran, the M5 went to a **black screen with the Apple
logo** and stayed there until powered off. It did not show the macOS progress
bar or login screen as in attempt 14's reset.

## Interpretation (bounded)

* **Confirmed:** the launcher's chainload preparation completed. On the boot021
  side, the next-stage path started (`Preparing to run next stage`).
* **Likely, from the pinned `src/main.c:194-214` sequence:**
  * boot021 then ran its handoff shutdown: `nvme_shutdown`,
    `exception_shutdown`, `usb_iodev_shutdown`, `display_shutdown`,
    `fb_shutdown(restore_logo)` (which restores the iBoot Apple logo seen on
    screen), `mmu_shutdown`;
  * then it jumped through the copy stub to hv002 at `base + 0x800`.
  * The same shutdown sequence handed off to Linux successfully in
    attempt 14.
* **Likely:** hv002 stopped **before its framebuffer init**. A running m1n1
  replaces the restored logo early in `m1n1_main` (`src/main.c:136-189`). The
  window covers `start.S` relocation, `firmware_init`, `heapblock_init`,
  `gxf_init` if supported, `mcc_init`, `mmu_init`, `aic_init`, `smp_init`,
  `wdt_disable`, `pmgr_init` and `display_init`. USB init comes later, so no
  USB is consistent with this.
* **Not established:** whether this is the chainload mechanism or early m1n1
  re-initialization on t6050 in general, or something specific to the hv002
  build. Nothing hv002 changes (HV/kboot/proxy-op code) runs before USB comes
  up, so a general second-m1n1-start problem is at least as likely.

## Suggested next steps for M5 (no live action taken)

1. **Discriminating test (one short session, no Linux).** Chainload the stock
   boot021 `m1n1.bin` (bit-identical to the installed object) through the
   same launcher chainload code. If it also never returns, the problem is
   chainload or early re-init on t6050, not hv002.
2. **Early visibility.** A private debug build could paint progress codes
   straight to the framebuffer from early `m1n1_main` (the Linux panel trick),
   so the next hang names its step.
3. **Offline checks of the chainload inputs:**
   * the round-trip of boot_args and the pushed ADT on this iBoot revision;
   * MCC/PMGR/AIC re-initialization on M4-class locked sysregs after a first
     m1n1 has run;
   * whether upstream has verified chainload on M4/M5.

## Return

The human reports the M5 froze at the Apple logo, was powered off, and the
human confirms the return to Macintosh HD. Fresh policy/default checks:
**NOT CHECKED**. Logs stay local in ignored `build/native-intake/`.
