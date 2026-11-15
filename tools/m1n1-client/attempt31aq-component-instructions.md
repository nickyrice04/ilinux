# M1: 31AQ full-helper component review only

M5 reviewed `459161d`: 31AP's real guarded collection, initial admission and
owned read-only mount cleanup passed. Macintosh HD desktop/default return is
human-confirmed. No repeated 31AP check, routine mode query or restart is needed.
Original Full passed that Recovery admission; boot021 restoration is still
outstanding. The result establishes no new Aura/Linux entry or multicore rate.

The next physical objective is a complete matched Aura/Linux RAM boot with
exact readback, one timed observation and independent verified boot021 rollback.
The surrounding write-capable transaction is **not ready yet**. This handoff
reviews only its newly implemented read-only full-helper backend.

## What is implemented

Review tools/boot-object31aq-native/ and native/boot/attempt31aq-component/.
The original full31AJ CLI, core recognizer, JSON and header stay byte-exact;
the complete 31AO typed state and v3 HMAC replace only the old state semantics.
The builder verifies 140 old AP inputs plus three source-page inputs and proves
exact reversal and diagnostic-only mark removal. It adds no Apple write API.

M5 built the component with clang21/SDK27.2, arm64/min13: 89504 bytes,
SHA-256 271f24012fa632c328bc92bd5310362aed700fc41cddb75c793c6f9bb4c1769c.
Its public component profile is a self/artifact binding, not an install kit or
execution instruction. Do not stage it or substitute it into the old31AJ or
31AP pages. Old keys, baselines, profiles and spent markers remain untouched.

18 focused methods pass normally, under ASan/UBSan and in independent normal
review. The real original31AF, existing candidate and boot021 identities run
through fresh keyless admission, own-random private key, key-bound baseline,
candidate, raw-policy and restored validators. Both-role metadata drift,
presence, independent HMAC contract, wrong key/profile, unsupported data and
intended nonce/object/CTRR transitions are covered. All policy/volume metadata
are synthetic. This is not actual installation, restoration or firmware entry.

## Review limits and next implementation

The actual31AP success ended with Preboot **unmounted**. Old transaction code
expects a mounted view, and a read-only view is insufficient for installation.
Asahi's public path normally arrives with Preboot mounted; it does not prove
`kmutil` will automatically mount or promote ours. Review the concrete design
in research/attempt31aq-preboot-lifecycle-2026-11-15.md.

The missing controller must establish owned RO admission and a fresh bound
baseline, transition explicitly to verified owned RW capability only for the
separately authorized lab operation, validate readback, then verify cleanup
before a boot cue. It must preserve foreign mounts, refuse uncertainty, persist
durable private baseline/attempt state, avoid retries, bind target identities
across visits privately and keep rollback independent of candidate availability.
Those implementation/physical properties are not supplied by this component.

Review the three new sources and proof/fixture evidence. If useful, independently
compile and run the README's focused controls with already held verified original
artifacts in fresh output directories. If a reference is absent, report that
specific coverage limit; do not request a new large image transfer or mock an
identity to mark a pass. Do not repeat old suites or inspect raw Apple analysis.
Report your compiler/SDK and distinguish your compiler output from M5's hash.

No page server, helper transfer, staging, M1 restart, proxy, camera, Recovery,
mount, policy/security/default change, install, restore or Linux boot is requested.
Publish only sanitized component findings. Keep native readiness false and
install/restore/Linux/SMP/performance NOT RUN. M5 continues the managed
transaction integration; this review creates no physical handoff.
