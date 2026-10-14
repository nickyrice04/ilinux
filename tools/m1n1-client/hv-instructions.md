# HV sessions: census v2, then hv002 (boot033 under the private hypervisor)

**M5 handoff, 2026-10-14: hv002.** Read `native/hv/README.md` first, including
why hv001 was blocked. Private tooling: never send any of it upstream.
**Native/HV live checks NOT RUN at this handoff.** Both sessions are RAM-only
and human-started.

* Keep Macintosh HD as default at Full Security.
* No volume, security, `bputil`, `kmutil` or installed-m1n1 change.
* Installed boot021 and the clean client pin `57a9339` stay unchanged.
* No automatic retries. Power off returns to Macintosh HD.
* hv001 (`native-j716c-hv001`) is superseded. Do not run it.

## Offline readiness (M1)

1. `git pull --ff-only`, stopping on divergence. Verify the file hashes in
   `native/hv/README.md` against your checkout.
2. Download release `native-j716c-hv002` asset `ilinux-j716c-hv002.tar.gz`
   (SHA-256 `c79ffded48bebc580734918c1540fd589937d5440e2a385a65186c801f2c4254`).
   * Verify it before extracting into a fresh `build/native-hv002-download/`.
     That yields `build/native-hv002-download/native-hv002/`.
   * Keep the existing `build/native-boot033-download/ilinux-j716c-boot033`.
3. In the client venv, with no device, run:

   ```sh
   tools/m1n1-client/run.sh native/hv/test_hv_launch.py
   python3 -I native/boot/test_launcher.py
   tools/m1n1-client/run.sh -c "import sys; sys.path.insert(0, 'third_party/m1n1/proxyclient'); import m1n1.hv, m1n1.bootmem, m1n1.tgtypes, m1n1.proxyutils, construct, serial; print('imports PASS')"
   tools/m1n1-client/run.sh native/hv/hv_launch.py --package build/native-boot033-download/ilinux-j716c-boot033 --hv-package build/native-hv002-download/native-hv002
   ```

   Expect:
   * **33** hv tests PASS, including `TimerModelTests` (needs `cc`) and
     `PackageTests` against the real packages. Record any skipped test.
   * Launcher tests PASS.
   * `imports PASS`.
   * `Package PASS: boot033 guest and hv002 m1n1` and `OFFLINE ONLY`.
4. Publish sanitized readiness in `progress.md` and `coordination.md`, with
   live checks NOT RUN. Tell the human when ready.

## Session 1: census v2 (reads only, ~5 minutes)

The human starts **iLinux Boot Lab → Continue** and reports `Running proxy...`.
Then invoke this once:

```sh
tools/m1n1-client/run.sh native/hv/census.py --device auto --confirm CENSUS-J716C-READ-ONLY
```

* It checks chip, the boot021 marker and that no secondaries are started.
* It then reads **19** registers under m1n1's exception guard. There are no
  register writes, and m1n1's console text is not echoed.
* Record the table and the verdict (classes only).
  * `ENA_V=1 ENA_P=1` is expected and **no longer blocks**.
  * `IMP_APL_ACTLR_EL12`, `UPMCR0` and `UPMSR` are informational: hv002 never
    touches them on t6050.
  * Missing ECV, or a trapped `PMCR0`/`IPI_SR_EL1`/start-path register,
    blocks.
* **Stop on SError or hang:** power off and return to Macintosh HD.
* `VERDICT: BLOCKED` ends here. Report it.
* After `PASS for hv002`, power off and return to Macintosh HD.
* `hv_launch.py` repeats these same guarded reads in its own boot before the
  chainload, so a state change between boots is still caught.

## Session 2: hv002 (only after census PASS and the human's separate start)

1. Film the M5 screen as before. Both Macs on power, same direct cable.
2. The human starts **iLinux Boot Lab → Continue** and reports the proxy.
3. **Terminal A:** start the vUART logger. If USB re-enumerates during the
   chainload it says `vUART disconnected` and reopens; that is expected.

   ```sh
   tools/m1n1-client/run.sh native/hv/vuart_log.py --log build/native-intake/hv002-vuart.log
   ```

4. **Terminal B:** invoke this once:

   ```sh
   tools/m1n1-client/run.sh native/hv/hv_launch.py --package build/native-boot033-download/ilinux-j716c-boot033 --hv-package build/native-hv002-download/native-hv002 --launch --device auto --confirm HV-J716C-RAM-DIAGNOSTIC --log build/native-intake/hv002-events.log
   ```

5. Pass signals, in order. `Waiting for reconnection...` may appear after the
   chainload.
   1. In terminal B:
      * `Target PASS: t6050, installed boot021`;
      * `Register preflight PASS`;
      * `Target PASS: hv002 running`;
      * `HV PASS: single-CPU mode, ECV timer traps on; guest timers masked at
        source`;
      * `Hardware DT PASS`;
      * `Starting EL1 guest`.
   2. In terminal A: the first kernel line, then advancing printk times. That
      the times advance is the first proof the source-masked timer works.
   3. In terminal A: `PID 1 reached` and `[diag] heartbeat` lines.

   Then press **Ctrl-C once** in terminal B: expect the HV shell. Run `bt` and
   record the symbolized frames. Ctrl-D resumes.
6. **Stop** on any of:
   * `STOP:`;
   * an EL2 exception;
   * a guest panic;
   * a reset;
   * 120 s after `Starting EL1 guest`;
   * the first failed signal.

   Then power off and return to Macintosh HD.
   * If printk times **stop advancing** after the first kernel lines, use
     Ctrl-C and `bt`, record the frames, then stop. This is the README's
     ECV-trap risk.
7. If the guest is still alive at 120 s, record that as an **HV-only**
   result. Attempt 14's reset either reproduces under the HV or does not; both
   are informative. If it reproduces, report the last 50 vUART lines and the
   last events in `hv002-events.log`, noting any `Dangerous write` lines.

Logs and media stay local in ignored `build/native-intake/`. Commit only
sanitized excerpts: no serials, MACs, raw ADT or memory dumps.
