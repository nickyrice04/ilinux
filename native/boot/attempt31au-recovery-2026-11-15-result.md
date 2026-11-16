# 31AU Recovery result — November 15, 2026

**Install refused; exact boot021 restoration and Macintosh HD desktop/default
return are human-confirmed. No candidate boot occurred; Linux remains NOT RUN.**

The finite install result is frozen in checkpoint `2c33914`. The human's photo
shows valid-Mach-O/compression/wrapping/installation/done, followed by actual
non-synthetic `REFUSED / install / POSTCONDITION / POLICY_OR_OBJECT`. Writer exit
was **0**; mutation attempted, cleanup verified and state preserved were true;
candidate and rollback verification were false. No emitted final install shell
success was observed. A success printf inside pasted source is not a result.

| Diagnostic | Actual observed value |
| --- | --- |
| Selected reference present; read attempted/succeeded | true / true / true |
| Reference comparison available; selected reference changed | true / true |
| Object stage | DECODE_REJECTED |
| Identity / container / codec | UNKNOWN / IMG4 / LZFSE |
| Recognizer completed / known exact / candidate exact | false / false / false |
| Lab CTRR enabled / disabled / unknown | false / true / false |
| Preservation contract | true |
| Selected payload / CTRR / complete phase contract | false / false / false |

**Confirmed display observation:** the selected reference changed and its file
was read. **Source-level interpretation:** the original recognizer classifies
failure in its decoder path after framing/size prerequisites. The underlying
cause remains **Unknown**; this could require decoder/encoding investigation,
but it does not establish firmware rejection or candidate identity. Disabled lab
CTRR is a separate failed requirement. The preservation result is the controller's
guarded result, not a fresh independent M1 policy read.

M1 stopped the candidate path and instructed the complete independent boot021
restore box once. The human explicitly confirmed all four required fields:
`RESTORE_COMPLETE`, `rollback_verified=true`, `cleanup_verified=true`, and final
shell `helper_exit=0`. Raw restore output, a separately numeric Apple writer exit
and exact command count were not received; one restore was instructed and no
repeat was reported. These limits remain distinct from the confirmed success
fields. Prior restoration evidence was not reused as this attempt's outcome.

The human then separately confirmed the usual **Macintosh HD desktop** and
**Macintosh HD default Startup Disk**. M1 stopped its exact owned page server by
SIGINT; server exit **0**, process absent and listener closed were verified.

All **190** source pins and **293** prior evidence/artifact/review/closed-session
files remain unchanged. The prior checkpoint stays frozen. No prior key,
baseline, state or consumed receipt was reset or re-armed. M1 ran no target
controller, mount, policy query or writer; no M1 restart, proxy or VM. The
Original Full preservation requirement was retained; no extra policy workaround,
new volume, firmware change or guard relaxation was attempted.

Native RAM observation, Linux/live target version/SMP/GPU/performance are
**NOT RUN**. The candidate was not booted after refusal. M5 next owns **offline
analysis and a proposed fix**, preserving all AU and earlier private state.
This result supplies no retry or new experiment authorization. Public evidence
contains only finite observations and original prose; raw media/private policy,
identifiers, credentials and local service metadata remain excluded.
