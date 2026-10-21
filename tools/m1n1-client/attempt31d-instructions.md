# Attempt 31D — one CPU1 entry and request test, then Macintosh HD

**M5 offline preparation PASS; M1 intake pending; native 31D NOT RUN.**
This tests the diagnostic-console stall hypothesis after 31C's arrival timeout.
The M1 verifies offline and waits for the human to authorize the new live start.
Read the newest `AGENTS.md` and `coordination.md` first. This replaces the
previous 31C handoff. 31A, 31B and 31C are consumed; preserve all receipts.
Never reset an old receipt or rerun its commands. The old copy-only 31, Linux
launcher and full-image SMP candidate remain held.

## Why 31D

31C passed the RAM gate and acknowledged both CPU1 starts, but no arrival flag
was observed. Pinned public bootloader code can wait indefinitely for a
transmitter during diagnostic output before publishing that flag. 31D tests
this hypothesis by zeroing two UART **RAM base variables** and publishing them
to PoC before start. Its USB proxy must be active; USB/framebuffer settings
stay unchanged. Both UART outputs are muted until power-off, reducing that
fallback diagnostic output. It adds partial reset/spin identity observations,
so a timeout retains more information. No UART MMIO probe or flush is added.

Read `native/boot/attempt31d/review.md` and the linked REA findings. This is a
candidate experiment, not a diagnosed native fix or faster desktop boot.

## Scope and expected outcome

Use the **existing installed boot021** in the existing iLinux Boot Lab entry.
No new image, chainload, install, boot/security/default-disk/volume change.
Keep Macintosh HD intact, at its last-reported Full Security and as default;
routine policy rechecks remain waived.

The controller verifies this exact t6050/J716c/18-core layout, installed code
and fresh SMP state. It allocates 16 KiB of temporary RAM and uploads a 192-byte
original helper. It sets WFE parking, prepares CPU1's dedicated stack, and
zeros/publishes the two diagnostic-UART RAM bases, then issues the same two
32-bit CPU1 start writes. It then verifies CPU1 identity/entry and
two completed read-only timer requests through the installed parked loop.
The helper runs on CPU0; CPU1 uses installed boot021 code. No reset-vector or
installed-code write, frequency change, other-core start, Linux launch or
generic CPU stop. Existing secondary initialization does write architectural
CPU state; this experiment is **not read-only hardware**.

Expected result: `CPU1_ENTRY_AND_REQUESTS_PASS`. A success establishes a bounded
bootloader entry/request path; Linux SMP, timer IRQs/IPIs, cache coherence,
performance, energy and macOS parity remain NOT RUN/unproven. Failure is useful
evidence and is never permission to retry, reconnect or change a gate.

## Offline intake before either Mac restarts

Preserve local work and `git pull --ff-only`; stop on divergence. Record HEAD.
No parallel proxy/USB readers, Linux boot, REA experiment or SMP controller.
Use the clean pinned client `57a9339ffd1876e78297b17d34dece8cff8fa1ba` and the
retained verified boot042 package. No root/stage-one files need AirDrop.

From repository root:

```sh
mkdir -p build/native-intake/attempt31d
shasum -a 256 -c native/boot/attempt31d/source-sha256.txt
tools/m1n1-client/run.sh tools/m1n1-client/verify-package.py \
  build/native-boot042-download/ilinux-j716c-boot042 \
  --manifest-sha256 60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd \
  > build/native-intake/attempt31d/package-receipt.json
python3 -I native/boot/smp31d.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin
python3 -I native/boot/test_smp31d.py
python3 -I native/boot/test_smp31c.py
python3 -I native/boot/test_smp31b.py
python3 -I tools/m1n1-client/test_attempt31b_supervise.py
python3 -I tools/m1n1-client/test_attempt31d_supervise.py
python3 -I tools/m1n1-client/test_attempt31c_supervise.py
python3 -I native/boot/test_smp31_census.py
python3 -I kernel/experiments/smp31/test_audit_boot021.py
python3 -I kernel/experiments/smp31/test_renderer.py
```

Require all **60 source pins**, all exits 0 and **73 Python test methods PASS**
(10 new controller + 3 new supervisor + 60 prior); no skips,
repairs or guessed pins. The default controller must say `OFFLINE PASS` and
must not open USB, reserve the real attempt, allocate target RAM or start CPUs.
The supervisor tests create/terminate only their own dummy child processes.
Read `native/boot/attempt31d/review.md` and review the controller/supervisor.
The 31B/31C manifests pin historical handoff pointers. Use the 31D manifest
and offline CLI; do not regenerate old manifests. Both shared controller
sources remain byte-identical. This is a new receipt namespace, not a retry
of the consumed command. No root/stage-one file transfer is required.

