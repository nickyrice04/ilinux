# 31AD: corrected ordered-fileset candidate (offline package)

31AD answers the 31AC `configure-boot` rejection (reported fileset error, exit
71). The offline analysis in [`research/native31ad-fileset-ordering.md`](../../research/native31ad-fileset-ordering.md)
raised a **Hypothesis**: the 31AC image placed its normal executable text after
its boot-executable text, so the installer's split-protection file-offset check
underflows an unsigned subtraction. 31AD relinks the unchanged, hash-pinned 31AC
payload so normal text precedes boot text, and wraps it in a nested `MH_FILESET`;
the code bytes do not change. The cause of exit 71 is **not** confirmed — the
real Recovery error was never captured — so 31AD *tests* the hypothesis.

## What is finished and verified (host, offline)

From the repository root, with stock Python and Apple clang:

```sh
python3 -I kernel/experiments/bootimage31ad/test_ordered.py   # 32 methods
python3 -I kernel/experiments/bootimage31ad/test_image.py     # 23 methods (control history)
python3 -I tools/recovery31ad/test_render.py                  # 5 methods
python3 -I tools/recovery31ad/test_write_render.py            # 7 methods
python3 -I kernel/experiments/omarchy-kconfig/test_kconfig_fragment.py  # 8 methods
python3 -I kernel/experiments/visible31ad/run.py \
  --output build/31ad-visible-host-review --cc clang \
  --target aarch64-none-elf --compile-only                    # 5 AArch64 objects
```

All 75 test methods PASS; the compile-only check emits five freestanding objects
(`COMPILE_PASS_NOT_LINKED`). The reused `visible31ac` / `observer31ab` sources are
byte-identical to their frozen 31AC/31AB pins. Exact results, host environment and
source bindings are in [`validation.json`](validation.json).

## What is NOT done (requires the isolated VM, then review and approval)

* The canonical two-base link and the 26-case QEMU run (VM job
  `virtualization/jobs/088-ordered31ad/`): **NOT RUN** — macOS has no ELF linker.
* The 196608-byte ordered candidate (`bootimage31ad/ordered.py`), its real
  SHA-256, the original-only archive and its release: **not produced**. No dummy
  pin is shipped; see [`manifest.json`](manifest.json).
* The production one-paste Recovery pages (`tools/recovery31ad/`): the **rollback**
  block is fully determined now; the **install** and **diagnosis** pages need the
  real candidate pin.
* Native Recovery install, 30-second marker observation, boot021 rollback, Linux,
  SMP, GPU and performance: **NOT RUN / HOLD**.

## Boundaries

`install_authorized` is **false**. The 31AC authorization does not carry to this
new image; a fresh explicit human approval of the exact 31AD candidate and the
full replace/observe/rollback plan is required before any write. macOS stays
intact and Full Security; the lab stays Permissive; no new volume or security
downgrade is part of this plan. M1 follows
[the review and Recovery sequence](../../tools/m1n1-client/attempt31ad-instructions.md).
A successful install would make the ordering hypothesis Likely; it would not
prove native entry, display, SMP or performance. A second rejection leaves the
cause Unknown and must not be retried with altered flags.
