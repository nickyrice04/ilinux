# PMGR probe sessions (private; read-only first)

**M5 handoff, 2026-10-14.** Private tooling: never send any of it upstream.
**Live checks NOT RUN at this handoff.** Every session is RAM-only and
human-started, on the installed boot021 m1n1 in the lab, exactly like the Stage A
check and the register census. The tool is `native/probe/pmgr_probe.py`; it is
independent of attempt 15 (boot034) and of the hv003 ladder.

* Keep Macintosh HD as default at Full Security.
* No volume, security, `bputil`, `kmutil` or installed-m1n1 change.
* Installed boot021 and the clean client pin `57a9339` stay unchanged.
* No automatic retries. **Stage 2 can reset the SoC**: power off and restart
  after any `LINK LOST`, `NOT RESTORED` or `STOP:` line.

## Why

Attempt 14 (boot033) reached native PID 1, then the SoC reset silently about
5.6 s after Linux's genpd `sync_state` powered off the unclaimed boot-on PMGR
domains (Likely trigger, **not proven**). Boot034 tests that inside Linux with a
500 ms release ladder. The m1n1 proxy can ask the same question **one domain at
a time, in seconds, without building or booting a kernel**.

What it can tell us:

* **Stage 1 (read-only):** which PMGR domains exist, which are on right now,
  their parents, flags (`critical` = always-on, `notify_pmp`, virtual) and what
  uses them. The sanitized macOS ADT export in the repo
  (`hardware/adt/adt-sanitized.json`, the same PMGR table) has **661** device
  records: 338 virtual (no register), 323 with a power-state register, of which
  118 are flagged critical and 205 are not, and 33 of those 205 are
  `notify_pmp`. Expect the same from the lab ADT. (The Stage-B DT's 188 domains,
  34 always-on, 152 unclaimed, 27 `notify_pmp` count the domains the DT models, a
  different population, so they need not match.)
* **Stage 2 (writes):** whether powering a named domain off, and back on, with
  the same register sequence m1n1 itself uses, resets the SoC or drops the link,
  and **which domain**.

What it cannot tell us (state this when reporting):

* m1n1's sequence is not Linux's. There is no PMP report, no clock or reset
  sequencing and no genpd parent accounting. **No reset here does not clear a
  domain** for Linux; a reset here is a finding about that domain, not a
  reproduction of attempt 14.
* A reset only says the link dropped. The M5's screen (restarted to Macintosh HD
  or frozen) says which.

## Offline readiness (M1)

1. `git pull --ff-only`, stopping on divergence.
2. With no device attached:

   ```sh
   python3 -I native/probe/test_pmgr_probe.py
   tools/m1n1-client/run.sh -c "import sys; sys.path.insert(0, 'third_party/m1n1/proxyclient'); import m1n1.adt, m1n1.proxy, m1n1.tgtypes, construct, serial; print('imports PASS')"
   tools/m1n1-client/run.sh native/probe/pmgr_probe.py --help
   ```

   Expect `Ran 85 tests ... OK`, `imports PASS` and the help text. The test file
   plants 22 deliberate bugs in the tool and requires the other tests to catch
   each one, and it runs the refusal rules against the real 661-record t6050
   table (skipped with a reason if `hardware/adt/adt-sanitized.json` is absent);
   record the counts and any skip you see.
3. Publish sanitized readiness in `progress.md` and `coordination.md` with live
   checks NOT RUN. Tell the human when ready.

## Stage 1: read-only table (one short session)

The human starts **iLinux Boot Lab → Continue**, then `Running proxy...`. Both
Macs on power, same direct cable. Film the M5 screen.

```sh
mkdir -p build/native-intake
tools/m1n1-client/run.sh native/probe/pmgr_probe.py read \
  --device auto --confirm PMGR-PROBE-J716C-READ \
  --json build/native-intake/pmgr-stage1.json 2>&1 | tee build/native-intake/pmgr-stage1.txt
```

* It sends **no write request of any kind** (it does not even build ProxyUtils).
  The target's console text is not shown (it carries the device serial); the
  table is the evidence.
* Expected ending: `Stage 1 finished: read only, no write request was sent.`
  and `Wrote pmgr-stage1.json`, exit 0.
* The table has one row per PMGR device **with a power-state register** (323
  expected; `--show-virtual` adds the 338 virtual ones, and the JSON always has
  them): `ACTUAL`/`TARGET` power state (`ACTIVE` 0xf, `CLKGATE` 0x4, `PWRGATE`
  0x0), `FLAGS` (C critical, V virtual, N notify_pmp, O boot-on flag, P perf) and
  `CYCLE`: `ok` means stage 2 would accept the domain, otherwise the refusal code
  (`crit` always-on, `sys` system-essential by name, `virt` virtual, `trap`
  unreadable, `off` not fully on, `auto` hardware-managed, `link` needed by the
  proxy link, `kids` children still powered).
* The summary line gives the counts. Report them next to the DT-side numbers
  above; a difference is a result, not a failure.

Stage 1 may be followed by stage 2 in the same boot. If you stop here, power off
and return to Macintosh HD.

## Planning stage 2 (no device needed)

