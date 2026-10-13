# Second-machine m1n1 client

Prepared 2026-10-13 on the second macOS computer. This is client preparation,
not authorization to install a boot entry, change security or boot the M5.

**Current handoff:** follow [`../../native/boot/README.md`](../../native/boot/README.md)
for the checksummed job-021 package and offline-only launcher checks. The
user authorized preparation/pushes only and explicitly stopped before boot
settings. Do not run the live examples below during this preparation phase.

## Installed locally

* `third_party/m1n1` is an unmodified, detached checkout at
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`, matching the native plan.
* `tools/m1n1-client/.venv` uses the existing Python 3.9.6 with upstream's
  pinned `construct==2.10.70` and `pyserial==3.5` wheels.
* Offline proxy, proxyutils, shell and hypervisor imports pass; `pip check`
  passes. No target connection, register access or boot was performed.
* Clone and environment are ignored by Git. No upstream files were changed.

From the repository root, repeat the offline check:

```sh
tools/m1n1-client/.venv/bin/python -I tools/m1n1-client/check.py
```

## Before a physical test

1. Finish and verify the M5 backup. Keep the M5 on power.
2. Have a USB data cable (USB-C to USB-C, or USB-A on this host to USB-C on
   the M5). Connect directly to a Thunderbolt-capable target port; avoid
   charge-only cables. Power can use another port or MagSafe.
3. The M5 needs its separately approved dedicated m1n1 boot entry and
   target-side installation/security prerequisites. GitHub and this client
   do not create that entry. Follow `kernel/native-enablement/first-boot-plan.md`
   and its gates; do not run the standard Asahi installer assuming M5 support.
4. Keep the client pinned to `m1n1-revision.txt`. `run.sh` refuses a different
   or dirty client checkout. The current pin matches the project's planned
   target version, which has not been observed live. If the sender declares
   a different revision, stop and reconcile the handoff; never auto-update.
5. For Stage B, transfer agent A's actual job-020 `Image`,
   `t6050-j716c.dtb` and diagnostic `initramfs.cpio.gz` with checksums.
   They are ignored build outputs and are absent from this clone.
6. Project-local LLVM 23.1.3 provides clang, lld, llvm-objcopy, llvm-nm and
   llvm-objdump. Use `tools/m1n1-client/run.sh SCRIPT [ARGS]` to select it.
   A local ARM64 assembly/link/disassembly smoke check is provided below.
   This does not establish full hypervisor or hardware readiness.

## LLVM and USB checks

LLVM is a minimal extraction of the official ARM64 macOS release under
`third_party/LLVM-23.1.3-macOS-ARM64/`, ignored by Git. No Homebrew, global
PATH change or system package installation is needed. Release archive:
https://github.com/llvm/llvm-project/releases/tag/llvmorg-23.1.3

The archive SHA-256 was checked against GitHub's release asset digest:
`3dcfd88aec10be204a24037bcb0dc0ad777882e9dbe8ac60e2639060d8a794b1`.
The downloaded archive is removed after successful installation to save space.

```sh
tools/m1n1-client/run.sh tools/m1n1-client/check-toolchain.py
tools/m1n1-client/run.sh tools/m1n1-client/usb-check.py
```

The USB checker defaults to device-path discovery only. After the backup
and target boot-entry gates are complete, explicitly connect with:

```sh
tools/m1n1-client/run.sh tools/m1n1-client/usb-check.py --connect /dev/cu.usbmodemP_01
```

Connection mode sends exactly one **proxy P_NOP** request and closes the port,
with a 10-second deadline. It does not import `m1n1.setup`, negotiate transport
features, access registers/memory, reset the panic counter or request a boot.
It suppresses incidental target console output and does not save logs/history.
Opening the serial port can interrupt target autoboot into proxy mode; the
serial transport transmits a request, so this is a non-mutating protocol
check rather than passive USB observation. Run it only in the agreed target
session. A fake serial transport test checks the exact outgoing opcode and
zero arguments, and verifies closure on success and timeout:

```sh
tools/m1n1-client/run.sh tools/m1n1-client/test_usb_check.py
```

## Receive and checksum the native package

Local intake directories are ready and ignored by Git:

* `build/native-intake/inbox/`: received package, in its own subdirectory.
* `build/native-intake/receipts/`: successful verification JSON.
* `build/native-intake/results/`: reviewed observations from approved tests.

Expected sender handoff: `Image`, `t6050-j716c.dtb`, `initramfs.cpio.gz`, and
`m1n1-revision.txt` containing the full target commit. Include the corrected
single-core launcher and boot-entry procedure when ready, with their review
status and exact intended boot arguments. Include a standard `SHA256SUMS`
covering every file except itself. Send the SHA-256 of `SHA256SUMS` separately
in the GitHub handoff so transfer errors can be detected against the sender's
record. Existing packaging can be accommodated after reviewing its format.

For a received directory (replace placeholders with the actual values):

```sh
tools/m1n1-client/run.sh tools/m1n1-client/verify-package.py \
  build/native-intake/inbox/PACKAGE \
  --manifest-sha256 SENDER_MANIFEST_SHA256 \
  > build/native-intake/receipts/PACKAGE.json
```

Check exit status: only exit 0 with a complete JSON receipt is a pass. The
verifier rejects missing, changed, unlisted or linked files, unsafe paths,
and a declared target revision different from the client pin. It only reads
files; it never extracts archives, imports package code or executes a launcher.
Checksum success proves agreement with the supplied handoff, not boot safety
or authenticity independent of that handoff. No real package has arrived yet.

Before any approved diagnostic session, reverify the package and copy
`boot-result-template.md` into a new results file. Record the manifest digest,
launcher/procedure digests, approval scope, exact invocation, expected vs
observed output, timeout/failure checkpoint and recovery outcome. Keep
unobserved results explicitly marked. No automatic raw logging or upload.

## Connection check after the target gate is approved

Run the offline checker again with the M5 booted into its approved m1n1
proxy entry. On macOS the primary interface is normally
`/dev/cu.usbmodemP_01`; `P_03` is the secondary virtual UART. Confirm actual
device names rather than assuming them. No extra USB driver is installed.

Use the bounded checker above for the first live test. The upstream shell
is not a read-only handshake: `m1n1.setup` calls
`PMU(u).reset_panic_counter()` during startup. It also permits hardware writes
from the shell and stores history in `~/.m1n1-history`.

Do not use `tools/linux.py` for the first single-core test. It unconditionally
starts secondary CPUs before Linux, even with `maxcpus=1`. Use the reviewed
`native/boot/launch.py` instead, only after separate live-session approval.
It loads the verified uncompressed Image directly, with no compression guess.

## Sources

* https://asahilinux.org/docs/sw/m1n1-user-guide/
* https://asahilinux.org/docs/sw/tethered-boot/
* https://asahilinux.org/docs/sw/m1n1-hypervisor/
* Pinned upstream `requirements.txt`, `proxyclient/m1n1/setup.py`,
  `proxyclient/m1n1/proxy.py`, and `proxyclient/tools/linux.py`.

Upstream's AGENTS.md forbids AI work in its repository; upstream is kept
unmodified. These local setup notes and checks belong to iLinux only.
