# 31L: offline entry review; no restart or native runner released

2026-10-22. Supersedes earlier pre-execution instructions for the next action.
**31K is consumed. Physical31L is HOLD / NOT RUN. Keep M5 in macOS.**

## Why this handoff is offline

The31K CPU0 reporting control passed, but both CPU1 recorders remained at phase
zero. Their common incoming-memory assumptions mean that another similar marker
run could produce the same result without locating the failure. We have not
identified a justified CPU-start correction. The new checker tests exact entry
address calculations and interpretation limits without opening a target.

Read [the result review](../../research/native31k-result-review.md),
[fresh REA findings](../../research/native31l-entry.md) and
[checker documentation](../../kernel/experiments/smp31l-analysis/README.md).
Keep all consumed receipts and frozen31K/J/I inputs intact.

## M1 work available now

From your existing checkout, inspect local changes before fast-forwarding:

```sh
git status --short
git pull --ff-only
```

If there are local changes or divergence, preserve them and report the conflict;
do not reset the tree. Read this file again after updating.

Use the already verified boot021 `m1n1.bin` in the retained package. Substitute
its existing local path below; no image transfer or replacement is needed.
Run with the existing Python interpreter from the repository root:

```sh
python3 -I kernel/experiments/smp31l-analysis/test_entry_contract.py \
  --image /EXISTING/BOOT021/m1n1.bin \
  --report native/boot/attempt31k-controller-2026-10-22.json

python3 -I kernel/experiments/smp31l-analysis/entry_contract.py \
  --image /EXISTING/BOOT021/m1n1.bin \
  --report native/boot/attempt31k-controller-2026-10-22.json
```

Expected: test success with no skipped image/report checks, and
`OFFLINE_ENTRY_CONTRACT_PASS`, `symbol_mode: reviewed_layout_only`,
`native_next_attempt_ready: false`, `cpu1_effective_entry: UNKNOWN`,
`hardware_emulator: false`. The numerical address/translation case counts are
software scenarios, not measured hardware states. Full-symbol validation is a
separate M5 result unless the exact pinned symbols are already available on M1.

Both commands read local artifacts and run original stdlib analysis. They do
not enumerate USB, import the proxy client, open a serial port, issue hardware
requests, mutate an image, or consume a native attempt. The checker is not an
installer or a live launcher.

Report the checked Git commit, image digest, test count/skips, tool version and
checker result. Keep local absolute paths and raw diagnostic data out of public
notes. Retain `native31L / CPU1 execution / Linux SMP: NOT RUN or unverified`.
If asked to publish the result, use a new dated offline review file and update
current status without editing historical consumed reports.

## Release gate for a future physical31L

M5 must first provide a separately reviewed controller and exact instruction
pins that test a new distinction supported by firmware or public-source
evidence. That handoff must state target operations, identity/translation
conditions, expected outcomes, time bounds and the return procedure.

**There is no live command in this handoff.** Do not run31K again, clear receipts,
start a proxy session, restart either Mac, or infer native readiness from an
offline PASS. No repeated boot-policy check is requested. No installed image,
security setting, volume, raw device or original macOS change is part of this
work.
