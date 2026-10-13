# Driver-interface pass: evidence and implementation handoff

2026-10-13, agent B. Continues F-070–F-072 and the existing native bring-up;
does not restart the project. Claude/A retains the live VM, wakeup, display
and video-default work. This pass uses the separate diskless Linux lab.

## Concrete progress

* A local Linux DockChannel HID patch fixes malformed-message bounds,
  termination and cleanup problems, and rearms input after work-allocation
  failure. It exercises seven actual pinned driver functions in an isolated
  ARM64 Linux harness. See [input patch and reproduction](../../../kernel/experiments/driver-contracts/dockchannel-hid/README.md).
* Original ACIPC software ring/buffer arithmetic and a strict extractor of
  selected N1 operational configuration are implemented and Linux-tested.
  They are building blocks, not a functioning network driver. See
  [N1 experiment](../../../kernel/experiments/driver-contracts/acipc/README.md).
* Fourteen REA/Ghidra kernel-member queries completed across input, audio,
  mic transport, camera, ANE host API, GPU, network management, DCP and RTKit.
  Independent Apple LLVM decoding matches all **976 instruction words** to
  the original carrier. Four whole-function pseudocode results are rejected;
  the other ten still require semantic review. No generated Apple code is
  copied into Linux.
* Two small ISP routines retain the public Linux command IDs and sizes.
  This supports reusing those particular layouts and avoids an unnecessary
  rewrite. It does not establish camera firmware or sensor compatibility.
* Three additional N1 AirshipDK ring routines completed REA analysis. Their
  **131 instruction words** independently match the cache, bringing this
  pass to **17 functions / 1,107 words**. All three pass numeric bounds
  checks and still require semantic review; error-path callees are absent.

## Linux test results

[validation.json](validation.json) records versions, scope and outcomes.
The actual extracted HID functions reproduce ten independent failures on
the baseline (ASan, UBSan or explicit behavioral assertions); the patch
passes all ten plus three valid cases with Clang/compiler-rt 21.1.2.
This includes avoiding an out-of-range interface array access, rejecting
truncated input, releasing malformed queued work, and rearming after an
allocation failure. It is not a full kernel-object or native hardware test.

Six optimized VM parser runs process 10 million valid synthetic packets
each, alternating baseline/patched order. Median time is **29.581 → 29.868
ns/packet (+0.97%)**; [raw measurements](hid-parser-benchmark.jsonl) and
compiler flags are retained. There is no physical input, real HID consumer,
core pinning or controlled frequency in this microbenchmark. It quantifies
software checking overhead, not responsiveness or energy on native Linux.

The ACIPC arithmetic tests pass 8,525,654 wrap cases plus bounds/overflow
checks and 49,840 queue state/count cases on Linux GCC 15.2.0 and Clang
ASan/UBSan; 18 Python configuration/extraction tests pass.
The expanded REA evidence/extraction suite passes 26 tests on macOS and
ARM64 Linux. The lab uses guest-only Clang for sanitizers because its
Alpine GCC package lacks the required runtimes.

## N1: the useful code was behind the visible stubs

The visible Centauri dext executables have only four-byte dummy text.
The separate DriverKit cache contains the actual AirshipDK transport code.
An original bounded extractor verifies its digest and function-start table,
then copies only **524 selected instruction bytes** into a 1,344-byte
synthetic ELF analysis carrier. It has no program headers or entry point;
it is neither the original library nor an executable implementation.
No complete cache, shared strings or protected service code is copied.

[n1-targets.json](n1-targets.json), [n1-checks.json](n1-checks.json) and
[artifact-manifests.json](artifact-manifests.json) retain provenance.
On valid local state, the head/tail routines use division-based remainder,
not a power-of-two mask. Their u16 bound/head/tail state and full/empty
guards support a one-empty-slot software queue interpretation. This agrees
with selected static ACIPC configuration declaring non-power-of-two sizes.
The mapping from that local helper to each active firmware queue is still
unknown: do not equate its bound with usable DMA slots, infer phase bits,
or guess memory barriers from it. External error handlers are unresolved.

The original Linux-portable experiment therefore keeps ordinary software
indices and explicit geometry separate from future hardware descriptors.
No Apple instruction sequence or decompiled implementation is translated.

## Artifacts, method and evidence quality

Reference host: Mac17,6 / t6050 M5 Max, macOS 26.6.2 build 25G83.
REA 6.4.0 and Ghidra 12.1.4 run in a diskless 2-vCPU/8-GiB Linux lab with
JDK 21; no live Omarchy disk is attached. The analysis VM does not expose
native GPU/ANE/ISP/N1/DockChannel hardware. No personal sensor capture occurs.

