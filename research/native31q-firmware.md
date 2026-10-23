# 31Q: raw-image metadata and the CPU startup preparation path

Date: 2026-10-23. **Offline findings; native31Q HOLD / NOT RUN.** M1's31P
review at `5058916` passed379 source pins,122 Python methods and12 C groups.
No new native result follows from that review. CPU1 execution remains unverified.

## What this pass establishes

The current generic raw-image metadata producer does not emit the additional-
object selector examined in31P. Its likely firmware path prepares fallback
memory ranges separately from the main entry-vector path. These observations
narrow the investigation; they do **not** identify a missing CPU1 release step,
prove CPU1's first instruction, or justify another marker-only startup retry.

Analysis addresses below refer to retained files, never live pointers or approved
native reads. Apple bytes, assembly and pseudocode remain in ignored local build
storage. This document records behavioral findings and original engineering
decisions only. No installer, personalized boot object or security setting was
accessed to produce a new boot configuration.

## Inputs and provenance

The retained generic J716c iBoot input is unchanged from31P:

- Decoded input SHA-256: `b4822fc8902c3693ee590c544011603423a75291edd60afd31210d068a4ca120`.
- Analysis ELF SHA-256: `f89169923c17be829c6b31c3c04c5695d06d42a42cea7390f61214202400dcee`.
- Analysis base: `0x100c1aa4000`; the wrapper's mapped bytes match the input.

The current generic `kmutil` executable was read as data, never invoked:

- Universal-file SHA-256: `2f435e8f872e75e7edcf0ec108f3360e18b1e4123451032062b7c28aa4106b43`.
- ARM64e slice SHA-256: `13827d7242e4550f3d45994f9849ce3a84dbb14d3bb6de21601c4488287582fb`.
- Host version: macOS26.6.2/build25G83. The slice matches the universal file.

The recorded installation used raw entry2048 and base0. The historical executable
hash and emitted metadata were not captured. A matching recorded OS version is
insufficient to prove identical executable bytes or historical output. Therefore
the **current producer behavior is confirmed statically**, while its application
to the installed historical image remains **inferred**, not observed. No private
policy object is needed or requested for this checkpoint.

## Raw metadata producer versus collection metadata

The raw-option path around `0x1001444e0` reaches the constructor at
`0x100023f34` through the call at `0x100144860`, then the serializer at
`0x100023420` through the call at `0x10014486c`. This serializer produces eight
property names: `kclo`, `kcep`, `kcrf`, `kcrz`, `kcsf`, `kcsz`, `kclf`, `kclz`.
It does not emit `kcbz`. The adjacent collection serializer at `0x1000235a0`
does emit that selector; it must not be substituted for the raw producer merely
because it is nearby or has a similar interface.

31P independently traced the firmware's property callback: `kcbz` supplies the
descriptor field at offset `0x38`, which selects additional-object preparation;
`kcep` supplies the entry-offset field at `0xa0`. These are offsets within the
analyzed software descriptor, not hardware register offsets. The current raw
producer supports prioritizing the ordinary raw/producer-A path. It does not
prove that every historical descriptor field was zero, that no other producer
exists, or that collection-object loading is a missing hardware startup step.

**Engineering decision:** trace the actual raw handoff and its consumers before
attempting to reproduce the optional collection-object path. Do not synthesize
`kcbz`, modify installed metadata or replay firmware operations to force a branch.

## Fallback range preparation is distinct from CPU1 entry

The producer-A preparation path allocates48KiB for a fallback region and publishes
its location through analysis global `0x100c1f2a1d0`. The associated getter at
`0x100c1ad4f20` and helper at `0x100c1ca7070` distinguish the additional-object
range from a16KiB fallback view. The fallback's contents and this range selection
do not establish that CPU1 reaches it.

The range consumer's **entry is `0x100c1aec574`**. The requested REA location
`0x100c1aec7fc` lies inside that function; it is not a second function entry.
The helper call at `0x100c1aec8a0` participates in preparing three16KiB ranges
from the48KiB fallback allocation. This consumer is called at `0x100c1ae5ba4`
inside the handoff function beginning at `0x100c1ae53b8`, before the checked
entry-vector operation at `0x100c1ae5c60`.

**Confirmed static distinction:** the fallback range publication and the entry
pointer are separate objects and consumers. A buffer containing an idle pattern
is not evidence that it is CPU1's effective reset target. Software memory-range
setup, power-state transitions and acknowledged startup writes likewise do not
prove instruction fetch. Conditional cluster-memory preparation remains a
research question; this pass supplies no protection bypass or safe replay recipe.

**Engineering decision:** keep the existing native receipts and entry probes
unchanged. Trace the range consumer's ownership and startup dependencies before
designing a new original controller operation. A new physical test needs a
specific discriminating observation, not another guessed vector or register.

## Validation and limits

Five REA/Ghidra12.1.4 function queries completed in the existing isolated Linux
lab: image wrapper, file loader, raw property constructor, raw property serializer
and handoff range consumer. All three CPU query batches verified loopback-only
network interfaces; the VM launcher used explicit no-network configuration.
No physical USB device or target was attached to these analysis runs.

Apple LLVM21 independently decoded **2,701 instruction words /10,804 bytes in25
disjoint bounded blocks** across the two inputs. The checked words match the
analysis inputs, the retained iBoot carrier and the universal executable slice;
zero mismatches. The companion validation record preserves input/output hashes,
query timing, requested versus returned function entries, body ranges, P-code
coverage/truncation and independent block hashes. Counts describe static coverage,
not execution or semantic correctness of every instruction.

The image-wrapper and range-consumer P-code are truncated at their export limits.
The file-loader P-code omits relevant callback argument flow, and decompiler type
propagation is incomplete. Reported body coverage and a successful query exit
cannot repair those omissions. Whole-function pseudocode is not accepted as
verified source. Behavioral claims are restricted to independently checked
instruction ranges and corroborated callers/consumers; unresolved indirect calls
and runtime conditions stay unknown.

The first CPU query VM completed both requests successfully. Its outer host
wrapper then encountered a bookkeeping error after being edited while running.
The successful query records and VM completion log were retained separately;
this was not silently reclassified as a clean wrapper run. Later wrappers were
kept unchanged while active. No failed or incomplete query supplies native proof.

Public-source rechecking found no change from the retained Gravity bootloader
and FAQ pins used in31O. That is a limited source check, not evidence that nobody
has solved the problem elsewhere. It supplies no new T6050 startup fix.

## Next useful work

1. Follow the normal raw handoff's range-ownership and per-cluster preparation
   consumers using the same retained input and bounded instruction checks. Keep
   optional collection preparation separate from the inferred historical path.
2. Establish the relationship between the effective entry source, published
   ranges and the first secondary's startup prerequisites. Compare it with the
   unchanged m1n1/Linux path; distinguish omitted preparation from merely different
   software structure. Unknown conditions remain unknown.
3. Implement an original bounded operation only after that comparison supplies a
   concrete hypothesis. Validate its memory ownership, failure paths and recorded
   observables offline before asking for a physical boot.

After verified CPU1 entry, the native sequence remains coherency, timer/IPI and
rendezvous checks, then the other Performance and Super clusters, Linux SMP,
scheduling/frequency policy and measured throughput/energy. An online-core count
alone would not establish macOS parity. This checkpoint changes no native image,
macOS file, boot policy or volume. **No restart requested.**
