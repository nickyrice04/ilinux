# 31AB bounded observer preparation

This original portable component converts caller-owned snapshots into a small
framebuffer marker plan and exercises that plan against ordinary RAM. It is a
step toward an observable resident-host entry; **native use is NOT_DEPLOYABLE**.
It neither modifies nor links into the frozen `sptm31ab-host` entry artifact.
There are no monitor calls, address-translation instructions, target-pointer
dereferences, page-table writes, device operations or display accesses here.

The range parser uses the independently checked local behavioral contract:
an externally supplied bounded count, 24-byte records, 64-bit physical base at0,
64-bit virtual/PAPT base at8, and 32-bit page count at16 in 16KiB units. It ignores
the opaque final four bytes. The caller must establish the actual range-array
snapshot's source, extent and lifetime. This is not a decoder of the entire
monitor record or a replacement for opaque helper initialization. The implementer
used behavioral reports and public declarations, without reading Apple output.

The selected boot-video prefix follows the pinned public ARM64 `boot_args`
declaration: revision/version at0/2 and six 64-bit video fields at40–87. The
decoder accepts exactly that88-byte selected prefix, revision2/version2 and
depth low byte30 or32; it preserves the display and high depth metadata and
strips only the base's low two metadata bits. All six fields use explicit
little-endian reads. The physical video base is never cast to a pointer.
See the [observer contract](../../../research/native31ab-observer.md) for public
source provenance and its limits. Size/version agreement alone does not
authenticate an incoming boot record.

Original stricter policies make the result suitable for bounded integration:

- Maximum64 range records, exact count×24 snapshot extent, nonzero page counts,
  16KiB-aligned bases and checked half-open interval ends. Physical or virtual
  overlap is refused, including duplicate ranges. Input order is preserved.
- Translation requires complete interval coverage and a nonzero resulting VA.
  Adjacent records may be crossed only if their translated VA intervals are
  contiguous. A valid table entry is not proof of write permission or cache type.
- A marker is at most32×16 pixels. Full framebuffer width/stride/height/base
  arithmetic must fit64bits; every selected row must be covered by the table.
  Rows use four bytes/pixel and raw framebuffer coordinates. Rotation/scale and
  the meaning of the display field remain outside this component.
- Outputs remain unchanged on failure. The RAM painter checks every row, buffer
  bound and row overlap before its first store. Input/output objects must not
  overlap. A late invalid row therefore cannot produce a partial paint.

`obs31_paint_ram` accepts an ordinary byte array and a numeric virtual-address
label. It never dereferences a planned numeric address. It writes a bounded
border/checker pattern with caller-supplied raw little-endian pixel words;
depth30 rejects the upper two bits as an original restriction. It does not
interpret channel order or supply volatile MMIO stores, barriers or cache
maintenance. Successful RAM output is neither scanout evidence nor permission
to use the same stores against a live framebuffer.

The next integration needs a separately qualified writable alias, translation
regime and framebuffer cache/visibility contract. A translation probe can
contribute evidence for a specific alias but does not authenticate the table or
prove framebuffer visibility. Keep the owned entry/fault record and a positive
observer signal before adding fixed monitor calls. No CPU registration or
secondary start is part of this component.

Run the same dependency-free test runner on macOS or ARM64 Linux, using a fresh
ignored result directory (the VM controller supplies its own output path):

```sh
python3 -I kernel/experiments/observer31ab/run.py \
  --output build/observer31ab-host --sanitize --freestanding
```

Twelve unique C groups cover malformed snapshots, arithmetic overflow, physical
and virtual overlap, noncontiguous translation, all1200 small sparse-table
oracle queries, descriptor revisions/depth, bounds, cross-record rows and
whole-buffer canaries/unchanged failure output. Optimized and ASan/UBSan runs
are separate variants of those same groups. The optional freestanding AArch64
object is compiled and its undefined symbols recorded using the unchanged,
hash-pinned original31Z ELF checker. It is not linked or executed; any listed
runtime helpers remain future link dependencies. Results bind all five sources
and that checker. No proprietary header is needed to build or run the tests.