[targets.json](targets.json) pins questions, addresses, selected members and
derived SHA-256 values. [checks.json](checks.json) records each evidence ID,
original-byte anchors, numeric function bounds, decoder checks and limitations.
Source carrier SHA-256 is
`26ddfbe95c7e6ac9a76aedac424576bf00467e7c13da49dd82f8010efdb75093`;
the running boot's choice of carrier remains unverified. Raw binaries,
assembly and pseudocode stay in ignored `build/rea-lab`.

The member extractor preserves original virtual addresses and code bytes;
it does not apply collection fixups. Unresolved authenticated pointers and
external calls remain unknown. The gate now also detects bad-instruction /
truncated-control-flow warnings. A numeric bounds check is necessary but
does not certify semantics. In particular:

| Target | Result and permitted conclusion |
|---|---|
| HID `parseNewBytes` | 200 high-pcode operations outside body: reject whole pseudocode. Input patch derives from public Linux source, not this result. |
| DockChannel async read | Bounded static routine allows one outstanding read and returns busy on a second; prepares count/completion state before interrupt enable. Supports preserving receive rearming. Absolute register contract and runtime ordering still require hardware evidence. |
| Audio `setDescriptor` | Index below four; host command has four 16-byte slots. This is not proof of physical ADMAC descriptor bitfields or DMA ownership. |
| AOP mic command | Out-of-body operation plus truncated control flow: reject pseudocode. Transport/interface ownership remains unresolved. |
| ISP doorbell | Conditional 32-bit store through a runtime base and offset. No constant register address established. |
| ANE host command | Wrapper has asynchronous send and wait/cancel/timer calls. It does not reveal the full firmware protocol or establish Linux ownership of the active ANE path. |
| GPU queue kick | Two 64-bit stores through runtime-derived offsets; indirect synchronization target unresolved. No G17 command submission is implemented. |
| N1 PCI client selection | Cross-boundary/truncated output: reject whole pseudocode. Manager is lifecycle glue, not proof of packet descriptors. |
| DCP send | Eight-instruction forwarding adapter with unresolved indirect destination. No display RPC ABI recovered from it. |
| RTBuddy endpoint send | State-gated indirect transport operation and conditional retry are visible; removed-block warning and unresolved dispatch limit interpretation. N1 ACIPC is a separate protocol. |
| ISP pool configuration | Static construction uses opcode `0x0117`, length `0x9c`, u32 channel, adjacent u16 pool type/count, two u32 metadata-size values, and data-block count one at offset `0x94`. Matches the named fields of pinned Linux `cmd_ch_buffer_pool_config_set`. Metadata-size values and actual sensor selection remain unknown. |
| ISP primary scaler | Static construction uses opcode `0x0b01`, length `0x38`; this matches pinned Linux output configuration. Branch-dependent stride calculations must not be generalized to every format. |
| GPU firmware kick | Constants corresponding to notification types `0x83` and `0x87`, with low payload bits derived from `(argument & 7) << 2`, are visible before indirect dispatch. Compare with old m1n1 framing; endpoint, argument meaning and selected path remain unverified. Do not copy old G13/G14 queue assumptions into G17. |
| Audio interrupt read | 271 operations outside the small body: reject whole pseudocode. No ADMAC interrupt-register change follows. |

These are static observations, not runtime traces. Labels and class names
alone do not prove that a particular method is invoked on this machine.

## Coverage of the requested driver families

Every row remains **partially answered**, not hardware-complete. Exact source
pins and links for accelerators are in [the source map](accelerators-source-map.md);
input/audio/USB details are in [the transport scout](../../../kernel/experiments/driver-contracts/dockchannel-hid/scout.md).

