# 31AK: canonical Recovery work directory

This is an original, offline path correction around the frozen 31AJ transaction.
The confirmed 31AJ attempt stopped before enrollment because Recovery's
`/private` is a system symlink. The strict native helper refuses a supplied
profile path with any symbolic component. The separate Recovery codec control
passed, but target-state admission, Linux and native SMP were not reached.

The three original dependency hashes in `render.py` bind the frozen 31AJ profile,
renderer and verified source loader. Dependencies are read without following
symbolic components and compiled from hash-checked memory snapshots. The
original renderer's transaction is retained. The new module changes only the
work-directory handling, associated identity checks, cleanup and failure advice;
it does not edit any frozen file or weaken native `O_NOFOLLOW` behavior.

## Directory binding

The future block creates one root-owned mode0700 temporary directory through
the existing system `/private/tmp` interface. It records device/inode/owner/mode,
derives the physical path with `cd -P` and `pwd -P`, checks the lexical and
physical identities agree, and rejects a symbolic physical component. Only this
new owned directory is resolved; KIT, STATE, lab/original volume guards, policy
paths and their no-follow requirements remain unchanged.

The block enters that verified physical directory inside its outer subshell.
Its kernel-held working directory anchors relative file copies, snapshot output
and cleanup. Repeated checks compare the named WORK directory with `stat .`,
owner0/mode700 and `pwd -P`, including another named-path check afterward.
Helper/profile/snapshot arguments use the canonical WORK path, so the unchanged
native descriptor walker can open them without encountering `/private`'s alias.
Bindings are checked before helper work and each potential enrollment/policy
command. Candidate/helper/rollback/profile hashes are still checked after copy.

The implementation deliberately does not depend on `/dev/fd/9` lookup semantics.
Bounded macOS workspace controls showed that `stat('/dev/fd/9')` need not report
the underlying descriptor's device/inode, and `cd /dev/fd/9` can fail ENOTDIR.
The actual shell fixtures therefore exercise a pinned working directory rather
than a mocked Linux-style fdesc assumption. The C helper's existing descriptor
reads and no-follow protections are unchanged.

Cleanup is restricted to the five fixed temporary filenames in the held working
directory, followed by empty-directory removal only while its binding matches.
There is no recursive removal or deletion of persistent transaction state. A
failed identity check can leave an owned private temporary directory; cleanup
is not claimed in that case. This protects against accidental path substitution,
not a malicious process with unrestricted root control of the whole machine.

## Unchanged transaction boundaries

The candidate, native helper, canonical profile and intended raw boot021 bytes
are unchanged. The new workflow still uses the already staged 31AJ kit and its
fixed state directory. It keeps paired-Recovery/Full-original/Permissive-lab
admission, private comparison-key and baseline checks, metadata comparisons,
exact contained-object identity, one-shot mutation markers and independent
restore. There is no automatic reboot, default selection, policy reset,
firmware operation, restaging or native authorization.

Before an install command is attempted, failures say `PRE_ENROLLMENT_STOP` and
explain that independent restoration requires the persisted baseline/key; it is
not a universal recovery command. Restore admission failures say
`RESTORE_PREFLIGHT_STOP` and do not claim restoration. After any attempted boot
or policy command, `POST_COMMAND_STOP` preserves the conservative outcome and
guarded-restore requirement. Returned failures retain fresh-readback behavior.

## Focused offline verification

From the checkout root:

```sh
python3 -I tools/recovery31ak/test_paths.py
```

These are original synthetic workspace controls. The full blocks are rewritten
to fake root/stat/helper/write tools and temporary lab/original/data paths before
execution; the harness asserts that actual Recovery/volume/boot-write references
are absent. Root ownership and machine/policy state are simulated. Actual shell
filesystem behavior, `cd -P`, canonical paths and directory identity are exercised
on macOS. The fake helper additionally rejects every symbolic component in its
supplied profile, snapshot, baseline and key paths.

The old 31AJ block reproduces the capability refusal under an isolated
`private -> System/Volumes/Data/private` layout. The new install and independent
restore complete under that same layout, including candidate-missing restoration
and already-restored no-repeat behavior. Negative controls cover wrong ownership
or permissions, a directory replacement, pre-capability/missing-baseline
refusals and post-command failures. HTML boxes round-trip the exact new blocks;
write arguments, strict path guards and shell syntax are checked separately.

These tests do not establish real Recovery admission, policy preservation,
enrollment, physical core operation, display readability or performance. No
system link, host settings, boot object or security mode is changed. Parent
package preparation supplies a new Git-only source closure and page receipt;
M1 independently reviews the correction before any separately authorized visit.
