# Hardware Inventory — Reference Host

Collected 2026-10-11 with read-only commands (`sysctl`, `system_profiler`,
`ioreg`, `diskutil list`, `csrutil status`) and the sanitized device-tree
extractor [`scripts/adt_extract.py`](scripts/adt_extract.py). Serial numbers,
UUIDs, ECID/die IDs, nonces and MAC addresses were deliberately **not**
recorded.

Evidence labels: **Observed** = read directly from this machine. **Measured**
= produced by our benchmarks (see `benchmarks/results/`). **Spec** = Apple
marketing or specification figure, not verified here. **Inferred** = our
interpretation of observed data.

## Identity

| Item | Value | Evidence |
|---|---|---|
| Machine | MacBook Pro 16-inch class, model identifier **Mac17,6**, board target **J716c** (`J716cAP`) | Observed (`hw.model`, ADT root `compatible`) |
| SoC | **Apple M5 Max**, platform name **t6050**, `chip-id` **0x6050**, board-id 0xe, chip-epoch 1 | Observed (ADT `/chosen`, `platform-name`) |
| CPU family | `CPUFAMILY_ARM_SOTRA` (0xF76C5B1A), subfamily `CPUSUBFAMILY_ARM_HC_HD` (5) | Observed (`hw.cpufamily` decoded with SDK `mach/machine.h`) |
| Kernel | Darwin 25.6.0, `xnu-12377.161.14~5/RELEASE_ARM64_T6050` | Observed |
| macOS | 26.6.2 (build 25G83) | Observed |
| System firmware / OS loader | 18000.161.10 (ADT reports the boot stage as `mBoot-18000.161.10`) | Observed |
| SIP | Enabled | Observed (`csrutil status`) |
| Hypervisor support | `kern.hv_support=1` (Hypervisor.framework available) | Observed |

## CPU

18 cores in three 6-core clusters, two core types, **no efficiency cores**.
macOS names the performance levels "Super" (`hw.perflevel0`) and "Performance"
(`hw.perflevel1`).

| Cluster (ADT `cluster-id`) | ADT `cluster-type` | ADT `compatible` | macOS perflevel | Cores (MPIDR) | L1i / L1d per core | L2 |
|---|---|---|---|---|---|---|
| 0 | **M** | `apple,sawtooth` | 1 "Performance" | cpu0–5 (0x000–0x005) | 128 KiB / 64 KiB | 8 MiB shared |
| 1 | **M** | `apple,sawtooth` | 1 "Performance" | cpu6–11 (0x100–0x105) | 128 KiB / 64 KiB | 8 MiB shared |
| 2 | **P** | `apple,everest` | 0 "Super" | cpu12–17 (0x200–0x205) | 192 KiB / 128 KiB | 16 MiB shared |

Observed. Notes:

* The ADT uses a new cluster type letter **`M`**. Earlier generations used
  `E` and `P`. Any Linux or m1n1 code that keys on `E` or `P` needs updating
  (Inferred).
* The `compatible` strings name older core designs (`sawtooth`/`everest`).
  Apple reuses old names in the ADT. Don't treat them as the microarchitecture
  name; `hw.cpufamily` says SOTRA (Inferred).
* Every CPU node has `no-aic-ipi-required`, which suggests IPIs use the
  system-register fast-IPI path rather than AIC (Inferred).
* Cache line 128 B; base page size 16 KiB; timebase 24 MHz (Observed).
* Per-core `cpu-impl-reg`, per-cluster `acc-impl-reg`, `coresight-reg` and
  `cpu-uttdbg-reg` MMIO windows are recorded in `adt/adt-nodes.tsv` (Observed).

### ISA features (Observed, `hw.optional.arm.*`)