| Family | What the project has / can reuse | Blocking work and next bounded test |
|---|---|---|
| GPU / GPU matrix accelerators | VM VirGL/Metal and Venus work; pinned native DRM driver selects G13/G14. G17 queue/kick code is accessible. | G17 firmware initialization, queue layout, memory/fences and shader ISA. Validate a firmware notification and its dispatch first, then one native bounded submit. GPU matrix accelerators are separate from ANE. |
| Display | VM presentation; existing DRM/KMS + AFK/EPIC implementation. | Resolve ordinary AFK send target, ring lifetime and current IOMFB ABI; later native boot framebuffer before accelerated display. |
| Wi-Fi / Bluetooth | VM virtio networking; native PCIe/DART foundations and new offline ACIPC evidence/tests. | Descriptor/index/phase/credit rules, normal firmware lifecycle, netdev/cfg80211 and HCI integration. USB Ethernet remains the planned native fallback. |
| Neural Engine | macOS reference benchmark; old public ANE driver and ordinary host API symbols. | Current firmware protocol, model/compiler contract and device ownership remain unknown. Stop at protected-service boundaries. No native ANE backend is claimed. |
| Webcam | Existing Linux V4L2/vb2/ISP includes M3 support; two selected command layouts match. | t6050 firmware startup, sensor configuration, metadata requirements, IRQ/DMA and stream completion. Start with synthetic/test patterns if available after native boot. |
| Microphone | Linux AOP/AFK/EPIC and `aop_audio.rs` already exist; macOS AOP audio host component identified. | Active mic routing and new firmware ABI, device ownership, DMA/clock negotiation; command parser tests before any capture. No audio recording made. |
| Speakers / headset / HDMI audio | Existing ASoC, Apple ADMAC, MCA and codec foundations; t605x AudioDMA command helper analyzed. | ADMAC evolution registers/descriptors, clocks/routing and t6050 configuration. Preserve speaker-protection requirements; do not enable uncalibrated speaker output. |
| Keyboard / trackpad | Existing DockChannel/MTP/HID driver, now with a locally tested bounds/rearm patch. | MTP firmware startup, DT resources, interrupts, reset/SMC mapping and physical input delivery. First keyboard, then multitouch/haptics on an authorized RAM-only boot. |
| Mouse / external HID | Linux HID is the reusable upper layer; VM input is already functional. | USB transport first for wired devices; N1 HCI first for Bluetooth. No separate proprietary mouse algorithm is needed for standard HID. |
| USB-C / USB audio / external cameras | Standard Linux USB/HID/UAC/UVC stacks; public Apple PHY/DWC3/XHCI code. | t6050 PHY tunables, PD/SPMI/retimers and IRQ/DMA resources. Validate controller/port enumeration before higher-level peripherals. Thunderbolt is separate. |
| Unified memory / DMA | Existing Apple DART/IOMMU and DMA APIs; sanitized t8110-class bindings. | Per-device stream IDs, translation ownership, coherency, reset and buffer lifetime. VM shared memory does not validate native DART. |
| Storage, CPU and power | Previous SMP/PMGR evidence and draft SART/NVMe patches; A owns VM latency. | Continue existing native gates/build plan; avoid broad changes here while A works. Energy efficiency needs native residency/thermal measurements after reliable boot. |

Other useful next artifacts: ordinary AirshipDK ring/completion helpers;
AppleHIDTransportSCMCommon framing; AppleT6050TypeCPhy tunables;
AudioDMA transfer programming; ISP IPC command/reply dispatch; AFK shared
ring management; AppleT8110DART invalidation; SMC charge/temperature interfaces;
AVD/AVE and ProRes command queues. Rank these by a specific Linux question,
not by binary size. Exclude credentials, personal sensor data, SEP, pairing,
DRM and protected service implementations.

## Reproduction and continuation

Use the [lab README](../../rea-lab/README.md) and acquire `quiet` before a lab
boot. Never attach A's active disk. Derive only explicitly allowlisted members.
The new runner validates pinned hashes, requires explicit target IDs, refuses
existing output files and caps each REA query at 90 seconds:

```sh
python3 -I /mnt/source/analyze_drivers.py /mnt/lab/driver-targets.json \
  /mnt/lab/artifacts /mnt/lab/evidence/new-pass camera-pool camera-scaler
```

On the host, the existing trusted LLVM tools can independently cross-check
the saved results without running the target:

```sh
python3 -I reverse-engineering/rea-lab/crosscheck_drivers.py \
  reverse-engineering/findings/driver-interfaces-2026-10-13/targets.json \
  build/rea-lab build/rea-lab/driver-checks-repeat.json
```

Next: integrate the HID patch into a disposable native-kernel build and
compile the full object; continue N1 ring/completion and camera firmware
questions; carry the supported/unsupported matrix into agent C's native
configuration handoff. Agent C must use native packages and drivers after
the existing boot gates, not the VM kernel or macOS bridge configuration.
No native boot, security, partition, firmware or macOS changes occur here.
The lab is stopped and its `quiet` lock released. The local HID patch is
ready for A's disposable native build; the ACIPC model remains an offline
experiment until descriptor and hardware ownership evidence exists.
