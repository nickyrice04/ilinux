# 31AL read-only snapshot diagnostic renderer

This is original MIT code for diagnosing the first guarded admission snapshot
that stopped 31AK. The observed 31AK capability pass followed by an admission
snapshot refusal does not identify the refusing branch. This workflow collects
that missing evidence. It is not another install attempt and does not establish
that the firmware, boot object, CPU adapter or GPU works.

`render.py` returns inert text through `render(value)` and an inert, single-box
HTML page through `page(value)`. It never executes the rendered block or serves
a page. The caller must supply the strict existing
`ilinux31aj-recovery-profile-v1` profile with the new diagnostic helper's exact
byte count and SHA-256. Candidate and boot021 entries remain pinned identity
metadata in that profile; their files are neither needed nor copied here.

The fixed future kit is
`/Volumes/iLinux Boot Lab - Data/Users/Shared/iLinuxBoot/31al-diagnostic`.
It contains only `profile.json` and `ilinux31aj-reader`. The package controller
owns its offline preparation and any separately authorized future staging.
Rendering or testing this module does not stage it. The legacy helper filename
is required by the unchanged strict profile/self-identity loader.

The renderer hash-verifies the frozen 31AK renderer before compiling it. That
renderer independently verifies its frozen 31AJ dependencies. This module
reuses only the strict profile validation and the canonical, held-CWD identity
guard. It never calls either frozen install or restore renderer. Its new scratch
prefix is `ilinux31al`; cleanup is narrowed to its three known scratch files.

## Intended diagnostic sequence

Only a separately reviewed and explicitly authorized Recovery invocation may
use the generated block. No invocation was run on this host or in Recovery while
developing this module.

1. Require a root shell and the fixed, distinct, nonsymbolic mounted lab and
   original System paths. Check the exact profile and helper pins.
2. Create one private scratch directory. Resolve its physical name, check root
   ownership and mode 0700, enter it and bind both its name and the kernel-held
   working directory to the original device/inode identity. The alias layout
   `/private -> System/Volumes/Data/private` is handled by canonicalization;
   paths containing symbolic components are not sent to the helper.
3. Copy only the verified profile and helper into the scratch directory. Recheck
   their pins. Bind the working directory again before opening a new capture
   file with noclobber semantics.
4. Invoke the pinned helper once with
   `--diagnose-snapshot --target-volume LAB --original-volume ORIGINAL --profile P`.
   Its stdout goes to the scratch capture; stderr is suppressed. Record only its
   bounded exit status in a fixed shell record.
5. Recheck directory identity. Reject missing, symbolic, nonregular or empty
   output. Run the same helper's `--validate-diagnostic FILE --profile P` mode.
   This validator accepts at most 8192 bytes, rejects unknown fields and values,
   and reprints only its canonical allowlisted finite diagnostic record. The
   block never displays a raw capture with `cat`, raw stderr, paths, policy
   values, unknown object hashes or identifiers.
6. Display that validated record in Terminal **before cleanup**. Capture its
   visible text or a photograph before leaving Terminal. Cleanup removes only
   the three known scratch files while the original directory identity still
   matches. If its named directory is replaced, cleanup stops rather than
   touching a different directory.

The diagnostic helper contract is documented in
[`../boot-object31al-native/README.md`](../boot-object31al-native/README.md).
Its `ilinux31al-snapshot-diagnostic-v1` record can distinguish command capture,
parsing, volume/Recovery identity and policy/admission guard failures without
printing private metadata. A valid refusal has diagnostic exit 2; a passing
initial admission has exit 0. Its validator returns 0 for either valid record.
An unexpected child exit is displayed and remains a stop even if a structured
record can be validated.

The separate `ilinux31al-shell-diagnostic-v1` record has fixed fields:
`schema`, `stage`, `helper_exit`, `read_only`, `writes_authorized`, `native_ready`,
`identifiers_returned` and `policy_values_returned`. `helper_exit` is null or
0–255. Its finite `stage` values are:

| Stage | Meaning |
| --- | --- |
| `INPUT_BINDING` | Root, input path, source-file or exact pin check refused. |
| `WORK_BINDING` | Scratch directory creation, ownership/mode, identity, copy or binding check refused. |
| `OUTPUT_OPEN` | Creating the new capture failed; the diagnostic child did not run. |
| `HELPER_EXIT` | Child exit status; an unexpected value or interruption remains a stop. |
| `OUTPUT_MISSING` | Capture missing, empty, symbolic or not a regular file. |
| `VALIDATOR_FAILED` | The capture or its validation was refused. Raw contents remain hidden. |
| `DIAGNOSTIC_CAPTURED` | The bounded allowlisted native record was shown successfully. |

These stages isolate the shell boundary that 31AK did not expose. They do not
identify the internal native branch; only the native record can do that.

No block contains `kmutil`, `bputil` write commands, enrollment, comparison-key
generation, snapshot-value extraction, a persistent state/baseline directory,
candidate installation, boot021 restoration, default selection, a security
change, or a native boot. Temporary scratch files are the only writes made by
the diagnostic shell. A passing diagnostic does not authorize any subsequent
operation or claim native readiness. Existing boot/default/restoration state
remains unconfirmed by this workflow; return to Macintosh HD/default and report
the safe output for review rather than retrying an install or restore.

## Offline checks

After the complete 31AL source inventory and local two-file kit have been
verified, prepare a new page directory from the repository root:

```bash
python3 -I tools/recovery31al/package.py --prepare --kit build/ilinux-31al-diagnostic --output build/31al-diagnostic-page
python3 -I tools/recovery31al/package.py --page build/31al-diagnostic-page/recovery.html --check-only
```

The output directory must not exist. The first command creates inert text, HTML,
the canonical public profile and a preparation receipt below workspace `build/`.
The second verifies the exact rendered page and complete source closure without
opening a socket. Neither command stages files on lab Data or executes the
Recovery diagnostic. The profile and helper are the exact local artifacts listed
in the public delivery record; no candidate or boot021 is transferred.

A future lab-Data copy is a separate `package.py --stage --kit ...` invocation
requiring explicit lab-Data staging authorization and local administrator
authentication. Preparing, checking or serving a page never invokes it. This
module adds no automatic staging, install, restoration or boot step.

Run the renderer and staging fixture suites from the repository root:

```bash
python3 tools/recovery31al/test_render.py
python3 tools/recovery31al/test_stage.py
```

The 19 tests run generated Bash only against disposable workspace fixtures and
synthetic fake commands. They exercise the real filesystem alias and held-CWD
behavior, input pins, wrong ownership/mode, named-directory replacement,
noclobber/redirection failures, empty, missing or symbolic output, a killed
diagnostic child, unexpected child exit,
malformed/private/unknown-field/oversized captures, stderr suppression, both
diagnostic outcomes, immutable imports, Bash syntax and the inert single-box
HTML. The fixture contains no candidate or boot021 file and never creates
transaction state. Real native diagnostic parser/validator tests belong to the
native helper suite; these fakes do not validate actual Recovery or hardware.

The 24 staging tests use disposable workspace targets and an injected synthetic
backend. They retain the frozen original target metadata policy and guard, and
test the exact two files, private modes, current original installation, lab Data
role/group/container, FileVault refusal, no overwrite, source hashes and held
file identity, repeated source closure, before/after target identity, named
base/destination replacement, partial-write cleanup and preservation of foreign
files and all older kits/state. `stage_kit` requires already-admitted controller
functions rather than importing a mutable controller path; an unverified
`package.py` fixture is never executed. The production live backend is never
constructed by these tests. The implementation is ready for separate review;
no production staging invocation is claimed.
