# 31AL read-only Recovery diagnostic result

November 14, 2026. **Observed:** the one human-operated diagnostic emitted a
validated finite refusal; the human subsequently confirmed both the Macintosh HD
desktop and its default Startup Disk. This is a completed read-only diagnosis,
not a native boot or an installation attempt.

## Captured result

The Terminal photograph shows both shell records, `HELPER_EXIT` and
`DIAGNOSTIC_CAPTURED`, with `helper_exit=2`. Between them, the helper reports:

- scope `RECOVERY_READ_ONLY_DIAGNOSTIC`; status `REFUSED`;
- stage `AUX_IDENTITIES`; failure kind `GUARD`;
- reason `PREBOOT_MOUNT_PATH`;
- command `DISK_INFO`, command exit **0**, stdout count **4770 bytes**;
- snapshot collected **false**, initial admission valid **false**;
- read only **true**; writes authorized/native ready/identifiers returned/policy
  values returned all **false**.

The final safe-result message and `DIAGNOSTIC_CAPTURED` establish that display
validation succeeded. Its numeric exit was not printed separately; zero follows
from the reviewed shell control flow. The outer block's numeric exit was also
not separately printed. Do not confuse metadata-command exit0 or a successful
safe display with successful target admission. Only emitted records are evidence;
the large pasted source text above them is not evidence that every line ran.

## Source interpretation and limits

**Confirmed from the pinned original source:** the exact reason is attached to
`!safe_path(mount)`, where `mount` is the Preboot info `MountPoint`. The unchanged
collector applies a lexical path guard here. The actual value is deliberately
not returned, so which path rule failed remains **Unknown**. The retained
DISK_INFO exit/count is capture context, not evidence of a failed diskutil command.

This narrows the 31AK initial-snapshot refusal to a specific guard in the current
31AL visit. It does not establish that the previous visit had the identical
operand, nor establish an invalid physical mount, firmware restriction or parser
fix. Source order places the later directory-open, policy-read, pairing/security,
selected-object and comparison phases after this guard; they were not reached.
No new Full/Permissive or pairing verification is claimed for this visit.

M5 owns offline interpretation and any proposed remedy. Preserve the guard and
frozen sources while identifying the next safe evidence needed; this result
provides no permission to retry, broaden admission, install, restore or boot.

## Closure and preservation

The human confirmed Macintosh HD desktop and default. No repeated routine policy
query was requested. The verified owned page-server listener was stopped with
SIGINT; its process completed exit0 and port closure was checked. Camera stayed
off; no USB/proxy or M1 restart. No new persistent diagnostic baseline/key or
consumed-state reset. All 92 pinned sources and 54 previously inventoried evidence,
kit, page, receipt and closed-session files verify unchanged; no test suite,
build or transfer was repeated. Raw photo, policy, identifiers, private paths
and local server address are not published.

Install/restore/native observation/Linux/SMP/performance remain **NOT RUN**.
Boot021 restoration remains **OUTSTANDING**; no new installed-object query or
rollback occurred. Original Full is still the required invariant.

Handoffs: `a16b0b5` (staged diagnostic), `1e3de57` (exact page readiness).
The machine-readable companion contains the complete transcribed safe records.
