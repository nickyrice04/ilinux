# Stage B attempt 3: boot022 preflight passed; m1n1 SError at handoff

Session: 2026-10-13 America/New_York (UTC timestamps below).
Execution/readiness commit: `c5f515c20346494c5f5e96b72f4b71230c867de8`.
M5 handoff: `3c7eae1` (includes `bf79263`). Human reported Running proxy after
published readiness. Exactly one invocation; no retry or additional USB call.
Previous attempts and receipts remain separate and unchanged.

## Observed result

* Start UTC **2026-10-14T02:34:32.733054+00:00**; end UTC
  **2026-10-14T02:35:04.792407+00:00**. Controller **exit 1, 32.059 s**.
* Package, USB identity, chip/boot021 marker/initial secondary checks,
  ADT root compatibility and initial board/framebuffer checks all passed.
  RAM upload completed. **Prepared-DT validation passed**, including the
  corrected enabled framebuffer, geometry/format/range, one exposed CPU,
  disabled NVMe/cpufreq and fixed boot arguments. Secondary recheck and
  cache/DAIF setup completed before the handoff checkpoint.
* **Handoff requested at 2026-10-14T02:34:42.905947+00:00**:
  `Preflight PASS; handing off. Observe the M5 display; USB console ends here.`
  Launcher entered `proxy.kboot_boot(kernel)` (`launch.py:124`).
* Controller then raised **UartTimeout** while waiting for the kboot reply.
  Safe trace: `kboot_boot` → `request` → `_request` → `proxyreq` → `reply` →
  `readfull`, with source lines retained in ignored JSON. This transport result
  alone does not establish Linux success/failure. Cleanup ran; no close error.
* **Target screen supplies the failure evidence:** m1n1 reports `Exception:
  SError`, `Exception taken from EL2h`, `Running in EL2`, and
  `Unhandled exception, rebooting...`. Relative PC printed by m1n1 is
  **`0x16458`**, retained only as a non-identifying code offset for matching-build
  symbolization. No absolute PC, other addresses or register dump retained.
* **Kernel execution, PID 1, online_cpus=1 and 60-second liveness: NOT OBSERVED.**
  This differs from attempts 1/2: controller preflight passed and a handoff was
  requested, but m1n1 failed during preparation; no Linux success is claimed.
  One-CPU DT validation is not a measurement of running Linux's online count.
* Stop reason: explicit target exception. The prescribed screen deadline was
  **02:36:42.905962 UTC / 22:36:43 Eastern**, 120 seconds after the checkpoint.
  Human was instructed to stop on the failure and return; precise power-off
  timing was not measured. No second launcher invocation or reconnect occurred.
* **User confirms successful return to the usual Macintosh HD desktop.** Fresh
  build/default/security checks remain NOT CHECKED for this attempt. Earlier
  M5-reviewed Full/Permissive policy output is the pre-attempt baseline.
* No volume, security, default-startup or boot-object changes were issued by M1.
  Installed m1n1 and client pin are unchanged. RAM/register/hardware preparation
  did occur; this was the authorized RAM attempt, not a read-only handshake.

## Sanitized screen sequence

After DT preparation, the supplied photo shows:

```text
FDT prepared [address omitted]
mca-switch node not found!
pcie: Error getting node /arm-io/apcie
pcie: Unsupported compatible
pcie: Error getting node /arm-io/apcie-ge0
pcie: Error getting node /arm-io/apcie-ge1
Exception: SError
Exception taken from EL2h
Running in EL2
[register dump omitted]
Unhandled exception, rebooting...
```

Earlier display/GPU/reserved-memory warnings are also visible, but the
framebuffer preflight gate now passed. The ordering does not prove PCIe caused
an asynchronous SError. Do not diagnose Linux or a specific driver from proximity
alone. No Linux banner, PID 1 or heartbeat is visible in this image.

## M5 handoff: investigate offline

1. Perform read-only return/default/protection checks on M5, distinguishing
   independently queried results from human-reported desktop return.
2. Resolve relative code offset `0x16458` against the retained exact boot021
   m1n1 build symbols/map if available; verify matching binary provenance first.
   The installed binary is unchanged in boot022. An SError's reported PC need
   not identify the original faulting operation, so retain that uncertainty.
3. Review pinned `src/kboot.c:kboot_boot()` around its pre-kernel hardware
   setup: cache/tunables/clocks, USB, PCIe and DAPF. The photo reaches the
   PCIe messages but does not show the later `Setting SMP mode to WFE...` or
   `Preparing to boot kernel...` messages. These are useful bounds, not proof
   of an exact failing function. Follow actual code/symbol evidence.
4. Keep the now-passing framebuffer/board/CPU/storage/version gates. Prepare
   any targeted correction and regression offline, with provenance, before
   proposing another physical session. **No retries, reinstall, boot-setting
   changes or new live diagnostics are authorized by this result handoff.**

## Provenance and limits

* Boot022 archive SHA-256:
  `b59db87bee50f5a2b57f65ea54e9ecd9fc07d410251bb38175001ac056ee6862`.
* Intake manifest SHA-256:
  `862391dd99ee93d07c196e502196cefc869b2549274d6139d781f564b4bc50a0`.
* Stage-B DT SHA-256:
  `7adc1364687df9c358692489f2a574241e869cf03b67538eaaaaf0233b4365a7`.
* Clean client pin: `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
  Installed marker remains `##m1n1_ver##ilinux-57a9339-boot021` (live PASS).
* Readiness completed archive/package/13-file intake, source hash checks,
  and 31 launcher + 5 framebuffer + 4 pinned-ADT tests. Prior unchanged USB
  tests remain historical; no tests were rerun just to write this result.
* The unchanged launcher `main(argv)` ran once with documented arguments via
  the sanitized logging wrapper and `run.sh` pin/toolchain setup. Gates,
  180-second controller bound and cleanup stayed intact.
* Ignored evidence: `build/native-intake/results/boot022-stage-b-attempt3.json`
  and `.md`; receipt `build/native-intake/receipts/boot022.json`. Full source,
  procedure and payload digests/timed checkpoints are retained there.
  No raw ADT, target memory, serial-bearing device paths, absolute exception
  addresses or photo were copied into the repository.
