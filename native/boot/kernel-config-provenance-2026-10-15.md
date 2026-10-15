# kernel.config provenance in packages boot024–035

2026-10-15, M5 agent. Offline; no package, release or handoff file changed.
Labels: Confirmed / Likely / Hypothesis / Unknown.

## What differed (Confirmed)

The arm64 Images embed their build config (`CONFIG_IKCONFIG=y`: the gzipped
`.config` between the markers `IKCFG_ST` and `IKCFG_ED`). Comparing each
package's `kernel.config` with the config inside its own Image, for all 14
packages extracted on this Mac:

| Packages | Shipped `kernel.config` vs the Image's own config |
|---|---|
| boot021, boot022 (job 020's Image) | identical |
| boot024, 025, 027–035 (11 packages, each Image rebuilt) | 8 lines differ, the same 8 in every package: `RUSTC_VERSION` 0 → 109900, `RUSTC_LLVM_VERSION` 0 → 230101, `RUSTC_LLVM_MAJOR_VERSION` 0 → 23, and five `RUSTC_HAS_*` probes present only in the Images' configs |
| boot036 (prepared, not published) | identical |

No user-visible option differs in any package. Every one of the 8 lines is a
toolchain-detection symbol that Kconfig computes from the installed `rustc`.

## Why (Confirmed for the copy, Likely for the timing)

* **Where the file came from (Confirmed):** job 020 copied its tree's `.config`
  into the package (`virtualization/jobs/020-t6050-full-build/run.sh:132`).
  At that time the tree had no `rustc` detected.
* **How it was carried forward (Confirmed):** jobs 024–036 start from the
  previous package (`cp -a .../native-boot0NN/verified/. "$OUT/export/"`) and
  replace only the Image. Their `cmp "$SRC/.config" "$WORK/.config"` compares
  tree to tree, never tree to the packaged file. So job 020's `kernel.config`
  rode along unchanged through boot035 (SHA-256 `4f7f4599…` in every manifest).
* **When rustc appeared (Likely):** rust was installed in the build VM after
  job 020 configured its tree, most likely for m1n1's `BUILDSTD=1` build: job
  021's `toolchain.txt` already lists rustc 1.99.0. Every later kernel build
  then re-detected it.

## What it changes (Likely: nothing in the built kernels)

* No option differs, and `CONFIG_RUST` is off.
* The 8 symbols only gate Rust support in Kconfig. No C or assembly file under
  the checked-out `arch/` and `drivers/` of the pinned tree references them.
  `init/`, `kernel/` and `rust/` are not in that sparse checkout, so this is
  Likely, not Confirmed.
* The only byte-level effect is the embedded config text itself.
* Attempt results through attempt 15 are unaffected, and attempt 16 (boot035)
  can run as published.

## The guard (Confirmed by test)

`native/boot/kconfig_guard.py` extracts the Image's embedded config.
`make-package.py` now refuses any package whose `kernel.config` is not
byte-identical to it.

* **Exception:** the 11 drifted package names (`DRIFTED`), which may differ in
  toolchain-detection lines only.
* **Shared definition:** the boot036 config check (`control_channel.py`) uses
  the same helpers, so "toolchain detection" means the same thing everywhere.
* **Tests (`native/boot/test_kconfig_guard.py`):**
  * synthetic Images, mismatches and malformed embeddings;
  * a survey of every local package, asserting `DRIFTED` is exactly the set
    that drifts.
* **In practice:**
  * the guarded packager rebuilds boot036 byte-identically
    (`521ffd6d…`);
  * fed boot035's stale `kernel.config` for boot036, it refuses and names the
    8 lines.

Future kernel jobs should export the tree's `.config` as job 041 does. The
packager now enforces this, so a missed copy fails at packaging time.
