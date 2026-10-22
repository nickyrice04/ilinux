# Attempt31J — connection succeeds; power and opaque state change without entry marker

**Observed,2026-10-21 Eastern:** one authorized31J invocation verified the
primary interface on the first cached query and reached the unchanged CPU1
campaign. Result **STOP / cpu1_arrival / cpu1_arrival_timeout**, exits **1/1**,
no supervisor deadline. **Native attempt consumed=true.** Both CPU1 starts were
attempted/acknowledged, **66 explicit mutation intentions**.

CPU1's PS actual field changed **0→15** and opaque low byte **0→2** after the
second start. CPU0 stayed15/2. All four paired observations completed, **8 PS
reads and8 core-state reads**, errors null. **93 complete recorder samples/465
reads stayed phase0**, no committed identity or reset record. These register
transitions do not prove CPU1 instructions, reset release, running state or PC.

Controller **5.270s**, supervisor **5.679s**. Human confirmed normal Macintosh
HD at **+45.136s**, within90s. **No retry/reconnect/further target command.**
CPU1 arrival/callback progress/park remain unverified; **Linux boot/native Linux
SMP NOT RUN**. No all-core/performance or efficiency claim.

Reviewed exact final outputs:
[controller](attempt31j-controller-2026-10-21.json),
[supervisor](attempt31j-supervisor-2026-10-21.json).
Private journals/stderr, registry data, full register words, USB paths and
identifiers remain under ignored build; no raw artifacts are published.

## Provenance and offline verification

Handoff `ad9892e9858e34539d611ee2f9b7645c25a5ad6d`;
published readiness/execution `3277ca13bc8013640d8ba78bf7d4481d49abdc0b`.
[Independent M1 readiness](attempt31j-m1-offline-2026-10-21.md): **226 source
pins/579 image-only methods PASS**, no skips/repairs. Both documented offline
commands and retained13-file package check exit0. Symbol mode
`reviewed_layout_only`; **full-symbol checks NOT RUN on M1**. M5's separate
VM/full-symbol/wire validation is offline evidence, not this native result.

