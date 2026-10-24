# 31Z entry snapshot and physical-memory planner

This original portable C component preserves a bounded cold-entry argument
snapshot and computes allocator extents without reusing monitor-owned memory.
It contains no entry assembly, monitor calls, dereferences of captured addresses, mapping
operations or native controller. **NOT_DEPLOYABLE:** the versioned observation
below does not establish a usable SPTM launch or native boot contract.

`entry.c` classifies the full 64-bit reason word while retaining all three raw
argument words. Unknown reasons retain the observation and grant no typed role.
Only cold reason0 yields typed iBoot/monitor argument words; panic reason4 has
a separate accessor. Secondary1, warm2 and hibernation3 remain comparator labels
with raw words, not authority to reuse cold initialization. Unsupported profiles
and inconsistent snapshots are refused. No captured address is dereferenced.

The explicit `SPTM31Z_T6050_25G83_OBSERVED` profile refers to the retained/current
T6050 kernel with SHA256
`2bd94a6fcff6203861e46b39920c16e1b5563d9bb17405b8a42c59c2ef4486e0`
(17,168,528 bytes, macOS26.6.2/25G83). The independent 31Z investigation found
that its cold path forwards incoming x1/x2 as iBoot/monitor arguments and copies
**848 monitor bytes**. The snapshot helper copies exactly that many bytes from
a separately supplied readable buffer into caller-owned storage. The caller
must bind the buffer to the captured pointer, establish readable/stable storage
and verify the source identity. Selecting the enum does none of those things.
The library neither detects versions by length nor authenticates entry state.

Only one field is decoded: the little-endian u64 at byte24 is the first available
physical address. Its qualification combines the exact local cold consumer's
unchanged forwarding to the corresponding global with the public XNU assignment
and matching field meaning in both measured SDKs. The rest remains opaque.
Measured SDK26.5 physical/virtual layouts have832/840 bytes; SDK27 variants have
856/864/872/880 bytes depending on virtual-platform/MTE settings. None matches848.
Their other offsets are not imported into this API. The tests refuse every
truncated length and all four larger SDK sizes. Successful decoding does not
establish ownership, pointer validity or physical bounds; the decoded value must
pass the memory planner with independently qualified inputs before allocation.
Monitor argument buffers may contain random seeds or other sensitive state:
keep snapshots private and do not serialize or log their payload. Public tests
use only synthetic bytes. Keep the owned snapshot alive while consumers use it.

`memory.c` accepts **independently decoded physical** RAM bounds, the monitor's
first available physical address, iBoot's physical high-water mark, a page size
and up to16 live reservations. It returns the exact complement of those
reservations within `[monitor_first_available, ram_end)`, with owned copies of
its inputs. It checks overflow, containment, alignment and disjointness before
changing output. The monitor boundary cannot precede the retained iBoot mark;
that inconsistent ordering is refused instead of repaired by taking a maximum.
Unsorted reservations are accepted; overlaps and duplicates are refused even
below the allocation boundary. Touching ranges and an empty result are valid.

This is useful when constructing an allocator after a qualified monitor
handoff: the older iBoot allocation mark alone can point into pages subsequently
used by the monitor. A counterexample test demonstrates this, and an independent
bitmap oracle checks all256 reservation subsets at all9 boundaries in an
eight-page model. The planner does not establish that supplied bounds are true.
PAPT bounds are virtual aperture addresses and must not be substituted for
physical RAM. Every live image, argument buffer, stack, table, firmware and
device reservation intersecting the candidate interval must be supplied.
Reservations remain owned for the whole plan lifetime; this API cannot release
them, and reconstructing a plan is not permission to reuse them.

The qualified public contracts and SDK provenance are summarized in
[the 31Z public contract](../../../research/native31z-public-contract.md).
Official XNU's entry comment describes x1/x2 roles for all nonpanic reasons;
the cold-only typed accessor here is a stricter local-evidence policy. The
local full-width comparisons confirm cold0/panic4, while the other numeric
labels come from the measured SDK26.5 comparator. Newer SDK27 reason5 is retained
as an unknown observation, without argument roles. This component does not claim a
complete local warm, secondary, hibernation or panic producer contract.

The component intentionally has no "fixups complete" or CPU-registration
success Boolean. Such a caller assertion would not establish permission changes,
register CPUs, or provide a qualified monitor call interface. Those operations,
the actual stack/EL contract, source argument lifetime and native launch remain
separate prerequisites.

Run the same dependency-free runner on macOS or Linux, from the repository root,
with a fresh output directory:

```sh
python3 kernel/experiments/sptm31z-adapter/run.py \
  --output build/31z-adapter-host --sanitize --freestanding
```

`--cc` and `--clang` accept single executable paths. The runner executes only
these original synthetic tests, using C11, `-Wall -Wextra -Werror -pedantic` and
`-O2`; optional sanitizer repetitions use `-O1`, ASan and UBSan with recovery
disabled. It records source hashes, compiler identities, commands, stdout/stderr
and results in the fresh directory, refuses an existing output directory and
fails if a source changes during the run. There are16 unique C test groups;
sanitizer repetitions do not increase that count. The entry suite covers854
invalid lengths and all848 byte positions; the memory suite covers2304 bitmap
cases as well as boundary, overlap and overflow failures.

The freestanding option compiles two AArch64 ELF relocatable objects with Clang
without an SDK. A bounded standard-library ELF reader inventories their undefined
symbols. Any `memcpy`/`memset` or other runtime dependency must be supplied by a
future integration; the runner does not link or execute these objects. Unsupported
object inspection is an explicit failure. Compilation and synthetic host tests
are software validation, not evidence of firmware compatibility or native boot.
