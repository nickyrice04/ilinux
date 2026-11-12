# Direct31AH: pinned Aura and execution-window preparation

This is offline build/format work for the reported direct-entry J716c route.
It does not authorize enrollment, a policy change or a native boot. Native CPU,
USB, firmware, CTXR enforcement and performance remain untested here.

## Source contracts

Aura: `aurora-silicon/aura@bd9f3e8273dc79ae9095c19c2c4f32218446ad4e`.
Its [Mach-O guide](https://github.com/aurora-silicon/aura/blob/bd9f3e8273dc79ae9095c19c2c4f32218446ad4e/docs/macho-boot-object.md)
describes ordinary custom-object parsing with no `__TEXT_BOOT_EXEC` and
`kcbz=0`, direct entry, and a separately padded executable window. No Apple
validator, signature check or private policy selector is patched or overridden.
The existing Permissive lab policy is a future enrollment prerequisite; original
macOS retains its own policy. Format inspection alone does not authorize entry.

The raw image must have its public `AURALOAD` load header. The pinned wrapper
carries it unchanged at file offset `0x10000`, entering at `0x10800`, with its
vector address in the public thread-state field. Neither our old resident
SPTM observer nor an arbitrary Mach-O image is accepted by this padding tool.

The actual November 11 J716c operator report names this Aura revision and Linux
`dc8f6f77934b471a13c91e7780e2d91ebc904b3d`, macOS 27.2.1/26B131 and
mBoot-20457.41.3. Exact operator flags, padded artifact digest and local CDC
diff were not published together. Building this source is a source-based
reproduction, not a claim of byte-identical reproduction of that operator's
unpublished artifact. The project's existing 26.6.2 environment is not qualified
by that newer-firmware report.

## Original bounded padding tool

`pad_boot.py` implements the public geometry from
[`aurora-installer@2d5c44e`](https://github.com/aurora-silicon/aurora-installer/blob/2d5c44e37d04173cb7085120b34862b75a609934/macOS/Recovery/Sources/Account/AuraStage1.swift),
`MachOBootObject.expandExecuteWindow()`. Attribution and GPL-2.0-only terms are
in the source. It is a narrow Python implementation rather than the installer's
Recovery application, and runs only on workspace artifacts in this workflow.

The requested kernel pool is 128 MiB, with 16 MiB kept for Aura and enough
padding for a 2 MiB aligned pool at any loader placement. Every segment stays
fully file-backed and linear in file/VM offsets. Both outer and primary-member
segment records, affected sections and the empty chained-fixup pointer move
consistently. Raw image bytes and entry/vector values do not change.

The tool rejects unknown command/segment inventories, nonempty fixups or symbol
tables, member disagreement, overlapping or unbacked ranges, unexpected CPU or
thread state, missing load header, a loader runtime larger than its slot, already
padded input and bounded arithmetic/size violations. It creates a sparse file
exclusively, follows no input/output symlink, checks zeros and the full output
after writing, and does not overwrite a prior artifact. Its receipt always says
`enrolled=false`, `native_tested=false`, `restart_ready=false`.

A matching kernel needs `CONFIG_ARM64_CTXR_EXECMEM` and the chosen-property
handoff. Padding does not turn an incompatible kernel into a compatible one.
The pool and firmware-reservation checks in Aura and the kernel remain necessary.
This formatter does not simulate Apple execution permissions or live CTXR ranges.

## Optional J716c proxy delta

`j716c-proxy-usb2.patch` and `proxy_policy.h` are original downstream work derived
from public source behavior. They are **not the operator's unpublished patch**.
Baseline and optional variant must remain separate in manifests and outputs.

The pinned public USB implementation deliberately defers normal automatic gadget
initialization on T6050. Its explicit `usb_cdc_schedule()` / `usb_cdc_poll()`
already provide a single scheduled USB2 setup without a reset or watchdog in
this mode. The optional compile flag `ILINUX_J716C_PROXY_USB2` schedules that
existing transition when all the following hold:

- The native-payload path has failed and Aura is entering its fallback proxy.
- Detected chip is `0x6050`, board is `0x0e` (the project's observed J716c tuple).
- The public ADT-based USB2 deferral reports the matching PHY family.
- No earlier host-request window was offered in this boot.

The call uses a 1000 ms delay, zero reserved bits and zero flags. Existing API
state/deadline and once-only polling guards remain. Failure refuses rather than
retrying or resetting a carrier. Native enumeration is unknown until an approved
physical trial; a successful compile or the software guard test does not prove it.

This is not an ESP-installed Stage 1 or ESP Stage 2 configuration. The first
offline images are plain development/proxy builds, without `CHAINLOADING`,
`ESP_STAGE2`, experimental SPTM or resident-monitor flags. Their role is a generic
unconfigured proxy or RAM-chainloaded loader. They contain no lab volume identity,
credentials, firmware extraction or per-user configuration. A production ESP
chain would require the separate upstream stage flags and configuration format.

## Isolated build recipe

[`build-aura.sh`](../../../../virtualization/jobs/094-direct31ah-aura/build-aura.sh)
requires a Linux VM, exact selected source blob pins, Clang/LLD, Rust plus its
`aarch64-unknown-none-softfloat` build-std support, the lockfile's cached Cargo
sources, and the pinned public archive. It uses locked/offline Cargo and a
deterministic source/date/version tag. Build output and temporary files must be
on the writable workspace share; immutable source and project shares stay read-only.

The recipe creates two clean trees and reports two distinct variants, then
runs the 24 original padding cases and six pure software guard assertions. The
receipt and actual build logs, not this README, establish which operations ran.
No result is predeclared here. Compiler/link failure is distinct from native
compatibility. Generic baseline output names are:

```text
baseline/aura.bin
baseline/aura-raw.elf
baseline/aura.elf
baseline/aura-boot.macho
baseline/aura-boot-128m.macho
baseline/build_cfg.h
baseline/build_tag.h
baseline/padding.json
baseline/build.log
```

The optional variant uses the same names under `j716c-proxy/`. Root artifacts
include `source-check.json`, `build-result.json`, `padding-tests.log` and license
notices. Public source and all file-specific copyright/license notices must stay
with redistributed source/binaries. Aurora's built-in logo remains unmodified.
The build also collects root notice files from Cargo's active resolved dependency
graph, records their hashes and declared licenses, and excludes unenabled optional
dependencies. Cargo's raw metadata stays private because it contains cache paths;
the exported index contains no local manifest/cache paths.
Rust `-Z build-std` additionally compiles `core`, `alloc` and `compiler_builtins`
outside that project metadata graph. The separate build-std exporter retains the
installed Rust-source copyright/MIT notices, library copyright attribution and
compiler-builtins' complete MIT/Apache-2.0-with-LLVM-exception license text. Its
index records notice hashes and installed Rust/source/Cargo package versions.

## Native gate

No installation or policy command is provided by this experiment. Before any
future lab enrollment, qualify the whole kernel/DT/modules/initramfs set, actual
firmware profile and memory reservations, entry diagnostics, USB/control, and
the new Mach-O-to-raw restoration policy. The public guide says Mach-O enrollment
enables Kernel CTRR again; merely restoring old raw bytes is therefore not a
complete qualified rollback. Retain the old frozen package and original macOS.
