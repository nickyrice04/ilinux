# M1 handoff — 31E early CPU1 recorder and conditional request campaign

31D is consumed. This is a new controller/receipt namespace, using the existing
boot021 lab entry and retained boot042 package. No new image/root transfer or
installation is needed. Preserve every earlier source and receipt.

**Sequence: offline intake, publish readiness, human starts the M5 lab boot,
one supervised controller, immediate return to Macintosh HD.** Do not run the
live supervisor during offline intake. Original macOS, startup security,
volumes, installed bootloader and default startup selection stay unchanged.
Routine policy rechecks remain waived.

## Offline intake, before restarting the M5

Preserve local work. Run `git pull --ff-only`; stop on divergence and record the
commit. Read `native/boot/attempt31e/controller-review.md`,
`publication-review.md` and `controller-validation.md` in that same directory.
From repository root run:

```sh
python3 -I tools/m1n1-client/attempt31e-offline.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin
```

Expected: `OFFLINE_CHECKS_PASS_AWAIT_HUMAN_START`, all checks PASS, no skips,
`hardware_operations:0`. `restart_ready:false` deliberately means this script
cannot authorize a boot by itself. It never imports a USB client or invokes
live mode. M1's image-only mode verifies the exact image and reviewed layout;
the absent full symbol listing is explicitly NOT RUN. M5's VM separately tests
the original complete symbol listing and independently assembles the helpers.

Also run the existing local client pin check and retained package intake:

```sh
tools/m1n1-client/run.sh native/boot/smp31e.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin
```

This command has **no `--live`**, performs source/image/helper verification,
and must print its OFFLINE PASS. `run.sh` checks the existing pinned client;
do not install or update it to work around a failure. Retain the package's
previous 13-file verification evidence; if any package file changed, rerun
its existing intake before proceeding. Do not reconstruct expected digests.

Confirm that `build/native-intake/attempt31e/` contains no consumed/controller/
supervisor evidence from a real launch. Never delete, edit, force or reset an
existing receipt. Unit tests create only temporary synthetic receipts.

Publish a short sanitized readiness report: revision, manifest digest/count,
method count, symbol mode, both exit codes, and unchanged prior evidence.
Native31E, CPU1 entry and Linux SMP remain **NOT RUN**. Then wait for the human's
fresh start; do not request another policy-check loop.

## Helper health and target startup

A blanket M1 restart is no longer required. Require an awake, powered helper,
one owned reader, and no unresolved helper panic/USB fault. If those conditions
fail, stop and recover the helper before beginning a new target session. The
controller discovers the expected direct USB interface before target mutation.
Never reconnect/restart the helper to resume an uncertain target session.

Once intake passes and the human is ready: keep the M1 awake/unlocked, lid open,
with the direct cable connected. Shut down the M5, hold its power button, select
**the existing iLinux Boot Lab entry for this boot**, and wait at `Running
proxy...`. No Recovery, security-setting change, boot-object replacement, new
volume or Linux launcher is part of this attempt.

## Exactly one live run

Start an independent human-visible **90-second timer immediately before** this
command, from repository root on M1:

```sh
python3 -I tools/m1n1-client/attempt31e-supervisor.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin \
  --confirm START-CPU1-J716C-31E
```

The fixed supervisor checks pins before reserving and before spawning. The
controller persists intent before mutations. Bounds: serial read/write 2 s,
controller 60 s, supervisor 65 s plus bounded TERM/KILL handling, arrival 3 s and
1 s for each of eight conditional requests. The human timer is independent of
both computers' software. A timed-out RPC may already have executed.

What the controller does:

1. Checks exact loaded text, CPU/reset identity, RAM bounds and fresh state.
   Keeps the prior direct-USB and diagnostic-UART RAM isolation.
2. Runs 16 fixed CPU0 address-translation probes, using the observed EL1 or
   EL2/VHE regime. Requires the existing writable alias, read-only identity
   code mapping, matching physical destinations and expected memory attributes.
   It changes no mapping, HCR, protection register or boot policy.
3. Writes the original 204-byte recorder into fixed unused **loaded RAM**,
   cleans the write alias to PoC and invalidates the identity instruction view.
   Publishes its 4-byte hook last; verifies both views and the whole immutable
   text with only those two allowed deltas. A denied write or mismatch stops.
4. Issues the same two fixed 32-bit CPU1 startup writes using a guard-free
   helper so early CPU1 faults are not hidden by a temporary global guard.
   No extra core, guessed power write, stop/reset command or retry exists.
5. Samples the early record and reset/spin publication. Only confirmed arrival
   plus a complete recorder permits eight timer callbacks, counter-progress
   checks and a final park check. Unexpected entry before the second write is
   recorded, then stops without that second write. No Linux continuation.

On **any result**, lost proxy, deadline or human timer: power off the M5 and
select **Macintosh HD**. Return immediately after a result; do not wait for the
full timer. No cleanup RPC, restoring code, freeing the stack, reconnecting,
rerunning, adding a power operation or trying another controller. RAM patches
and allocations persist until power-off; the installed boot object is unchanged.
Confirm the normal macOS desktop has returned.

## Report results without another boot

Use `supervisor-result.json`, `controller.json` and, only if needed, the last
complete JSON line in private `consumed.jsonl`. Keep raw receipts/stderr/console,
USB paths, target memory, identifiers and Apple artifacts private under build.
Publish only the schema-reviewed sanitized result and an original summary.

A complete success requires supervisor/controller exit 0, no deadline,
`CPU1_ENTRY_AND_REQUESTS_PASS`, phase complete, both start writes acknowledged,
arrival verified, complete recorder, eight completed requests, progressing
counter, final park verified, all RAM/permission/publication checks PASS.
The successful path has **80 mutation requests**; an ordinary arrival timeout
after complete publication/two starts has 72. Other refusals may stop earlier.
Counts are intentions; use acknowledgments and final state separately.

For STOP, retain phase/reason, permission booleans, body/hook/text-publication
results, attempted/acknowledged starts, early recorder summary (including
partial-read/error information), reset/spin classification, exception/guard
booleans and any completed requests. Do not infer a current PC from the phase.
A zero record cannot distinguish no execution, a fault before publication, or
invisible writes. A complete recorder is not arrival or proof the final
barrier/replay completed. A permission refusal identifies a different next
step; never loosen security or remap memory to continue.

Round-trip times include USB, host scheduling, Python and journal overhead;
they are diagnostic distributions, **not CPU latency or performance benchmarks**.
No result here proves Linux SMP, cache coherence under load, timer interrupts,
IPI correctness, stability, full-core utilization, or efficiency parity.

Record exact commit, time boundaries and human macOS-return confirmation in a
new `native/boot/attempt31e-...-result.md`; update progress/coordination and push.
If software was killed before a final JSON, retain unknowns explicitly. M5 then
uses the early phase/EL/cache observations to choose the next original change.
Success advances to a reviewed two-core Linux correctness/renderer/memory batch;
no such continuation is authorized by this controller.
