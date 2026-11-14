# M1: 31AJ portable correction and boot preparation

Your `8352602` finding is incorporated. Preserve the original 57-entry closure,
old receipts and all four delivery files. Use the new portable inventory and
adapter, not an edited old manifest or an extra executable transfer. Reuse the
247 passing methods and original artifact/source review; only the portable
correction and its new receipts need checking.

Read `native/boot/attempt31aj-portable/README.md` and the latest status entry.
Verify the new inventory has no missing or changed member. Run the new adapter's
focused tests. The new M5 clean-export receipt records preparation from Git-only
sources with exactly the four delivered files and no producer test executable.
Confirm all four generated profile/install/restore/HTML hashes still match the
original `native/boot/attempt31aj-kit/page-preparation.json`.

The existing prepared workspace directory from your original review is valid;
no rematerialization or file transfer is needed. From the checkout root:

```sh
python3 -I tools/recovery31aj/prepare.py \
  --profile native/boot/attempt31aj-kit/recovery-profile.json \
  --kit build/31aj-m1-prepared \
  --source-inventory native/boot/attempt31aj-portable/source-sha256.txt \
  --output build/31aj-m1-portable-pages
python3 -I tools/recovery31aj_portable/adapter.py \
  --page build/31aj-m1-portable-pages/recovery.html --check-only
```

If your actual verified prepared directory has a different workspace name, use
that existing directory. Choose a new output basename if it already exists;
preserve old evidence. Do not remove or fabricate a file to satisfy a pin.

Once the latest M5 status confirms staging and explicitly releases the physical
handoff, prepare to serve the verified page with the portable adapter. Choose
M1's current literal private LAN address and pass it with `--bind`, plus the
desired `--port` and bounded `--seconds` (maximum 1800). Send the resulting local
URL privately to the user. Do not publish LAN addresses in Git. No repository,
artifact or directory is served; the adapter exposes only the exact reviewed
HTML at `/31aj`. Keep both independent phase text boxes available.

Do not restart M1 or start a proxy. For the later native observation, use the
existing camera handoff rather than another quality clip. Frame after any move,
confirm actual RECORDING before the human boot cue, and use an independent
maximum 90-second timer from the boot cue. Stop/cover the camera before Recovery
authentication. The diagnostic is self-contained; no USB upload or Linux network
connection is assumed.

The next M5 restart is for the correctly paired lab Recovery workflow, not a
direct jump into an unstaged/unverified candidate. Keep Macintosh HD Full and
the lab's existing policy boundary. No native boot after a refused/failed install.
The reviewed independent restore block remains available and requires exact
boot021/disabled CTRR at the end; Macintosh HD desktop/default return is separately
confirmed. Do not infer authorization for a boot-object or Startup Disk change
from a staging-only status. Record what actually ran, with all unrun phases
marked NOT RUN. Do not include private keys, metadata tokens, identifiers or media.
