# Progress Log

Newest first. Each milestone lists: discovered, implemented, tested,
measured, still unsupported, and next.

---

## 2026-10-16 · M1: MTP E1 probe stopped on a NameError before touching the M5

* **E1 session 1 stopped before any device contact.** Human-started proxy; the
  probe was invoked once at **18:18:00 UTC** (HEAD `9a3e002`) and printed
  `STOP: NameError name 'M1N1Proxy' is not defined`, exit 1. **No serial port
  was opened and no request was sent to the M5**: the error is raised while the
  probe builds its API object, before `open_primary`. `mtp-probe.txt` holds only
  the pin-check line and the STOP line; no JSON was written.
* **Cause (Confirmed, reproduced in isolation under the client's Python 3.9.6):**
  `mtp_probe.py:426` has `M1N1Proxy = staticmethod(M1N1Proxy)` inside class `Api`,
  nested in `connect_and_run`, where `M1N1Proxy` is a function-local import
  (line 418). A class body that assigns a name resolves the right-hand side in
  class, global and builtin scope only, so the enclosing function's import is not
  visible. The same shape is at `native/probe/pmgr_probe.py:808-809` (`M1N1Proxy`
  and `load_adt`): **the PMGR probe would stop the same way.** No other tracked
  file has it.
* **Why the tests passed:** neither suite builds that class. The PMGR test
  exits earlier at the m1n1 pin check, and the E1 tests never call
  `connect_and_run`.
* **Suggested fix (M5-owned code; not applied by M1):** alias before the class
  (`_proxy_cls = M1N1Proxy`, then `M1N1Proxy = staticmethod(_proxy_cls)`, and the
  same for `load_adt`), or build the API with `types.SimpleNamespace`; add an
  offline test that runs `connect_and_run` through the API construction with
  the real `m1n1.proxy` imports and a stub transport.
* **M1 did not edit the probe or retry.** E1's approval covers the reviewed
  probe and the procedure says stop on any `STOP:` line. A rerun needs M5's
  patch, M1's re-verification and the human's go. The M5 stays at
  `Running proxy...` at the human's discretion; nothing needs cleaning up.
  Attempt 17 is unaffected (its launcher path is separate and was exercised
  live in attempts 14-16).


## 2026-10-16 · M1: MTP E1 probe and boot036 attempt 17 offline readiness PASS

* Pulled `0363bd5` (13 commits). Both items are queued in `coordination.md`:
  E1 (read-only, human-started, no retries, E1 only) and attempt 17 (no
  network-settings change on the M1). Order: **E1 first, then attempt 17**, as
  two separate human-started lab boots.

**MTP E1 read-only register probe** (`kernel/experiments/mtp-input/m1-instructions.md`)
* E0 offline PASS: `test_mtp_probe.py` Ran **26** tests OK; `mtp_probe.py plan`
  `PLAN: 66 reads, all 32-bit, none with a side effect; nothing was written`;
  `read --help` rc 0 under the pinned client.
* **M1 independent review:** the probe's proxy wrapper exposes only `read32`
  inside ADT-declared regions (any other attribute raises `Forbidden`); the code
  calls only `read32`, `faulted`, `get_exc_count`, `get_bootargs_rev` and
  read-only memory fetches; no write, mask, call, reload or chainload anywhere;
  it reuses `pmgr_probe`'s gates (USB identity, chip t6050, boot021 marker, no
  secondaries), needs `--confirm MTP-PROBE-J716C-READ`, and refuses an existing
  JSON output file.
* **Residual risk, not removed by reading:** a read of an unpowered block could
  raise an asynchronous SError that hangs m1n1. Recovery is a power-off; the
  probe writes nothing persistent.
* Record: ignored `build/native-intake/results/mtp-probe-readiness.json`.

**Attempt 17 / boot036 (USB control channel)**
* Archive **18,902,541 bytes**, SHA-256
  `f09a00000925aea64a6ea7ab6dace05958d779d2367fc6aec233becc58ca71a3`, verified
  against Git before extraction; 14 regular members, no absolute or parent
  paths. **13-file intake and offline launcher PASS.**
* **102 reviewed M1 cases PASS** (37+10+6+16+5+19+2+6+1). Boot036 suites:
  `test_ramroot` 30 PASS; `test_usb_dt` 6 tests (all 6 skipped), `test_control_channel`
  6 (1 skipped), `test_kconfig_guard` 7 (1 skipped): the skips are the
  real-package cases that need the M5's build directories, as the checklist says.
* Payload: Image `e0e53113…f3f7` (44,681,728 B), Stage-B DT `a676087b…efa5`,
  Stage-B initramfs `5f4b478b…b248` (2,392,627 B), SHA256SUMS `4fbd64d4…442f`.
  Client pinned clean at `57a9339`; installed boot021 unchanged.
* **Controller:** `launch.py` `4d55f0c9…840b` matches; the other five digests are
  unchanged. M1 read the `9ee6b2f` diff: the default `stage-b` profile behaves
  as in attempt 16 (initramfs, fixed arguments, confirmation string, 180 s
  deadline, append check); the `ramroot` profile is new code attempt 17 does
  not use.
* **M1 independent package review** (because it adds a network-reachable SSH
  server to the M5):
  * DT versus boot035: 358 to 361 nodes; exactly three `snps,dwc3` controllers
    added, three USB DARTs enabled, **39** power domains disabled (13 each for
    `atc0`-`atc2`); nothing else changed.
  * initramfs: `/init` is built from the committed `init.c`; dropbear (Arch Linux
    ARM 2026.94-1) starts with `-F -E -s -R -j -k -K 15 -p 22` (no password
    logins, no port forwarding); root's password is locked (`*`);
    `root/.ssh/authorized_keys` is **byte-identical to the M1 public key**
    (`SHA256:o7wtpNY0RUOIIGTyIJvspZFOetYFFG2oeMw5ecZc3yI`), one line, no other
    key; `/init` strings show IPv6 link-local only, no DHCP or `ifconfig`.
  * The checklist's key grep prints the M1 key; the private half is present at
    mode 600.
* **Wrapper note:** `launch.py` now formats `Board/framebuffer PASS; allocating
  RAM for … payloads.`, so a literal-print scan would drop that checkpoint.
  `run-attempt17.py` adds it explicitly (checked against all 16 attempt-16
  checkpoints), saves each record with `fsync`, and prints a 10-minute deadline.
* Records: ignored `build/native-intake/receipts/boot036-attempt17.json`,
  `…/results/boot036-stage-b-attempt17.json`, `…/run-attempt17.py`.

**Live checks NOT RUN for either item.** Before attempt 17 the M1 should be
restarted fresh and kept awake with `caffeinate -i`; `ifconfig -l` is recorded
immediately before the handoff; the original video file (AirDrop or cable, not
Messages) is needed. No M1 network setting changes; if the new interface has no
`inet6` address M1 stops and asks.


## 2026-10-15 · M5: MTP keyboard/trackpad input path analysed from macOS; ring transport prepared offline (hardware NOT RUN)

* **Discovered** (REA on this Mac's kernelcache + read-only `ioreg`; labelled in
  `kernel/experiments/mtp-input/README.md`):
  * M4/M5 firmware delivers device→host HID reports through one 2 MiB
    shared-memory ring registered with `{0xC1,2}` then `{0x91,0,0,iova,size}`
    100 ms after the first DockChannel bytes; host→device stays on the
    DockChannel FIFO; same 8-byte-header/word-checksum framing. Doorbell content,
    DART SID and register base are Unknown.
  * The keyboard needs no firmware; the STM image is an update program only
    (`needsFirmwareAtBoot() == 0`).
  * The trackpad image is `J716c_Multitouch.im4p` (XML OSObject graph, CBOR-encoded
    by macOS with 0xd3 alignment tags); it also needs an SMC function
    (`function-afe-reset`) that t6050 Linux lacks: the trackpad blocker.
* **Implemented** (untracked, nothing committed): `kernel/experiments/mtp-input/`
  (README, design, DT delta, config delta, `patches/0002` ring-transport patch,
  firmware converter, read-only m1n1-proxy probe, M1 instructions);
  `virtualization/jobs/042-mtp-input/` (kernel-side checks).
* **Tested (offline):** ring core 54,871 checks; the real patched driver against a
  firmware model 39,483 checks (ASan/UBSan, clang and gcc); converter 27 tests;
  probe 26 tests; 12/28/19/16 mutants caught. VM job 042 on the boot036 tree:
  0001+0002 apply, driver compiles with `W=1` and no warning, Image links with
  the new symbols and is reproducible (`6fb8c371…`).
* **Not verified:** everything on the M5; that the firmware behaves like the model;
  byte equality of the converted trackpad image with macOS.
* **Next:** the user approved queueing the E1 read-only probe for the M1 agent
  (human-started, no retries; entry in `coordination.md`,
  `kernel/experiments/mtp-input/m1-instructions.md`); the files are committed on
  `main` and reach the M1 with `git pull --ff-only`. A boot037 package needs the exact
  DT-delta rule in `native/boot/make-package.py` (a separate offline proposal
  was started).

## 2026-10-15 · M5: boot036 rebuilt with the M1's key; attempt-17 handoff prepared (NOT RUN)

* **Implemented:**
  * boot036 rebuilt by job 041 with the M1's public key (`a6717b0`,
    `SHA256:o7wtpNY0…`). The shipped initramfs authorizes exactly that key; the
    VM self-test overlay authorizes its own test key, for test boots only.
  * Job 041 now pins the kernel's build time, user and host. Two builds gave
    the same Image (`e0e53113…`), so the RAM root can pin boot036's kernel.
  * The attempt-17 checklist (`tools/m1n1-client/stage-b-instructions.md`) and
    the handoff records in `native/boot/` now point at boot036.
* **Tested:**
  * Package `ilinux-j716c-boot036` (18,902,541 bytes, SHA-256 `f09a0000…71a3`):
    exact delta and kernel.config-provenance checks PASS.
  * The committed launcher (`65ece253…`, unchanged) verifies it offline.
  * Generic-VM liveness and the dummy_hcd USB self-test were rerun on these
    exact outputs (see the report).
* **Not verified:** everything native.
* **Next:** publish `native-j716c-boot036` (user approval), M1 readiness, one
  human-started attempt 17 reached over SSH.

## 2026-10-15 · M1: control key published for boot036; macOS EEM driver checked

* **Public key published** for boot036's USB gadget: commit `a6717b0` adds only
  `kernel/experiments/usb-gadget/authorized_keys` (one line, ed25519, comment
  `ilinux-m1-control`). Fingerprint for M5 to confirm:
  `SHA256:o7wtpNY0RUOIIGTyIJvspZFOetYFFG2oeMw5ecZc3yI`.
* **Private half** is `build/control/m1-control` (mode 600, git-ignored, not
  tracked; the folder carries no iCloud sync markers). It was created without a
  passphrase, as requested, and stays on this Mac. `kernel/experiments/
  usb-gadget/` did not exist before this commit; M5 gets it on its next pull.
* **Read-only M1 facts for M5:**
  * `sw_vers`: macOS **26.0.1**, build **25A362**.
  * `/System/Library/Extensions/AppleUSBEEM.kext`: `CFBundleVersion` **5.0.0**;
    `bInterfaceClass` **2**, `bInterfaceSubClass` **12**, `bInterfaceProtocol`
    **7**. This is exactly the expected CDC-EEM triple, so the built-in driver
    can bind a gadget that presents it.
* **Not done and not authorized:** no network, sharing or security setting was
  changed; no interface exists yet (boot036 NOT RUN). If a new network
  interface appears, M1 will not alter network settings without the human's
  approval; prefer addressing that needs no system configuration change.
* **Host precautions retained** from attempt 15 (the M1 panicked in the
  CDC-ACM serial driver, a different USB driver): fresh restart, `caffeinate
  -i`, durable `fsync` records. A panic in the EEM path is not ruled out.
* **Next:** M5 builds boot036 with this key; M1 then runs offline intake and
  publishes readiness before any live attempt.


## 2026-10-15 · M1: attempt 16 runs the whole ladder, alive >= 108 s; first stable native baseline

* One boot035 RAM attempt at readiness `7a37fb6`, M5 handoff `4debc28`.
  **Controller exit 0, 10.493 s**; handoff 2026-10-15T20:28:25.611598Z. All gates
  PASS. **No M1 host panic** (uptime continuous since 11:09 EDT, no new panic
  report).
* **First stable native baseline.** PID 1 alive, one CPU, `online_cpus=1`
  heartbeats 000-021 every 5.0 s to kernel 108.4 s; `60s elapsed; still alive`
  at 63.36 s. Clip (120.5 s, 320x568) ends at kernel ~110.7 s, no restart.
* **Release ladder completed:** first release 19.43 s (`atc?_usb_aon`, **no
  `smc_i2cm`**), step 11 `atc?_common_dp_3` at 24.55 s passed,
  `ladder complete: 74 domains released` at 57.31 s (M5 had predicted 145; only
  74 were powered on at boot). A `dispext*` domain was released and the console
  kept rendering.
* **Refuted:** attempt 15's step-17-immediate explanation. **Not separated:**
  SMC domains versus the M1's post-panic reset for attempt 15's second reset,
  because this run changed both (SMC nodes removed, no M1 panic). Attempt 14
  (no M1 event) still needs the SMC or simultaneity explanation.
* Domain-name digits and the panel/GPIO lines were not readable at this
  resolution. User reports no M5 or M1 crash afterwards (not filmed).
* Fresh policy/default NOT CHECKED. No retry or settings change. Report:
  `native/boot/stage-b-2026-10-15-attempt16-result.md`.


## 2026-10-15 · M1: boot035 attempt 16 offline readiness PASS

* Pulled/read M5 handoff `4debc28` (boot035 / attempt 16; published as
  `9815dd7`), the Stage-B checklist and `native/boot/attempt15-review-2026-10-15.md`.
  Archive **16,723,179 bytes**, SHA-256
  `81cbbd1ca09ec53bbfe8f616e578c07d7f878a26a7629c2d1de40d969be966e7`, verified
  against Git before extraction; 14 regular members, no absolute or parent paths.
  **13-file intake and offline launcher PASS.**
* **102 M1 offline cases PASS** (37+10+6+16+5+19+2+6+1), all exit 0; synthetic
  transport only. Image SHA-256 unchanged from boot034
  `1131a1af5e4d5cfa3206c5eb0afe1a6d72d86a2761a8d906b592e33556882579`; Stage-B DT
  `b1105bbf2c207c8c816c4b9cc0231ecc1d49543e05fe4b772bcb153019e186db`;
  SHA256SUMS `7635c5e4a25b051fa933ad969e2407c3f6a63cea876570f58052a474cf162f8d`.
* **M1 independent DT diff (boot034 vs boot035):** 365 -> 358 nodes; exactly
  `smc_i2cm0`-`6` (`power-controller@8028`-`@8058`) removed; none added; no
  property changed on any surviving node; nothing references the removed nodes;
  188 -> 181 pwrstate domains; GPIO reserved ranges kept. Image, initramfs, m1n1
  and config identical to boot034. All six controller digests match; client
  pinned clean at `57a9339`; installed boot021 unchanged.
* Ignored receipt `build/native-intake/receipts/boot035-attempt16.json`, record
  `build/native-intake/results/boot035-stage-b-attempt16.json` and wrapper
  `build/native-intake/run-attempt16.py` retain the hashes. The wrapper differs
  from attempt 15's only in names and an `fsync` after every record save, so a
  host crash cannot lose checkpoints again.
* **Reading of the experiment:** survives the whole ladder (about 94 s) and
  stays alive to 180 s -> SMC domains were the trigger, and the attempt-15 host
  reset was not. Reset again -> record the step ~5.6 s earlier. If the M1
  panics again at handoff the run is still informative: a surviving M5 refutes
  the host-reset explanation.
* **Ready for Stage B attempt 16** after publication. Human plans portrait
  framing filling the frame vertically, phone fixed. **Native boot035 and live
  checks NOT RUN at readiness.** hv003 and the PMGR probe remain unchecked by M1.
* Next: M1 freshly restarted and kept awake with `caffeinate -i`; one filmed RAM
  launch; film to reset or **180 s from handoff** (the ladder alone runs to
  ~94 s); then Macintosh HD. No retry/reinstall/settings/volume change.

## 2026-10-15 · M5: kernel.config provenance gap in boot024–035 found and guarded

Packages boot024–035 shipped job 020's `kernel.config`. Their Images embed
(IKCONFIG) a config that differs in 8 rustc-detection lines and no option.
boot021, boot022 and boot036 match. `make-package.py` now refuses a
`kernel.config` that is not the Image's own (`native/boot/kconfig_guard.py`,
7 tests). Details: `native/boot/kernel-config-provenance-2026-10-15.md`.

## 2026-10-15 · M5: boot036 USB control channel prepared offline (native NOT RUN, not published)

* **Discovered:**
  * macOS 26.6.2 ships `AppleUSBEEM.kext` (interface 2/12/7). All three usb-drd
    ports carry `ncm-interrupt-ep-disabled`, and omarchy-m5's NCM stalled on its
    interrupt endpoint, so the gadget is CDC-EEM (bulk only).
  * m1n1's own gadget uses DART instance 1, stream 1, and leaves the ATC, DART and
    DRD domains and the USB2 PHY on. Linux's pwrstate probe would arm
    AUTO_ENABLE on those domains and the boot034 ladder would release them.
  * The `kernel.config` shipped since boot024 is job 020's: it differs from the
    config that built boot024–035 in 8 rustc-detection lines, no real option.
* **Implemented:** `kernel/experiments/usb-gadget/` (init with one EEM gadget per
  UDC, key-only dropbear and per-heartbeat port status; DT builder; initramfs
  staging; VM self-test). Also:
  * the `native/boot/usb_dt.py` and `control_channel.py` contracts;
  * `make-package.py` boot036 with exact checks and `--record-dir`;
  * VM job 041;
  * the `tools/vm-job.sh` lock fix: a held lock no longer lets a second VM start.
* **Tested:**
  * 12 contract tests pass, rejecting 19 DT, 16 initramfs and 12 config deviations.
  * Job 041: the config delta is exactly the 14 gadget symbols, m to y.
  * The DT is byte-identical from the VM and the Mac, and schema-clean.
  * All 9 shipped packages are signature-validated, and 22/22 ELF files are
    16 KiB-safe.
  * Package `ilinux-j716c-boot036` (SHA-256 `521ffd6d…`): the unchanged
    launcher's offline check passes.
  * Generic VM: liveness PASS. The dummy_hcd self-test PASS: EEM enumeration,
    ping, SSH with the key, refusal without it, and an 8 MiB copy intact.
* **Measured:** the initramfs is 2.39 MB (+2.09 MB, about +0.5 s over the proxy);
  the Image grew by 80 KiB.
* **Not verified:** everything native. That includes the dwc3 probe on m1n1's
  PHY state, one DART instance being enough, and macOS binding EEM.
* **Next:** attempt 16 (boot035) first. Then the user's SSH-key decision, a
  rebuild if attempt 16 changes the DT, publication, and attempt 17
  (`tools/m1n1-client/control-channel-draft.md`). Report:
  `native/boot/boot036-control-channel-2026-10-15.md`.

## 2026-10-15 · M5: boot035 removes the SMC-owned power domains (attempt 16 NOT RUN)

* **Discovered:**
  * No Asahi PMGR DT (t8103, t600x, t602x, t8112, t6030, t8122) exposes any
    `smc_*` domain; our ADT-generated t6050 draft carried `smc_i2cm0`–`6`.
  * In the real t6050 table every other SMC-island domain is virtual; the seven
    I2C masters are the only AP-writable ones and have no consumer.
  * The reset lag matches: attempt 14 5.55–5.69 s after the bulk power-off,
    attempt 15 5.70–5.88 s after the last SMC release (Likely mechanism: the SMC
    resets the SoC after losing an I2C master).
  * Asahi's simple-framebuffer nodes claim the display coprocessor's domain; ours
    claims none (`disp_cpu`, `disp_adma` unclaimed). Noted, not changed.
  * The pinned m1n1 already carries the M4-era WFI, CTRR and secondary-watchdog
    fixes; this M5 reports `wdt-version = 3`, so m1n1 disarms both watchdogs.
* **Implemented:** VM job 038; `make-package.py` boot035 with an exact DT-delta
  check; `boot034-package-manifest.json` retained; attempt-16 checklist; review
  and roadmap (`roadmap.md` Phase 3 is now the path to a native Omarchy boot).
* **Tested:** seven nodes removed and nothing else (decompiled diff), schema
  clean, the packager's guard refuses an unchanged DT, offline launcher
  verification PASS, all repository suites PASS except the five that need the
  M1 client venv.
* **Not verified:** everything native; whether the SMC mechanism is right.
* **Next:** publish `native-j716c-boot035` (user approval), M1 readiness, one
  filmed attempt 16 to 180 s. Optional: PMGR probe on one `SMC_I2CMn`.

## 2026-10-15 · M1: attempt 15 outlives the 8.8 s reset, resets at ~27.7 s; M1 panicked at handoff

* One boot034 RAM attempt at readiness `a57837b`, M5 handoff `9499bd0`, started
  2026-10-15T15:08:37.154Z. **The M1 host kernel-panicked at 15:08:47Z, within
  ~0.5 s of the expected handoff** (NULL dereference in Apple's `usb.cdc` driver,
  reached from the launcher's Python process through IOSerialFamily/usb.serial/
  cdc.acm). The controller record stops at "Uploading DT, initramfs and kernel";
  later checkpoints and the exit status are **NOT RECORDED**. The M5 nevertheless
  booted Linux from the handoff with the expected GPIO counts.
* `Take15.mov` (49.9 s) reviewed. Kernel `ladder armed` 1.370 s; **sync_state
  kept domains on** at 3.236/3.237 s (call 1.4 ms vs 5.0 ms in attempt 14);
  PID 1 at 3.254 s; heartbeats 000-004 to 23.34 s. Ladder from 19.42 s, one
  release per 0.512 s; **17 releases visible** (six `smc_i2cm*`, then `atc*`
  usb_aon/phymxwrap/usb, then `atc?_common_dp_3` at 27.614 s).
* **Confirmed (single variable):** attempt 14's reset at ~8.77 s did **not**
  recur; Linux ran >= 27.6 s with the sync_state bulk power-off removed.
* **Silent reset at kernel ~27.7-27.85 s**, 0.07-0.24 s after the 17th
  power-off line; no message of any kind; Apple logo, then macOS login (11:09).
  `ladder complete` not reached.
* **Confounded:** candidates are ladder step 6 (`smc_i2cm?`, 21.98 s, +~5.7 s,
  matches attempt 14's 5.55-5.69 s latency but is a weak fit among 17 steps),
  step 17 (immediate), or the **M1's own post-panic hard reset**, which fell in
  the same seconds. Display domains were **not** reached (earlier DT-order
  estimate retracted; the ladder is newest-registered first).
* Video was rotated 90 deg after ~19 s: domain-name digits unreadable.
* Both machines restarted; fresh policy/default NOT CHECKED. No retry or
  settings change. Report: `native/boot/stage-b-2026-10-15-attempt15-result.md`.
  Recommend one clean rerun of unchanged boot034 on a freshly restarted M1.


## 2026-10-15 · M1: boot034 attempt 15 offline readiness PASS

* Pulled/read M5 handoff `9499bd0` (boot034 / attempt 15), the Stage-B checklist
  and `kernel/experiments/genpd-sync-state/`. Archive **16,723,189 bytes**,
  SHA-256 `a856a9b8c6b7fdafeeb68da8dddbc9c82f7e9b5cddf1dc691512f63c0803f5ff`,
  verified against Git before extraction; 14 regular members, no absolute or
  parent paths. **13-file intake and offline launcher PASS.**
* **102 M1 offline cases PASS** (37+10+6+16+5+19+2+6+1), all exit 0; synthetic
  transport only. Image SHA-256
  `1131a1af5e4d5cfa3206c5eb0afe1a6d72d86a2761a8d906b592e33556882579`
  (44,599,808 bytes); Stage-B DT unchanged
  `4b3adee52465b809e9c8a1946b7610c63f1ae3c0b24f7334cd485260da84adce`.
* Versus boot033 only the Image and package-manifest metadata differ. All six
  reviewed controller digests match; client pinned clean at `57a9339`.
  Installed boot021 unchanged.
* **M1 independent review of the Image change:**
  * `apply.py` read in full: both sync_state paths return early under
    `pd_ignore_unused`; one trace line before each real power-off; a bounded
    delayed-work ladder (17 s start, 500 ms step) that releases only
    boot-on, `stay_on`, non-always-on domains, name logged first.
  * `test_genpd.py`: the 2 tests that can run here pass (exact ladder block
    under ASan/UBSan, 5 mutations caught). 3 skip because M1 has no Linux tree
    (by design; M5 ran them in VM job 036).
  * Static count reproduced independently from the Stage-B DT:
    **152** unclaimed, non-always-on domains.
* **Observation for M5 (not a blocker):** the prepared framebuffer node claims
  no power domains, so the ladder also releases the display domains. In DT
  order (estimate; runtime order may differ): `dispext0..3_*` at ~20-34 s
  kernel time and the built-in panel's `disp_adma`/`disp_cpu` at ~49 s. A black
  screen during the ladder is therefore **ambiguous**: a reset is followed by
  the Apple logo and macOS login; a display power-off stays black. M1 will keep
  filming to the 120 s bound either way and report both cases.
* Ignored receipt `build/native-intake/receipts/boot034-attempt15.json`,
  record `build/native-intake/results/boot034-stage-b-attempt15.json` and
  wrapper `build/native-intake/run-attempt15.py` retain the hashes.
* **Ready for Stage B attempt 15** after publication. **Native boot034 and
  live checks NOT RUN at readiness.** hv003 and the PMGR probe are separate
  tracks: M1 offline readiness for them is not yet done.
* Next: one filmed RAM launch; keep filming to reset, `ladder complete` or
  120 s from handoff; then Macintosh HD. No retry/reinstall/settings change.


## 2026-10-14 · M5: proxy-driven PMGR probe built offline (NOT RUN)

* **Discovered:**
  * The real t6050 PMGR table (sanitized ADT export) has 661 device records; CPU
    core domains (`MCPU*`, `PCPU_*`), cluster managers (`MCPM*`, `PCPM`) and
    `AIC*` are ordinary non-critical power-state domains, so the ADT's critical
    flag alone would have let a naive tool power them off.
  * The m1n1 hypervisor's link-essential set (UART0, ATCn_USB, ATCn_USB_AON and
    parents) reproduces from the real table as 19 domains, which the tool never
    cycles.
  * Of the 205 non-critical domains with a register, 33 are `notify_pmp`; the
    accelerator/display "SYS" roots (ISP_SYS, GFX, AVD_SYS, ANS, DISP*, ANE_SYS,
    ...) carry it. Hypothesis: these are the domains whose unreported power-off
    matters in attempt 14; nothing here proves it.
