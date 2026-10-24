# 31Y: a reproducible offline boot-image discriminator

2026-10-24. **A useful software lead advanced:** Apple's local read-only inspector
derives collection properties from original synthetic files, including a nonzero
additional-object selector when the tested public boot/SPTM segments are present.
This removes an unmeasured format assumption from the alternate-host investigation.
It does not establish acceptance by the installer or firmware, or CPU startup.

No message was posted to anyone. No installed image, volume, policy or firmware
was changed. No fixture was executed or installed. The work uses ordinary format
parsing; no authorization check or protection was disabled.

## Measured parser behavior

The experiment ran `/usr/bin/kmutil inspect` on macOS 26.6.2, build 25G83,
against explicit workspace fixture paths. System and auxiliary collection paths
were explicit nonexistent workspace paths with `--allow-missing-collections`.
No real boot collection or personalized object was an input. The tool hash is
`2f435e8f872e75e7edcf0ec108f3360e18b1e4123451032062b7c28aa4106b43`.

The original fixture generator uses public Mach-O structures. The images have
synthetic branch-to-self markers, empty prelink dictionaries and deterministic
fixture IDs. These are parser inputs, not alternate kernels. The largest is
96 KiB. All Apple program bytes and private analysis remain outside Git.

| Stage | Cases | Observed result |
| --- | ---: | --- |
| Plain image | 3 | Exit 71: missing `__info` section. |
| Empty `__PRELINK_INFO.__info` | 3 | Exit 71: missing `_PrelinkKCID`. |
| Add synthetic collection ID | 3 | Exit 0, but property derivation fails: missing `__TEXT_EXEC`. |
| Add separate executable segment | 3 | Exit 0, but property derivation fails: missing `__LINKEDIT`. |
| Link-edit before prelink-info | 3 | Exit 0, but property derivation fails with a checked offset-subtraction error. |
| Put link-edit last | 3 | All 14 boot properties derived; `kcbz=0`. |
| Public boot/SPTM segment layout | 2 | All 14 properties derived; `kcbf=32768`, `kcbz=32768`. |

The first six stages each compare a flat `MH_EXECUTE`, a flat `MH_FILESET`, and
a fileset with one embedded original image. The final stage compares the two
flat forms with `__DATA_SPTM` and `__TEXT_BOOT_EXEC`; neither has a fileset entry.
These are small controlled fixtures, not an exhaustive validator specification.

**Confirmed:** `LC_FILESET_ENTRY` is not necessary for this inspector's successful
property derivation in these cases. It may still matter to other consumers.
Renaming a file to Mach-O or selecting `MH_FILESET` alone is insufficient for the
tested inspector. The earlier third-party registration failures did not supply
their exact error text, so these results do not retrospectively diagnose them.

**Confirmed:** the successful boot-segment fixtures cause the inspector to derive
nonzero `kcbz` itself. No `kcbz` input, custom property dictionary, installed
metadata edit, signature or ticket is supplied. This is a legitimate parser path.
The resulting `kcsz=32768` and `kcbz=32768` exceed either named segment's individual
16 KiB fixture size; they must not be treated as simple declarations of the real
monitor's required allocation. No T6050 firmware allocation is inferred.

The first sandboxed run failed to create a Disk Arbitration session before parsing.
That environment failure is retained separately. The subsequent bounded read-only
runs reached the parser without administrator elevation. The final reusable
generator reproduces all 20 separately tested prototype byte sequences.

## What REA adds

The [one-function REA result](native31y-firmware.md) identifies a wrapper that
analyzes a file and then selects raw or collection serialization using a
caller-supplied bit. The collection serializer can expose the derived selector;
the wrapper does not choose its mode solely from Mach-O file type or an analyzer
return value. This agrees with the measured 14-property collection output.

The indirect binding of both CLI subcommands to that wrapper has not been proved.
Therefore **inspector success cannot be promoted to `configure-boot` acceptance**.
The tested output is valuable even with that limit: it gives repeatable local
format measurements before any future installation experiment.

## Original implementation and next engineering step

[The original generator and strict classifier](../kernel/experiments/bootimage31y/README.md)
preserve known-negative cases, validate positive output and compare the full
normalized matrix against a versioned reference. This prevents the observed
exit-0 failures from becoming false readiness claims. Fourteen focused tests cover
image bounds, entry mapping, metadata, ordering and output refusal behavior.

[The CPU2 binding plan](../kernel/experiments/smp31y-target/README.md) is a separate
original nine-test deliverable. It derives a same-cluster physical control from
retained ADT/layout evidence and catches the old observer span that would reject
a successful CPU2 record. It contains no live controller. CPU2 success would
change the raw-path diagnosis; a second negative would remain ambiguous.

The preferred alternate-host next step is to qualify the **version-matched
SPTM-to-OS interface**: entry reason and two argument pointers, monitor-owned
memory boundaries, fixups completion and exception setup. Apple's public consumer
code supplies architectural evidence, while its complete platform headers and
helper-library contract are not available in the located source. Ordinary Aura
entry expects a raw boot-argument pointer in x0; a wrapper-only change would
misinterpret the documented SPTM handoff. See the
[public source comparison](native31y-host-source.md).

Original adapter work can continue without the unpublished x1n1 implementation,
but a qualified entry contract must precede executable native code. The parser
fixtures are not that adapter and must never be sent as a boot package. **No
restart is ready.** A software workaround remains plausible; neither a working
solution nor an Apple-only dependency has been demonstrated.