* Armv8.x/9.x baseline: LSE/LSE2, RCpc (LRCPC/LRCPC2), PAuth/PAuth2/FPAC,
  BTI, SB, DIT, ECV, WFxT, CSSC, HBC, FlagM/FlagM2, FRINTTS, JSCVT, FCMA, AFP,
  RPRES, CRC32, AES/PMULL/SHA1/SHA256/SHA512/SHA3, DotProd, I8MM, BF16/EBF16,
  FP16/FHM, RDM.
* **SME, SME2, SME2p1**, plus SME_F64F64, SME_I16I64, SME_F16F16, SME_B16B16,
  SVE_B16B16. Maximum streaming vector length is 64 bytes (**SVL = 512 bits**).
* **No non-streaming SVE** (`FEAT_SVE` absent). Measured consequence: code
  built with `-march=armv9.2-a+sme2` (which implies SVE2) crashed with SIGILL.
  `-mcpu=native` and `-march=armv8.6-a+sme2` work. Any Linux distribution
  baseline that assumes SVE when SME is present would break on this CPU.
* **MTE**: FEAT_MTE, MTE2, MTE4 and MTE store-only are present; MTE3 and
  MTE async are not reported.
* Not reported: FEAT_SSBS, FEAT_SPECRES/SPECRES2.

## GPU

| Item | Value | Evidence |
|---|---|---|
| Cores | 40 | Observed (`system_profiler`) |
| Driver class | `AGXAcceleratorG17X` (G17 generation, "X" variant); firmware via `AGXFirmwareKextG17RTBuddy` | Observed (IORegistry) |
| ADT nodes | `sgx` = `gpu,t6050`; two GPU coprocessors `gfx-asc` and **`gfx1-asc`** (both `iop,ascwrap-v6`); `mapper-gfx-asc` = `iommu-mapper,gfx` | Observed |
| API | Metal 4; families apple7–apple10, metal3, metal4 | Observed (`gpubench info`) |
| Working set | `recommendedMaxWorkingSetSize` 115.4 GB; max single buffer 86.6 GB | Observed |
| Matrix hardware | FP16 GEMM throughput is about 4× the scalar FP16 FMA peak, consistent with the M5 "Neural Accelerators" in each GPU core | Measured + Inferred, see `benchmarks/` |

## Neural Engine

| Item | Value | Evidence |
|---|---|---|
| ADT node | `ane0`, `compatible = ane,t8132exclave`, with its own DART `dart-ane0` | Observed |
| Drivers | `H11ANEIn`, `AppleT6050ANEHAL`, `H1xANELoadBalancer`, **`ANEExclaveProxy`**, `ANEClientHints` | Observed |
| Interpretation | On this macOS version the ANE is driven through an **exclave**, a secure isolated domain, with XNU holding a proxy. The block is labelled as t8132-generation (M4-family) ANE IP | Inferred |
| Core count | Not exposed by any interface checked so far | Unknown |

## Memory

| Item | Value | Evidence |
|---|---|---|
| Capacity | 128 GiB (`hw.memsize` 137438953472; usable 136450785280) | Observed |
| Controller | `mcc,t6050` (`AppleT6050MemCacheController`) | Observed |
| Page size | 16 KiB | Observed |
| Bandwidth | GPU copy ≈ 540 GB/s, GPU read ≈ 560–578 GB/s; single CPU thread STREAM copy ≈ 136 GB/s | Measured (smoke runs; full baseline in `benchmarks/results/`) |

## Storage

| Item | Value | Evidence |
|---|---|---|
| Device | `APPLE SSD AP2048Z`, 2 TB, firmware revision 2973.120, TRIM yes | Observed |
| Controller | ADT `ans` = `iop,ascwrap-v6` (RTKit coprocessor), driver `AppleANS3CGv2Controller`; `sart-ans` = `sart,coastguard` | Observed |
| Layout | GPT: `Apple_APFS_ISC` 576.7 MB, main APFS container 2.0 TB (Macintosh HD system snapshot, Preboot, Recovery, Data ≈ 889 GB used, VM), `Apple_APFS_Recovery` 5.4 GB | Observed (`diskutil list`, read-only) |
| Encryption | Inline AES via the SEP/AES engine (`aes,s8000` node) | Observed node, Inferred role |

