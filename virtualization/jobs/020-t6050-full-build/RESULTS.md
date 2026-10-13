# Job 020 results: full t6050 native kernel build

Ran 2026-10-13 in the Linux guest toolchain (18 cores). Reproducible via
`../run.sh`. No native boot; build + validation only.

## Build

* Base: AsahiLinux/linux `77cb8f24c2381a8abb7272d7bbdec548d6426a8a`
  (`base.txt`), + the committed t6050 series 0001–0007 (`series.txt`,
  `am.log`, am exit 0).
* **`make Image modules dtbs` exit 0, 249 s, 0 distinct warning/error lines**
  (`build-exit.txt`, `build-warnings.txt`).
* Config (`config-selected.txt`, full `kernel.config`): every requested
  bring-up symbol set, none missing — `ARM64_16K_PAGES`, `ARCH_APPLE`,
  `APPLE_{RTKIT,MAILBOX,SART,DART,PMGR_PWRSTATE}`, `NVME_APPLE`,
  `DRM_SIMPLEDRM`, `FRAMEBUFFER_CONSOLE`, `HID_DOCKCHANNEL`, `BLK_DEV_INITRD`.

## Artifacts (`artifacts.txt`, in the guest at `/var/tmp/t6050-build`)

| File | Size | sha256 (short) |
|---|---|---|
| `Image` | 44,468,736 | `f9cf7c00…` |
| `t6050-j716c.dtb` | 61,326 | `5d6fe648…` |
| `initramfs.cpio.gz` | 302,448 | `15565c4b…` |
| modules | 1,571 built | — |

The Image/modules/initramfs stay in the guest (only useful for a native
boot, which is user-gated). Digests here fix provenance.

**Job-021 export note:** these exact payloads have now been exported into the
checksummed private boot package. The seven-patch Image was linked before
section 5's separate HID hardening/object test and was not relinked afterward.
Do not describe that additional HID patch as included in this Image.

## DT validation (`dtbs-check-exit.txt`, `dtbs_check-t6050.txt`)

`dtbs_check` exit 0 (dtschema 2026.9). **The t6050-j716c.dtb produces zero
schema warnings** (`grep "^…/t6050-j716c.dtb:" dtbs_check-full.log` → 0).

> **Correction.** An earlier version of this file reported "248 schema
> warnings" for our DT. That was a filtering error: the first filter matched
> any log line containing `t6050`, which caught warnings belonging to **other**
> Apple SoC DTBs (t6022, t6031, t6030…) whose allowed-enum text lists
> `apple,t6050-*`. Warnings are prefixed with their own dtb path; attributed
> correctly, **our DT has none**. The filter in `run.sh` is fixed. See the
> DT compatible audit below (F-056, corrected).

**DT compatible audit (probe-readiness).** Beyond schema, each device probes
only if a driver's `of_match_table` matches one of its compatibles.
`../../../kernel/experiments/t6050-dt/probe-audit.sh`, run against this built
tree, confirms **every bring-up-critical device matches a driver** on its
t6050 string or its generic fallback:

| Device | Matches driver on | Driver |
|---|---|---|
| AIC | `apple,t8122-aic3` (fallback) | irq-apple-aic |
| DART | `apple,t8110-dart` (fallback) | apple-dart |
| ASC mailbox / RTKit | `apple,asc-mailbox-v4` (fallback) | soc/apple/mailbox |
| PMGR pwrstate | `apple,t8103-pmgr-pwrstate` (fallback) | pmdomain/apple/pmgr-pwrstate |
| PMGR bus | `apple,t8103-pmgr` (fallback) | simple-pm-bus |
| NVMe (ANS2) | `apple,t8132-nvme-ans2` (fallback) | nvme/host/apple |
| SART | `apple,t6050-sart` (our patch) | soc/apple/sart |
| pinctrl/GPIO | `apple,t8103-pinctrl` (fallback) | pinctrl-apple-gpio |
| cluster cpufreq | `apple,t8112-cluster-cpufreq` (fallback) | apple-soc-cpufreq |
| watchdog | `apple,t8103-wdt` (fallback) | apple_wdt |
| I²C | `apple,t8103-i2c` (fallback) | i2c-pasemi |
| UART | `apple,s5l-uart` | samsung_tty |
| timer / cache / OPP / fixed-clock / simple-bus | generic | core |

The only compatibles with no driver match are the 18 **CPU cores**
(`apple,sotra-m` / `apple,sotra-p`). That is **correct**: CPUs are
core-enumerated, not driver-probed, and both names are already in the CPU
binding enum (`Documentation/devicetree/bindings/arm/cpus.yaml`), following
the same pattern as M4's `apple,donan-e/p`. No code references the bare CPU
compatible (only a separate `-pmu` node would, for perf).

**Audit conclusion: the draft DT is schema-clean and probe-ready; no
compatible change is needed.** (Perf PMU and any not-yet-present device nodes
are separate, non-compatible questions.)

## DockChannel HID hardening against the real in-tree driver (`dch-exit.txt`)

Built `drivers/hid/dockchannel-hid/` from the asahi tree, `W=1`:

* **Baseline: 0 W=1 warnings** (`dch-baseline-warnings.txt`).
* The `a351bff` input-bounds patch (24 insertions, 4 deletions) **applies
  cleanly to the real driver**, patched build exit 0.
* **New warnings introduced: none. Warnings removed: none**
  (`dch-patched-warnings.txt` identical to baseline).

So the hardening compiles cleanly against the actual kernel driver with no
warning regression — the build-level check the patch needed before any native
input test.
