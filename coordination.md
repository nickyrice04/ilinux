# Coordination: agents working in this workspace

Created 2026-10-13. Read this together with `AGENTS.md`, `progress.md`,
`blockers.md` and `decisions.md` before starting work. If this file and an
older plan disagree, this file wins for ownership and order of work.

## Roles

### Current M5 handoff — boot032 / attempt 13 reserved-GPIO repair prepared

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

### Historical M1 result — attempt 12 main-GPIO cache boundary; return PASS, 2026-10-14

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


### Historical M1 readiness — boot031 / attempt 12 offline PASS, 2026-10-14

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

### Reviewed M5 handoff — boot031 GPIO cache/IRQ handoff repair; attempt 12 prepared

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

### Reviewed M1 result — attempt 11 decoded pin-controller boundary; return pending, 2026-10-14

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

### Historical M1 readiness — attempt 11 PASS, 2026-10-14

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

### Reviewed M5 handoff — boot030 / attempt 11, 2026-10-14

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

### Reviewed M1 result — attempt 10 P:05 S:09 W:04; return confirmed, 2026-10-14

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

### Historical M1 readiness — attempt 10 PASS, 2026-10-14

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

### Reviewed M5 handoff — boot029 / attempt 10, 2026-10-14

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

### Reviewed M1 result — attempt 9 phase 12; video reviewed; return confirmed, 2026-10-14

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

### Historical M1 readiness — attempt 9 PASS, 2026-10-14

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

### Reviewed M5 handoff — boot028 / attempt 9, 2026-10-14

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

### Reviewed M1 result — attempt 8 timer/ticks PASS; return confirmed, 2026-10-14

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

### Historical M1 readiness — attempt 8 PASS, 2026-10-14

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

### Reviewed M5 handoff — boot027 / attempt 8, 2026-10-14

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


### Historical M1 result — attempt 7 later initcalls; return confirmed, 2026-10-14

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

### Historical M1 readiness — attempt 7 PASS, 2026-10-14

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

### Reviewed M5 handoff — attempt 7 / unchanged boot025, 2026-10-14

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

### Historical M1 result — attempt 6 late Linux init; return confirmed, 2026-10-14

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

### Historical M1 readiness — boot025 attempt 6 PASS, 2026-10-14

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

### Reviewed M5 handoff — boot025 / attempt 6 offline ready, 2026-10-14

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

### Historical M1 result — attempt 5 early Linux panic; return confirmed, 2026-10-13

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

### Historical M1 readiness — boot024 attempt 5 offline PASS, 2026-10-13

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

### Reviewed M5 handoff — boot024 early observation ready for M1 intake

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

### Historical M1 result — attempt 4 controller PASS; return confirmed, 2026-10-13

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

### Historical M1 readiness — attempt 4 checks PASS, 2026-10-13

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

### Reviewed M5 handoff — DAPF correction, 2026-10-13

Latest: attempt 3 passed all boot022 preflight gates, then m1n1 raised an
SError during DAPF setup; Linux execution NOT OBSERVED. Exact-image ELF/REA/
GNU/LLVM analysis and the sanitized ADT expose a fixed-index DAPF/GAPF mismatch.
An original source guard builds/tests, and the current launcher implements a
narrow verified 96-byte RAM work-list correction for the unchanged installed
m1n1. Boot022 payload unchanged. Native correction NOT TESTED. M1 must verify
updated controller code offline before the human starts one proposed attempt 4.
Fresh user-supplied policy JSON: original Full/lab Permissive, both exit 0.
Independent original build/FileVault/SIP/authenticated-root and staged m1n1
checks pass. No host boot/settings changes. Current instructions:
`tools/m1n1-client/stage-b-instructions.md`; evidence and limits:
`kernel/experiments/dapf-handoff/README.md`.

M5 completed offline analysis/implementation; all test VMs are stopped and both
quiet locks released. M1 owns the new offline verification and sanitized result
record. Reuse boot022; no download/reinstall/Recovery. The native change is a
RAM-only data-table correction, not a new persistent boot object. Previous
attempt 3 is consumed. Do not reconnect or launch merely to verify the code;
wait for the human to start the proposed single attempt after readiness.
Preserve original Full Security, all existing gates/time bounds and macOS return.
The supplied post-attempt-3 policy result is current; no duplicate query needed.

