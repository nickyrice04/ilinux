# 31AK: repair the Recovery workflow, then measure native SMP

31AK is a **procedure-only correction**. The installed test candidate has not
changed: it is the already built 31AJ Aura/Linux/RAM diagnostic, with the same
native reader, canonical profile and exact boot021 restoration artifact. Its
screen will still identify the diagnostic as 31AJ. No binary rebuild, transfer,
restaging, new volume, firmware update or security change is required here.

## What actually happened in 31AJ

The [M1 report](../attempt31aj-capability-refusal-2026-11-14.md) establishes a
Recovery capability refusal before target admission, baseline/key creation or
any enrollment/policy command. Recovery's legitimate `/private` alias met our
strict no-follow reader while it opened the copied profile. The separate
Recovery synthetic codec control passed. Linux never ran; zero native observation
windows were used. This is a deployment bug in our software, not CPU startup or
GPU performance evidence and not proof of an Apple-only barrier.

**Boot021 was not restored.** A fresh user-supplied read-only object check
identifies the contained lab payload as **EXACT_31AF**, with opaque wrapper
semantics still unqualified. A separate read-only M5 check confirms both current
Macintosh HD and its default Startup Disk. Desktop/default return is distinct
from changing the lab object. Evidence:
`../attempt31aj-post-refusal-object-2026-11-14.json` and
`../attempt31aj-post-return-2026-11-14.json`.

The next physical sequence must therefore still start from the actual 31AF
baseline and finish the intended raw boot021/disabled-CTRR restoration. There
is no reason to spend a separate native boot merely to fabricate that baseline.
No physical retry is authorized by these offline files.

## Implemented correction

New original code lives in `tools/recovery31ak/`. The renderer resolves only the
newly created owned work directory to its physical path before deriving native
helper/profile/snapshot paths. Directory device/inode, root ownership, mode0700,
physical components and a kernel-held working directory are compared repeatedly.
Temporary copies and snapshots use relative writes in that held directory;
cleanup removes only fixed temporary filenames and its verified empty directory.
The helper's descriptor-based `O_NOFOLLOW` rules stay unchanged. No system link
is edited and no persistent transaction state is deleted or re-armed.

Failure advice now distinguishes pre-enrollment refusal, guarded restoration
preflight refusal and an ambiguous result after a command was attempted. It
does not tell a user with no saved baseline to run restoration blindly.

The new package controller retains all 62 old portable source bindings and their
inventory, and admits the separately pinned new workflow. It reuses the original
preparer/server from verified source snapshots, replacing only the renderer and
source-inventory selector in memory. There is **no staging or boot mode** in the
controller. Default invocation only displays help; page check-only opens no socket.
Consumer source inventories contain explicit Git-delivered files, never ignored
producer executables. Old inventories, member files and receipts remain unchanged.

## Evidence and scope

* The actual unchanged native reader reproduces refusal through a symlinked
  profile path and verifies the same canonical profile/exact boot021 file through
  its physical path. `actual-helper-path-controls.json` records both controls.
  This runs only `--verify-file`, with no Recovery, policy or hardware query.
* Sixteen focused full-shell methods reproduce the old alias failure and pass
  corrected install/restore flows under the same Recovery-like layout. They
  cover owner/mode refusal, directory replacement, failure advice, preserved
  foreign data, independent restoration, exact HTML and unchanged write arguments.
  Hardware/root/policy state and write tools are synthetic; shell filesystem
  canonicalization is exercised on macOS.
* Fourteen package methods check source admission, unchanged original pins,
  producer/output refusal, fixed routing and inert defaults. Independent review
  repeated all 30 focused methods and found no material issue.
* `clean-export-verification.json` and `page-preparation.json` are generated
  records, excluded from their own input inventory to avoid a hash cycle. They
  record preparation from a Git-only export with just the existing four delivery
  files; no producer executable or new payload is supplied.

None of these results proves actual Recovery admission, successful installation,
18 physical CPUs, memory speed, native GPU acceleration or macOS parity. Those
remain physical questions. M1 reviews the changed 30 methods and exact new pages;
the unchanged 247-method reader/artifact/transaction review is reused.

## Shortest path to the requested workstation

1. Review this correction and run one meaningful, separately authorized RAM test
   of the unchanged candidate. Capture actual kernel entry and eighteen distinct
   pinned checksum workers across the real three six-core clusters, overlapping
   work intervals, timers, RAM integrity and liveness. Finish exact boot021/lab
   CTRR restoration and Macintosh HD default return. Keep Original Full throughout.
2. Once SMP is demonstrated, measure CPU-class scaling, actual frequency behavior,
   within/across-cluster wakeups, memory bandwidth and latency using the existing
   portable workloads against macOS. DT capacities 794/1024 are uncalibrated;
   online CPU count and the 64 MiB checksum do not establish performance parity.
3. Qualify N1 networking/SSH and native NVMe with a coherent pinned platform stack,
   starting with read-only storage. An agent can then work through a reliable Linux
   control channel. Write benchmarks require disposable Linux storage; accessing
   existing APFS/FileVault data is a separate feature and permission boundary.
4. Integrate matching G17C/kernel/Mesa/display prerequisites with the existing
   Omarchy root. Measure menu, typing and application/frame latency. Eighteen
   cores alone cannot guarantee a responsive, efficient software-rendered Retina
   desktop. Reuse the distro work instead of restarting it.
5. Measure sustained performance, energy per task, idle power, thermal behavior,
   suspend and peripherals separately. Functionality and macOS-class efficiency
   are distinct acceptance results.

[Current primary-source and exact-topology review](../../../research/m5-native-next-2026-11-14.md)
documents the same-board 18-CPU report, current Apple raw-boot fix statement,
M/M/P topology and relevant GPU foundations. A new SPTM guest-reset affinity fix
belongs to a different execution path and is not a demonstrated direct-Linux fix.
No blind rebase or firmware update is part of this correction.

REA remains useful for an observed early-entry or secondary-release failure.
For this own-source path fault, source review and the actual-reader experiment
provide more direct evidence than decompilation. The first native milestone
will determine the next specific firmware or driver question to trace.

M1 handoff: `tools/m1n1-client/attempt31ak-instructions.md`. **No restart yet.**
