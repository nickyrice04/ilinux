# Boot032: respect firmware-excluded GPIO pins

2026-10-14. Candidate repair for **attempt 12's B73/C0059 cache boundary**.
Native boot032 and attempt 13 are **NOT RUN**. Continue the installed boot021
entry; no reinstall, security, volume or startup-default changes.

## Evidence and engineering decision

1. **Observed:** M1 report `f3218fd` ends at P05/S09/W04/H02/D0059/B73/C0059.
   Main GPIO `/soc/pinctrl@29c000000` is entering `devm_regmap_init_mmio`.
   NUB GPIO completed the boot031 IRQ handoff, 61 pins/7 parents/1 mask, and
   returned 0. The recording covers 40.163333 seconds, not the full 120-second
   window. No main-controller return or PID 1 was observed. This is a boundary,
   not an exact faulting PC or proof that a particular pin stalls.
2. **Observed on this Mac:** a bounded, read-only IODeviceTree query of `gpio0`
   gives compatible `gpio,t8101`, 221 pins, 7 interrupt groups and
   `no-restore-gpio-pins` u32 little-endian values **6,7,5,141,112**. Only these
   non-identifying facts are recorded; no raw ADT or host identifiers saved.
3. **REA-assisted, independently byte-checked:** AppleGPIOICController::start
   references that property and `/arm-io/gpio0`, validates a u32 list, and sets
   a per-pin byte flag at the array referenced by object offset 0x108. In-body
   instructions in AppleT8101GPIOIC::initPinsAndGroups test that flag and skip
   the corresponding pin-register read. Original-carrier/derived-member bytes
   and Apple LLVM agree. `apple-evidence.json` records 4,112 bytes/1,028 words
   for start; the prior init audit covers 564 bytes/141 words. Start's provider
   removed-block warning leaves whole pseudocode at **manual_review_required**;
   init's out-of-body pcode remains **rejected_cross_boundary**. Neither whole
   pseudocode is accepted as source. Only the narrow in-body observations above
   inform the exclusion contract; unresolved virtual calls remain unresolved.
4. **Exact Linux source/object evidence:** boot031 sets raw defaults to all
   221 declared pins. `regcache_init` invokes the hardware-default scan when
   raw defaults are requested without explicit defaults. No exclusion is
   present. REA's initial `regcache_hw_init` query failed because the static
   function was inlined; querying the actual `regcache_init` symbol succeeded.
   `linux-evidence.json` checks all 336 object instruction words, all 299
   nonrelocated linked words against the boot031 Image and bounded pcode.
   Source inspection separately establishes flat-cache hole semantics and
   gpiolib's existing `gpio-reserved-ranges` support.
5. **Hypothesis:** accessing a firmware-excluded pin explains the B73 stall.
   The earliest excluded pin in the old ascending scan is 5; no native read
   address was captured. The reason Apple excludes these pads is **unknown**.
   We do not attempt to override access protections or change the pads.

## Original Linux implementation

`apply.py` requires the exact retained boot031 driver digest. On t6050 it
strictly validates the standard `gpio-reserved-ranges` property, including
nonempty/even cells, range bounds, overflow and overlaps, before MMIO. It
preserves existing GPIO numbering and builds explicit cache defaults from
permitted registers only. For the main controller this is **216 of 221** pins.
Raw defaults are zero, so regcache cannot perform a contiguous initialization
scan. `REGCACHE_FLAT_S` and access callbacks reject cache holes; ordinary flat
cache would otherwise return an uninitialized hole as zero. Non-t6050 cache
configuration is retained.

`source-delta.patch` is a review aid for changes to existing files. The apply
recipe and accompanying headers together reproduce the complete implementation.

GPIO input's uncached read, output/direction operations, pinmux, IRQ callbacks,
startup masking and pending-bit dispatch all respect availability. gpiolib
uses the same DT ranges to exclude these lines from requests. Existing IRQ mode
and locked-pad handling remains. Pending excluded sources detected during
startup return `-EBUSY` **before parent installation** rather than accessing
their pad registers or acknowledging their bits. This is a startup check,
not proof that a reserved source cannot assert later; native IRQ ownership
and complete peripheral operation remain unverified.

Only the Image and Stage-B DT change among payloads. The DT semantic difference
is exactly `gpio-reserved-ranges = <5 3>, <112 1>, <141 1>` on the main controller.
Packaging checks that exact delta against the pinned boot031 DT. The historic
full/non-Stage-B DT is retained for provenance and is **not the launch target**;
it does not yet carry this diagnostic-boot exclusion property. Config,
initramfs, m1n1, topology and other disabled-node choices remain unchanged.

The launcher checks live ADT geometry and the exact exclusion set before any
payload upload/DAPF correction, and checks the packaged and effective DT.
Firmware/board mismatches stop, rather than guessing an address or pin list.
The actual pinned m1n1 parser is covered by synthetic ADT integration tests.

## Diagnostic changes

The panel adds `I:xxx` beside D. I is a hexadecimal **pin index**, not an MMIO
address; `FFF` means no active indexed operation. B91 marks the permitted MMIO
cache read; B92 means explicit defaults completed; B90 validates exclusions;
B93 checks excluded pending sources. Earlier B codes and public D/C IDs remain.
Panel lanes are non-atomic last boundaries, not an exact exception record.
Capture literal values and errors before interpreting them. Rendering adds
overhead, so this build is unsuitable for performance comparisons.

## Reproduction and next gate

`virtualization/jobs/032-gpio-reserved/run.sh` is run only in the existing isolated ARM64 Linux build VM with
the repo read-only at `/mnt/ilinux` and a writable job share. It preserves
`/var/tmp/ilinux-boot031/linux` and makes `/var/tmp/ilinux-boot032/linux`.
`test_gpio.c` executes the installed helpers and extracted actual GPIO callbacks
against an MMIO model that asserts on forbidden reads/writes; it also tests
excluded pending IRQ rejection, dispatch/tail masking, geometry and error
propagation. `test_panel.c` tests the actual renderer with three font sizes,
guard pixels, exact glyph output and repainting. No proprietary code is copied
into Linux or published; raw REA results/binaries stay in the ignored local lab.

See `validation.json` for final results. Generic VM liveness cannot validate
native GPIO, power, GPU or performance. M1 follows
`tools/m1n1-client/stage-b-instructions.md`: offline readiness, one human-started
filmed attempt, then Macintosh HD. Once native PID 1 and 60-second liveness
work, the next development gate is a Linux control/input channel and usable
RAM root for the configuration agent, before the Omarchy desktop.