### Historical M1 result — attempt 3 m1n1 exception; return confirmed, 2026-10-13

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

### Historical M1 readiness — boot022 intake PASS, 2026-10-13

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

### M5 handoff reviewed by M1 — boot022 / Stage B attempt 3, 2026-10-13

Code and checklist: `0bea8f2` or later. Download:
https://github.com/nickyrice04/ilinux/releases/tag/native-j716c-boot022
Both assets published; remote archive digest and size verified against local.

Latest: Stage B attempt 2 never handed off to Linux. Boot021 lacked m1n1's
required framebuffer placeholder. Job 022 reproduces this with the actual
pinned C function and corrects only the Stage-B DT; boot022 is verified offline.
Kernel/initramfs/installed m1n1 unchanged; the boot021 marker remains correct.
M1 must intake boot022 before one reviewed attempt 3. The user's fresh read-only
post-return JSON reports original Full/lab Permissive, both exit 0; reviewed,
not independently rerun. Native correction NOT TESTED, Linux NOT RUN. Original root/build,
FileVault/SIP/authenticated-root and staged m1n1 were independently rechecked.
No volume/security/default/boot-object changes. Current instructions:
`tools/m1n1-client/stage-b-instructions.md`; evidence:
`virtualization/jobs/022-framebuffer-handoff/RESULTS.md`.

M5 owns the completed DT-only package and regression. M1 owns offline intake,
one bounded live controller invocation after readiness and human lab selection,
sanitized screen/checkpoint evidence and original-macOS return. Do not reinstall
m1n1 or repeat Recovery. Download/verify before restart; no extra readiness
round trip through the M5 agent is required once intake and policy checks pass.
Use a separate attempt-3 record; preserve prior failures. Keep original Full
Security and the existing single-core RAM scope. No automatic retry.

Policy prerequisite is now satisfied. At this update, GitHub main still ends at
`bf79263`, with no M1 boot022 intake report visible. M1 can complete intake and
confirm readiness directly to the human; do not request the same M5 policy
check again before this attempt. No new boot or settings change was performed
while recording the supplied result.

### Historical M1 result — Stage B attempt 2 stopped; return confirmed, 2026-10-13

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

### Consumed M5 handoff — corrected Stage B attempt 2, 2026-10-13

The user requests review, next-boot preparation and repository instructions
for M1 after the lab boot. B reviewed/fast-forwarded `fff8b95` and `1635ff0`:
attempt 1 failed before upload/handoff; the ADT root-lookup defect is confirmed
against the pinned source. Keep its original evidence immutable. Linux NOT RUN.

The next step is one fresh Stage B attempt with M1's corrected launcher. This
current user direction authorizes that reviewed continuation, not an automatic
retry of the consumed attempt. Original Full Security, no volume/security/
boot-object/default changes, no SMP or storage expansion. No repeat approval
or redundant readiness-message round trip is needed for this exact scope.

M1's 31+4 corrected-code tests and unchanged USB/intake readiness remain valid;
B independently reran 31 launcher cases, checked the ADT API, and verified the
real package. Launcher/payload/pin unchanged by B. Read-only M5 checks: original
Macintosh HD/build 25G83, original System/Data FileVault, SIP/authenticated-root,
AC, no project VMs, staged m1n1 hash match. The user supplied fresh read-only
original Full/lab Permissive JSON, both exit 0. Default/installed-object checks
were not rerun and are not inferred from this policy result.

Human may shut down and pick iLinux Boot Lab once. M1 then pulls/reads
`tools/m1n1-client/stage-b-instructions.md`, confirms listed source hashes/pin
and offline package verification, creates a distinct attempt-2 evidence record,
and executes the launcher once after the human reports proxy ready. Record the
new RAM-utility/ADT checkpoints as well as screen milestones, stop at the
specified bounds and return to Macintosh HD. Publish sanitized actual results.
No new native action occurred in B's review; attempt 2 remains NOT RUN.


### Historical M1 result — 2026-10-13: Stage B attempt 1 failed; return confirmed; ADT lookup fixed offline

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

### Historical M1 readiness — 2026-10-13: ready for the authorized Stage B attempt

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

### Consumed authorization — one Stage B attempt after M1 readiness, 2026-10-13