* **Implemented:** `native/probe/pmgr_probe.py` (`read`, `plan`, `cycle`) and
  `tools/m1n1-client/pmgr-probe-instructions.md`.
* **Tested:** 85 offline tests incl. the real table and 22 mutants; no hardware.
* **Not verified:** everything live, including whether m1n1's register sequence
  on these domains behaves like Linux's (it does not report to the PMP).
* **Next:** M1 offline readiness, stage 1 in one short lab session, then (separate
  approval) a control domain and a `notify_pmp` domain. Independent of boot034 and
  hv003.

## 2026-10-14 · M5: hv003 repairs and instruments the chainload (NOT RUN)

* **Discovered:**
  * The hv002 stop is a hang before `fb_init()` in the new m1n1: restored
    Apple logo, no progress bar, so a hang rather than a reset.
  * Our copy stub kept its 64-bit entry literal at 4 mod 8 and runs with the MMU
    off, where an unaligned 8-byte load faults (Likely: arithmetic and an
    instruction emulator agree; not hardware-confirmed).
  * The proxy chainload differs from Asahi's in-tree stage-1→2 one: six
    relocated blobs and a whole-ADT rebuild (a first on t6050).
  * Review also found and hv003 fixes: the launcher echoed every target console
    byte (including the device serial) to the terminal and `--log`; the new
    m1n1's heap could start below live iBoot structures; host breadcrumbs are
    erased by boot021's own redraw; the stub had no entry mark.
* **Implemented:**
  * `0002-ilinux-hv-t6050-hv003-crumbs.patch` (additions only, startup.c and
    main.c) and VM job 037; padded stub; `adt_patch.py` raw ADT patcher;
    `hv_chainload.py` plan/gates/breadcrumbs; launcher modes
    `--layout-only`, `--chainload-only`, `--control stock`,
    `--chainload-mode`; `make_hv_package.py` (manifest schema 2, two guests).
* **Tested:** 168 chainload, 76 launcher, 10 ADT and 13 crumb tests (267 under
  `discover -s native/hv`), 37 native launcher tests, 5 genpd; a 71-bug mutation
  sweep (2 survivors, now covered). Machine code of the final binary: crumb
  calls in contract order, state word in `.data`; DAPF guard passes.
* **Not verified:** everything on hardware, including whether the stub
  hypothesis is right, `adt_patch.py` on a real t6050 ADT (rung 1 is its first
  parse) and the Device-memory framebuffer stores with the MMU off.
* **Released:** `native-j716c-hv003`, archive `3924337…2c05`.
* **Next:** M1 offline readiness, then the ladder in
  `tools/m1n1-client/hv-instructions.md`; boot034 / attempt 15 is independent.

## 2026-10-14 · M5: boot034 tests genpd sync_state as the attempt-14 reset trigger

Boot034 / attempt 15 prepared after reviewing M1 attempt 14 (`a4269bb`) and the
hv002 chainload stop (`fd473b1`). The hypervisor is blocked at the chainload, so
this attempt does not use it. Exact source shows genpd **sync_state powers off
every unclaimed boot-on PMGR domain without honoring `pd_ignore_unused`** (the
flag guards only the later sweep that attempt 14 printed). In the Stage-B DT,
152 of 188 domains are unclaimed and not always-on; `of_platform_sync_state_init`
did 5 ms of work 5.6 s before the reset. Boot034 makes sync_state honor the flag,
logs every real power-off, and after ≈ 20 s kernel time releases the unclaimed
domains one per 500 ms, naming each first, so any reset is attributable.
Only Image changes. Exact-source ASan/UBSan model (5 mutations caught), VM build
with identical config and ELF/Image roundtrip, linked-code review and exact-image
generic one-CPU PID1/60s liveness PASS. **Native boot034/live checks NOT RUN.**
No launcher or reviewed-digest change. M1 next: `tools/m1n1-client/stage-b-instructions.md`,
offline readiness, one human-started filmed attempt 15 (keep filming past 60 s:
stop on reset, `ladder complete` or 120 s) and return to Macintosh HD.
Evidence/code: `kernel/experiments/genpd-sync-state/`.

* **Chainload analysis (no live action):** `native/hv/hv002-chainload-analysis-2026-10-14.md`.
  The hv002 stop is most likely in our proxy chainload procedure or early re-init,
  not in HV code; a hardened chainload with on-screen breadcrumbs was then built as
  hv003 (entry above) and is independent of boot034.

## 2026-10-14 · M1: hv002 census v2 PASS; Session 2 never got past the chainload

* Census v2 PASS for hv002 at 22:58:05 UTC: all 19 registers readable, ECV=1,
  `VM_TMR_FIQ_ENA_EL2` ENA_V=1 ENA_P=1 (expected), PMCR0/IPI_SR readable.
  Returned to Macintosh HD.
* **Session 2 (hv002) stopped at the chainload.** Package, target, register
  preflight, ADT/boot-blob copy and `Preparing to run next stage` all passed.
  Then `Waiting for reconnection...` for about 80 s and
  **`STOP: UartTimeout Reconnection timed out`**.
* No m1n1 USB device on the M1 afterwards; the vUART never returned (log
  empty). The M5 sat at a black screen with the Apple logo (the restored iBoot
  logo) until powered off.
* **Hypervisor and guest NOT STARTED.** hv002 likely stopped before its
  framebuffer init, in early m1n1 re-initialization; cause unknown. Report and
  suggestions (stock boot021 chainload as a discriminating test, early
  on-screen progress codes): `native/hv/hv002-session2-2026-10-14-result.md`.
* User confirms return to Macintosh HD; fresh policy/default NOT CHECKED.
  No retry.


## 2026-10-14 · M1: hv002 sessions offline readiness PASS

* Pulled/read M5 handoff `6e58ccd`, `native/hv/README.md` and
  `tools/m1n1-client/hv-instructions.md`. README file hashes 8/8 match.
* Release `native-j716c-hv002`: archive 2,134,659 bytes, SHA-256
  `c79ffded48bebc580734918c1540fd589937d5440e2a385a65186c801f2c4254`, verified
  before extraction. Four regular members; `m1n1-hv.bin`, `System.map` and the
  symbol list match `hv-manifest.json`. Guest Image is unchanged boot033.
* **Offline PASS:**
  * 33 hv tests, none skipped; `TimerModelTests` compiled with cc
    (ASan/UBSan) on M1, and four `PackageTests` ran on the real packages;
  * 37 launcher tests;
  * client-venv imports;
  * offline `hv_launch.py`: Package PASS (boot033 guest + hv002 m1n1),
    OFFLINE ONLY, exit 0.
  * Client pin clean at `57a9339`.
* **M1 independent review:**
  * census v2 (`hv_regs.py`) does guarded reads only;
  * the patch source-masks expired guest timers (`CNTx_CTL_EL02.IMASK`),
    injects HCR_VF, and hides the mask from guest CTL reads; guest CTL writes
    and CVAL/TVAL re-arms lift it;
  * both guest timers are zeroed before entry;
  * the UPMCR0/UPMSR block is gated on `uncore_version`.
* Ignored record `build/native-intake/results/hv002-readiness.json`.
* **Ready for Session 1 (census v2)** after publication. Session 2 (hv002)
  only after a census PASS and a separate human start. **Live checks NOT RUN
  at readiness.**


## 2026-10-14 · M5: hv002 replaces hv001 (source-masked guest timers, ECV gate, uncore gate)

* **Discovered:**
  * The hv001 census block is genuine: guest-timer FIQ enables are set and
    write-locked, and polling cannot stop the physical FIQ.
  * Review also found an unvalidated uncore PMU read in the HV FIQ path
    (m1n1 gates it on `uncore_version`; M5 has none).
  * With ECV the pinned HV already traps every guest timer access and re-runs
    `hv_update_fiq()` after each, which is where a shadowed `CTL` fits. This
    is the M1's suggested direction, verified against the code.
* **Implemented:**
  * the hv002 m1n1 patch (+155/−7), built by job 035 with no C warnings;
  * census v2 rules in `hv_regs.py`, shared by `census.py` and a new in-boot
    launcher preflight;
  * a launcher flag gate for ECV;
  * the package check requires the hv002 symbol.
* **Tested:**
  * machine-code review of the timer, trap, gate and uncore paths;
  * the timer model test (exact patch code, ASan/UBSan, 8 scenarios, 3
    mutations caught);
  * 33 hv tests PASS; pure `native/boot` suites PASS (unchanged).
* **Released:** `native-j716c-hv002`, archive `c79ffded…4254`.
* **Not verified:**
  * live behavior, including whether Apple's ECV traps EL1 timer accesses as
    specified;
  * M1 client-venv imports.
  * No performance claim.
* **Next:** M1 readiness, then census v2, then (if PASS) one hv002 session.

## 2026-10-14 · M1: H1 register census BLOCKED for hv001 (guest-timer FIQ enables set)

* One read-only census at readiness `8267222`, 22:24:14 UTC: exit 2, under
  one second. Chip, marker and no-secondaries gates passed; 15 guarded reads,
  no writes, no retry.
* **All 15 registers readable.** That includes the unguarded `hv_start()`
  reads (AMX/APVMKEY/APSTS/ACTLR/SPRR/GXF/CNTHCTL); ECV=1.
* **BLOCKED:** `VM_TMR_FIQ_ENA_EL2` reads **ENA_V=1 ENA_P=1**. The enable bits
  are already on and the register traps on write at EL2 (attempt 5), so hv001
  refuses to start. Guest timers `CNTV/CNTP_CTL_EL02` read ctl=7 (enabled,
  masked, expired).
* **hv001 Session 2 NOT RUN.** User confirms return to Macintosh HD; fresh
  policy/default checks NOT CHECKED. Report and revision direction (mask guest timers at
  the architectural source with a shadowed CTL via the ECV traps):
  `native/hv/census-2026-10-14-result.md`.


## 2026-10-14 · M1: hv001 sessions offline readiness PASS

* Pulled/read M5 handoff `4814b6f` (hv001 prepared in `ee5b824`), `native/hv/README.md`
  and `tools/m1n1-client/hv-instructions.md`. All six README file hashes match.
* Release `native-j716c-hv001`: archive 2,134,653 bytes, SHA-256
  `c659462c77df8a56979aff5f5f5596cbbdb49a6bbe0eaef5d2ecfd9bd6f4ebb1`, verified
  before extraction. Four regular members; `m1n1-hv.bin` `6d031661…85ac`,
  `System.map` and the symbol list match `hv-manifest.json`. Guest Image is the
  unchanged boot033 `250d9ff5…eb15`.
* **Offline PASS:**
  * 28 hv tests; PackageTests ran against the real packages, not skipped;
  * 37 launcher tests;
  * client-venv imports (m1n1.hv, bootmem, tgtypes, proxyutils, construct,
    serial);
  * offline `hv_launch.py`: Package PASS, OFFLINE ONLY, exit 0, with bootargs
    `console=ttySAC0,115200` before `console=tty0` and
    `earlycon=s5l,0x505200000`.
  * Client pin clean at `57a9339`.
* **M1 independent review:**
  * `census.py` does reads only: 15 `ProxyUtils.mrs` calls under the
    exception guard, no `msr`, a 120 s alarm, and chip/marker/no-secondaries
    gates.
  * The m1n1 patch is limited to: no secondary start on T6050; a read-only
    `VM_TMR_FIQ_ENA_EL2` gate that refuses to start if it is enabled; polled
    guest timers in `hv_update_fiq`; and private op `0x7f0` (cache, tunables,
    clock and DAPF without USB/PCIe).
* Ignored record `build/native-intake/results/hv001-readiness.json` holds the
  hashes and results.
* **Ready for Session 1 (read-only register census)** after publication.
  Session 2 (hv001) only after a census PASS and a separate human start.
  **Census and hv001 live checks NOT RUN at readiness.**


## 2026-10-14 · M5: hv001 private hypervisor path prepared (census, then boot033 at EL1)

* **Discovered (offline, pinned m1n1 source + M5 sanitized ADT):**
  * The upstream HV cannot run on t6050 as is: it starts all secondaries and
    writes `VM_TMR_FIQ_ENA_EL2`.
  * kboot's memory map would hand the HV's own RAM to Linux.
  * The boot033 DT has no USB/PCIe/SPMI nodes, so Linux cannot touch the HV
    link.
  * Upstream `map_essential` keeps the link's PMGR domains powered. The
    devices decode correctly: 661 records of 48 bytes; for a USB0 link, UART0
    `0x280900360` and ATC0_USB `0x288300150`.
* **Implemented:**
  * `native/hv/` m1n1 patch (+53/−1), built by VM job 034 (no C warnings).
  * `hv_launch.py`: RVBAR-free chainload, NOP-verified reconnect, HV flag gate,
    boot033 DT gates, Linux RAM above the HV with overlap checks, RESERVED
    CPU_START hook, vUART console with `tty0` still `/dev/console`.
  * `census.py`: read-only register census.
  * `vuart_log.py`: reconnecting logger.
  * M1 instructions.
* **Tested:** 28 offline tests PASS, in script and unittest modes. Real
  packages verify offline; tampered packages and wrong symbol offsets are
  rejected. Pure `native/boot` suites PASS and those files are unchanged.
* **Released:** `native-j716c-hv001`, archive `c659462c…ebb1`.
* **Not verified / unsupported:**
  * the M1 client-venv imports;
  * every live behavior (census, chainload re-enumeration, HV start,
    unguarded register reads in `hv_start`, vUART IRQs, EL1 guest);
  * no performance claim (never benchmark under the HV).
* **Next:** M1 offline readiness, then census session, then (if PASS) one
  hv001 session. See `tools/m1n1-client/hv-instructions.md`.

## 2026-10-14 · M1: attempt 14 reaches native PID 1; silent SoC reset ~5.6 s later

* One boot033 RAM attempt at readiness `994b62f`, M5 handoff `b76ab6b`.
  **Controller exit 0, 10.74 s**; handoff 2026-10-14T19:50:04.394670Z. Target,
  marker, no-secondaries, GPIO ADT, final hardware DT, DAPF layout/correction,
  framebuffer descriptor and kboot reply PASS.
* **Native diagnostic PID 1 reached for the first time.** `Run /init` at
  3.152165 s; `PID 1 reached` at 3.166444 s. DT model `Apple MacBook Pro
  (16-inch, M5 Max)`, MemTotal 132456096 kB, CPU online mask `0`.
  `[diag] heartbeat 000/001 online_cpus=1` at 3.230083 and 8.233382 s.
* **GPIO repair works on hardware.** `pinctrl@2881e4000`: cache 61/61/0, IRQ
  handoff 61/7 masked=1, returned 0 after 103600 us. Main `pinctrl@29c000000`:
  cache **221/216/5**, IRQ handoff 221/7 masked=0, returned 0 after 264934 us.
  ASC mailbox probe returned 0 after 4570 us. Panel D 0052 decodes to
  `mbox@419608000` and D 004C to `iommu@41dc50000` (SART); both use PMGR
  `power-controller@140`.
* Late init: `clk: Not disabling unused clocks`, `PM: genpd: Not disabling
  unused power domains`, `of_platform_sync_state_init` returned 0 after 5017 us.
* **Silent SoC reset at kernel ~8.77 s**, about 0.5 s into the second 5 s sleep.
  The screen went to black within one video frame with no kernel, panic,
  watchdog or reboot text. Apple logo about 3.4 s later, then macOS login at
  3:50 PM; the user reports the default OS. **60-second liveness NOT REACHED.**
  Cause unknown. m1n1 had disabled both watchdogs before handoff (on screen).
* Media: `IMG_2669.mov`, 34.297 s at 30 fps, reviewed locally (AVFoundation
  frames, brightness traces, upscaled crops). It stays in ignored
  `build/native-intake/inbox/`; no still photo; review images deleted.
* **Attempt 14 consumed.** Report: `native/boot/stage-b-2026-10-14-attempt14-result.md`.
  M5 next: read-only return checks, then the reset trigger. Ranked hypotheses
  in the report: PMGR power-off at sync_state despite `pd_ignore_unused`,
  ANS mailbox/SART side effects, and the second idle period. Fresh policy/
  default NOT CHECKED. No retry or settings changes.


## 2026-10-14 · M1: boot033 attempt 14 offline readiness PASS; boot034 proposals

* Pulled/read M5 handoff `b76ab6b`, the attempt-14 checklist and scheduler-RAM
  evidence. Archive **16,723,317 bytes**, SHA-256
  `6cbf5d1396ddd2b5f79255e65c6c776f8122921b06327271e1102f7b7f0d55cd`,
  verified against Git before extraction; 14 regular members, no absolute or
  parent paths. **13-file intake and offline launcher PASS.**
* **102 M1 offline cases PASS** (37+10+6+16+5+19+2+6+1), all exit 0; synthetic
  transport only. Image SHA-256
  `250d9ff58e5f5397e1bb54682f2bd8a7a679f44f2863629ef7b89ec45ad1eb15`;
  Stage-B DT SHA-256 unchanged
  `4b3adee52465b809e9c8a1946b7610c63f1ae3c0b24f7334cd485260da84adce`.
