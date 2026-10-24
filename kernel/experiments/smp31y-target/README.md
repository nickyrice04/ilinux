# 31Y offline CPU2 comparison plan

This original tool derives the target bindings for **CPU2 only**, in CPU0's
already active M/Performance cluster. It reads pinned sanitized ADT, 31G
topology observations and the published boot021 layout. It produces JSON;
there is no transport, native controller, executable payload or boot operation.
An optional check hashes the retained boot021 image and seven source files as
data. It does not execute downloaded code or repeat the old native campaign.

Run the public-input plan and its focused tests from the repository root:

```sh
python3 -I kernel/experiments/smp31y-target/plan.py
python3 -I kernel/experiments/smp31y-target/test_plan.py
```

`--image`, `--source` and `--proxy-source`, supplied together, additionally
recheck retained bytes. `--source` names the directory containing the seven
source filenames; the exact matching `proxy.c` may come from another retained
directory. Only six files are read from `--source`, with `proxy.c` read from
`--proxy-source`. Symbol-table bytes are not rechecked by this option; the two
pinned public layout records bind the earlier symbol-table audit. Missing or
changed evidence refuses; no guessed fallback is generated.

## What this comparison could decide

All ten consumed starts in 31C–N targeted CPU1. CPU2 changes the physical core
while retaining the same cluster, core type, raw boot image and known start
register pair. It is a meaningful control for a CPU1-specific condition. It is
not a predicted workaround and does not test a new cluster's preparation.

| Result of a separately qualified single comparison | Consequence |
| --- | --- |
| Committed CPU2 prefix identity | Refutes the claim that this raw setup cannot enter any secondary. Investigate per-core state/selection and then separately qualify further execution. A prefix alone is not Linux SMP. |
| Partial record, unexpected identity or observer error | Preserve it and stop. This distinguishes an entry/observation change from a clean zero; it is not silently converted to timeout or accepted as CPU2. |
| Start pair completed, power/state changed, all entry records zero | Extends the negative result to two M0 targets. Common entry/context/visibility failures remain indistinguishable; it does not prove SPTM necessary or all software routes impossible. |
| Preflight refusal or ambiguous start completion | No comparable negative. Do not retry or advance to another core. |

CPU6 and CPU12 add cluster-power, ordinal and possibly core-type variables;
they are less controlled substitutes. A second CPU1 attempt with unchanged
conditions supplies less discrimination than this CPU2 comparison.

## Bindings that must change

Offsets below are relative to the exact boot021 image; hardware addresses are
identified separately. The tool derives array strides from the published
symbol boundaries and computes row2, rather than treating CPU1's row as reusable.
The 64 KiB stack stride comes from the hash-pinned layout audit. Expected MPIDR
uses the audited M0 class expectation and CPU2's ADT affinity; ADT `reg` alone
does not contain Aff2. Actual identity remains to be observed.

| Binding | CPU2 plan |
| --- | --- |
| Topology | CPU2, M0/local core2; expected low24 MPIDR `0x40002` |
| Runtime CPU-info record | `0x117208`; validate valid/die/cluster/core/impl against fresh ADT |
| Spin record / flag | `0x90290` / `0x90298` |
| Reset record / stack field | `0x90030` / `0x90038` |
| Dedicated Normal stack | `0x178000` through `0x188000` exclusive; top `0x188000` |
| Shared target / reset-stack pointer | `0x90a10` becomes2; `0x90a20` names image base plus CPU2 stack top |
| Hardware reset mirror | CPU2 `0x210250000`; CPU0 comparator `0x210050000`; read64 only |
| Hardware opaque-state observation | CPU2 `0x210250100`; CPU0 comparator `0x210050100`; read32 only, semantics unknown |
| Hardware power-domain observation | ADT `MCPU0_2`, domain3, `0x280600010`; read32 only, not execution acknowledgement |
| Known start pair | Existing addresses `0x280688004`, `0x280688008`, now both value4/32-bit |

The old post-start spin scan includes row2 in its zero-only span. Reusing that
scan would reject successful CPU2 entry. The new plan excludes row2 while
covering **row1 and rows3–31**, plus the separate CPU0 invariant. Reset-table
freshness likewise treats row2 as the target and all other secondary rows as
fresh sentinels. The initial full-array census must still reject any already
alive secondary before preparation.

The vector/cold Normal prefixes read actual MPIDR and do not embed CPU1's ID.
Their code offsets remain `0xc00`/`0xd00`; hooks remain0/`0x800`; the record
identity fields remain helper+`0x1008`/`0x1088`. Device records remain image+
`0x90a40`/`0x90a80`, with identity at+16. **The existing classifiers, reset
observer, power/state adapters, allowlists and controllers are CPU1-specific.**
They must not be inherited unchanged or modified through global monkeypatching.
Normal identity is at+8, Device identity at+16; mixing them would break evidence.
The first Normal store precedes the identity read. Later Device recording still
depends on Normal progress; these are not independent first-fetch proofs.

## Required before a controller could be reviewed

The plan does not satisfy these live requirements:

1. Bind the exact image, firmware/board, usable RAM, all18 ADT/runtime CPU
   records and boot CPU0, then fresh spin/reset/shared-state invariants. Reject
   live topology or source drift. CPU2 stack/helper ranges must fit owned RAM,
   be disjoint and remain allocated throughout the observation.
2. Replace the old CPU0/CPU1-only reset-format observation with CPU0/CPU2.
   Preserve full-word equality and the reviewed address/lock/low-field gates;
   unknown upper fields retain their prior interpretation limits. Read guards
   must succeed before proceeding. A matching mirror is not a sampled PC.
   CPU2's fresh mirror/opaque/power accessibility has not been observed.
3. Qualify CPU0 mappings, aliases and probes for the CPU2 stack/records;
   preserve CPU0 positive controls and 31M cache-geometry/owned-span controls.
   Publish body before hook, clean CPU2-fetched text to PoC, invalidate the
   instruction alias and verify whole text and readbacks. These qualify CPU0's
   actions, not CPU2's incoming translation or coherency.
4. Rebuild and independently check the original fixed pair for value4 and the
   exact two addresses. Do not reuse the frozen value2 leaf. Preserve barriers,
   no intervening host transactions, and completion-unknown handling. Its
   return establishes CPU0 store completion only.
5. Bind all tracker expectations, result labels, receipt ownership, source
   closure and test fixtures to CPU2. Read the spin flag before the identities
   it validates; after start use only reviewed guard-free observations. Retain
   unexpected/partial records and exception evidence. A zero marker cannot
   establish that no instruction was fetched.

The candidate envelope remains one pair, no additional core, no secondary
callbacks, no retries, three seconds for arrival, 60 seconds for the controller
and an independent 65-second supervisor. Any loss of transport, missing token,
exception, partial record or deadline ends the experiment without a retry or
Linux handoff. Once a start intent exists, never restore hooks/shared state,
free helper/stack storage, change reset destinations or issue a stop operation:
the secondary may execute late. A prospective controller needs durable
connection/start reservation and an explicit human-return procedure, following
the already reviewed campaign pattern. None is implemented or authorized here.

No new reset destination, cluster-power write, post-start SEV/IPI, firmware
replay, installed image or security-policy change is included. A decision to
prepare and perform the comparison is separate from this offline binding pass.

Evidence: [31X audit](../../../research/native31x-cpu-audit.md),
[layout](../smp31/boot021-ram-layout.json),
[symbol record](../smp31/boot021-symbols.json),
[31G ordinals](../../../native/boot/attempt31g/topology-observation.json),
[31N fixed-pair contract](../smp31n-startpair/README.md).