The user explicitly approves one Stage B Linux RAM boot after M1 confirms
readiness, then return to Macintosh HD. Keep Macintosh HD at Full Security;
no volume/security changes. This supersedes earlier Stage B permission holds
for this exact session. No repeat permission question is needed.

M5 preparation: current root Macintosh HD, original System/Data FileVault on,
build 25G83, AC power, no project VM processes, staged m1n1 matches boot021.
The user's fresh original Full/lab Permissive result from the preceding turn
remains the policy baseline. No code/payload changed since `e2c0cc7`; the
existing M5 test results apply, with no redundant run.

At this preparation checkpoint no M1 readiness commit after `e2c0cc7` is
visible on GitHub. M1 must pull this authorization, complete/report 31 launcher,
20 USB and 7 intake cases plus package verification, and confirm ready before
the human shuts down M5. Use `tools/m1n1-client/stage-b-instructions.md` for
one `--device auto` launcher attempt with the existing boot021/client pin.
No separate P_NOP, retry, shell, SMP start, installation or Recovery operation.
Stop at success/failure/time bound, return via the held-power picker to
Macintosh HD, and publish sanitized actual results. Linux remains NOT RUN
until observed; the M5 agent has not restarted or opened USB during preparation.


### Current M5 handoff — Stage B prepared offline, 2026-10-13

B reviewed/integrated `974e894`: Stage A P_NOP PASS and user-confirmed desktop
return. Read-only M5 checks now confirm original build 26.6.2/25G83, original
System/Data FileVault, SIP/authenticated-root and unchanged staged m1n1 hash.
The user's fresh post-return JSON reports original Full/lab Permissive, both
exit 0; B reviewed that output, not an independent privileged rerun. Default
startup selection and the installed boot object were not newly inspected.

B fixed Stage B's stale P_01 filename gate by sharing M1's descriptor selector
through `tools/m1n1-client/usb_identity.py`. Use `--device auto`; no guessed
path, second-port probing or fallback. Serial-init failures close the port,
transport errors redact identifiers and safe launch checkpoints aid diagnosis.
The boot021 payloads, manifest, pin and CPU/DT restrictions remain unchanged.
31 launcher, 16 stdlib identity/CLI and 7 intake tests pass; local payload
verification PASS. No native Linux or new live USB test ran.

M1 may now pull and perform the offline checks in
`tools/m1n1-client/stage-b-instructions.md`, including all 20 USB cases with
its prepared upstream client environment. Record readiness and preserve the
completed Stage A result. Wait for the human's explicit Stage B approval and
readiness before any restart/launch. Stage B is one RAM Linux attempt, no SMP
start, disabled Linux NVMe/cpufreq, PID 1/one CPU/60-second screen liveness,
then Macintosh HD return. No Recovery/reinstallation/security change required.
B owns subsequent target-specific kernel/DT diagnosis and CPU/power REA work;
M1 owns physical-session coordination/results, C waits for tested Linux access.

### Current M1 handoff — 2026-10-13: Stage A P_NOP passed; Macintosh HD return confirmed

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

### Earlier M1 handoff — 2026-10-13: Stage A stopped before handshake; USB naming fixed offline

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

### Prior Stage A authorization — session ended before handshake, 2026-10-13

The user explicitly approved **one m1n1 boot, one USB handshake, then back to
Macintosh HD**, keeping Macintosh HD at Full Security. This supersedes earlier
Stage A approval holds; no repeat approval is needed for this exact scope.
Follow `tools/m1n1-client/stage-a-instructions.md`. Stage B/Linux, upstream
shells/launchers, register/memory requests, policy changes and reinstallations
are outside this session.

M5 checks: current root Macintosh HD/FileVault on, staged m1n1 hash/size match,
AC power, no project VM processes. Fresh original Full/lab Permissive policy
result was supplied by the user in the preceding turn. Artifacts are unchanged;
existing offline tests/receipt remain applicable, no redundant test run.

M1 pulls this handoff and confirms ready before the user shuts down the M5.
Use the held-power picker, **iLinux Boot Lab → Continue**, leaving Macintosh
HD as default. On M1 discover the actual primary port and run the existing
10-second-bounded P_NOP checker once. Record actual outcome; no retries. After
success or failure, power off M5, use the held-power picker for **Macintosh HD
→ Continue**, then verify return/protections and publish sanitized results.
All Stage A results are still **NOT RUN** until observed. The M5 agent has not
restarted this computer or opened any USB connection during preparation.