* Versus retained boot032 only Image and package-manifest metadata differ.
  Six reviewed controller digests match the checklist; client pinned clean at
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`. Installed boot021 unchanged.
* Fresh ignored receipt `build/native-intake/receipts/boot033-attempt14.json`,
  record `build/native-intake/results/boot033-stage-b-attempt14.json`/`.md`
  and one-shot wrapper `build/native-intake/run-attempt14.py` retain payload,
  source, procedure and receipt hashes.
* **Ready for Stage B attempt 14** after publication. Human reports the M5
  proxy already running; recording starts before launch and continues through
  the stop criterion. M5's post-attempt-13 protection prerequisite applies.
  **Native boot033/live checks NOT RUN at readiness.**
* Next: one documented RAM launch; capture all four panel rows (S is now
  watchdog-sampled), GPIO counts/errors, PID 1/one CPU/60-second liveness;
  stop at panic/rejection, userspace milestone or 120 seconds after handoff,
  then Macintosh HD. No reconnect/retry/reinstall/settings/volume changes.
* **For M5 (proposals, not authorization):** boot034 should turn on the kernel's
  own stall reporting with panic output drawn straight to the screen, and load
  the GPIO driver after PID 1. Details and evidence: `coordination.md` (M1
  proposals). Hypervisor study:
  `research/m1n1/hv-linux-guest-feasibility-2026-10-14.md`; not usable on
  t6050 without m1n1 changes, not the next step.


## 2026-10-14 · M5: boot033 removes scheduler framebuffer rendering; attempt 14 prepared

Boot033 / attempt 14 prepared after reviewing M1 attempt 13 (`9a045cf`).
Attempt 13 has no attributed GPIO result or native PID 1; cause remains unknown.
Confirmed own-code overhead: scheduler hooks repaint all eight diagnostic lanes.
Boot033 keeps scheduler state in RAM and samples S from the bounded watchdog;
S is no longer an immediate checkpoint display. Only Image changes. Preserve
boot032 GPIO exclusions, installed boot021, all gates and the current lab entry.
Full Image/ELF roundtrip, actual-hook ASan/UBSan, 102 controller cases, 13-file
intake and 13+8 intake/evidence cases PASS. Linked hook: 14 instructions, no
calls. Exact Image/initramfs generic VM reaches PID 1/one CPU/60s liveness at
60.192455 kernel seconds (60.368s wall); native boot033/live checks NOT RUN.
User reports post-attempt-13 Full/Permissive; fresh exit codes not supplied.
M5 read-only original-root/build/FileVault/SIP/staged-m1n1 checks PASS, superseding
pending return status below; default/installed object/authenticated-root were
not rechecked. No boot/security/volume changes. M1 next: current Stage-B checklist,
offline readiness, one human-started filmed attempt 14, stop by milestone/error/
120s from handoff and return to Macintosh HD. No setup/retry or extra M5 approval
loop. Claude workflow: `native/boot/claude-workflow.md`. Evidence/code:
`kernel/experiments/scheduler-ram-only/`. Native userspace still gates Linux
control/RAM root/configuration-agent work, then Omarchy and hardware performance.


## 2026-10-14 · M1: attempt 13 dynamic heartbeat; return pending

* One boot032 RAM attempt at published readiness `8f2c908`, M5 handoff `f2b2c4d`.
  **Controller exit 0, 10.589 s**; UTC 17:56:51.492019–17:57:02.081153,
  handoff 17:57:01.852238. Boot021 marker, live GPIO ADT exclusions, final
  hardware/GPIO DT, both DAPF checks/readback, framebuffer/readback and kboot
  PASS. USB closed; no extra handshake, reconnect, retry or settings change.
* Reviewed **40.13-second IMG_2665.mov** and detailed **IMG_2666.jpeg**.
  Native Linux/Tux, J716c/t6050 **EL2 cpus=1**, **ticks=25**, IRQ/FIQ masks0,
  pending=1/strip=1/display=6 are readable. Timer PASS/phys/virt text, printed
  phase digits and console_setup are covered/unobserved, not copied from prior boots.
* Literal final photo: **P05 / W00 H06 / D0000 I000 / B00 C0000**;
  S mixed/repainting and **NOT CONFIRMED**. Video shows P0D at 10s then P05;
  H00/01/02/04/05 sampled at 10/15/20/30/39.98s, photo H06. W/D/I/B/C remain
  zero in these samples. S06 clearly sampled at 30s; no stable final S assigned.
* Offline decoder returns unknown device/no marked operation. I000 is numeric 0,
  not evidence of a pin 0 read without attributed D/C and B91. P05 is the first
  work-flush boundary by source; no nonzero device or GPIO checkpoint observed.
  The six-heartbeat watchdog is bounded; H06 is not userspace liveness or proof
  of a later timer failure. Exact blocked PC/task/cause remain unknown.
* GPIO cache/IRQ counts, retries/returns/errors, readable watchdog stack and
  scheduler summary **NOT OBSERVED**. Do not import attempt12 NUB success.
  **PID 1/userspace online_cpus=1/60-second liveness NOT OBSERVED**; no explicit
  panic seen. Console stays at partly covered reschedule text while panel changes.
* Reviewed video times 0/5/6/7/8/9/10/15/20/30/39.98s; no 60/90s or full 120s
  coverage. Photo adds H06/detail, not duration. Stop deadline communicated as
  **1:59:02 p.m. Eastern**, return instructed after deadline. **Macintosh HD
  return PENDING HUMAN CONFIRMATION**; fresh policy/default NOT CHECKED.
* **Attempt 13 consumed.** Detailed report:
  `native/boot/stage-b-2026-10-14-attempt13-result.md`. M5 next: read-only review
  after confirmed return and offline worker/scheduler/console analysis. No
  GPIO repair or pin-fault claim. Preserve installed boot021, pin and gates.


## 2026-10-14 · M1: boot032 attempt 13 offline readiness PASS

* Pulled/read M5 handoff `f2b2c4d`, Stage-B attempt-13 checklist and reserved-GPIO
  evidence/validation. Archive **16,723,345 bytes**, SHA-256
  `001ef39cd64d8fef7c3779c5169c00726474d6ebc56cea90b9f6f5d9c9bd0500`,
  verified against Git before safe extraction. **13-file intake and offline
  launcher PASS**; source/controller/decoder hashes and clean client pin PASS.
* **102 M1 offline cases PASS** (37+10+6+16+5+19+2+6+1), all exit 0; synthetic
  transport only. Image SHA-256
  `589c33577d1bc2ddeb2f96e544f87b9ead6bc52e774410567170a7235dd70bcb`;
  Stage-B DT SHA-256
  `4b3adee52465b809e9c8a1946b7610c63f1ae3c0b24f7334cd485260da84adce`.
* Independently compared retained boot031: only Image, Stage-B DT and manifest
  metadata differ. Semantic DT difference is exactly main GPIO reserved ranges;
  node paths and 286 public IDs retained. Installed boot021 unchanged; client
  pinned clean at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
* Fresh ignored receipt `build/native-intake/receipts/boot032-attempt13.json`
  and result `build/native-intake/results/boot032-stage-b-attempt13.json`/`.md`
  retain payload/source/procedure/receipt hashes. Sanitized one-shot wrapper
  includes the new GPIO gate checkpoint and safe error-frame handling.
* **Ready for the authorized Stage B attempt 13** after publication. Human
  reports proxy running and recording; requested entire panel including I and
  recording through stop. M5 post-attempt-12 protection prerequisite already
  PASS. **Native boot032/live checks NOT RUN at readiness.**
* Next: one documented RAM launch; capture P/S/W/H/D/I/B/C, actual GPIO
  cache/IRQ counts and errors/returns, PID 1/one CPU/60-second userspace liveness;
  stop at panic/rejection, userspace milestone or 120 seconds after handoff,
  then Macintosh HD. No reconnect/retry/reinstall/settings/volume changes.


## 2026-10-14 · M5: boot032 / attempt 13 reserved-GPIO repair prepared

* Consumed M1 attempt 12 (`f3218fd`): final P05/S09/W04/H02/D0059/B73/C0059
  places the main GPIO controller at cache initialization. NUB IRQ handoff
  61/7/1 and return 0 observed; main return and native PID 1 remain unobserved.
* Fresh user post-attempt-12 JSON PASS: original **Full**, lab **Permissive**,
  both exits 0. Independent M5 read-only root Macintosh HD/build 25G83/
  FileVault/SIP and unchanged staged m1n1 checks PASS. No host settings changed;
  default/installed boot object/authenticated-root were not independently
  re-queried. The report's pending policy check is superseded.
* Read-only GPIO metadata gives excluded pins **5,6,7,112,141**, 221 pins,
  7 groups. REA + original bytes/LLVM confirm Apple's in-body skip behavior.
  Exact boot031 Linux source/REA/linked bytes show its cache scans declared
  pins without exclusions. This is a supported **candidate cause**, not a
  native fault PC. Start pseudocode remains manual-review; prior init pcode
  remains rejected. No proprietary code or binary published.
* Boot032 adds validated DT reserved ranges, explicit permitted cache defaults,
  sparse-cache/access checks, GPIO/pinmux/IRQ exclusions, and rejection of
  initially pending excluded IRQs before parent installation. New I lane
  records pin index; B90–93 refine progress. Main expected cache is 221/216/5.
  All 286 public D/C IDs remain. Only Image and one Stage-B DT property change
  among payloads; installed boot021/config/initramfs/fixed args/gates remain.
* Full Image/ELF roundtrip and exact source-recipe reproduction PASS. Actual
  helper/callback ASan+UBSan tests: 216 allowed reads, zero forbidden MMIO,
  errors/IRQ masks/8 geometries; 8-lane renderer/3 fonts PASS. GPIO binding and
  selected Stage-B schema PASS. **102 controller tests**, **13 intake files**,
  **13 member + 8 evidence tests PASS**. Exact Image/initramfs diskless,
  networkless, one-CPU VZ reaches PID 1 and 60s liveness at **60.192890 s**.
  Native GPIO/MMIO is not exposed by VZ; no native performance/energy claim.
* **Native boot032 / attempt 13 / live checks NOT RUN.** M1 follows
  `tools/m1n1-client/stage-b-instructions.md`: verify private release
  `native-j716c-boot032`, publish offline readiness, then one filmed human-started
  attempt and Macintosh HD return. No extra approval round trip, provisioning,
  Recovery, new skip, retry or settings/volume/security changes.
* Record all panel lanes including I, actual cache/IRQ counts, errors/probe
  return and PID-1/one-CPU/60-second liveness separately. Native userspace is
  the next gate before Linux-side control/input/RAM root and the configuration
  agent's Omarchy work. Evidence: `kernel/experiments/gpio-reserved/README.md`
  and `validation.json`. All test VMs stopped before handoff.

## 2026-10-14 · M1: attempt 12 GPIO cache checkpoint; macOS return PASS

* One boot031 RAM attempt at readiness `83f0f20`, reviewed M5 handoff `cd9ac3f`.
  **Controller exit 0, 10.545 s**; UTC 16:19:37.850798–16:19:48.396252,
  handoff 16:19:48.168614. Boot021 marker, final hardware DT, both DAPF
  checks/96-byte correction/readback, 16-byte framebuffer descriptor/readback
  and kboot reply PASS. USB closed; no retry/reconnect/settings changes.
* Reviewed **40.163333-second video** and detailed **IMG_2664.jpeg**. Native Linux
  reports **J716c/t6050 EL2 cpus=1**, timer **PASS/25 ticks**, phys=1/virt=7,
  irq_masked=0/fiq_masked=0, pending=1/strip=1/display=6 and printed phases
  **1→10→11→12→13→2→3→4→5**. Four panel rows visibly render.
* Final literal **P:05 S:09 / W:04 H:02 / D:0059 / B:73 C:0059**, at video
  25/30/40.013333 s and photo. Offline decode: **/soc/pinctrl@29c000000**,
  **GPIO bounded register-cache initialization**. This narrows the boundary
  beyond prior B63; no exact blocked instruction/register/cause established.
* Earlier **/soc/pinctrl@2881e4000** reports **pins=61 parents=7 masked=1**
  for t6050 IRQ handoff, then **returned 0 after 1918983 usecs**, retry 1 end.
  Main-controller return/counts/errors NOT OBSERVED. First GPIO success does
  not establish all GPIO/peripheral support or validate the proposed hang cause.
* Watchdog 1: phase5/worker4/device1/**ticks=1285**; scheduler7/selections1337/
  prev10/next12/current12/**kworker/u4:0**, events_power_efficient. Photo provides
  14 symbolic frames/offsets through timer softirq/IRQ exit. Later device2/
  **ticks=2565**, selections2620/prev10/next38/current38/**kworker/u4:1**.
  Lower stack/prefixes obscured; first watchdog stack is not a proven B73 stack.
* **PID 1/userspace online_cpus=1/60-second liveness NOT OBSERVED**; no explicit
  panic seen. Clip sampled at 0/5/10/15/18/20/22/25/30/40.013333 s; no 60/90s
  or full 120s coverage. Photo adds detail, not elapsed coverage. Early S digits
  remain unconfirmed. Human confirms **Macintosh HD desktop return PASS**;
  later screen changes not separately reported, fresh policy/default NOT CHECKED.
* **Attempt 12 consumed.** Stop/return instructed at **12:21:48 p.m. Eastern**.
  Detailed evidence: `native/boot/stage-b-2026-10-14-attempt12-result.md`.
  M5 next: read-only return checks and offline analysis of the exact main-GPIO
  cache path. Preserve installed boot021, client pin, gates and fixed arguments.
  No new live attempt until updated instructions and human start.


## 2026-10-14 · M1: boot031 attempt 12 offline readiness PASS

* Pulled/read M5 handoff `cd9ac3f`, Stage-B attempt-12 instructions and GPIO
  handoff evidence/validation. Archive **16,724,870 bytes**, SHA-256
  `73ad67d17c78da9ef2eeec63122e52271e8a9521120add8d60588a6585ab9246`,
  verified before extraction. **13 intake files**, offline launcher, reviewed
  controller/source hashes and public decoder tables PASS. Image SHA-256
  `09d3cc302da20ef53c41bec3324d702b249a729a55e3799b5676618034bff37d`.
* **90 M1 offline tests PASS** (37+6+16+5+19+2+4+1), all exit 0; synthetic
  transport only. Clean m1n1 client remains pinned at
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`; installed boot021 unchanged.
  Only Image/package manifest differ from retained boot030. System Python's
  unsupported tar filter option stopped initial extraction; revalidated archive
  and safe regular-file/directory paths, then extraction/intake succeeded.
* Fresh ignored receipt `build/native-intake/receipts/boot031-attempt12.json`
  and result `build/native-intake/results/boot031-stage-b-attempt12.json`/`.md`
  retain source/procedure/controller/payload/receipt hashes. Sanitized wrapper
  prepared with a zero-attempt guard and unchanged documented launcher arguments.
* **Ready for the authorized Stage B attempt 12** after publication. Human
  reports proxy running and recording. M5 post-attempt-11 return/protection
  prerequisite already PASS; no repeat approval or setup. **Native boot031 and
  live checks NOT RUN at readiness.** Generic VM results do not validate GPIO.
* Next: one filmed RAM launch; capture literal four-row panel, GPIO stages and
  actual counts/errors/returns, Linux PID 1/one CPU/60-second liveness. Stop on
  rejection/panic, userspace liveness milestone or 120 seconds from handoff;
  return to Macintosh HD. No retry/reconnect/reinstall/settings change.

## 2026-10-14 · M5: boot031 GPIO cache/IRQ handoff repair; attempt 12 prepared

* Reviewed M1 `f35efa5`: attempt 11 controller PASS and final **P05 S09 W04 H02
  D0059 B63 C0059** identify `/soc/pinctrl@29c000000` at its callback. Earlier
  NUB pinctrl returned 0. Exact blocked PC/IRQ storm/userspace remain unproven.
* Exact Linux REA/source/ELF/LLVM covers **392 instruction words**, 331 linked
  nonrelocated matches and 61 separately reviewed relocation words. Two Apple
  GPIO routines add **222 original-byte/LLVM-checked words**. Initialization
  pseudocode fails the cross-boundary gate; only bounded, independently verified
  instructions support its status-clear observation. No proprietary code copied.
* Implemented **t6050-only** geometry validation and cache length from declared
  pins (AP 221 rather than 512), plus gpiolib `init_hw` masking of inherited input
  IRQs, MMIO readback and valid-bit pending-status clears before parent enable.
  Outputs/mux/pulls/group/data preserved. Locked active pins/errors fail visibly;
  no lock override or new driver skip. Seventeen new B checkpoints distinguish
  cache/pinctrl/GPIO/handoff stages. **Candidate hang fix, native NOT RUN.**
* Full Image/ELF roundtrip and unchanged config PASS. Actual helper/geometry
  ASan/UBSan regressions cover sizes/partial words/field preservation/error paths,
  baseline over-read and pending-IRQ behavior. **90 controller cases**, 13-file
  intake and exact one-CPU/4 GiB diskless/networkless VZ boot PASS: all phases,
  PID 1, online_cpus=1 and 60s liveness at **60.189741 s**. VZ does not exercise
  t6050 GPIO/AIC/MMIO or establish native efficiency/peripheral functionality.
* Fresh post-attempt-11 user JSON original **Full** / lab **Permissive**, exits 0.
  Independent root **Macintosh HD**, build **25G83**, FileVault/SIP enabled and
  staged m1n1 checksum unchanged. This resolves the report's pending return.
  Default/installed object/authenticated-root not independently re-queried.
* Only RAM Image changes. Installed boot021/client pin, DT/config/initramfs,
  args/single skip/hardware gates/current entry stay. No boot/security/volume/
  default/firmware changes. Preserve all prior attempts and packages.
* All owned build/REA/test VMs stopped; both shared quiet locks released.
* Next: M1 verifies private **native-j716c-boot031**, publishes readiness, then
  one human-started filmed **attempt 12**. Record GPIO handoff counts/errors,
  literal panel and decoded D/C/B, probe return and PID-1/60s liveness, then
  Macintosh HD within the existing bound. No provisioning/reinstall/automatic
  retry or extra M5 approval loop. Native userspace precedes Linux control/input
  and the configuration agent's Omarchy work. See the current Stage-B checklist
  and `kernel/experiments/gpio-handoff/README.md`.

## 2026-10-14 · M1: attempt 11 panel/heartbeat/stack evidence; return pending

* One boot030 RAM attempt at readiness `3c0b051`, reviewed handoff `1125c33`.
  **Controller exit 0, 10.526 s**; UTC 15:27:11.254767–15:27:21.781567,
  handoff 15:27:21.541577. Target boot021 marker, hardware DT, both DAPF
  checks/96-byte readback, 16-byte descriptor/readback and kboot reply PASS.
* Reviewed **43.43-second video** plus detailed **IMG_2662.jpeg**. Photo directly
  confirms J716c/t6050 **EL2, cpus=1**, counter **PASS/25 ticks**, timer
  **phys=1 virt=7 irq_masked=0 fiq_masked=0**, printed phases
  **1 → 10 → 11 → 12 → 13 → 2 → 3 → 4 → 5**, and **pending=1 strip=1 display=6**.
* Four-row panel changes through first and second device probes; final readable
  **P:05 S:09 / W:04 H:02 / D:0059 / B:63 C:0059** at video 30/43.28 s and photo.
  Offline public-table decode: **/soc/pinctrl@29c000000**, t6050/t8103 pinctrl,
  platform driver probe callback boundary. Earlier D=C=0057 maps to
  **/soc/pinctrl@2881e4000**; photo reads **returned 0 after 164043 usecs**, retry 1 end.
