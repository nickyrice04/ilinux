# Stage B — attempt 5 preparation: boot024 early-screen diagnostics

**Current instruction for M1.** Read this file and `coordination.md` after
`git pull --ff-only` (preserve local work; stop on divergence). Attempt 4 is
consumed: DAPF/preflight/kboot reply PASS, Linux NOT OBSERVED. M5 has built and
validated boot024 to expose the missing handoff milestones. Your next action
is offline intake/readiness; then the human can start **one** RAM boot.

Do not run Recovery, installer, bputil, kmutil, partition/security/default
commands, or reinstall m1n1. Macintosh HD stays Full Security. The installed
boot021 m1n1 and clean client pin `57a9339ffd1876e78297b17d34dece8cff8fa1ba`
are correct. Reuse the tested direct cable and primary-interface discovery.
No new peripheral, SMP, DVFS or storage experiments.

## What changed and what it will tell us

Only the packaged Linux **Image** changes from boot022. It adds three early
entry rectangles and a DT-backed early framebuffer console. The launcher adds
`earlycon=ilinuxfb initcall_debug` and fills a checked **16-byte kernel RAM data
descriptor** from the validated prepared framebuffer. The previously tested
96-byte DAPF RAM correction remains. All board/version/CPU/storage/framebuffer
gates remain. No persistent files are written on the target by this procedure.

Read `kernel/experiments/early-framebuffer/README.md` for evidence and limits.
REA confirmed that installed m1n1 clears its console before jumping to Linux;
last attempt's logo alone cannot identify the stop. We need the screen evidence.

## Return protection prerequisite — already PASS

After attempt 4, M5 reviewed fresh human-supplied JSON: original **Full**, lab
**Permissive**, both exit 0. M5 independently read original root Macintosh HD,
build 25G83, FileVault=true, SIP enabled, and the unchanged staged m1n1 digest.
Default selection/installed boot object/authenticated-root were not separately
re-queried this turn. No settings changed. Do not request the same policy check
again or introduce an M1↔M5 approval loop unless new evidence changes state.

## M1 offline intake — complete before asking the human to restart

Download the new package separately; keep every earlier package and result.
Run from the repo root, stopping on any error:

```sh
(
set -e
mkdir -p build/native-boot024-download
# If already downloaded, verify it; do not overwrite blindly.
gh release download native-j716c-boot024 --repo nickyrice04/ilinux \
  --pattern ilinux-j716c-boot024.tar.gz --dir build/native-boot024-download
(
  cd build/native-boot024-download
  shasum -a 256 -c ../../native/boot/archive-sha256.txt
  tar -xzf ilinux-j716c-boot024.tar.gz
)
mkdir -p build/native-intake/receipts build/native-intake/results
tools/m1n1-client/run.sh tools/m1n1-client/verify-package.py \
  build/native-boot024-download/ilinux-j716c-boot024 \
  --manifest-sha256 "$(cat native/boot/intake-manifest-sha256.txt)" \
  > build/native-intake/receipts/boot024.json
python3 -I native/boot/launch.py --package build/native-boot024-download/ilinux-j716c-boot024
python3 -I native/boot/test_launcher.py
python3 -I native/boot/test_entry_guard.py
python3 -I native/boot/test_dapf_guard.py
python3 -I native/boot/test_framebuffer.py
tools/m1n1-client/run.sh native/boot/test_dapf_guard_adt.py
tools/m1n1-client/run.sh native/boot/test_launcher_adt.py
tools/m1n1-client/run.sh native/boot/test_protocol.py
)
```

Require package PASS, 13 verified receipt files, and **31 + 6 + 16 + 5 + 2 + 4
+ 1 = 65 cases PASS**, with the clean pinned client. M5 already compiled/tested
the kernel and C/assembly in Linux; no new compiler/decompiler setup on M1.
An intake receipt is not a live-boot authorization. The verifier's generic
historical `next` field does not override this current checklist.

Archive: **16,720,911 bytes**, SHA-256
`f7cb69153adc832cae3a66fd6159e7fd41fccc2a113d3550962a7f959edd9636`.
Image SHA-256:
`6b683a2f52e769d1a23474b6807d009da8ad2e19d2168e62caba6cbbae240f7d`.
SHA256SUMS digest:
`c9b132f08ea093667c9abb3798315e77cc6347d28897bdfa87654d14e20a2219`.
Git-tracked manifests are authoritative; stop on disagreement.

Reviewed controller digests (also record the checked-out Git commit):