31J manifest SHA-256:
`360c1939430bbcf3a0b946a00fc1fe5d20b96b0b711998c36fde07cecf6fe765`.
Existing3,932,160-byte boot021 image:
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
Clean client remains `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
All226 pins, frozen31I202/host-only6 inputs and prior31B–31I plus separate
host-only31J evidence remain unchanged. No source fix, image transfer or install.

After publication, human authorized **“Start 31J; all confirmed”**: fresh lab
Running proxy, powered Macs, direct known-good cable seated, healthy awake/
unlocked/open-lid M1 and independent90s timer. Setup facts are human-reported.
Timer cue preceded the single documented supervisor; wrapper start
**2026-10-22 03:14:23.474 UTC / 2026-10-21 11:14:23 PM Eastern**.
No separate USB checker or manual handshake preceded it.

## Discovery and connection

| Evidence | Recorded result |
|---|---|
| Cached query attempts / returns | 1 / 1 |
| Query category / output kind / stderr | primary_verified / xml_plist / absent |
| Inventory classified / primary verified | true / true |
| Modem interfaces / primary candidates | 2 / 1 |
| Query start offset / query elapsed | 0.000185s /0.020308s |
| Total discovery elapsed / ready | 0.020810s /true |
| Discovery native_ready / progress failure | false /false |
| Source/pin recheck | passed |
| Client import attempted / returned | true /true |
| Native reservation attempted / consumed | true /true |
| Serial open attempted / returned | true /true |
| UART init attempted / returned | true /true |
| Proxy init attempted / returned | true /true |
| Controller construction attempted / constructed | true /true |
| Last connection phase | controller_run |
| Transport close attempted / closed | true /true |
| Connection/native journal failure flags | false /false |

Discovery's **device_opens0,target_requests0** apply only to cached registry
observations. The subsequent serial open and target campaign occurred; these
zeros are not totals for the session. Native_ready=false is also discovery's
local scope. The pure reset-decision hardware_operations0 likewise describes
local report validation, not an absence of target operations in this run.

The parent reservation's **consumed=false/scope=supervisor_invocation_only** is
a static invocation record. The child's final **native_attempt_consumed=true**
and consumed journal establish native consumption. Both receipts remain and
block reentry. Parent controller_started=true means process spawn; this run
also has independent constructed/run evidence. No enumeration wait/retry was
needed; one query and one serial-open attempt only. No finalization error field
or outer-deadline/interruption field was emitted. Transport closed locally.

Connection journal: **19 complete rows**; consumed journal: **142 complete
rows**. Controller stderr contains only the expected clean-client pin line.
Raw rows are retained privately, not copied into the public report.

## Reset readback and publication gates

Exactly **2 existing reset reads/2 returns/2 immediate guard acknowledgements/
2 validated rows**, complete observation, mirrors equal, error null. Both rows:
legacy vector page match=true, bit0 lock classifier=true, bit11=false,
low11:1=zero, firmware bits41:11=image_base, bits10:1/47:42=zero,
upper63:48 present and high63:42 nonzero. Corrected firmware-backed gate passed:
`RESET_ADDRESS_READBACK_PASS`, upper field **present_uninterpreted**.
Exact entry/effective reset route and upper semantics remain **UNKNOWN**.
The address comparison mask is fixed source metadata, not a captured raw word.
A passing readback contract does not prove instruction fetch or reset routing.

RAM: all11 predicates true, BootArgs revision3. Direct USB/expected UART bases
true, initially2 enabled diagnostics, RAM zeroes published. Live ADT binds the
two32-bit PS locations and all18 topology routes; CPU1 startup mapping unchanged.
CPU0 **EL2**, regime verified; all16 code probes,2 PS and2 added core-state
translation checks PASS. Identity-code write booleans represent expected write
**denials**, not a new grant or remap. Recorder body/vector hook/whole text
readback PASS. Existing helper/recorder bytes and protections unchanged.

## Combined power and opaque core-state observations

| Sequential phase | CPU0 PS desired/actual | CPU1 PS desired/actual | CPU0 byte | CPU1 byte | Bytes equal |
|---|---|---|---:|---:|---|
| before_start | 0/15 | 0/0 | 2 | 0 | false |
| after_first_start | 0/15 | 0/0 | 2 | 0 | false |
| after_second_start | 0/15 | 0/15 | 2 | 2 | true |
| final (natural arrival expiry) | 0/15 | 0/15 | 2 | 2 | true |

For both CPUs in all four PS samples, parent_missing/device_disabled/
auto_enabled are false. PS8/8,4/4 complete pairs,error null. Core-state8/8,
4/4 complete pairs,error null,journal_failed=false. Baseline changed flags are
null; later CPU0 flags false, CPU1 false/true/true. Values are decimal opaque
low bytes only; no full core-state word is retained in this public schema.

Pairs are sequential CPU0 thenCPU1. Existing PS pair precedes added core-state
pair; they are not simultaneous measurements. Guarded baseline precedes CPU1
start intent; subsequent fixed-width helper reads preserve the reviewed
post-start exception handling. Final pairs follow **natural arrival timeout**,
not an in-flight observation deadline. Terminal observation error null.

**Confirmed comparison:** both observed CPU1 fields change in the post-second-
start sample and remain so in the final sample, while the CPU0 reference is
unchanged. Desired PS0 is preserved without normalization. Legacy active15
and opaque byte2 do not establish t6050 reset release, running state or PC.
Execution/reset/running fields remain NOT_ESTABLISHED, PC NOT_OBSERVED,
t6050 register semantics UNKNOWN. The observation establishes access completed
in this session, not general safety or the register's meaning.

## Recorder, timeout and interpretation

**66 mutation intents**, starts attempted/acknowledged **2/2**. Recorder
**93/93 complete samples,465/465 reads**, highest phase0,identity not committed,
complete=false,error null,closed=false. Reset/spin observation
**no_reset_record_seen**,93 samples. No independent arrival;8 timer requests
planned,0 completed,round-trip list empty,counter progress=false,park=false.
No CPU1 callback or Linux boot ran. No timing/CPU performance conclusion follows
from these USB/Python/host/journaling durations.

CPU0 code publication PASS and CPU1 telemetry's no_recorder_publication_seen
are separate facts. Missing CPU1 identity/EL/MMU/cache fields stay null/unknown,
not inferred disabled. The vector can also serve an exception slot; neither
missing marker nor a future marker alone establishes reset provenance or PC.

Topology remains18 cores:12 Performance (ADT M),6 Super (ADT P),three clusters
of six. CPU1 target remains Performance/core1/cluster0 with the boot CPU.
Later-cluster legacy mismatch IDs6–17 are structural metadata, not extra-core
starts. Linux capacity remains uncalibrated; all-core operation NOT RUN.

Under the published outcome table, M5 next reviews **effective dispatch/first-
store visibility using the combined evidence**. No new power/reset/stop write,
vector relocation, longer timeout, width/address scan or automatic retry follows
from an opaque state transition. Prior31I connection failure and31H gate refusal
remain separate observations;31J's successful connection/readback does not prove
their original causes or a CPU-start fix.

## Return and boundaries

Immediately on supervisor outcome, human was told to power off and choose
Macintosh HD before detailed inspection. Usual desktop confirmed; return was
recorded **2026-10-22 03:15:08.610 UTC / 2026-10-21 11:15:08 PM Eastern**,
**+45.136s** from wrapper start. This is a confirmation interval, not exact
power-off or macOS boot time. No return problem reported. Owned bounded caffeine
process already exited; no process signaled during return bookkeeping.

No target command after supervisor completion, no retry/reconnect, cable
troubleshooting, target rollback/cleanup or Linux continuation. Installed
boot021, retained boot042, pinned client, macOS/volumes/settings unchanged.
Routine policy checks remain waived: original Full/lab Permissive/Macintosh HD
default stay last reported, not freshly verified. No new boot/default/security/
firmware change. Preserve all receipts and frozen sources. Frozen pre-execution
NOT RUN text is historical; this result supersedes it for the consumed31J only.