### M5 review after return — 2026-10-13

B reviewed and fast-forwarded M1 report `c6f2c6f`. Native m1n1 reached
`Running proxy...` by the screen evidence reviewed by M1; that is an actual
bootloader milestone on this unit. USB/P_NOP and Linux remain NOT RUN.

Read-only M5 checks now independently confirm original root **Macintosh HD**,
**26.6.2 / 25G83**, original System/Data FileVault enabled, SIP enabled and
original authenticated-root enabled. The csrutil installation menu changed
order between queries: choose by the name in the same live prompt, never by
a cached number. Staged m1n1 size/hash still match; the installed boot object
was not separately read. Default restoration remains the user's observation.

The user supplied the fresh post-return helper result: **original Full / exit
0; lab Permissive / exit 0; read_only true**. This completes the return-policy
check; B did not independently rerun the privileged query. The M5 local helper
now accepts `--expected-lab Permissive` so the intended lab policy is not
mistaken for a failure. No policy/startup/payload changes were made this review.

Next session is now authorized above: the existing Stage A checklist, one
bounded P_NOP on the actual primary M1 USB path, then return to Macintosh HD.
The installed entry is ready for that test; no Recovery/reinstallation
is needed for the planned boot. After Stage A, review and authorize Stage B's
one-core RAM Linux/PID-1/60-second heartbeat diagnostic. Native desktop,
peripheral functionality and performance parity remain unvalidated.

### Current M1 handoff — 2026-10-13: lab m1n1 installation and original macOS return complete

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

<details>
<summary>Historical preparation handoff (superseded by the execution results above)</summary>

### Current authorization: lab-only Recovery policy and m1n1 installation

The user explicitly authorized lab-only Recovery setup, Permissive Security,
disabling kernel CTRR and installing the verified m1n1 boot object, while
keeping **Macintosh HD at Full Security**. This supersedes prior security and
custom-boot holds for this exact lab scope. No repeat approval is needed.
B prepared/staged a tested read-only Recovery helper and the one-operation-
at-a-time instructions. M1 guides the human on the M5 through sections 5–6 of
`kernel/native-enablement/boot-entry-setup.md`, records actual results and helps
return to original macOS. M1 must not run the M5 commands on itself.
Stage A/P_NOP and Stage B/Linux testing are still not authorized by this setup.

**Observed progress:** B created the unique empty APFS lab volume, preserving
the original volumes' names/roles/FileVault states. Original policy reports
Full Security; SIP/authenticated-root enabled. Repeated installer verification
PASS. Normal GUI launch succeeded; after the user authorized its license, B
selected and visually verified **iLinux Boot Lab** as destination.

**M1 return handoff (user-observed):** the user completed installation/setup,
reached the lab desktop and reported `sw_vers` **26.6.2 / 25G83**, then confirmed
successful return to the usual **Macintosh HD** desktop. These observations
establish lab first boot and return; M1 has not remotely inspected the M5.
B reviewed/integrated M1 report `f34970e` and independently confirmed current
Macintosh HD build 26.6.2 / 25G83, FileVault/SIP/authenticated-root enabled,
and a separate mounted lab System/Data group with the same installed build.
The user subsequently ran the read-only policy helper and supplied its JSON:
**original Full / exit 0; lab Full / exit 0; read_only true**. B reviewed this
user-provided result; it is not an independently rerun query or an inference
from the pre-install baseline. This resolves the pending policy read.
B has now staged the exact m1n1 binary at
`/Volumes/iLinux Boot Lab - Data/Users/Shared/iLinuxBoot/m1n1.bin` after
rechecking the lab System/Data roles and separate volume group. The reread
copy matches the tracked manifest: 3,932,160 bytes, SHA-256
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
Only the new staging folder, m1n1 and now the read-only `recovery-preflight.sh`
were created on lab Data; no existing file was overwritten. Helper SHA-256:
`e65636d03cfb7a7000f86810fdc8888e209b99bedaa1b36ca7a125de4bf72188`.
Its 21 preflight cases, seven documented-operation guard cases and syntax checks
pass with stand-ins; no real policy writes were tested. Current root and payload
were rechecked; AC power, no project VM processes. System Settings already
shows **iLinux Boot Lab** selected. B opened the pane but did not change its
selection or click Restart. No security/custom-boot change has run yet.
Boot021 and the existing client pin are unchanged.
Live USB/P_NOP, live target-version check, native m1n1/Linux/Omarchy remain
**NOT RUN**. Current handoff: `kernel/native-enablement/boot-entry-setup.md`.

