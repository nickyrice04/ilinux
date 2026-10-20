# Stage B — attempt 27: two-stage Omarchy boot on boot042

**ATTEMPT 27 CONSUMED, 2026-10-20: one launcher invocation and one root send.**
Native two-stage switch, Omarchy, second USB/SSH link, automatic keyboard and
its single rerun PASS; human typed without extra letters but desktop latency
remains large. Human returned to Macintosh HD. No retry or settings change.
Menu after-check incomplete; deadline overrun and local collector mistake are
recorded in `native/boot/stage-b-2026-10-20-attempt27-result.md`. Do not run this
historical checklist again without a new reviewed scope and human start.

Current planning: [CPU, Wi-Fi and storage after attempt 27](../../native/boot/post-attempt27-plan-2026-10-20.md).
M5 is preparing the next CPU experiment; no new pinned package or live command
is ready. Preserve the current receipts and await the new handoff.

**Historical preboot handoff (published 2026-10-20):** M1: this is
an offline intake request until the handoff is committed/pushed, the two private
images match the records, and the human explicitly starts the attempt. Do not
restart the M5 based on a draft. Attempt 26 is consumed; its result is in
`native/boot/stage-b-2026-10-19-attempt26-result.md`.

Continue the existing installation: installed boot021 m1n1 and client pin
`57a9339ffd1876e78297b17d34dece8cff8fa1ba`, unchanged boot042 package, existing
iLinux Boot Lab entry. Keep Macintosh HD at Full Security and as the default.
No Recovery setup, installer, volume/partition, boot policy, firmware, m1n1,
network-setting or host-package changes. Storage is attempt 28, separately
reviewed. This attempt keeps NVMe disabled and supplies no storage modules;
`nr_cpus=1`, `cpufreq.off=1`, `idle=nop arm64.nowfxt` remain.

## What is being tested

Stage one (59,630,835 bytes) goes through m1n1. The M1 then sends the Omarchy root
(2,435,460,021 bytes) through the established USB SSH pipe. Stage one verifies
its exact size/hash, unpacks into RAM and soft-reboots into it, keeping the same
kernel. The USB gadget disappears during the switch and must return.

The root includes the attempt-26 fixes: repeat delay 1000 ms, cleanup of replaced
menu requests, automatic keyboard startup, a keyboard-check rerun fix, disabled
weather, and a 180-second SSH login grace period. Native keyboard loading at
startup is new timing; attempt 26 proved only the manual path. GPU, trackpad,
frequency scaling, extra cores, storage and efficiency are not enabled here.
See `native/boot/attempt27-two-stage-validation.md` for exact evidence and limits.

## Offline intake on the M1

Run from the repository root. Preserve local work; use `git pull --ff-only`
and stop on divergence. Record `git rev-parse HEAD`. Read `coordination.md`,
this checklist and the validation report. The private key remains on the M1.

1. Reverify the existing boot042 package against Git. No new release is needed:
   archive SHA-256 `a2e57c0ccddcd7c8e60affac0ffa033deb9db1639119a7aa93faaedea276a781`,
   18,877,362 bytes; SHA256SUMS digest
   `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd`.

   ```sh
   mkdir -p build/native-intake/attempt27 build/attempt27
   tools/m1n1-client/run.sh tools/m1n1-client/verify-package.py \
     build/native-boot042-download/ilinux-j716c-boot042 \
     --manifest-sha256 60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd \
     > build/native-intake/attempt27/package-receipt.json
   ```

2. The human privately transfers **both new files**. Place them at
   `build/attempt27/stage1.cpio.zst` and `build/attempt27/ramroot.cpio.zst`.
   Preserve the old images. Never put an image, test overlay, raw journal, private
   key or proprietary artifact in Git or a Release. A file with the old root's
   `565644be…` hash is not this attempt's root.

   ```sh
   python3 -I tools/m1n1-client/verify-two-stage.py \
     --stage1 build/attempt27/stage1.cpio.zst \
     --stage2 build/attempt27/ramroot.cpio.zst \
     > build/native-intake/attempt27/pair-receipt.json
   ```

   Require exit 0 and `status: PASS`. This hashes both images and reads only the
   embedded pin with `/usr/bin/tar`, extracting nothing to disk or running it.
   Expected stage one `84c01f536516b85939f6ead55e37d0a9fa4838414edb84e033aef221f6006ed3`;
   root `5eaa2fdb52dcbbaf20b4a9780f7d23e625535e3f5386f1659ed332fb7826d345`;
   embedded count 215,513, unpacked bytes in 16 KiB pages 11,012,489,216.
   The panel retains the build-time source label `candidate only`; identify
   the approved pair by the published size/hash records and verification receipt.

