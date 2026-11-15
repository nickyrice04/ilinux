# M1: review the source-only 31AS Recovery repair

November 15, 2026. Review offline first; this is not a restart or live transaction
cue. The 31AR result `01c64b5` stopped at unavailable `/usr/bin/cmp`, before
controller dispatch, enrollment, managed mount or Apple writer. Macintosh HD
desktop/default return is human-confirmed. Boot021 rollback remains OUTSTANDING.
Do not describe the return alone as restored boot021 or a native firmware result.

31AS replaces the two profile comparisons with exact length/mode/SHA-256
verification, hardens hash-producer exit handling and adds builtin availability
checks for the fixed shell/native tools. It removes cmp and awk dependencies.
No alternate comparator path is guessed. Review the exact reversible changes
and the dependency-refusal output in `tools/recovery31as/package.py`.

All 162 original inputs, helper125168/profile823, candidate, boot021, `31ar-kit`,
`ilinux31ar-state`, scratch prefix and native guards remain unchanged. Do not
restage, rebuild, transfer artifacts, rename state, clean old scratch or reset
markers. Both independent operation blocks receive the repair; restore remains
candidate-independent. Native 31AR labels are intentional; the page is new 31AS.

Verify `native/boot/attempt31as-page/source-sha256.txt` and review the new focused
test evidence. The shell harness actually executes the bootstrap with original
workspace utilities and genuine artifact pins; it intercepts native calls with
an explicit synthetic fixture. It does not test Recovery/native hardware.
If the exact production kit is absent on M1, report shell coverage as skipped,
not passing. No transfer is needed merely to review or serve the page.

Prepare the source-only page into a fresh directory and check it without a
socket:

```bash
python3 -I tools/recovery31as/package.py \
  --prepare --output build/31as-m1-source-page
python3 -I tools/recovery31as/package.py \
  --page build/31as-m1-source-page/recovery.html --check-only
```

Compare all six outputs with the new producer receipt. Do not regenerate an
already exact directory just to change its name. The combined page has two
complete text boxes; independent install.html and restore.html each have one.
Both use whole-box Command-A/Command-C, browser quit and one Terminal paste.
No clipboard trial or hand-edited workaround is needed.

The visible title must be **31AS Recovery profile verification**, and the route
is `/31as`. The old 31AR page is not the corrected page. Report the new byte
counts and hashes from the producer receipt; do not substitute historical values.

After M5 accepts your offline review and requests serving, start only the exact
new page through `tools/recovery31as/package.py --page ...`, using the current
private IPv4 bind, port8031 and a bounded lifetime of at most1800 seconds.
Verify actual HTTP body equality, then return the complete private URL and
publish a finite readiness report. URLs, process IDs and network details stay
out of Git. No M1 restart, USB proxy, camera calibration, native suite or package
build is required. Keep camera recording off throughout Recovery authentication.

The later separately cued transaction retains its original safety requirements:
one guarded lab install, exact INSTALL_COMPLETE/readback/cleanup plus final
shell success before a single external maximum90-second RAM test; then paired
Recovery's independent boot021 restore with conditional lab-only CTRR and exact
RESTORE_COMPLETE/cleanup plus final shell success. Macintosh HD stays Full and
its default/desktop return must be confirmed separately. This is a diagnostic,
not the Omarchy desktop or a performance-parity claim. A display-validator pass
alone can represent a refusal and never admits a boot.

Stop on refusal, missing output, uncertainty or spent state. No repeated writer,
forced unmount, policy reset, old-state adoption or automatic next boot. Publish
only sanitized actual observations and keep Recovery/writes/native/SMP unrun
until observed. No proprietary bytes, private policy data, identifiers or media
belong in Git.
