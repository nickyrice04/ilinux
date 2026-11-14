# M1: review 31AK Recovery-path correction offline

Your 31AJ refusal report is incorporated. Boot021 restoration did not run; M5's
fresh user-provided read-only check identifies the lab payload as EXACT_31AF.
M5 independently confirms current/default Macintosh HD. No policy or boot
setting was changed by this correction work. Keep Macintosh HD Full Security.

31AK changes the procedure, not the 31AJ candidate, helper or canonical profile.
All four already-delivered files and your prepared workspace directory are valid.
There is no binary transfer, rebuild, lab restage, marker deletion or re-arming.
The intended physical result remains actual 31AF → unchanged 31AJ diagnostic →
exact raw boot021 / disabled lab CTRR → Macintosh HD / default. Actual admission is unrun.

Use your isolated clean checkout and preserve unfinished work. Read
`native/boot/attempt31ak/README.md` plus the new renderer/package controller.
Verify every new source inventory member is tracked and hash-exact, with all 62
old portable bindings unchanged. Reuse your previous 247-method/artifact review.

From the checkout root, run only the new focused checks and workspace preparation:

```sh
python3 -I tools/recovery31ak/test_package.py
python3 -I tools/recovery31ak/test_paths.py
python3 -I tools/recovery31ak/package.py --prepare \
  --kit build/31aj-m1-prepared --output build/31ak-m1-pages
python3 -I tools/recovery31ak/package.py \
  --page build/31ak-m1-pages/recovery.html --check-only
```

Use your actual existing verified prepared-directory name if it differs. Output
must be new; preserve previous evidence. Source inventory is fixed to
`native/boot/attempt31ak/source-sha256.txt`; profile remains the original 31AJ Git
profile. Page check-only creates no socket. Do not execute either rendered block.

The 30 new methods are the focused boundary, not a request to rerun all unchanged
tests or boot Linux. The alias fixtures exercise actual macOS shell paths with
fake root/policy/write tools, and reproduce frozen 31AJ's failure. Review that
only a new owned temporary directory is physically resolved; volume/kit/state
and native no-follow checks remain unchanged. Check held-directory identity,
relative writes/fixed-file cleanup, failure-stage advice, unchanged enrollment
arguments, saved key/baseline checks and independent restoration.

Review the M5 actual-helper control receipt: the unchanged native reader refuses
an aliased profile and verifies the canonical profile plus exact boot021 using
only `--verify-file`. It is not Recovery admission or boot021 installation.
The clean Git-export receipt establishes that the correction is reproducible
without another producer-only executable. Compare your new page hashes against
the new 31AK preparation receipt, not the old 31AJ page hash. Profile and all
binary hashes must still match the old ones exactly.

Publish a sanitized review and push it, distinguishing fresh checks from reused
results. Mark Recovery/install/native/rollback/performance NOT RUN. Do not start
a production page server, camera, proxy or physical retry from this review.
The previous 31AJ visit ended; a new reviewed physical sequence needs the user's
go-ahead. No additional security-mode command, camera-quality retest or M1
restart is needed to complete this offline review.

After a future explicit authorization, serve the new page using this controller
with `--page`, explicit private-LAN `--bind`, port and bounded `--seconds`.
Do not use the frozen 31AJ server to validate a 31AK page. The M5 agent verifies
the exact live page before any new restart cue. Reuse the recording plan:
camera off/covered for credentials, fresh framing after a move, actual RECORDING
confirmation before the native cue, independent maximum 90-second deadline,
one diagnostic observation and guarded exact boot021 restoration afterward.
