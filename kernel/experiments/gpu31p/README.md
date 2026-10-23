# 31P: dual-ASC descriptor and identity contract, offline only

This original Python/C code validates retained, sanitized T6050 GPU metadata and
round-trips its public 32-byte segment descriptor shape. It does not initialize
the GPU, generate a device tree, map memory, contact a target, or replay firmware.
An accepted contract keeps **GPU enablement HOLD / native NOT RUN**.

`contract.py --adt hardware/adt/adt-sanitized.json` checks J716c/T6050 identity,
the GPU's recorded MMIO/interrupt/power resources, both ASC roles, their shared
mapper and interrupt-controller references, and each parent's agreement with its
firmware nub. It preserves every descriptor field and rejects malformed widths,
lengths, spans, alignment and within-role overlaps. The decoder's generic
alignment policy is one byte; the observed-machine profile explicitly requires
16 KiB alignment. That is a profile check, not discovery of a GPU page-table ABI.

The public format names its first 64-bit field `phys`. Our name
`descriptor_phys` preserves that provenance without claiming it is a usable CPU
physical address. IOVA, remap and descriptor address remain separate domains.
The last 32-bit word is opaque and survives unchanged. No flags are inferred.
The two roles legitimately overlap in IOVA space. The `sgx` aggregate MMIO window
also contains smaller resource windows. Neither is rejected as an accidental
global overlap. Unique paths and handles are enforced for the nine contract
nodes; duplicate unrelated PCI service paths in the retained IOKit capture are
not mistaken for duplicate GPU nodes.

The portable C library provides bounded encode/decode/validation functions with
no allocation or file/device I/O. It supports unaligned byte buffers, checks all
address additions and length/count conversions, and leaves output untouched on
failure. The caller must provide valid accessible buffer capacities and distinct
non-aliasing input/output arrays. End-exclusive 64-bit overflow is conservatively
rejected, including a range ending exactly at `2^64`.

From the repository root:

```sh
python3 -I kernel/experiments/gpu31p/test_contract.py
python3 -I kernel/experiments/gpu31p/contract.py --adt hardware/adt/adt-sanitized.json
mkdir -p build/gpu31p-check
cc -std=c11 -Wall -Wextra -Werror -pedantic -O2 \
  kernel/experiments/gpu31p/segments.c kernel/experiments/gpu31p/test_segments.c \
  -o build/gpu31p-check/test-segments
build/gpu31p-check/test-segments
```

The C test prints only `GPU31P_SEGMENTS_PASS` on success. Its 12 test groups use
synthetic literal golden bytes, not Apple firmware. The Python suite has 38
methods covering those byte semantics, actual retained metadata, and hostile or
contradictory inputs. Tests create temporary files only below the repo's ignored
`build/` directory. The CLI reads one bounded regular file, refuses symlinks and
special files, rejects duplicate JSON keys/nonfinite numbers, and emits only
fixed labels, counts, booleans and hashes. `--live` is not an option.

`adt-validation.json` records the actual retained ADT result independently of the
synthetic tests. Its positive result does not verify firmware execution, UAT
translation, GPU memory coherence, a render/compute result, or performance.
See [the finding and implementation decisions](../../../research/native31p-gpu-contract.md).
