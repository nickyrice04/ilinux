# M1: 31AV offline review, keep both Macs in macOS

November 15, 2026. This is a new **offline component review**, not a Recovery
page, replacement boot package or restart cue. The consumed 31AU attempt is
closed. Do not restart either Mac, start a page/proxy, stage files, run a target
controller, query private policy/state, or reset/re-arm any earlier transaction.

## Read the actual result first

Use `native/boot/attempt31au-recovery-2026-11-15-result.md` at `9a6411c`.
The writer returned zero, selection changed and the selected file was readable,
but IMG4/LZFSE decoding did not complete. Lab CTRR remained disabled. The
controller refused and no candidate boot occurred. Restoration and Original
desktop/default are human-confirmed with the report's stated transcript limits;
do not ask the owner to repeat a security check.

## Review the new components

1. Read `native/boot/attempt31av-plan.md`, `tools/codec31av/README.md` and the
   `research/attempt31av-ctrr-2026-11-15.md` finding with its finite JSON. Keep a reproduced desktop codec
   counterexample distinct from the unavailable actual Recovery carrier.
2. Verify the new tool's source/build bindings and the unchanged 190-source AU
   closure. No generated helper replaces the staged AU helper. Check source
   path confinement, explicit inert default, no live collector, allocation and
   input/output bounds, and exact known size/SHA-256 admission.
3. Run the new codec suite with the installed Apple SDK, normally and under
   ASan/UBSan, following its README. Use only deterministic generated fixtures
   and an already-held exact project candidate. If that candidate is missing,
   report its method **NOT RUN** and run the remaining named methods; do not
   substitute synthetic bytes for genuine-artifact evidence or request another
   large transfer merely to reproduce an existing producer result.
4. Check the decisive regression: a valid Apple-encoded deterministic 1 MiB
   fixture fails the original 64 KiB stream decoder but passes the proposed
   bounded buffer path. Validate deliberate refusals, including malformed or
   truncated frames, trailers, bad declared counts, unsupported/keybag forms,
   bounds and wrong known hashes. Buffer API success alone must not admit an
   object; strict framing, the extra destination byte and exact size/hash remain
   required. A different M1 runtime outcome must be reported as observed rather
   than forced to match M5.
5. Review the REA/LLVM findings as a qualified client-side request trace. A
   request sent to BootPolicy does not establish service-side SIP2 semantics or
   historical Recovery compatibility. Do not infer an enable-only writer, policy
   workaround, firmware rejection or requirement to wait for Apple.

## Return an efficient report

Publish original prose and finite JSON: source pins, runtime/toolchain versions,
method pass/fail/not-run counts, deterministic counterexample, refusal results,
new actionable findings and explicit limits. Generic library extraction and raw
REA/decompiler output remain ignored and are not transferred or committed.
Native Linux/SMP/GPU/performance remain **NOT RUN**. Preserve prior evidence,
all keys/baselines/spent receipts and the closed AU state.

Recommend the next offline change or a specifically informative future Recovery
check. No install, boot, setting, firmware or security action is authorized by
this handoff. Macintosh HD remains protected at Full Security.
