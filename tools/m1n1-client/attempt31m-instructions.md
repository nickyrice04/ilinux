# M1 handoff —31M paired CPU1 entry observation

**31L is consumed. Native31M and Linux SMP have not run.** Review the M5
validation record and publish independent M1 readiness before the human restarts
M5. Reuse installed boot021 and retained boot042. No image transfer, reinstall,
Recovery, volume/security/default change, repeated policy check or M1 reboot.

## Why this attempt differs

31L's CPU0 controls passed, but CPU1 produced no visible Normal or Device marker.
31M corrects one observation limitation: cached CPU0 zeros could hide a
noncoherent secondary store. It samples each existing Normal record, then only
if all sampled fields are zero performs bounded clean-and-invalidate and samples
again. These are CPU0-issued operations with potentially wider shareable-cache
effects. No CPU1 cache instruction or new MMIO/start/reset operation is added.

A committed expected identity proves CPU1 prefix execution. A positive after
maintenance alone cannot prove cache causality because CPU1 may write between
samples. All-zero still cannot exclude execution. This is an entry diagnostic,
not an all-core or desktop-speed fix. Read `research/native31m-result-review.md`,
`research/native31m-firmware.md` and `native/boot/attempt31m/controller-review.md`.

## Independent offline intake

Preserve local changes and all consumed receipts. Run `git status --short`, then
`git pull --ff-only`; stop on divergence, do not reset. From the repo root:

```sh
python3 -I tools/m1n1-client/attempt31m-offline.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin

tools/m1n1-client/run.sh native/boot/smp31m.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin
```

Both must exit0 without skips or repairs; second must print OFFLINE PASS.
The intake's restart_ready=false/hardware_operations0 describes offline intake;
it performs no discovery or USB access. Full symbols remain NOT RUN on M1 unless
the exact pinned symbol file is supplied. Preserve clean client57a9339,
boot021 hashff75f4a9…2072664, the retained13-file package and all frozen sources.
If a package file changed, repeat its existing verification. Do not update the
client to bypass a refusal.

All six use files under `build/native-intake/attempt31m/` must be absent.
Never clear or rename receipts to rerun a consumed attempt. Publish sanitized
readiness: tested commit, source manifest digest/count, methods/skips, symbol
mode, both exits, frozen31L/K/J/I/host closure status and prior receipts preserved.
Review cache geometry, ownership, controls and stop semantics. Report a concern
before boot; otherwise wait for the human's fresh start.

## One supervised session after readiness

Keep M1 awake/unlocked, lid open, powered and connected by the known-good direct
cable/ports. The human shuts down M5, holds power, selects the existing **iLinux
Boot Lab** for this boot, and waits for `Running proxy...`. Keep Macintosh HD as
default. Start an independent **90-second timer immediately before** this command:

```sh
python3 -I tools/m1n1-client/attempt31m-supervisor.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin \
  --confirm START-CPU1-J716C-31M
```

Do not precede it with a handshake or an old runner. There is one discovery and
one serial-open attempt, with no fallback/reconnect/retry. Supervisor reservation
and child native consumption are distinct; preserve all use files on either.
Existing60-second child,65-second supervisor,2-second serial,3-second arrival and
90-second human bounds remain. Each CPU0 control has its own2-second bound.
No callbacks are authorized, including on Device-only arrival.

The runtime census still requires18 cores:12 Performance (ADT M),6 Super (ADT P).
Only CPU1 in CPU0's active Performance cluster is targeted, using the same two
start stores. The exact reset mirror, loaded image and source checks remain.

Before starts, a small returning CPU0 leaf reads CTR_EL0. Unsupported/unknown
geometry refuses rather than guessing. The issuing CPU must be verified EL2
with the expected VHE regime. Complete128-byte owned granules, matching Normal
translations and no CPU0 record stores after initialization are required. A
separate CPU0 maintenance control must preserve canaries and restore its marker.
That control is not evidence about CPU1. Existing CPU0 Device/Normal controls,
CPU1 prefixes and their body/hook/whole-text checks remain.

Only an all-zero cached triad permits maintenance of its fixed owned record.
Any partial/positive observation or failure stops. No maintenance of Device RAM,
code, MMIO or arbitrary addresses is allowed after starts. No whole-cache,
invalidate-only, idle, debug, security-register or firmware operation is added.
The cold path retains its terminal spin, not a verified architectural park.

On **any result, lost proxy or timer**, immediately power off M5 and choose
**Macintosh HD**. Do not wait out the timer after a result or inspect logs first.
No further target reads, cleanup, reconnect, retry or Linux continuation.
Confirm the usual macOS desktop; no repeated policy check is requested.

## Publish after return

Keep raw journals, stderr, registry/serial identifiers and Apple artifacts private.
Publish sanitized final controller/supervisor JSON and a new native result note:

- Commit, source pins, actual consumption, connection phases, exceptions,
  deadlines, journals, finalization, exits and elapsed times.
- CPU0 cache qualification fields; cache permissions/publication; separate
  Device/Normal/maintenance controls, their attempts, acknowledgements and errors.
- Each `paired_observation`: cached/maintained snapshot status, phase, committed
  identity classification, channel, read counts and maintenance intent/attempt/
  acknowledgment counts. Missing maintained samples are missing, not zeros.
  Keep raw identity/address values private. Preserve partial fault evidence.
- Inherited Device/cold/power/opaque-state observations; starts attempted and
  acknowledged; total mutation intents. Planned/completed callbacks must be0.
- Human return confirmation/time; Linux SMP, performance and efficiency remain
  unverified. Positive evidence deliberately returns STOP/exit1 too.

Maintain the distinction between a CPU0 qualification refusal, a negative bounded
observation and an unexpected transport failure. Preserve all receipts, update
progress/coordination and push the reviewed report. M5 interprets it before any
new experiment; no automatic follow-up session.

Timing limit: the3-second arrival budget is checked around observation batches,
not a hard per-RPC interrupt. Local control budgets are checked before/after
operations; an in-flight request can reach its serial timeout. The independent
supervisor and human return bounds remain necessary.
