# M1 handoff — 31N consecutive CPU1 startup writes

**31M is consumed. Native 31N and Linux SMP are NOT RUN.** Run independent
M1 intake and publish readiness before the human restarts M5. Reuse installed
boot021 and retained boot042. No image transfer, installation, Recovery, volume,
security/default change, repeated policy check or routine M1 reboot is needed.

## What this test changes

31M's cache controls passed and all CPU1 entry observations remained negative.
A source audit found 127 target-interface calls and 33 journal callbacks between
its two CPU1 start stores in the complete synthetic run. That is an offline call
count, not a native timing measurement. macOS's checked PMGR code and public
m1n1 issue the two starts together, without USB observation between them.

31N sends the same two aligned 32-bit writes, value 2 to `0x280688004` followed
by `0x280688008`, through one fixed CPU0 routine. A DSB SY separates the stores;
there are no intervening host requests. This tests whether our instrumentation
changes startup behavior. The routine is not atomic, does not mask interrupts,
and provides no guaranteed hardware inter-store timing. It adds no address,
core, reset-vector write or firmware replay. CPU1's prefixes and all paired
cached/maintained observations remain unchanged.

Read `research/native31n-result-review.md`, `research/native31n-upstream.md`,
`research/native31n-firmware.md` and `native/boot/attempt31n/controller-review.md`.
Only committed expected CPU1 identity establishes prefix execution. Power state,
start acknowledgements and CPU0 controls do not. Every positive/partial/error
still stops when observed; callbacks and Linux continuation are not authorized.
The pair deliberately removes the old between-store abort opportunity: even if
CPU1 publishes after the first store, the second follows before any observation.

## Independent offline intake

Preserve local changes and every consumed receipt. Check `git status --short`,
then `git pull --ff-only`; stop on divergence and do not reset. From repo root:

```sh
python3 -I tools/m1n1-client/attempt31n-offline.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin

tools/m1n1-client/run.sh native/boot/smp31n.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin
```

Both commands must exit 0 without skips or repairs; the second prints OFFLINE
PASS. Offline `restart_ready=false` and `hardware_operations=0` describe intake,
not a live result. Exact full-symbol testing remains NOT RUN on M1 unless its
pinned symbol file is supplied. Keep client `57a9339` clean and the retained
13-file package unchanged; if a package file changed, repeat its existing check.

All six use files under `build/native-intake/attempt31n/` must be absent. Never
remove, rename or replace receipts to reuse a consumed attempt. Publish readiness
with tested commit, source digest/count, method count/skips, symbol mode, command
exits, frozen M/L/K/J/I/H/host closures and preservation of earlier receipts.
Review fixed leaf bytes, translation/publication gates, pair completion accounting
and no-retry behavior. Then wait for the human's fresh start.

## One supervised session after readiness

M1 stays powered, awake, unlocked and open, connected by the known-good direct
cable and ports. The human shuts down M5, holds power, chooses the existing
**iLinux Boot Lab** for this boot and waits for `Running proxy...`. Macintosh HD
stays the default. Start an independent **90-second timer immediately before**:

```sh
python3 -I tools/m1n1-client/attempt31n-supervisor.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin \
  --confirm START-CPU1-J716C-31N
```

No preliminary handshake, old runner, reconnect or retry. Existing single
registry discovery/open, 2-second serial, 60-second child, 65-second supervisor
and 90-second human bounds remain. Arrival/control budgets are checked around
operations, not hard per-RPC interrupts; an in-flight request may reach timeout.

The census still requires 18 cores: 12 Performance and 6 Super. Only CPU1,
sharing CPU0's active Performance cluster, is targeted. All pre-start image,
source, reset, topology, mapping, cache and CPU0 control gates remain. The new
44-byte leaf is published into the already-owned helper allocation and checked
before use. Complete freshness/stack/target checks precede its single call.

The old after-first-store sample is intentionally absent: sampling there would
reintroduce the variable being tested. Missing data is not zero. A successful
return token plus clean diagnostics acknowledges the pair; it does not prove
CPU1 executed. A failed, missing or unexpected return leaves completion uncertain:
zero, one or both stores may have happened. Preserve that uncertainty; there is
no cleanup RPC, follow-up query or retry after an uncertain pair.

On **any result, lost proxy or timer**, immediately power off M5 and return to
**Macintosh HD** before inspecting logs. Confirm the usual desktop. Do not
continue to Linux, start another core or repeat a security check.

## Publish after return

Keep raw logs, addresses/identifiers, stderr and Apple artifacts private. Publish
sanitized final controller/supervisor JSON plus a new result note covering:

- Exact release/readiness commit, source pins, consumption, connection phases,
  exceptions, deadlines, journal/finalization outcomes, exits and elapsed times.
- All CPU0 controls and new pair-leaf permission/publication results.
- Pair intent, dispatch attempted, reply/token/diagnostic status, acknowledged
  stores and possible-completion classification on failure. Preserve the
  distinction between a planned two-store operation and observed completion.
- Explicit absence of the after-first-store snapshot; after-pair and final
  power/opaque state, if actually acquired.
- Each cached/maintained channel's samples, reads, phases, committed identity
  classification, maintenance attempts/acknowledgements and partial errors.
- CPU1 starts, callbacks planned/completed (both zero), immediate human return
  confirmation/time, and CPU1/Linux SMP/performance marked only as evidenced.

Positive evidence deliberately returns STOP/exit 1 too. No automatic next step:
M5 reviews the result before any further physical experiment. Preserve receipts,
update progress/coordination and push the reviewed result.