Check that none of these live-use files exists in `build/native-intake/attempt31d/`:
`supervisor-once.json`, `consumed.jsonl`, `controller.json`, `controller.stderr`,
`supervisor-result.json`. Do not delete a pre-existing file to make intake pass.
Such a file means stop and report it for review, even if an earlier connection
failed. No `--force`/receipt reset exists.

Publish a sanitized M1 offline readiness report with exact revision, package
and source-pin results, method counts and no fixes/skips. Native/live, hardware
writes and CPU1 starts remain **NOT RUN**. Then wait for the human's start.
Do not execute the supervisor during intake; it is the live command.

## One live run

Follow the established fresh-M1/reseat procedure if not already done. Both
Macs powered, M1 unlocked/lid open, direct cable. Stop other owned readers.
The human shuts down the M5, holds power and selects the **existing iLinux Boot
Lab** for this boot, then waits at `Running proxy...`. No Recovery or settings
change. Do not replace the installed bootloader.

Start the human-visible **90-second timer immediately before** the following
command. Run it **once**, from repository root:

```sh
python3 -I tools/m1n1-client/attempt31d-supervise.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin \
  --confirm START-CPU1-J716C-31D
```

Bounds: 2s serial read/write, 60s controller alarm, independent 65s parent
deadline with termination then kill, 3s arrival and 1s per request. The parent
cannot recover a frozen target, so the human timer remains independent.
Controller intents are fsynced before mutations. Interrupted dispatch means
unknown completion, not zero writes. Allocated RAM/CPU1 stack stay reserved
until power-off; no rollback, retry, extra-core command or target cleanup.

Immediately on PASS, STOP, lost proxy, deadline or human timer, instruct the
human to power off the M5 and select **Macintosh HD**. Do not wait out the
timer after a completed result. Do not boot Linux in this session, even on
success. Confirm the usual macOS desktop has returned. This is the already
authorized return path; no repeated policy-check request is needed.

## Report for M5

Read the supervisor result and controller JSON. For a success require:

* supervisor exit 0, deadline false;
* `result:CPU1_ENTRY_AND_REQUESTS_PASS`, `phase:complete`;
* start writes attempted 2, acknowledged 2; `cpu1_arrival_verified:true`;
* requests completed 2 and counter progress true; mutation requests 15;
* diagnostic_uart_check: direct_usb_proxy true, bases_expected_or_zero true,
  enabled_count 1 or 2, ram_zeroes_published true;
* entry_observation arrival_flag_seen; arrival_samples greater than zero;
* every `ram_check` boolean true and `bootargs_revision` 2 or 3;
* `linux_boot:NOT RUN` and `native_linux_smp:NOT RUN`.

Controller durations include USB/software overhead; they are not core-start
latency benchmarks. Do not describe a successful bootloader test as two-core
Linux, sustained stability, timer-IRQ/IPI correctness or energy parity.

For STOP, preserve `ram_check`, `diagnostic_uart_check`, `entry_observation`,
`arrival_samples`, phase, fixed reason, attempted versus acknowledged writes
and partial arrival/request evidence. A clean arrival timeout after both
starts has 13 mutation requests. Other stops may occur earlier. Partial
stages are sequential RAM samples, not an atomic snapshot or CPU program counter.
Do not discard them or treat no_reset_record_seen as proof of no execution.
The current code retains the exception counter after helper readiness and avoids ordinary bulk reads after
start. A timeout alone does not locate the fault or prove CPU1 never entered.
An abrupt supervisor termination may leave only the durable local receipt;
report unknowns explicitly, without rerunning anything.

Publish a new sanitized result under `native/boot/`, the exact schema-reviewed
controller/supervisor JSON when available, revision, timing boundaries and
human return confirmation. Update progress/coordination and push. Keep raw
receipts, stderr, console/video, USB paths, addresses, ADT and all personal or
Apple artifacts private under ignored build. Do not paste the whole receipt
into a public report. If the machine cannot return normally, stop and report;
do not improvise boot/security/firmware changes.

Next, M5 reviews entry evidence before preparing the two-core Linux DT/launcher
and renderer comparison. No automatic continuation is included in 31D.

If no arrival, the M5 reviews the new stage evidence before any next command.
Do not add a UART flush, longer arrival bound, power-register read/write,
reset-vector edit, another core, diagnostic reconnect or new image on the spot.
