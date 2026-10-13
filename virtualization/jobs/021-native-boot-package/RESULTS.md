# Job 021 results — 2026-10-13

**Prepared and offline-tested; native M5 boot, USB connectivity and installation
remain untested. No host boot/security/storage settings were changed.**

## Export and builds

* All three original job-020 payload hashes match its retained `artifacts.txt`.
  The full kernel Image is reused; no silent kernel rebuild or patch change.
* Clean full m1n1 build at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`
  succeeds, including both ELF links and raw binary. Source checkout remains
  unmodified. ELF is AArch64, entry `0x800`; `_base=0`, `version_tag=0x809e8`,
  prepared-DT pointer symbol `dt=0x116538`. The version offset is also checked
  against actual raw binary bytes when packaging.
* Toolchain: GCC 16.1.1, GNU ld 2.46.0, Rust/Cargo 1.99.0, Python 3.14.8,
  dtc 1.8.1, ARM64 Linux VM. No host-level installation.
* One Rust standard-library future-incompatibility warning is reported by
  Cargo; it does not fail this build. No other warning/error line in the final
  m1n1 build log. Flags and dependency versions are retained in the package.
* Stage-B diagnostic init compiles static with `-O2 -Wall -Wextra -Werror`.
  CPIO ownership/timestamps are normalized, gzip timestamp omitted.
* Stage-B DT decompiles without warnings. `dt-validate` against job 020's
  processed schema returns 0 with **no diagnostic output**. NVMe remains
  disabled; three cpufreq nodes are disabled; serial stdout-path is removed.

## Launcher validation

* 17 original Python tests pass on macOS and ARM64 Linux: valid sequence,
  nonzero Image offset, wrong chip/build/board, already-started secondary,
  DT preparation failure, multiple CPUs, enabled storage, missing framebuffer,
  changed arguments, m1n1 workaround append, corrupt/truncated data,
  symlink rejection, offline no-connect and explicit live gate.
* One VM-only integration test uses the **actual pinned M1N1Proxy serializer**.
  It observes exactly one final kernel handoff and 64 secondary-state reads
  (two passes across all 32 slots), with no SMP-start or cpufreq-init request.
  USB and ProxyUtils hardware execution are simulated, not hardware-tested.
* All file sizes/hashes and Stage-B DT checks pass through the production
  verifier. This mode imports no upstream code and opens no USB device.

## Diskless VM payload smoke test

The packaged native `Image` and Stage-B initramfs booted in a separate
Virtualization.framework VM: **1 vCPU, 4 GiB RAM, no disk, no network**.
Arguments: `console=hvc0 rdinit=/init maxcpus=1 nr_cpus=1 panic=0`.
The process was deliberately bounded to 65 seconds and then terminated.

Observed: `PID 1 reached`, `online_cpus=1`, the 60-second-alive message,
and heartbeat 012. This tests the exact kernel/initramfs through generic
ARM64 boot and userspace. The VM supplies its own DT and virtio console;
it does **not** test J716c DT fixups, native simpledrm, AIC, USB, SMP, storage,
power efficiency or the m1n1 hardware handoff. No native performance claim.

The first build-VM invocation omitted `rootflags=subvol=@` and could not
find init; the documented invocation corrects that existing Btrfs layout.
All exports/builds/tests above used the corrected VM boot. The diskless
payload smoke test has no Btrfs/root-disk dependency.

## M1 intake integration

Merged M1 commit `33d99f7` without discarding its intake tools or records.
All seven synthetic intake regressions pass on macOS. Its actual verifier
accepts the final extracted archive (13 manifest entries plus SHA256SUMS),
using the separately tracked manifest digest and declared pinned revision.
The receipt explicitly retains `boot_authorized: false`. All runtime payload
bytes are unchanged from the final VM tests; only revision metadata was added.

## Package and remaining gate

Archive `ilinux-j716c-boot021.tar.gz`: **16,717,560 bytes**. SHA-256:
`b534680fc25dff78d8eaecfb96ed5b9733a3f408ae20cb4947722cb8163edc15`.
The tracked [manifest](../../../native/boot/package-manifest.json) pins every
file. Raw logs remain ignored in `out/`; the archive is a private prerelease
asset, not a Git blob. Only allowlisted open-source outputs are packaged.

Next: M1 downloads and verifies offline, then reports readiness. A dedicated
M5 OS entry/provisioning procedure and its separate user approval are still
required. Native Linux output is attempted on the M5 screen, not promised
over the m1n1 USB proxy. See the corrected first-boot plan and M1 handoff.
