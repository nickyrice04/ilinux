# 31AI transport: autonomous baseline inline payload, offline only

This directory prepares and checks workspace data. It contains no serial/USB
backend, firmware call, installer, boot-policy operation or native launcher.
Nothing here makes a restart ready. Keep the frozen 31AH artifacts unchanged.

## Selected route and alternatives

Use the reviewed **baseline** Aura runtime, with an appended diagnostic RAM
payload. The exact public source has this path already; a successful payload
returns from `payload_run()` before fallback proxy handling. The optional 31AH
USB2 delta acts only at fallback proxy entry and therefore adds no demonstrated
benefit to this autonomous route. It remains a separate, unqualified alternative.

The real proxy loader is
[`proxyclient/tools/linux.py`](https://github.com/aurora-silicon/aura/blob/bd9f3e8273dc79ae9095c19c2c4f32218446ad4e/proxyclient/tools/linux.py).
It requires an existing working proxy; it uploads DT, kernel and initrd into heap
allocations and calls `cpufreq_init`, `smp_start_secondaries`,
`kboot_prepare_dt` and `kboot_boot`. Finding those methods does not establish a
physical controller path. Baseline T6050 USB2 is deferred, the operator's CDC
delta is unpublished, and pinned Linux T6050 DWC3 is host-only. No Linux gadget,
M1-to-Linux upload, SSH or continuing remote control is assumed here.

Autonomous input removes that transfer prerequisite. A separately approved
camera observation could capture the display while the RAM diagnostic runs,
but cannot replace a kernel console/control channel, prove instructions that
never reach the screen, or recover a failed boot. Native controller behavior,
recording and the complete stop/restore procedure remain separate work.

## Actual public input contract

Pinned Aura source: `bd9f3e8273dc79ae9095c19c2c4f32218446ad4e`.
[`src/payload.c`](https://github.com/aurora-silicon/aura/blob/bd9f3e8273dc79ae9095c19c2c4f32218446ad4e/src/payload.c)
provides the scanner, gzip loading, FDT selection, tagged initrd loading and
`payload_run`. `aura-raw.ld` puts `_payload_start` at `_end`; its load header
records `_end - _base`. These distinguish executable runtime from appended input.

Our strict subset is, in this order:

1. Exact sanitized J716c DT. It begins at the page-aligned runtime end, satisfying
   libfdt alignment; it stays below the earliest possible execution-pool start.
2. One gzip member containing the exact Linux Image bytes. Public
   `decompress_gz`/`finalize_uncompression` reserve the heap allocation, including
   the Image's declared memory extent, and `load_kernel` selects that copy.
3. One **outer gzip member** containing `aura_initramfs`, a little-endian
   32-bit length, and the exact gzip-compressed diagnostic cpio. Public loading
   decompresses the outer member into heap before `load_cpio` retains the inner
   archive. Keeping only an inline tag would leave the initrd pointing at input
   that can overlap the future pool; our layout refuses that alternative.
4. One fixed `chosen.bootargs` line, then a zero guard tail. No `boot=`,
   `chainload=`, EFI identity, disk path, TSO or graphics experiment is inserted.

The propertyless J716c DT ranks **1** in the real `payload_profile_rank`, including
when `os_firmware.version` is `V26_6_2`. The exceptional J613/J615 profile is not
used. This is not evidence that local 25G83 firmware executes the boot object;
it means this particular DT-selection rule does not reject it for being 26.6.2.

The root filename allowlist is `dev`, `proc`, `sys`, `run` and one static AArch64
`/init`. No extra modules or utilities are accepted; the exact init executable
still needs its own source/behavior qualification. The Image must have a valid 16 KiB
arm64 header and fit the 128 MiB pool by its declared memory extent and offset.
The DT retains all eighteen M/M/P CPU nodes and capacities, removes DROM data,
and disables described unqualified SEP/ISP/USB4 consumers. Static nodes do not
establish online cores, scheduling, frequency scaling or performance.

`payload_run` also performs CPU initialization, secondaries and mitigations,
prepares runtime DT fields and enters `kboot`. Its source calls include frequency
setup, NVMe shutdown and the later PCIe/DAPF handoff. These are real controller
operations on hardware. A RAM-root design and source inspection do not prove the
absence of firmware-side effects or storage writes. Failed/missing secondary startup can leave fewer CPU nodes in the
prepared DT. The diagnostic must report actual online/concurrent CPUs.
The main routine still has final pending-call, NVMe, USB/exception and display
cleanup gates before it vectors. The parser mock does not execute these gates.
The real pure `stage1_proxy_payload_action` does select a valid native payload
even with neither CDC nor KIS available; that decision is included in the mock.

## Runtime slot versus temporary input

The reviewed baseline runtime is **3,997,696 bytes**. With the actual 31AH Image,
sanitized DT and private diagnostic root, the original builder produced
**19,639,230 raw bytes**. That input exceeds 16 MiB; it does not enlarge `_end`.
The loader's source-compatible encoded payload is temporary data, not additional
Aura instructions or retained initrd memory.

[`ctxr_exec.c`](https://github.com/aurora-silicon/aura/blob/bd9f3e8273dc79ae9095c19c2c4f32218446ad4e/src/ctxr_exec.c)
starts the 128 MiB OS pool at `align_up(Aura_base + 16 MiB, 2 MiB)`. It checks
the runtime end, armed bounds, firmware/read-only ranges, boot arguments and
heap. It does not require the entire encoded payload to fit Aura's runtime slot.
[`kboot.c`](https://github.com/aurora-silicon/aura/blob/bd9f3e8273dc79ae9095c19c2c4f32218446ad4e/src/kboot.c)
reserves retained ranges outside the pool, copies/fixes the DT into heap, refuses
an initrd/DT overlap with the pool, and moves the heap Image to the pool only
after payload scanning has finished. Thus temporary compressed input may be
overwritten at the final kernel move once all retained objects have moved out.

`extend_exec.py` is a separate bounded adapter; it changes no frozen formatter.
It authenticates the exact baseline runtime, validates the inline stream against
the exact three input artifacts, and extends the public wrapper's code segment
to the same fixed execution geometry. It preserves raw bytes and entry/vector
values and moves both headers' post-code metadata consistently. Full output
revalidation checks zero padding. Its receipts always retain native/enrolled/
restart fields as false. The enlarged input does not qualify live permissions.

`layout_model` accepts hypothetical addresses only. It checks overlap/overflow
requirements and illustrates heap staging; it does not reproduce the complete
allocator or read firmware registers. Actual base/window bounds, retained
firmware buffers, available heap, EL2 entry and all runtime DT fixups must be
qualified on the target. Aura enters Linux directly with its prepared DT in
x0 and cleared x1–x4; the old resident SPTM observer ABI is not used.

## Tools and evidence

`inline.py` is original, host-safe Python using only the standard library and
the project's frozen FDT reader/checker. It reads public source **as data** and
checks selected Git blob pins before producing `payload.bin`, `aura-inline.bin`
and `plan.json` in a new workspace directory. It refuses unknown baseline bytes,
input symlinks, wrong board/core/layout/root data, extra configuration and
oversized/truncated/corrupt members. Compression versions and exact output hashes
are recorded; byte identity across different zlib versions is not promised.

`test_inline.py` contains 37 original host-safe cases. Synthetic executable
bytes are never executed. The actual local input build and tests are evidence
of format handling, not CPU execution or firmware acceptance.
All thirteen fields of every newc record must contain exactly eight hexadecimal
characters. Signed, whitespace-prefixed, `0x`-prefixed and other nonhexadecimal
spellings are refused before conversion; uppercase hexadecimal remains valid.

`test_extend_exec.py` adds 22 distinct host-safe format/refusal cases using an
independent metadata encoder. Only its unittest context substitutes a synthetic
baseline pin; production admission has no digest override. Cases cover nested
text overlap, entry/vector movement, UUID/prelink/header inconsistency, corrupt
compressed bytes, retained-inline-initrd refusal, large temporary input, and
output preservation. New adapter identity checks bind both UUIDs and the prelink
identity to the full raw stream, including appended input.

`run_public_mock.py` runs only inside the isolated Linux VM. It authenticates
the selected public sources, then compiles the real `payload.c` scan/load/run
functions, real tinf gzip/CRC code and real libfdt/profile selection. Original
fake hooks replace ADT identity, heap backend, CPU/NVMe work, runtime DT fixups,
physical window movement and kernel entry. It checks exact Image/DT/initrd
bytes and preparation order, both profile modes, checksum/board refusals,
mitigation timeout, prepare/boot failures and an initrd retained in inline input.
The emitted receipt distinguishes executed pure parser code from mocked hardware.

Completed November 13 controls: 37 input cases and 22 extender cases PASS;
the actual pinned-source VM mock passes eight cases, including propertyless-DT
rank 1 in both profile modes and native-payload selection with neither carrier.
An independent read-only audit verifies all 26 selected source pins, the VM
receipt's four input digests and the actual expanded candidate. Its 153,190,400
bytes hash to `0d43feada6d758fcfea2ce78b4fd9f21ae4b7a7450ab06ba9e8c6c06b834dc4d`;
raw data, entry/vector and zero padding pass, including the strengthened identity
guards. This is workspace artifact evidence. Native entry and hardware remain
NOT RUN; no physical authorization follows from these controls.

Example VM-only sequence, using exact workspace paths supplied by the parent:

```sh
python3 -I kernel/experiments/direct31ai/transport/run_public_mock.py \
  --source-tree "$AURA_SOURCE" --payload "$INLINE/payload.bin" \
  --image "$IMAGE" --dtb "$DTB" --initramfs "$RAMROOT" --output "$MOCK_OUTPUT"
python3 "$AURA_SOURCE/tools/macho_boot_object.py" \
  "$INLINE/aura-inline.bin" "$INLINE/aura-inline-unpadded.macho"
python3 -I kernel/experiments/direct31ai/transport/extend_exec.py \
  --macho "$INLINE/aura-inline-unpadded.macho" --raw "$INLINE/aura-inline.bin" \
  --image "$IMAGE" --dtb "$DTB" --initramfs "$RAMROOT" \
  --output "$INLINE/aura-inline-128m.macho"
```

The exact public wrapper is never executed on macOS. No tool above opens a USB
endpoint or changes a boot object/policy. Diagnostic binary/root outputs remain
private workspace artifacts under the existing source/relink delivery limit.
Public code here contains no Apple bytes or decompiler output. Actual receipt
files determine which VM controls and layouts passed; this document predeclares
no native result, camera session, firmware change or authorization.