Choose domains offline from the stage-1 JSON:

```sh
tools/m1n1-client/run.sh native/probe/pmgr_probe.py plan ISP --from-json build/native-intake/pmgr-stage1.json
```

It prints `PLAN <name> ...` for each domain it would power-cycle, or
`REFUSED <name>: <reason>` and exit 3. Names are the ADT names from the table
(case-insensitive). The same check runs again against live registers before any
write.

Suggested first experiments (labels: **Hypothesis**, nothing here is confirmed).
Against the real table with every register ACTIVE, 131 domains would be `ok`, 8
of them `notify_pmp` leaves: `AVD_SYS`, `GFX`, `ISP_SYS`, `JPG`,
`MSR0_ASE_CORE`, `MSR1_ASE_CORE`, `PRORES`, `SCODEC_STREAMING`. The real
`ACTIVE` set in the lab will be smaller; use your stage-1 JSON.

1. **Control:** one `ok` leaf domain that is *not* `notify_pmp` and plays no
   known role in the link (for example a `UART1`..`UART6`, `SPI3` or `FPWM0`;
   not `I2C*`, whose buses may carry the Type-C controllers). Expectation if
   the power-off alone is harmless: `PROBE PASS`.
2. **notify_pmp:** one `ok` domain flagged `N` from the list above. macOS and
   Linux report such domains' state changes to the PMP; this probe does not. A
   delayed reset or link loss only here would support that mismatch as the
   trigger (the PMP report driver in the Asahi tree exists for exactly this and
   has no t6050 entry in our draft DT).
3. Only then more domains, one per run at first.

A parent can only be cycled when its children are already off, so name them
first (`plan GPU_SHADER,GPU`). The probe powers off in the order given, settles
after each, then powers back on in reverse order.

## Stage 2: power-cycle named domains (WRITES)

Only after the human separately approves stage 2 and starts a fresh lab boot.

```sh
set -o pipefail
tools/m1n1-client/run.sh native/probe/pmgr_probe.py cycle ISP \
  --device auto --confirm PMGR-PROBE-J716C-POWER-CYCLE --settle 10 --tail 10 \
  2>&1 | tee build/native-intake/pmgr-cycle-isp.txt
echo "exit $?"
```

* At most **4** domains per run; start with one. `--settle` (1–60 s, default 10)
  is how long each domain stays off; `--tail` (0–60 s, default 10) keeps
  watching the link after the last restore. The default reset lag seen in attempt
  14 was about 5.6 s.
* Every register write is **announced first** (`POWER-OFF <name> ... reg 0x...`),
  so the last line before a loss names the domain. Film the M5 screen and note
  the time of the last line.
* Results:

  | Last line starts with | Meaning | Do |
  |---|---|---|
  | `PROBE PASS` | Every domain was powered off, restored and verified; the link stayed up through every settle and the tail. | Next experiment is fine in the same boot. |
  | `LINK LOST` | The link dropped N seconds after the named domain was powered off. Nothing was restored. | Look at the M5 (restarted or frozen), **power off completely**, report the line verbatim. |
  | `NOT RESTORED` | A domain did not come back to ACTIVE. | **Power off completely**, report. |
  | `Interrupted with ... powered off` | Ctrl-C or a transport error after a power-off; restore requests were sent but not verified. | Power off completely before anything else. |
  | `PLAN REFUSED` | A refusal; nothing was written. | Report the reasons; no retry. |
  | `STOP:` | A gate or transport problem. | Report; no automatic retry. |

* Exit codes: 0 pass, 1 stop, 3 plan refused, 4 link lost, 5 not restored,
  130 interrupted (argparse errors exit 2).

## What the tool refuses

Stage 2 writes only to domains you name, and refuses (zero writes, whole run)
when any named domain is: unknown or ambiguous (the real table has two devices
named `APCIE_PHY_SW`); virtual (no register); flagged critical (always-on);
**system-essential by name**: CPU cores `MCPUn_m`/`PCPU_n`/`ECPU*`, cluster
managers `MCPMn`/`PCPM`, and `AIC*` (the ADT does not flag these critical; the
display and accelerator `*_CPU` domains are not matched); unreadable; not fully
on; auto-enable, reset or device-disable bits set; in the **link closure**
(UART0 and every `ATCn_USB`/`ATCn_USB_AON` plus all their parents, the set the
m1n1 hypervisor keeps on for its own link; 19 domains in the real table); a
parent with children that are still powered (including virtual critical
children); named twice; or the 5th domain of a run.
With no UART0/ATC device in the ADT it refuses everything (the link dependency
is unknown). `--die` selects another die when `die-count` > 1.

## Always

* **Stop on SError, hang or reset:** power off and return to Macintosh HD. No
  retries.
* Logs and media stay local in ignored `build/native-intake/`. Commit only
  sanitized excerpts: no serials, MACs, raw ADT or memory dumps. The tool prints
  no device path and no serial; check your terminal capture before sharing.
* Report literally: the command, the exit code, the last printed line, the
  screen state (restarted to Macintosh HD, frozen, or untouched) with the video
  time. Mark anything unobserved NOT OBSERVED.
