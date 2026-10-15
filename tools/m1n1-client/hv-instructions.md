# HV sessions: hv003 chainload ladder (then boot033/boot034 under the hypervisor)

**M5 handoff, 2026-10-14: hv003.** Read `native/hv/README.md` and
`native/hv/hv002-chainload-analysis-2026-10-14.md` first. Private tooling:
never send any of it upstream. **Native/HV live checks NOT RUN at this handoff.**
Every session is RAM-only and human-started.

* Keep Macintosh HD as default at Full Security.
* No volume, security, `bputil`, `kmutil` or installed-m1n1 change.
* Installed boot021 and the clean client pin `57a9339` stay unchanged.
* No automatic retries. **Power off and restart between sessions**: only one
  chainload can happen per boot of the installed m1n1.
* hv001 and hv002 are superseded. Do not run them.
* This ladder is independent of the boot034 / attempt 15 native test
  (`stage-b-instructions.md`); the human picks the order, and every rung is its
  own boot.

## Why hv003

hv002 passed every preflight, then never came back from the chainload
(`hv002-session2-2026-10-14-result.md`). The M5 review found two things:

1. **A probable cause (Likely, not hardware-confirmed):** our copy stub kept
   its 64-bit entry literal at an offset that is 4 mod 8, and the stub runs
   with the MMU off, where an 8-byte load from Device memory at that address
   faults. Upstream's assembler pads its literal pool; ours did not. hv003's
   stub is padded, assembled with clang and run through an instruction emulator
   in tests.
2. **A procedure that differed from Asahi's own:** we relocated six blobs and
   rebuilt the whole ADT in Python (a first on t6050). hv003 does what the
   in-tree stage-1→2 chainload does: it moves only SEPFW and patches that one
   ADT property's 16 bytes in place, with a layout gate in front of every write.

The next silent hang can no longer be silent: a **breadcrumb strip** is painted
into the top-left corner of the M5's screen (details below).

## Offline readiness (M1)

1. `git pull --ff-only`, stopping on divergence. Verify the file hashes in
   `native/hv/README.md` against your checkout.
2. Download release `native-j716c-hv003` asset `ilinux-j716c-hv003.tar.gz`
   and verify its SHA-256 against `native/hv/README.md` **before extracting**
   into a fresh `build/native-hv003-download/` (that yields
   `build/native-hv003-download/ilinux-j716c-hv003/`). Keep your existing
   `build/native-boot033-download/` and `build/native-boot034-download/`.
3. With no device attached:

   ```sh
   python3 -I native/hv/test_adt_patch.py
   python3 -I native/hv/test_hv_chainload.py
   python3 -I native/hv/test_crumb.py
   tools/m1n1-client/run.sh native/hv/test_hv_launch.py
   python3 -I native/boot/test_launcher.py
   tools/m1n1-client/run.sh -c "import sys; sys.path.insert(0, 'third_party/m1n1/proxyclient'); import m1n1.hv, m1n1.bootmem, m1n1.tgtypes, m1n1.proxyutils, construct, serial; print('imports PASS')"
   tools/m1n1-client/run.sh native/hv/hv_launch.py --package build/native-boot034-download/ilinux-j716c-boot034 --hv-package build/native-hv003-download/ilinux-j716c-hv003
   tools/m1n1-client/run.sh native/hv/hv_launch.py --package build/native-boot033-download/ilinux-j716c-boot033 --hv-package build/native-hv003-download/ilinux-j716c-hv003
   ```

   Expect all suites OK (the README lists the M5's counts: 10, 168, 76, 13, 37;
   record yours). `test_crumb.py` and the stub tests need `cc`, `clang` and
   `otool`; the package round-trip tests skip with a stated reason when no
   local build matches, so record any skip. Then `imports PASS`, and for both
   guests `Package PASS` with `OFFLINE ONLY`.
4. Publish sanitized readiness in `progress.md` and `coordination.md` with live
   checks NOT RUN. Tell the human when ready.

## The ladder (stop at the first failing rung and report)

All live commands need `--launch --device auto --confirm HV-J716C-RAM-DIAGNOSTIC`
and the human's start (**iLinux Boot Lab → Continue**, then `Running proxy...`).
Film the M5 screen, **including the top-left corner**, from before the launch
until the session ends. Both Macs on power, same direct cable.

| Rung | Command (after the common arguments) | Writes to the target | Purpose |
|---|---|---|---|
| 1 | `--layout-only` | none (two m1n1 heap-bookkeeping requests) | Prints the planned region and gates against the live layout; first parse of the real ADT. |
| 2 | `--chainload-only` | RAM only | Chainload hv003 (with breadcrumbs), verify it, stop. |
| 3 | `--chainload-only --control stock` | RAM only | Only if rung 2 fails: chainload the installed boot021 binary as a control. |
| 4 | *(none: full run)* | RAM only | Chainload, start the hypervisor, boot the guest at EL1. |

