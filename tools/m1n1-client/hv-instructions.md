# HV sessions: H1 census, then hv001 (boot033 under the private hypervisor)

**M5 handoff, 2026-10-14 (reviewed twice).** Read `native/hv/README.md` first.
Private tooling: never send any of it upstream. **Native/HV live checks NOT RUN
at this handoff.** Both sessions are RAM-only and human-started.

* Keep Macintosh HD as default at Full Security.
* No volume, security, `bputil`, `kmutil` or installed-m1n1 change.
* Installed boot021 and the clean client pin `57a9339` stay unchanged.
* No automatic retries. Power off returns to Macintosh HD.

## Offline readiness (M1)

1. `git pull --ff-only`, stopping on divergence. Verify the file hashes in
   `native/hv/README.md` against your checkout.
2. Download release `native-j716c-hv001` asset `ilinux-j716c-hv001.tar.gz`
   (SHA-256 `c659462c77df8a56979aff5f5f5596cbbdb49a6bbe0eaef5d2ecfd9bd6f4ebb1`).
   * Verify it before extracting into a fresh
     `build/native-hv001-download/`. That yields
     `build/native-hv001-download/native-hv001/`.
   * Keep the existing `build/native-boot033-download/ilinux-j716c-boot033`.
3. In the client venv, with no device, run:

   ```sh
   tools/m1n1-client/run.sh native/hv/test_hv_launch.py
   python3 -I native/boot/test_launcher.py
   tools/m1n1-client/run.sh -c "import sys; sys.path.insert(0, 'third_party/m1n1/proxyclient'); import m1n1.hv, m1n1.bootmem, m1n1.tgtypes, m1n1.proxyutils, construct, serial; print('imports PASS')"
   tools/m1n1-client/run.sh native/hv/hv_launch.py --package build/native-boot033-download/ilinux-j716c-boot033 --hv-package build/native-hv001-download/native-hv001
   ```

   Expect:
   * **28** hv tests PASS. `PackageTests` find the two download directories
     and run against the real packages; record whether they ran or were
     skipped.
   * Launcher tests PASS.
   * `imports PASS`.
   * `Package PASS` and `OFFLINE ONLY`.
4. Publish sanitized readiness in `progress.md` and `coordination.md`, with
   live checks NOT RUN. Tell the human when ready.

## Session 1: H1 register census (reads only, ~5 minutes)

The human starts **iLinux Boot Lab → Continue** and reports `Running proxy...`.
Then invoke this once:

```sh
tools/m1n1-client/run.sh native/hv/census.py --device auto --confirm CENSUS-J716C-READ-ONLY
```

* It checks chip, the boot021 marker and that no secondaries are started.
* It then reads 15 registers under m1n1's exception guard. There are no
  register writes, and m1n1's console text is not echoed.
* Record the printed table and the verdict; they contain classes only.
  `IMP_APL_ACTLR_EL12` is informational: t6050 never uses it.
* **Stop on SError or hang:** power off and return to Macintosh HD.
* `VERDICT: BLOCKED` ends here. Report it; M5 revises the patch.
* After `PASS`, power off and return to Macintosh HD anyway. Each session
  starts from a fresh boot.

## Session 2: hv001 (only after census PASS and the human's separate start)

1. Film the M5 screen as for Stage B; the panel and console still render
   there. Both Macs on power, same direct cable.
2. The human starts **iLinux Boot Lab → Continue** and reports the proxy.
3. **Terminal A:** start the vUART logger. It opens interface 3 as soon as it
   appears. If USB re-enumerates during the chainload it says
   `vUART disconnected` and reopens; that is expected.

   ```sh
   tools/m1n1-client/run.sh native/hv/vuart_log.py --log build/native-intake/hv001-vuart.log
   ```

4. **Terminal B:** invoke this once:

   ```sh
   tools/m1n1-client/run.sh native/hv/hv_launch.py --package build/native-boot033-download/ilinux-j716c-boot033 --hv-package build/native-hv001-download/native-hv001 --launch --device auto --confirm HV-J716C-RAM-DIAGNOSTIC --log build/native-intake/hv001-events.log
   ```

5. Pass signals, in order. `Waiting for reconnection...` may appear after the
   chainload.
   1. In terminal B:
      * `Target PASS: t6050, installed boot021`;
      * `Target PASS: hv001 running`;
      * `HV PASS: single-CPU mode, guest timer FIQs disabled (polled)`;
      * `Hardware DT PASS`;
      * `Starting EL1 guest`.
   2. In terminal A: the first kernel line, then advancing printk times.
   3. In terminal A: `PID 1 reached` and `[diag] heartbeat` lines, which are
      diag init's kmsg copies.

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
7. If the guest is still alive at 120 s, record that as an **HV-only**
   result. Attempt 14's reset either reproduces under the HV or does not;
   both are informative. If it reproduces, report the last 50 vUART lines and
   the last events in `hv001-events.log`. Note any `Dangerous write` lines;
   those are guest PMGR writes to the HV link's power domains, held on.

Logs and media stay local in ignored `build/native-intake/`. Commit only
sanitized excerpts: no serials, MACs, raw ADT or memory dumps.