* First watchdog: **phase=5 worker=4 device=1 ticks=1304**; scheduler
  **sched=7 selections=1274 prev=52 next=20 current=20/kdevtmpfs**. Photo provides
  14 readable symbolic frames/offsets through timer softirq/IRQ exit; lower
  frames obscured. Later **device=2 ticks=2584**, selections=2550/prev=52/
  next=38/current=38/**kworker/u4:1**. First stack is not a proven final-driver
  stack. H=02 is a kernel watchdog count, not userspace liveness.
* **PID 1/userspace online_cpus=1/60-second liveness NOT OBSERVED**. No explicit
  panic observed. Video sampled at 0/10/15/20/30/43.28 s; no 60/90-second or full
  120-second coverage. Photo improves text, not duration evidence. Hidden
  fields/stack frames remain unconfirmed; no exact blocked PC/cause established.
* Return instructed at deadline **11:29:21 a.m. Eastern**; **Macintosh HD return
  PENDING HUMAN CONFIRMATION**, fresh protection/default **NOT CHECKED**.
  No retry, reconnect, reinstall or settings change. Full media remains out of Git.
* **Attempt 11 consumed.** Detailed report:
  `native/boot/stage-b-2026-10-14-attempt11-result.md`. M5 next: read-only checks
  after confirmed return and offline analysis of the decoded pin-controller
  callback/dependencies. Preserve installed boot021, clean client pin and gates.

## 2026-10-14 · M1: boot030 attempt 11 offline readiness PASS

* Pulled/read M5 handoff `1125c33`, probe-path README/evidence/validation and
  public D/C/B decoder tables. Archive SHA-256
  `260f57106007b654a522480e3c20fb2b3630338a5b90edaa64bd067fa0ec2c16`
  and 16,724,043-byte size verified **before extraction**. All **13 intake
  files**, offline launcher and reviewed controller/decoder digests PASS.
  Image SHA-256 `190cd86d5f823326f5a44277f5efb96cc01c85b3a3f9ffbde16d9cb7abe35067`.
* **90 M1 offline cases PASS:** 37 launcher + 6 entry + 16 DAPF + 5 framebuffer
  + 19 hardware + 2 pinned ADT/DAPF + 4 root ADT + 1 real proxy serializer;
  all exit 0, synthetic transport only. Clean client remains pinned at
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`; installed boot021 unchanged.
* Only Image/package manifest differ from retained boot029. Fresh ignored
  receipt `build/native-intake/receipts/boot030-attempt11.json` and result
  `build/native-intake/results/boot030-stage-b-attempt11.json`/`.md` prepared
  with source/procedure/controller/payload/receipt/decoder hashes.
* **Ready for the authorized Stage B attempt 11** after publication. Human
  reports proxy running and video recording including all four panel rows.
  Post-attempt-10 protection prerequisite already PASS per M5; no extra restart
  or review loop. **Attempt 11 native/live checks NOT RUN at readiness.**
* Next: one reviewed RAM launch, literal P/S/W/H/D/B/C and Linux milestones,
  recording through the stop criterion with a close final frame. Decode public
  IDs offline and review video before publishing, then Macintosh HD within the
  existing bound. No retry, wider blacklist, reinstall or settings changes.

## 2026-10-14 · M5: boot030 identifies deferred-device and probe-operation boundaries

* Reviewed M1 `9d04195`: attempt 10 controller PASS (10.496 s), and paused
  video directly reads **P:05 S:09 W:04**. Three native strip lanes render;
  H/small fields/full transitions/userspace remain unobserved or unconfirmed.
  P=05 places progress at the first deferred-work flush by source inference.
  No exact driver, blocking PC or cause established. Macintosh HD return confirmed.
* Exact boot029 REA/Ghidra plus source/LLVM/linked bytes cover bus/platform
  wrappers: **81 instruction words, 69 nonrelocated matches**, 12 relocation
  words reviewed separately. Bus attach includes interface locking/callbacks;
  platform probe includes clocks/domain attachment before the driver callback.
* Boot030 adds **56 probe boundaries**, root/current device table IDs from
  286 public DT nodes, task attribution and a compact **four-row panel**.
  It repaints saved lanes and marks H before printk. The next native run can
  distinguish device locking/runtime PM/DMA/clocks/domains/driver entry.
  This improves diagnosis; **native hang unresolved, no new driver skip**.
* Only **Image** changes. Installed boot021, DT/config/initramfs/args and
  controller/hardware gates remain unchanged. Full Image/ELF roundtrip,
  actual helper/panel/identity/platform/parser sanitizer tests, **90 controller
  cases** and **13-file intake PASS**. Exact one-CPU/4 GiB diskless/networkless
  VZ reaches all phases/PID 1/one CPU and liveness at **60.190510 s**. Native
  AIC/MMIO/scanout and performance are not validated by these tests.
* Post-attempt-10 user policy JSON PASS: original Full/lab Permissive, exits 0.
  Independent root Macintosh HD/build 25G83/FileVault/SIP/staged m1n1 SHA PASS.
  Default/installed boot object/authenticated-root not re-queried. No host
  settings, volume, default, firmware or installed m1n1 changes.
* All test/REA VMs stopped; both shared quiet locks released.
* Next: M1 verifies private `native-j716c-boot030`, publishes offline readiness,
  then the human starts **one filmed attempt 11**. Record literal P/S/W/H/D/B/C,
  decode D/C/B offline and review early/final video through the stop criterion.
  **Native attempt 11/live checks NOT RUN.** Follow the current Stage-B checklist
  and `kernel/experiments/probe-path/`. No reinstall, automatic retry or extra
  M5 approval loop. Native PID 1/liveness precedes Linux control/input and the
  configuration agent's Omarchy handoff; GPU/SMP/idle/DVFS remain separate work.

## 2026-10-14 · M1: attempt 10 readable strip; return confirmed

* One boot029 RAM attempt at readiness `8c96579`, reviewed M5 handoff `73c5e0d`.
  **Controller exit 0, 10.496 s**; UTC 14:48:59.495128–14:49:09.991426,
  handoff 14:49:09.756446. Target boot021 marker, hardware DT, both DAPF
  checkpoints/96-byte readback, 16-byte descriptor/readback and kboot reply PASS.
* **Video reviewed:** 27.197-second `IMG_2660.mov`; sampled frames/crops through
  27.05 seconds show native Linux/deferred-probe diagnostics and literal
  **`P:05 S:09 W:04`**, unchanged at 11, 12, 13.6, 20.4 and 27.05 seconds.
  Three strip lanes visibly render. H/full transition sequence **NOT OBSERVED**;
  H is not inferred zero. Small timer/display/pending fields **NOT CONFIRMED**
  because of blur/overlap; no prior attempt's values substituted.
* Source decodes P=05 as first deferred-work flush, S=09 as scheduler exit and
  W=04 as the boundary before `bus_probe_device`. Progress beyond phase 13 is
  **inferred from P=05's source path**; phase-13 text not directly observed.
  No exact blocked driver/PC, timer fault or hang fix established.
* PID 1/userspace `online_cpus=1`/60-second liveness, readable heartbeat/stack
  and retry-compatible details **NOT OBSERVED**. Video samples do not cover
  every frame or the full observation window. Full media remains out of Git.
* **Macintosh HD return CONFIRMED by human** (“back, update”). No later
  strip/message observation supplied. Fresh protection/default **NOT CHECKED**.
  No retry, reconnect, reinstall or boot/security/volume/default changes.
* **Attempt 10 consumed.** Result: `native/boot/stage-b-2026-10-14-attempt10-result.md`.
  M5 next: read-only return checks and offline deferred-worker/device-probe
  and diagnostic-visibility analysis. Preserve boot021/client pin and gates.

## 2026-10-14 · M1: boot029 attempt 10 offline readiness PASS

* Pulled/read M5 handoff `73c5e0d`, context-display README/evidence/validation.
  Boot029 archive SHA-256
  `ebed9be8b34c3684aaf01ef06b8fc108e0c548960c1f83a25ed411c5ef42ce16`
  and 16,722,976-byte size verified **before extraction**. All **13 intake
  files**, offline launcher and reviewed controller digests PASS. Image SHA-256
  `53f5f2c5a7a2d9d0d2ae92961222090c97f0c266bb4066408acd577660e7cc32`.
* **90 M1 offline cases PASS:** 37 launcher + 6 entry + 16 DAPF + 5 framebuffer
  + 19 hardware + 2 pinned ADT/DAPF + 4 root ADT + 1 real proxy serializer;
  all exit 0, synthetic transport only. Clean client remains pinned at
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`; installed boot021 unchanged.
* Only Image/package manifest differ from retained boot028. Fresh ignored
  receipt `build/native-intake/receipts/boot029-attempt10.json` and result
  `build/native-intake/results/boot029-stage-b-attempt10.json`/`.md` prepared
  with source/procedure/controller/payload/receipt hashes; prior artifacts kept.
* **Ready for the authorized Stage B attempt 10** after publication. Human
  reports proxy running and video recording including bottom-left edge.
  Post-attempt-9 protection prerequisite already PASS per M5; no extra restart
  or review round trip. **Attempt 10 native/live checks NOT RUN at readiness.**
* Next: one reviewed RAM launch; capture display state/console_setup, literal
  enlarged P/S/W/H strip and context-switch/stack/timer/userspace evidence.
  Review recording, then Macintosh HD within existing bounds. No retry, wider
  blacklist, reinstall or settings change. Mapping success alone is not visibility.

## 2026-10-14 · M5: boot029 fixes diagnostic mapping; narrows context-switch observation

* Reviewed M1 `29f0f8e`: attempt 9 controller PASS; paused video observes
  native J716c/t6050 EL2/one CPU, counter PASS/25 ticks, phases 1/10/11/12,
  then `reschedule pending=1 strip=0`. No literal lanes, phase 13, watchdog
  stack or diagnostic userspace/liveness observed. Macintosh HD return confirmed.
* REA/Ghidra plus exact source and an actual-function regression test confirm
  the old diagnostic mapper skips absent/retired consoles. The exact native
  strip=0 prerequisite is still unknown. REA omits 31 instruction words from
  `__switch_to`; full source/LLVM/linked-byte review accounts for those paths.
  Evidence covers 152 instruction words, 126 nonrelocated linked matches.
* Boot029 fixes independent validated-DT framebuffer initialization, adds
  display-state reporting, 4× strip glyphs and context-switch subphases. It
  changes only **Image**, with no guessed register changes or expanded skip.
  Installed boot021, DT/config/initramfs/args/hardware gates remain unchanged.
  **Native hang unresolved; this is a tested diagnostic repair.**
* Full Image/ELF roundtrip, helper/renderer/parser/mapper ASan/UBSan, **15 map
  scenarios**, old-defect reproduction, **90 controller cases** and **13-file
  intake PASS**. One-CPU/4 GiB diskless/networkless VZ reaches pending=1,
  phase 13/all later phases, PID 1/one CPU and liveness at **60.192201 s**.
  Generic strip=0/display=1 is expected. No native AIC/scanout/performance proof.
* Fresh post-attempt-9 user JSON PASS: original Full/lab Permissive, both exit 0.
  Independent root Macintosh HD/build 25G83/FileVault/SIP/staged m1n1 SHA PASS.
  Default/installed boot object/authenticated-root not separately re-queried.
  No settings, volume, default or installed m1n1 changes.
* All test/analysis VMs stopped; both shared quiet locks released.
* Next: M1 verifies private `native-j716c-boot029`, publishes offline readiness,
  then the human starts **one filmed attempt 10**. Capture display state and
  literal enlarged P/S/W/H strip; review video before reporting, then return
  within the existing bound. No extra M5 approval loop or installation restart.
  **Native attempt 10/live checks NOT RUN.** Current procedure:
  `tools/m1n1-client/stage-b-instructions.md`; engineering/provenance/tests:
  `kernel/experiments/context-display/`. Stable native diagnostic userspace
  precedes Linux control/input and the configuration agent's Omarchy work.

## 2026-10-14 · M1: attempt 9 phase 12/pending=1/strip=0; return confirmed

* One boot028 attempt at readiness `87a80dd`, reviewed M5 handoff `3503bf1`.
  **Controller exit 0, 10.530 s**, UTC 2026-10-14 14:11:02.041163–14:11:12.571778;
  handoff 14:11:12.342802. Hardware DT, boot021 marker, both DAPF checkpoints,
  96-byte correction/readback, 16-byte framebuffer descriptor/readback,
  prepared args and kboot reply PASS. Installed m1n1/client pin unchanged.
* **Video reviewed**: human supplied 21.598-second `IMG_2659.mov`; paused frames
  and enlarged lower-screen crops inspected from start through 21.45 seconds.
  Native Linux, clock blacklist, J716c/t6050 EL2/one CPU, counter PASS/25 ticks
  and timer status **phys=1 virt=7 irq_masked=0 fiq_masked=0 OBSERVED**.
* Printed phase sequence **1 → 10 → 11 → 12**; final visible line
  **`reschedule pending=1 strip=0 (P/S/W/H hex)`**, unchanged in reviewed later
  samples. Phase 13/2, heartbeat, scheduler summary/stack and worker/retry
  **NOT OBSERVED**. Literal P/S/W/H lanes **NOT OBSERVED**, not inferred zeros.
* Diagnostic PID 1/userspace `online_cpus=1`/60-second liveness **NOT OBSERVED**.
  Kernel one-CPU checkpoint is observed separately. No explicit panic visible;
  exact cause unknown. Sampling/clip duration do not cover every frame or the
  whole 120-second observation window. Full media stays out of workspace/Git.
* **Macintosh HD return CONFIRMED by human** after deadline/return guidance.
  No later message reported; fresh protection/default checks **NOT CHECKED**.
  No retry, reconnect, reinstall, wider skip or settings change.
* **Attempt 9 consumed.** Result: `native/boot/stage-b-2026-10-14-attempt9-result.md`.
  M5 next: read-only return checks and offline analysis after phase 12/before
  phase 13, including scheduling/visibility and strip availability. No exact
  blocking PC or confirmed root-cause repair claimed.

## 2026-10-14 · M1: boot028 attempt 9 offline readiness PASS

* Pulled/read M5 handoff `3503bf1`, scheduling-boundary README and validation.
  Boot028 archive SHA-256
  `689fce13b00c4e59af61e5a23666509579985b89920a0477e4b107c6cf5944e9`
  and 16,722,641-byte size verified **before extraction**. All **13 intake
  files**, offline launcher and reviewed controller hashes PASS. Image SHA-256
  `514dde0c48c17d77d1979fb98b13f5ecb45096839e8b10a72d24adcf9df0778f`.
* **90 M1 offline cases PASS:** 37 launcher + 6 entry + 16 DAPF + 5 framebuffer
  + 19 hardware + 2 pinned ADT/DAPF + 4 root ADT + 1 real proxy serializer;
  all exit 0, synthetic transport only. Clean client remains pinned at
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`; installed boot021 unchanged.
* Only Image/package manifest differ from retained boot027. Fresh ignored
  receipt `build/native-intake/receipts/boot028-attempt9.json` and result
  `build/native-intake/results/boot028-stage-b-attempt9.json`/`.md` prepared
  with source/procedure/controller/payload/receipt hashes; prior artifacts kept.
* **Ready for the authorized Stage B attempt 9** after publication. Human
  confirms Running proxy and video recording including the bottom-left edge.
  Post-attempt-8 protection prerequisite already PASS per M5; no extra restart
  or M5 review needed. **Attempt 9 native/live checks NOT RUN at readiness.**
* Next: one reviewed RAM launch, capture literal P/S/W/H sequence and kernel
  timer/scheduler/stack/userspace milestones, review recording, then Macintosh HD
  under existing limits. No retry, wider blacklist, reinstall or settings change.

## 2026-10-14 · M5: boot028 closes the preemption observation gap

* Reviewed M1 `7da251d`: attempt 8 reached native J716c/t6050 EL2, one CPU,
  counter PASS/25 ticks, then timer status. Phase 2 and diagnostic userspace
  NOT OBSERVED. Video remains unreviewed; no exact hang PC or cause established.
* REA/Ghidra plus exact source/LLVM/linked bytes confirm the idle NOP branch
  already exists and boot027 can reschedule before arming its watchdog.
  Two complete bodies, 261 instruction words/163 nonrelocated linked matches;
  no new Apple binary extraction or speculative register change.
* Boot028 corrects that observation gap: watchdog armed before preemption,
  phases 10–13, bounded scheduler state/one stack and a lock-free bottom-left
  P/S/W/H status strip in existing scanout RAM. Scheduler/driver operations
  remain; only Image changes. Root cause still unknown; no wider blacklist.
* Full Image/ELF roundtrip, actual helper/renderer ASan/UBSan, **90 controller
  cases** and **13-file intake PASS**. Exact one-CPU/4-GiB diskless/networkless
  VM reports pending=1, phase 13, all remaining phases, PID 1/one CPU and
  liveness at **60.191892 s**. VM has no native AIC/framebuffer; strip visibility
  and physical scheduling remain untested. No performance improvement claimed.
* Fresh post-attempt-8 user JSON PASS: original Full/lab Permissive, both exit 0.
  Independent original root/build 25G83/FileVault/SIP/staged m1n1 checksum PASS.
  Default/installed boot object/authenticated-root not separately re-queried.
  No boot/security/volume/default changes or installed m1n1 replacement.
* Next: M1 verifies private `native-j716c-boot028`, publishes readiness, then
  the human starts **one filmed attempt 9**. Capture the strip and review the
  video; no additional M5 approval loop for unchanged verified instructions.
  Native attempt 9 **NOT RUN**. Follow `tools/m1n1-client/stage-b-instructions.md`
  and `kernel/experiments/schedule-boundary/README.md`. Preserve current setup.
  Stable diagnostic userspace precedes Linux control/input and Omarchy setup.

## 2026-10-14 · M1: attempt 8 timer/ticks PASS; phase 1 last visible; return confirmed

* One boot027 RAM attempt at readiness `174419e`, reviewed handoff `46ad887`.
  **Controller exit 0, 10.492 s**; UTC 2026-10-14
  13:38:30.894614–13:38:41.387312; handoff 13:38:41.148275.
* Target boot021 marker, final hardware DT/arguments, both DAPF checkpoints,
  96-byte correction/readback, 16-byte framebuffer descriptor/readback and
  kboot request/reply PASS. Installed m1n1/client pin unchanged.
* Fresh `IMG_2658.jpeg` **OBSERVES** native Linux, exact clock blacklist message,
  `target=j716c-t6050 mode=EL2 cpus=1`, `phase=1 device=0`,
  **`timer counter=PASS ticks=25`**, and final visible
  `timer phys=1 virt=7 irq_masked=0 fiq_masked=0`.
* Phase 2+, worker/retry/heartbeat and diagnostic PID 1/userspace
  `online_cpus=1`/60-second liveness **NOT OBSERVED**. One CPU is independently
  visible in the kernel checkpoint. No explicit panic visible; root cause unknown.
* Video recording confirmed, but video not supplied/reviewed. Human was asked
  to review its ending; no video-review result received. Full media not copied
  or committed; the still does not exclude transient later messages.
* Return instructed under the 120-second bound; **Macintosh HD desktop return
  CONFIRMED by human**. No later message reported. Fresh security/default checks
  **NOT CHECKED**. No retry, reconnect, reinstall or settings changes.
* Result: `native/boot/stage-b-2026-10-14-attempt8-result.md`. **Attempt 8 consumed.**
  M5 next performs read-only return checks and offline investigation after timer
  status/before phase 2 (preemption/watchdog setup/visibility); no proven fault
  yet. Keep passing tick evidence separate from later scheduling progress.

## 2026-10-14 · M1: boot027 attempt 8 offline readiness PASS

* Read handoff `46ad887` and deferred-probe evidence. Downloaded private boot027;
  archive SHA-256 **33c7ff4d1f8e93c929a5024ebb19b7dee825cb14e1c7bf93f7df8c5526bf6a8c**
  and 16,721,223-byte size PASS **before extraction**. All **13 intake files**,
  offline launcher and reviewed controller digests PASS. Image SHA-256
  **5a5ca64eaf2c3389e9fca226d7244150edbc8975738fe11a9304c0c996e29b64**.
* **90 M1 offline cases PASS:** 37 launcher, 6 entry descriptor, 16 DAPF,
  5 framebuffer, 19 hardware binding, 2 pinned ADT/DAPF, 4 root ADT and
  1 real proxy serializer. All exit 0; synthetic transport only.
* Clean client remains pinned at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
  Installed boot021 m1n1 unchanged. Only Image and package manifest differ
  from retained boot025; DT/initramfs/config/m1n1 remain byte-identical.
* Fresh ignored receipt `build/native-intake/receipts/boot027-attempt8.json`
  and `build/native-intake/results/boot027-stage-b-attempt8.json`/`.md` retain
  source/procedure/payload/receipt hashes. Previous packages/results preserved.
* **Ready for the authorized Stage B attempt 8** after this publication.
  Human reports Running proxy and video recording. M5 post-attempt-7 protection
  prerequisite already PASS. No extra restart or M5 review needed.
* **Attempt 8 native/live checks NOT RUN at readiness.** One reviewed launch;
  capture Hardware DT, both DAPF checkpoints, timer/tick/main/worker phases and
  diagnostic userspace/liveness. Review video; stop on failure or the existing
  time limit, then Macintosh HD. No retry, reinstall or settings changes.

## 2026-10-14 · M5: boot027 attempt 8 diagnoses deferred work and validates hardware binding

* Reviewed M1 `a2239f9` / attempt 7: native Linux progressed to
  `deferred_probe_initcall` at 1.371769 seconds after two completed late
  initializers. No panic or diagnostic userspace observed; last line is not a
  blocking PC. Macintosh HD return confirmed.
* Exact boot025 REA/Ghidra and source analysis covers two deferred-probe bodies,
  94 LLVM instruction words and linked relocations. Debugfs, deferred worker
  locks/device probes, timer/scheduling and console visibility remain possible
  causes. **Root cause unknown; no speculative additional blacklist.**
* Boot027 adds opt-in bounded timer/tick and deferred-probe phase diagnostics,
  six maximum timer-softirq heartbeats and 32 detailed driver retries. Both
  normal triggers/flushes are preserved. Only **Image** changes; the existing
  clock-debug skip stays and `ilinux_probe_diag=1` is fixed in the launcher.
* Hardware validation now checks this J716c/t6050 CPU MPIDR/family topology,
  AIC3 geometry/phandle/translation and timer routes before handoff, retaining
  live chip/board/pin/secondary/DAPF/framebuffer guards. Corrected stale intake
  receipt instructions so M1 continues Stage B instead of repeating setup.
* Full Linux 7.1.9 Image link/ELF roundtrip, **11 actual-helper ASan/UBSan
  scenarios**, **90 controller cases** and **13-file intake PASS**. Exact
  packaged Image/initramfs in one-CPU/4-GiB diskless/networkless VZ reports
  counter PASS/25 ticks in 100 ms, phases 1–9, PID 1/one CPU and liveness at
  **60.187341 seconds**. This VM does not test native M5 AIC or reproduce the hang.
* Post-attempt-7 fresh human JSON PASS: original Full/lab Permissive, both exit
  0. Independent root Macintosh HD/build 25G83/FileVault/SIP/staged m1n1 hash
  PASS. Default/installed object/authenticated-root not separately queried.
  No boot/security/volume/default changes or installed m1n1 replacement.
* **Next:** M1 verifies private `native-j716c-boot027` and latest controller,
  publishes readiness, then the human starts one filmed attempt 8. No extra M5
  approval loop. Record timer/phase/worker checkpoints and PID 1/liveness or
  first failure, return within the existing bound. **Native attempt 8 NOT RUN.**
  Follow `tools/m1n1-client/stage-b-instructions.md` and
  `kernel/experiments/deferred-probe/README.md`. Continue the existing Boot Lab
  setup; no Recovery, reinstall, repeated Stage A, automatic retry or widened skip.


## 2026-10-14 · M1: attempt 7 reaches deferred-probe checkpoint

* One boot025 attempt at readiness `9bda4dd`, reviewed handoff `995efd7`.
  **Controller exit 0, 10.433 s**, UTC 2026-10-14
  04:53:40.692574–04:53:51.122617; handoff 04:53:50.882694.
* Both DAPF checkpoints, 96-byte RAM correction/readback, 16-byte framebuffer
  descriptor/readback, target boot021 marker, final DT/arguments and kboot reply
  PASS. Only fixed `initcall_blacklist=clk_debug_init` added; package unchanged.
* Fresh photo **OBSERVES later native initcalls**: `boot_wait_for_devices` and
  `sync_state_resume_initcall` return 0; final visible line is
  `calling deferred_probe_initcall+0x0/0xb8 @ 1` at 1.371769 s.
  No returned line or panic/Oops visible. Exact blocking cause not established.
* Exact blacklist/AIC/timer log lines and rectangle count **NOT OBSERVED** in
  the supplied still; timestamp progress is observed. **Diagnostic PID 1 /
  online_cpus=1 / 60-second liveness NOT OBSERVED**. Initcall `@ 1` is distinct.
* Prior photo `IMG_2655.jpeg` was excluded; fresh `IMG_2657.jpeg` reviewed.
  Full photos/video not copied or committed; video has not been reviewed.
* Stop/return instructed at the 120-second limit. **Macintosh HD desktop return
  CONFIRMED by the human.** No later screen message reported. Fresh security/
  default checks NOT CHECKED.
* Result: `native/boot/stage-b-2026-10-14-attempt7-result.md`. M5 next performs
  read-only return checks, then exact-build deferred-probe /
  shared-dependency analysis offline. **Attempt 7 consumed**; no additional
  skip, reconnect, retry, reinstall or settings changes authorized.

## 2026-10-14 · M1: attempt 7 offline readiness PASS

* Pulled/read `995efd7` and the exact-build clock-debug evidence. Retained
  boot025 archive, all **13 files**, offline launcher and reviewed controller
  hashes PASS. New ignored receipt: `build/native-intake/receipts/boot025-attempt7.json`.
  Original receipts/packages/results remain intact; no download or rebuild.
* **69 offline cases PASS:** 35 launcher + 6 descriptor + 16 DAPF + 5
  framebuffer + 2 pinned DAPF parser + 4 root ADT + 1 proxy serializer.
  All exit 0, synthetic transport only. Clean client remains pinned at
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`; installed boot021 m1n1 unchanged.
* Package unchanged: archive `908d0a9aa88c83469738f146f464bcb3815e812e56ef1615f0168cb7ce595f86`;
  Image `8849de7c2b8e529ad5895707ed26f535993cc8ff85447c450b2c13240185a0ea`.
  Only fixed argument `initcall_blacklist=clk_debug_init` is added. All existing
  guard hashes match; no broader blacklist or arbitrary arguments accepted.
* Separate ignored `boot025-stage-b-attempt7.json`/`.md` record prepared under
  `build/native-intake/results/`, with current source/procedure/receipt digests.
  Post-attempt-6 original Full/lab Permissive prerequisite already PASS per M5.
* **Ready for the authorized Stage B attempt 7** after publication. Human
  reports Running proxy and video recording; no extra restart/review needed.
  One launch, capture exact blacklist line and later initcalls/userspace/liveness,
  then Macintosh HD under existing bounds. **Attempt 7/current live checks/Linux
  NOT RUN at readiness.** No USB opened, retry, reinstall or settings changes.

## 2026-10-14 · M5: attempt 7 ready with one optional clock-debug skip

* Reviewed M1 `039a17b`: boot025 attempt 6 passed controller/DAPF/descriptor
  gates and reached late native initialization. The screen stopped after
  `calling clk_debug_init` at 1.360189 s. No visible panic or diagnostic
  userspace/one-CPU/60-second heartbeat. Last line is not an exact blocking PC.
* Exact boot025 ELF/Image, two full REA/Ghidra function bodies and 195 LLVM
  instruction-word checks identify optional clock debugfs registration. Normal
  clock registration/consumer APIs are separate. Root cause remains unknown.
* Implemented one fixed controller argument: `initcall_blacklist=clk_debug_init`.
  Reuse **unchanged boot025**; no new kernel build or release asset. Prepared-DT
  validation rejects missing, expanded or appended blacklist changes.
* **69 controller cases PASS**, including four new argument-boundary tests;
  all **13 package files PASS**. Exact Image/initramfs in diskless/networkless
  one-vCPU/4-GiB VZ reports exactly one skipped initcall, reaches diagnostic
  PID 1/online_cpus=1 and passes the 60-second heartbeat. Native attempt 7
  **NOT RUN**; this generic VM does not reproduce/resolve the native hang.
* Post-attempt-6 human JSON PASS: original Full/lab Permissive, both exit 0.
  Independent read-only root Macintosh HD/build 25G83/FileVault=true/SIP enabled
  and unchanged staged boot021 m1n1 SHA. Default/installed object/authenticated-
  root not separately queried. No host boot/volume/security/default changes.
* **Next:** M1 pulls current main, rechecks the existing boot025 package and
  updated launcher, publishes readiness, then the human starts one filmed
  attempt 7. No extra M5 approval round trip. Capture the exact blacklist
  checkpoint, later initcall boundary and userspace/liveness or first failure,
  then Macintosh HD within existing bounds. No retry or expanded blacklist.
  Follow `tools/m1n1-client/stage-b-instructions.md`; evidence and limits are
  in `kernel/experiments/clock-debug/README.md`.

## 2026-10-14 · M1: attempt 6 reaches late Linux initialization; return confirmed

* One boot025 attempt at readiness `32f5bcf`, reviewed M5 handoff `f8e98ee`.
  **Controller exit 0, 10.391 s**, UTC 2026-10-14
  04:27:29.761928–04:27:40.153385; handoff 04:27:39.918074.
* Both **DAPF checkpoints PASS**, 96-byte correction/readback; **framebuffer
  descriptor PASS**, 16-byte data/readback. Target boot021 marker, final gates
  and kboot reply PASS. No changed pin or installed boot object.
* **Native late Linux initialization OBSERVED.** Photo shows advancing
  timestamps through 1.360189 s. Last completed visible `bert_init` returns 0;
  final line is `calling clk_debug_init+0x0/0x120 @ 1`. Human confirms screen
  stayed there until shutdown. No panic/Oops visible; exact cause not established.
* Earlier AIC profile/Initialized and `arch_timer` lines are NOT OBSERVED in
  the supplied still. Later execution supports progress beyond the prior AIC
  panic, not full interrupt/timer validation. Video was recorded but not reviewed.
* **Diagnostic PID 1 / online_cpus=1 / 60-second liveness NOT OBSERVED**.
  Initializer `@ 1` is not the diagnostic userspace milestone. Rectangle count
  not reported. Full media and raw target data not copied or committed.
* At the 120-second limit, return was instructed. **Human confirms usual
  Macintosh HD desktop return.** Fresh security/default checks NOT CHECKED.
  No reconnect, retry, reinstall or boot/volume/security/default changes.
* Result: `native/boot/stage-b-2026-10-14-attempt6-result.md`. **M5 next:**
  read-only return checks and offline exact-build clock debug initialization
  analysis. Attempt 6 consumed; no new live attempt authorized.

## 2026-10-14 · M1: boot025 attempt 6 offline readiness PASS

* Pulled/read `f8e98ee`, current checklist and AIC evidence. Private boot025
  archive verified against Git **before extraction**; offline launcher and
  **13 receipt files PASS**. Earlier packages and receipts retained.
* **65 offline cases PASS:** 31 launcher + 6 descriptor + 16 DAPF guard +
  5 framebuffer + 2 pinned DAPF parser + 4 root ADT + 1 proxy serializer.
  All exit 0, synthetic transport only; no USB opened during readiness.
* Archive (16,720,464 bytes):
  `908d0a9aa88c83469738f146f464bcb3815e812e56ef1615f0168cb7ce595f86`.
  Image: `8849de7c2b8e529ad5895707ed26f535993cc8ff85447c450b2c13240185a0ea`.
  SHA256SUMS: `aae4c401ef45457cbd03687b4325ffd0bcbe1c15fcac9bf48a1167046c3c4d5d`.
* All five reviewed controller digests match; clean client remains pinned at
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`. Actual comparison confirms only
  Image differs from boot024. Installed boot021 m1n1/marker remain unchanged.
* New ignored `build/native-intake/receipts/boot025.json` and separate
  `build/native-intake/results/boot025-stage-b-attempt6.json`/`.md` retain exact
  source/procedure/payload digests and the one-attempt evidence plan.
* Post-attempt-5 original Full/lab Permissive prerequisite already PASS per M5.
  Human reports proxy running and video recording. **Ready for the authorized
  Stage B attempt 6** after publication; no extra restart or M5 review needed.
* Capture both DAPF checks, descriptor PASS, AIC profile/final Initialized line,
  timer progress and kernel/PID 1/CPU/liveness or first failure; then return to
  Macintosh HD within existing bounds. **Attempt 6/current live checks/Linux
  NOT RUN at readiness.** No retry, reinstall or boot/settings changes.

## 2026-10-14 · M5: boot025 AIC correction ready for M1 intake

* Reviewed M1 `fcf40c1`: attempt 5 reached native early Linux, then an
  undefined instruction in `aic_init_cpu+0x9c`. Exact boot024 ELF/Image mapping
  identifies `msr s3_5_c15_c1_3, x0`, the legacy guest-timer FIQ enable write.
  The fast-IPI write is not the reported fault; restriction mechanism unknown.
* Two REA/Ghidra queries, matching linked bytes, 173 LLVM instruction-word
  checks and public m1n1/Linux source support an original restricted t6050 AIC
  profile. It preserves host timers/fast IPIs, masks guest timer sources through
  architectural registers, rejects unsupported guest IRQ/KVM paths and separates
  legacy uncore handling. Older profiles retain their capabilities.
* Full Image link and 38 actual-driver scenarios with ASan/UBSan PASS. All 65
  controller cases and 13-file package intake PASS. Exact packaged Image plus
  unchanged initramfs reaches PID 1, one CPU and 60-second liveness in diskless,
  networkless generic VZ. That VM has no M5 AIC; **native boot025 NOT RUN**.
* Boot025 changes only Image from boot024. Installed boot021 m1n1, client pin,
  DT/initramfs/config, DAPF/descriptor guards and fixed arguments stay unchanged.
  Archive `908d0a9aa88c83469738f146f464bcb3815e812e56ef1615f0168cb7ce595f86`;
  Image `8849de7c2b8e529ad5895707ed26f535993cc8ff85447c450b2c13240185a0ea`.
* Fresh post-attempt-5 human JSON PASS: original Full/lab Permissive, both exit 0.
  Independent read-only root Macintosh HD, build 25G83, FileVault=true, SIP
  enabled and staged m1n1 SHA unchanged. Default/installed object/authenticated-
  root not separately queried. No boot/volume/security/default changes.
* **Next:** M1 verifies private `native-j716c-boot025` offline and publishes
  readiness. The human then starts one filmed attempt 6 under the current
  `tools/m1n1-client/stage-b-instructions.md`; no additional M5 round trip is
  needed for unchanged verified code. Record AIC profile/final Initialized,
  timer progress, PID 1/one CPU/60-second heartbeat or first failure, then return
  to Macintosh HD. No retry/reinstall. Research and limits are in
  `kernel/experiments/aic-t6050/README.md`. No native performance claim.

## 2026-10-13 · M1: attempt 5 reaches early Linux; AIC panic; return confirmed

* One recorded boot024 attempt at readiness `e362a7f`, reviewed handoff
  `1d1be38`. **Controller exit 0, 10.421 s**, UTC 2026-10-14
  03:54:01.823993–03:54:12.246249; handoff 03:54:12.010468.
* **Both DAPF checkpoints PASS**, including the 96-byte RAM correction/readback.
  **Early framebuffer descriptor PASS** (16-byte kernel RAM data/readback),
  target boot021 marker, final preflight and kboot reply PASS.
* **Native early Linux execution/readable screen OBSERVED.** Human photo shows
  undefined-instruction Oops at `aic_init_cpu+0x9c/0x150`, then
  `Kernel panic - not syncing: Attempted to kill the idle task!`.
  IRQ initialization call trace is in the sanitized result; exact cause still
  needs matching boot024 kernel analysis. No speculative hardware diagnosis.
* Rectangle count / first chronological line / initializer pair not reported.
  **PID 1 / diagnostic online_cpus=1 / 60-second liveness NOT OBSERVED**.
  Early `nr_cpu_ids=1` is visible; it does not establish diagnostic userspace.
* Panic prompted stop/return guidance at the observation limit. **User confirms
  usual Macintosh HD desktop return.** Fresh security/default checks NOT CHECKED.
  No reconnect, retry, reinstall or boot/volume/security/default changes.
* Sanitized result: `native/boot/stage-b-2026-10-13-attempt5-result.md`.
  Full photo/video and register/address dumps not copied or committed. Phone
  video was confirmed before launch; its content has not been reviewed.
* **M5 next:** read-only return checks, then offline exact-build analysis of
  `aic_init_cpu+0x9c` and AIC feature/register handling. Attempt 5 is consumed;
  no new physical attempt authorized. Installed boot021 m1n1/client pin unchanged.

## 2026-10-13 · M1: boot024 attempt 5 offline readiness PASS

* Pulled and reviewed `1d1be38`, current Stage B instructions and early-screen
  evidence. Downloaded private boot024 separately; verified the Git-tracked
  archive SHA-256 **before extraction**, then all **13 receipt files** and
  offline launcher verification PASS. Earlier packages/receipts/results retained.
* Archive (16,720,911 bytes):
  `f7cb69153adc832cae3a66fd6159e7fd41fccc2a113d3550962a7f959edd9636`.
  Image: `6b683a2f52e769d1a23474b6807d009da8ad2e19d2168e62caba6cbbae240f7d`.
  SHA256SUMS: `c9b132f08ea093667c9abb3798315e77cc6347d28897bdfa87654d14e20a2219`.
* **65 offline cases PASS:** launcher 31, entry descriptor 6, DAPF guard 16,
  framebuffer 5, real pinned DAPF parser 2, root ADT 4, proxy serializer 1.
  All exit 0; synthetic transport only. The serializer test explicitly uses
  `M1N1_SOURCE` pointing to the existing pinned checkout; no USB opened.
* All five reviewed controller digests match. Client is clean at
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`. Actual file comparison confirms
  **only Image differs from boot022**; installed boot021 m1n1/marker unchanged.
* New ignored receipt `build/native-intake/receipts/boot024.json` and separate
  `build/native-intake/results/boot024-stage-b-attempt5.json`/`.md` retain exact
  provenance, procedure/controller hashes and the one-invocation evidence plan.
* M5-reviewed post-attempt-4 policy prerequisite already PASS: original Full,
  lab Permissive, both exit 0. No duplicate query or changes to boot/settings.
* **Ready for the authorized Stage B attempt 5.** Human has started the lab and
  confirms Running proxy plus phone video recording. After publishing readiness,
  run the documented launcher once, capture both DAPF checkpoints, descriptor
  PASS and rectangle/kernel/PID 1/CPU/liveness observations, then Macintosh HD.
* **Attempt 5/current live checks/Linux NOT RUN at readiness.** Historical Linux
  remains NOT OBSERVED. No reinstall, settings changes or automatic retry.

## 2026-10-13 · M5: boot024 early observation ready for M1 intake

* Reviewed M1 `4b1a5b9`: attempt 4 passed DAPF/preflight/kboot reply but no
  readable Linux milestone. Do not label the remaining logo a proved GPU,
  AIC or kernel failure.
* REA/Ghidra on the exact boot021 ELF confirms console clearing before the
  final kernel jump. Source + 144 LLVM instruction-word checks corroborate
  two function bodies; no proprietary decompilation needed for this blocker.
* Implemented original Linux entry rectangles and a flat-DT early framebuffer
  console; added initializer tracing. Boot024 changes only Image from boot022.
  Launcher fills a bounded/readback-checked 16-byte kernel RAM descriptor;
  the tested 96-byte DAPF RAM correction and every existing gate remain.
* Full Image build, actual C/libfdt + ARM64 assembly tests with sanitizers,
  65 Python/real-parser/proxy cases, and 13-file package intake PASS.
  Exact packaged Image + unchanged initramfs reached PID 1, one CPU and
  60-second liveness in a diskless generic VZ VM. **Native early display and
  boot024 NOT RUN**; no native performance claim.
* Fresh post-attempt-4 user JSON: original Full/lab Permissive, both exit 0.
  Independent read-only checks: original root Macintosh HD, build 25G83,
  FileVault true, SIP enabled, unchanged staged m1n1 SHA. Default/installed
  object/authenticated-root not separately re-queried. No host settings writes.
* Boot024 archive `f7cb69153adc832cae3a66fd6159e7fd41fccc2a113d3550962a7f959edd9636`;
  Image `6b683a2f52e769d1a23474b6807d009da8ad2e19d2168e62caba6cbbae240f7d`.
  REA/implementation evidence: `kernel/experiments/early-framebuffer/README.md`.
* **Next:** M1 follows `tools/m1n1-client/stage-b-instructions.md`: download
  private release `native-j716c-boot024`, verify offline, publish readiness.
  Human then starts one attempt 5 with phone video already recording, selects
  existing iLinux Boot Lab, and M1 runs the reviewed launcher once. Record
  rectangle count/last readable initializer/PID 1/liveness, then return to
  Macintosh HD. No reinstall, security/volume/default changes or auto-retry.

## 2026-10-13 · M1: attempt 4 controller/DAPF PASS; screen milestones unobserved

* One boot022 attempt at `d4209d3`: **controller exit 0, 10.458 s**, UTC
  2026-10-14 03:13:05.896584–03:13:16.354836. All preflight gates passed.
* **Both DAPF checkpoints PASS**: reviewed live layout/code/table matched;
  one bounded 96-byte RAM correction applied and read back, other entries
  retained. Handoff requested at 03:13:16.120938 UTC; kboot reply succeeded.
* Human reports unchanged logo and text too fast to read/photograph.
  **Linux kernel/PID 1/online_cpus=1/60-second liveness NOT OBSERVED**.
  No identifiable failure reported; controller success is not Linux success.
* At the 120-second limit, power-off/startup-picker return was instructed.
  **User confirms successful return to the usual Macintosh HD desktop.**
  Fresh protections/default checks NOT CHECKED. No reconnect, retry, reinstall
  or settings changes.
* Sanitized result: `native/boot/stage-b-2026-10-13-attempt4-result.md`.
  M5 should perform read-only return checks and establish an observable early-boot path
  offline before any separately authorized physical attempt. Keep passing
  framebuffer/DAPF/CPU/storage/version gates. This attempt is consumed.

## 2026-10-13 · M1: attempt 4 offline readiness PASS; awaiting explicit human start

* Pulled/read `2773a73` and the DAPF evidence/current checklist. Existing
  boot022 offline launcher verification **PASS**. All **13 receipt files**,
  retained archive and Git-tracked intake manifest still match; receipt unchanged.
* **53 offline cases PASS:** 31 launcher + 16 DAPF RAM-guard + 2 real pinned
  DAPF-parser + 4 root-ADT. All suites exit 0; fake transport/synthetic memory
  only. Prior unchanged USB/framebuffer/intake results remain applicable.
* Reviewed launcher/guard/FDT/USB-selector hashes match the handoff. Client
  clean at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`. Reuse boot022 and the
  installed boot021 m1n1/marker; no download, rebuild or reinstall.
* Proposed attempt adds a verified 96-byte RAM data-table correction after
  existing final gates. Both `DAPF layout PASS` and `DAPF RAM table corrected`
  checkpoints are required in the new evidence record; real correction NOT TESTED.
* Post-attempt-3 policy prerequisite PASS per M5-reviewed user JSON: original
  Full/lab Permissive, both exit 0. No repeat query or inter-agent approval loop.
* Separate ignored `build/native-intake/results/boot022-stage-b-attempt4.json`
  and `.md` prepared with source/procedure/payload digests and checkpoint plan.
  Prior attempts/receipts retained. **Offline ready for attempt 4; wait for the
  human's explicit start and Running proxy report before one invocation.**
* **Attempt 4 and all its live checks NOT RUN.** Linux execution remains
  NOT OBSERVED historically. No USB opened, target command or settings change
  during readiness; no automatic retry. Same bounded screen observation and
  Macintosh HD return procedure after the eventual single attempt.

## 2026-10-13 · Agent B: m1n1 handoff error traced; DAPF guard implemented

* Integrated M1 `f889133`. Boot022 framebuffer/preflight passed on hardware;
  handoff raised SError at relative PC 0x16458. Linux execution NOT OBSERVED.
* Retained ELF reproduces exact installed image. PC maps into inlined
  `dapf_init_t8110a` after an MMIO store. REA/Ghidra decompilation, GNU and LLVM
  cover 300 matching instruction words; all 319 pcode operations stay in body.
  Five table-pointer relocations verified. SError's exact triggering write is
  not established; fixed-index DAPF/GAPF mismatch is confirmed in the inventory.
* AOP has DART+GAPF, no DAPF. Original m1n1 selects its region 1 as DAPF.
  New original source guard selects DAPF metadata before any register/power
  access; full m1n1 build and 12 synthetic C scenarios with sanitizers PASS.
* Avoided a reinstall: updated controller validates live code/table/ADT and
  omits only that absent AOP entry through a readback-verified 96-byte RAM data
  write. No instruction/filter/security/persistent-file patch. Other DAPF work
  and existing board/CPU/storage/framebuffer/version gates remain active.
* Linux VM: 31 launcher + 14 guard + 2 pinned-parser + 4 root-ADT + 1 serializer
  + 5 framebuffer cases PASS. Real parser caught raw-reg length handling;
  corrected before native testing. Host guard suite expanded to 16 PASS with
  two final ordering/abort tests. Real boot022 offline verification PASS.
* All VMs stopped; quiet locks released. Code/test/provenance details are in
  `kernel/experiments/dapf-handoff/README.md` and `evidence.json`; raw REA/ELF/
  generated binaries remain ignored. No physical benchmark or native attempt.
* User's fresh post-attempt-3 read-only policy result is original Full/lab
  Permissive, both exit 0; reviewed, not independently rerun. Independent
  Macintosh HD/build 25G83, System/Data FileVault, SIP/authenticated-root and
  staged m1n1 hash checks PASS. Default/installed object not independently read.
* Next: M1 verifies new controller code against existing boot022 while M5 stays
  in macOS; human then starts one proposed attempt 4. No re-download, Recovery,
  security change or automatic retry. Native correction remains NOT TESTED.

## 2026-10-13 · M1: boot022 preflight PASS; m1n1 exception at handoff; return confirmed

* One boot022 invocation at `c5f515c`: controller exit 1, **32.059 s**,
  UTC 02:34:32.733054–02:35:04.792407 on 2026-10-14.
* **All preflight checks passed**, including the corrected prepared framebuffer,
  single-core DT and disabled storage/cpufreq. Live boot021 marker PASS.
  Handoff requested at **02:34:42.905947 UTC**; `kboot_boot` reply timed out.
* Human photo shows **m1n1 SError in EL2**, followed by `Unhandled exception,
  rebooting...`, after DT preparation and PCIe messages. Safe relative code
  offset and exact text are in the result; no raw addresses/register dump saved.
  Message proximity does not establish PCIe as the cause.
* **Linux kernel/PID 1/online_cpus=1/60-second liveness NOT OBSERVED.** Handoff
  requested is distinct from kernel execution; this is not the earlier
  preflight-only NOT RUN result. No native success or performance claim.
* **User confirms usual Macintosh HD desktop return.** Fresh build/default/
  protection checks remain for M5. No settings changes, reinstall or retry;
  boot022, installed m1n1 and clean client pin unchanged.
* M5: read `native/boot/stage-b-2026-10-13-attempt3-result.md`, perform read-only
  return checks, then investigate matching-build symbols and pinned pre-kernel
  hardware setup offline. Preserve the passing observation gate. This one
  attempt is consumed; no new live session or boot-setting changes authorized.

## 2026-10-13 · M1: boot022 intake PASS; ready for authorized attempt 3

* Pulled `3c7eae1` (descendant of `bf79263`) and read the current handoff.
  Downloaded private boot022 to its own ignored directory; verified the
  Git-tracked archive checksum **before extraction**, then offline launcher
  verification and all **13 intake-file hashes/declared revision PASS**.
* Archive (16,717,590 bytes):
  `b59db87bee50f5a2b57f65ea54e9ecd9fc07d410251bb38175001ac056ee6862`.
  Intake manifest:
  `862391dd99ee93d07c196e502196cefc869b2549274d6139d781f564b4bc50a0`.
  New receipt: ignored `build/native-intake/receipts/boot022.json`.
* **31 launcher + 5 framebuffer + 4 actual pinned-ADT tests PASS** locally,
  all offline. Reran ADT cases because the changed FDT gate/test fixture is
  in that path. Prior 20 USB tests remain applicable to unchanged selector/
  client. M5's C/serializer/intake tests are separate reported evidence.
* Reviewed source hashes match the checklist. Clean client stays pinned at
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`. Compared actual package files:
  only the Stage-B DT differs; kernel/initramfs/m1n1 and other payloads match
  boot021. The installed **boot021 m1n1 marker is correct**; no reinstall.
* M5 policy prerequisite is already PASS per `3c7eae1`: user-supplied original
  Full/lab Permissive JSON, both exit 0, reviewed by M5. No duplicate check.
* Separate ignored `boot022-stage-b-attempt3.json`/`.md` evidence prepared;
  earlier receipts and attempts preserved. **Ready for the authorized Stage B
  attempt 3**, after the human selects the existing lab and reports proxy ready.
* **Attempt 3/Linux NOT RUN; current live checks NOT RUN.** No USB opened,
  settings changed or target commands sent during intake. One invocation only,
  then observe kernel/PID 1/online_cpus=1/60-second liveness within the documented
  limits and return to Macintosh HD. No retries or boot-setting changes.

## 2026-10-13 · Agent B: post-attempt-2 policy check received and accepted

* User supplied the requested read-only helper JSON: original **Full**, lab
  **Permissive**, both exit 0. B reviewed this output, not an independent rerun.
  This completes the outstanding M5 policy prerequisite for attempt 3.
* Remote reviewed through `bf79263`; no new M1 boot022 intake report visible.
  M1 verifies boot022 and confirms ready directly to the human before restart;
  no repeat policy check or additional M5-agent approval loop is needed.
* Documentation only; no code/payload, security, volume, default or boot-object
  changes. Existing offline tests apply. Attempt 3 NOT RUN; native Linux NOT RUN.

## 2026-10-13 · Agent B: boot022 removes confirmed framebuffer packaging blocker

* Code/instructions pushed as `0bea8f2`; private prerelease
  `native-j716c-boot022` published. GitHub reports both assets uploaded and
  the archive digest/size exactly match the local verified artifact.
* Reviewed M1 `9516e0c`: attempt 2 uploaded RAM payloads, but no Linux handoff.
  Actual boot021 DT lacks the node pinned m1n1 expects; its C function returns
  success without creating that node. This is a confirmed package defect.
* Implemented a DT-only correction, plus offline/prepared framebuffer validation.
  Kernel/initramfs/m1n1 unchanged. No rebuild, Recovery or reinstall required.
* Six actual pinned C/libfdt cases PASS with ASan/UBSan in the isolated ARM64
  VM; old-package failure reproduced. 31 launcher + one real serializer case
  PASS in VM; five framebuffer and seven intake cases PASS on host. Real
  archive round trip, 13-file intake and offline launch verification PASS.
* Boot022 archive: 16,717,590 bytes, hash and toolchain recorded in
  `virtualization/jobs/022-framebuffer-handoff/RESULTS.md`. VM stopped; quiet
  locks released. No physical performance benchmark or native Linux execution.
* Fresh independent return checks: original Macintosh HD/build 25G83,
  System/Data FileVault, SIP/authenticated-root, AC and staged m1n1 hash PASS.
  Fresh policy JSON requested, pending; default/installed object not queried.
* Next: M1 verifies new boot022 while M5 remains in macOS; after policy check,
  one reviewed attempt 3, visible PID 1/one CPU/60 seconds and Macintosh HD
  return. Native fix NOT TESTED; Linux NOT RUN. Instructions updated for M1.
* Fastest Omarchy path: visible native liveness → interactive access/rootfs →
  ARM64 desktop, then measured GPU/SMP/power enablement. Driver research follows
  the actual next failure rather than delaying this concrete handoff repair.

## 2026-10-13 · M1: Stage B attempt 2 stopped at prepared-DT framebuffer gate

* One corrected attempt at `993a6af`: **exit 1, 10.202 s**, UTC
  2026-10-14 01:58:58.489367–01:59:08.692220. Package/primary/target checks
  passed; corrected ADT root access and initial board/framebuffer checks passed.
* RAM payload upload completed. Prepared-DT validation stopped with exact
  **`no enabled boot framebuffer; observation path absent`** at `fdt.py:90`,
  called by `launch.py:113`. No Linux handoff or `kboot_boot`; **Linux NOT RUN**.
  Live packaged-marker verification PASS. Missing versus disabled/mismatched
  framebuffer node remains unresolved; no raw target DT was retained.
* Human confirms return to the usual **Macintosh HD desktop**. Photo shows
  m1n1 DT preparation ending at `FDT prepared` (address omitted), consistent
  with the controller's subsequent rejection. A freeze is not established.
  Linux NOT RUN; fresh build/default/protection checks NOT CHECKED this attempt.
* Boot021, launcher and clean client pin unchanged; no volume/security/default/
  boot-object changes, no reconnect or retry. Existing offline tests remained
  valid and post-pull package verification passed. Attempt 1 evidence preserved.
* Separate sanitized result: `native/boot/stage-b-2026-10-13-attempt2-result.md`.
  Next: M5 read-only return checks and offline framebuffer investigation.
  The one corrected attempt is consumed; no further live session authorized.

## 2026-10-13 · Agent B: first Stage B stop reviewed; corrected attempt 2 ready

* Reviewed/integrated M1 `fff8b95`/`1635ff0`: target checks passed, preflight
  KeyError before upload/handoff, return confirmed, root-lookup defect fixed
  offline. Verified LazyADT/root semantics against local clean-pinned source.
  The defect fits the recorded checkpoint; exact live throw site stays uncertain.
* Reran all 31 corrected launcher tests and real boot021 offline verification:
  PASS. Reviewed M1's four pinned-parser synthetic tests and passing report;
  did not claim an independent rerun of those dependency-based tests. No new
  launcher, kernel, DT, initramfs, selector or m1n1 changes.
* Independent read-only return checks: original root/build 25G83, original
  System/Data FileVault, SIP/authenticated-root, AC, no project VM processes,
  and staged m1n1 hash/size match. User supplied fresh original Full/lab
  Permissive JSON, both exit 0; default selection/installed object not queried.
* User requests next-boot preparation and M1 repository handoff. Prepared one
  corrected Stage B attempt 2, using existing readiness without another
  permission/readiness-message loop. Preserve attempt-1 evidence. M1 must pull,
  confirm exact source hashes/pin/package, and make a new evidence record
  before one live launcher invocation. No code or payload rebuild needed.
* Refined checkpoint collection to distinguish utility setup, ADT root access,
  framebuffer, upload and handoff, retaining safe explanations. Same bounded
  one-core RAM diagnostic, no Linux NVMe/cpufreq, no new volume/security change.
* Ready for human lab boot, one M1-controlled attempt, then Macintosh HD return.
  No reboot/USB/native Linux action or benchmark in this review. Linux remains
  NOT RUN; attempt-2 outcomes must be recorded from actual observations.

## 2026-10-13 · M1: Stage B preflight failed; return confirmed; ADT lookup fixed offline

* Single authorized launcher attempt at `fff8b95`: **exit 1, 1.135 s**, UTC
  2026-10-14 01:38:53.644283–01:38:54.779211. Package/USB identity and target
  chip/packaged-marker/secondary checks passed; **KeyError** before board/
  framebuffer confirmation, payload upload or Linux handoff. No retry.
* Live packaged m1n1 marker check is now **PASS**. **Linux remains NOT RUN**;
  kernel/PID 1/one-CPU/60-second screen milestones were not reached.
* User reported “heap limit” (normal utility setup output in pinned source)
  and confirms return to Macintosh HD. New post-attempt build/default/security
  checks are not reported. No volume/security change, no reconnect during diagnosis.
* Offline: confirmed `utils.adt["/"].compatible` misuses the pinned ADT API;
  root access is `utils.adt.compatible`. Corrected locally, retained board/CPU/
  DT gates and added real pinned-parser regressions with synthetic data.
  **31 launcher + 4 new ADT tests PASS; real package offline verification PASS**.
* The defect matches the live checkpoint/type, but the raw exception argument/
  traceback was not retained, so the precise live throw site remains uncertain.
  Boot021/client pin unchanged; fix has not been tried on hardware.
* Full sanitized result/investigation: `native/boot/stage-b-2026-10-13-result.md`.
  M5 should review and perform read-only return checks. **No retries**; current
  task is offline diagnosis/reporting, not a new boot authorization.

## 2026-10-13 · M1: ready for the authorized Stage B attempt

* Pulled/read authorization `b06c56e19a172771866c6e8c8c9a490db105cc84`
  and the exact Stage B checklist. User authorizes one RAM Linux attempt after
  this readiness report, then Macintosh HD return, preserving original Full
  Security with no volume/security changes, retries or additional setup.
* Documented offline launcher verification **PASS**. **31 launcher, 20 USB
  (including four upstream fake-transport cases), and 7 intake tests PASS**:
  58 cases total, each suite exit 0. No device was opened by these tests.
* Rechecked all **13 received boot021 files** against the retained receipt and
  SHA256SUMS against the tracked digest
  `9d2b9ec1ae9dad601fb25a6536e838b57ab436160ab6ceddf208b764de41f581`.
  Payload/receipt unchanged; client clean/pinned to
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
* Launcher SHA-256:
  `96af0a81b332376d5707a8e0d52aab6aca08959743d41f510b994772ed0f8364`.
  Shared USB selector SHA-256:
  `72cc8c2a916b8964b2e4b5afc4c1aac22fe8031a2c2f8658df6882b063a47137`.
* Prepared fresh ignored `build/native-intake/results/boot021-stage-b-authorized.md`
  from the current template, plus a sanitized JSON record. They retain Git/code/
  procedure/package provenance and prior Stage A PASS separately. Prior screen
  preparation is historical; this authorized-session record is current.
* **Ready for the authorized Stage B attempt.** M1 will guide one lab boot,
  execute the documented `--launch --device auto` command once after the human
  reports m1n1 running, observe checkpoints/screen milestones, then guide return.
  No separate handshake, upstream shell/launcher or secondary startup.
* At this readiness checkpoint **Stage B/Linux and live target-version checks
  remain NOT RUN**. Runtime checks occur only during the authorized attempt.
  The controller deadline is 180 seconds; screen observation ends at the
  60-second liveness message, explicit failure or 120 seconds after handoff.
  M5 read-only return verification follows the user's return report.

## 2026-10-13 · Agent B: one Stage B RAM boot authorized, awaiting M1 readiness

* User approved one Linux RAM attempt after M1 confirms readiness, then
  Macintosh HD return, with original Full Security and no volume/security
  changes. Updated the checklist and coordination handoff; no repeat approval
  is needed for this scope.
* Rechecked original root/build/FileVault, AC power, no project VM processes
  and staged m1n1 hash/size against boot021. The prior-turn fresh user-supplied
  Full/Permissive JSON remains the current policy baseline.
* No M1 readiness report after `e2c0cc7` was visible at this preparation
  checkpoint. M1 pulls this authorization, verifies its offline controller
  suite/package and confirms ready before human shutdown.
* Documentation only: launcher, selector, payloads and client pin unchanged.
  Existing tests apply; no reboot, live USB, kernel handoff or new benchmark.
  Linux/Stage B stays NOT RUN until actual screen/controller evidence arrives.

## 2026-10-13 · Agent B: Stage A reviewed; Linux launcher USB blocker fixed offline

* Fast-forwarded M1 commits `70ad452`/`974e894`. One physical P_NOP succeeded
  in 0.158 seconds (exit 0); user confirmed Macintosh HD return. This is proxy
  evidence, not native Linux or live build-marker verification.
* Independent read-only return checks: original Macintosh HD, 26.6.2/25G83,
  original System/Data FileVault on, SIP enabled, original authenticated-root
  enabled (selected by name in the same live csrutil prompt). Staged m1n1 is
  still 3,932,160 bytes with the expected boot021 SHA-256. Installed object
  and default startup selection were not independently queried.
* The user supplied fresh read-only policy JSON after this Stage A return:
  original Full and lab Permissive, both exit 0. Privileged noninteractive
  execution required a password, so this evidence is the user's output, not
  a separate agent rerun. No policy, volume, payload or default-setting writes.
* Found the same P_01 filename assumption in Stage B's launcher. Moved M1's
  validated descriptor selector into `usb_identity.py`, reused it at live
  connection time and added `--device auto`. Missing/ambiguous/wrong/stale
  interfaces stop before opening. Paths/raw registry remain private in memory.
* The launcher owns/closes the serial transport even on interface-init failure,
  restores its deadline handler, redacts transport errors and reports safe
  preflight/upload milestones. Existing chip/build/secondary/effective-DT gates
  and fixed arguments remain. Boot021 binaries/manifest/client pin unchanged.
* Validation: **31 launcher + 16 stdlib USB identity/CLI + 7 intake tests pass**;
  real local boot021 verifies offline. Tests cover wrong pin/device, ambiguity,
  no offline discovery, timeout/interruption/cleanup and existing DT/CPU gates.
  The unchanged four upstream serializer handshake cases remain for M1's
  configured environment (the combined M1 USB suite still has 20 cases).
* Prepared `tools/m1n1-client/stage-b-instructions.md`: exact offline checks,
  proposed one-attempt RAM launch, controller/screen time bounds, no automatic
  retry, native PID-1/one-CPU/60-second milestones and macOS return evidence.
* Next: M1 verifies the changed controller; user approves one Stage B session.
  No USB port was opened, Linux launched or M5 restarted in this review.
  Native Linux/Omarchy, efficient idle/DVFS, SMP and G17 acceleration remain
  unvalidated. Asahi's current M5 table still lists these hardware blocks TBA.

## 2026-10-13 · M1: Stage A P_NOP passed; Macintosh HD return confirmed

* User started a new Stage A attempt after checker fix `70ad452`. On M1,
  discovery and connection-time re-identification found **one primary** among
  two modem interfaces: **VID/PID 1209:316d, CDC data interface 1**. No callout
  names, serial numbers or raw registry output are retained in the handoff.
* Actual command: `tools/m1n1-client/run.sh tools/m1n1-client/usb-check.py --connect`.
  **PASS, exit 0; one P_NOP replied in 0.158 seconds**, within the 10-second
  deadline. UTC start **2026-10-14T01:13:02.764830+00:00**, end
  **2026-10-14T01:13:02.922801+00:00** (2026-10-13 evening in America/New_York).
  The port closed; no retries, feature negotiation, memory/register requests
  or boot/launcher requests were sent by M1.
* After the guided power-off/held-power picker return, the user confirmed:
  **back at the usual Macintosh HD desktop**. This is user-observed return,
  not remote M5 inspection. Current build, default selection and protection
  states have not been freshly rechecked after this attempt. Earlier original
  Full/lab Permissive and FileVault/SIP/authenticated-root results are baseline.
* Local sanitized evidence: ignored
  `build/native-intake/results/stage-a-20261014T011302Z.json`, now updated with
  user-confirmed return. Boot021, original intake receipt and clean client pin
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba` are unchanged.
* This validates descriptor-based primary selection and a responding m1n1
  proxy on this setup. **Live target-version verification, Linux/Stage B and
  native Omarchy remain NOT RUN.** No runtime-version or Linux compatibility
  claim follows from P_NOP. No new test was run for this documentation update.
* M5 agent next: review the evidence and perform the planned read-only return
  checks. Stage A handshake and desktop return succeeded; do not repeat setup
  or automatically start another boot. Stage B requires separate authorization.

## 2026-10-13 · M1: Stage A stopped before handshake; USB naming fixed offline

* Controlled M5 m1n1 boot reached `Running proxy...` (user/screen observed).
  M1 discovery saw two modem callouts, but neither matched the checker's
  hard-coded `P_01` suffix. No serial port was opened and no P_NOP was sent.
  This was an identification stop, not a failed USB exchange. User confirms
  subsequent return to Macintosh HD. No fresh post-attempt protection check
  or default-selection check has been reported; the earlier checks are baseline.
* Pinned m1n1 source explains the assumption: `usb_build_serial()` uses the
  ADT serial when available; `P-0` is only the fallback. Descriptors identify
  VID/PID 1209:316d, primary CDC control/data interfaces 0/1 and secondary
  virtual UART 2/3. `usb.c` assigns the primary pipe to console/proxy. USB0,
  USB1 and USB2 screen labels do not identify the host CDC callout role.
  No actual callout names or photographs are retained in the repository.
* Fixed the local checker to walk cached macOS IORegistry USB ancestry and
  require exactly one matching primary data interface 1/class 0x0a. Missing
  metadata, unrelated devices, secondary interfaces, ambiguity and stale or
  linked/non-device paths stop before opening. There is no filename fallback.
  Bare `--connect` re-identifies the sole primary; paths/serials/raw registry
  stay in memory and are not printed or saved. Printed results include UTC
  start/end and elapsed time for the eventual single handshake.
* Validation: **20 offline tests pass**, including synthetic fallback and
  serial-derived names, secondary/wrong/missing/ambiguous identity, stale paths,
  privacy, no-open discovery and no retries. Fake transport verifies one
  serialized P_NOP with zero arguments, the 10-second alarm and closure on
  success, timeout and initialization error. M1's read-only discovery with
  M5 back in macOS finds no primary and stops without opening any port.
* Boot021, ignored intake receipt and clean client pin
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba` are unchanged. No target commands,
  security changes, installations or boots were performed during this repair.
* **NOT RUN:** live USB/P_NOP, live target-version verification, Linux and
  native Omarchy. The new metadata mapping is offline-tested, not yet verified
  with M5 in m1n1. This request prepares another Stage A attempt; do not start
  one automatically. When the user starts the next session, use the revised
  checklist, one bounded handshake without retries, then original-macOS return.

## 2026-10-13 · Agent B: Stage A authorized; M1/human execution handoff ready

* User approved one m1n1 boot, one USB handshake and return to Macintosh HD,
  preserving Full Security. This lifts the Stage A hold only, not Stage B/Linux.
* Rechecked current root Macintosh HD/FileVault, staged m1n1 package hash/size,
  AC power and no project VM processes. The user's fresh Full/Permissive policy
  result from the preceding turn remains the pre-session baseline.
* Updated the M1 checklist with explicit scope, one-time picker selection,
  unchanged default/security settings, one 10-second-bounded P_NOP, no retries,
  power-off/held-power return and sanitized outcome reporting. M1 confirms it
  has the instructions before the human shuts down the M5.
* No payload/client/handshake code changed, so prior offline tests remain valid.
  No reboot or live USB action performed here; Stage A results remain NOT RUN.
  Next: M1/human performs the approved session and publishes actual evidence.

## 2026-10-13 · Agent B: installed m1n1 handoff reviewed; return checks complete

* Reviewed/integrated M1 commit `c6f2c6f`: lab-only policy/install succeeded,
  incidental native m1n1 screen reached `Running proxy...`, original desktop
  return/default restoration user-confirmed. No USB handshake or Linux boot.
* Independently checked current root Macintosh HD, build 26.6.2 / 25G83,
  original System/Data FileVault, SIP and original authenticated-root enabled.
  The numbered csrutil OS menu reordered between invocations; verified the
  original by selecting its name in the same interactive process. Record this
  as a tooling gotcha, not a protection failure.
* Staged m1n1 still matches package size/SHA-256. This rechecks the staged file,
  not the installed boot object or the incidental runtime version.
* User supplied a fresh read-only policy result after return: original Full,
  lab Permissive, both exit 0. Updated the local ignored policy helper with
  an explicit expected-lab argument; no policy writes or privileged rerun.
* Updated Stage A/first-boot instructions to reflect completed provisioning.
  No rebuild or repeat installation is needed. Recovery's missing shasum and
  the temporary sha256 adapter remain recorded in M1's original report; the
  pinned Recovery helper and staged binary were not modified.
* Next: separately authorized controlled m1n1 boot + one 10-second-bounded
  USB P_NOP, then macOS return; after review, the one-core RAM Linux test.
  No live/native test or benchmark was run in this review. Nothing yet
  establishes native Linux/Omarchy or macOS-class hardware performance.

## 2026-10-13 · M1: lab m1n1 installation and original macOS return complete

Evidence: human-entered commands on the M5, user-reported results and screen
photos reviewed by M1; no remote M5 query by M1. Only sanitized conclusions
are retained. Raw photographs, policy identifiers and credentials are not copied.

* Lab desktop build confirmed **26.6.2 / 25G83** before paired Recovery.
  Staged helper SHA-256 matched
  `e65636d03cfb7a7000f86810fdc8888e209b99bedaa1b36ca7a125de4bf72188`.
  Recovery lacked `shasum`; a temporary same-shell function accepted only
  `shasum -a 256 FILE` and delegated to `/sbin/sha256 -q`. No helper file
  or system tool was modified. The helper/payload checks then passed.
* Read-only preflight: **exit 0; original Full; lab Full; lab paired 1TR**.
  An initial mistyped readiness variable stopped the guarded operation;
  the corrected command subsequently reached authentication and succeeded.
* Authorized lab policy update succeeded: **lab Permissive, kernel CTRR
  Disabled**, with helper postcheck **original Full / lab Permissive / paired
  1TR**. The guarded installation rechecked policy and payload before kmutil.
* User reports **kmutil exit 0; Installed yes**, and final policy check
  **original Full / lab Permissive**. This completes boot-object installation.
* **Incidental m1n1 startup observed:** user released the power button early
  during the return sequence. Their photo shows m1n1 screen output/logo and
  `Running proxy...`. User reports promptly powering off, then successfully
  returning to the usual Macintosh HD desktop and selecting **Macintosh HD
  as the default startup disk**. This is screen evidence of m1n1 execution,
  not a completed Stage A test or evidence of Linux execution. Duration and
  exact running version were not verified; USB initialization text does not
  establish a controller connection or a successful P_NOP exchange.
* **NOT RUN:** live USB connection/P_NOP, live target-version check, Stage A
  controlled handshake, Stage B/native Linux and native Omarchy. No launcher
  was run by M1. No Linux boot, liveness or performance result is claimed.
* Boot021 package/ignored intake receipt are unchanged. M1 rechecked the clean
  client pin: `57a9339ffd1876e78297b17d34dece8cff8fa1ba`. No new offline
  test run was needed for this documentation-only update; prior results stand.
* Next: M5 agent reviews this handoff and can verify original macOS protections
  read-only after return. The Full/Permissive result above was observed in
  Recovery after installation; post-return policy/SIP/FileVault checks have
  not been newly reported. Do not repeat installation. Wait for explicit
  Stage A authorization before any controlled m1n1 boot or USB connection;
  Stage B requires its own approval.

## 2026-10-13 · Agent B: authorized lab Recovery installation handoff ready

* User explicitly approved lab-only Recovery setup, Permissive Security,
  disabling kernel CTRR and m1n1 installation, preserving original Full
  Security. Earlier policy/install holds are superseded for this scope.
* Rechecked root Macintosh HD/FileVault, lab group separation and m1n1
  hash/size. AC power; no project VM process. Opened Startup Disk: it already
  shows iLinux Boot Lab selected. No selection change or Restart click by B.
* Added an original read-only `kernel/native-enablement/recovery-preflight.sh`.
  It checks exact internal APFS mounts, separate groups, build/payload,
  original/lab Full policy and lab paired 1TR, keeping identifiers in memory.
  It supports postchecks requiring original Full/lab Permissive. Staged a new
  copy beside m1n1 on verified lab Data; reread SHA-256 matches source:
  `e65636d03cfb7a7000f86810fdc8888e209b99bedaa1b36ca7a125de4bf72188`.
* Validation: 21 synthetic preflight cases (valid + 20 failures), seven
  documented-operation guard cases and all five documentation shell blocks
  pass. Tests use stand-ins; no real policy/install operation. The real
  read-only plist helper correctly identifies Macintosh HD.
* Refreshed primary Apple pairing and Asahi installation references, checked
  this host's bputil/kmutil help, and prepared one-at-a-time guarded commands.
  Policy failures prevent installation; final checks keep original Full.
* **Pending human execution:** after M1 pulls the handoff, restart into lab
  macOS, shut down/hold power for paired Recovery, run sections 5–6, then
  return to Macintosh HD and restore its default selection. No boot-policy
  change, custom-object installation or restart has occurred in this session.
  Stage A/P_NOP and native Linux/Omarchy remain **NOT RUN** and separately gated.
* Integrated M1 commit `1420572`: offline Stage A checklist and Stage B
  evidence draft are prepared, package hashes/client pin unchanged. Both
  agents' progress entries are preserved; current lab authorization is above.

## 2026-10-13 · M1: Stage A instructions and Stage B evidence draft prepared offline

* Fast-forwarded to `1607f2a` (includes requested `2438c01`) and read the current
  staging/policy handoff. B reports original/lab Full Security, both exit 0,
  from user-provided read-only JSON; M1 has not independently queried policy.
* Added `tools/m1n1-client/stage-a-instructions.md`: separately authorized
  discovery, one bounded P_NOP handshake, stop/return criteria and no automatic
  transition to Stage B. No instructions were executed against the target.
* Prepared ignored `build/native-intake/results/boot021-stage-b-prepared.md`
  from the updated result template, with source/manifest/payload hashes,
  proposed fixed invocation/arguments and separate controller/screen deadlines.
  Actual timestamps/results remain NOT RUN or NOT OBSERVED.
* All 13 package files still match the existing receipt. Boot021, receipt and
  clean client pin `57a9339ffd1876e78297b17d34dece8cff8fa1ba` are unchanged.
* Wait for explicit Recovery/security/custom-boot and separate Stage A/B
  authorization. USB/P_NOP, live target-version, native m1n1/Linux/Omarchy
  remain **NOT RUN**. No reboot, policy write, live connection or launch.

## 2026-10-13 · Agent B: user-provided policy check passes for both installations

* Reviewed the user's sanitized output from the M5 read-only helper:
  `read_only: true`, original `exit: 0, mode: Full`, lab `exit: 0, mode: Full`.
  This resolves the pending post-return policy check. Evidence is the user's
  supplied command output; B did not independently rerun the privileged query.
* The already verified m1n1 file remains staged on lab Data. No new host write,
  startup/security change, custom boot installation or restart was performed.
* Next: obtain the user's explicit authorization for the prepared lab-only
  Recovery/security/custom-boot procedure. Recheck recovery pairing and the
  target volume group in Recovery before any write. Preserve original Full
  Security. Stage A and Stage B live tests remain separately gated and **NOT RUN**.

## 2026-10-13 · Agent B: m1n1 file staged on lab Data; boot settings unchanged

* User authorized staging m1n1 while preserving original macOS. Rechecked
  the mounted lab System/Data roles and shared volume group, its separation
  from the original group, and original FileVault. Destination parents are
  real directories on lab Data; the destination file did not exist.
* Created only `Users/Shared/iLinuxBoot/m1n1.bin` under
  `/Volumes/iLinux Boot Lab - Data`, with exclusive creation and no overwrite.
  Reread bytes equal the source and tracked manifest: **3,932,160 bytes**,
  SHA-256 `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
  Sanitized local receipt: ignored `build/installer-verification/m1n1-staged.json`.
* Gave the user the administrator-only read-only policy helper command for
  their M5 Terminal. Its result is still **PENDING USER CHECK**; neither OS's
  current policy mode is inferred from earlier results. No raw policy/IDs saved.
* This is file staging only. No custom boot object installed, no startup-disk
  or security change, and no restart. Original System/personal files untouched.
  Boot021 and client pin unchanged. Live USB/P_NOP, native m1n1/Linux/Omarchy
  remain **NOT RUN**.
* Next: review the user's sanitized policy output; obtain explicit approval
  for lab-only policy/custom-boot setup before the paired-Recovery restart.
  M1 can pull this handoff and prepare the existing result template offline.

## 2026-10-13 · Agent B: M1 return report reviewed; native observation plan prepared

* Reviewed/fast-forwarded M1 commit **f34970e**. It records the user's successful
  lab setup/boot at 26.6.2 / 25G83 and return to original Macintosh HD. It does
  not claim any m1n1 or Linux boot.
* Independently read the returned M5: original root Macintosh HD, same build,
  FileVault/SIP/authenticated-root enabled. Lab System/Data are in one group
  distinct from the original; mounted lab metadata confirms the matching build.
  Lab FileVault is off, as planned. About 968.43 GB of container space is free.
* Rehashed packaged m1n1: expected 3,932,160 bytes/SHA-256 match. Lab payload
  staging is absent. No copy, policy write, custom-boot install or live test run.
* **Remaining check:** current per-OS boot-security modes need administrator
  authentication. `sudo -n` is unavailable and computer-use safety review
  blocked opening Terminal. A local read-only helper was prepared but **NOT RUN**;
  no workaround or security change was attempted. Original Full Security before
  installation remains historical evidence, not a fresh post-return result.
* Updated first-boot plan/result template with package provenance, P_NOP,
  preflight/handoff, on-screen kernel/PID 1/CPU/memory/interrupts, 60-second
  heartbeats and return evidence. Specified the proposed screen time limit and
  distinguished it from the existing controller deadline. No native USB console
  is promised; blank output requires a logging plan before further attempts.
* Next: finish read-only policy verification, stage the exact boot object, then
  separately authorized lab-only policy/custom-boot work, Stage A and Stage B.
  All live USB/m1n1/Linux/Omarchy results remain **NOT RUN**.

## 2026-10-13 · M1 handoff: lab setup and return to Macintosh HD succeeded (user-observed)

* User completed the installer-managed restart and Setup Assistant, reached
  the iLinux Boot Lab desktop, and reported `sw_vers` **26.6.2 / 25G83**.
* After guidance to shut down, use startup options and select Macintosh HD,
  the user confirmed: "I'm back at my usual Macintosh HD desktop now."
  Lab first boot/setup and return to the original desktop are therefore
  confirmed by the user's observations, not remote inspection by M1.
* No post-return original-build or security-state checks have been reported
  yet. Do not infer current Full Security/SIP/FileVault status from the return
  alone. M5 agent should perform the planned read-only verification next.
* Verified boot021 package and m1n1 client pin are unchanged. Live USB/P_NOP,
  live target-version check, native m1n1, native Linux and native Omarchy
  remain **NOT RUN**. No security/custom-boot stage is authorized by this result.

## 2026-10-13 · Agent B: lab volume created; macOS installation in progress

* User authorized lab-entry setup while preserving original macOS and stopping
  before boot-security changes. Created one empty **iLinux Boot Lab** APFS
  volume in the original internal container, without resizing partitions or
  setting a quota/reserve. Existing-volume names/roles/FileVault states match.
* Read-only original-policy check reports **Full Security**. SIP and authenticated
  root are enabled; FileVault is on. Current OS **26.6.2 / 25G83**, AC/100%,
  about 997.93 GB free after creation. No project QEMU/vzrun processes running.
  Backup completion is user-reported; destination disconnected, no content recheck.
* Full installer verification repeated: PASS. The ordinary Apple GUI opened
  successfully with no security override. The user authorized its displayed
  license; after disk selection B observed **iLinux Boot Lab** as the explicit
  installation destination, not the original Macintosh HD.
* **Partial completion:** volume created and installer destination selected.
  During the handoff the GUI advanced to installation progress, still explicitly
  targeting the lab. Completion, first lab boot and original-macOS return checks
  are unverified. No security change, custom
  boot object, startup-disk change or restart has been performed by B.
* Prepared the human/M1 restart handoff at the top of
  `kernel/native-enablement/boot-entry-setup.md`. Save remaining work and let
  Apple's installation/restarts finish, use a local lab account,
  verify the matching build and return to original macOS. No Recovery/security
  work yet. Live USB/P_NOP, native m1n1/Linux/Omarchy remain **NOT RUN**.

## 2026-10-13 · Agent B: installer contents verified without security changes

* User authorized resolving verification and stopping before volumes/boot changes.
  Found the installed SharedSupport.dmg also contains Apple's original XAR
  InstallAssistant package; the signed postinstall script explains that layout.
  Inspected only as data; no scripts or installer code executed, no images mounted.
* `pkgutil --check-signature`: **signed Apple Software**. Gatekeeper's **install**
  assessment: accepted, **Apple Installer**. Both exit 0. Official catalog and
  embedded metadata identify **26.6.2 / 25G83**, product `140-93587`.
* Verified compressed XAR table against the catalog and signed stored checksum;
  every archived/extracted checksum for all five entries passes. Compared the
  signed Payload against the installed app: **695 files, 226 directories,
  26 symlinks**, zero mismatches or unexplained additions. Three executable
  signatures pass strict/all-architecture Apple-anchor verification.
* The generic whole-app custom-omit-rule rejection remains unchanged. It was
  explained and independently checked, not suppressed or relabeled as a pass.
  No Gatekeeper exception, quarantine removal, re-signing or weakened policy.
* Added a read-only pinned-product verifier; actual run PASS and **11 synthetic
  regressions PASS**. Apple artifacts and raw receipts remain local/ignored.
  No second 18 GB download. See `native/boot/macos-installer-download.md`, D-046.
* Reviewed/integrated M1 report `dfdf8cf`: package/13 files and 26 offline tests
  pass, clean client at agreed pin. Its published observations remain below.
* Next: separately approved lab provisioning. Installer launch, live USB/P_NOP,
  native m1n1/Linux/Omarchy remain **NOT RUN**. No volume, boot policy, startup
  selection, security setting or reboot changed. If a later normal installer
  launch is blocked, stop for that specific failure; no override is authorized.

## 2026-10-13 · M1 agent: boot021 offline verification complete; live checks NOT RUN

* **Verified checkout:** `58dc2baffceda76d546b0e6fb8f101089dfd35b8`, obtained
  by a clean `git pull --ff-only`. These are the M1's observed results from
  that handoff; this report was added after pulling B's later preparation notes.
* **Archive:** downloaded private prerelease `native-j716c-boot021` and matched
  `ilinux-j716c-boot021.tar.gz` against Git's checksum **before extraction**:
  `b534680fc25dff78d8eaecfb96ed5b9733a3f408ae20cb4947722cb8163edc15`.
* **Verifiers:** offline launcher PASS against the repository manifest; intake
  PASS for all 13 files and the declared m1n1 revision. The tracked SHA256SUMS
  digest matched `9d2b9ec1ae9dad601fb25a6536e838b57ab436160ab6ceddf208b764de41f581`.
* **Tests:** 17 launcher + 7 intake + 2 fake-serial USB tests passed (26 total).
  LLVM 23.1.3 passed ARM64 assembly, link, objcopy, nm and disassembly checks.
* **Client:** clean, pinned to `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
  Package revision agreement is an offline check, not a live version observation.
* **Receipt:** retained locally at ignored `build/native-intake/receipts/boot021.json`,
  timestamp `2026-10-13T20:02:34.601710+00:00`, with `boot_authorized: false`
  and `target_version_observed_live: false`. Payloads remain under ignored
  `build/native-boot-download/`; neither binaries nor the local receipt are committed.
* **Live status:** USB handshake/P_NOP, live target-version check, native m1n1,
  native Linux and native Omarchy **NOT RUN**. Discovery only found no USB
  modem paths; no serial port was opened. This is not a failed cable test.
* **Ready for the next coordinated step:** no offline verification blockers.
  Physical testing remains on hold pending boot-entry provisioning and explicit
  authorization; B's installer assessment issue remains separately unresolved.
  No `--connect`, `--launch`, upstream launcher, boot installation, disk/security
  change or reboot was performed by the M1 agent.

## 2026-10-13 · Agent B: matching installer downloaded; native checks NOT RUN

* User authorized the 26.6.2 installer download only. Apple's softwareupdate
  completed successfully; `/Applications/Install macOS Tahoe.app` is present.
* Embedded asset plist confirms **26.6.2 / 25G83**. SharedSupport.dmg is
  18,384,624,402 bytes and passes hdiutil checksum verification. No disk image
  was mounted. Running macOS build and observed APFS volume names/roles match
  the pre-download state; no lab entry was created.
* `codesign` verification and Gatekeeper assessment reject the app's custom
  resource-envelope rules. Record this as unresolved, not as successful trust
  verification or proven corruption. Installer was not launched; no workaround
  or security exception was applied. See `native/boot/macos-installer-download.md`.
* User reports M1 offline verification finished; its published detailed receipt
  is still pending. Let M1 record its own observed results. Live USB/P_NOP,
  native m1n1, native Linux and native Omarchy all remain **NOT RUN**.
* Next: M1 publishes offline results; resolve installer assessment before a
  separately approved lab installation. No volume/boot-setting change or reboot.

## 2026-10-13 · Agent B: dedicated M5 entry procedure, no host changes

* Prepared `kernel/native-enablement/boot-entry-setup.md` at the user's request.
  Read-only checks found about 1.017 TB free, no lab entry, original FileVault
  enabled and the exact 26.6.2 / 25G83 Apple installer available (~18.4 GB).
* Proposed a second full macOS installation named `iLinux Boot Lab` in the
  current APFS container, then a lab-only custom m1n1 boot object. Described
  shared metadata/possible installer firmware effects and explicit approval.
* Checked local kmutil/bputil help, Apple pairing/volume instructions and Asahi
  stage-two source. The Recovery preflight checks separate System/Data group
  identity, payload/build and paired 1TR without saving identifiers.
* Validation: five shell blocks parse; a simulated valid preflight passes and
  eleven mismatch/error cases fail. Rehashed the actual 3,932,160-byte m1n1.
  No claim of actual Recovery, installer or native hardware validation.
* No installer downloaded; no volume, boot policy, startup setting or reboot
  changed. Next: M1 receipt, then separate authorization for the reviewed
  installation procedure, Stage A and eventually Stage B.

## 2026-10-13 · Agent B: first-boot package and corrected controller launcher

* User authorized preparation, launcher/instruction fixes and GitHub handoff,
  explicitly stopping before boot settings. Work is in the published checkout.
* Exported the three existing job-020 artifacts and matched every original
  checksum. Clean-linked unmodified pinned m1n1 in the Linux VM; prepared a
  Stage-B DT with NVMe/cpufreq disabled and a static diagnostic initramfs.
* Added an offline-default, checksummed launcher with no SMP-start, cpufreq-init,
  setup.py/PMU reset or shell. It checks chip/build/board, secondary state,
  framebuffer and the final DT before a separately approved handoff.
* Validation: 17 tests on macOS and ARM64 Linux, one real-proxy-serializer test,
  zero Stage-B schema diagnostics; diskless VM reaches PID 1 and sustains one
  CPU/heartbeats for 60 seconds. No native M5 compatibility result.
* Corrected the APFS boot-entry prerequisite, unsupported persistent USB/log
  assumptions, and HID provenance (object-tested separately, not in Image).
* Integrated M1 commit `33d99f7`, preserving its receipt tools. Seven intake
  regressions pass; its verifier accepts the actual package with boot approval
  still false. Sender manifest digest and revision metadata are included.
* Handoff: `native/boot/README.md`; job-021 results and manifest. Payload is a
  private prerelease asset, not a Git blob. M1 verifies offline and stops.
* Remaining: separately reviewed OS-entry provisioning and user approval,
  then physical P_NOP and RAM diagnostic. No boot/security/partition change.

## 2026-10-13 · Second-machine agent: native package intake ready, boot on hold

* Created ignored inbox/receipt/result directories under `build/native-intake/`.
  Added a streaming SHA-256 verifier using the sender's separately supplied
  manifest digest; checks required payloads and declared target revision.
* Recorded `57a9339ffd1876e78297b17d34dece8cff8fa1ba` as the client pin. The
  shared runner checks the revision and clean checkout before invocation.
* Seven synthetic intake regressions pass (valid receipt, corruption,
  manifest mismatch, revision mismatch, missing/extra content, links and
  traversal); both existing USB fake-transport tests pass with the pin guard.
* Added an approved-boot result template with provenance, observations,
  timeout/recovery and explicit NOT RUN defaults. No real package or result
  has been received, and no USB connection or boot command was attempted.
* Per user: wait for corrected single-core launcher and boot-entry procedure;
  upstream linux.py stays on hold. First live action is bounded handshake,
  followed only by approved diagnostic boots and recorded observations.

## 2026-10-13 · Second-machine agent: LLVM and non-mutating USB checker

* Installed a minimal official LLVM 23.1.3 macOS ARM64 toolchain inside ignored
  `third_party/`; SHA-256 matches GitHub's release asset digest. The archive
  is removed after extraction. No global install or PATH changes.
* Actual upstream ARMAsm builds `nop; ret` for ARM64 ELF: clang, lld,
  objcopy, nm and objdump pass, including exact expected instruction bytes.
* Added an explicit USB connection checker: only P_NOP, 10-second bound,
  no setup.py, feature negotiation, memory/register access or boot request.
  Fake-serial tests verify the serialized request and close-on-timeout.
* Default discovery opens nothing; no device is detected. Explicit serial
  opening can interrupt target autoboot into proxy mode. No M5 session run.
* Remaining: verified backup (user reports in progress), cable, approved
  target entry/version, physical check and checksummed Stage-B artifacts.

## 2026-10-13 · Second-machine agent: proxy client prepared offline

* Prepared ignored m1n1 checkout at the plan's `57a9339ffd1876e78297b17d34dece8cff8fa1ba`
  and a workspace venv with upstream-pinned construct/pyserial wheels.
* Python 3.9.6 imports proxy/proxyutils/shell/HV successfully; pip dependency
  check passes. The local offline checker opens no devices. No USB modem
  path is currently present, and no hardware session was attempted.
* User reports the M5 backup is in progress. Remaining: verified backup,
  data cable, target m1n1 entry/version, physical handshake, checksummed
  job-020 payload transfer, and LLVM tools for assembly-dependent operations.
* Flagged upstream shell's startup panic-counter reset and home-directory
  history, and `linux.py`'s need for `--compression none` with raw `Image`.
* Handoff/check command: `tools/m1n1-client/README.md`. No target boot,
  security change, host-wide package installation or upstream edit.

## 2026-10-13 · Second-machine agent: GitHub checkout setup

* Downloaded the private `nickyrice04/ilinux` repository on the user-designated
  second macOS machine; local `main` tracks `origin/main`.
* Git 2.50.1 is installed; GitHub CLI 2.102.0 authenticated as `nickyrice04`
  with credentials in the OS keyring. Git fetch and push dry-run succeeded;
  GitHub reports push permission. This entry is the real push verification.
* Set repository-local commit identity to the account's GitHub noreply
  address, fast-forward-only pulls and simple pushes.
* Recorded user authorization for GitHub handoffs and cross-machine
  coordination limits. No native boot, USB proxy test or build performed.
* Next: prepare/check the second-machine m1n1 proxy environment and cable
  before the separately authorized native gates. Ignored build artifacts
  and VM disks are absent from this checkout.

## 2026-10-13 · Agent B: native CPU dispatch, idle hooks and startup guard

* **Investigated:** REA/Ghidra completed six CPU/idle queries; 872 instruction
  words match original bytes and LLVM. `enableCluster` pseudocode is rejected;
  two bounded idle hooks and selected mapping/writer paths were reviewed.
* **Implemented:** an original read-only kernel-collection reference parser.
  Twelve PMGR dispatch entries resolve to exact symbols; eleven stored
  call-site discriminators agree. Seventeen synthetic parser tests pass on
  ARM64 Linux; all 43 analysis-tool Python tests pass on the host.
* **Corroborated:** a further 51-instruction slice connects the literal
  `clusters` property to the descriptor pointer read by the startup routine.
  This strengthens H2 but does not prove live branch/register semantics.
* **Implemented/tested:** a conservative public-m1n1 startup guard and
  actual-function harness: one baseline regression reproduced; eight patched
  cases pass under GCC and Clang ASan/UBSan. Mismatch has zero startup writes
  or shared-state changes. Complete patched `smp.c` compiles to ARM64 `smp.o`.
  The first object attempt exposed a missing copied header; setup fixed and
  the final batch passed. No boot image linked or deployed.
* **Next:** A can use the optional guard after testing the unmodified native
  baseline. B's remaining question is live branch/register-map selection,
  followed by GPU/display and idle/context restore. A owns native builds,
  DT validation and C's handoff. The analysis VM is stopped; B's lock released.
* **Handoff:** `reverse-engineering/findings/cpu-startup-2026-10-13/handoff.md`
  (F-076/F-077, D-042). No native compatibility or performance gain claimed.

## 2026-10-13 · Agent B: driver-interface REA and Linux input robustness

* **Investigated:** GPU/display, N1 network/Bluetooth, ANE host API, ISP,
  audio/mic and HID/shared transports. REA/Ghidra completed 17 functions;
  Apple LLVM and original bytes agree on 1,107 instruction words. Four
  whole-function pseudocode results are rejected; others remain reviewed
  static evidence with explicit unresolved dispatch/ownership.
* **Implemented/tested:** local DockChannel HID bounds/cleanup/rearm patch,
  against pinned Asahi source; seven actual extracted driver functions in
  ARM64 Linux. Ten baseline regressions reproduce, all pass after patch,
  plus three valid cases (Clang ASan/UBSan). Full kernel-object/native tests
  remain pending; the VM virtio-input driver is unchanged.
* **Measured:** synthetic parser median 29.581 → 29.868 ns/packet (+0.97%),
  six 10-million-packet runs. This is software overhead, not physical input
  latency or power. No hardware performance gain claimed.
* **Implemented:** original ACIPC geometry/span helpers and strict N1
  operational-config extraction; 8,525,654 arithmetic cases and 18 Python
  tests pass in Linux. Real AirshipDK ring functions were located behind
  DriverKit stubs and analyzed through a narrowly extracted ELF carrier.
* **Next:** A's native build can consume the standalone HID patch; B's
  next REA questions are N1 descriptors/ordering and ISP firmware startup.
  The tested ISP pool/scaler command IDs and sizes match existing Linux.
  C still configures a native installation only after the existing gates.
* **Handoff:** `reverse-engineering/findings/driver-interfaces-2026-10-13/handoff.md`
  (F-073–F-075, D-041). No macOS, boot, firmware or live-VM changes.

## 2026-10-13 · Agent B: isolated REA/Ghidra and native SMP evidence

* **Implemented:** diskless Linux analysis lab, Ghidra 12.1.4 ARM64 native
  decompiler build with JDK 21 and REA 6.4.0; safe kernel-payload/member
  extraction and provenance checks. No live Omarchy disk or A-owned changes.
* **Observed:** the actual ARM64e carrier includes PMGR/CLPC/SoCTuner/NVMe;
  the visible `.kc` files are Intel. Four REA driver dossiers obtained;
  all 554 instruction words independently cross-checked with LLVM and the
  original carrier. Three pseudocode results fail function-boundary checks.
* **Implemented/tested:** original evidence gate, sanitized ADT layout audit
  and portable C startup-mask prototype. The latter exercises existing SMP
  hypothesis H2 without MMIO. 24 Python tests pass on macOS and ARM64 Linux;
  C tests pass with Linux GCC and macOS ASan/UBSan, including 18-core
  uniqueness and 5,984 valid single-cluster masks.
* **Limits:** experimental Alpine provider environment; unknown collection
  fixups/cross-member dispatch; candidate mask semantics, RVBAR and physical
  SMP remain unverified. No native performance or compatibility gain claimed.
* **Handoff:** `reverse-engineering/findings/rea-native-2026-10-13/handoff.md`
  (F-070–F-072, D-040). Analysis VM stopped and `quiet` released. A continues
  vmpoll/F-050; agent C's native configuration role stays behind native gates.

## 2026-10-13 · Agent A, goal 4: fixed VA-API driver is the VM default

The user assigned agent A goals 4–7. Goal 4 done:

* **Shipped** `vm-integration/etc/environment.d/70-ilinux-vm-video.conf`, so
  desktop-launched `mpv`/FFmpeg use `mesa-virgl-video-ilinux` by default
  (lossless-download fix + NV12 decode), no `ilinux-video` wrapper (D-032).
* **Verified** after a fresh boot: a session-launched `mpv r2160.mp4` loads
  `/usr/lib/ilinux-va/virtio_gpu_drv_video.so`, `Using hardware decoding
  (vaapi)`, `VO: [gpu] 3840x2160 vaapi[nv12]`; download regression 0/180
  mismatched; GL and Vulkan unchanged (F-055).
* **Gotcha recorded:** `sudo -u omarchy` bypasses `environment.d`, so VM
  session tests must launch through the session (`systemd-run --user`).
* **Not done:** on-screen visual capture (hyprlock idle-lock blocked grim;
  decode is frame-exact and the zero-copy display path was validated earlier,
  F-048/F-051). A fresh floating-window power run is offered, not taken.
* **Goals 5–7 note:** A owns them per the user. B's RE/driver-interface work
  feeds A as evidence; A owns the native build/validation (5), backup prep
  (6) and the handoff kit (7). Confirm with the user if B expects to own any.

## 2026-10-13 · Agent A: DT compatible audit (and a correction)

Audited the draft t6050 DT's compatibles for probe-readiness. **Result: the
DT is already correct — schema-clean and probe-ready; no change needed.**

* **Correction:** my job-020 report of "248 DT schema warnings" was a grep
  error. The filter matched any log line containing `t6050`, which caught
  warnings for *other* Apple SoC DTBs whose allowed-enum text lists
  `apple,t6050-*`. Attributed by dtb-path prefix, **`t6050-j716c.dtb` has 0
  dtbs_check warnings.** Fixed the filter in `run.sh`; corrected F-056,
  RESULTS.md and AGENTS.md.
* **Probe audit** (`kernel/experiments/t6050-dt/probe-audit.sh`, run against
  the built tree): every bring-up-critical device matches a driver on its
  t6050 string or generic fallback (AIC, DART, mailbox, PMGR, NVMe, SART,
  pinctrl, cluster-cpufreq, WDT, I²C, UART). The only non-matches are the 18
  CPU cores (`apple,sotra-m/p`) — correct, as CPUs are core-enumerated and
  both names are already in `cpus.yaml` (like M4's `apple,donan-e/p`).
* Probe *matching* is confirmed; actual *probing* and firmware startup remain
  runtime questions for the first native session.

## 2026-10-13 · Agent A, goal 5+7: native kernel build and handoff kit

Per the user, goals 5 then 7 are prioritized; goal 2 is checkpointed below
and goal 3 deferred unless they block native work.

**Goal 5 (native kernel build + first-boot plan), in progress:**

* Read the native-enablement plan and both REA handoffs. Separated this
  machine's facts from inherited M5 Pro reports: m1n1 single-core boot and
  the SMP failure are M5 Pro reports (chip-id 0x6050); this unit is an M5 Max
  (also 0x6050), so single-core boot here is Likely, not Confirmed, and the
  SMP failure is not a local observation. Recorded in the first-boot plan.
* **Reproducible full build** as job `020-t6050-full-build` (runs in the
  Linux guest toolchain, not the live-VM measurement path): fetches pinned
  AsahiLinux/linux `77cb8f24`, applies the committed t6050 series (0001-0007,
  am exit 0), configures a 16 KiB-page bring-up kernel (framebuffer console,
  initrd, Apple drivers, dockchannel), builds `Image` + modules + DTBs, runs
  `dtbs_check`, builds the **real in-tree `dockchannel-hid` driver** baseline
  vs the a351bff hardening patch (new-vs-baseline warning diff), and makes a
  static diagnostic initramfs. Build results committed separately.
* **[First-boot plan](kernel/native-enablement/first-boot-plan.md):** the
  credible early-boot observation path is the **m1n1 USB proxy** (second
  machine, pre-Linux) plus the **framebuffer console** (simpledrm on mBoot's
  framebuffer) — **not** dockchannel-UART serial, USB Ethernet, keyboard or
  SSH (each needs a missing driver or a boot-policy change). Staged tests A-E
  with expected output, failure checkpoints and uniform recovery (RAM-only;
  force-off → macOS). The exact next physical test needing user approval is
  gate N1 + Stage A (m1n1 proxy reads chip-id 0x6050).
* Fixed two build-script issues found in the first run: no `/usr/bin/time` in
  the guest (removed), and non-idempotent re-runs (now reset+clean+re-am).

**Goal 7 (config-agent handoff kit):** `native/handoff/` — VM-only files not
to apply natively, what carries over, a hardware matrix with fallbacks
(consuming B's driver-interface findings, no RE duplicated), how agent C gets
network (USB Ethernet / the second machine, since N1 Wi-Fi has no driver),
a read-only `acceptance-checks.sh`, and guardrails.

**No native boot, host-security, partition, firmware or git-history change
was made.** No native support is inferred from VM success.

## 2026-10-13 · Agent A, goal 2: cross-vCPU wakeup latency (CHECKPOINTED)

Checkpointed 2026-10-13 and deferred per the user, pending native work. The
`cpuidle-vmpoll` interim fix is committed (`f4baf47`); the `TIF_POLLING_NRFLAG`
kernel change and idle-power re-measure are **not started**. Resume only if
latency blocks native development.

* **Root cause found (F-054).** A cross-vCPU wakeup costs about 21 µs
  (one vCPU: 1.6 µs; macOS: 3.8 µs). With Apple's in-kernel GIC,
  Hypervisor.framework parks an idle vCPU inside `hv_vcpu_run`, and arm64
  always IPIs the CPU it wakes.
* **Implemented:** `omarchy-arm64/kernel/vmpoll`, a cpuidle driver with a
  bounded POLL state before WFI. A/B/A results:
  * cross-vCPU: 21.2 → 13.3 → 20.9 µs;
  * unpinned: 36.6 → 13.3 → 39.8 µs;
  * same-vCPU unchanged; idle QEMU CPU unchanged.
* **Fixed:** `cpubench pingpong` now pins each end (`-c A,B`).
* **Deferred next (not started):**
  1. Repeat the matrix plus an idle-power ABBA under the `quiet` lock.
  2. Add `TIF_POLLING_NRFLAG` to arm64 in the VM kernel, build `vmpoll` in,
     rebuild the package and validate (IPI-free wakeups of polling vCPUs).
  3. Re-test F-050 (goal 3).

## 2026-10-12 · Linux Mesa video: lossless downloads and NV12 decode

* **Root cause found (F-054).** A cross-vCPU wakeup costs about 21 µs
  (one vCPU: 1.6 µs; macOS: 3.8 µs). With Apple's in-kernel GIC,
  Hypervisor.framework parks an idle vCPU inside `hv_vcpu_run`, and arm64
  always IPIs the CPU it wakes.
* **Implemented:** `omarchy-arm64/kernel/vmpoll`, a cpuidle driver with a
  bounded POLL state before WFI. A/B/A results:
  * cross-vCPU: 21.2 → 13.3 → 20.9 µs;
  * unpinned: 36.6 → 13.3 → 39.8 µs;
  * same-vCPU unchanged; idle QEMU CPU unchanged.
* **Fixed:** `cpubench pingpong` now pins each end (`-c A,B`).
* **Next:**
  1. Repeat the matrix plus an idle-power ABBA under the `quiet` lock.
  2. Add `TIF_POLLING_NRFLAG` to arm64 in the VM kernel, build `vmpoll` in,
     rebuild the package and validate (IPI-free wakeups of polling vCPUs).
  3. Re-test F-050 (goal 3).

## 2026-10-12 · Linux Mesa video: lossless downloads and NV12 decode

* Continued from commit `4d8987e`; audited existing kernel patches, VM,
  benchmarks and current Asahi evidence. The top native gaps are boot/SMP,
  G17 GPU/DCP and idle/DVFS, with precise uncertainties in
  `reports/bottleneck-priorities-2026-10-12.md`.
* **Implemented and installed** `mesa-virgl-video-ilinux 26.2.4-1` in the VM:
  opt-in NV12 H.264 decode plus lossless NV12/I420/YV12 CPU downloads.
  Source/recipe: `omarchy-arm64/packages/mesa-virgl-video/`.
  Use `ilinux-video mpv FILE` in the guest; system Mesa/GL/Vulkan stay intact.
* **Validated:** final VA image/crop tests 18/18, zero incorrect bytes
  (stock: 37,008); 1,440/1,440 hardware-decoded 1080p/4K frames match software
  in the final matrix; installed package repeats it and passes another
  240/240 Baseline/Main frames. mpv hardware-decode/EGL
  smoke passes 120 frames. Package builds and installs; `pacman -Qkk` passes.
* **Measured:** paced 4K60 decode, two ABBA blocks, QEMU CPU use falls from
  0.2962 to 0.17385 cores (**41.3%**). Whole-SoC power is noisy; no energy or
  display-performance gain is claimed. F-052/F-053, D-031.
* **REA:** actual metadata evidence for the renderer and AppleVideoDecoder
  arm64e, plus bounded LLVM disassembly of the H.264 factory. REA deep
  analysis reports missing backends; no successful decompilation claimed.
* **Corrected F-045:** current failure is cross-format download, not every
  CPU readback. An experimental dirty-flag change failed to fix it and was
  removed. The final fix bypasses shader conversion for lossless 4:2:0.
* **Limits:** VM only; shader conversions outside the even/progressive
  fast path, decode fences, other codecs and native hardware remain open.
  Full method, evidence, build limits and next work:
  `reports/video-download-and-nv12-2026-10-12.md`.
* No macOS system, boot, firmware, partition, security or personal-data edits.

### Next

1. Investigate F-050's intermittent guest display stall using DRM fence and
   compositor timing evidence.
2. Run controlled on-screen playback/power comparisons with the NV12 driver.
3. Trace the remaining shader conversion path (odd crops, scaling, interlace)
   and add proper decode-fence lifetime handling before async host decode.
4. Prepare full native-kernel/schema validation and a reviewable, explicitly
   authorized native boot experiment; do not infer hardware support from VM tests.

## 2026-10-12 · Display path: measured stage by stage; mpv defaults; methodology fix

### Discovered

* **mpv's default scaling was most of VM video power** (F-048).
  * 4K60 hardware playback: 7.3 W with mpv's defaults (linear-light
    downscaling, wide filters, dithering), 3.9 W with `profile=fast`.
  * Decode alone is 3.0 W.
  * The guest display chain itself is cheap: a fullscreen 60 fps client that
    only clears costs about +0.8 W over idle.
* **Hidden windows are never drawn** (F-049).
  * During the VM runs the VM window was off screen, so QEMU and
    WindowServer presented nothing. The native player's window was on screen.
  * So the `COCOA_GL_NOPRESENT` A/B compared two non-presenting runs, and
    VM-vs-native playback ratios aren't like for like yet.
  * F-046 is corrected accordingly.
* **Hyprland direct scanout brings no saving in the VM.** Every flip becomes a
  scanout switch in QEMU, so it stays off.
* **mpv `--vo=dmabuf-wayland` fails.** The compositor can't import VA-API
  surfaces through virgl.
* **Intermittent vsync collapse to about 10 fps** in 3 of 6 fresh boots
  (F-050, open). Six causes were ruled out by measurement, including the
  screensaver, the notification overlay, CPU placement and App Nap.

### Implemented

* **QEMU 0012:** display-path measurement switches. `COCOA_GL_NOPRESENT=1`
  consumes guest frames without drawing them; `COCOA_GL_LATENCY=1` logs
  flush-to-draw latency.
* **Benchmark tools:**
  * `benchmarks/linux/vfill.c`: a fullscreen Wayland EGL client at a fixed
    fps, with full-frame damage and per-second frame counters.
  * `benchmarks/src/winvis.m`: reports whether a process has windows on
    screen, by PID, without reading titles.
  * `benchmarks/src/occlude.m`: covers the VM window, for App Nap tests.
* **`playback_power.py`:**
  * new `vfill-*` and mpv render-path cases;
  * a per-case `vm_window_on_screen` record;
  * refuses to run with a hidden VM window unless `--allow-hidden` is given.
* **macOS `playback_power.py`:** records whether the player window was on
  screen.
* **VM mpv defaults:** `vo=gpu` and `profile=fast`, alongside VA-API.

### Measured

* **Present vs no-present** (ABBA, 4 sessions): no difference. Invalid as a
  presentation measurement (F-049).
* **mpv render paths, 4K60 hardware decode:**
  * defaults: 7.28 W with `vo=gpu`, 5.92 W with `gpu-next`;
  * fast profile: 3.88 W with `vo=gpu`, 3.85 W with `gpu-next`;
  * decode alone: 3.03 W.
* **Unpaced FIFO steady state:** 120 fps; 205 s with no input showed no
  throttling.

### On-screen follow-up (same day, VM window floated with your OK)

* **Presentation measured with the window on screen** (`COCOA_FLOAT=1`).
  * 4K60 playback with the VM defaults: 3.60–4.14 W, against 2.91 W native
    (71–81%).
  * Presenting is about +0.3 W of that.
* **Latency: a guest frame waited 6–8 ms** (p95 11–13 ms) for QEMU's GUI
  tick, and only 70–80% of 120 fps output was drawn.
* **QEMU 0013, drawing on flush, is the new default** (D-030, F-051): p50
  0.14 ms, p95 about 2 ms, every frame drawn at 60 and 120 fps, no measured
  power change.
* **IOSurface presenter (opt-in, `COCOA_GL_PRESENT=iosurface`):**
  * p50 0.12 ms, and 0 torn frames in 1,200 alternating-colour frames;
  * but +0.8 W at 4K60 (ABBA);
  * Apple's GL crashes rendering into lossless-compressed IOSurfaces.
* **Vsync collapse (F-050) narrowed:**
  * it strikes alternating fresh boots, in every configuration tried;
  * it is not presentation, the window state or App Nap.
* **Tools:**
  * `vfill -a`: alternating colours, for tearing tests;
  * `winvis` now counts floating windows.

### Next

1. **F-050:** trace guest DRM flips and fences, and Hyprland's frame
   scheduling, in an affected boot. Affected boots alternate, so the boot
   after a healthy one should reproduce it.
2. **A Metal-side presenter** with compressed, framebuffer-only drawables.
   It may give the IOSurface path's p95 without its video cost.
3. **Then video encode, HEVC/VP9 decode, and the guest Mesa fixes**
   (dirty decode targets, NV12-only).

## 2026-10-12 · Hardware video decode in the VM: VA-API on VideoToolbox

### Discovered

* **The virgl video protocol isn't version-stable** (F-042). Mesa 26 sends
  shifted profile values (H.264 High = 11) and virgl format numbers. Its VA
  frontend offers I420, so FFmpeg-based players ask for 3-plane surfaces.
* **VA-API omits the PPS reference-index defaults** (F-043). They have to be
  learned from slice headers, or VideoToolbox rejects B-frames.
* **`kCVPixelBufferOpenGLCompatibilityKey` changes VideoToolbox's output.**
  With IOSurface-only output, decode is bit-exact (F-044).
* **Mesa's virgl decoder has no decode fence and never marks targets dirty**
  (F-045). Zero-copy consumers work; CPU readback returns stale data.
* **Apple's `glClientWaitSync` busy-polls** (F-047). virglrenderer's fence
  thread spun while waiting:
  * 17% of its samples during 4K60 playback, 3% under GPU-bound glmark2;
  * polling with sleeps saves about 0.3–0.4 W in 4K60 playback (ABBA
    A/B) at unchanged glmark2 throughput (528 fps).
* **Decode is no longer the gap to macOS** (F-046):
  * VM hardware decode alone: +1.1 W over idle at 4K60.
  * *Corrected later the same day:* the rest of the VM's +5.1 W was mpv's
    default scaling, not frame copies (F-048). Host presentation was not
    measured, because the VM window was off screen (F-049).

### Implemented

* **virglrenderer 0008:** a VideoToolbox backend for virglrenderer's video
  interface.
  * H.264 Constrained Baseline, Main and High.
  * IOSurface planes are blitted into the guest's surfaces on the GPU.
  * Pictures are fenced back to VideoToolbox's pool.
  * Planar targets go through a VTPixelTransferSession.
* **virglrenderer 0009:** shader-translation fix (TEX temporary writemask).
* **virglrenderer 0010:** GL fence waits poll and sleep on macOS.
  `VIRGL_GL_FENCE_WAIT=block` restores the old wait for A/B runs.
* **QEMU 0011:** `virtio-gpu-gl,video=on`.
* **Launcher and build:** video is on by default (`--no-video` opts out,
  D-029), and the build uses `-Dvideo=true`.
* **Benchmarks:**
  * `benchmarks/vm/playback_power.py` with the guest helpers in
    `benchmarks/vm/guest/` (playback and decode-only cases, ABBA order);
  * `benchmarks/macos/playback_power.py`, with `benchmarks/src/avplay.m`
    as the native AVFoundation reference.
* **Research:** `research/testing/stress-and-stability-methodology-2026-10.md`
  (65 sources):
  * reviewer methods (30-minute Cinebench loops, 3DMark 20-loop stability);
  * M5 Max sustained results;
  * proposed pass tiers T0–T3;
  * a summary of the reference stress-test video (no transcript).
* **VM integration:** `/etc/mpv/mpv.conf` (`hwdec=vaapi`, `gpu-api=opengl`),
  so plain `mpv file` decodes on the media engine with mpv's default
  `gpu-next` renderer.
* **Blockers:** Touch ID recorded as out of scope (B-014), with
  libfprint USB readers and FIDO2 keys as the Linux alternatives.
* **Validation:**
  * A from-scratch rebuild applies every patch (virgl 0001–0010, QEMU
    0001–0011).
  * The rebuilt source trees match the working trees file for file.
  * The rebuilt runtime decodes the 600-frame test clip bit-exact.
  * Omarchy.app was rebuilt.

### Measured

* **Function:**
  * `vainfo` lists `VAProfileH264High`, Main and Constrained Baseline.
  * A 1080p60 High-profile B-frame clip decodes bit-exact against FFmpeg:
    600/600 frames, 0 errors.
  * mpv plays 4K60 and 1080p60 in real time through zero-copy dmabuf
    interop, dropping 0–2 frames per 1,500.
* **Playback power** (SoC, AC, 25 s windows):

  | Clip | Native macOS | VM, hardware | VM, software |
  |---|---|---|---|
  | 4K60 | 2.91 W | 7.04 W | 17.34 W |
  | 1080p60 | 2.36 W | 4.33 W | 6.72 W |

  Hardware decode saves 59% at 4K60. The VM uses 2.4× native's power for
  4K60 playback.
* **Flat-out throughput, 4K60 clip:**
  * hardware 155 fps at about 1 vCPU, mostly guest kernel time waiting on
    QEMU's lock;
  * software 508 fps on 8.4 vCPUs.
* **Main-thread profile, 4K60 hardware playback:**
  * 20% blocked in VideoToolbox decode;
  * 5% CPU in the NV12→I420 conversion;
  * about 1% in GPU copies.

### Still unsupported or open

* **Decode coverage:** HEVC, VP9 and AV1 decode, and VA-API encode on
  VTCompressionSession.
* **CPU readback of decoded surfaces:** needs a guest Mesa fix (F-045).
* **The I420 conversion:** a guest Mesa change offering only NV12 for
  decode would remove it.
* **Synchronous decode on QEMU's main thread:** making it asynchronous
  needs completion tracking in vrend (F-045).
* **~~Presentation costs about 4 W at 4K60~~:** corrected. It was mpv's
  scaling (F-048). Host presentation is still unmeasured (F-049).

### Next

1. **Presentation path:**
   * QEMU's Cocoa display presenting the guest scanout as an IOSurface
     layer (zero-copy into WindowServer);
   * check Hyprland direct scanout in the VM;
   * rectangle sampling in vrend for zero-copy imports.
2. **Guest Mesa patch:** dirty decode targets and NV12-only decode
   surfaces.
3. **HEVC and VP9 decode, then encode;** test Chromium's VA-API path.
4. **Defaults:** make hardware decode the default in the VM's mpv and
   browser configuration.

---

## 2026-10-12 · Vulkan in the VM: Venus on MoltenVK, presenting at 120 Hz

### Discovered

* Venus bring-up on macOS needed six host-side fixes: proxy init,
  stream sockets, partial reads, FIFO eventfd, no `MAP_FIXED` under HVF,
  and the info-table entry (F-035).
* HVF never mapped sub-page blobs, and its data-abort handler retried the
  guest's store forever: vkcube spun in `memcpy` (F-036).
* Apple's GL binds IOSurfaces only as rectangle textures, so vrend's
  import (`GL_EXT_memory_object_fd`) failed. That put the compositor's
  context in error: a scrambled or blank desktop (F-037).
* Metal→GL IOSurface access is ordered once the Metal work is *scheduled*
  (0/300 stale frames) but not after `commit` alone (F-037).
* Vulkan FIFO lost about a quarter of its frames to Mesa's commit-timing
  targets in the VM (F-038).
* gdb can't attach in the guest (SME without SVE); `eu-stack` works (F-039).

### Implemented

* **virglrenderer 0007:** IOSurface mirror import for Venus images on native
  CGL. A Metal blit, or a swizzle pass for RGBA, feeds a GL
  rectangle→2D blit. It waits only until the copy is scheduled, and
  unsupported formats degrade instead of breaking the compositor.
* **QEMU 0010:** host-page rounding for blob subregions; HVF rejects
  unaligned host pointers instead of aborting.
* **VM session:** `MESA_VK_WSI_DEBUG=nowlts` via `environment.d` (D-028).
* **Launcher:** Venus is on by default (`--no-venus` opts out, D-027).
  Omarchy.app was rebuilt.
* **Tools:**
  * `benchmarks/vm/vkbench.sh`: vkcube fps and CPU;
  * `benchmarks/src/vkcompute.{c,comp}`;
  * guest `vkmark` and `glmark2` installed for later runs.
* **Validation:** a full from-scratch rebuild applies every patch (virgl
  0001–0007, QEMU 0001–0010) and boots.

### Measured

* **vkcube (1272×679 RGBA16F, 2592×1458@120 output):**
  * FIFO 119.5 fps (was 92.9; before 0010 it never presented);
  * mailbox about 3,000 fps;
  * mirror 0.12 ms per update (0.87 ms with a completion wait).
* **vkcompute:** 10.6–11.0 TFLOPS, 94–98% of native MoltenVK 11.24, bit-exact.
  Submit+wait p50 381–390 µs vs 204 µs native.
* **glbench with Venus/blob on vs off:** 0.99–1.17×, no regression.

### Still unsupported or open

* **Zero-copy presentation.** It needs IOSurface-backed Venus memory plus
  rectangle sampling in vrend.
* **Real vblank pacing from QEMU.** That is the root fix for F-038.
* **Venus round trips are 1.9× native.** Feedback and ring-wakeup latency.
* **Watch item.** Two guest shutdowns stalled for minutes, with 137 virtio-gpu
  commands in flight, while the fixed bugs were present: the store-retry
  loop, and the compositor in context error. They have not reproduced on the
  final build (clean 3 s shutdowns after vkcube and vkcompute).
  `tools/vm-restart.sh` samples QEMU if one recurs.

### REA gap analysis (same day)

* **Inventory:** a metadata-only REA inventory of 727 driver bundles and 887
  launchd plists, joined with the ADT and the live IORegistry.
  * Outputs: `hardware/macos/*.tsv` and
    `reverse-engineering/macos-hardware-services.md`, a 23-row gap matrix
    with priorities and VM bridges.
  * Security components were excluded before recording.
* **New findings:** F-040 (the CLPC/SOCTuner/PPM/PTD policy layer is the
  efficiency gap) and F-041 (RTKit coprocessors throughout).

### Next

1. **Host-side bridges the gap matrix points to:**
   * VideoToolbox decode/encode remoting;
   * a Core ML/ANE API for the guest;
   * camera as a UVC device;
   * paced vblank timestamps.
2. **Zero-copy Venus presentation.**
3. **Battery and Low Power Mode measurements under Vulkan load.**

---

## 2026-10-12 · Microphone, kernel package, Omarchy.app

### Implemented

* **QEMU patch 0007:** CoreAudio capture through an AudioQueue. The guest
  sees a working capture source. A live recording was not tested on the
  user's machine (privacy).
* **`linux-ilinux-vm` pacman package:** built, installed and booted, and it
  owns its modules. The limine boot integration and the stock kernel were
  removed from the VM (D-026).
* **`Omarchy.app`:** a Mach-O stub, launch script and bundled signed QEMU.
  Its window and Dock identity show as "Omarchy". LaunchServices launch from
  the agent shell is blocked by Gatekeeper (ad-hoc signed plus provenance);
  the user approves it once.

### Next

1. Vulkan in the guest: Venus via MoltenVK or KosmicKrisp. This needs new
   source downloads, so it needs approval.
2. GPU texture-upload and draw-call gaps (blob or zero-copy resources).
3. fsync-heavy storage: an ext4 data volume option, or lower virtio latency.
4. Battery and Low Power Mode measurements (the machine was on AC so far).
5. Native track: an m1n1 read-only session needs separate authorization.

---

## 2026-10-12 · Storage, clipboard, host agent, idle refresh

### Implemented

* **Host agent** (`tools/ilinux-host-agent`, launcher-managed) and guest
  `ilinux-host-bridge`: Mac battery, a clock step right after host sleep
  (tested: a 30 s lag was fixed within one cycle), and time zone. No polling
  in the guest.
* **Storage:**
  * virtio-blk runs on a dedicated iothread with 4 queues, doubling
    random-I/O scaling;
  * QEMU patch 0005 makes `cache.direct` use F_NOCACHE on macOS (it was
    O_DSYNC);
  * `storbench syncwrite` added (F-033, D-023).
* **Clipboard sharing with macOS:** QEMU built with spice-protocol
  (`qemu-vdagent`), plus a stdlib-only guest vdagent clipboard agent for
  Wayland (wl-clipboard) and a udev `uaccess` rule. Tested both directions
  (D-022).
* **QEMU patch 0006, adaptive display refresh:** a hidden window caused a
  redraw-request storm (1 guest frame vs 1832 requests in 20 s).
* **Housekeeping:** deleted the obsolete ext4 `root.img` (13 GB).

### Measured

* **Storage vs native:** warm 4K QD1 reads at 101%; 32 threads at 42% (was
  20%); cold sequential reads with F_NOCACHE at 100%; write+fsync at 22%
  (btrfs dependent-I/O chain).
* **Microphone:** QEMU's CoreAudio backend has no capture
  (`max_voices_in = 0`). A capture voice needs writing, ideally with an app
  bundle so macOS attributes the microphone prompt to it.

---

## 2026-10-12 · Efficiency pass: CPU heterogeneity, App Nap, GPU fences, power

### Discovered

* **App Nap (F-027):** a hidden QEMU window naps the whole VM, putting every
  vCPU at PRI 4 on M cores, about 4× slower.
* **macOS QoS on M5 Max (F-028):** only `background` QoS reaches the M cores.
  `utility` behaves like `default`.
* **VirGL fences (F-030):** on macOS they were polled every 1 ms, costing
  about 1.5 ms per guest GL sync. QEMU enabled the sync thread only for EGL,
  and virglrenderer needs eventfd.
* **Idle power (F-032):** an idle Omarchy VM costs only +0.09 W SoC. The
  earlier +0.38 W reading included post-login churn and a lingering test
  user manager.

### Implemented

* **Workspace QEMU and virglrenderer patches:**
  * `bg-vcpus` heterogeneous vCPUs: host QoS plus guest
    `capacity-dmips-mhz` (D-019);
  * `app-nap=on|off|auto` (D-020);
  * event-driven VirGL fences with a pipe-backed eventfd (D-021).
* **Launcher:** `--hetero`, `APP_NAP` (default `auto`), and the guest time
  zone follows the Mac (`ilinux.tz=`).
* **`omarchy-qos`:** `RESERVE_EFFICIENT_CPUS=auto` keeps system and
  foreground slices off much-slower efficient CPUs, plus a system unit
  `omarchy-qos-system.service`.
* **Tools:**
  * `benchmarks/src/glbench.c`: the same GL 4.1 code on CGL and EGL;
  * `benchmarks/vm/{vm_power_states,hetero_placement}.sh`;
  * `tools/power_{summary,table}.py`;
  * `vmconsole.py`: robust completion marker.

### Measured (`reports/vm-vs-macos-parity.md`)

* **GPU vs macOS GL:**

  | Test | Parity |
  |---|---|
  | ALU | 99.7% |
  | Blended fill | 74% (was 17%) |
  | Readback | 61% (was 23%) |
  | Draw calls | 50% |
  | Texture upload | 28% |

* **CPU:** foreground single-thread is 99% of native. The background tier
  gives 1.84× (1 thread) and 2.25× (6 threads) more work per joule than
  foreground.
* **Idle:** +0.09 W (`app-nap=auto`) and +0.14 W (`off`) over host-only
  1.713 W.

### Next

* Texture-upload and draw-call gaps: blob or zero-copy resources, and Venus
  (Vulkan) via MoltenVK or KosmicKrisp.
* Battery-mode measurements (on battery and in Low Power Mode).
* Package the kernel for pacman.

---

## 2026-10-12 · Session 2: Omarchy 4 desktop in a GPU-accelerated VM

### Implemented

* **Guest system:**
  * Omarchy 4.0.4 (aarch64 edge) on btrfs (`@`, `@home`, `@log`, `@pkg`,
    zstd) with snapper (D-013).
  * Kernel v2: 7.1.6 with 16K pages and uclamp, the full ALARM module set,
    essentials built in (D-014).
  * Network: Quad9 with DoT (D-015).
* **GPU compute from Linux:** guest llama.cpp → ggml RPC → vsock (vzrun
  `--vsock-forward`) → host Metal `ggml-rpc-server`.
* **GPU desktop:** QEMU 11.1.1 (HVF) + VirGL 1.3.0 + upstream libepoxy, all
  built from pinned sources in the workspace (D-012). The launcher is
  `virtualization/qemu/run-omarchy-gpu.sh`.
* **Fixes we wrote:**
  * libepoxy: a missing `libEGL` no longer aborts. Every GL lookup probed
    EGL first.
  * QEMU Cocoa patch: stable Retina window size, window size sent to the
    guest at launch, app name from `-name`.
  * Omarchy shell under Qt 6.12: the `QtQuick/Color` type shadowed the
    shell's `Color` singleton, leaving a black, empty bar. Fixed with a
    self-disabling pin plus a pacman hook (D-017).
* **Mac integration:**
  * the battery bridge feeds IOKit data over virtio-serial into
    `test_power`, so UPower and the bar show the Mac battery;
  * SDDM autologin (D-016);
  * opt-in full-screen Space and full keyboard grab (D-018).

### Tested / measured

* **ggml RPC:** Q4_0 8B prefill 2737 t/s (**89%** of native Metal),
  generation 85.1 t/s (**81%**). Socat `nodelay` was essential: with delayed
  ACK, generation was 23%.
* **Guest renderer:** `virgl (Apple M5 Max)`, OpenGL 4.1 core, GLES 3.0
  (Mesa 26.2.4).
* **Desktop:** Hyprland 0.56.2 at 2592×1458 at 120 Hz, scale 2. The bar,
  notifications and lock screen are themed (screenshots taken in the guest
  with `grim`).
* **Idle desktop cost:** QEMU used ≈ 3.4% of one host core with the desktop
  idle. Omarchy's idle chain works: screensaver at 150 s, lock at 300 s, then
  DPMS off, after which the guest stops rendering.
* **Native series (job 018):** `git am` on asahi 77cb8f24 is clean. `sart.o`
  and nvme `apple.o` build with 0 errors and 0 warnings, and
  `t6050-j716c.dtb` builds.

### Still unsupported / next

* No Vulkan in the guest (Venus/MoltenVK not built). No microphone capture
  with the CoreAudio backend.
* GPU benchmark (guest VirGL vs native GL) and host power: idle desktop vs
  macOS idle.
* Package the custom kernel for pacman. Guest timezone should follow the
  Mac's.

---

## 2026-10-11 · Native-enablement research pass (m1n1, Asahi Linux, PMGR/DVFS, drafts)

### Discovered

* **m1n1 (`57a9339`) on t6050:** single core plus NVMe read. SMP is still
  broken: cores power on but never run m1n1 code (PR #610). The cause is
  Unknown; ranked hypotheses are in `kernel/native-enablement/plan.md` §1.2.
* **M5 MPIDR:** M cores are 0x4XXYY and P cores 0x1XXYY (F-019). The old
  draft DT would have had every CPU node pruned by m1n1. Fixed.
* **Our ADT, decoded:**
  * the PMGR table: 661 records, 6 blocks, a second die at +0x21_0000_0000
    (F-021, F-024);
  * CPU DVFS: M 15 states up to 4.380 GHz, P 20 states up to 4.608 GHz
    (F-022);
  * SART `sart-version = 4`, the NVMe M4+ layout, and per-CPU
    `function-enable_core` (F-020, F-023).
* **AsahiLinux/linux:** `asahi` already has the NVMe firmware-ABI series.
  No branch has SARTv4 or the M4+ NVMe register split.
* **Idle:** m1n1 forces `idle=nop arm64.nowfxt` on M4+ (F-026).

### Implemented

* **`adt_extract.py`:** wider whitelist, full binary tables, and a
  content-based leak check (`--check-only`). Re-extracted: 0 problems.
* **The DT generator:** now covers PMGR power domains (188), MPIDR-correct
  CPUs, OPP and energy-model data, cpufreq, disabled DART/SART/NVMe drafts.
  `validate.sh` fixed and strict: **0 dtc warnings**.
* **Local patch series `kernel/patches/t6050/0001–0007`:** SARTv4, the NVMe
  M4+ split, bindings, and the DT. Untested; compile test pending. Not for
  upstream.
* **`kernel/native-enablement/plan.md`:** a dependency-ordered plan for items
  (a)–(j).

### Next

1. Compile-test the series and run `dtbs_check` in the VM, once it is free.
2. A native m1n1 read-only diagnostics session. This needs user
   authorization and a deployment plan.
3. Draft the SPMI gen-4 driver and a dockchannel-uart console driver.

---

## 2026-10-11 · Session 1: foundations, baselines, VM track, energy

### Discovered

* **Exact hardware:** MacBook Pro Mac17,6 (J716c), **Apple M5 Max = t6050**
  (`chip-id` 0x6050, SoC generation tag "H17", CPU family SOTRA).
  * 6 P ("Super", 16 MiB L2) + 12 M ("Performance", 2 × 8 MiB L2) cores;
    the ADT cluster type is `M`.
  * 40-core G17X GPU, H16-generation ANE (exclave-mediated), 128 GiB,
    2 TB ANS3 SSD.
* **ISA:** SME/SME2/SME2p1 (SVL 512) without non-streaming SVE. MTE present.
* **Linux status for t6050:**
  * No DT and no kernel bring-up. m1n1 has initial T6050 support with no SMP.
    GPU (G17), ANE, ANS3 NVMe, the N1 Wi-Fi chip, DCP and others have no
    Linux drivers.
  * **Asahi forbids generative-AI contributions** (2026-09-08), so this
    project's outputs stay local (D-007).
* **macOS QoS:** background work runs on M cores at ≈ 25% of P-core
  throughput, at **≈ 4× better energy per FLOP**.
* **SME:** one engine per cluster. The P-cluster engine gives 2.17 TFLOP/s
  FP32 (rail `PCPM` ≈ 9.8 W); the chip saturates at 3.23 TFLOP/s.
* **GPU:** FP16 GEMM ≈ 64 TFLOP/s (matrix units) vs 17.6 scalar. Core ML's
  planner prefers the GPU over the ANE on M5 Max.
* **ANE:** 14.0 TFLOP/s FP16 on a 1×1-conv stack at ≈ 3.6 W. Proven by the
  ANE energy counter and MLComputePlan.
* **Microarchitecture:** M5 P-core FMA throughput drops ≈ 11% when all FMLAs
  read the same two source registers (F-016). This explained a fake "112%
  VM parity".
* **Omarchy 4 already supports aarch64 upstream** (edge). Real `pacman` in
  our VM resolves the full default set: 842 packages, 0 unresolved.
* **VM facts:** SME2 is passed through. MIDR is masked. Wakeups cost 21–52 µs
  vs 3.8 µs native. Virtio storage reaches 3–30% of native.

### Implemented

* Benchmarks:
  * `cpubench` (freq, fma, **fma_asm**, intmix, sort, sgemm, SME f32/bf16/i8,
    pingpong, syscall);
  * `membench` (STREAM, latency incl. DIT/DMP-off, faults);
  * `storbench`;
  * Metal `gpubench`;
  * **`powermon`** (no-root IOReport energy and DVFS sampler).
* Model generators: `tools/synth_gguf.py` and `tools/synth_mlx.py`
  (synthetic models with identical shapes for llama.cpp and MLX).
* Analysis helpers: `tools/compare_results.py` (parity tables);
  `hardware/scripts/{adt_extract,ioreg_driver_map,kext_personalities}.py`.
* **VM track:**
  * `virtualization/vzrun` (Virtualization.framework runner: direct kernel or
    EFI boot, virtiofs, NAT, nested, NVMe and disk-mode options);
  * GPG-verified Arch Linux ARM image build;
  * the scripted job runner.
* **omarchy-qos** (QoS tiers via systemd slices, cpuset, uclamp), VM-tested
  and with one bug fixed.
* **Draft t6050 DT** (CPUs, AIC3, timer, WDT, 3 × pinctrl, 9 × I2C, UART),
  compile-checked with a workspace-built `dtc` 1.8.1. Local only.
* REA 6.4.0, project-local (`tools/rea`, `.mcp.json` and deny-list settings in
  `~/Documents/iLinux`). MLX, mlx-lm and coremltools in `tools/venv`.

### Tested and measured (highlights; see `reports/performance-parity.md`)

| What | Result |
|---|---|
| macOS CPU, 1 P core / 18 cores (asm FMA) | 140.8 GFLOP/s / 1.89 TFLOP/s |
| macOS SME f32, 1 thread / chip | 2.17 / 3.23 TFLOP/s |
| macOS STREAM, 18 threads (median) | ≈ 369 GB/s copy |
| macOS GPU FP16 GEMM / copy bandwidth | 64 TFLOP/s / 537 GB/s |
| macOS SSD seq read / write | 11.0 (13.3 at 4 threads) / 11.2 GB/s |
| llama.cpp Metal 8B Q4_0 | pp512 3090 t/s, tg128 105 t/s, ≈ 0.56 J/token |
| MLX 8B 4-bit / Gemma-3-12B bf16 | tg 100.8 / 21.7 t/s |
| ANE (Core ML conv stack) | 14.0 TFLOP/s at ≈ 3.6 W |
| **Linux VM vs macOS** (identical code and flags) | CPU compute 97–101%, SME 97–100%, STREAM 93–100%, DRAM latency 72–84%, syscalls 77%, wakeups 7%, storage 3–57% |
| omarchy-qos in VM | 5/5 pass; uclamp skipped (no `CONFIG_UCLAMP_TASK_GROUP` in the ALARM kernel) |

### Still unsupported or blocked

* Native Linux on t6050 (B-001), GPU (B-002), ANE (B-003), NVMe (B-004),
  Wi-Fi (B-012).
* GPU acceleration inside VMs needs host installs such as krunkit (new
  approval).
* No Linux-side energy counters yet.
* Strict BLAS-free llama.cpp prefill comparison on macOS needs `cmake`
  (not installed).

### Next

1. ✅ (2026-10-11) VM llama.cpp CPU comparison (F-017) and VZ storage-mode
   matrix (F-018). Follow-up: `fsync` default plus pre-allocation in `vzrun`.
2. Build a guest kernel config with `CONFIG_UCLAMP_TASK_GROUP` (and possibly
   16K pages) to test omarchy-qos clamps and the VM memory overheads.
3. Omarchy VM install: keyring, `omarchy-arm64-vm` integration package,
   Hyprland on llvmpipe smoke test.
4. Propose GPU-in-VM experiments (krunkit/Venus; llama.cpp API remoting) to
   the user for approval.
5. Decode the PMGR `devices`/`ps-regs` tables to extend the DT draft with
   power domains (local research).
