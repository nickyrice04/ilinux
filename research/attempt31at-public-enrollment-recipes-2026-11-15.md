# Public enrollment recipes after the saved 31AS postcondition failure

November 15, 2026. Primary public source was read through the GitHub connector at
immutable revisions. No installer, foreign script, private state, Apple policy
command, mount, firmware operation or boot command was executed for this note.
The command forms below describe source behavior; they are not a new authorized
Recovery procedure. Existing transaction and rollback guards remain intact.

## Corrected conclusion

**Confirmed in published source:** our candidate command has the same Mach-O
mode and compression choice as the working J714s installer. Public reports do
not justify blaming `--compress` for the saved 31AS candidate failure. They also
do not establish that our exact J716c installation or object was accepted.

**Reported by the other owner:** the initial J714s failure report suspected
compression, but its final updates retract that diagnosis. The first attempt
had never enrolled the custom object. A later correctly enrolled compressed
object reached Aura; its subsequent loop was attributed to a Stage2 NVMe
handoff issue. The report then confirms a boot with 15 CPUs at EL2 after the
Stage2 fix. This is another owner's J714s/T6050 result on 27.2, not our
J716c/T6050 result on the current 26.6.2 lab.

The frozen source is betizzel/omarchy-m5 commit
[`9e9cf29a48709b670ec30b9ee212108d78ecd215`](https://github.com/betizzel/omarchy-m5/commit/9e9cf29a48709b670ec30b9ee212108d78ecd215).
Its [final failure-note updates, lines 357–380](https://github.com/betizzel/omarchy-m5/blob/9e9cf29a48709b670ec30b9ee212108d78ecd215/docs/install-failure-2026-11-13.md#L357)
supersede the hypotheses near the beginning of that same file:

| Source location | Correct interpretation |
|---|---|
| Lines 359–367 | The first stub had not reached Finish setup/enrollment; the initial logo/power-off was not evidence against compression or Aura. |
| Lines 369–375 | Correct enrollment used compression and reached Aura. The subsequent Stage2/U-Boot ANS power handoff was the next problem; the report replaced Stage2 with a version containing Aura PR 213. |
| Lines 378–380 | The owner then confirmed first-boot setup and 15 CPUs at EL2, plus graphics/display/network observations. This is an attributed result, not reproduction here. |

[Release-2 notes](https://github.com/betizzel/omarchy-m5/blob/9e9cf29a48709b670ec30b9ee212108d78ecd215/patches/j714s-27.2/RELEASE-2.md#L41)
separately retain compression and correct the earlier failure diagnosis. Do not
copy the beginning of the failure note without its concluding updates.

## Exact command, mount and object-path comparison

The J714s installer applies
[patch 0002](https://github.com/betizzel/omarchy-m5/blob/9e9cf29a48709b670ec30b9ee212108d78ecd215/installer/patches-j714s/0002-Recovery-enroll-a-board-s-padded-Mach-O-Stage-1-with.patch)
to omacom's pinned Recovery implementation. It checks the padded Mach-O properties
(`kcbz=0`, expected padded `kcrz`) and enrolls the padded object with this form:

```
kmutil configure-boot -c PADDED_OBJECT --compress -v TARGET_SYSTEM_VOLUME
```

Our frozen 31AR candidate argv is:

```
/usr/bin/kmutil configure-boot --custom-boot-object ./candidate.macho --volume LAB_SYSTEM_VOLUME --compress
```

Both are Mach-O enrollment, with no `--raw`, no raw-entry arguments, and a
compressed custom boot object. The short/long object and volume options are the
corresponding option forms in the existing inspected Apple command interface.
The relative object name is resolved in our held, verified scratch directory;
the public installer supplies an absolute staged file path. This comparison
identifies no demonstrated argv defect.

The public Recovery policy action is `bputil -nc -v TARGET_GROUP` before kmutil;
its optional custom-boot-argument mode adds `a`. This is visible in
[BootSelection.swift, lines 36–41](https://github.com/omacom/omarchy-mac-installer/blob/c07e54c2134a8ec1415e7e2b917589ae1d3d7dc9/Recovery/Sources/BootSelection.swift#L36)
and the [patched Mach-O enrollment](https://github.com/betizzel/omarchy-m5/blob/9e9cf29a48709b670ec30b9ee212108d78ecd215/installer/patches-j714s/0002-Recovery-enroll-a-board-s-padded-Mach-O-Stage-1-with.patch#L14).
Our existing lab admission already requires Permissive Security and the
previously approved raw-boot state; repeating that policy writer is not a
demonstrated fix and is not proposed here.

The public hand-enrollment script checks paired 1TR and object properties,
requires an available rollback object, then delegates storage to kmutil. It does
not itself copy a custom kernelcache to Preboot. For a return to raw mode it
requires the lab Kernel CTRR policy to be disabled first. See
[enroll-stage1.sh at Aura 22b71758, lines 121–151](https://github.com/aurora-silicon/aura/blob/22b71758dfd048f6a874073db55fbe6bd1d17f44/tools/recovery/enroll-stage1.sh#L121).

The public failure-note inspection locates objects beneath
`PREBOOT/GROUP/boot/NSIH/System/Library/Caches/com.apple.kernelcaches/kernelcache.custom.*`.
Our reader likewise derives a specific `kernelcache.custom.COIH` using the
selected lab group's NSIH/COIH; it does not select the newest wildcard entry.
The public instructions do not establish that a wildcard entry is the selected
object, nor that a valid compressed object must have the same outer bytes as its
uncompressed input. [Published Preboot inspection, lines 273–278](https://github.com/betizzel/omarchy-m5/blob/9e9cf29a48709b670ec30b9ee212108d78ecd215/docs/install-failure-2026-11-13.md#L273).

The base Recovery app mounts Preboot read-only for owner metadata when needed;
in its external/iSC copy branch it requests a normal mount before copying the
relevant support data. It remounts its target stub System writable for installer
housekeeping. These are distinct from our verified owned Preboot RW mount, and
none licenses writes to Macintosh HD. See
[RecoveryActions.swift, lines 151–161](https://github.com/omacom/omarchy-mac-installer/blob/c07e54c2134a8ec1415e7e2b917589ae1d3d7dc9/Recovery/Sources/RecoveryActions.swift#L151),
[lines 369–375](https://github.com/omacom/omarchy-mac-installer/blob/c07e54c2134a8ec1415e7e2b917589ae1d3d7dc9/Recovery/Sources/RecoveryActions.swift#L369),
and [lines 438–464](https://github.com/omacom/omarchy-mac-installer/blob/c07e54c2134a8ec1415e7e2b917589ae1d3d7dc9/Recovery/Sources/RecoveryActions.swift#L438).

Another concrete difference is time: J714s patch 0002 permits 60 minutes for
the compressed configure operation; our controller bounds its child to three
minutes. A real expiration would be a timeout/nonzero outcome, so it does not
explain a correctly recorded exit zero. It matters when reviewing a future
larger matched package, not as a reason to repeat the current writer.

## Kernel CTRR wording is not qualified by this report

There is a real documentation conflict that needs qualification, not a relaxed
guard. Aura's
[Mach-O guide, lines 63–68](https://github.com/aurora-silicon/aura/blob/22b71758dfd048f6a874073db55fbe6bd1d17f44/docs/macho-boot-object.md#L63)
says Mach-O enrollment reenables the volume's Kernel CTRR policy. The J714s
[move guide, lines 76–79](https://github.com/betizzel/omarchy-m5/blob/9e9cf29a48709b670ec30b9ee212108d78ecd215/docs/move-to-27.2.md#L76)
repeats that expectation.

But the final J714s failure-note update at
[line 371](https://github.com/betizzel/omarchy-m5/blob/9e9cf29a48709b670ec30b9ee212108d78ecd215/docs/install-failure-2026-11-13.md#L371)
summarizes a completed compressed enrollment as
“policy Permissive, CTRR off, coih present”. Its successful boot is described
later, after changing Stage2, without a second policy transcript.

**Unknown:** which exact status field, capture time or command output the
unqualified words “CTRR off” represent. That public note does not publish the
full labeled post-enrollment `bputil` output or a status-line count. Searches of
the public repository did not find a second labeled External CTRR status or
another published policy transcript resolving this discrepancy. Absence from
search is not proof such a line never exists. Hardware CTXR execute windows,
hardware CTRR regions and the LocalPolicy Kernel CTRR setting are separate
observations and must not be substituted for one another.

This source therefore cannot justify accepting disabled Kernel CTRR in our
candidate phase. Keep the existing expected policy guard until a narrowly scoped
version/field investigation explains the target's actual behavior independently.

## Confirmation and zero exit deserve their own evidence

The public installer explicitly handles kmutil's confirmation prompt separately
from authentication. Its native transport recognizes the supported yes/no prompt
forms and allows one affirmative response for configure-boot, while rejecting
unexpected/repeated confirmation. It also waits for password echo-mode changes
before sending a password; our transport instead leaves credentials and
confirmation directly with the owner on `/dev/tty`. Source:
[Authorization.c, lines 195–219](https://github.com/omacom/omarchy-mac-installer/blob/c07e54c2134a8ec1415e7e2b917589ae1d3d7dc9/Recovery/Native/Authorization.c#L195).

**Generic hypothesis, weak for this recorded run:** a declined/empty confirmation
that Apple handles as a normal return could yield exit zero without committed
enrollment. The public transport code does not establish that return behavior.
The existing
[31AS install checkpoint](../native/boot/attempt31as-install-2026-11-15-checkpoint.json)
already records observed Apple messages for valid Mach-O, compression, wrapping,
installation and completion, not just a process exit code. That observation makes
simple confirmation cancellation a weaker explanation for this particular run.
It remains a useful theoretical transport control to test offline, rather than
the strongest diagnosis. Do not capture credentials, silently answer an
unqualified prompt, or infer the exact postcondition from completion text alone.

The saved postcondition predicates identify exactness and expected CTRR as
failures, but exactness failure alone does not prove the old object remained:
an unrecognized/unsupported compressed framing could also be classified UNKNOWN.
The immediate priority is the object recognizer and the independently observed
disabled Kernel CTRR predicate: determine whether the selected object was
misrecognized, and qualify the actual policy behavior. Completion text alone
does not resolve either. Preserve exact selected-object and policy postconditions
and the existing boot021 rollback route; this note proposes no further
installed-state query or boot.
