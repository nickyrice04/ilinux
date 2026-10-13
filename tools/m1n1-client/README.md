# Second-machine m1n1 client

Prepared 2026-10-13 on the second macOS computer. This is client preparation,
not authorization to install a boot entry, change security or boot the M5.

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
4. Agree on the target m1n1 version with agent A. The proxy ABI is not stable;
   use a matching client checkout if the target version changes.
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

## Connection check after the target gate is approved

Run the offline checker again with the M5 booted into its approved m1n1
proxy entry. On macOS the primary interface is normally
`/dev/cu.usbmodemP_01`; `P_03` is the secondary virtual UART. Confirm actual
device names rather than assuming them. No extra USB driver is installed.

The upstream interactive command, for an explicitly authorized target
session, is:

```sh
M1N1DEVICE=/dev/cu.usbmodemP_01 tools/m1n1-client/.venv/bin/python -I third_party/m1n1/proxyclient/tools/shell.py
```

**This is not a read-only handshake:** upstream `m1n1.setup` calls
`PMU(u).reset_panic_counter()` during startup. It also permits hardware writes
from the shell and stores history in `~/.m1n1-history`. Review/authorize those
effects before use; no shell or boot command was executed during setup.
If the first session must be strictly read-only, prepare a separate minimal
handshake instead of using that shell.

When eventually using `tools/linux.py`, the uncompressed job-020 `Image`
requires `--compression none` (the script cannot infer compression from
the filename `Image`). Final boot arguments still need agent A's review.

## Sources

* https://asahilinux.org/docs/sw/m1n1-user-guide/
* https://asahilinux.org/docs/sw/tethered-boot/
* https://asahilinux.org/docs/sw/m1n1-hypervisor/
* Pinned upstream `requirements.txt`, `proxyclient/m1n1/setup.py`,
  `proxyclient/m1n1/proxy.py`, and `proxyclient/tools/linux.py`.

Upstream's AGENTS.md forbids AI work in its repository; upstream is kept
unmodified. These local setup notes and checks belong to iLinux only.
