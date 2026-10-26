# 31AG: offline review and selected-object evidence; no new experiment

**Do not restart M1, start a proxy, install a candidate or repeat 31AF.** There is
no new native image or release. Pull main while preserving local work and read
the [31AG overview](../../native/boot/attempt31ag/README.md),
[handoff findings](../../research/native31ag-handoff.md) and
[Asahi/M4 comparison](../../research/native31ag-asahi-m4.md).

The human reported 31AF installation success and an Apple-logo-only observation
directly to M5. Actual exits/duration remain unknown. Return to macOS is reported;
exact boot021 rollback and Macintosh HD default restoration remain unconfirmed.
Use the existing [restoration-only follow-up](attempt31af-result-followup.md) to
reconcile or complete those steps. Do not infer restoration from a staged file.

## Independent offline review

1. Verify the new source closure, including the fixed earlier dependencies:

   ```sh
   shasum -a 256 -c native/boot/attempt31ag/source-sha256.txt
   ```

2. Run only the three new host-safe suites; expected **65 distinct methods**:

   ```sh
   python3 -I kernel/experiments/entry31ag/test_classify.py
   python3 -I kernel/experiments/entry31ag/test_range_audit.py
   python3 -I tools/boot-object31ag/test_read_selected.py
   ```

   These use synthetic metadata and do not query a policy, run Apple code, launch
   a VM or perform an installation. Do not run the selected-object live mode on
   M1. Its M5/model/root/lab guards are part of the source review.

3. Run the classifier on the committed human result:

   ```sh
   python3 -I kernel/experiments/entry31ag/classify.py native/boot/attempt31af-human-2026-10-26-result.json
   ```

   Expected: native entry UNCONFIRMED, furthest stage UNKNOWN, no proven pre-entry
   failure or Apple-only requirement. It validates report fields, not provenance.

4. Evaluate the intentionally conditional range example:

   ```sh
   python3 -I kernel/experiments/entry31ag/range_audit.py --properties native/boot/attempt31ag/legacy-inspector-properties.json --image-bytes 0x6c000 --load-base 0xfffffe0007000000 --reserved-offset 0x8000 --reserved-bytes 0x54000
   ```

   Expected `CONDITIONAL_INCONSISTENCY`, not native failure. Exit0 means evaluation
   completed. The dictionary was measured in an earlier standalone inspector
   context; the actual Recovery profile is unmeasured. Do not replace it with
   a guessed true profile, override a selector or modify metadata to force boot.

5. Review M5's separate GNU/QEMU/REA receipts as **reviewed, not locally rerun**.
   The three complete emulator cases confirm the requested EL through PSTATE,
   preserve SP=0 and all modeled bytes, and produce paint/status2/status1 as
   recorded. QEMU supplied the register reader; no equivalent native reader is
   qualified. REA gates reject affected whole-function pseudocode. The installer
   collection-kind argument and protection-profile flag are distinct.

6. Review the selected-object reader's command allowlist, exact lab/System-role/
   separate-current-group/Preboot guards, read-only O_NOFOLLOW reads, limits and
   two generic artifact pins. It never writes, mounts, changes security, decrypts
   or prints raw policy/identifiers/paths. IMG4 optional metadata stays opaque;
   matching concerns only the exact known payload and authenticates no signature.

Publish a sanitized offline verdict naming rerun/reviewed evidence, source pins,
any actionable finding and current restoration evidence. Preserve frozen sources,
consumed receipts and prior results. No readiness for a native restart follows.

## M5-only local read-only evidence, when supplied by the human

The new reader follows Asahi's selected-CBO path using the lab's display-only
policy query. The coordinating M5 agent supplies the exact local Terminal
command after source review. This needs local sudo authentication, not another
routine Full/Permissive check. Credentials stay in Terminal; the output contains
only `read_only` and a match label.

* `BOOT021`: the configured lab file or supported wrapper payload equals the
  pinned restore image at observation time. Default selection, historical boot
  and complete rollback are still separate claims.
* `31AF`: the configured lab file/payload equals the candidate. Do not test it
  again; reconcile/finish the existing exact rollback/default sequence.
* `UNKNOWN`, `NO_CUSTOM_OBJECT` or `REFUSED`: do not guess a path, change flags,
  scan other volumes or turn the diagnostic into an installation.

If M1 retained the original installation capture, extract only nonidentifying
PageProtectionType/derived-property evidence if actually present. Do not invent
it or rerun installation to collect it. Raw personalized envelopes, policy keys,
volume identifiers, logs and screenshots stay private.

The next physical experiment needs an actual qualified loader/entry observation
or a matching accepted host control. This checkpoint does not supply one and
does not establish that Apple alone must provide the solution.
