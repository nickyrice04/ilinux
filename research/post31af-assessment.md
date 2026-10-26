# After 31AF: pause silent restart tests, qualify entry offline

2026-10-26 Eastern. **Decision: no new experiment restart is ready. Continue
bounded offline investigation; an Apple-only stop has not been established for
the alternate host. A vendor firmware dependency remains a serious possibility
for native multicore.** First complete or confirm the existing restoration.

## What the result establishes

The [direct human report](../native/boot/attempt31af-human-2026-10-26-result.md)
says 31AF installed successfully, then showed only the Apple logo. Numeric exits,
actual duration and an independent capture were not supplied. The human returned
to macOS but could not confirm exact boot021 rollback or the default restoration.
Do not fill those gaps from the prior 31AE session. The install/observation is
consumed; only the unfinished restoration from its authorization remains.

This is an unresolved custom-host entry/display result. 31AF never attempts a
secondary start, so it cannot itself reproduce a CPU-startup prohibition. Earlier
[attempt 27](../native/boot/stage-b-2026-10-20-attempt27-result.md) already reached
native Omarchy through the raw path. That progress stands; it did not establish
multicore, GPU or performance parity. The experimental resident route seeks a
different firmware context for the unresolved physical CPU startup.

## Remaining software assumptions found in original code

1. **Complete image readability.** `immutable31af/entry.S` calls
   `immutable_readable(native_image_base, 0x60000)` before parsing the video input.
   That includes the monitor-owned `0x54000` reservation. It walks the complete
   image again for framebuffer alias protection. Removing writes into the
   reservation did not remove this read-translation dependency. The original
   41-case evidence mapped it readable/read-only; it did not test inaccessible
   pages. Native reservation readability remains unmeasured.
2. **Entry profile.** The observer parks immediately unless CurrentEL is EL2;
   it additionally requires cold reason 0, recognized HCR/MMU/input/helper/table
   state and supported attributes. Retained [entry analysis](native31ab-entry.md)
   permits different ELs depending on the monitor's own state. Its native value
   has not been captured. A valid but unsupported entry is indistinguishable
   from failure before entry on the present screen-only test.
3. **Actual loader-to-entry selection.** The retained
   [producer review](native31y-firmware.md) leaves part of the indirect raw versus
   collection mode binding unresolved. Installation success validates an
   installer gate, not the complete executing firmware path. Raw boot021 takes
   BootArgs in x0; the resident observer takes a reason in x0 and distinct
   argument records in x1/x2. Wrapping raw boot021 without a qualified adapter is
   not a positive control for that contract.
4. **Observability.** Refusal/fault status stays in registers with no native
   retrieval path. Framebuffer translation and actual panel scanout are separate
   requirements. No qualified independent early loader/entry channel is currently
   provided by these files. An unqualified UART or monitor call would add another
   assumption rather than prove entry.

These are documented dependencies and hypotheses, **not diagnoses of the native
logo-only result**. Do not remove address/alias protections just to obtain output.

## New bounded offline qualification

The original [qualification wrapper](../kernel/experiments/entry31af-qualification/README.md)
executes the exact released 31AF payload under controlled missing mappings. Two
paint controls and ten omission cases cover 4-KiB ordinary EL2 and 16-KiB VHE.
Each omission removes one 16-KiB range: first/middle/last reservation, unused
header or unused ordinary text. Boot entry, vectors and reachable helpers stay
mapped. The original full-byte preservation and no-partial-paint checks remain.

The [validation receipt](post31af-qualification.json) records **12 execution
cases PASS** in the isolated VM: two full 8192-pixel paint controls and ten
status-7 refusals without any framebuffer change. An independent comparison
confirms all 48 before/after payload/input/table/scratch pairs are equal. Both
4/16-KiB profiles execute unchanged released instructions, with the existing
fixture's A5-populated monitor reservation in modeled RAM; the original on-disk
payload remains unchanged. This demonstrates a
synthetic case where entry executes but no marker appears; it does not identify
the native mappings or prove firmware acceptance. No new native image is
produced; frozen sources, payload and receipts remain unchanged.