3. Check the unchanged launcher and sender without opening USB:

   ```sh
   python3 -I native/boot/launch.py \
     --package build/native-boot042-download/ilinux-j716c-boot042 \
     --profile ramroot --ramroot build/attempt27/stage1.cpio.zst
   python3 -I tools/m1n1-client/m5-stage2.py \
     --image build/attempt27/ramroot.cpio.zst --dry-run
   python3 -I tools/m1n1-client/test_verify_two_stage.py
   python3 -I tools/m1n1-client/test_m5_stage2.py
   python3 -I native/boot/test_ramroot.py
   ```

   Require package and RAM root PASS, OFFLINE ONLY, sender `dry run: no session
   opened`, and all tests passing (8 / 18 / 45 locally). Record skips if the M1
   lacks the old boot035/040 fixtures; their absence is not a passing test.
   Launcher SHA-256 stays
   `b14ec7a1d6957197d808609a9c4888995598e23ce4c63707db2a58476a9e0740`.
   Upload estimate is 104,310,566 bytes, 20.9 s at 5 MB/s, deadline 300 s.
   That is an estimate, not a native measurement. Do not pass `--operator-key`.

4. Reuse the M1's tested reader, `usb-pipe`, proxy and key from attempt 26.
   Recheck their recorded digests and the key's public half against
   `kernel/experiments/usb-gadget/authorized_keys`. Re-run the existing link,
   proxy and clock suites if these inputs changed. The known socket-close race
   in `test_usb_pipe` must be recorded if seen, not hidden by a passing rerun.
   Confirm the SSH entries with `ssh -G -F tools/m1n1-client/m5-ssh-config m5s`
   and `m5o`: stage one is root with its own known_hosts file, stage two is
   omarchy with a separate file. Only one SSH session at a time on interface 1.

Record sanitized offline readiness in `progress.md` and `coordination.md`, with
native boot/live checks **NOT RUN**, and stop for the human. Do not publish raw
receipts without reviewing them for identifiers. On 2026-10-20 the user declined
further routine policy checks; do not block this attempt on another check.
Last reported policies are original Full and lab Permissive; no fresh policy
verification is claimed. Keep Macintosh HD as the default; no settings changes.

## One human-started attempt

Both Macs on power; the same direct cable. Use the established fresh-M1-restart,
cable-reseat and unlocked/open-lid procedure, `caffeinate -i`, and film the M5
from before launch through return. The human shuts down the M5, holds power for
startup options and chooses the **existing** iLinux Boot Lab entry for this boot.
Do not change the default startup disk. Wait for `Running proxy...`.

Before the launch, on the M1, run the existing read-only discovery gate:

```sh
tools/m1n1-client/run.sh tools/m1n1-client/usb-check.py
```

Stop on ambiguity or a failed gate. Clear only the two lab known_hosts files
from the preceding boot (new keys are generated for both stages):

```sh
rm -f build/control/known_hosts-stage1 build/control/known_hosts-omarchy
```

Launch **once**, keeping the existing controller identity/DT checks intact:

```sh
tools/m1n1-client/run.sh native/boot/launch.py \
  --package build/native-boot042-download/ilinux-j716c-boot042 \
  --profile ramroot --ramroot build/attempt27/stage1.cpio.zst \
  --launch --device auto --confirm BOOT-J716C-RAM-ROOT
```

Record the exit, upload duration and handoff time. Do not transcribe the
m1n1 serial-number line. Require `Hardware DT PASS`; any STOP ends the attempt.

After handoff, start the established interface-0 journal reader (own terminal):

```sh
build/control/bulk-log-reader \
  --out build/native-intake/attempt27/stage1-journal.txt --wait 120 --seconds 1800
```

Stage one should show its status screen and `WAITING FOR STAGE TWO`. Check the
MTP DART probe and absence of faults in the journal, and compare the stage-one
host-key fingerprint on the panel with the journal. No storage/CPU probe.
If stage one or its link never arrives within 120 seconds, record it and stop.
Accept the ordinary accessory prompt if shown; change no accessory setting.

Then, with no other SSH session open, send the root. This command deliberately
writes its output to a file without a pipeline, preserving its exit status:

```sh
python3 -I tools/m1n1-client/m5-stage2.py \
  --image build/attempt27/ramroot.cpio.zst \
  > build/native-intake/attempt27/stage2-send.log 2>&1
printf 'sender exit %s\n' "$?"
```

Watch the file in another terminal (`tail -f`) and the panel. Require the exact
root hash to verify, then `switching`. Sender exit 0 means the switch was
requested, **not** that Omarchy or the second USB link succeeded. Compare
`ssh-keygen -l -f build/control/known_hosts-stage1` with the panel/journal key.
Record transfer bytes, seconds, rate and unpack time separately.

For this first native two-stage attempt, send once. On refusal, corruption,
unpack failure, stalled progress for 60 seconds, or no switch within 10 minutes
of starting the sender: capture the reason and end the attempt; no automatic
retry, alternate image, driver unload, fallback polling, or launcher edit.
Do not reproduce the VM's intentional failure tests on hardware.

