# 31AD: M1 review and the one-paste Recovery sequence

**PREPARATION AND REVIEW ONLY.** Do not run any Recovery write command because
this document exists. The agents prepare and review; the human operates the M5.
These are never M1 boot-policy commands. A write happens only after (1) the
isolated-VM candidate is built and independently reviewed, (2) M1 publishes a
sanitized offline review, and (3) the human gives a **fresh** explicit approval
of the exact 31AD candidate — the 31AC approval does **not** carry over.

31AD reorders the frozen 31AC payload to satisfy the Mach-O split-protection
ordering invariant and wraps it in a nested fileset. The motivating root cause
(31AC exit 71) is a **Hypothesis, not a diagnosis**; read
[`research/native31ad-fileset-ordering.md`](../../research/native31ad-fileset-ordering.md)
and [`native/boot/attempt31ad/manifest.json`](../../native/boot/attempt31ad/manifest.json)
before the sequence below.

## 1. Freeze and review the offline package (available now)

Preserve local changes; `git pull --ff-only` and record the exact reviewed
commit. This package is at delivery status `PENDING_VM_LINK`: the candidate image
and archive are **not yet built**, so review the source, tooling and hypothesis
now, and review the candidate as separate M5 VM evidence when it exists.

Using existing M1 tools, from the repository root:

```sh
python3 -I kernel/experiments/bootimage31ad/test_ordered.py
python3 -I kernel/experiments/bootimage31ad/test_image.py
python3 -I tools/recovery31ad/test_render.py
python3 -I tools/recovery31ad/test_write_render.py
python3 -I kernel/experiments/omarchy-kconfig/test_kconfig_fragment.py
python3 -I kernel/experiments/visible31ad/run.py \
    --output build/31ad-visible-m1-review --cc clang \
    --target aarch64-none-elf --compile-only
```

Expect 75 packaging/renderer methods PASS and five AArch64 objects
(`COMPILE_PASS_NOT_LINKED`). Compare the recorded `source_bindings_sha256`
(`ac5b7fcca628ff7fcec720dfcfefb537d0766ace161531cd47fed40c1ea8fcca`) and confirm
the reused `visible31ac` / `observer31ab` sources are byte-identical to their
frozen 31AC/31AB pins. Confirm the ordering guard rejects both flat root types
and the unordered nested control:

```sh
python3 - <<'PY'
import json, pathlib, importlib.util
spec = importlib.util.spec_from_file_location("v", "kernel/experiments/bootimage31ad/validate_ordered.py")
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
print("range_check API present:", hasattr(v, "range_check"))
PY
```

On an M1 without an ELF linker/QEMU, record the two-base link, the 26 runtime
cases, the ordered-image generation and `validate_ordered.py` on the real image
as **NOT RUN on M1**, and review them as separate M5 VM evidence once produced.
Do not install tools to fill that gap or treat the Mach-O parser/guard as a boot.
Report the exact commit, hashes, commands, tool versions, actual outcomes and
actionable findings.

## 2. Review the candidate when the VM link completes (pending)

The real candidate comes only from the isolated VM
(`virtualization/jobs/088-ordered31ad/run.sh`): `visible31ad/run.py` links
`payload.bin`, `visible31ad-test/run.py` runs the 26 QEMU cases, and
`bootimage31ad/ordered.py` wraps the linked payload into the 196608-byte image.
When that evidence is published, verify offline:

* `validate_ordered.py <image> --payload <payload.bin>` PASS, and both parsed
  headers satisfy `__TEXT_EXEC.fileoff <= __TEXT_BOOT_EXEC.fileoff`;
* the inner payload bytes equal the linked payload after the reserved header page;
* the image is exactly 196608 bytes, and its SHA-256 matches the manifest once
  the manifest is pinned.

Only after this does a write profile carry a real pin. There is no dummy profile;
the renderers refuse one.

## 3. The one-paste Recovery model

