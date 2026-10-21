# Revised attempt31A — reset-vector census before native SMP

Read this after `AGENTS.md` and the newest coordination entry. The old
copy-only31 pair, launcher profile and collector remain **HOLD**. This new
instruction authorizes **one read-only hardware census**, not a Linux boot,
CPU start, m1n1 replacement or automatic continuation to31B. Native31A is
**NOT RUN** until a result is published. M5 implemented and offline-tested
the guarded startup candidate and adaptive renderer policy; see
`kernel/experiments/smp31/README.md` and `validation.json`.

## Why this short step

More rendering CPUs made a large difference in the VM. We know the t6050
start-bit layout, but have not observed the current raw-boot reset target.
The old `_start` entry hypothesis is not enough to deploy an entry patch.
This census reads CPU0/CPU1 RVBAR mirrors once each, through the existing
guarded read path. It does not read PMGR hardware, scan other CPUs, touch
SPTM or program a reset vector. No new images need to be transferred.

## M1 offline intake, before restart

Preserve local work, then `git pull --ff-only`; stop on divergence. Record
HEAD. Keep installed boot021, clean client57a9339, the existing Boot Lab
entry/cable and verified boot042 package. Do not rerun an installer or use
the older hypervisor chainload. Routine policy rechecks remain waived.

From repository root:

```sh
mkdir -p build/native-intake/attempt31a
shasum -a 256 -c native/boot/attempt31/smp-source-sha256.txt
tools/m1n1-client/run.sh tools/m1n1-client/verify-package.py \
  build/native-boot042-download/ilinux-j716c-boot042 \
  --manifest-sha256 60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd \
  > build/native-intake/attempt31a/package-receipt.json
python3 -I native/boot/smp31_census.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin
python3 -I native/boot/test_smp31_census.py
python3 -I kernel/experiments/smp31/test_renderer.py
```

Require all exits0; census says `OFFLINE PASS`, no USB opened by that command.
No proxy is expected while the M5 is in macOS. Do not open an arbitrary port;
the live census performs the existing descriptor-checked USB discovery.
Review `smp31_census.py` and the validation record. Publish a sanitized
readiness note; native/live/CPU starts/Linux boot remain **NOT RUN**. Wait for
the human to restart. Do not rebuild, execute or transfer `m1n1-OFFLINE.bin`.

## One human-started census

Both Macs powered, direct cable, M1 unlocked/lid open. Follow the established
fresh-M1/reseat procedure if not already completed. Human shuts down the M5,
holds power, selects **existing iLinux Boot Lab** for this boot, and waits at
`Running proxy...`. Macintosh HD stays the default, at Full Security; no
security/volume/default-disk changes. No additional routine policy check.

Start a human-visible90s timer immediately before the command. Run once:

```sh
tools/m1n1-client/run.sh native/boot/smp31_census.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin \
  --live --device auto --confirm CENSUS-J716C-SMP-31A \
  > build/native-intake/attempt31a/census.json \
  2> build/native-intake/attempt31a/census.stderr
```

The tool imposes60s overall and5s serial-read bounds. It verifies chip, board,
all18 topology records, pinned startup/SMP text, boot CPU and no started
secondary before the two reads. Its ADT exists only in memory; parser error
output is suppressed because it can contain private properties. It emits
only CPU IDs, lock bits and image-relative target classes/offsets. A read
fault stops before any further hardware read. Do not retry, reconnect, dump
the ADT, run a shell, clear locks, or edit gates to obtain a result.

On success require `CENSUS_COMPLETE_REVIEW_REQUIRED`, `cpu_starts:0`,
`mmio_reads:2`, two rows, and Linux/SMP **NOT RUN**. Matching `vectors` rows
do **not** authorize a start or prove execution reached those vectors. A
different target is useful evidence, not a reason to patch it live. Any STOP,
fault or90s human timeout ends the attempt. Retain failed output privately.

After either outcome, tell the human to power off and select **Macintosh HD**
for the return. No shutdown register/CPU-stop command. Confirm the return.
Publish the sanitized JSON (inspect it against the schema), exact source
revision, exit/duration, target classifications and human return confirmation
in a new result under `native/boot/`. Update progress/coordination and push.
Do not publish raw console/ADT/USB paths/video, host data or Apple artifacts.

The M5 then selects the precise next entry/start fix. Native SMP, revised
Linux DT/launcher, renderer integration, stability, speed and energy remain
unvalidated; do not mark31B ready based on this census or the VM results.
