# 31AF: review the immutable observer, then one bounded native test

**Preparation/review only. No new native write or restart is authorized by this
file.** The single 31AE experiment is consumed. Read the
[31AE result](../../native/boot/attempt31ae-recovery-2026-10-25-result.md),
[31AF decision](../../research/native31af-decision.md) and
[public-source review](../../research/native31af-public-contract.md).

31AE passed installation but produced no observed marker. Its record and stack
overlapped the monitor reservation. 31AF removes that assumption entirely: no
stack, C calls, image writes or monitor services, and a larger centered marker.
The reservation has the public reference footprint; that is not a proven minimum.
The remaining entry profile is explicitly resident cold/EL2 with supported MMU,
translation and supplied-table state. Unsupported cases remain silent; a missing
marker would still be inconclusive and would not prove an Apple-only blocker.

## M1 offline review

Pull main with `git pull --ff-only`, preserving local work. Verify every source
pin in `native/boot/attempt31af/source-sha256.txt`. Download the archive and
standalone candidate using the Git manifest, checking exact sizes and hashes
before inspecting members. Run `native/boot/attempt31af/verify.py --archive <file>`.
Read extracted members only as data. Exact boot021 is included with its license
and source revision; it must equal the previously retained restore image.

Using existing tools only, the focused suites are:

```sh
python3 -I kernel/experiments/bootimage31af/test_image.py
python3 -I kernel/experiments/bootimage31af/test_rejected31ae.py <retained-31ae-candidate>
python3 -I tools/recovery31af/test_write_render.py
python3 -I tools/recovery31af/test_prepare.py
python3 -I native/boot/attempt31af/test_verify.py
python3 -I kernel/experiments/immutable31af-test/run.py --self-test
```

The five unittest suites contain 47 methods. The exact-old-image suite requires
the hash-pinned 31AE candidate. The self-test is a separate fixture-generator
check and runs neither a compiler nor an emulator. Do not repeat unrelated
suites or the known incompatible host LLD script.

Reconstruct the original zero-header payload from the downloaded candidate as
16 KiB of zero followed by candidate bytes `0x8000..0x64000`; verify its hash
against Git. Validate the image with `bootimage31af/validate.py`, then round-trip
it through `image.py` and require byte equality. The validator checks complete
geometry, both header views, both finite arithmetic profiles and payload binding;
it is not Apple's full acceptance contract.

Review the separate M5 evidence without presenting it as locally rerun: host
compile-only, GNU two-base link, compiled instruction audit, complete-payload
emulation with read-only populated reserved memory, old first-store negative
control, and actual read-only Apple property derivation. The runtime harness
does not emulate Apple firmware, native panel scanout or physical CPU startup.
Publish a sanitized review naming exact commit, hashes, rerun/reused evidence and
any actionable finding. Preserve all previous frozen files and consumed receipts.

## Streamlined Recovery pages

After verifying the source closure, generate both full phases without executing:

```sh
python3 -I tools/recovery31af/prepare.py --output build/31af-reviewed-pages
```

Compare install, rollback and HTML against the archive and `bash -n` each full
block. The page has only **Install** and **Rollback**. The user has already
demonstrated clipboard transfer in Recovery; **do not add a separate clipboard
smoke command or repeat the inspector control matrix**.

After M1 PASS and the human's approval of the exact new candidate/sequence,
serve only this reviewed page directory through the same private local workflow.
Confirm readiness before M5 restart. M1 needs no restart, proxy or USB controller.
Credentials and raw private evidence stay local; never publish server addresses,
machine identifiers or unredacted Recovery images.

## One authorized physical sequence, when separately approved

1. Use the established temporary **iLinux Boot Lab** Startup Disk/paired Recovery
   flow. Keep the lab selected through installation and rollback Recovery. No
   new security or volume change. Original Macintosh HD must remain Full.
2. In Recovery's Web Browser, open M1's reviewed page and copy the **complete
   Install block**. Quit the browser, open Utilities → Terminal and paste once.
   It independently checks lab identity/pairing/build, exact helper/boot021 and
   original Full/lab Permissive, then hashes the same candidate pathname before
   one Mach-O configure command. No raw candidate flag and no hand edits.
3. Read Apple's prompts. Enter the requested volume administrator username first,
   then the password when asked. Record configure/capture/block exits and any
   actual error privately. A nonzero result ends candidate testing; use only the
   fresh-guarded exact rollback, without changed flags or a retry.
4. Only after the install and policy postcheck succeed, boot the lab once. Start
   a **30-second timer**. Look at the **center of the display for a 128×64 black
   and white bordered checkerboard**, rather than the former tiny top-left
   pattern. Record marker present/absent or actual firmware text. At 30 seconds,
   power off even if only the Apple logo remains; do not wait several minutes.
5. Return to lab-paired Recovery. Copy the independent **complete Rollback block**,
   quit the browser and paste once in Terminal. It restores exact staged boot021
   (3932160 bytes, `ff75f4a9…072664`), raw entry 2048 and lowest VA 0, after its
   own fresh guard. Record numeric exits and postcheck/success marker.
6. Return to **Macintosh HD** and restore it as default Startup Disk. Confirm the
   original desktop and default separately; stop the M1 page server.

No repeated desktop policy query, extra review/approval loop for the same already
approved phase, diagnostic-only clipboard paste, unchanged retry, DFU, erase,
firmware modification or security reduction is part of this sequence. If a fresh
Recovery guard fails, stop instead of guessing another target.

Publish a new result with each actual transition and distinguish observed values
from human reports. A marker proves entry through validated framebuffer stores;
final cache completion, monitor readiness, Linux, SMP, GPU and performance remain
separate outcomes. A blank result stays inconclusive. No subsequent boot follows
automatically from either outcome.
