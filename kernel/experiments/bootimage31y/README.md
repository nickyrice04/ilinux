# Read-only boot-image format experiment

This original Python tool generates **non-bootable synthetic Mach-O fixtures**
and optionally submits them to Apple's read-only `kmutil inspect` command.
It never invokes `configure-boot`, creates a kernel collection from system files,
executes a fixture, contacts a device, or changes an installed image or policy.
All output must go to a new directory under this repository's ignored `build/`.
Generated files have no execute permission. Do not install them manually.

The fixture bytes contain original branch-to-self markers, empty metadata and
test-sized segments. They contain no Apple code, real kernel, personalized
object or machine identifier. Their deterministic collection IDs identify only
the fixture contents. The one-page SPTM region is **not a T6050 memory layout**.

## Run

Portable checks and fixture generation, without any Apple tool invocation:

```sh
python3 -I kernel/experiments/bootimage31y/test_probe.py
python3 -I kernel/experiments/bootimage31y/probe.py \
  --output build/bootimage31y-generated
```

On macOS, explicitly request read-only inspection:

```sh
python3 -I kernel/experiments/bootimage31y/probe.py \
  --output build/bootimage31y-inspected --inspect
```

Use a new output directory each time. No `sudo` is needed. A sandbox that denies
Disk Arbitration can prevent the tool from reaching the parser; the process
signal stops the matrix and must not be recorded as an image-format rejection.
Do not disable security settings to run the inspection. Linux supports the
generator and tests; it cannot run Apple's local inspector.

`expected-results.json` records the 20-case measurement on macOS 26.6.2/25G83,
including fixture hashes, process exits, normalized parser diagnostics and all
derived properties. The inspector's binary hash is recorded for applicability;
an M1 or future macOS version must report its actual hash/version independently.
The runner compares the entire result signature and returns nonzero on a
different result, an unknown output shape, a timeout or a process signal.
A changed result is evidence to investigate, not grounds to weaken the test.

The reference expects six collection-loading errors, nine property-derivation
errors and five successful derivations. **Nine negative cases return exit 0
from `kmutil`.** The classifier therefore requires an explicit, complete,
nonduplicated property block and refuses unknown output. A zero process exit
alone is not a successful probe. A matching matrix is still not boot acceptance.

## What it establishes

The tested inspector needs collection metadata, standard segment names and
compatible ordering to derive these properties. Both tested `MH_EXECUTE` and
`MH_FILESET` fixtures can reach derivation without an `LC_FILESET_ENTRY`. The
fixtures with the public `__DATA_SPTM` and `__TEXT_BOOT_EXEC` segments produce
nonzero `kcbz` automatically; the ordinary ordered fixtures produce zero.
No private metadata is patched or supplied to force a selector.

This is a repeatable offline format discriminator. It does **not** establish
that `configure-boot` accepts the file, iBoot starts it, SPTM accepts its context,
CPU1 enters, or Linux SMP works. The properties can describe ranges spanning
more than one segment: do not reinterpret a property size as a segment's declared
size or a required hardware allocation.

The remaining entry, fixups and memory-ownership contract is discussed in
[the format findings](../../../research/native31y-format-probe.md) and
[the public entry comparison](../../../research/native31y-host-source.md).
