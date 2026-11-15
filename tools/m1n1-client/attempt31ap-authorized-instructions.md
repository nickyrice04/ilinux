# M1: staged 31AP conditional read-only Recovery handoff

November 15, 2026. M5 reviewed `a136914`: all 140 pins and 34 focused methods
pass with no actionable code finding. The user requested staging and preparation
of the conditional read-only check, preserving Original Full. The existing
temporary lab-default/Original-return approval persists for this workflow.

The owner authenticated locally and provided the exact successful staging
JSON: helper124640/d31279b4…4684 and profile823/c64b596f…c747, diagnostic-only;
no boot-object, security, volume or default change by that copy. Do not restage,
overwrite or reset old state. M5 then selected the lab temporarily in Original
System Settings. A fresh read-only selected-device/real-group comparison
confirms default LAB and current ORIGINAL. No Restart was clicked or issued.
Evidence: native/boot/attempt31ap-handoff-2026-11-15.json.

## No helper transfer is needed to serve the page

Your missing-kit finding was correct for the old `--prepare --kit` workflow.
The actual server, however, validates only the frozen sources, canonical public
profile and exact rendered HTML. It never reads the helper. The target already
has the exact files, and the unchanged Recovery block verifies their hashes and
sizes before copying and again before execution. That target gate remains intact.

The new source-only adapter is outside the frozen 140 inputs, which remain
unchanged. Its three source hashes and nine-method independent review are in
native/boot/attempt31ap-source-page/. It generates the same three reviewed files
without a kit, helper, private cache, stage, host query or socket. Its receipt
truthfully says `SOURCE_PROFILE_PAGE_ONLY` and
`binary_delivery_verified_on_M1=false`. Do not claim binary delivery happened.
No native or prior suite/build/reference transfer needs repeating.

## Prepare and check the exact page

Pull the commit containing this handoff. Review the small adapter/source hashes,
then run from the checkout:

```bash
python3 -I tools/recovery31ap-page/prepare.py --prepare \
  --output build/31ap-m1-source-page
python3 -I tools/recovery31ap/package.py \
  --page build/31ap-m1-source-page/recovery.html --check-only
```

If that fresh output path already exists, do not overwrite or delete it. The
unchanged second command can verify an already matching page before reuse;
report any mismatch. Expected exact identities:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| profile.json | 823 | c64b596fd0d2e7003098eda79fa3a7f9841e13de79d2ce430d2b49f15d2bc747 |
| diagnose-paste.txt | 5615 | d9a47b93fc65ac78aa7a2b0e662bb6f2ce568584c74cf07575735f6247631bd7 |
| recovery.html | 8357 | fff051694d5cecd389e9fcc26204189277c0c83ba66f619429acc631558ff466 |

The visible title must be **31AP typed-policy Preboot check**. Native outer31AM
and inner31AL schema labels are expected because those validators are unchanged.
The old `ilinux31am.` fresh scratch prefix is also intentional; do not edit it.

## Start only the bounded page server

After exact source/page validation, start the unchanged reviewed controller:
`python3 -I tools/recovery31ap/package.py --page build/31ap-m1-source-page/recovery.html`.
Supply your current explicit private IPv4 `--bind`, `--port 8031 --seconds 1800`.
Do not guess or publish the address. Return the complete printed live URL
privately to the human, including its inherited `/31aj` route. Record the finite
exact-page/server readiness evidence in Git; omit LAN details and process IDs.
An expired page server may be restarted without repeating a Recovery operation.

No M1 restart, USB/proxy, camera calibration, original helper execution on M1,
new large image, package build, native suite rerun or helper transfer. Keep
recording off or covered during authentication. Only a photograph of the emitted
safe Terminal results is needed. M5 gives the shutdown cue after this live page
is established; keep M5 running until then.

## One human-started check, then Original return

On M5's cue: save work and shut M5 down. From fully off hold power until startup
options appear; select **Options → Continue**, not the old lab boot tile. The
temporary lab default is for paired lab Recovery. Authenticate only in the local
system prompt.

Open the exact new page, select its entire single box and copy once. Quit the
browser, open Utilities Terminal, paste the whole block once and run it. No
clipboard trial, edited disk number, second box or retry.

The helper may conditionally mount only the identity-bound shared Preboot
read-only when positively unmounted. Existing valid mounts remain untouched.
It verifies source/path/actual read-only status, performs guarded collection and
initial admission, then cleans up only its own verified mount. No policy write,
installation, restoration, firmware/volume change or Linux boot is authorized.

Capture the emitted outer JSON, nested diagnostic, shell records and exits.
A successful result needs outer `DIAGNOSTIC_COMPLETE`, nested
`INITIAL_ADMISSION_PASS`, helper exit0 and known successful/unused cleanup with
no uncertainty. A display-validator exit0 alone can validate a refusal and is
not a pass. Pasted script text is not execution evidence. Never print raw rejected
output if validation fails.

Stop after this one check, pass or refusal. Do not force an unmount, remount,
rerun or recursively delete scratch. Report uncertain cleanup truthfully.
Restore Macintosh HD as default and return to its desktop using the existing
approved return flow. If Recovery Startup Disk cannot apply it through remaining
read-only Preboot, shut down, hold power, select Macintosh HD once, then restore
its default in Original System Settings. Never boot the old lab tile.

Confirm desktop and default separately. No repeated routine Full/Permissive
command is needed. Keep credentials, identifiers, raw policies, personal media,
private paths and LAN details out of Git. Install/restore/Linux/SMP/performance
remain NOT RUN; boot021 restoration stays OUTSTANDING. M5 decides the next step
from this result; there is no automatic installation or retry.
