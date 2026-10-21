# 31G controller review — power state plus entry evidence

31F consumed at `f2d9035`. Native31G/CPU1/Linux SMP **NOT RUN**.
Installed boot021, client57a9339, macOS, security and volumes stay unchanged.

## Decision and evidence

CPU0 verified 31F's RAM publication but CPU1 produced no observed marker. The
missing marker cannot prove zero instructions or a physical power transition.
Fresh REA, original-byte/LLVM checks and strictly filtered IORegistry topology
establish that CPU1's existing two addresses and mask2 are correct. Do not
change them. See `research/native31g-reset-routing.md`.

The new original topology planner validates 18 distinct die-wide masks from
`acc-cores`. The previous four-core formula fails for CPUs6–17 on this
six-core-per-cluster machine. This is useful for later multi-cluster enablement,
but does not explain CPU1 or authorize more starts. ADT M is Performance;
ADT P is Super. Scheduler capacity/energy values remain uncalibrated.

## Exact delta from frozen31F

- Before allocation/start, bind live ADT format, all18 topology ordinals and
  CPU1's unchanged route. Bind only MCPU0_0/id1 and MCPU0_1/id2, flags0,
  no parents, group0/reg0, offsets0/8, translated base0x280600000.
- Keep 31F's recorder, publication, 16 translation checks and two starts.
- Upload16 original bytes at helper+384 (64-byte aligned within the existing
  allocation), clean/invalidate/read back before startup. Exactly one LDR W0
  bracketed by DSB SY; no global exception guard writes.
- Two extra AT read probes require correct physical address and Device-nGnRnE
  encoding0. Successful AT is a mapping check, not peripheral-access proof.
- Baseline uses guarded P_READ32 while CPU1 has not started; exception evidence
  checked immediately without clearing it. After startup, exact32-bit helper
  reads only; no guarded RPC or adjacent64-bit read.
- Pair reads before start, after each acknowledged start, and only on natural
  arrival timeout or verified final park. Maximum8. Each intent is durably
  journaled before dispatch; each decoded result retained independently.
- No power-state reads after any other fault. Unexpected early entry before
  the second start stops; **no final PS sample** then. This is intentionally
  a prefix of the four fixed phases, not a missing tracker transition.
- Natural arrival timeout remains the primary reason if terminal observation
  itself fails. Read failures can lose the proxy, so the existing independent
  supervisor/human deadlines and return-on-any-result rules still apply.

Success74 mutation intents; ordinary timeout66. Three added RAM/helper-cache
operations; hardware start writes remain exactly2. PS reads cause no requested
hardware writes. No retry, cleanup, PS writes, other cores or Linux continuation.

## Limits and decision table

| Observation | Supported conclusion | Next investigation |
|---|---|---|
| Baseline read fails | This reviewed read is unavailable in this session | Stop; inspect access/mapping evidence offline |
| CPU1 actual changes while recorder stays empty | Power-domain transition observed, entry still unverified | Effective reset route, retention/cache visibility, earliest store |
| CPU1 actual remains inactive | No active state observed at these bounded sample times | Startup sequencing/clock/power prerequisites, no speculative power writes |
| CPU1 already reports active throughout | Status alone cannot distinguish reset-held/waiting/executing | Effective reset/entry path |
| Recorder progresses | Some recorder publication observed | Identity/EL/reset-stack and subsequent verified requests |

No ARM VM model is claimed to emulate Apple power, SPTM, caches or reset logic.
Offline tests reject unsafe/control-flow errors; hardware supplies missing facts.