**Next human/M1 session:** pull this handoff before restarting. Boot lab macOS,
shut down and enter its paired Recovery with one continuous power hold. Run
the helper and gated policy/install commands; verify original Full/lab
Permissive and actual kmutil exit. Stop on failures without bypass/retry loops.
Return via the picker to Macintosh HD and restore it as default. Publish only
sanitized observed outcomes. Stage A later tests only m1n1/P_NOP; Stage B separately
tests one-core Linux PID 1 and 60-second liveness. The result template now
separates controller output, screen observations, timing and macOS return.
No persistent USB Linux console or SSH is present. Blank screen means output
not observed; establish logging before another blind attempt.

**M1 offline preparation complete:** `tools/m1n1-client/stage-a-instructions.md`
contains the later authorized handshake checklist. Stage B evidence draft is
local/ignored at `build/native-intake/results/boot021-stage-b-prepared.md`,
pre-filled from the current template and verified package with provenance,
expected milestones and timing bounds. All 13 payload checksums still match;
boot021 and the clean client pin are unchanged. M1 read B's policy-result
handoff at `1607f2a`, without an independent target query. B integrated M1's
`1420572` report. Lab Recovery installation is now authorized as stated above;
live Stage A/B approvals remain pending. All live USB/target-version/native
tests are **NOT RUN**.

</details>

### Current boot-package assignment (user authorized 2026-10-13)

B now owns preparing/exporting the boot package, correcting the single-core
launcher and first-boot instructions, testing them in isolation and pushing
the M1 handoff. Work is in `native/boot/` and job 021; A's QEMU/latency work
is untouched. The M1 agent downloads/verifies and reports offline readiness.
**Earlier package-only boundary, superseded by the current lab authorization
above.** Partition changes and live native tests remain on hold.
Payload publication is authorized; these are open-source
build outputs, not Apple artifacts. Follow the corrected first-boot plan;
older statements about an empty APFS stub or persistent proxy console are
superseded. No native hardware success is claimed by this handoff.

B's next preparation milestone is complete: the user requested exact dedicated
entry steps while M1 verifies. `kernel/native-enablement/boot-entry-setup.md`
selects a second full macOS installation named `iLinux Boot Lab`, matching the
available 26.6.2 / 25G83 installer. It documents paired-Recovery checks,
lab-only policy/boot-object commands and macOS return. At that preparation
milestone no volume creation, policy change or reboot had run. The current
handoff above records subsequent installation and authorization; an offline
receipt alone does not authorize host changes.

**Download and verification result:** the matching 26.6.2 / 25G83 installer is
downloaded. User subsequently authorized resolving verification without
disabling security checks. Its original package passes Apple's signature and
Gatekeeper install assessment; all five signed entries and the installed
695 files/226 directories/26 symlinks match. Three executable signature checks
and eleven synthetic verifier regressions pass. The outer app's custom-omit-
rule rejection remains unchanged; no security exception or bypass was used.
See `native/boot/macos-installer-download.md` and D-046.
M1 has now published its observed offline results below and in `progress.md`.
USB/P_NOP, live target-version check, native m1n1, native Linux and native
Omarchy remain **NOT RUN**. The current authorization above supersedes the
earlier installer-launch and lab boot-security holds; native-test holds remain.

### M1 offline receipt: ready for coordination, physical testing on hold

