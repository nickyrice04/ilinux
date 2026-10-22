# M1 handoff —31H reset-format and opaque core-state campaign

31G is consumed; **native31H NOT RUN**. Use existing boot021 lab entry and
retained boot042 package. No new image, AirDrop, install, volume, startup-policy
change, routine policy check or routine M1 reboot is needed.

Order: **offline intake → publish readiness → human starts existing M5 lab →
one supervised run → immediate Macintosh HD return**. Earlier README/stage-B
files remain frozen inputs to consumed attempts; follow this handoff and current
coordination.md. Keep all prior receipts intact.

## Offline intake before the M5 restart

Preserve local work; run `git pull --ff-only`, stopping on divergence. Record
revision. Read `research/native31h-reset-entry.md`,
`native/boot/attempt31h-plan.md` and `native/boot/attempt31h/controller-review.md`.
From repository root:

```sh
python3 -I tools/m1n1-client/attempt31h-offline.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin

tools/m1n1-client/run.sh native/boot/smp31h.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin
```

Both must exit0, all tests PASS, no skips. First result:
`OFFLINE_CHECKS_PASS_AWAIT_HUMAN_START`, `hardware_operations:0`,
`restart_ready:false`. That flag is intentional: an offline test cannot start
hardware. Image-only intake verifies exact boot021 and reviewed layout; complete
symbol checks are explicitly NOT RUN on M1 without that file. M5 VM separately
checks the exact symbol digest. Second command prints OFFLINE PASS. No `--live`
or supervisor command belongs in this phase. Do not install/update the client
to work around failure; it must remain clean at pin57a9339.

Confirm no real31H receipts exist in `build/native-intake/attempt31h/`. Never
remove/reset/force a consumed receipt. Retain the package's prior13-file intake;
rerun its existing intake if a package file changed, without inventing hashes.
Publish sanitized readiness: revision, manifest digest/count, method count,
symbol mode, both exit codes and unchanged prior evidence. Keep native31H,
CPU1 entry and Linux SMP marked NOT RUN/unverified. Wait for the human.

## M5 startup and one live command

Require an awake powered M1, direct cable and one owned reader, with no
unresolved helper panic/USB fault. A healthy M1 needs no restart. Do not recover
or reconnect a helper to resume an uncertain target session.

After intake passes: keep M1 awake/unlocked with its lid open. The human shuts
down M5, holds power, selects **the existing iLinux Boot Lab entry for this
boot**, and waits at `Running proxy...`. Do not enter Recovery or change the
default startup selection. Start an independent human-visible **90-second timer
immediately before** the following single command on M1:

```sh
python3 -I tools/m1n1-client/attempt31h-supervisor.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin \
  --confirm START-CPU1-J716C-31H
```

The supervisor binds all reviewed sources before reservation and again before
spawn. Controller/receipt names are distinct from31G. Bounds remain60 seconds
controller,65 seconds supervisor plus bounded child termination,2 seconds per
serial read/write,3 seconds arrival and1 second per conditional callback. Added
core-state pairs have a one-second soft deadline; the independent human timer
covers target hangs/asynchronous faults that software cannot contain.

31H preserves the same two CPU1 start writes, RAM-only vector recorder and all
arrival gates. It retains the two existing reset-mirror reads more precisely;
unexplained fields/mirror disagreement stop before mutations. Then it combines
four PS pairs with at most8 exploratory32-bit core-state reads at fixed
CPU0/CPU1 addresses. The baseline is guarded before CPU1 start; subsequent
reads use the existing guard-free helper. No PS, RVBAR, stop or protection write
is added. No cold-entry hook or another core is enabled.

The added register's t6050 meaning and never-started-core accessibility are
unverified. Zero/nonzero/change or equality with CPU0 is **not** execution,
reset release or PC evidence. Follow the outcome table; do not improvise.

On **any result**, lost proxy or timer: immediately power off M5 and select
**Macintosh HD**. Do not wait out the timer after a result. No retry, reconnect,
cleanup RPC, rollback, stack free, new register read or Linux boot command.
The RAM experiment ends by power-off; installed boot021 and macOS stay intact.
Confirm the normal macOS desktop returned. No repetitive policy-check loop.

## Report without another boot

Use private `supervisor-result.json`, `controller.json`, and only if needed the
last complete `consumed.jsonl` line. Publish a sanitized summary and reviewed
JSON, never raw console/stderr, USB paths, full register words, identifiers or
Apple artifacts. The new reviewed fields are:

- `rvbar_observation`: bounded legacy/firmware field relations, bit classes,
  mirror equality, partial-read counts/error; exact/effective entry UNKNOWN.
- `reset_format_gate_passed`, `cpu_state_permissions` booleans.
- `cpu_state_observation`: four ordered pairs, low bytes0–255, change/equality
  fields, attempted/completed counts, partial/error/journal flags. All execution,
  running-state, reset and PC conclusions remain unestablished.

Also retain phase/reason, PS field pairs, recorder/reset/spin evidence, RAM and
publication checks, attempted/acknowledged starts, exceptions/guard flags,
completed requests, terminal error, timing and human return confirmation.
Ordinary complete publication/arrival timeout has66 mutation intentions; success
has74. Partial refusals may stop earlier. Intent is not acknowledgement.

Success still requires both exits0/no deadline, `CPU1_ENTRY_AND_REQUESTS_PASS`,
complete recorder, verified CPU1 arrival,8 requests, counter progress, verified
park, complete PS/state observations and all binding/publication checks PASS.
No result here establishes Linux SMP, macOS performance or efficiency parity.
Round-trip timings include USB/Python/journaling overhead; they are not CPU
benchmarks. A failed final observation after natural arrival timeout is retained
separately from the original arrival-timeout reason. Any other fault gets no
additional terminal sampling.

Write `native/boot/attempt31h-...-result.md`, update progress.md/coordination.md
and push sanitized results. M5 selects the next implementation from combined
firmware-format, power, opaque-state and entry evidence. No automatic next boot.
