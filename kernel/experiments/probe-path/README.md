# Boot030 / attempt 11 — identify the deferred device and probe operation

2026-10-14. **Native attempt 11 NOT RUN; the native hang remains unresolved.**
Only Image changes from boot029. This improves the native diagnostic path; it
is not a claim that Omarchy or macOS-equivalent performance is ready.

## Evidence and decision

[M1 attempt 10](../../../native/boot/stage-b-2026-10-14-attempt10-result.md),
reviewed at `9d04195`, directly observes **P:05 S:09 W:04** in paused frames
from 11 through 27.05 seconds of a 27.197-second video. Three strip lanes now
render on this machine. H, small timer/display fields, full transitions,
watchdog stack and diagnostic PID 1/liveness were not observed or not confirmed.
The clip does not cover the full 120-second observation window.

The exact source places P=05 at the first deferred-work flush, S=09 at scheduler
exit and W=04 before `bus_probe_device`. Passage beyond the earlier phase-12
boundary is a source-path inference, not a direct reading of phase-13 text.
The evidence does not identify a driver, blocking PC, deadlock or timer fault.

REA 6.4.0/Ghidra 12.1.4 analyzed exact boot029 `bus_probe_device` and
`platform_probe` objects in the isolated lab. [audit.py](audit.py) checks both
complete bodies against ELF/LLVM and linked Image: **81 instruction words**,
**69 nonrelocated matches**, plus 12 relocation words reviewed in linked GNU
disassembly. [evidence.json](evidence.json) pins identities and limits.

The bus wrapper first attaches the device, then takes a bus-interface mutex
and invokes interface callbacks. The platform wrapper applies clock defaults
and attaches power domains before calling the driver. W=04 alone distinguishes
none of these. Original diagnostics now mark this path rather than guessing a
new driver skip. Public source and our exact Linux objects answer this question;
no Apple extraction or proprietary implementation is needed.

## Implementation

[apply.py](apply.py) checks five exact boot029 source digests and every edit
anchor before writing an isolated copy. Existing bootloader, DT, config,
initramfs, kernel arguments and controller/hardware gates stay unchanged.
The sole `clk_debug_init` blacklist remains; no extra skip, core, device,
clock, power-domain or security-policy change is introduced.

* **56 probe boundaries** cover bus attach and interface callbacks, device
  locking, driver matching, supplier/parent runtime PM, DMA/pinctrl/sysfs setup,
  PM-domain activation, clock defaults, platform power-domain attach, driver
  callback and cleanup. [phases.json](phases.json) defines each literal hex B.
  A marker is the boundary before an operation, not a program counter.
* **D** identifies the root deferred retry. **C** identifies the device supplied
  to the most recently marked operation, including nested synchronous probes.
  Both are four hex digits indexing [device-identities.json](device-identities.json),
  generated solely from the pinned, sanitized Stage-B DT. They are assigned
  table indexes, never chip IDs, serial numbers, pointers or raw hardware data.
  0000 means unknown/non-OF/dynamic/unmatched; do not guess a device from it.
* At diagnostic start, the target-specific helper binds 286 public paths to
  referenced OF nodes. Reference cleanup occurs at normal diagnostic completion.
  Hot-path lookup compares pointers in this fixed table and renders bounded
  cells. Markers are gated to the active deferred-retry task; unrelated async
  tasks cannot overwrite its B/C. Async work it waits on is not traced internally.
  Original device references, locks, callbacks, return codes and work flushes
  are preserved.
* A **four-row panel** places all lanes within 11 glyph columns at 4× scale:

  ```text
  P:xx S:xx
  W:xx H:xx
  D:xxxx
  B:xx C:xxxx
  ```

  It remains at the bottom left of validated scanout RAM. Every update repaints
  saved lanes so overwritten H/identity cells can recover; own-console rows
  reserve the panel. A different console can still overwrite it. Heartbeat H
  is also updated **before** its printk, preserving a clue if logging blocks.
  Mapping success alone is not visibility. This renderer is larger and slower;
  it is temporary diagnostic instrumentation, not a performance optimization.

