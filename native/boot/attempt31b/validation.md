# CPU1 controller 31B — offline validation and limits

2026-10-21. **Native 31B NOT RUN.** This is an original RAM-only controller for
the installed boot021 image, not the earlier rebuilt m1n1 candidate. Exact
source hashes, compiler flags and final guest timestamps: [validation.json](validation.json). The M1
checklist is `tools/m1n1-client/attempt31b-instructions.md`.

## Evidence and implementation

M1 census 31A at `527defe` observed locked CPU0/CPU1 mirrors pointing to the
installed vectors. Previous byte-validated REA of this Mac's PMGR driver and
the sanitized ADT locate misc-cores at `0x280688000`; the known public m1n1
CPU1 sequence uses value 2 at offsets 4 and 8. CPU1 is in cluster 0: the later
six-core cluster-stride correction does not change those two values. Reuse
the accepted REA behavioral evidence (`kernel/experiments/smp31/rea-validation.json`),
not its rejected cross-boundary pseudocode. No new Apple binary decompilation
was needed for this controller; the immediate question concerns the installed
open-source entry and requires native observation.

`audit_boot021.py` and `boot021-ram-layout.json` verify the linked layout. Source
inspection additionally covered m1n1 startup, exception, proxy, UART proxy,
memory, CPU features and client execution/serialization paths at revision
`57a9339ffd1876e78297b17d34dece8cff8fa1ba`. The controller compares startup bytes
and the entire linked code region against the pinned image. Eight
R_AARCH64_RELATIVE literals in text are reconstructed from the verified image
and runtime base; none are skipped. It validates the exact features_m4 pointer
and 20-byte descriptor used by this part, all 18 topology records, all 32 spin
records, fresh stack table, and primary identity. Hardware ID and topology,
not a marketing model name, select this path.

The helper is 192 bytes, with original assembly in `helper31b.S`, embedded as
instruction constants in `smp31b.py`. It runs on CPU0 through the bootloader's
existing executable alias. Allocation is 16 KiB, aligned and checked against
boot-args RAM bounds and the existing image. Upload/readback, data-cache clean
and instruction-cache invalidation precede execution; existing proxy requests
end with DSB SY/ISB. No mapping/security permission is changed. Register reads
require EL1/EL2, no reported EL3, Apple part 0x068, CPU0 MPIDR and enabled MMU.

The original bounded helper adds aligned RAM reads, an OR scan capped at 256
words and a single RAM target publication followed by DSB/SEV. It has no MMIO,
MSR, stack or literal pool. CPU1 executes the installed `timeout_calculate(0)`
twice, returning through the installed SMP loop. Timer values stay private;
only monotonic progress is reported. Other cores' complete spin records are
checked to remain zero, not just their alive flags.

The installed `smp_call` waits without a bound, and the WFE setter sends IPIs
after a secondary is alive. Neither is used post-start. More subtly,
REQ_MEMREAD resets a shared exception counter and temporarily changes a shared
guard; reading the guard itself also gives a self-inconsistent checksum.
The controller therefore reads diagnostics through its guard-free helper once
ready and performs **no bulk read or read/clear of that counter after start**.
After startup, request publication is also guard-free. The two startup MMIO
writes still use the installed guarded-write protocol and check diagnostics
after each. Diagnostics have the existing bootloader's limitations; this is
not a proof that every possible secondary exception is observable.

The controller never manufactures CPU1's identity/arrival/stack-table evidence.
It retains the dedicated stack after timeout, never retries or frees state,
and leaves shutdown to the human. A receipt is created exclusively and fsynced
before any target allocation. Mutation intent is durable before dispatch.
The separate supervisor enforces its own deadline and kills only its child
process group. Both refuse reuse; no force/reset option is provided.

## Offline tests

* **46 Python methods PASS** on the M5 host: 19 controller, 3 supervisor,
  11 unchanged census, 5 prior layout audit, 8 renderer regression tests.
  Controller cases include fault/lost reply at each of 11 mutation points,
  exact-address/value allowlists, wrong/stale state, changed relocated
  literals, invalid helper/CPU identity, late arrival, no arrival, pending
  request, stalled counter and retained fault evidence. These use synthetic
  hardware and are not native evidence.
* GCC 16.1.1 and Clang 23.1.1 independently assemble identical 192-byte helpers,
  SHA-256 `dc046b303191b9a4fcb26a9e689fa4ec7b936dd1ae67dc5fd9b81c4edf4bf8aa`.
  No relocations; instruction audit covers all 48 words, including padding.
* **Actual ARM64 helper execution PASS** in Linux userspace: aligned read,
  zero/240/256-word scans, 257/UINT64_MAX refusal before dereference, and RAM
  publication/DSB/SEV. Privileged register entries were compiled and inspected,
  not executed at VM userspace EL0.
* **Actual pinned-client serializer PASS** with an independent fixed-opcode
  endpoint model. It exercises the complete controller; no bulk start, stop,
  SMP-call, wait or Linux opcode appears. No USB or native proxy involved.
* **Actual pinned secondary-loop and timer source PASS**, both optimized and
  ASan/UBSan builds: entry, correct stack/identity, two requests and idle-loop
  visits. Synthetic registers, atomic shared fields and host sleep model the
  relevant interfaces. This does not emulate reset, Apple cache coherence,
  exception state, WFE power behavior or PMGR.
* Real pinned ADT-parser fixture PASS for the exact 18-core topology and known
  boot-args revisions, rejecting unknown revision. Final VM job 059 guest exit 0
  on Linux 7.1.6-vzrun2 aarch64, existing 12-vCPU/24-GiB VZ guest.
  The job wrapper's process exit is not substituted for its guest result.

Initial iterations retained as limitations/history: the first small helper
assembled successfully; after expanding it, the old embedded digest correctly
refused it until reviewed constants were updated. A receipt test initially
tried to write under the read-only source mount; the fixture was corrected to
use its own temporary root. A late-response test first injected delay before
request timing began; its injection point was corrected to the publication RPC. These were offline failures, not target attempts.

Reproduce in the existing VM, under the project quiet/VM locks:

```sh
mkdir -p virtualization/jobs/059-smp31b/out
cp build/native-boot042/verified/m1n1.bin virtualization/jobs/059-smp31b/out/boot021.bin
tools/vm-job.sh virtualization/jobs/059-smp31b smp31b
```

Job 059 outputs remain ignored. Check `out/run.log` and `out/validation.log` for
guest exit 0 and every PASS; it builds normal and sanitizer tests with GCC,
compiles the helper with both toolchains, and executes no Apple artifacts.
No new VM disk, root repack, multi-GB download or host installation was needed.

## Native boundaries and next dependency

One human-started 31B, 3s arrival/1s per request, 2s serial bounds, 60s controller,
65s independent supervisor plus bounded termination, 90s human limit.
Observation deadlines reject late replies; a blocked RPC may outlast an
observation window until its separate serial/parent timeout ends it. No Linux,
CPU frequency, IPI test, secondary MMU enablement, storage or renderer change.
The existing secondary entry initializes architectural state; do not call the
whole experiment read-only or claim it performs only two hardware operations.
Only the controller's explicit MMIO writes are limited to those two CPU1 starts.

Even a PASS establishes only this short bootloader entry/request path. Native
Linux two-core DT/spin-table handoff, timer IRQs, scheduler/IPI/coherence checks,
thermal stability and renderer performance follow separately. An arrival
timeout does not identify the first failing instruction. The helper does not
instrument or rewrite reset entry, and cannot recover a wedged SoC.
