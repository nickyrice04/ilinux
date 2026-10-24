# 31Z — independent M1 entry and memory-component review

**OFFLINE_PASS_NATIVE_HOLD, 2026-10-24 Eastern. Native 31Z HOLD / NOT RUN.**
Pulled main with `git pull --ff-only`, from `776b54f` through
`516ed2ceded7fa7f4625d1981c7a4932e30afcce`. The worktree was clean; no prior
work discarded. [Reviewed metadata](attempt31z-m1-offline-2026-10-24.json).

## Actual M1 checks

All **17 current manifest entries PASS**, documented shasum command exit 0 in 0.021 s.
Manifest SHA-256:
`2332878cf180e95df264a7b04fe1b24ce458074267dab461046f0ddaf0b8e9df`.

The documented `run.py --sanitize --freestanding` command completed once,
exit 0 in **2.495 s**, using an unused ignored output directory. Actual M1 tools:
Python 3.13.5, Apple clang 17.0.0 (clang-1700.3.19.1), macOS 26.0.1 / build 25A362.
No tool install, skipped check, source repair or retry.

| Independently executed on M1 | Result |
| --- | --- |
| Entry optimized | 8 groups PASS |
| Memory optimized | 8 groups PASS |
| Entry ASan + UBSan | Same 8 groups PASS |
| Memory ASan + UBSan | Same 8 groups PASS |
| AArch64 freestanding compilation and ELF symbol inspection | 2 objects PASS |

**16 unique C groups**, with sanitizer repetitions counted separately rather
than as additional groups. Exact expected success markers and empty run stderr
were checked for all four executions. Entry coverage includes 854 rejected lengths
and 848 byte-position checks; the independent memory bitmap oracle covers 2304
configurations. Every test marker and all eight source bindings equal the published
M5 host and final ARM64 Linux VM records. Source-binding SHA-256:
`dedeb9a2ba256ccde2e79520fcd52603d534702af61eb080b81a4390effafd9d`.

Both cross-compiled objects are ELF64 little-endian AArch64 relocatables, also
checked independently from their headers. They were neither linked nor executed:

| Object | M1 SHA-256 | Undefined runtime symbols |
| --- | --- | --- |
| entry-aarch64.o | `73b30bacb0b0b4ee776b7b9fd418df11bb87968ae2fc67763b288d8a2b7698e4` | none |
| memory-aarch64.o | `a887f0644777f3a18cb9b385e36226006357855a5be77c4d5663c98b28642b54` | memcpy, memset |

Object hashes differ from M5's newer compiler as allowed by the handoff. Runtime
implementations and a linked integration are still required. Raw commands,
compiler paths, binaries and logs stay ignored; public metadata contains only
the original synthetic-test results and reviewed hashes.

## Independent code and scope review

Read both original C APIs, implementations, tests, runner and README; both 31Z
research notes; REA, host and VM validation records. **No actionable blocker found
within the documented offline scope.** No production or test source was changed.

Entry classification compares the whole 64-bit reason and preserves all raw words.
Unknown reasons grant no typed role; mismatched snapshots and unsupported profiles
refuse without changing output. The typed boot accessor and monitor snapshot are
cold-only. Copying requires exactly 848 bytes from a separate caller-readable buffer,
never dereferences captured numeric pointers, owns its snapshot, and decodes only
the little-endian physical allocation boundary at byte 24. Unaligned byte buffers
are supported. Actual source identity, buffer binding, stability and nonoverlapping
valid C objects remain explicit caller requirements. The enum cannot authenticate
an actual monitor handoff; real snapshots may contain private seeds/state.

The memory planner rejects overflow, invalid/alignment-inconsistent bounds,
monitor-before-iBoot ordering, out-of-RAM reservations and duplicates/overlaps,
including overlaps below the allocation boundary. Validation and local construction
precede the output assignment. Sorting at most 16 reservations gives at most 17
available extents; their disjoint total fits within the validated RAM interval.
Reservations crossing the allocation boundary are clipped by the complement computation; touching
ranges and an empty result are valid, and retained inputs are owned copies.
There is no reservation-release permission. Correct physical RAM/page inputs and
all live images, argument buffers, tables, stacks, firmware and device reservations
must be supplied independently; virtual aperture bounds cannot stand in for RAM.

The runner uses bounded subprocess calls and argument arrays, requires fresh output,
checks exact success output, binds all eight component files and rejects a source
change across execution. Optional ELF inspection is bounded by object contents;
it inventories runtime dependencies, not firmware acceptance. No monitor dispatch,
MMIO, transport, registration planner, lifecycle validator, native entry assembly
or native controller is present.

## Research evidence and remaining gates

M5's retained/current-kernel comparison, four REA requests and SDK/header/source
checks are **reviewed upstream evidence, not independently reproduced on M1**.
Its two cancellations and two limited dossiers remain recorded; neither completed
dossier admits whole-function pseudocode. The reported 1672 independently checked
words/zero mismatches do not repair those refusals. The first minimal VM's missing
sanitizer runtime failure remains distinct from the final VM084 pass.

The selected848-byte consumer observation agrees with none of the measured SDK
sizes 832/840/856/864/872/880. Agreement at one physical-field offset is not a
complete ABI. M5's evidence qualifies registration using one zero-extended32-bit
ADT affinity argument, with boot-CPU-first ordering under an already resident
monitor before lockdown. It establishes neither monitor activation after raw
entry nor the missing step in earlier failed boots. No registration implementation
or native acceptance result follows from these helpers.

REA/private kernel decoding, SDK conditional-layout compilation, external-source
retrieval and M5 VM/Linux sanitizer execution were **NOT RUN on M1**. The required
macOS ASan/UBSan checks did run. Prior executable suites and31Y's read-only inspector
matrix were not repeated; their source identities were verified separately.

Remaining gates: accepted host-image construction, actual entry stack/translation
state, the complete matching monitor/helper contract, argument lifetime and memory
ownership, fixups/exception lifecycle, ordered registration/per-CPU continuation,
and physical-secondary observation. A working software bootstrap and an Apple-only
necessity both remain unproved. No native image or boot attempt is ready.

## Preservation and handoff

All **19 earlier frozen manifests and 5739 listed-file hash checks PASS unchanged**;
these are manifest-entry checks, not 5739 distinct files. The retained 13-file boot042
package is byte/size-identical to its earlier receipt. Installed boot021 remains
unchanged. Client checkout is clean and still pinned to
`57a9339ffd1876e78297b17d34dece8cff8fa1ba`.

Before/after SHA-256 comparison preserves **499 prior intake evidence files**, counted
recursively across existing attempt31 directories, including consumed receipts.
No new 31Z native-use file exists. Compiler temporary directory is empty; the owned
bounded caffeinate process had exited. Prior public reports and source closures
were not edited. Evidence remains under ignored `build/native-intake/attempt31z-offline/`
and `build/31z-adapter-m1-review/`; receipts have not been cleared or reused.

**Neither Mac restarted. Native 31Z, CPU startup, Linux SMP, GPU acceleration and
live target-version checks remain HOLD / NOT RUN.** Discovery queries, device opens,
target requests and native invocations 0. No installation, installed-object, security,
firmware, volume or default-startup change and no external contact. Original Full /
lab Permissive / Macintosh HD default remain last reported, not freshly checked.
The next work is qualified offline integration on the M5 agent's side.
