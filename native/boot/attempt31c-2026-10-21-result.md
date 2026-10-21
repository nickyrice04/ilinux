# Attempt 31C — RAM checks pass; CPU1 arrival times out

**Observed, 2026-10-21:** the single authorized supervised 31C run returned
**STOP / `cpu1_arrival` / `cpu1_arrival_timeout`**, controller exit **1**.
All **11 RAM-check booleans are true**, BootArgs revision **3**. The controller
recorded **9 mutation requests**, **2 CPU1 start writes attempted and
acknowledged**, arrival **unverified**, **0 requests completed**, counter
progress **unverified**. Controller elapsed **4.466 s**, supervisor **4.865 s**,
supervisor deadline **false**. Human confirmed usual Macintosh HD return at
**+51.953 s** from command start, within the independent 90 s bound.

**31C is consumed.** The write-capable CPU1 experiment ran and stopped; this
was not another preflight-only refusal. No retry, reconnect, live gate edit,
extra-core command, target rollback or Linux continuation occurred.
**Linux boot/native Linux SMP, timer-request completions, renderer performance
and energy tests remain NOT RUN.** CPU1 entry is **not verified**; a timeout
does not prove that CPU1 executed no instruction or identify where it stopped.

Exact schema-reviewed final outputs:
[controller](attempt31c-controller-2026-10-21.json),
[supervisor](attempt31c-supervisor-2026-10-21.json).
Raw receipts, stderr and target details remain private under ignored build.

## Provenance and offline gate

M5 handoff **`61bbe522e1da70423396eabefbbae68794fb5706`**;
published M1 readiness/execution **`c48464d557d1183aed6bb5127319ddf3c36b8e80`**.
The [independent intake](attempt31c-m1-offline-2026-10-21.md) passed all
**46 source pins**, boot042's **13 package files**, the existing boot021
image/helper and clean client pin. **60 Python methods PASS**, zero skips,
failures or fixes; all nine requested subprocesses exited 0. The real
BootArgs/ADT/high-address client tests reported by M5 remain separate VM
evidence, not native CPU-entry proof.

Source-manifest SHA-256:
`b4021e4669e42732e4f1130f5a997451ecfdcbf94326a6bdd4bd63620cafe208`.
Controller:
`8b69e15e248b596ad1f51b7b013c2a0e72d8096d65afe8815166998e45fca567`.
Supervisor:
`0ca31f902c2ceb2d5bc94bd075a6d74a575fcee2060ddf0d10ec358574240f49`.
Existing 3,932,160-byte boot021 image:
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
Client remains `57a9339ffd1876e78297b17d34dece8cff8fa1ba`; shared 31B
controller/helper and source pins remained unchanged during execution.

Both 31A and 31B remain consumed. Prior 31B evidence digests were checked
before/after 31C intake and after the live run and stayed unchanged. No real
31C live-use files existed before/after offline tests; the actual run created
its separate one-use evidence. No receipt was removed or reset.

## Execution and boundaries

After readiness publication, the human explicitly confirmed starting **31C**,
a fresh M1 restart, direct cable reseat, both Macs powered, M1 unlocked/lid
open, M5 Running proxy and 90 s timer readiness. These preparation facts are
human-reported. The timer cue immediately preceded the one documented
supervisor command with `--confirm START-CPU1-J716C-31C`.
Local command start: **20:41:51.672 UTC / 4:41:51 PM Eastern**.

| Controller evidence | Result |
|---|---|
| Result / phase / reason | STOP / cpu1_arrival / cpu1_arrival_timeout |
| RAM predicates / BootArgs revision | 11 true / 3 |
| Explicit mutation intents | 9 |
| CPU1 start writes attempted / acknowledged | 2 / 2 |
| CPU1 arrival verified | false |
| Timer requests completed / counter progress verified | 0 / false |
| Linux boot / native Linux SMP | NOT RUN / NOT RUN |
| Controller elapsed | 4.466 s |
| Supervisor exit / deadline / elapsed | 1 / false / 4.865 s |

The RAM predicates cover supported/consistent revision, integer/nonempty
64-bit interval, physical width, machine-aperture containment, ADT containment
and complete read, matching chosen DRAM base/size and image containment.
The new bound therefore passed on this native run; no raw numeric bounds or
target ADT are published. It did not widen the usable interval.

**Inferred from the exact controller flow and phase/receipt progression:**
the full inherited preflight passed, followed by 16 KiB allocation, the
192-byte helper upload/readback and cache maintenance, helper readiness,
WFE selection and CPU1 RAM setup/readback. Seven explicit mutation intents
preceded the two start-write intents. The final phase was the bounded
three-second arrival check. Post-start observations use the reviewed helper
and avoid ordinary bulk reads/global diagnostic-guard changes. No timer
request phase was reached; arrival identity/stack and final parked state are
not established by the saved result. Durations include proxy/software overhead and are
not CPU-start latency benchmarks.

The private consumed receipt has **17 records**. Publication contains only
the reviewed final JSON schemas, not the whole receipt. Acknowledged register
writes are dispatch evidence, not proof that CPU1 entered the parked loop.
The timeout alone cannot distinguish a startup/entry issue, unexpected reset
state, late arrival or an observation-path issue. No cause is established.

## Return and next M5 review

Immediately on the supervisor result, the human was instructed to power off
and select Macintosh HD; result inspection followed that instruction. No
further target command or cleanup was attempted. The controller closed its
transport. Return confirmation recorded **20:42:43.625 UTC / 4:42:43 PM Eastern**,
**+51.953 s** after command start. This includes UI/confirmation overhead and
is not a macOS boot-time measurement. Only the owned bounded caffeine
assertion was stopped after confirmation.

Installed boot021, client pin, macOS, boot/security/default/volume settings
and firmware are unchanged. Routine policy/default rechecks remained waived;
original Full/lab Permissive/Macintosh HD default are last reported, not newly
verified. No new image transfer, frequency operation, Linux or renderer test.

**M5 next: review CPU1 arrival/entry and the existing observation path offline
using this exact partial result.** Preserve the 31C once/consumed receipts;
no automatic retry, guard relaxation or time-limit extension. CPU1 entry is
still unverified, so two-core Linux, timer IRQ/IPI/coherence and renderer
integration remain held pending separately reviewed evidence. The source-pinned
checklist/readiness text stays frozen for provenance; this result and current
coordination supersede its pre-execution NOT RUN wording for the 31C controller.