## Other SoC blocks (selected ADT `compatible` values)

| Block | ADT compatible | macOS class |
|---|---|---|
| Interrupt controller | **`aic,3`** | `AppleInterruptControllerV3` |
| IOMMUs | `dart,t8110` (all DARTs) | `AppleT8110DART` |
| Power manager | `pmgr1,t6050` | `AppleT6050PMGR` |
| Internal PCIe | `apcie,t6050` (+ `pcie-apiodma,t6020`) | `AppleT6050PCIe` |
| Thunderbolt PCIe | `apciec,t6050` ×3, `acio,v2` ×3 | `AppleT6050PCIeC` |
| USB | `usb-drd,t6050;usb-drd,t8142`, `atc-phy,t6050;atc-phy,t6040` | `AppleT8142USBXHCI`, `AppleT6050TypeCPhy` |
| Display | `disp0,t605x` + DCP (`iop,ascwrap-v6`) + 4 × `dispextN,t605x` | `AppleDCPExpert` |
| Coprocessor mailbox | All IOPs use `iop,ascwrap-v6` | n/a |
| Keyboard/trackpad | `mtp` (`iop,ascwrap-v6`) + `dockchannel,t8002` + `hid-transport,mux` | n/a |
| SMC | `smc` (`iop,ascwrap-v6`) | `AppleSMC*` |
| I2C / GPIO / WDT / UART | `i2c,t8101`, `gpio,t8101`, `wdt,t8101`, `uart-1,samsung` | n/a |
| Audio | `iop-audio,controller`, `admac-evolution,t6050`, mic paths via `iisaudio,isolated-stream-proxy` | n/a |
| Secure domains | `sep` + `esm` (`iop,exclave-sep-manager`), `aop-exclave-mailbox`, `isp-exclave-proxy`, ANE exclave | n/a |
| Media | `avd,t8103;avd,t6020` (decode), `ave2` ×2 (encode), `apr,n0/n1` (ProRes), `jpeg,t8101` ×2, `scaler,t8101` ×2 | n/a |
| Other | `apple-processor-trace,t6050`, `error-handler,t6050`, `mcc,t6050` | n/a |

The full sanitized node list (656 nodes) is in `adt/adt-nodes.tsv` and
`adt/adt-sanitized.json`. Mapping to Linux drivers is in
`../reports/compatibility-matrix.md`.

## Power / thermal context for benchmarks

* Battery cycle count 46, max capacity 99% (Observed).
* Energy mode: `pmset` reports `powermode 2` on AC and `0` on battery.
  `system_profiler` describes the AC setting as **"Low Power Mode: Yes"**.
  Every benchmark run records the active source and mode in `env-*.txt`. A
  single-thread FMA run gave the same result on battery (Automatic) and on AC
  (≈125 GFLOP/s), so the AC low-power setting does not cap single-core peak.
  Its effect on sustained multi-core and GPU power is **untested**.

## Installed tooling relevant to the project (Observed)

Xcode 27.0 (27A266a), Apple clang 21.0.0, Swift 6.4, system Python 3.9.6,
Homebrew 7.0.7 (python@3.12, uv, node 26.5, gh, llama.cpp b10280 with ggml
0.18.1 Metal/BLAS/CPU-apple_m4 backends, openblas, gcc, zstd, xz), Docker
Desktop (installed, daemon not running), lldb, dtrace, otool, nm,
dyld_info. **Not installed:** UTM, QEMU, Lima, Tart, Apple `container`,
vfkit/krunkit, Ghidra/Java JDK, radare2/rizin, MLX, coremltools, fio,
shellcheck, cmake, ninja, Rust, Go.

## Asahi applicability

The t6050 SoC is outside the generations Asahi Linux supports. Current status,
with sources, is in `../research/asahi/asahi-status-m5-2026-10.md`. **Native
Linux boot is not possible on this machine today.**