Full command, rung 2 as the example (replace the mode flag for the others):

```sh
set -o pipefail
tools/m1n1-client/run.sh native/hv/hv_launch.py \
  --package build/native-boot034-download/ilinux-j716c-boot034 \
  --hv-package build/native-hv003-download/ilinux-j716c-hv003 \
  --launch --device auto --confirm HV-J716C-RAM-DIAGNOSTIC \
  --chainload-only 2>&1 | tee build/native-intake/hv003-rung2.txt
echo "exit $?"
```

The launcher prints only its own sanitized lines (the target's console bytes are
no longer echoed), so the terminal capture above is the record. `--log` belongs
to the full run only (rung 4), takes a **new** file name in an existing,
writable directory every time (an existing path, a dangling symlink, a missing
or unwritable directory and an over-long name are refused up front), and is
created before the first write to the target.

### Rung 1: `--layout-only`

* No memory writes, like the census (ProxyUtils itself issues two m1n1
  heap-bookkeeping requests, `heapblock_alloc(0)` and `heapblock_set_limit`).
  It prints a sanitized table: m1n1 base, the planned destination region,
  SEPFW, the ADT, boot_args and framebuffer ranges, the video geometry, the
  blobs that would be overwritten (NOTES), the current and new
  `top_of_kernel_data`, and `LAYOUT PASS` or `LAYOUT FAIL` (exit 0 or 3).
* A raw-ADT parse error here (`ADTError`) is itself a result: the launcher
  stops before any write. Report it literally.
* The framebuffer lines say what the screen can show: `breadcrumb strip
  eligible for the host`, `stub bar will paint`, and `new m1n1 will paint (its
  guard ...)`. If the last is `no` (stride above 0x10000, height above 0x4000, or
  a geometry the stub refuses) only the stub's slot 3 and bar can appear; if
  `new m1n1 paints only c0-c8 (slots 5-13)` is printed (framebuffer base not 16K
  aligned), do **not** expect c9 to c15 and read the strip accordingly.
* Record the whole table. **`LAYOUT FAIL` ends the ladder**: report it, M5
  adjusts the plan. NOTES are not failures, but copy them verbatim.
* Rung 1 writes nothing, so rung 2 may follow **in the same boot** once the
  table is recorded and you have read the NOTES. Any rung that writes (2, 3, 4)
  needs a power cycle after it.

### Rung 2: `--chainload-only`

Expected output, in order: `Package PASS`, `Mode: LIVE CHAINLOAD ONLY`,
`Target PASS`, `Register preflight PASS`, `Chainload mode: in-tree`, the layout
table and `Layout gate PASS`, `Breadcrumbs: stub bar enabled`, `Staged and
verified`, `Copy stub written and verified`, `Live ADT patched ... and
verified`, `Handoff. Screen strip: ...`, `Chainloaded hv003 into RAM`,
`New-instance proof PASS`, `Target PASS: hv003 running`, and finally
`CHAINLOAD PASS` with exit 0: the new m1n1 answered on USB, reported the hv003
marker, and its boot_args pointer is the copy the launcher staged. The
hypervisor was **not** started. Power off afterwards.

Reading the screen if it does not pass (top-left strip, 21 slots left to right):

| Screen | Meaning |
|---|---|
| Nothing lit; restored Apple logo frozen | The host never reached the handoff, boot021 faulted during its own shutdown, or the stub faulted before its entry mark. Compare with the launcher's last printed line. |
| **Slot 3 only** (the fourth block; slots 0–2 may also show) | The stub was entered but its copy loop, clear or bar did not finish. |
| White **bar** only (slots 0–4) | The stub ran and jumped. The new m1n1 died before `c0`: in `_start` (relocation, `pan_fixup`). |
| Bar + *k* separate blocks | The new m1n1 completed steps `c0`…`c(k-1)` and died in the next one (table below). |
| Bar + all 16 blocks, m1n1 logo/console shown | m1n1 reached its normal console; if USB still did not return, the problem is after `fb_display_logo` (USB init). |
| Few blocks at the far right only | `display_init` cleared the framebuffer after `c13`; read the lit ones as `c14`/`c15`. |
| Screen goes black or the Mac restarts to the boot picker | A reset (watchdog, fault), not a hang. Say so; a frozen strip and a frozen logo are hangs. |