Verified handoff commit: `58dc2baffceda76d546b0e6fb8f101089dfd35b8`.
Private prerelease `native-j716c-boot021` was downloaded and its archive
SHA-256 matched Git before extraction:
`b534680fc25dff78d8eaecfb96ed5b9733a3f408ae20cb4947722cb8163edc15`.
Offline launcher and intake verification passed for all 13 files; SHA256SUMS
matched tracked digest
`9d2b9ec1ae9dad601fb25a6536e838b57ab436160ab6ceddf208b764de41f581`.
Tests passed: **17 launcher, 7 intake, 2 fake-serial USB**. LLVM 23.1.3 passed
ARM64 assembly/link/objcopy/nm/disassembly. The clean client remains pinned
to `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.

M1's complete JSON receipt is local and ignored:
`build/native-intake/receipts/boot021.json` (2026-10-13 20:02:34 UTC).
It records `boot_authorized: false` and `target_version_observed_live: false`.
There are no offline verification blockers. USB discovery opened no port and
found no modem paths; it does not establish cable status. First live test is
still the separately authorized bounded handshake. Boot-entry provisioning
and explicit physical-test approval remain pending. B reviewed and integrated
this report (`dfdf8cf`) while completing installer content verification. The
subsequent normal GUI launch succeeded; installation is pending as recorded above.

### Second-machine checkout (2026-10-13)

The user designated a separate macOS computer as the second-machine agent.
Its checkout is `~/Documents/ilinux`, tracking the private
`https://github.com/nickyrice04/ilinux.git` repository. GitHub authentication
as `nickyrice04`, fetch access and account push permission are verified.
This role is distinct from research agent B and post-boot configuration
agent C. It supports the m1n1 USB proxy and cross-machine handoffs; USB
connectivity and native boot have not been tested by this setup.

The user explicitly authorized repository pushes for agent communication,
superseding the older local-only Git rule. Fetch and use `git pull --ff-only`
before work, commit explicit paths, then push without force. If another
machine advances the branch, fetch and reconcile before retrying; never
reset away another agent's work. Local advisory locks do not coordinate
separate computers: record ownership and handoffs here before shared work.
Credentials remain in the OS credential store, never in tracked files.
Ignored VM disks, build payloads and local third-party checkouts are not
downloaded by Git. Proxy-client dependencies now pass offline imports; see
`tools/m1n1-client/README.md`. LLVM 23.1.3 now passes offline ARM64 assembly,
link and disassembly. A bounded P_NOP-only USB check is prepared and fake-
transport tested. Physical connectivity and target boot-entry readiness
remain unverified; no target session has run.

**User direction (2026-10-13, package handoff):** the second-machine agent has
received B's corrected single-core package/launcher and completed offline
verification only. Keep the client pinned to the agreed target revision.
Do not run upstream `proxyclient/tools/linux.py`. First live test is the
separately authorized bounded USB handshake; thereafter record only approved
diagnostic boots. Intake requirements and the result template are in
`tools/m1n1-client/README.md`; current package instructions are in `native/boot/README.md`.

| Agent | Who | Owns |
|---|---|---|
| **A** | The session that wrote this plan (`AGENT_ID=agent-a`) | VM responsiveness: goals 2–3. QEMU source and patches (`virtualization/qemu/src/qemu`, `patches/qemu/`), the VM kernel config (`omarchy-arm64/kernel/linux-ilinux-vm/`), latency benchmarks |
| **B** | The second build agent (`AGENT_ID=agent-b`) | Goals 4–7: video default, native readiness (`kernel/`, new `virtualization/jobs/`), backup preparation, the configuration handoff kit |
| **C** | A configuration agent, later | Omarchy configuration on a natively booted install (goal 9). Starts only after gate N4 |

The user makes every gated decision (N1–N4 below). No agent changes boot
security, partitions, firmware or the macOS installation.

### Agent B scope update from the user (2026-10-13)

The user has directed B to focus on REA/backend setup and targeted macOS
binary research, with an evidence and implementation handoff for A. B will
leave A's wakeup, QEMU and display work untouched and defer live-guest video
changes while A owns that VM. B's current files are under
`reverse-engineering/rea-lab/` and
`reverse-engineering/findings/rea-native-2026-10-13/`. Analysis tools will run
in a separate diskless Linux job, never against the live Omarchy disk.
Build/analysis jobs must acquire `quiet` so A's measurements do not overlap.
The agent C configuration handoff remains required before native desktop use.

B milestone: REA/Ghidra works; original extraction/evidence tools and a
read-only startup-layout experiment pass ARM64 Linux tests. See
`reverse-engineering/findings/rea-native-2026-10-13/handoff.md` (F-070–F-072).
The analysis VM is stopped and B's locks are released. A's live VM, QEMU,
vmpoll and frame-rate work remain A-owned. The candidate native masks are
not validated MMIO semantics and must not be installed as a hardware fix.

