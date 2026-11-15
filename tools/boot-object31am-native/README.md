# 31AM conditional read-only Preboot companion

Original MIT code for the evidenced31AL Preboot-path deployment stop. This is
an offline-built proposal for a later explicitly authorized Recovery check.
No live mount, Recovery, policy query, installation or native result is supplied.

The new companion preserves all frozen31AL files. `build.py` verifies and loads
the exact existing generator and observer inputs. The generator copies original
`core.c`, `json.c` and `reader.h` byte-for-byte and proves observation marks strip
back to exact original `state.c`. New `preboot.c` includes that generated state
translation unit to reuse its private CF/APFS helpers; `result.c` includes the
byte-identical observer. The original collector, strict policy parser and
initial-admission validator remain unchanged.

## Fixed CLI and conditional operation

Default/help are inert. The logical helper filename remains `ilinux31aj-reader`
because the strict original profile/self-identity reader requires it. The new
binary has its own exact hash and separately bound public profile. Its candidate
and rollback identities are unchanged and do not authorize either operation.

- `--preboot-diagnose --target-volume LAB --original-volume ORIGINAL --profile P
  --scratch WORK`: the fixed reviewed Recovery operation.
- `--diagnose-fixture WORKSPACE_PLIST --profile P --scratch WORKSPACE_DIR`:
  workspace-only synthetic metadata, command and mount-state model. It cannot
  dispatch live mount/unmount commands and never asserts physical evidence.
- `--validate-result FILE --profile P`: strict bounded safe-result display.

There is no installation, policy write, full/private snapshot, key generation,
repair, writable remount, force or native boot mode. No source or device override
exists on the live CLI. A local owner must separately authorize future staging,
conditional mounting and any temporary Startup Disk operation before execution.

The live preparation requires root, the model/Recovery environment and fixed
distinct lab/original mounts. It identifies the internal System/Data groups,
container and unique Preboot role through original checks, including UUID and
device consistency. Preboot is shared by the lab and Original in this container;
no unverified `/Volumes/Preboot` name is assumed.

`Mounted` is optional plist metadata. If present, it must be a boolean consistent
with the kernel observation. It is never inferred false merely because absent.
The authoritative mount-table read is bounded and must succeed completely. Known
`/dev/disk`, `/dev/rdisk` and bare BSD names are normalized for comparison;
snapshot-device suffixes count as occupied. An unrecognized APFS source or failed/
truncated table cannot prove absence. An existing valid mount is bound through
a fresh descriptor and kernel source/mountpoint information, then left untouched.

A new mount is attempted only with a string-valued empty mountpoint and positive
kernel absence, followed by a second identity/mount-state observation. Unsafe
paths, missing evidence, contradictions or changed identity remain stops.

The scratch directory must be canonical, nonsymbolic, owned by the effective
user, mode0700 and named `ilinux31am.<random suffix>`. The helper holds its FD,
enters that directory and binds named/held/current-directory identities. It
creates only a new mode0700 `preboot` child; preexisting children are not reused.
The fixed live mount command is:

```text
/sbin/mount_apfs -o rdonly,nobrowse,nofollow /dev/<derived device> ./preboot
```

The source is only the identity-verified device, passed through `execve` arguments
without a shell. The relative target is anchored to the held working directory;
the kernel's `nofollow` option supplies an additional symbolic-link refusal.
The fixed Apple tools must exist; there is no fallback. Direct invocation avoids
the documented Disk Arbitration frontend. This does not claim complete knowledge
of every internal APFS implementation behavior. No filesystem-check or repair
program is requested by this companion.

After the command, fresh metadata must preserve identity and report the exact
owned mountpoint. A newly opened post-mount FD, rather than the retained
underlying-directory FD, verifies the kernel APFS source/mount-on path and
`MNT_RDONLY`. Only then may the unchanged collector/initial validator run once.
The collector itself still verifies paired1TR, Original Full Security and all
existing policy/object constraints. Preparation alone does not establish those.

## Cleanup and truthful failures

The underlying pre-mount child FD is retained for checking the directory after
unmount. Every post-mount FD is closed before the unmount request. Only a newly
created mount whose current identity, source, location and read-only flag can
still be verified may receive `/sbin/umount ./preboot`, without force or retries.
Existing mounts are never unmounted. A writable/unverified view or changed
binding remains untouched with an explicit uncertainty/refusal result.

Nonzero mount and unmount exits are followed by fresh observation: a command can
fail after changing mount state. An observed partial mount can be cleaned only
under the same owned/read-only checks. Even a nonzero unmount that demonstrably
removed the mount remains an overall refusal; its known cleanup is reported.
The child is removed only after fresh absence plus underlying-directory identity.
No recursive deletion occurs. Failed or uncertain cleanup overrides overall pass.

Caught INT/TERM/HUP prevent further diagnosis and make the result a refusal;
cleanup is attempted after the current bounded original operation returns.
Uncatchable termination or power loss can leave a mount until Recovery shuts
down. A refused cleanup or invalid output must not be called a completed rollback.

## Safe result and interpretation

The exact20-key outer schema is `ilinux31am-preboot-result-v1`. Its finite stages,
reasons and initial/cleanup labels are defined by `preboot.h` and `result.c`.
`mount_attempted`, `mount_created`, `mount_read_only_verified`,
`mount_state_uncertain`, bounded/null command exits and cleanup describe the
mount operation explicitly. `mount_created` means verified ownership, not that
false proves no change; uncertainty is separate. The outer record deliberately
does not claim the mount table was unchanged or call mounting a pure read.

The nested `diagnostic` is null or the unchanged16-key31AL record. Its
`read_only`/`writes_authorized` flags describe the collector, not the preparation.
Outer `preboot_write_requested`, `boot_object_installed`,
`security_settings_changed`, `native_ready`, `identifiers_returned` and
`policy_values_returned` are always false. Temporary scratch-directory metadata
is written; no Preboot filesystem-content write is requested. Raw paths, IDs,
policy values, stderr and unknown labels are never displayed.

Diagnosis returns0 only for valid initial admission plus successful required
cleanup; all other outcomes return2. Validation returns0 for either valid
structured outcome, including a refusal, and2 for invalid/oversized/symbolic input.
It reads at most8192 bytes and reconstructs only strict allowlisted output,
including a separately validated nested record. Display validation is not
authenticated hardware evidence or permission to install/boot. An internal
invariant failure after a possible operation emits a conservative uncertain-mount
refusal, never a reset claim that nothing happened.

## Offline build and tests

```bash
python3 -I tools/boot-object31am-native/test_native.py
python3 -I tools/boot-object31am-native/test_native.py --sanitize
```

The new methods compile original C with the installed Apple SDK and run only
synthetic CF/file/child controls. They never inherit/rerun the older29 methods,
query host mount state or execute Apple mount/policy tools. Cases cover absent
plist keys with positive kernel proof, unsafe/contradictory metadata, identity
changes, partial command outcomes, read-only and cleanup refusals, valid nested
diagnosis, strict output consistency and redaction. A separate workspace harness
executes the actual production mount-binding branch with a modeled overlay:
new FD identities differ from retained underlying FDs, kernel statfs is injected,
and fresh FDs are proved closed before any unmount could occur. This proves
software behavior under the model, not hardware mount or Recovery compatibility.

`build.py --output NEW_WORKSPACE_PATH --candidate-definition DEFINITION` creates
the helper and sanitized build receipt under ignored `build/`. Receipts bind
all new build inputs, frozen input hashes and original guard-preservation proof,
candidate definition, compiler/SDK, ABI, minimum OS and binary size/hash. No
new live action or public binary publication is performed by building.
