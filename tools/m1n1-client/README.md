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
6. LLVM/lld/llvm-objcopy are not installed here. Assembly-based operations
   need a separately prepared toolchain; basic imports do not test those.
   Do not interpret this environment as full hypervisor readiness.

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
