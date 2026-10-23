# 31W: CPU workaround evidence and a practical stop condition

Checked 2026-10-23 after M1's 31V review, merged as `9befeb3`. This is a bounded
public-source investigation. No downloaded source ran; no hardware, firmware,
installation, upstream communication or private conversation was involved.
The target remains the locally identified J716c/T6050 M5 Max with retained
25G83 boot evidence. Earlier notes and consumed experiments remain frozen.

## Decision

**No verified software workaround for this machine's secondary-entry failure
is available in the sources checked. “Only Apple can make it work” is also
not established.** Those statements are compatible: the CPU work is practically
blocked by missing actionable evidence, even though all software alternatives
have not been disproved.

Stop unchanged native CPU-start experiments. They have no new discriminating
input. Further native SMP work should wait for either a qualified accepted host
bootstrap, or a specific missing startup condition with an independently
observable prediction. Continuing to build or repackage speculative shims does
not supply either. This is a practical defer decision for the CPU bring-up
track, not proof of permanent hardware impossibility or a requirement to abandon
independent GPU/offline work.

## What is actually established

| Evidence class | Established fact | Remaining uncertainty |
|---|---|---|
| Local native observation | The consumed [31N result](../native/boot/attempt31n-2026-10-22-result.md) confirms completion of the adjacent CPU1 start stores, with no committed identity in the observed channels. The [image/publication audit](native31n-result-review.md) covers the raw image, matching reset mirror and PoC publication. | Effective CPU1 first fetch, incoming translation/protection state and an alternative unobserved entry remain unknown. Power/state changes and CPU0 controls are not CPU1 execution proof. |
| Attributed firmware diagnosis | [Asahi PR610](https://github.com/AsahiLinux/m1n1/pull/610) reports powered secondaries without code execution. Its [reviewer](https://github.com/AsahiLinux/m1n1/pull/610#discussion_r3514334184) suggests an iBoot/firmware bug, and the [author agrees](https://github.com/AsahiLinux/m1n1/pull/610#discussion_r3514495744). | The discussion does not identify an exact blocking operation, inaccessible state or accepted workaround. The merged initial-support patch is not a demonstrated root-cause proof. |
| Project assessment about Apple | [Gravity's pinned FAQ](https://github.com/GravityLinux/website/blob/cfc74e6b3fcdb2f794fbf725464f27b506ad8d21/content/about.md) attributes M5 Pro/Max startup failure to platform misconfiguration, says Apple was informed and says the project must wait. | This is Gravity's assessment. It contains no public Apple response, Feedback record, root-cause mechanism or fixed build. The scoped searches found no such corroboration; private reporting may exist. |
| Alternate-path positive lead | The [SiliconForest report at `5c978948`](https://github.com/chriskearney/siliconforest-linux/blob/5c978948f42c44c725d621bde31d70cd3439167c/Documentation/arch/arm64/t6050-sptm-ans.rst) attributes 18-CPU Linux operation to a resident-SPTM host on J714s/26A428. | The exact accepted host object, initial monitor context and physical-secondary provenance are unavailable in the located material. A guest CPU count does not itself establish how many physical CPUs executed it. |
| Public implementation boundary | Aura's [pinned release](https://github.com/aurora-silicon/aura/blob/553b566f69275ff4e46ee6542a7236fb80a333a2/docs/releases/0.1.0.md) excludes internal Mach-O/SPTM host development. [31V](native31v-upstream.md) compared its actual startup code: applicable WFE policy is post-arrival; special entry changes target other SoCs/layouts. | Acknowledging x1n1 development is not publication of the host used by the positive report. No accepted native alternative follows from the ordinary public image outputs. |

The firmware/handoff explanation is credible and supported by upstream
observations. The stronger assertion that no permitted software boot path can
work is a different claim. None of the located sources establishes that claim
for this board and firmware.

## Firmware versions do not form a controlled fix/regression test

The reports span several releases, but change machines, images and observation
methods. They must not be treated as a same-machine firmware A/B experiment.

| Platform and reported environment | Reported result | Scope |
|---|---|---|
| M5 Pro; 26.2 beta 2 and 27.0 beta 2 | Powered secondaries do not execute m1n1 code. | Original [PR610 report](https://github.com/AsahiLinux/m1n1/pull/610); no exact local 25G83 comparison. |
| J714s, 15-core M5 Pro; 25F71, mBoot-18000.120.36 | No early CPU1 marker in the author's custom-loader experiments. | [Pinned findings](https://github.com/betizzel/omarchy-m5/blob/15cd70c1fad65322b85be4de4362cbed816a11c1/docs/smp-t6050-findings.md); [31T](native31t-upstream.md) explains why its boot-CPU register probe cannot establish every secondary's effective state. |
| J716c, local M5 Max; 25G83, mBoot-18000.161.10 | Adjacent start stores complete; CPU1 identity unobserved. | Our [consumed 31N evidence](../native/boot/attempt31n-2026-10-22-result.md), with no firmware switch performed by this research. |
| M5 Pro/Max; 27.0 beta 5 | Gravity still reports the platform issue. | [Project FAQ](https://github.com/GravityLinux/website/blob/cfc74e6b3fcdb2f794fbf725464f27b506ad8d21/content/about.md); not a published test matrix or Apple confirmation. |
| J716s, 18-core M5 Pro; 27.2 boot objects, mBoot-20457.41.2 | Raw-path secondaries remain unobserved; proposed Mach-O/BootKC images rejected before iBoot. | [Independent report](https://github.com/rolotrealanis98/m5pro-linux/blob/bb0c75e69d06247faf595641c5a12b0fadc415d2/docs/smp-t6050-raw-path.md); no qualified accepted alternative. |
| J714s, M5 Pro; 26A428 | Author reports all 18 Linux CPUs under resident SPTM HV. | [Positive guest report](https://github.com/chriskearney/siliconforest-linux/blob/5c978948f42c44c725d621bde31d70cd3439167c/Documentation/arch/arm64/t6050-sptm-ans.rst); different host route, missing physical-entry evidence. |

This table supports persistence of the reported raw/custom-loader problem. It
does not identify a working firmware version, prove that a newer version fixes
it, or establish that every release has the same root cause. The positive guest
report is not a controlled counterexample for the local raw-image path.

## Fresh exact-board code check: PR631 is not a demonstrated workaround

The scoped search surfaced
[Asahi m1n1 PR631, “T6050 j716c bringup”](https://github.com/AsahiLinux/m1n1/pull/631).
It is closed and unmerged, with head
`2f70530e15de90e3106f8c5fdb12d9d829781d39`. Inspection of its actual
[source changes](https://github.com/AsahiLinux/m1n1/pull/631/files) found:

- Validation/reporting of the ADT `Core` descriptor; no implementation of an
  additional firmware/platform operation merely because that descriptor exists.
- A masked reset-destination comparison and refusal on mismatch.
- A stop after the first failed secondary, preservation of its target/stack on
  timeout, and MPIDR-to-stack reuse after a CPU's first entry.
- The existing two PMGR start writes remain unchanged. No successful physical
  secondary-entry result accompanies these changes.

These are useful diagnostic and lifetime protections, not a new release
prerequisite. The relevant local frozen work already isolates CPU1, preserves
its startup state, checks the raw entry/mirror relation and performs the pair
without host traffic between its stores. This PR therefore supplies no distinct
next stimulus for the failed local case.

The newly checked [Asahi documentation PR279](https://github.com/AsahiLinux/docs/pull/279/files)
corrects device release years and overview links. Its support-table context is
not a CPU root-cause analysis or a firmware workaround.

## The proposed XNU shim has not acquired runtime proof

The refreshed antiapplefox repository is still
[`35695e2a91feaff53e9df7b62bd1ab030bc58be0`](https://github.com/antiapplefox/m5-linux/tree/35695e2a91feaff53e9df7b62bd1ab030bc58be0),
the same source inspected in 31T/31U. Its current
[README](https://github.com/antiapplefox/m5-linux/blob/35695e2a91feaff53e9df7b62bd1ab030bc58be0/README.md)
makes strong static BootKC/SPTM conclusions while explicitly disclaiming hardware
bring-up, a working shim and a working Linux MMU port. The prior
[actual packager/scaffold audit](native31u-upstream.md) still applies; no new
revision has repaired those implementation gaps or supplied image-acceptance
and physical CPU evidence.

Asahi's [own explanation](https://asahilinux.org/2026/08/progress-report-7-2/)
supports a conditional firmware path: XNU detection loads SPTM, but presenting
ordinary m1n1 as XNU conflicts with its expected memory-management environment.
A compatible alternate host could therefore require a substantial continuing
contract, not one extra initialization call. Its restored SPTM guest tracing
also means that a blanket claim of hypervisor impossibility is too strong.
Neither point supplies the missing physical T6050 host bootstrap.

Fresh head checks leave [Asahi](https://github.com/AsahiLinux/m1n1/commit/7cde7d1a784d851ebfee5579fa363c38b14150c0)
at `7cde7d1a784d851ebfee5579fa363c38b14150c0`,
[Aura](https://github.com/aurora-silicon/aura/commit/553b566f69275ff4e46ee6542a7236fb80a333a2)
at `553b566f69275ff4e46ee6542a7236fb80a333a2`, and Gravity's FAQ at
`cfc74e6b3fcdb2f794fbf725464f27b506ad8d21`. Aura still exposes only
[`main`](https://api.github.com/repos/aurora-silicon/aura/branches?per_page=100),
the same [six public PRs](https://api.github.com/repos/aurora-silicon/aura/pulls?state=all&per_page=100)
and [no public releases](https://api.github.com/repos/aurora-silicon/aura/releases?per_page=100)
through the checked API. Its
README history adds no newly published host contract since 31V. The positive
SiliconForest report remains tied to its cited commit; its document path returns
404 at the [current default tip](https://github.com/chriskearney/siliconforest-linux/tree/65cd54ba0da8f93e4530f851382ccb5187ab794c)
`65cd54ba0da8f93e4530f851382ccb5187ab794c`.
That is a location/version limit, not evidence of retraction or falsity.

## Continue, defer, or conclude firmware dependency

| New input | Appropriate next action | What it would establish |
|---|---|---|
| Exact accepted host source/object description, revision, board/firmware and initial monitor context, linked to one physical non-boot CPU's entry | Compare that route offline with the retained raw path; only then assess a bounded original implementation. | A concrete software alternative worth qualifying. Not automatic compatibility with 25G83 or all-core Linux. |
| A precise missing startup condition, ownership/access requirements and predicted observation, supported independently of CPU0/guest shadows | Design an offline check that discriminates it; assess native scope separately. | A testable hypothesis. More range setters or another zero marker alone do not meet this condition. |
| An Apple or independently reproducible fix tied to a specific build and unchanged board/image setup | Review its scope and changed prerequisites before considering any firmware-dependent plan. | Evidence of a firmware fix for that setup, not proof that no software alternative ever existed. |
| Only unchanged source heads, a general support table, compilation success or an attributed guest CPU count | Defer native CPU work; preserve the existing evidence. | No new actionable CPU-start hypothesis. |

To justify **“Apple is required for this raw boot path”**, the missing condition
must be identified and shown to be fixed before handoff in a state that permitted
post-handoff software cannot supply or change. To extend that conclusion to
**every permitted software path**, an accepted alternate initialization route
must also be excluded by evidence. Neither level is established here. Absence
of located public code is insufficient, and working macOS alone does not prove
that its initialization is available to a custom loader.

The minimum next input is consequently concrete: **the actual accepted host
bootstrap and physical-entry provenance from a reported successful T6050 run,
or one independently qualified missing condition in the local raw path**.
Until then, no further unchanged reboot is justified. A user who needs a usable
native Linux system rather than open-ended bring-up research can reasonably
defer this CPU track now without accepting an unsupported Apple-only claim.

## Retention

Fresh checks cover relevant issue/review metadata, exact-board code, firmware
reports, current heads/branches/releases and narrow commit searches. Small
sources and scoped API metadata remain under ignored `build/research31w/public/`,
with URL/time/hash manifests and validation. Unrelated issue bodies, personal
profile fields and diagnostic-file patches were omitted from retained search
metadata. Failed requests are recorded, including the corrected website branch
request and the missing current-tip report path. No downloaded source was
imported or executed; no large or proprietary artifact was downloaded.