Hooks add no allocation, lock, sleeping call, printk or new MMIO/register probe
inside the marked operations. ID setup uses normal OF reference APIs before the
active interval. Inactive operation is a gated return. A camera can miss rapid
transitions; lanes are not an atomic snapshot, and an interrupted render can be
stale. Correlate B/C/D with P/W/S/H and the reviewed video.

## Reading the next attempt

P, S, W and H preserve previous meanings. P order is
`01 → 0A → 0B → 0C → 0D → 02 ... 09`, not increasing numerical order.
P=05/07 are the two flush entries. W=04 precedes bus probing; W=05 follows it.
B=00 is no marked probe operation yet. D remains the root retry while C can
change during nested work. D/C values 0001–011E have entries in the decoder;
missing or unreadable values must stay NOT OBSERVED, never inferred zeros.

[decode.py](decode.py) accepts `--device`, `--current`, and `--phase` with the
literal hex values from D, C and B. It is a standard-library, offline lookup.
Inspect [phases.json](phases.json) directly if any lane is unavailable.

Useful distinctions: B=10 device lock; B=31–33 runtime PM/barrier;
B=42 pinctrl; B=43 DMA; B=61 clock defaults; B=62 power-domain attachment;
B=63 actual platform driver callback. These narrow follow-up work without
proving the named operation is faulty. Some branches are conditional/no-ops.
A B=63 result plus a known D/C can justify targeted analysis of that driver;
B=62 instead directs analysis to the domain provider and dependency chain.
Do not bypass either live.

## Validation and limitations

[Job 030](../../../virtualization/jobs/030-probe-path/README.md) uses retained
Linux 7.1.9, 16 KiB config, GCC 16.1.1 20260430, binutils 2.46.0, `make -j2`.
Full Image/ELF roundtrip and config identity pass. ASan/UBSan cover:

* Actual compact panel, seven lanes, exact rendered glyph pixels across three
  font geometries, padding/canaries, overwrite recovery and rejected bounds.
* Actual node-reference helper: 286 references, target gate, unknown IDs,
  current-task gating, nested device attribution and balanced cleanup.
* Actual platform-probe function: eight success/error/no-callback/deferral cases
  preserve callback ordering and return behavior.
* Actual DT parser/mapper: 15 lifecycle/format/geometry/failure scenarios.
* Inherited actual deferred-probe helper: pre-armed watchdog, finite six reports,
  one stack, scheduler state and error paths.

The initial compile stopped on a renderer signedness warning with `-Werror`;
changing the unsigned bound corrected it. The final guarded resume reused the
verified experimental source copy and passed all tests/full link. Earlier
boot029 source/package remains untouched. The fresh-copy job contains the final
code and the same test/build steps. An initial source-export job also stopped
on a moved unused path; its corrected export passed before analysis.

[validation.json](validation.json) records final package, controller/intake,
exact-image VM checks and output hashes. VM liveness cannot validate native
AIC, driver MMIO, panel scanout, energy use or desktop compatibility.

Post-attempt-10 user policy JSON PASS: original Full/lab Permissive, both exit 0.
Independent read-only root Macintosh HD/build 25G83/FileVault/SIP/staged m1n1
hash pass. Default selection/installed object/authenticated-root not re-queried.
No host boot, volume, firmware, default or security changes.

M1 follows the [current checklist](../../../tools/m1n1-client/stage-b-instructions.md),
publishes readiness, then one human-started filmed attempt 11. Capture all four
rows and review early and final frames through the bounded stop/return. Stable
native diagnostic userspace is the next gate; then Linux USB/input/control and
a usable root allow the Linux-side agent to configure Omarchy. GPU, SMP and
idle/DVFS remain separate native engineering tasks.
