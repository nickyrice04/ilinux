# M1 handoff — 31O offline review; do not restart M5

**31N is consumed. 31O native work is HOLD / NOT RUN.** This handoff releases
offline tools only. It has no supervisor, live controller, USB discovery or
target command. Keep M5 in Macintosh HD. No M1 reboot, image transfer, Recovery,
installation, volume/security/default change or repeated policy check is needed.
Preserve every previous receipt; never rerun 31N or clear its use files.

## Why the direction changed

31N's single CPU0 routine completed both reviewed start stores, but no CPU1
entry record committed identity. The tested host-delay variant did not resolve
the failure. Gravity Linux explicitly reports M5 Pro/Max platform configuration
problems preventing secondary-core startup, and other T6050 experiments report
similar failures. These strengthen a firmware-prerequisite investigation; they
do not establish our exact cause or prove a software fix impossible.

Matching-firmware REA found conditional command/restore structure, not a safe
list of missing writes. Two new original tools parse that structure and classify
the consumed reports offline. No firmware replay or further marker-only reboot
is warranted by the current findings. Read:

- `research/native31o-upstream.md`
- `research/native31o-controller-audit.md`
- `research/native31o-firmware.md`
- `kernel/experiments/smp31o-evidence/README.md`

## Independent offline review

Preserve local changes and receipts. Check `git status --short`, then
`git pull --ff-only`; stop on divergence instead of resetting. From repo root:

```sh
python3 -I tools/m1n1-client/attempt31o-offline.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin
```

This uses standard-library Python and repository sources; no m1n1 client import
or connection occurs. Expected exit 0 and result
`OFFLINE_REVIEW_PASS_NATIVE_HOLD`, with `restart_ready=false` and
`hardware_operations=0`. Both consumed reports must retain unverified CPU1
execution. Test counts and source digest are in the output and final validation
record. Do not skip or repair a failed check.

Without `--symbols`, full-symbol validation is NOT RUN. Without the optional
private `--ibootdata`, actual firmware parsing is NOT RUN on M1; the synthetic
decoder tests still run. Do not download, transfer or publish Apple firmware
merely to fill that optional field. M5's matching-payload validation remains
separate evidence. Existing boot021 and the retained 13-file package are unchanged.

## Publish an offline review, then wait

Record the tested commit, pins/digest, test counts, command exit, both report
classifications, symbol mode, optional-input status and any refusal. Mark new
discovery/device opens/target requests/native invocations as zero. Preserve all
old receipts and source closures. Publish only reviewed metadata and original
notes in a new offline result document plus progress/coordination updates.

Do not label this result readiness to boot: **native 31O remains HOLD**. M5 owns
the next firmware-prerequisite investigation. A future physical handoff must
identify a specific new condition and predicted distinguishing result, state
every operation, and pass its own offline review. It will use a fresh attempt
identity; no automatic follow-up or reuse of a consumed runner follows here.
