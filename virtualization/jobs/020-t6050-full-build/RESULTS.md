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

## DT validation (`dtbs-check-exit.txt`, `dtbs_check-t6050.txt`)

`dtbs_check` exit 0 (dtschema 2026.9). The DTB compiles with 0 dtc warnings,
but the draft DT has **248 schema warnings**, essentially all one class:
*compatible string not in the binding's enum*. The offending compatibles are
borrowed from other SoCs that the t6050-updated bindings don't list:

| Compatible in the draft DT | Count | Expected t6050 value |
|---|---|---|
| `apple,t6031-dart` | 90 | `apple,t6050-dart` |
| `apple,t6030-dart` | 34 | `apple,t6050-dart` |
| `apple,t6000-dart` | 14 | `apple,t6050-dart` |
| `apple,t6031-cluster-cpufreq` | 18 | `apple,t6050-cluster-cpufreq` |
| `*-asc-mailbox` (t6000/t6031/t6030…) | ~100 | `apple,t6050-asc-mailbox` |

**Why it matters (not just schema):** at boot a device probes only if a
driver's `of_match_table` matches its compatible. If a node carries a single
non-fallback compatible no driver claims, that device won't come up. **Next
action for the DT:** audit each subnode's compatible — use the t6050 variant
with the correct generic fallback (e.g. `"apple,t6050-dart","apple,t8110-dart"`),
or extend the DART / asc-mailbox / cluster-cpufreq bindings to list t6050
(our series only added t6050 to sart, nvme-ans and the top-level binding).
This is a DT-source task, not a build blocker.

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
