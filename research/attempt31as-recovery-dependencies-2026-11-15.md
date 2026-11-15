# Recovery dependencies after the 31AR stop

November 15, 2026. Independent source review only. No host query, system
command, mount, installation or recovery-state modification was performed for
this review.

## Observed boundary

The [31AR result](../native/boot/attempt31ar-recovery-2026-11-15-result.md)
records a real shell error for the unavailable absolute `/usr/bin/cmp`, then
the fixed refusal and returned prompt. Both comparator sites in the frozen
`tools/recovery31ar/render.py` precede controller dispatch. Consequently this
paste did not reach controller enrollment, its managed Preboot mount or an
Apple writer. The photograph does not separately label the comparator site;
the first is likely, rather than independently identified.

This is a shell dependency failure. It supplies no new candidate, CPU startup,
firmware handoff or Linux performance result. The exact claim is that the
requested path was unavailable to that Recovery shell. It is not evidence that
every possible comparator path is absent.

The owner separately confirmed Macintosh HD desktop and default return.
**Boot021 restoration remains outstanding:** no restoration was run, and
desktop return does not identify the lab's selected boot object. Original Full
remains the required invariant; no new final policy query is claimed.

## What existing physical evidence qualifies

The [31AP result](../native/boot/attempt31ap-recovery-2026-11-15-result.json)
contains actual successful Recovery collection, admission and owned read-only
mount cleanup. Its shell is generated through the frozen 31AP, 31AM and 31AL
renderers and the 31AK held-directory block. That provides useful prior
dependency evidence, with these limits:

| Dependency | Evidence and limit |
| --- | --- |
| `/usr/bin/id`, `/usr/bin/mktemp`, `/usr/bin/stat`, `/bin/pwd` | Required on the successful 31AP flow and before 31AR's comparator stop. No path change is needed. |
| `/bin/cat` | New public-profile heredoc materialization in 31AR, preceding either comparator. Its required shell branch was passed before this stop. |
| `/bin/cp`, `/bin/chmod` | Required for copying and admitting the helper on the successful 31AP flow. |
| SHA-256 fallback | The same preference for `/sbin/sha256`, `/usr/bin/shasum`, then `/usr/bin/openssl` was required by 31AP. At least the selected branch worked. The result does not identify that branch or prove all alternatives exist. |
| `/usr/bin/awk` | Used only by the shasum/openssl alternatives. Its availability is not separately established if sha256 was selected. The new repair removes this dependency. |
| `/bin/rm`, `/bin/rmdir` | Present in the old shell's exit cleanup with suppressed errors. A visible diagnostic pass alone does not separately establish availability or successful scratch removal. Check executability before the controller in the repaired page. |
| `/usr/bin/cmp` | Introduced in 31AR; actually unavailable at the observed stop. Remove the dependency from both complete operation blocks. |

This table is a source-based interpretation of actual earlier execution, not a
new inventory of the running Recovery image. Kernel mount tools and Apple
writer availability are additionally managed by the unchanged native
controller; shell preparation does not establish those later outcomes.

## Repair acceptance criteria

The narrow repair retains the exact existing helper, public profile,
candidate, boot021, lab kit path and fresh transaction-state namespace. It
replaces both comparator calls with the already pinned profile byte length
and SHA-256. This applies the same content-integrity assumption already used
for every executable artifact; it does not admit a differently formatted
profile or relax the native profile/self binding.

Preserve the hash tool preference, but check the selected producer's exit
status before printing any digest. Parse its fixed output using Bash rather
than adding another external command. A nonzero producer that printed the
correct digest must still refuse. Missing, malformed or unavailable hashing
must refuse before controller execution. Preflight the remaining required
shell utilities with built-in tests, including success-path cleanup tools.

Executed shell controls should cover both complete install and independent
restore blocks, correct and corrupted staged/copied profiles, absent hashing,
valid-looking output with nonzero hash status and the unavailable-comparator
environment. Controller interception in that harness is a shell-boundary
fixture, not native installation or hardware identity evidence. Retain the
already tested real native controller and its original phase-validation
evidence separately.

No source-only page test can prove live APFS RW behavior, Apple's mutation or
authentication behavior, native entry, all-core execution or smooth Omarchy.
Those remain separate physical observations after the repaired page is
reviewed and the later native cue is issued.

## Independent implementation review

Reviewed the frozen `tools/recovery31as/package.py`, tests, README and M1
handoff. The implementation performs four exactly reversible substitutions in
each original operation block: fixed executable preflight, checked hash
producer with builtin parsing, and the two pinned profile checks. The new
167-source closure retains all 162 original inputs. The helper, profile, kit,
state namespace and native transaction logic are unchanged.

Independently executed all **19 focused methods**, with **zero skips**, in
**76.290 seconds**. Both positive complete bootstrap paths, candidate-free
restore, all three hash producers, status/output errors, content/copy/symlink
refusals and each missing fixed utility passed. Package, whole-box, exact
source-closure, route and inert preparation controls also passed. These are
the executed shell fixtures described above, not native-controller execution.
No remaining actionable source or privacy finding was identified. No host
query, server, mount, Apple writer, new staging or native boot was performed.
