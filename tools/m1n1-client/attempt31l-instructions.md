# M1 handoff —31L Normal-memory CPU1 entry experiment

**31K is consumed. Native31L/CPU1/Linux SMP remain NOT RUN or unverified.**
The M5 offline release must pass the companion validation record, and M1 must
publish independent intake before the human restarts M5. Use the existing
boot021 lab entry and retained boot042 package. No image transfer, reinstall,
volume/security/default change, repeated policy check or routine M1 reboot.

## What this tests

Both31K Device-memory records were negative despite the CPU0 control passing.
31L adds an original Normal-memory prefix before each existing recorder. A
committed CPU1 identity would establish execution and visibility through this
new channel. It would not prove the subsequent Device recorder ran, reset
provenance, or that a cache issue caused the earlier failures. Both records
zero remains inconclusive. This is a diagnostic attempt, not a CPU-speed fix.

Read `research/native31l-first-fetch.md`,
`research/native31l-platform-prepare.md`, and
`native/boot/attempt31l/controller-review.md`. Raw Apple artifacts stay private;
no firmware cleanup sequence is copied or replayed.

## M1 offline intake

Preserve local work. Run `git status --short`, then `git pull --ff-only`; stop
on divergence and report it rather than resetting. From the repository root:

```sh
python3 -I tools/m1n1-client/attempt31l-offline.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin

tools/m1n1-client/run.sh native/boot/smp31l.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin
```

Both must exit0 without skips or repairs. First reports
`OFFLINE_CHECKS_PASS_AWAIT_HUMAN_START`, hardware_operations0 and
restart_ready=false: this phase performs no real discovery or USB action.
Second prints OFFLINE PASS; do not add `--live`. Full-symbol checks remain
NOT RUN on M1 unless the exact pinned symbol file is supplied. M5's full-symbol
VM result is separate. Keep the client clean at57a9339 and all earlier source
pins/receipts intact. Keep the existing13-file package verification; if a
package file changed, repeat its existing intake. Do not update/install the
client to bypass a refusal.

No31L use files may exist in `build/native-intake/attempt31l/`. Never clear,
rename or force consumed receipts, including connection-only ones. Publish
sanitized readiness with commit, manifest digest/count, methods/skips, symbol
mode, both exits, frozen-pin status and prior receipts preserved. M1 should
also review the Normal-record/stop semantics; report concerns before any boot.
Then wait for the human's fresh start.

## One supervised lab session after M1 readiness

Leave M1 awake/unlocked, lid open, direct known-good cable/ports. No routine M1
restart. The human shuts down M5, holds power, selects the **existing iLinux
Boot Lab** for this boot and waits for `Running proxy...`. Do not enter Recovery
or change the default startup disk. Start an independent **90-second timer
immediately before** this one command on M1:

```sh
python3 -I tools/m1n1-client/attempt31l-supervisor.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin \
  --confirm START-CPU1-J716C-31L
```

No preliminary manual USB handshake or old checker. Discovery uses the existing
bounded cached-registry checks and exact primary identity before one serial-open
attempt. No reconnect, fallback or target retry follows. The supervisor reserves
its invocation; connection progress is recorded separately; the child reserves
native consumption before the serial attempt. Parent spawn alone is not proof
of native consumption. Any use file blocks reuse of this invocation.

The existing60-second child,65-second supervisor,2-second serial and3-second
arrival bounds remain; the human90-second timer covers failure software cannot
contain. Two CPU0 controls each have2-second local bounds. Do not extend any
window. No callbacks are authorized in31L, even on complete Device-only arrival.

The hardware census still validates18 cores:12 Performance (ADT M) and6 Super
(ADT P). Only CPU1, in CPU0's active Performance cluster, is targeted. The same
two CPU1 start stores and strict reset mirror checks remain. No new MMIO,
reset destination, system-register write or mapping change is introduced.

The existing16KiB helper allocation owns separate64-byte Normal records on
128-byte boundaries and a separate CPU0 control. Initialization/cache publication
happens only before starts. CPU0 Normal translation/permissions, control,
known-zero freshness, instruction readback and whole text must pass first.
Two60-byte prefixes write a phase before MRS, then commit low24 MPIDR before
branching to the retained Device recorders. All effects are in loaded RAM.

Any Normal publication, including partial/uncommitted identity, stops. A
committed expected CPU1 identity is useful positive evidence; it is not a
verified park, Linux arrival or Device comparison. Every observation error
stops with partial counts. The inherited cold tripwire remains a terminal spin,
externally bounded by the human return, never a verified architectural park.

On **any result, lost proxy or timer**, immediately power off M5 and choose
**Macintosh HD**. Do not wait out the timer after a result. No extra reads,
cleanup, retry, reconnect, Linux command or cable troubleshooting in-session.
Confirm the normal macOS desktop. Original macOS/installed image/settings stay
intact; no repeated policy check is requested.

## Results to publish after return

Use private final controller/supervisor JSON and durable journals as needed.
Publish sanitized final JSON plus a new `native/boot/attempt31l-...-result.md`.
Never publish raw stderr, registry data, serial paths, identifiers or Apple
artifacts. Include:

- Actual consumption, connection phases/counts, attempted/returned transport
  flags, deadline/journal/finalization errors and both exits/timings.
- Source manifest and all preflight/reset/topology/publication gates.
- `cpu0_normal_control`, `normal_permissions`, `normal_publication`,
  `normal_observation`, `normal_reads`, `cpu1_prefix_identity_observed`, plus
  inherited Device control/cold/vector/power/state observations and counters.
- For each Normal channel: acquired reads/samples, highest phase,
  any_record_seen, identity_status and error. Raw identity values are private.
  Partial phase/identity is not CPU1 proof. Missing samples remain missing.
- Starts attempted/acknowledged and mutation intents; requests_completed must
  be0. Every expected positive is deliberately a STOP (exit1), not a failed
  test merely because the controller did not return a success code.
- Human Macintosh HD return confirmation/time. Keep Linux SMP and performance
  parity unverified. A first positive does not compare Device visibility.

A natural timeout or observation deadline consumes the session too. Preserve
partial reports when final JSON is absent, state unknowns explicitly, update
progress/coordination and push. M5 interprets the evidence before any next boot.
