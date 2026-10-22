# 31O: offline startup evidence and firmware structure

31N completed the two CPU1 start stores locally, with clean diagnostics, but no
committed CPU1 entry record. It closes the tested host-communication-gap variant.
It does not prove no instruction was fetched. **31O is an offline research
checkpoint: no new native runner, reset operation or reboot is released.**

## What is implemented

`evidence.py` independently classifies the sanitized 31M and 31N reports. It
checks completion facts, counter consistency, controls, observation phases and
unsupported conclusions. Its successful negative classification means a complete
observation ended without visible entry; CPU1 execution remains unverified.
Positive metadata requires review of the actual committed identity record and
cannot silently become hardware proof. Missing/faulted evidence stays incomplete.
The bounded JSON reader rejects duplicate keys, non-finite values and malformed
types. Output uses fixed classifications, counts and hashes rather than arbitrary
input text, raw register words or local paths.

`rcfg.py` parses the matching decoded generic firmware's RCfg directory and
command framing. It validates section bounds, names, sequence references and
record lengths, producing structural counts and indexes. It exposes no hardware
interface and does not execute, flatten or replay the command programs. Unknown
opcodes remain opaque. A descriptor-dependent condition is not inferred from
the apparent position of two records. The parser was implemented from behavioral
format findings using synthetic fixtures; proprietary input and decompiler
output remain outside Git.

`tools/m1n1-client/attempt31o-offline.py` verifies the frozen 31N sources and this
checkpoint's own pins, runs the new regression suites, checks both consumed
reports, and reruns the exact boot021 entry/Normal-prefix contracts. It does not
feed the new report into a historical checker that accepts only a 31K schema.
An optional matching private iBootData input is hash checked before parsing.
M1 can complete its review without that private input or the symbol file.

These tools accelerate static investigation and evidence review. They are not
an Apple firmware emulator, a native SMP fix, a benchmark or proof of macOS parity.
The final validation companion records actual host/VM counts, input digests and
limits. Synthetic tests cover invalid data and contradictory claims; the real
generic payload is checked privately, with only structural summaries published.

## Decision and next useful evidence

The independent [upstream review](../../../research/native31o-upstream.md)
found an explicit M5 Pro/Max platform problem reported by Gravity Linux and
similar failures in other T6050 experiments. These are attributed reports, not
an Apple confirmation or proof of this Mac's exact cause. No demonstrated
firmware upgrade or alternate packaging fix was found.

Next investigation must connect a specific firmware preparation condition to
the custom raw-loader path, show an actual reset-state change, or identify a
supported observation of execution. The current reset mirror is sampled only
before CPU1's power transition. A later same-address comparison may be useful
inside a stronger test, but an unchanged mirror remains inconclusive and does
not justify a reboot on its own. The serial Normal-prefix then Device-recorder
path also has a shared first-store dependency; their negatives are not wholly
independent.

All 12 Performance and 6 Super cores remain the target. After actual secondary
entry come bounded rendezvous, coherency/timers/IPIs, other clusters and Linux
idle/scheduling/frequency/energy measurements. Networking, storage and GPU work
remain required for a usable desktop; an online CPU count alone is insufficient.