B's next user-authorized pass covers GPU/display, network/Bluetooth, ANE's
ordinary host interface, camera, audio/microphone, HID input and shared
transports. Findings live in `reverse-engineering/findings/driver-interfaces-2026-10-13/`;
original protocol experiments live in `kernel/experiments/driver-contracts/`.
B retains the isolated lab and does not own A's live VM/video changes.
Protected services and personal sensor recordings remain excluded.

B completed F-073–F-075: 17 REA functions, independent byte/LLVM evidence,
a Linux-tested DockChannel HID patch and original offline N1 ACIPC queue
helpers. Full handoff: `reverse-engineering/findings/driver-interfaces-2026-10-13/handoff.md`.
The lab is stopped and B's `quiet` lock released. A's goal-5 native build
can apply `kernel/experiments/driver-contracts/dockchannel-hid/0001-dockchannel-hid-validate-input-bounds.patch`
to a disposable checkout and compile the full driver object. Do not install
it in the VM's virtio-input path or advertise native input as tested.

## Shared resources: rules

### Current assignment (user confirmed 2026-10-13)

A owns goals 5–7: the complete native kernel/schema build, first-boot
observation plan, backup preparation and C's configuration handoff. Goals
2–3 are checkpointed unless they block native development. B owns targeted
REA work on CPU startup, GPU/display and idle/DVFS, with original offline
experiments and findings for A. The older owner table and goal ordering
below are historical where they conflict with this assignment.

B's completed startup/idle pass is recorded in
`reverse-engineering/findings/cpu-startup-2026-10-13/`. Its optional startup
guard passed eight Linux cases with sanitizers and startup-object compilation;
the analysis VM is stopped and B's locks are released. B has not modified A's
kernel build jobs, native payloads or handoff kit. The dockchannel proxy is
not established as a Linux console; early-boot observability remains a
goal-5 prerequisite.

1. **Locks** (`tools/lock.sh`, advisory, stored in the gitignored
   `virtualization/run/locks`):
   * `vm`: hold it for any QEMU Omarchy VM console command, restart, or
     install into the guest. `tools/vm-restart.sh` refuses to restart while
     another agent holds it, so export `AGENT_ID`.
   * `quiet`: hold it for power and latency measurements. While someone holds
     it, nobody else builds, benchmarks or restarts a VM. Keep it short
     (usually 30 minutes or less); measurements are invalid without it.
   * `qemu-build`: QEMU and virglrenderer builds and `runtime/` installs.
   * `git-history`: history rewrites. Only with the user's OK, and only while
     no other agent is committing.

   Run `tools/lock.sh status` before heavy work. Release locks as soon as you
   are done. Never clear another agent's lock unless it is stale and the
   user agrees.
2. **Git:** one shared working tree and branch. Commit with explicit paths
   only: no `git add -A`, `git add .` or `git commit -a`. Never commit another
   agent's uncommitted files. Use the attribution line from your session
   instructions.
3. **Shared docs** (`progress.md`, `decisions.md`, the findings catalog,
   `blockers.md`, READMEs): re-read right before editing, make small
   targeted edits, and never rewrite a whole shared file from a stale copy.
   Each agent writes its own progress entry.
4. **ID ranges:** agent A uses F-054–F-069 and D-032–D-039. Agent B uses
   F-070–F-089 and D-040–D-049. Agent C uses F-090 and up, and D-050 and up.
5. **Native kernel builds** run in the separate job VM
   (`virtualization/jobs/`). They load the host heavily, so never run one
   during someone else's `quiet` window.
6. **The floating VM window** (`COCOA_FLOAT=1`, which keeps the VM window on
   screen) is for on-screen measurements only. Tell the user before a session
   that uses it.

## Goals, in order

