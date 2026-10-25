# 31AD Recovery paste workflow — offline tooling, no new boot ready

The user cannot keep the Recovery browser and Terminal open together. Each phase
must therefore be copied in full, the browser quit, Terminal opened and the block
pasted once. No phase depends on variables/functions surviving a reboot or a
previous shell. These tools **render and test that workflow offline**. They do
not grant authorization, stage host files, or make 31AD ready to install.

Apple's documented path is shutdown → hold power → Options → Continue → required
authentication. Inside Recovery, choose **Web Browser → Continue**; quit the
browser before choosing **Utilities → Terminal**. [Apple's Recovery guide](https://support.apple.com/guide/mac-help/macos-recovery-a-mac-apple-silicon-mchl82829c17/mac).
Clipboard retention across quitting the browser is **NOT RUN**, not promised by
that guide. First copy this harmless smoke-test block, quit the browser, open
Terminal and paste:

```sh
printf '%s\n' ILINUX_CLIPBOARD_OK
```

If that works, reopen the browser and copy the complete phase. If not, stop and
report the clipboard behavior instead of manually typing a long script. Native
browser/clipboard/Recovery execution of these new tools remains **NOT RUN**.

## Read-only diagnosis renderer

`render.py` takes a reviewed JSON profile with schema `ilinux31ad-diagnose-v1`
and exactly three `images`: `flat31ac`, `nested31ad`, `rawboot021`. Every image
requires integer `bytes`, lowercase `sha256` and HTTP(S) `url`. Historical 31AC
and boot021 pins are fixed; the original nested image needs its actual reviewed
pin. **No example with dummy pins is supplied or native-ready by default.**

Run only the renderer and its tests in the project workspace:

```sh
python3 -I tools/recovery31ad/test_render.py
python3 -I tools/recovery31ad/render.py --profile build/reviewed-profile.json --output build/new-recovery-page
```

The generated HTML exposes one complete Bash block. It downloads **data only**
into a fresh private `/tmp` directory, verifies each exact image immediately
before parsing that same resolved pathname, and calls only `kmutil inspect`.
Explicit nonexistent auxiliary/system paths prevent default collection lookup.
It records actual tool hash, Recovery product/build, pinned input/argv, separate
stdout/stderr and exact exit for each control. An inspector exit zero is not
installer acceptance; rejection is retained and the next control still runs.
No disk/policy guard or temporary Startup Disk change is needed for read-only
file parsing. No script is downloaded/executed, no `curl | bash`, no configure,
no reboot. Keep raw output private; publish only reviewed sanitized metadata.
The raw boot021 negative control is parsed as data, never used as a candidate.

The M1 should serve only the reviewed original package/page directory, never a
repository, personal directory or private research tree. Local network addresses
are configured in a private rendered profile and must not enter the public repo.

## Writes remain disabled

`rollback-scaffold.sh` is an independent self-contained review scaffold with a
literal default-deny gate. Running it exits 78 **before any guard or host tool**.
It is not a paste instruction and must not be relabeled by changing one switch.
A future qualified/authorized rollback block must preserve its exact lab identity,
build, helper/boot021 hashes, paired 1TR, Full/Permissive guard and tty handling.

The unreachable scaffold illustrates full combined configure output capture,
the complete `PIPESTATUS` array to preserve configure/capture exit codes, exact pre-call input hash
and argv, and fresh postcheck. Apple's interactive confirmation explicitly reads
`/dev/tty` so it cannot consume the pasted heredoc script. It never retries,
changes security or reboots. Rollback uses the pre-existing exact boot021 file,
not a prior phase variable or network download. No install block is rendered:
the actual fileset cause and a new installation test remain unqualified.

## Operational-phase renderer — still review/approval gated

`write_render.py` now renders a separate self-contained **install** block and
independent **rollback** block from a strict reviewed profile. This supersedes
the earlier statement that no install block can be rendered, while the historical
`rollback-scaffold.sh` remains deliberately disabled. Rendering is an offline
preparation operation, not installation qualification or human authorization.

The write-profile schema is `ilinux31ad-write-v1`, with exactly one `candidate`
object containing `bytes`, `sha256`, and `url`. Geometry must match the corrected
196608-byte original nested image; use its actual reviewed hash and artifact URL.
No profile or production paste block with dummy pins is shipped by default.

```sh
python3 -I tools/recovery31ad/test_write_render.py
python3 -I tools/recovery31ad/write_render.py --profile build/reviewed-write-profile.json --output build/new-reviewed-write-page
```

The HTML page has a complete-block selection button for each phase. Copy only
the current phase, quit browser, open Terminal and paste once. Installation
downloads data into private Recovery `/tmp`; rollback does not download anything
and can run after a reboot with no prior variables. Each phase redefines the
entire exact lab identity/build/helper/boot021/Full-Permissive/paired-1TR guard.

Install binds/hashes the **same resolved readonly candidate pathname** passed
to configure immediately before invocation, and privately records actual argv,
input size/hash, Recovery build and kmutil hash. There is no raw candidate flag
or fallback. Rollback uses only the existing immutable boot021, entry 2048/VA0.
Configure reads `/dev/tty`, while the full combined stdout/stderr stream is
retained and displayed through `tee`. Both pipeline statuses and the fresh
policy postcheck's numeric exit are preserved. Only successful configure,
capture and postcheck produce an explicit success marker. Errors return the
actual configure exit (e.g. 71), capture failure returns 74, and postcheck failure
returns its numeric exit. There is no automatic reboot, retry or security change.

**Only run generated phases after independent M1 review and a new explicit human
approval of the exact candidate and full replacement/observation/rollback plan.**
The old 31AC authorization is not a new-image installation grant. A failed
configure is not assumed atomic: no diagnostic boot, changed flags or retry.
Use the independent rollback only while its fresh guard passes. Native execution
of the new blocks, full output capture in Recovery, and clipboard retention remain
**NOT RUN**. The offline tests use private fixture paths and stubs, not real host
kmutil, policy, disk or network commands.
