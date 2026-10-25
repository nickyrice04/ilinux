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
python3 -I native/boot/attempt31ad/test_verify.py             # 3 methods (delivery verifier)
python3 -I kernel/experiments/visible31ad/run.py \
  --output build/31ad-visible-host-review --cc clang \
  --target aarch64-none-elf --compile-only                    # 5 AArch64 objects
```

All 70 methods across these five committed suites PASS; the compile-only check
emits five freestanding objects (`COMPILE_PASS_NOT_LINKED`). (The Omarchy-track
`omarchy-kconfig` suite is a separate concern, not part of this candidate, and is
excluded.) The reused `visible31ac` / `observer31ab` sources are byte-identical to
their frozen 31AC/31AB pins. The isolated-VM link job (088) ran:
the two-base link is byte-identical and the 26 QEMU cases PASS. `ordered.py`
produced the 196608-byte candidate (sha256 `406be900…cc16309`) and
`validate_ordered.py` returns `STRUCTURAL_PROFILE_PASS` with
`text_exec 32768 <= boot_exec 98304`. The original-only archive verifies PASS and
is published as prerelease `native-j716c-31ad`. Exact results, environment and
pins are in [`validation.json`](validation.json) and [`manifest.json`](manifest.json).

## What is NOT done (requires independent review, then a fresh approval)

* **Independent M1 offline review** of the released package and candidate.
* **A fresh explicit human authorization** of the exact 31AD candidate and the
  full replace/observe/rollback plan. The 31AC approval does not carry over.
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
