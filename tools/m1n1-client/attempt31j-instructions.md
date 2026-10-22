# M1 handoff —31J connection readiness and unchanged CPU1 campaign

31I is permanently consumed. **Native31J/CPU1/Linux SMP NOT RUN.** This release
supersedes the earlier host-only31J hold after independent offline intake.
Use the existing boot021 lab entry and retained boot042 package. No image
transfer, reinstall, volume/security/default change or routine M1 reboot.

## Complete offline intake before restarting M5

Preserve local work. `git pull --ff-only`, stopping on divergence; record the
revision. Read `research/native31j-connection.md` and
`native/boot/attempt31j/controller-review.md`. From repository root:

```sh
python3 -I tools/m1n1-client/attempt31j-offline.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin

tools/m1n1-client/run.sh native/boot/smp31j.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin
```

Both must exit0, all tests PASS, no skips or repairs. First result is
`OFFLINE_CHECKS_PASS_AWAIT_HUMAN_START`, hardware_operations0, restart_ready=false.
That flag is intentional; this phase runs no real discovery or USB operation.
Image-only intake verifies the exact image/reviewed layout; full-symbol checks
remain NOT RUN on M1 unless the reviewed symbol file is supplied. M5's VM checks
full symbols independently. Second command prints OFFLINE PASS, no `--live`.

No native31J receipts may already exist in `build/native-intake/attempt31j/`.
The separate host-only31J folder/report is expected and must be preserved.
Never delete/reset/force a receipt, including a connection-only journal. Keep
all31A–31I sources and evidence unchanged. The m1n1 client must remain clean at
57a9339; do not install/update it to fix a gate. Retain the package's prior13-file
verification; rerun its existing intake if a package file changed.

Publish sanitized readiness: revision, manifest digest/count, test method count,
symbol mode, both exit codes and unchanged earlier pins/receipts. Keep native31J,
CPU1 entry and Linux SMP NOT RUN/unverified. Then wait for the human.

## One fresh lab session

Keep M1 powered, awake/unlocked and its lid open. Use the direct known-good
cable and the ports previously used successfully; check seating before the M5
shutdown. A healthy M1 needs no restart. Do not use a hub, seize another reader,
change drivers or recover an uncertain previous target session.

After M1 publishes readiness, the human shuts down M5, holds power, selects
**the existing iLinux Boot Lab entry for this boot**, and waits at
`Running proxy...`. Do not enter Recovery or change the default startup disk.
Start an independent human-visible **90-second timer immediately before** this
single M1 command:

```sh
python3 -I tools/m1n1-client/attempt31j-supervisor.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin \
  --confirm START-CPU1-J716C-31J
```

No extra manual handshake or older USB checker precedes this command. The new
child performs discovery itself: at most4 cached queries, each capped at3s,
1s between only empty/absent outcomes,15s total. These are host registry
observations, not serial opens or CPU-start retries. Malformed metadata, a query
failure, ambiguous identity or a path failure stops immediately. No port is
opened without exact primary identity
and character-device verification; source pins are checked again before native
consumption. A persistent absence stops with a classified report.

The supervisor reserves its invocation first; `consumed:false` there describes
only that reservation and must not be read as a final native outcome. The child
creates `connection.jsonl` for host-only progress, then creates `consumed.jsonl`
only after readiness and before the single serial-open attempt. Once any serial
open is attempted, there is no enumeration retry, reconnect or fallback.
Both connection-only evidence and native receipts block rerunning this invocation.

The60s connection/native deadline includes discovery and finalization. The
independent65s child-process deadline also covers initial source/client checks,
with bounded parent termination.
Serial operations remain2s; CPU arrival3s; conditional callbacks1s. The human90s
window includes the readiness wait and covers target faults software cannot
contain. Do not extend the timer because enumeration was slow.

The CPU sequence is exactly31I: strict reset-address/lock/low-field/full-mirror
checks, same two CPU1 starts, RAM recorder, up to8 PS and8 opaque32-bit core-state
reads, conditional8 requests and park. No more cores, new start/reset/power/
security write, hook relocation or Linux continuation. The opaque state register
is still exploratory and cannot independently establish execution or reset release.

On **any result, lost proxy or timer**, immediately power off M5 and select
**Macintosh HD**. Do not wait out the timer after a result. No retry, reconnect,
cable troubleshooting, cleanup RPC, rollback, new register read or Linux command
in that session. Confirm the normal macOS desktop. Routine policy checks remain
waived. macOS, installed boot021 and settings stay intact.

## Publish the evidence after returning

Use private `supervisor-result.json`, `controller.json`, and the last complete
rows of `connection.jsonl`/`consumed.jsonl` if needed. Do not publish raw stderr,
registry data, serial paths, identifiers, Apple artifacts or arbitrary exceptions.
Publish the sanitized final JSON plus:

- `native_attempt_consumed` from the child, not inferred from parent spawn.
- Connection phase; attempted/returned import, serial, UART and construction
  flags; complete cached-query categories, counts, timing and partial prefix.
- `connection.discovery_observation` zero opens/requests apply only to cached
  discovery. They are not total hardware counts after serial opens.
- Controller phase/reason and its actual reset/PS/state/recorder/arrival evidence,
  mutation/start counters, callbacks/park, exceptions and journal/deadline flags.
  Missing CPU fields remain absent if the Controller did not produce them.
- Both exits, elapsed times, supervisor deadline, any finalization error and
  the human's Macintosh HD return confirmation/time.

If the child never emits final JSON, preserve partial journals and say which
facts are unknown. A parent `controller_started:true` means child process spawn
only. A verified primary means enumeration/lstat readiness, not CPU execution.

Success still requires both exits0, no deadline/finalization error, verified
CPU1 arrival, complete recorder,8 timer requests/counter progress and park, plus
complete PS/state and all publication/binding checks. Normal complete arrival
timeout retains66 mutation intents; success74. Intent is not acknowledgement.
No result here proves Linux SMP or performance/efficiency parity.

Write `native/boot/attempt31j-...-result.md`, update progress/coordination and push
sanitized results. Follow the outcome table in `research/native31j-connection.md`.
M5 owns the next interpretation; no automatic next boot.
