# 31AU install refusal checkpoint — November 15, 2026

**Observed: INSTALL REFUSED; restoration and Macintosh HD default/desktop return pending.**
The authorized one install was human-operated in paired Recovery. The display
shows Apple's valid-Mach-O/compression/wrapping/install/done sequence, followed by
an actual non-synthetic controller result: `REFUSED / install / POSTCONDITION /
POLICY_OR_OBJECT`, writer exit **0**, mutation attempted, cleanup verified and
state preserved. Candidate and rollback verification are both false. No emitted
`INSTALL_COMPLETE` or final shell success result is observed; the success printf
visible inside the pasted source is not execution evidence.

The photographed finite diagnostic reports:

| Field | Observed value |
| --- | --- |
| Phase/reference/read | candidate; reference present; attempted and succeeded |
| Object stage | DECODE_REJECTED |
| Object identity/container/codec | UNKNOWN / IMG4 / LZFSE |
| Recognizer completed / known exact / candidate exact | false / false / false |
| Lab CTRR enabled / disabled / unknown | false / true / false |
| Preservation contract | true |
| Selected payload / CTRR / complete phase contract | false / false / false |
| Selection comparison available / reference changed | true / true |

**Inferred, with limits:** the selected reference changed across the guarded
pre/post observation and its selected file was readable. This does not prove
candidate exactness, successful firmware entry or an unchanged-selection cause.
The original recognizer's decoder path rejected after its framing/size checks;
the cause remains Unknown, including whether this reflects decoder/encoding
compatibility. Disabled lab CTRR independently fails the candidate requirement.
The reported preservation pass is not a fresh independent M1 policy query.

The failed candidate must not boot. M1 instructed the complete independent exact
boot021 restore box **once**, preserving baseline/key/state and consumed markers.
Restore output and Macintosh HD default/desktop return remain pending. If restore
refuses, preserve the actual result and stop without force, reset, extra writer
or install retry. Prior restoration is not a result for this new attempt.

The reviewed page remains available for restore. All **190** source pins and
**293** prior evidence/artifact/review/closed-session files verify unchanged.
M1 ran no target controller, mount, policy or writer; no suite/rebuild or changed
flags. Native RAM observation, Linux/live target version/SMP/GPU/performance are
**NOT RUN**. No raw photograph, private policy, identifier, credential or selected
reference was copied into Git. Complete finite transcription is in the companion
JSON. M5 owns further offline analysis after restoration and safe return.
