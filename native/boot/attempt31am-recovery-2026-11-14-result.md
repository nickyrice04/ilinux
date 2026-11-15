# 31AM conditional Preboot result

November 14, 2026. **Observed in the human's Terminal photograph:** one reviewed
conditional check verified initially unmounted/empty Preboot, created and verified
an owned read-only mount, then successfully unmounted it. The unchanged diagnostic
progressed to a lab-policy parser refusal. The human subsequently confirmed both
the Macintosh HD desktop and its default Startup Disk.

## Complete captured result

Outer `ilinux31am-preboot-result-v1`, scope `RECOVERY_CONDITIONAL_PREBOOT`:

| Field | Value |
| --- | --- |
| status / stage / reason | REFUSED / DIAGNOSTIC / DIAGNOSTIC_REFUSED |
| initial_state | UNMOUNTED_EMPTY |
| mount_attempted / mount_created | true / true |
| mount_read_only_verified / mount_state_uncertain | true / false |
| mount_exit / unmount_exit | 0 / 0 |
| cleanup | UNMOUNTED |

The nested16-key31AL diagnostic reports scope `RECOVERY_READ_ONLY_DIAGNOSTIC`,
status **REFUSED**, stage **LAB_POLICY**, failure kind **FORMAT**, reason
**UNSUPPORTED_METADATA**, command **POLICY_READ**, command exit **0**, stdout
**2822 bytes**. Snapshot collected and initial admission valid are both false.
Read only is true; writes authorized, native ready, identifiers returned and
policy values returned are all false.

Both visible shell records (`HELPER_EXIT`, then `DIAGNOSTIC_CAPTURED`) show
helper exit **2**. Shell Preboot-write-requested, boot-settings-changed,
security-settings-changed, readiness and private-value-return flags are false.
The outer record likewise reports no Preboot write request, installation,
security change, readiness or returned private values. The fixed shell also performed private scratch writes, and the mount changed
Recovery mount state; this was not an operation with no state changes.

`DIAGNOSTIC_CAPTURED` and the final validated-result message establish successful
safe display. The display validator's numeric exit was not printed separately;
zero follows from reviewed control flow. The block's outer numeric exit was not
separately printed. Only emitted records are execution evidence; the pasted
source above them is not. This is human photo evidence of the reviewed helper's
observations, not an independent M1 query of the target.

## Interpretation and limits

**Confirmed for this visit by the finite result:** the Preboot prerequisite was
met under the reviewed read-only/ownership checks and required cleanup passed.
The result supports the unmounted/empty prerequisite hypothesis raised after
31AL. It does not establish the exact path in the earlier31AL visit.

The new stop is in the unchanged lab-policy parser. Its two explicit
unsupported-metadata paths cover non-absent protected auxiliary metadata and a
tag outside the supported semantic/identity sets. The finite record does not
identify which path, tag or value triggered it. Exact cause/remedy remains
**Unknown**. A successful POLICY_READ capture is not a successful policy parse,
security check or admission.

Source short-circuit order places Original policy parsing and final pairing/
security, selected-object and policy-comparison checks after the failed lab
parse. Those were not reached. No fresh Full/Permissive, paired1TR or installed
payload result is claimed. This supplies no new Linux, CPU, performance or
Apple-firmware result. Do not infer that relaxing the parser is the remedy.

M5 owns offline analysis and the next evidence-based proposal. No raw policy,
private tag value, identifier or rejected capture is requested or published.
No repeated conditional check, guard broadening, blind restore, installation
or native boot follows from this result.

## Closure and preservation

The human confirmed Macintosh HD desktop and default after the approved return.
No repeated routine policy command was requested. M1 stopped the verified owned
page-server listener with SIGINT; process exit0 and listener closure were checked.
Camera stayed off. All **111 source pins** and **75 previous evidence/kit/page/
review/closed-session files** verify unchanged. No source/test edit, old state or
consumed-receipt reset, repeated suite/build, proxy or M1 restart.

Live Recovery and conditional mount/cleanup were **RUN**, with the outcomes above.
Install/restore/native observation/Linux/SMP/performance remain **NOT RUN**.
Boot021 restoration remains **OUTSTANDING**. Original Full remains required;
no fresh final policy query or new boot-object/security/volume operation is claimed.

Handoffs: `8d8340a` (authorized staged visit), `40d2046` (exact live page).
The JSON companion retains every emitted finite outer/nested/shell field.