The M5's Recovery does not allow the Web Browser and Terminal to stay open
together, which caused manual-transcription errors in 31AC. 31AD therefore uses
**self-contained one-paste blocks**: each phase is copied in full, the browser is
quit, Terminal is opened, and the block is pasted **once**. No phase depends on a
variable, function or PASS surviving a browser quit or a reboot — each block
redefines its own guard, pins and handling. The pages are produced by
`tools/recovery31ad/` and **must not be hand-typed**.

First, with the human in the lab's paired Recovery (shutdown → hold power →
Options → Continue → authenticate; **Web Browser → Continue**, then quit the
browser before **Utilities → Terminal**), confirm the clipboard survives quitting
the browser with the harmless smoke test — copy it, quit the browser, open
Terminal, paste once:

```sh
printf '%s\n' ILINUX_CLIPBOARD_OK
```

If `ILINUX_CLIPBOARD_OK` does not print, **stop** and report the clipboard
behaviour. Do not manually type a long block. Native clipboard retention across
quitting the browser is **NOT RUN** and is not promised by Apple's guide.

### 3a. Read-only diagnosis (no write, after approval to run it)

`render.py` builds one page whose single block downloads **data only** into a
fresh private `/tmp` directory, verifies each exact image, and calls only
`kmutil inspect` on the flat 31AC image, the nested 31AD image and the raw
boot021 negative control. An inspector exit zero is not installer acceptance.
This needs the real `nested31ad` pin, so it is produced only after step 2.

### 3b. Authorized install, then rollback (one paste each)

After step 2, M1 review and a fresh human approval, `write_render.py` renders two
independent blocks from a reviewed `ilinux31ad-write-v1` profile:

* **install** — redefines the lab-paired `base_guard` (separate lab volumes,
  build 25G83, verified boot021, original Full / lab Permissive), downloads the
  candidate into a private `/tmp`, re-verifies the **same resolved readonly
  pathname's** size and SHA-256 immediately before a single
  `kmutil configure-boot --custom-boot-object … --volume "$ILINUX_OS"`, captures
  the full combined output through `tee` with `PIPESTATUS`, runs a Full/Permissive
  postcheck, and prints a success marker only when all pass. No `--raw`, no
  entry/flag override, no retry, no automatic reboot. A non-zero configure exit
  (e.g. 71) **stops**; the slot is not assumed untouched.
* **rollback** — independent, needs no download and no prior variable; restores
  the exact immutable boot021 (`3932160` bytes, `ff75f4a9…072664`) with
  `--raw --entry-point 2048 --lowest-virtual-address 0` only while its own fresh
  guard passes. This block is fully determined now.

Render (never run) the production pages, into a fresh directory, from the reviewed
profile:

```sh
python3 -I tools/recovery31ad/write_render.py \
    --profile build/reviewed-write-profile.json \
    --output build/31ad-recovery-page
```

Copy ONE complete block, quit the browser, open Terminal, paste once. The install
and rollback phases are separate pastes; the rollback is copied again after the
reboot. Enter credentials only into Apple's own prompt. Keep raw output private;
publish only reviewed sanitized metadata.

## 4. One bounded observation and return (only if install succeeds)

Only on an install success marker: shut down, hold power, select the lab entry
once, and observe the built-in screen for **30 seconds**. Record whether the
32×16 bordered checkerboard marker appeared, stayed, or never appeared, and any
firmware error separately. The diagnostic parks; it does not restart. Then roll
back with the independent rollback block, shut down, boot **Macintosh HD →
Continue**, and reapply Macintosh HD as the default Startup Disk using the
existing read-only return workflow. Do not leave the lab as default.

## 5. Boundaries and result

An absent marker leaves the cause Unknown (firmware rejection, entry not reached,
profile/input refusal, later fault, or display visibility). A marker proves this
original entry/display path only — not Linux, monitor-service readiness, SMP or
performance. Keep `native_entry_observed` separate from install success. Leave
physical secondary startup, Linux, GPU and performance **NOT RUN**. Record the
reviewed commit, candidate hash, guard/configure/rollback exits, observed screen
outcome and elapsed window; publish no identifiers, raw policy/disk output or
unredacted photographs. On a silent or failed attempt, review the new evidence
before proposing any changed experiment — no retry with altered flags, no new
security downgrade, volume operation, DFU, revive or restore.
