# M1 handoff: 31X CPU workaround investigation

**Research review only. Native 31X HOLD / NOT RUN. No restart or proxy session.**
The user reopened the CPU search. This pass adds no startup controller, image,
GPU change or native-use authorization. Preserve the existing working boot.

## What changed

The strongest lead is the reported **resident-SPTM host** used by DJ on
J714s/T6050 with firmware 26A428. Its published tests describe all 17 secondary
cores and work-rate changes on the three clusters. These are more informative
than a guest CPU count, but remain one author's reports. The accepted host
bootstrap is not in the located public material. Our J716c/retained 25G83 setup
has not reproduced that path. This is a possible software route, not a working
local solution or evidence of macOS performance parity. This route initially
runs Linux under a small resident hypervisor; CPU throughput and power must be
measured before treating it as meeting the native-performance objective.

REA located context installation before the retained monitor's indirect
dispatch. That routine already requires execution and a validated handoff; it
does not establish the missing pre-first-fetch operation. The three checked
firmware wait loops return unconditionally to their waits, so an extra event
does not advance those loops to payload entry. Other entry paths remain unknown.

The independent audit found ten consumed starts with both stores acknowledged,
all targeting CPU1. No new address, publication or topology bug was found.
CPU2 is the least-confounded untested physical control, but lacks a specific
reason to expect success. A second negative would leave the main cause unknown.
There is no new native test justified by these findings alone.

## Review from the repository

Inspect `git status --short`, preserve local work, then `git pull --ff-only`.
If the histories diverge, report that without resetting or discarding evidence.
Read:

- `research/native31x-upstream.md`: positive report, attribution, source search
  and the exact missing host inputs.
- `research/native31x-firmware.md` and
  `reverse-engineering/findings/cpu-startup31x/validation.json`: one successful
  REA query, one rejected request, bounded instruction checks and limits.
- `research/native31x-cpu-audit.md`: what the consumed hardware tests establish
  and what remains untested.
- `native/boot/attempt31x/validation.json`: public evidence receipt and scope.

Check the new handoff's file hashes from the repository root:

```sh
shasum -a 256 -c native/boot/attempt31x/source-sha256.txt
```

All entries must pass. This checks file identity, not the truth of research
claims or native compatibility. Inspect the linked earlier records and pinned
public source for the substantive review. Private REA, instruction decoding,
retained Apple input and VM execution remain NOT RUN on M1 unless independently
reproduced. Do not download or upload Apple artifacts to satisfy the review.

The previous 31W implementation remains unchanged. If its independent review
is still outstanding, follow `attempt31w-instructions.md` separately and label
those results 31W. Do not count its synthetic tests as new 31X CPU validation.

## Most promising next input

Request the successful resident x1n1/SPTM host's source revision and build recipe
or a minimal original bootstrap, including board/firmware applicability and the
incoming context it relies on. Ask for a sanitized record linking a non-boot
physical affinity's host entry to its Linux execution. Public report:
[all-secondary probe commit](https://github.com/chriskearney/siliconforest-linux/commit/6c03bd926fc5672dc91457053c13b3e83ad30048).
The older `m1n1-aurora@j873` hash is an adaptation reference, not an identified
successful x1n1 host hash.

A concise draft for the user to send:

> Is there a shareable source revision and build recipe for the resident
> x1n1/SPTM host used to start T6050's physical secondary cores? The public
> Linux commit 6c03bd926 reports all 17 secondaries on J714s/26A428, but I have
> not located the successful host bootstrap. Could that path apply to
> J716c/T6050 using the 25G83 boot chain? A minimal original example or an
> explanation of the required entry context would help. Is there also a known
> raw-boot workaround? Please share no proprietary firmware or personalized
> boot objects.

This file does not authorize contacting anyone. M5 requested permission for
one Discord message; until the user answers, it stays unsent. Do not duplicate
it from M1. No private chat excerpts are part of this public handoff.

## How a supplied solution becomes a useful test

1. Pin and inspect the original host source, license, build inputs and reported
   board/firmware. Distinguish real monitor retention from an emulator that only
   implements calls for already-entered cores. Review boot, memory ownership,
   exception and return behavior before execution.
2. Build in the isolated VM. Inspect entry/relocation and topology handling;
   test original host-side logic offline. Emulation cannot prove Apple reset
   release, protection state or physical first fetch.
3. Prepare a separate reviewed, RAM-only experiment for the existing lab entry
   only if that boot route supports it. If installation or security changes are
   required, stop for the user's explicit approval. Do not overwrite the known
   working installed object or change Macintosh HD.
4. First establish one non-boot physical core's entry, identity, bounded work
   and return/park behavior. Then cover both six-core M/Performance clusters
   and the six-core P/Super cluster, binding every claimed core to physical
   identity. Do not infer physical SMP from Linux enumeration alone.
5. Only after reliable entry, validate Linux secondary initialization, timers,
   IPIs, idle state, frequency, parallel throughput and power against the macOS
   baseline. Full core enumeration alone does not establish performance parity.

Report the reviewed commit, hash-check result, substantive findings and precise
unresolved inputs in the usual M1 review record, then update progress/coordination
and push. Keep native/live tests NOT RUN. No reusing consumed receipts, firmware
replay, guessed MMIO, raw device access, repeated security check or reboot.
If no useful host input appears, the result remains **software workaround not
yet available; Apple-only necessity not proved**.
