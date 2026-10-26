# Frozen 31AF whole-image readability qualification

This original wrapper adds synthetic page-table omissions around the **unchanged
released 31AF payload**. It creates no native payload, firmware or installation
package. It never accesses the Mac's hardware, boot policy or installed objects.
It is a dependency experiment, not a diagnosis of the human-reported logo result.

The frozen observer verifies every page of its complete image before parsing
BootArgs. In particular, no longer writing `__DATA_SPTM` does not remove its
requirement that the whole reservation be readable. The earlier synthetic model
mapped that whole region read-only; it did not test missing mappings.

There are twelve new cases: each of ordinary EL2/4-KiB and VHE EL2/16-KiB has a
valid paint control and five omission controls. Each omission removes exactly
16 KiB of identity mapping at image offsets:

| Offset | Purpose |
|---|---|
| `0x4000` | First reserved monitor page |
| `0x2c000` | Middle reserved monitor page |
| `0x54000` | Last reserved monitor page |
| `0` | Unused header canvas |
| `0x58000` | Unused ordinary text page |

No omission touches the boot entry, vectors or reachable helpers. Existing
source records, supplied aperture mapping and framebuffer bytes are unchanged.
Every present image page remains read-only. The expected outcome for each
omission is refusal phase `0x80`, status `7` (`IF31_IMAGE_READ`), before any pixel
store. The two controls should paint the existing exact 8192-pixel pattern.

The wrapper verifies five frozen source/layout hashes **before importing** the
old harness or QMP transport. It then replaces only the synthetic table generator
and refusal-status map in process memory. All original runtime checks remain:
park PC, SP zero, full exact pixel footprint, unchanged complete modeled physical
payload/reserved A5 bytes, input records, page tables and fixture scratch. The
reused harness's generic reserved-read-only mapping label is replaced in emitted
results with exact mapped/unmapped range metadata. Physical storage behind an
unmapped virtual page still exists for the emulator's independent readback.

Only the exact 393216-byte payload SHA-256
`91d2ce73f79784b78c96e08c606d3622aa3246a7561fdbec4d1066ebe9bfaa7c`
and frozen layout are accepted. All source bindings are rechecked after a run.

Host-safe fixture checks run Python only, with no compiler or emulator:

```sh
python3 -I kernel/experiments/entry31af-qualification/run.py --self-test
```

Compile/emulation is restricted to Linux and intended only for the existing
isolated, networkless build VM. Use short output paths for the reused QMP socket:

```sh
python3 -I kernel/experiments/entry31af-qualification/run.py --payload /job/payload.bin --layout native/boot/attempt31af/layout.json --output /job/out/qualification --qemu /usr/bin/qemu-system-aarch64
```

Without `--qemu`, the guest compiles fixtures and reports PREPARED_NOT_EXECUTED.
The self-test establishes table construction only. Actual emulator PASS requires
the full isolated execution command and separately retained results. Neither
outcome measures native entry EL, reservation mappings, panel scanout, monitor
readiness, physical secondary CPUs or performance. No native boot is authorized
or recommended by this wrapper.