## After the switch: desktop, link and image fixes

The reader may end when stage one's gadget disappears. Once it has exited,
start it again on interface 0 with a **new** output file:

```sh
build/control/bulk-log-reader \
  --out build/native-intake/attempt27/stage2-journal.txt --wait 120 --seconds 1800
```

The journal retains stage one's records; stage two prints its new host key.
If it keeps saying `STILL IN STAGE ONE` after a minute, record the failed switch
and stop. Allow up to 180 seconds after `switching` for desktop/link observation.
A missing second USB link is a recorded failure of that part: film any desktop
and keyboard behavior without relaunching or changing drivers.

If the link returns, run the established local proxy in a separate terminal,
then the clock helper and an `m5o` session, sequentially:

```sh
python3 -I tools/m1n1-client/connect-proxy.py --log build/native-intake/attempt27/proxy.log
# Another terminal, after the proxy is listening:
python3 -I tools/m1n1-client/m5-clock.py
ssh-keygen -l -f build/control/known_hosts-omarchy
ssh -F tools/m1n1-client/m5-ssh-config m5o
```

Compare stage two's key with its journal. In the M5 session, collect:

```sh
uname -r
cat /sys/devices/system/cpu/online
findmnt -n -o SOURCE,FSTYPE,SIZE,USED /
systemctl show -p SoftRebootsCount
cat /usr/share/ilinux/build-info.txt
systemctl --failed --no-pager
systemctl --user --failed --no-pager
systemctl status ilinux-keyboard.service --no-pager
sudo ilinux-keyboard --status
journalctl -b -u ilinux-keyboard.service --no-pager
```

Expect one CPU (`0`), `ilinux-stage2-root tmpfs`, `SoftRebootsCount=1`, build
`2026-10-20T02:57:20Z`, kernel boot042, and an active/exited successful keyboard
unit. Known unresolved VM failures are hardware provisioning, UFW and the user
document portal; record any difference, do not dismiss other errors as known.

Read the effective shell layout from that same user session:

```sh
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
OMARCHY_SHELL_IPC_TIMEOUT=20s timeout 25 omarchy-shell shell listShellConfig
```

Require valid JSON with `version: 1` and a nonempty `bar.layout`, with no
`omarchy.weather` item in any section. A timeout or empty response is inconclusive,
not evidence that weather is disabled. Keep the output local; publish the result.

If automatic keyboard startup succeeded with all four modules bound, run
`sudo ilinux-keyboard --no-typing` once to verify the rerun path. If it failed,
preserve the journal; do not manually repair it in this attempt. Ask the human
to open a terminal, type `omarchy` then Enter, and report missing/repeated keys
and visible response delay. Inspect available input devices; do not assume
trackpad support. No long key capture or sensitive typing.

After closing the interactive SSH session, the existing read-only probes can
capture the session's effective options and CPU/rendering baseline:

```sh
ssh -F tools/m1n1-client/m5-ssh-config m5o 'python3 -I -' \
  < tools/m1n1-client/m5-probes/inspect_desktop.py \
  > build/native-intake/attempt27/desktop-before.txt
ssh -F tools/m1n1-client/m5-ssh-config m5o 'python3 -I -' \
  < tools/m1n1-client/m5-probes/frame_probe.py \
  > build/native-intake/attempt27/frame.txt
```

With the human, open Super+K twice, then the root menu with Super+Space, then
close it. Repeat `inspect_desktop.py` to `desktop-after.txt` and check for
leftover `omarchy-menu-select` pollers. Record the effective repeat delay 1000,
weather configuration/request absence during the observed window, and SSH
journal behavior. Do not run the old A/B input-injection scripts, stop unrelated
processes, change render settings, install packages or start sustained benchmarks.
No frequency is claimed from requested-state fields. An agent login is possible
but signing in or changing the installation is separate from this test.

## End and report

Observe for up to ten minutes after reaching the desktop; end earlier if the
20-minute overall limit after the kernel handoff is reached. Stop on a reset, panic, fault, unexplained
loss of keyboard/link, or abnormal thermal behavior. A reset or M1 panic ends
the attempt with no relaunch. Stop this run's reader/proxy/session, then the
human returns the M5 to Macintosh HD using the established power-off/startup
options procedure. Routine post-return policy rechecks are also omitted per
the user's 2026-10-20 instruction. Record the return without inventing a fresh
policy result; no policy or default-startup changes.

Report exact Git/package/image pins, upload and transfer timings, verification
and unpack results, disappearance/re-enumeration times, desktop first frame,
automatic keyboard/rerun/typing results, repeat/menu/weather findings, failed
units, faults and return. Keep raw journals, videos, host identifiers and all
account data local in ignored `build/`. Publish only sanitized observations;
unobserved checks remain NOT RUN. This measures delivery and image behavior,
not GPU acceleration, all-core performance or macOS-level efficiency.
