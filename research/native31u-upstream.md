# 31U: qualifying alternate handoff claims and G17C receive-ring code

Checked 2026-10-23 after M1's independent 31T review. This pass reads public
source as data; it runs no downloaded code, hardware operation, boot change or
upstream communication. Earlier research remains frozen. The exact local target
is J716c/T6050 M5 Max with retained 25G83 firmware evidence.

## Result

**A new public report claims 18-CPU Linux operation on T6050 under a resident
SPTM hypervisor. It does not yet supply a qualified workaround for our raw-image
startup failure.** Unlike the earlier unsuccessful probes, this report is a
positive lead that deserves preservation. Its public kernel code establishes
the guest interface, while the host bootstrap implementation and corresponding
physical-entry evidence remain missing from the material located here. There
is still no basis to conclude that only an Apple update can make every path work.

The other concrete result is reusable comparison material: Vinix publishes a
72-byte G17C receive-ring implementation and firmware-specific initialization
research. Its version is 25F71, and its own G17C hardware gate remains closed.
The code helps compare layout and ownership; it does not qualify our 25G83 ABI.

## The new positive CPU claim is a resident-monitor guest result

[SiliconForest commit `5c978948f42c44c725d621bde31d70cd3439167c`](https://github.com/chriskearney/siliconforest-linux/commit/5c978948f42c44c725d621bde31d70cd3439167c)
reports U-Boot loading Linux from SSD on J714/T6050 with all 18 CPUs, storage,
Wi-Fi and SSH. Reading the actual
[qualification document at that commit](https://github.com/chriskearney/siliconforest-linux/blob/5c978948f42c44c725d621bde31d70cd3439167c/Documentation/arch/arm64/t6050-sptm-ans.rst)
adds essential scope:

| Question | Public evidence | Limit |
|---|---|---|
| Machine and firmware | J714s/M5 Pro; macOS 27.0 firmware **26A428**. | Same SoC designation, different board and firmware from our M5 Max/25G83. |
| Execution environment | Resident hardware SPTM; Linux guest IPA and guest RAM; host-mediated storage operations. | This is not documented as the ordinary raw m1n1/Linux handoff. |
| CPU result | Author reports all 18 CPUs booting, sleep/SIMD checks and timer interrupts. | The document references logs in the author's workspace; those logs are not included at the cited public source path. It does not expose physical CPU first-entry records or the host's vCPU-to-physical-CPU execution policy. |
| Changed code in the headline commit | Preserve four firmware-owned NVMe queue pages across U-Boot and Linux, with explicit quiesced RTKit ownership. | A storage handoff change, not a secondary-release implementation. |

The separate
[CPU idle change `6c03bd926fc5672dc91457053c13b3e83ad30048`](https://github.com/chriskearney/siliconforest-linux/commit/6c03bd926fc5672dc91457053c13b3e83ad30048)
explicitly reports J714s/M5 Pro **under SPTM HV**, all 18 CPUs online, and a
register-loss problem during WFI/WFIT. Its actual implementation preserves
callee-saved registers, flushes FP/SIMD ownership, and avoids timed waits on
the affected CPU parts. This is useful post-entry behavior. It cannot explain
how a previously unobserved physical CPU reaches its first instruction.

The host dependency is concrete, not merely terminology. The public
[`apple-dart-x1n1.c`](https://github.com/chriskearney/siliconforest-linux/blob/5c978948f42c44c725d621bde31d70cd3439167c/drivers/iommu/apple-dart-x1n1.c)
describes a Linux guest whose synthetic MMIO operations enter an **x1n1** EL2
host that forwards them to resident SPTM. It implements guest batching and
the declared world-switch interface. It does not implement the host's initial
boot, SPTM residency, or physical CPU release. The
[storage import record](https://github.com/chriskearney/siliconforest-linux/blob/5c978948f42c44c725d621bde31d70cd3439167c/Documentation/arch/arm64/t6050-sptm-storage-import.rst)
also describes the payload as a guest and distinguishes imported driver paths
from the original broader platform work.

This report must not be discarded merely because it uses a guest. A working
resident-monitor environment could be an informative alternative. However,
guest CPU count alone does not identify the physical startup mechanism, and
these kernel changes cannot establish the missing host prerequisites.

### What was checked for the missing host implementation

The public SiliconForest bootloader's
[experimental T6050 profile](https://github.com/chriskearney/siliconforest-m1n1/blob/a5cd88166aa90237466fadc5ea294aa92f91c997/README.md)
is an older ATC/display snapshot, explicitly unbuilt and unqualified in that
integration. Neither this profile nor its source inventory identifies the
x1n1 bootstrap used in the reported run. It therefore must not be substituted
for the unidentified host used by the later resident-SPTM CPU report.

The separately checked public
[`research/native-el2` commit](https://github.com/DjDeveloperr/m1n1/commit/5bf811302301ce0664cf071f54512cd4c21b5f84)
was also checked. It is an August M2 Pro/Windows diagnostic branch, with explicit
language that it is not a boot profile. Its name does not make it a T6050
resident-monitor remedy. Focused public repository and commit searches for
x1n1 located the guest drivers, but no corresponding host bootstrap source.
That is a retrieval limit, not a claim that no such source exists anywhere.

**Required next evidence:** the host source and exact revision, accepted payload
format, firmware/monitor versions, how residency is established, and a record
linking the reported CPUs to physical secondary execution. This would let us
compare a concrete handoff prerequisite with the retained raw path. Without
those facts, neither copying the guest driver nor repeating a raw CPU-release
test discriminates the hypotheses.

## BootKC packaging is still an unqualified acceptance hypothesis

The previously identified
[antiapplefox packager](https://github.com/antiapplefox/m5-linux/blob/35695e2a91feaff53e9df7b62bd1ab030bc58be0/scripts/pack-bootkc.py)
was inspected in full as text, alongside its
[format explanation](https://github.com/antiapplefox/m5-linux/blob/35695e2a91feaff53e9df7b62bd1ab030bc58be0/docs/bootkc-packaging.md).
This reveals specific differences between the advertised structure and the
implemented transformation:

| Advertised prerequisite | Actual packager behavior |
|---|---|
| At least one `LC_FILESET_ENTRY` | Defines the constant but adds no such command. Existing input commands are retained. |
| A `__TEXT_BOOT_EXEC` entry region | Renames existing segments and adjusts or preserves the thread PC; it does not construct that segment or a trampoline. |
| Qualified SPTM allocation/layout | Adds a zero-fill `__DATA_SPTM` region of `0x54000` bytes, with read/write protections, using a T8132 reference size. There is no T6050/version-specific acceptance validation. |
| Acceptance by the actual boot chain | Prints a hardware-validation warning; contains no evidence that the output is accepted by `kmutil`, iBoot or SPTM. |

These are source facts, not a reconstruction of Apple's validator or a diagnosis
of the rejection. Adding the omitted structure would still not establish the
monitor and continuing memory-management contract described in
[31T](native31t-upstream.md).

The later independent
[T6050 raw-path report](https://github.com/rolotrealanis98/m5pro-linux/blob/bb0c75e69d06247faf595641c5a12b0fadc415d2/docs/smp-t6050-raw-path.md)
describes an 18-core J716s M5 Pro with macOS 27.2 boot objects and
mBoot-20457.41.2. It reports both ordinary Mach-O and this packaged image
rejected by `kmutil` before iBoot, and explicitly notes the missing fileset
entry. The exact error text remains absent from the report. Consequently this
is evidence of unsuccessful registration, not an accepted XNU-conditioned
handoff and not proof that all permitted image formats are impossible.

Fresh head checks leave Asahi m1n1 at
[`7cde7d1a784d851ebfee5579fa363c38b14150c0`](https://github.com/AsahiLinux/m1n1/commit/7cde7d1a784d851ebfee5579fa363c38b14150c0),
the shim repository at `35695e2a91feaff53e9df7b62bd1ab030bc58be0`, and the raw-path
repository at `bb0c75e69d06247faf595641c5a12b0fadc415d2`. The new positive lead
above changes what should be investigated; it does not add a tested correction
to the previously inspected Asahi startup path.

## G17C code worth comparing, with explicit firmware and ordering limits

Vinix's current checked revision is
[`ffb1fc5b87660104de4c268804cf1fb2d8afe4bc`](https://github.com/vlang/vinix/tree/ffb1fc5b87660104de4c268804cf1fb2d8afe4bc).
Its [T6050/G17C evidence](https://github.com/vlang/vinix/blob/ffb1fc5b87660104de4c268804cf1fb2d8afe4bc/tools/agx-re/G17_T6050.md)
identifies M5 Max, **macOS 26.5/25F71, AGXG17X 351.2**, and G17C firmware
RTKit-3255.120.11. It describes separate firmware roles and shared-data
construction, but explicitly keeps real submission/firmware boot closed until
the required HAL300 contract is complete. This is a closer public source
comparison than a base-M5 or M4 driver; it is still neither 25G83 validation nor
demonstrated native GPU acceleration.

| Pinned code | Concrete behavior | Applicability |
|---|---|---|
| [Vinix G17 constants and structures](https://github.com/vlang/vinix/blob/ffb1fc5b87660104de4c268804cf1fb2d8afe4bc/kernel/gpu/agx/fw/g17.v#L47) | 256 entries, 72 bytes each, 32-bit type, fixed allowed-type mask; sparse control indices. | Independently published comparison for the observed 72-byte variant; values still require exact local firmware qualification. |
| [Vinix receive operation](https://github.com/vlang/vinix/blob/ffb1fc5b87660104de4c268804cf1fb2d8afe4bc/kernel/gpu/agx/fw/g17.v#L3042) | Checks both indices and sizes, reads producer on each call, rejects out-of-mask or type >=32, copies one record, then publishes advanced consumer through its atomic abstraction. | Producer sampling and fixed type policy differ from our original captured-snapshot utility. Its atomic abstraction is not evidence for our DMA mapping/barrier contract. |
| [Asahi event record](https://github.com/AsahiLinux/m1n1/blob/7cde7d1a784d851ebfee5579fa363c38b14150c0/proxyclient/m1n1/fw/agx/channels.py#L383) | `EventMsg` is fixed at **56 bytes**, with its own event decoding. | Do not substitute this older format for a 72-byte G17C record. |
| [Asahi receive polling](https://github.com/AsahiLinux/m1n1/blob/7cde7d1a784d851ebfee5579fa363c38b14150c0/proxyclient/m1n1/agx/channels.py#L41) | Captures producer once; reads/parses/handles records with modulo advance; publishes consumer after the loop. | A useful algorithm comparison, not a G17C hardware adapter or proof of equivalent memory ordering. |

Matching stride is only one condition. Event meaning, type mask, role, control
addresses, CPU-versus-GPU address domain, visibility, consumer lifetime and
completion remain separate qualifications. No event type is labeled as local
firmware readiness on the strength of these public implementations.

## Retention and decision

Small source files and API responses, exact URLs, UTC check times and SHA-256
hashes are retained under ignored `build/research31u/public/`. Download failures
and size-limit refusals are recorded; a renamed Vinix source path was resolved
to its current pinned location. No downloaded source was executed or imported.

The public evidence now supports a more precise answer: **an alternate
resident-SPTM path has a positive attributed T6050 report, but its initial host
handoff remains unqualified here; no ready-to-reuse raw-start fix was found.**
The next CPU discriminator is that missing handoff provenance, alongside the
retained raw/XNU branch comparison. The GPU source supplies a concrete versioned
ring comparison, while the exact native ABI stays unknown. Native readiness
remains HOLD; this pass proposes no boot procedure or protection change.
