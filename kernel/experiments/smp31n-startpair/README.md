# 31N fixed CPU1 start pair

This original CPU0 leaf tests whether host-side observation between the existing
two startup stores changes their behavior. It is a controlled timing change,
not a confirmed t6050 startup fix, firmware emulator or Linux SMP release.

The original 31M controller's synthetic negative-path replay contains **127
external interface/proxy calls and 33 journal callbacks between the two store
calls**. These are code-path counts, not measured native latency. The public
native result does not contain a trustworthy inter-store duration. The existing
native acknowledgments and power transition do not rule out a timing requirement.
Pinned m1n1 and the already reviewed macOS PMGR routine issue their start requests
on-target without those serial/host-journal transactions between them.

`start_pair.S` contains exactly the previously used 32-bit stores of 2 at
misc-cores offsets +4 and +8, in that order. A DSB SY precedes, separates and
follows the stores. It takes no arguments and returns `0x314e` only after the
trailing barrier. There are no memory reads, stack operations, system-register
writes, new MMIO addresses, cache operations or shared exception-guard changes.
The 44-byte leaf occupies helper offset `0x240`, disjoint from all existing code
and observation records. The interrupt state is unchanged: **the pair is not
atomic**, and no maximum hardware inter-store latency is established.

## Controller requirements

The controller must retain all existing image, source, hardware, topology,
translation, freshness, ownership and observation gates. It must verify zero
padding, publish/read back the exact leaf through the existing owned allocation,
clean to PoC and invalidate its RX instruction alias before use. All CPU1 record
and start-state checks move before the pair; state observations follow it.

This intentionally removes the old opportunity to stop after an unexpected
early record or state change between the two stores. The second store follows
the first as it does in the existing on-target m1n1 sequence; the experiment
does not claim an observation-dependent abort between them. The first new
observation after normal completion must retain the existing positive/error
stop rules. This tradeoff is part of testing the pair's timing contract.

Before dispatch, durably record one intent for a pair of two possible stores.
Invoke it exactly once with no arguments. A missing reply or fault leaves
**zero, one or both stores possibly complete**; no additional query, cleanup or
retry is authorized. Do not describe an invocation intent as proof that both
instructions executed. Only a matching return token followed by the existing
successful exception/guard check confirms the normal completion path and both
acknowledgments. Neither confirms CPU1 execution. There is no intermediate
`after_first_start` sample in this experiment.

A positive committed CPU1 record supports the timing-sensitive startup
hypothesis while leaving causal details unresolved. An all-zero result closes
this particular host-gap variant without proving that CPU1 never fetched an
instruction. Early/partial/error observations retain the existing stop behavior;
no callback or Linux continuation follows.

## Offline verification

`test_plan.py` independently decodes the original leaf into its two-store trace,
checks every interruption prefix and word mutation, and validates completion
and bounded allocation contracts. `test_prior_gap.py` replays only project-owned
synthetic models; it imports no downloaded client and makes no target calls.

`audit.py --object <assembled-object>` compares the separately assembled ARM64
ELF text with the fixed leaf and refuses unresolved text relocations. Apple LLVM
21.0.0 produced an exact 44-byte match during development. GNU assembly in the
isolated VM is a separate release check. Leaf SHA-256:
`8c591d55d1d92a6b466a33a9cc5af69f869504df066728862119c5f39037bf19`.

Eleven original test methods pass on the development host. Native operation is
**NOT RUN**; this directory alone neither authorizes nor initiates a boot.
