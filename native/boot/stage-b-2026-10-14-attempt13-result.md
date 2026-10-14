# Stage B attempt 13 — boot032 dynamic heartbeat, no attributed GPIO probe

2026-10-14. **One RAM attempt consumed. Controller PASS.** Native Linux reaches
late initialization and displays a changing diagnostic panel. Last photo:
**P05 / W00 H06 / D0000 I000 / B00 C0000**, with S not reliably readable.
No device-specific GPIO result or diagnostic userspace was observed.
**Macintosh HD return PENDING HUMAN CONFIRMATION** at publication preparation.
Fresh attempt-13 policy/default checks **NOT CHECKED**. No retry or settings change.

## Reviewed inputs and offline verification

* M5 handoff: `f2b2c4d327fa4d2cdc22b07eb47173b950023868`.
* Published readiness / execution: `8f2c908d7946491f3cf0137a249531cf7349c7a9`.
* Release `native-j716c-boot032`: **16,723,345 bytes**, archive SHA-256
  `001ef39cd64d8fef7c3779c5169c00726474d6ebc56cea90b9f6f5d9c9bd0500`, verified against Git before safe extraction.
* Image **44,534,272 bytes**, SHA-256 `589c33577d1bc2ddeb2f96e544f87b9ead6bc52e774410567170a7235dd70bcb`.
* Stage-B DT **61,567 bytes**, SHA-256 `4b3adee52465b809e9c8a1946b7610c63f1ae3c0b24f7334cd485260da84adce`.
* SHA256SUMS digest `0f0a1a65d793d4d0a5f0238efbc9f371532a8c7c1927ceff417d1b78418c060e`; **13 intake files PASS**.
* Offline launcher and **102 tests PASS**, all exit 0: 37 launcher + 10 GPIO
  guard + 6 entry + 16 DAPF + 5 framebuffer + 19 hardware + 2 pinned ADT/DAPF
  + 6 root ADT/GPIO integration + 1 real proxy serializer. Synthetic transport.
* Independently compared retained boot031: only Image, Stage-B DT and package
  manifest metadata differ. Semantic DT delta is exactly the main GPIO
  `gpio-reserved-ranges` property; same node paths and 286 public IDs.
* Client clean/pinned at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
  Installed boot021 unchanged. Source/controller hashes and receipt rechecked
  unchanged after execution, before report edits.
* Ignored receipt `build/native-intake/receipts/boot032-attempt13.json`, SHA-256
  `4b37026dfc995930bdc0ff654dd79d64eb168eb8dd54b4d80f0b6357fcf3ff74`. Fresh sanitized JSON/Markdown results retained
  under `build/native-intake/results/boot032-stage-b-attempt13.*`.
* Human requested current instructions, reported proxy running and recording.
  Readiness published and explicitly announced before the single launch.
  Requested all eight panel lanes and recording through the stop criterion.
* Post-attempt-12 protection prerequisite already PASS per M5: user Full /
  Permissive JSON exits 0; independent original root/build/FileVault/SIP and
  staged-m1n1 hash checks. Default/installed object/authenticated-root were not
  independently re-queried. This is separate from post-attempt-13 checks.

## Single controller execution

Reviewed launcher `main(argv)` called once through the sanitized local wrapper.
Zero-attempt/readiness/source guards, fixed checkpoint allowlist and safe error
frame handling remain. GPIO guard added to safe frame metadata and its fixed
PASS checkpoint recorded. Raw target output discarded; no raw dump saved.

```sh
tools/m1n1-client/run.sh native/boot/launch.py \
  --package build/native-boot032-download/ilinux-j716c-boot032 \
  --launch --device auto --confirm BOOT-J716C-RAM-DIAGNOSTIC
```

| Item | Result |
|---|---|
| Invocation count | 1 |
| Start UTC | 2026-10-14T17:56:51.492019+00:00 |
| Handoff UTC | 2026-10-14T17:57:01.852238+00:00 |
| End UTC | 2026-10-14T17:57:02.081153+00:00 |
| Elapsed / exit | **10.589 seconds / 0** |
| Target/marker/secondary guard | PASS: t6050, installed boot021 marker, no started secondaries |
| GPIO ADT before upload | PASS: 221 pins / 7 groups, exclusions 5,6,7,112,141 |
| Board/framebuffer prerequisite | PASS |
| Final hardware DT | PASS: J716c/t6050 CPU topology, AIC3 and timer routes |
| Final GPIO DT | PASS: exact geometry and reserved-ranges property |
| First DAPF layout | PASS: reviewed AOP DART/GAPF-only case |
| Final DAPF RAM correction/readback | PASS: bounded 96-byte table |
| Framebuffer descriptor/readback | PASS: bounded 16-byte kernel RAM descriptor |
| kboot reply / USB close | PASS |
| Screen deadline | 17:59:01.852238 UTC; communicated **1:59:02 p.m. Eastern** |