| # | Goal | Owner | Done when |
|---|---|---|---|
| 1 | Commit the verified Mesa video work | A | Done: `47efd62` |
| 2 | **Cross-core wakeup latency.** Message passing between two processes takes 1.6 µs on one vCPU (macOS: 3.8 µs) but about 21 µs across vCPUs. QEMU uses Apple's hardware GIC (`kernel-irqchip=on`), so the leading suspect is an idle vCPU being parked and then woken through the macOS scheduler. Bounded spinning before parking (in QEMU's HVF idle path, and/or the guest's `cpuidle-haltpoll`, which our kernel does not build) is the candidate fix. Note: arm64 7.1.6 ignores `idle=poll` | A | Cross-vCPU pingpong and syscall improve measurably; idle power is unchanged within noise; the poll window is bounded and documented; new QEMU patch or kernel config committed |
| 3 | **F-050 frame-rate collapse:** 7–19 fps on alternating fresh boots. Re-test after goal 2, then trace DRM flips, fences and Hyprland frame callbacks during an affected boot | A | Cause identified with evidence; fixed or documented with a workaround |
| 4 | **Video fix as the default** (`mesa-virgl-video-ilinux`, now opt-in via `ilinux-video`). Do an on-screen playback and power check first | B | Plain `mpv`/FFmpeg use the fixed driver; pixel-exact and zero-copy regressions pass |
| 5 | **Native track, safe steps:** full kernel build and `dtbs_check` for `kernel/patches/t6050` in the job VM; a written first-boot plan (see gates) | B | Kernel links; schema warnings triaged; plan committed |
| 6 | **Backup preparation:** a scrub list (local paths, the test VM password), licences (GPL-2.0 for QEMU patches, MIT for virglrenderer and Mesa patches, a choice for our own code), and a plan to remove the 640 MB of Core ML weights from history or start fresh from a clean snapshot | B prepares; user approves; `git-history` lock to execute | Private repo ready to push on the user's go-ahead |
| 7 | **Configuration handoff kit for agent C** (below) | B | `native/handoff/` committed and reviewed by A |
| 8 | Native gates N1–N4 (below) | User decides; then A and B | Per gate |
| 9 | **Omarchy configuration on the native install** | C | Acceptance checks in the handoff kit pass |

Agents may pull work forward when blocked, but keep goal 2 before goal 3 (3
re-tests 2). Keep goal 4's guest changes out of the VM while agent A holds
the `vm` lock.

## Native gates (all user decisions)

* **N1. Prerequisites.**
  * A current full macOS backup (Time Machine or equivalent).
  * A second computer and a USB-C data cable for the pre-Linux m1n1 proxy.
    Native Linux output is initially attempted on the M5 framebuffer;
    no persistent USB Linux console is established.
  * A separately reviewed and authorized OS boot environment with Apple boot
    assets, paired recovery and its own custom boot policy. An empty APFS
    volume is insufficient. Exact layout and installation remain gated; see
    `kernel/native-enablement/first-boot-plan.md`.
* **N2. RAM-only boots** over USB from the second computer: kernel,
  initramfs and device tree, with nothing written to the Mac's disk. In
  order:
  1. single-core console;
  2. secondary CPU start-up (SMP);
  3. NVMe read-only identification;
  4. keyboard and trackpad;
  5. boot framebuffer.
* **N3. Linux root partition.** Resizing the APFS container is a separate
  user decision, made after another backup.
* **N4. Omarchy installed natively.** Hand over to agent C with the kit.

## Configuration handoff kit (goal 7, for agent C)

Agent B writes it in `native/handoff/`. It must cover:

1. **VM-only files that must not be applied natively:**
   * `omarchy-arm64/configuration/vm-integration/*`: host bridge, vdagent,
     NAT DNS, `MESA_VK_WSI_DEBUG=nowlts`, the VM `mpv.conf`, autologin;
   * the VM kernel package.
2. **What carries over:**
   * `omarchy-qos` and the QoS tiers;
   * kernel options (16 KiB pages, uclamp);
   * the t6050 energy-model and OPP drafts (unvalidated);
   * the aarch64-apple package choices.
3. **A hardware matrix for the boot under test:** what works, what is
   absent, and the fallback for each absent device:
   * llvmpipe instead of GPU acceleration;
   * USB Ethernet or tethering for networking, since N1 Wi-Fi has no driver;
   * an external libfprint reader or FIDO2 key instead of Touch ID;
   * no Neural Engine.
4. **Access:** how agent C reaches the system. It needs network for itself:
   USB Ethernet, or running from the second computer over the serial or
   SSH link.
5. **Acceptance checks:**
   * all 18 CPUs and their capacities;
   * storage health;
   * display and input;
   * audio;
   * idle power with the WFI workaround in place;
   * suspend (expected not to work yet);
   * Omarchy's own test suite where applicable.
6. **Guardrails:**
   * never touch macOS volumes or the APFS container;
   * no firmware, SEP or boot-policy changes;
   * no credential handling;
   * record every change as a package or config file in this repository.