The initial VM setup did not run a case because the private job script lacked
its executable bit. That idle guest was stopped by signal, the permission and
pre-launch check corrected, and a separate successful run exited 0 and shut down
normally. Both workspace locks were released. Compiler command configurations
are retained; compiler/binutils versions were not freshly queried in this run.

## Public evidence: take the firmware risk seriously

Gravity's current FAQ attributes M5 Pro/Max secondary-start failures, as of its
tested macOS 27.0 Beta 5, to platform misconfiguration and says its project is
waiting for Apple. This is a relevant maintainer assessment. Its public statement
does not specify a complete mechanism or establish the exact local J716c/25G83
case. [Current FAQ](https://gravitylinux.org/about/),
[pinned source](https://github.com/GravityLinux/website/blob/cfc74e6b3fcdb2f794fbf725464f27b506ad8d21/content/about.md#L53).

Asahi's T6050/T6051 bring-up report separately says cores power on but do not
execute secondary code on the tested 26.2b2 and 27.0b2 versions. This corroborates
the observed failure class without proving a workaround impossible.
[Primary report](https://github.com/AsahiLinux/m1n1/pull/610).

A historical resident-SPTM report claims eighteen CPUs and per-core checks on
J714s/M5 Pro with firmware 26A428. That remains a useful alternate-route lead,
not independent replication on our board: the matching accepted resident host
and complete physical-entry evidence are unavailable in the located public
source. [Qualification report](https://github.com/chriskearney/siliconforest-linux/blob/5c978948f42c44c725d621bde31d70cd3439167c/Documentation/arch/arm64/t6050-sptm-ans.rst),
[guest probe change](https://github.com/chriskearney/siliconforest-linux/commit/6c03bd926fc5672dc91457053c13b3e83ad30048).

Fresh checks of Aura, Asahi m1n1, SiliconForest m1n1/Linux, antiapplefox and
Gravity's website found unchanged default heads relative to our retained pins.
No newly published reproducible matching resident host was found in that bounded
review. Aura still excludes its internal Mach-O/SPTM work from the documented
release; its ordinary Mach-O output is not a qualified replacement.
[Aura scope](https://github.com/aurora-silicon/aura/blob/ec4a6ab8b4252079e78196515577d73ef0a86135/docs/releases/0.1.0.md#L68).

## Next gates and stop criterion

1. Reconcile or finish exact boot021 rollback and original desktop/default
   restoration. [M1 restoration-only follow-up](../tools/m1n1-client/attempt31af-result-followup.md).
2. Trace the actual installed-image producer/caller binding using authorized
   local REA, with raw Apple artifacts confined to ignored build storage. Qualify
   the entry reason/register bank and legitimately available memory boundaries.
3. Design an original diagnostic with only necessary read dependencies while
   retaining conservative framebuffer alias protection. Add missing-mapping and
   relevant entry-profile cases offline. The new regression identifies a gap;
   it does not qualify replacement address guards by itself. Existing BootArgs
   field offsets do not prove a contiguous physical image boundary: qualify the
   matching producer/consumer before using physBase, virtBase or topOfKernelData
   to replace translations. A guessed VA-to-PA offset is not an adequate guard.
4. Require either a qualified independent observation of entry/failure, a working
   positive control for the same resident contract, or a reproducible accepted
   host before another experiment restart. Do not repeat silent marker variants
   based only on successful synthetic fixtures.
5. If a required state is unavailable through a permitted software path, or
   progress depends on unpublished host code or a vendor correction, mark native
   multicore **blocked pending external support**. External support could be
   community source or an Apple update; present evidence cannot narrow it to
   Apple alone. A verified restriction is stronger evidence than another blank
   screen, but pausing expensive testing does not require proving impossibility.

No near-term macOS-class native performance is promised. Observable entry,
physical SMP, GPU acceleration, power management and measured parity are separate
substantial gates. Existing VM work remains usable independently of this route.