Controller 180-second and transport 15-second bounds retained. The two-minute
screen deadline was communicated after handoff. Stop/return guidance was given
after the deadline when media arrived. Actual shutdown time was not independently
measured. No retry, separate handshake, reconnect, shell or additional live call.

## Media review and literal observations

Reviewed **IMG_2665.mov**, **40.13 seconds**, oriented **720×1280**, at
**0, 5, 6, 7, 8, 9, 10, 15, 20, 30, 39.98 seconds**, with enlarged lower-screen
crops. Reviewed detailed **IMG_2666.jpeg**, original oriented **4284×5712**,
with lower-screen/panel crops. Video begins at proxy, shows DT preparation,
then Linux/Tux and late initcalls. Review is sampled, not exhaustive.

| Video seconds | P | S | W | H | D | I | B | C |
|---:|---|---|---|---|---|---|---|---|
| 8 | 00 | 00 | 00 | 00 | 0000 | 000 | 00 | 0000 |
| 10 | 0D | NOT CONFIRMED | 00 | 00 | 0000 | 000 | 00 | 0000 |
| 15 | 05 | NOT CONFIRMED | 00 | 01 | 0000 | 000 | 00 | 0000 |
| 20 | 05 | NOT CONFIRMED | 00 | 02 | 0000 | 000 | 00 | 0000 |
| 30 | 05 | 06 | 00 | 04 | 0000 | 000 | 00 | 0000 |
| 39.98 | 05 | NOT CONFIRMED | 00 | 05 | 0000 | 000 | 00 | 0000 |
| Detailed photo | 05 | NOT CONFIRMED | 00 | 06 | 0000 | 000 | 00 | 0000 |

S changes visually but several frames contain mixed/repainting/overlapped digits.
Only clearly readable samples are transcribed. The table is not an atomic
snapshot or a complete list of intermediate states; H03 was not directly sampled.
No stable final S step is assigned. H05 in the last video frame and H06 in the
photo establish continuing kernel watchdog updates, not userspace liveness.

The photo/video directly expose **j716c-t6050 mode=EL2 cpus=1**, **ticks=25**,
**irq_masked=0 fiq_masked=0**, and the reschedule suffix **pending=1 strip=1
display=6**. Prefixes are partly covered. The timer `counter=PASS` and
`phys`/`virt` fields are covered and **NOT READABLE**; do not fill them from
prior boots. All eight panel lanes visibly render. `console_setup` is unobserved.

`clk_debug_init blacklisted` is visible. `deferred_probe_initcall+0x0/0x4e0`
is the last identifiable initializer, followed by target/timer/reschedule text.
Printed phase digits are obscured; panel **P0D → P05** is directly observed,
but a full printed phase sequence is not. The console text remains at the
reschedule line while H and S change. No readable watchdog text, scheduler
summary or symbolic stack appears in the supplied media. No exact kernel
build string, first kernel line or rectangle count was recovered.

**GPIO cache counts, IRQ handoff counts, retry-compatible messages, probe return,
reserved-pending IRQ, locked-pin and mask-readback error: NOT OBSERVED.**
Do not carry the first-controller success from attempt 12 into this result.
**PID 1 / userspace online_cpus=1 / 60-second userspace liveness: NOT OBSERVED.**
No explicit kernel panic seen in reviewed samples.

## Offline decode and bounded interpretation

The checked-in decoder for **D0000 / C0000 / B00 / I000** returns unknown
root/current device and no marked operation. Its numeric I conversion is 0,
which does **not** establish a pin-0 read: no device or B91 operation is attributed.
The renderer initializes saved lanes to zero; `ilinux_probe_path_start` sets
I=FFF when an attributed retry begins. That source context makes the zeros
consistent with no attributed retry, not proof of a pin fault.

