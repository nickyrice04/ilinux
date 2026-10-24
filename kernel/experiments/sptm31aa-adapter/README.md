# 31AA ordered CPU registration preparation

This original portable C module prepares the CPU argument list and logical
mapping that a future qualified native bridge can consume. It composes with
the frozen [31Z entry and memory helpers](../sptm31z-adapter/README.md) without
modifying them. **NOT_DEPLOYABLE:** it makes no monitor calls, starts no CPUs and
does not establish helper initialization, a resident monitor or entry permissions.

`sptm31aa_prepare_registration` takes a31Z entry snapshot, caller-provided ordered
CPU records and a separately supplied boot identity. It requires31Z's cold-only
argument role, a nonempty list within the64-record software bound, a boot identity
matching the first record, unique source CPU IDs, unique affinities and full raw
affinities that fit32 bits. On failure output remains unchanged. On success it
returns owned records in exactly the supplied order. The64-record capacity is
an original storage limit, not a hardware or monitor limit.

Each output contains the predicted registration ordinal, the caller's source
CPU ID, the caller's opaque core-class tag and the exact single64-bit registration
argument formed by zero-extending the checked ADT affinity. Source IDs may be
sparse or unordered; ordinal0 is the supplied boot CPU regardless of its source
label. Classes are retained without sorting or scheduling policy. There is no
callback wrapper, progress counter, completion Boolean, retry loop or result ID.
The output records are directly available to a future bridge; the current module
does not execute that bridge.

The behavioral basis is the [31Z local registration finding](../../../research/native31z-handoff.md)
and [versioned SDK/public contract](../../../research/native31z-public-contract.md).
The local consumer reloads the low32-bit ADT `reg` affinity for the single64-bit
argument. The SDK requires registration on the boot CPU, before machine lockdown,
for the supported CPUs, with the boot CPU registered first; registration order
assigns logical IDs. The API is void. The module's ordinals are therefore
predictions from the planned order, **not observed monitor-assigned results or
successful registrations**. Public XNU follows ADT order; the module does not
silently repair ordering by moving the boot CPU. Rejecting high input bits and
duplicates is original validation policy, not a claim about monitor error behavior.

Width validation cannot authenticate CPU identity. In this project's retained
topology, CPU2's ADT affinity is2; the diagnostic MPIDR value `0x40002` also fits32
bits but is not the registration argument observed for CPU2. The component does
not mask that diagnostic value, add Aff2 bits, or fall back to MPIDR. One test
deliberately supplies the wrong in-range value and shows that arithmetic alone
cannot identify the mistake. The caller must bind the actual input to ADT `reg`,
the complete supported CPU set, its source order and the boot identity. Likewise,
structural cold-entry validation is not authentication of a real monitor handoff.

The retained project fixture is independently bound to two frozen public files:

| Input | SHA256 |
| --- | --- |
|`hardware/adt/adt-sanitized.json`|`6f143434d2f05310067559f8fa3836ae564dd9934ebc5912660f2a9f5a8a73af`|
|`native/boot/attempt31g/topology-observation.json`|`b055f570f79c6b423fb917afcd73a2c9a87aded2cf6057f9dc708048eae2db42`|

The test runner walks sanitized CPU nodes in source order, extracts `cpu-id`,
the actual `reg` address, `cluster-type` and `state`, and compares IDs/affinities
against the independent topology observation. It requires one running CPU at
the first position. It never derives affinity from cluster indices or MPIDR.
The generated test header contains only those numeric labels; the18-CPU fixture
preserves the source `M`/`P` tags as character-code metadata. These retained
observations are test data, not fresh hardware state or an enabled native profile.

Run from the repository root with a fresh output directory:

```sh
python3 kernel/experiments/sptm31aa-adapter/run.py \
  --output build/31aa-adapter-host --sanitize --freestanding
```

The dependency-free runner verifies all frozen dependency/input hashes before
compilation and records all12 source bindings, generated fixture, compiler
identities, commands, output and results. It refuses an existing result directory
and fails if source bytes change during a run. It compiles only original project
code, with C11, `-O2 -Wall -Wextra -Werror -pedantic`; optional ASan/UBSan repetitions
use `-O1` and disabled recovery. No SDK headers or proprietary payload are needed.

There are11 unique C groups, including120 order permutations,56 duplicate pairs,
all64 possible positions for an oversized affinity, count/role/boot-identity
failures, full-width zero extension, source-ID/class retention, the18-CPU fixture
and composition with31Z snapshot/memory planning. Sanitizer repetitions do not
increase the unique group count. The frozen31Z suites are not rerun by this tool;
their helpers are linked into the new integration test and their bytes are pinned.

The freestanding option compiles one AArch64 ELF relocatable object and inventories
undefined symbols using the frozen original31Z ELF reader. The resulting object
depends on31Z's cold-role accessor and may also require C memory routines. It is
not linked or executed as native code. A future native consumer still needs the
qualified dispatch transport and any helper services actually used, plus the
matching image/exception lifecycle, actual boot-CPU and pre-lockdown context,
memory ownership and stack. This does not require opaque helper initialization
for a dispatch path that does not use those services. Reconstructing or replaying a plan
does not authorize duplicate registrations, and a void call cannot provide a
software success result that proves physical CPU startup.
