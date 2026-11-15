# 31AR Recovery pre-controller refusal and return

November 15, 2026. **Observed in the human's Terminal photograph:** one install
box paste stopped with `-bash: /usr/bin/cmp: No such file or directory`, followed
by the fixed31AR STOP message and a returned shell prompt. No controller JSON,
INSTALL_COMPLETE or final shell success record was emitted. The human then
confirmed both the usual Macintosh HD desktop and its default Startup Disk.

## Stopping boundary

The frozen renderer uses `/usr/bin/cmp -s` first for the expected public profile
against the staged profile, and later for the copied scratch profile. **Both
comparisons precede the native controller invocation.** A missing comparator
therefore refuses before controller enrollment, Preboot mounting or any Apple
writer. The first comparison is the likely stopping point; the photo does not
separately label which comparison invocation produced the error. That distinction
does not change the pre-controller boundary. Scratch may contain profile material
or copies; it was left intact without manual cleanup or resetting state.

These are source-based consequences of the reviewed short-circuit flow, not an
independent M1 query of target state. Pasted source shown with continuation
prompts is not evidence that its later writer/success lines executed. No numeric
shell status was separately echoed; fail() exits2 in the reviewed source, which
must be distinguished from an observed numeric exit.

The exact observed fact is that **the requested absolute comparator path was
unavailable to this Recovery shell**. No alternate path or replacement comparator
was queried or qualified. This is a page dependency failure, not a human typing
error, candidate format rejection or firmware-entry result. Bash syntax, byte-
exact page checks, desktop fixtures and PTY controls did not establish availability
of every shell dependency in actual Recovery.

Both install and independent restore blocks use the same comparator path, so
an offline repair and its review must cover both. No hand-edited workaround,
changed flags, hot patch, repeated paste or blind restore was instructed. The
new transaction baseline/key was not reached by this paste; the authorized
procedure calls for return after a clean pre-write refusal.

## Closure and evidence limits

The human confirmed desktop and default in response to the explicit request
for both, with no return problem. No separate final policy query was requested.
The controller invoked no policy or boot writer on the reviewed failure path;
Original Full remains the required invariant, not a newly printed final result.
M1 stopped its verified owned page server with SIGINT; process exit0 and listener
closure were verified. No agent restart, USB proxy or camera capture occurred.
The safe photo was not copied into Git.

All **162 frozen source pins**, **180 previous evidence/artifact/page/review/
closed-session files** and **6 prepared page/profile/paste outputs** remain
byte-identical. No source/test change, suite/build rerun, restaging, transfer,
old-state or consumed-receipt reset. The new own session was closed with this
outcome; prior receipts and first-run review evidence remain unchanged.

One Recovery shell paste was **RUN / REFUSED BEFORE CONTROLLER**. The31AR
controller, managed RO/RW mount, Apple installation/restoration, native entry,
Linux, SMP and performance remain **NOT RUN**. No native window was used.
Boot021 restoration remains **OUTSTANDING**; successful Macintosh HD return
alone does not establish restoration of the lab object.

M5 owns offline dependency repair and the next reviewed handoff. Do not replay
the old page or infer native compatibility from this stop. Prior reports39c09f9
and4a57360 remain historical offline/page evidence; this real Recovery result
adds the previously unqualified dependency observation. M5 accepted the physical
scope in1e77aaa, but no controller or writer was reached in this visit.