* `native/boot/launch.py`: `0a033a85a7a8ba2d9c3723468a9550df4df5afc598ef1267702671319376868f`
* `native/boot/entry_guard.py`: `d1fa8ca84aa1c7032c50c8766c8571054047720df35cb7d518310167ec183713`
* `native/boot/dapf_guard.py`: `bb33d9bebcec3a6cd925ed9e7b28dbabe3c7375c445d7e9d68ace18f4eaa7047`
* `native/boot/fdt.py`: `98ff4d58a0ca5b5abb68689b901aef526726704fa70925e96db6f1bbf836a591`
* `tools/m1n1-client/usb_identity.py`: `72cc8c2a916b8964b2e4b5afc4c1aac22fe8031a2c2f8658df6882b063a47137`

Prepare a fresh ignored `boot024-stage-b-attempt5.json`/`.md` record with Git
commit, procedure/controller hashes and receipt. Publish sanitized readiness
in `progress.md`/`coordination.md` and push. **Attempt 5/live checks NOT RUN.**
Tell the human when ready. Once they choose to restart for this test and report
`Running proxy...`, proceed once; no further M5 review round trip is needed for
unchanged verified code. Do not open USB during offline readiness.

## One human-started attempt

1. Both Macs on power, direct cable, M5 built-in display visible. Have the
   human start a close, focused **phone video of the display before launch**;
   60 fps if available. A recording lets us pause fast text afterward. Keep
   full video local; publish only sanitized checkpoints/error summaries.
   If no recording method is available, stop at readiness and arrange one
   rather than consume another attempt with unreadable output.
2. Human saves work, shuts down, holds power continuously to startup options,
   chooses **iLinux Boot Lab → Continue**. Keep Macintosh HD as default.
   If already at `Running proxy...` for this new attempt, do not reboot again.
3. With the human's start and the matching proxy running, invoke **once**:

   ```sh
   tools/m1n1-client/run.sh native/boot/launch.py \
     --package build/native-boot024-download/ilinux-j716c-boot024 \
     --launch --device auto --confirm BOOT-J716C-RAM-DIAGNOSTIC
   ```

   Use the existing sanitized wrapper if used previously, calling this same
   `main(argv)` once. It must retain the new fixed checkpoint below. Never
   import `m1n1.setup`, open a shell, issue a separate handshake or auto-retry.
4. Record start/end/elapsed/exit and all fixed controller checkpoints. Require
   both DAPF messages, then **`Early framebuffer PASS: kernel RAM descriptor
   checked and populated.`**, then preflight/handoff. Do not log raw target
   output, ADT, registers, callout path identifiers or memory. Unexpected errors:
   safe module/function/line metadata and reviewed fixed message, no locals.
   Stop on any rejection/timeout; do not bypass gates or select another port.
5. USB proxy ends at handoff. Controller exit 0 only means the request/reply
   succeeded. The human observes the top-left screen and records which appear:

   | Observation | Established milestone / next offline work |
   |---|---|
   | One white rectangle | Kernel `primary_entry` executed; inspect CPU entry/EL setup before marker 2. |
   | Two rectangles | `init_kernel_el` returned; inspect `__cpu_setup` before marker 3. |
   | Three rectangles | `__cpu_setup` returned; MMU transition and early C/DT/console setup are next if no text. |
   | Early Linux text / bootconsole `ilinuxfb` | Early C/DT console reached. Read last `calling`/`returned` initializer or exception. |
   | `PID 1 reached`, `online_cpus=1`, 60-second message | Native userspace/liveness milestones observed; record separately. |
   | No new rectangle or text | Observation still missing; may be handoff or invisible framebuffer write. No specific fault proven. |

   Rectangles may appear too quickly to distinguish intermediate states; the
   highest count seen is useful. Later text/real fbcon can overwrite them.
   Circular early text wraps to the top; timestamps identify the newest lines.
   Film the transition and capture the last readable initializer/error.
6. Stop on the 60-second userspace message, explicit panic/failure, or **120
   seconds after handoff**, whichever comes first. Controller transport has
   its own 180-second bound (discovery 15 seconds). No USB reconnect, rescue
   commands or second attempt under this checklist.
7. Human holds power until off, releases, then holds continuously to startup
   options and chooses **Macintosh HD → Continue**. Confirm desktop return.
   If return fails, stop/report; no automatic revive/restore/security changes.
8. Publish sanitized attempt-5 results and push: each controller checkpoint,
   highest rectangle count, first/last readable Linux line, initializer/panic
   summary, PID 1/CPU/liveness and return. Unseen milestones **NOT OBSERVED**.
   Do not commit full video/photos with register dumps or identifiers; redact
   before sharing. M5 performs the next read-only post-return protection check.

This diagnostic initramfs has no shell/network/SSH/agent and mounts no disks.
The Linux configuration agent comes later, after usable native access and a
separately approved root environment. This attempt measures boot milestones,
not Omarchy usability or macOS performance parity.
