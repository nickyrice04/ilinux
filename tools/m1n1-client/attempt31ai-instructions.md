# M1: independently review the self-contained 31AI RAM diagnostic

**Offline only. Do not restart, enroll a boot object, change policy/firmware,
select Startup Disk, open USB/proxy/camera or run Recovery commands.**
Read `native/boot/attempt31ai/README.md` and the latest shared status first.

## Preserve your existing work

Your 31AH report says the original checkout has five unfinished status edits.
Keep them. Fetch the published main, then review in your clean detached review
checkout or a new isolated worktree. Do not reset, clean, stash automatically,
replace old notes or merge overlapping edits without review. Pin and report the
exact new handoff commit; do not substitute another branch's similar artifacts.
The coordinating prompt names the published commit. An isolated worktree can
live under an ignored workspace `build/` directory if a new one is needed.

All frozen 31AH files remain unchanged. Its existing 41-entry inventory must
still verify. New source/evidence is bound by
`native/boot/attempt31ai/source-sha256.txt`; shared mutable status logs are
excluded from that inventory, and the reviewed Git commit owns their snapshot.

## Receive one folder containing two files

The user copies M5's `build/ilinux-31ai-review/` folder to M1's Downloads using
Universal Control/Clipboard, iCloud or a separate USB drive. The folder contains:

- `aura-inline-128m.macho.gz` — 15,984,123 bytes.
- `ilinux-direct31ai-diagnostic.tar.gz` — 16,031,305 bytes, nineteen members.

Keep both compressed. The new reader verifies them in memory. Do not unpack,
execute, rename internal members, load modules or invoke a boot command.
If the transfer changes a filename/location, supply its actual local path.
There is no public binary Release and no automatic upload/transfer.

## Fresh checks

From your clean review checkout root, with no administrator authentication:

```sh
(
  set -eu
  shasum -a 256 -c native/boot/attempt31ah/source-sha256.txt
  shasum -a 256 -c native/boot/attempt31ai/source-sha256.txt
  python3 -I kernel/experiments/direct31ai/transport/test_inline.py
  python3 -I kernel/experiments/direct31ai/transport/test_extend_exec.py
  python3 -I kernel/experiments/direct31ai/diagnostic/test_package.py
  python3 -I tools/m1n1-client/direct31ai/test_state_model.py
  python3 -I tools/m1n1-client/direct31ai/test_candidate_review.py
  python3 -I tools/m1n1-client/direct31ai/test_selected_object.py
  python3 -I tools/m1n1-client/direct31ai/candidate_review.py \
    --manifest native/boot/attempt31ai/candidate-manifest.json \
    --candidate "$HOME/Downloads/ilinux-31ai-review/aura-inline-128m.macho.gz" \
    --diagnostic-manifest native/boot/attempt31ai/diagnostic-manifest.json \
    --diagnostic-package "$HOME/Downloads/ilinux-31ai-review/ilinux-direct31ai-diagnostic.tar.gz"
)
```

Expected: **37 +22 +40 +40 +33 +49 =221 new methods PASS**. The actual two-file reader
ends `OFFLINE_CANDIDATE_INTEGRITY_PASS`, with extraction/execution/device/camera/
native-ready flags false. It verifies same-file reads, bounds, complete single
gzip/CRC, strict USTAR diagnostic contents, frozen kernel/root/source/VM bindings,
relink proof, baseline Aura prefix, six-segment layout, canonical metadata and
zero padding, plus exact Image/DT/initrd embedded inside the candidate.
A PASS establishes offline consistency, not physical readiness or authorization.
The selected-object suite uses synthetic fixtures and mock host commands only.
Follow its README when reviewing that helper. **Do not run its M5-only live mode
on M1.**

## What to independently assess

The new route uses unchanged baseline Aura and a native inline payload. It
avoids claiming the unpublished USB2 patch or Linux device-mode support. Runtime
Aura remains 3,997,696 bytes; transient encoded input is 19,639,230 bytes. Review
that the DT remains below the earliest pool start, compressed Image and tagged
initrd move to heap, and the pool is overwritten only after parsing. Native
addresses, protected ranges, secondary startup and all real guards remain runtime
questions. The new extender does not modify frozen 31AH or bypass a locked window.

Review the exact source pins and eight executed **public C parser** controls
separately from the mocked CPU/NVMe/heap/DT/window/kernel-entry hooks. Main's final
cleanup was not executed. The unchanged private-root generic VM result comes
from 31AH; it was not a new physical core test. The fresh object relinks exactly
to that tested executable and passed normal/stall controls. Licence text and
relink material accompany local-user delivery; full public binary source closure
is explicitly incomplete.

Review `research/direct31ai/findings.md` and the two-query REA consistency record.
Seventy-three checked instruction words establish neither entry EL nor live
lab firmware compatibility. Global Boot ROM 20457.1.29 and OS loader 18000.161.10
are separate. Public Aura recognizes the current OS-loader version; that is not
a requirement to update and not proof of physical compatibility.

The human confirms running Macintosh HD. Fresh M5 output from the fixed reader
is **`payload_relation:EXACT_31AF`**: the 442,368-byte OCTET payload equals the
hash-verified 31AF reference. Boot021 is not the currently selected lab payload.
The complete IMG4 is 445,430 bytes, with no outer trailer and one final opaque
300-byte IM4P context-[0] field. Full-container `match` deliberately remains
UNKNOWN; no property/signature verification was performed. Review this exact
payload boundary separately from wrapper authenticity and effective policy.
These facts do not establish raw boot021 restoration, CTRR or the default
selector. Do not run another M5 read or old security-mode loop from M1. Never
infer rollback from a failed process, a copied file or desktop return alone.

The new state model checks supplied assertions only. Audit its object/CTRR/
unrelated-policy/default separation, timeout/failure reconciliation, single-test
cap and no-retry behavior. It neither verifies live snapshots nor authorizes
writes. A complete lab-specific installation/restoration procedure still needs
review and a separate concrete human decision.

## Camera and report

Reuse the existing camera protocol as design input. Capability inventory exists;
recording, microphone-off behavior, framing and readable markers are not tested.
Do not activate hardware here. A later human-operated camera can observe a
self-contained RAM diagnostic; it cannot replace an independent stop/Recovery
path or prove unseen CPU execution. No remote Linux shell is promised.

Return the exact reviewed commit, both inventories, both file digests/sizes,
fresh method counts, actual semantic intake result and any actionable issue.
Distinguish freshly rerun checks from reviewed REA/VM/Apple-inspector records.
Keep native entry/EL/CTXR/18 physical cores/N1/GPU/NVMe/performance/camera/Recovery
and new policy/default checks **NOT RUN**. Keep old restoration unresolved unless
separate actual evidence closes it. Preserve the original worktree and all prior
consumed approvals; no restart or native preparation follows from this review.
