# Native startup guard experiment

This local m1n1 patch stops a secondary startup attempt when the existing
locked-register check finds that RVBAR does not match `_vectors_start`.
It caches the existing RVBAR read, prints the CPU identity and both entry
addresses, and returns before changing the shared spin table, reset stacks,
or CPU_START registers. It does not write RVBAR on locked-register systems.

This is an **optional diagnostic safeguard**, not an SMP enablement fix.
Test the pinned unmodified baseline first at the separately authorized
native gate. A different RVBAR could conceivably lead through a firmware
trampoline; no such path has been established here. The conservative
experiment intentionally declines that attempt and may leave fewer cores
available. It must not be presented as a proven native boot requirement.

The change follows public m1n1 control flow and existing hypothesis H1.
No proprietary pseudocode or instruction sequence is used. The CPU_START
encoding, polling interval and timeout on admitted attempts are unchanged.
Current REA evidence strengthens the separate cluster-mask hypothesis H2
but does not justify installing its candidate register encoding.

## Reproduce

From the repository root, prepare into a new ignored directory:

```sh
python3 -I kernel/experiments/native-startup/prepare.py \
  third_party/m1n1 build/rea-lab/native-startup
```

The script verifies public source commit
`57a9339ffd1876e78297b17d34dece8cff8fa1ba`, source digests and a clean source
tree. It applies the patch only to a disposable copy and extracts the actual
`smp_start_cpu()` function for the harness. It does not execute that source.

In the isolated ARM64 Linux lab, after acquiring the shared build window:

```sh
sh /mnt/lab/native-startup/run-linux.sh
```

The regression must fail on the baseline with the expected write counts,
not just an arbitrary error. The patched mismatch path must do zero writes,
zero waits and no shared-state changes. Seven additional cases cover admitted
startup, unlocked RVBAR, existing cores, range exclusions, EL3 and timeout.
Clang ASan/UBSan runs when installed; its availability is explicitly recorded.
The complete patched `smp.c` is also compiled to a freestanding ARM64 object
with m1n1's relevant C flags and actual headers. No boot image is linked or
installed by this experiment.

No speed or energy benchmark is appropriate for a rejected startup path.
Operation counts and timeout behavior are correctness assertions. Full
m1n1 linking, physical startup, recovery and power measurements remain
separate validation steps. See the associated CPU-startup REA handoff for
the recorded test results.