Per reviewed checklist/source, **P05** marks the first work-flush boundary.
**W00** does not show the previous W04 bus-probe boundary. No GPIO B90/B91/B73
boundary or nonzero D/C was observed in these samples. The changed observation
therefore does not test the reserved-pin hypothesis to completion. It neither
proves the GPIO repair worked nor localizes a new fault to GPIO pin 0.
M5 should inspect worker/scheduler and console progress offline using this
state; no exact blocking PC, lock, cause or task is established.

The watchdog source is bounded to six heartbeats. H06 in the photo is not, by
itself, proof of a subsequent timer failure or a 60-second userspace milestone.
Markers may be repainted or overwritten and have diagnostic overhead. No
native performance, all-peripheral or Omarchy success claim.

## Coverage, return and next handoff

The supplied clip is **40.13 seconds**, not the full 120-second observation
window; no 60/90-second video samples exist. Photo adds detail/H06 but no known
elapsed coverage. Hidden labels and missing transitions remain unconfirmed.
Later changes and Macintosh HD return are **pending human confirmation**.
Return guidance: power off, hold power for startup options, Macintosh HD →
Continue. Fresh policy/default checks are **NOT CHECKED** for this attempt.

Attempt 13 is consumed. M5 next: read-only return review after confirmation
and offline analysis of the un-attributed worker/console state. Preserve the
installed boot021 entry, client pin, gates and fixed arguments. No automatic
retry, extra blacklist, reinstall, volume/security/default change. A new attempt
requires updated instructions and human start. Native diagnostic userspace
still gates Linux control/input, RAM root and Omarchy configuration.

Full media stays in its original local location; no media/raw ADT/serial paths,
unique identifiers or proprietary binaries committed. Temporary review PNGs
are deleted after review. Earlier results/packages remain intact.

## Reviewed hashes

Full source/procedure/payload hashes are retained in the ignored JSON. The
following changed/controller/decoder inputs identify this invocation:

| Path | SHA-256 |
|---|---|
| `native/boot/launch.py` | `65ece2537fdb9ece0ed54dc234f8ee253bc2f3c44aac8c012014079b6366cfe0` |
| `native/boot/gpio_guard.py` | `a3c038d036e2bc97679bd29d78d16e42b3db06d96775918abaeb01a53434a755` |
| `native/boot/entry_guard.py` | `d1fa8ca84aa1c7032c50c8766c8571054047720df35cb7d518310167ec183713` |
| `native/boot/dapf_guard.py` | `bb33d9bebcec3a6cd925ed9e7b28dbabe3c7375c445d7e9d68ace18f4eaa7047` |
| `native/boot/fdt.py` | `ee577a08bb48242e84dbc50cd1f40a8d1f47a4d4481ca6dd6503829f53615ad3` |
| `tools/m1n1-client/usb_identity.py` | `72cc8c2a916b8964b2e4b5afc4c1aac22fe8031a2c2f8658df6882b063a47137` |
| `tools/m1n1-client/stage-b-instructions.md` | `ca8cbf26c8af8da6972c694b0e8e2b32c625cc868e9a7b76cca66256537b0674` |
| `native/boot/package-manifest.json` | `c429d219397fa76182b82e45732ef994f69f8ecfad42cca118d5d9273defdbf7` |
| `kernel/experiments/probe-path/decode.py` | `6a6a8cfc7c4fce7312bd9c6bb3027b1c457d9f30626dffc92225b1d81e0cc633` |
| `kernel/experiments/probe-path/device-identities.json` | `4bb4f3d0a1cf7fcd79a99729af1c342c63bc16e2e397cca2f15aa566be490e2e` |
| `kernel/experiments/probe-path/phases.json` | `f6aef0c5b2258ff32049fac78df9f82ed0a6ec599a3400a63730b71ce2c9f2c1` |
| `kernel/experiments/gpio-reserved/apply.py` | `44632a128a0ce005729793abc09d2003b2f047864e2e713aebc196e580ca24c2` |
| `kernel/experiments/gpio-reserved/validation.json` | `228a7cbc7dcce31397ea1d3ee388a08b396bb29a5b4c6db0aafaeea92dc210c0` |

Sanitized local wrapper SHA-256: `195c6f4fb4f3f7bf3586710cd1890d3abdb377fd88a355c87fbcb7aee3410a2b`.
