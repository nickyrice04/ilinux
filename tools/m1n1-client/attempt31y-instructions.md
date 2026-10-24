# M1 handoff: 31Y offline image-format and CPU2 plan review

**Offline review only. Native31Y HOLD / NOT RUN. No restart, proxy session,
installation or CPU2 start.** The user declined the proposed external post and
asked to keep investigating. This supersedes31X's pending-outreach wording and
draft: contact nobody. Preserve the frozen31X record itself.

## What advanced

The original format harness produces non-bootable Mach-O fixtures and optionally
submits only those files to Apple's read-only inspector. On M5's macOS26.6.2 /
25G83, the final20-case matrix has **six collection-loading errors, nine property
errors and five successful derivations**. All nine property failures returned
process exit0, so the strict classifier checks the actual output. Two successful
fixtures automatically derive nonzero `kcbz` from public boot/SPTM segment roles.
No supplied selector override or installed object is involved.

That is a repeatable format discriminator, **not installer or firmware acceptance**.
The one new REA query separates file analysis from caller-selected serialization;
indirect binding to both CLI subcommands remains unresolved. The remaining host
prerequisite is the applicable25G83 monitor-to-OS argument/version, fixups,
exception and memory-ownership contract. Public XNU supplies a useful comparator,
but its applicability and full platform interface remain unqualified.

The separate CPU2 plan derives a same-cluster control from five pinned public
inputs. It changes target bindings and non-target observer spans correctly,
while labeling expected identity as inferred. **No CPU2 controller, rebuilt
start leaf, live preflight or hardware qualification exists.** It is not a
predicted workaround or an instruction to repeat a native attempt.

## Review the new source and evidence

From the repository, inspect `git status --short`, preserve local work, then
use `git pull --ff-only`. Report divergence without resetting or discarding
evidence. Record the reviewed commit. Read:

- `research/native31y-format-probe.md`: the measured matrix, original harness
  and limits of parser success.
- `research/native31y-firmware.md` and
  `reverse-engineering/findings/cpu-startup31y/validation.json`: one successful
  query,116 returned instructions /136 P-code operations, and139 independently
  checked instruction words with zero mismatches.
- `research/native31y-host-source.md`: public monitor-to-OS entry, its difference
  from ordinary Aura entry, and the missing matching interface.
- `kernel/experiments/bootimage31y/README.md` and `expected-results.json`:
  fixture scope, strict classifier and full versioned reference signature.
- `kernel/experiments/smp31y-target/README.md`: CPU2 bindings, observation limits
  and the requirements a future controller would have to satisfy.
- `native/boot/attempt31y/validation.json`: the final handoff receipt.

Check the source manifest from the repository root:

```sh
shasum -a 256 -c native/boot/attempt31y/source-sha256.txt
```

Every entry must pass. Missing or changed evidence is a review failure to report,
not a reason to regenerate the reference or edit a frozen input. Hashes establish
file identity; the substantive claims still need review.

## Portable checks

Run only the new focused suites; older implementation suites need not be repeated:

```sh
python3 -I kernel/experiments/bootimage31y/test_probe.py
python3 -I kernel/experiments/smp31y-target/test_plan.py
python3 -I kernel/experiments/smp31y-target/plan.py
```

Expected: **14 format methods +9 CPU2 plan methods =23 passing tests**, with no
skips or repairs. The plan must emit `OFFLINE_CPU2_BINDINGS_PASS`, `target_cpu=2`,
`controller_present=false`, `deployment_ready=false`, `hardware_operations=0`
and `required_live_preflight="NOT SATISFIED"`. Its static pass is not native
readiness. Review row2 exclusion and row1/rows3–31 coverage, the separate CPU0
invariant, inferred MPIDR and the unreused CPU1-specific controllers.

Optionally generate the20 original fixtures without invoking any Apple tool:

```sh
python3 -I kernel/experiments/bootimage31y/probe.py \
  --output build/bootimage31y-m1-generated
```

Use a new ignored output directory; if that name exists, choose a new name.
Generation alone must remain `NOT_INSPECTED`. Never execute, install, transfer
as a boot package or add these fixtures to Git.

## Optional explicit read-only inspection on the Mac

This step is optional and independent of the portable review. Record the local
Python version, macOS product/build and local inspector identity:

```sh
python3 --version
sw_vers
shasum -a 256 /usr/bin/kmutil
python3 -I kernel/experiments/bootimage31y/probe.py \
  --output build/bootimage31y-m1-inspected --inspect
```

The runner also records the inspector hash in its local `results.json`. Use the
OS build plus that hash to identify the tool; do not claim the M5 tool version
when reviewing a different local binary. The runner uses explicit fixture and
nonexistent workspace collection paths, never real system collections. It does
not call `configure-boot`. No `sudo`, security change or installed-image access
is needed.

The reference is the **entire normalized20-case signature** in
`kernel/experiments/bootimage31y/expected-results.json`: fixture identities,
process exits, parser diagnostics and all derived properties. Matching aggregate
counts alone is insufficient. Report `completed_matrix`, `matches_reference`,
command exit and actual counts. A different signature on M1 or another macOS
version is evidence to retain and explain; do not weaken the classifier or replace
the reference to make it pass. A timeout, signal or environment denial is not
an image-format rejection and must not prompt a security-settings change.

Keep raw stdout/stderr and generated files under ignored `build/`. Report only
sanitized classifications, digests, public property values and relevant local
tool/build information. If this optional step is skipped or unavailable, mark it
**NOT RUN**; do not describe the portable tests as an inspector reproduction.

## Return the independent review

Write the standard dated review pair:

- `native/boot/attempt31y-m1-offline-YYYY-MM-DD.md`
- `native/boot/attempt31y-m1-offline-YYYY-MM-DD.json`

Use the actual review date. Record commit, manifest check, tools, both suite
counts/exits, plan outcome, substantive findings, and the optional inspector's
actual outcome or NOT RUN. Use `OFFLINE_PASS_NATIVE_HOLD` when the review has no
actionable blocker; skipping the optional inspector does not fail the portable
review. If a performed inspection differs, report that result for assessment
instead of claiming an unqualified overall pass or reference reproduction.

Private REA, Apple input decoding, independent instruction checks and VM execution
remain **NOT RUN on M1** unless independently performed; they are not required
for this handoff. Do not fetch or upload private Apple artifacts. Review their
published scope and qualification limits without claiming to have repeated them.

Update progress/coordination and push the review under the established repository
handoff authorization. Preserve all frozen31X/prior records and unrelated work.
No external contact, repeated security check, restart, native controller,
installed-image change or hardware session follows from this review. The outcome
remains a narrower software lead with a specific unresolved host contract,
not a working local SMP solution or proof that only Apple can fix it.