| Block | Step completed | Next step (where it died if this is the last lit block) |
|---|---|---|
| c0 | `_start_c` entered | bss clear, boot_args copy, first ADT walk (`/cpus`) |
| c1 | bss, boot_args copy, first ADT walk | `uart_init`, `dockchannel_uart_init` |
| c2 | uart + dockchannel init | `get_device_info`, `init_cpu` |
| c3 | device info, CPU init | `dump_boot_args` |
| c4 | boot_args dump | `exception_initialize` |
| c5 | exception init (end of `_start_c`) | `firmware_init` |
| c6 | firmware init | `heapblock_init` |
| c7 | heap | boot-policy print, `usb_enable_debugusb` (only when the policy asks; it waits 1 s by design), `gxf_init`, `mcc_init` |
| c8 | gxf / mcc | `mmu_init` |
| c9 | MMU (framebuffer mapped Normal-NC; skipped when its base is not 16K aligned) | `aic_init` |
| c10 | AIC | `smp_init` |
| c11 | SMP init (ADT bookkeeping only; no CPU is started) | `wdt_disable` |
| c12 | WDT disabled | `pmgr_init` |
| c13 | PMGR | `display_init`, `display_shutdown` |
| c14 | display | `fb_init`, `fb_display_logo` |
| c15 | framebuffer console up | `run_actions`, USB |

The host also paints slots 0–2 as it progresses, but boot021's own redraw
erases them at the handoff, so **only the stub's slot 3 and bar are
authoritative** after a handoff. Slots 0–2 matter only if the host stalls before
it (then they show on screen and in the launcher output). Slot 2 means
"everything staged; about to patch the live ADT and hand off".

Launcher lines that need an action. An ordinary failure ends the run as one
`STOP: <Class> <text>` line, so match the text anywhere in the line. The
target's console text is **not** shown by design (it carries the device serial);
the launcher's own lines and the screen strip are the evidence:

| Line (contains) | Meaning | Do |
|---|---|---|
| `layout gate FAILED, nothing was written:` | A gate refused before any write. Reasons include a destination over the ADT or framebuffer, a second chainload in one power cycle, a staging block below `top_of_kernel_data` or over the source of the SEPFW blob. | Report it verbatim; power off. A line about a second chainload means the power cycle was skipped. |
| `log file exists`, `log directory ...`, `log file name is too long` | `--log` was refused at argument time (exit 2), before anything else happened. | Choose a new name in an existing, writable directory. |
| `live ADT patch failed and was restored and verified` | The 16-byte patch did not land cleanly and the original is back. | Report; power off before anything else. |
| `live ADT SEPFW patched and NOT restored: POWER OFF completely` | The live ADT still carries the patch. | **Power off completely.** Report. |
| `reload() did not reopen the port` | The handoff was issued; the launcher now runs its own descriptor-checked reconnect (up to 30 s). | Wait. If it ends with `m1n1 did not answer after chainload`, read the strip, film it, power off. |
| `new-instance proof FAILED` | An m1n1 answered but it is the original instance (or reports another pointer). | Report both pointers; power off. |
| `USB identity check failed (<Class>)` / `USB transport failed (<Class>)` | No port opened, or it failed. | Do not retry automatically; check the cable and report. |
| `STOP: TimeoutError` | The 300 s preflight alarm fired. | Report the last printed line; power off. |

Always report the exit code and which slots were lit (with the video time).

### Rung 3: `--chainload-only --control stock`

Chainloads the installed boot021 binary through exactly the same code. If
this returns (`CHAINLOAD PASS`) and rung 2 did not, the problem is in the hv003
build; if it also fails, the chainload mechanism or early re-init on t6050 is at
fault. The stock build paints no `c`-blocks, so success on the screen is the
bar alone, and the launcher's evidence is `New-instance proof PASS` plus
`CHAINLOAD PASS`.

### Rung 4: the full run

Only after rung 2 passes and the human separately starts a new boot:

* Terminal A first: `tools/m1n1-client/run.sh native/hv/vuart_log.py --log build/native-intake/hv003-vuart.log`
* Terminal B: the command above **without** `--chainload-only`.
* Pass signals, in order:
  1. `Target PASS` (boot021), `Register preflight PASS`, layout gate PASS;
  2. `Target PASS: hv003 running` and `HV PASS: single-CPU mode, ECV timer traps on`;
  3. `Hardware DT PASS`, `Starting EL1 guest`;
  4. kernel lines on the vUART with advancing printk times, then `PID 1 reached`
     and `[diag] heartbeat` lines.
* Ctrl-C once in terminal B enters the HV shell. Run `bt`, record the symbolized
  frames, Ctrl-D resumes.
* Stop on `STOP:`, an EL2 exception, a guest panic, a reset, or 120 s after
  `Starting EL1 guest`. If printk times stop advancing right after the first
  timer interrupt, Ctrl-C, `bt`, then stop (see the ECV-trap risk in the README).
* With the boot034 guest, `ilinux-genpd:` lines (power-offs and the release
  ladder) also stream to the vUART.

## Always

* **Stop on SError or hang:** power off and return to Macintosh HD. No retries.
* Logs and media stay local in ignored `build/native-intake/`. Commit only
  sanitized excerpts: no serials, MACs, raw ADT or memory dumps.
* Report literally: the launcher output, the exit code, and the screen strip
  (which slots were lit) with the video time. Mark anything unobserved NOT OBSERVED.
