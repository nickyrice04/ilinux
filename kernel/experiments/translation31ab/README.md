# 31AB bounded EL2 translation experiment

This original component asks the existing EL2 stage-1 translation machinery about
write permission. It neither writes the candidate address nor changes mappings.
It is **not a deployable Apple host component**. The separately linked fixture
configures its own synthetic page tables inside standard ARM QEMU; that setup
must never be imported into a resident-SPTM image.

`probe.S` is a stackless AAPCS64 leaf returning `{status, raw_PAR}` in x0/x1. It
uses x0–x3 and condition flags; it preserves all callee-saved registers and LR.
It checks CurrentEL before reading EL2 controls; EL0 is excluded because that
read itself can trap. It refuses E2H or TGE, requires all
four DAIF masks already set and SCTLR_EL2.M enabled, then saves PAR, performs
`AT S1E2W`, synchronizes, captures PAR, restores the prior value and returns.
Status 0 means a translation result was captured; PAR.F can still report a fault.
Statuses 1–4 distinguish EL, HCR profile, DAIF and MMU refusals. Refusal returns
zero raw PAR. Normal return restores the caller's 64-bit PAR; traps/nonreturn
cannot promise that. No exception recovery or automatic retry is implemented.

The caller must separately establish a permitted ordinary AArch64 context with
the **64-bit PAR format**, stable page tables and no reentrant PAR user. This
version does not support D128, EL1, VHE, mixed HCR modes or authenticate an Apple
profile. DAIF masking does not establish those prerequisites. The probe does not
decode addresses, permissions or attributes and does not claim a later store
would pass AMCC/guarded protections or produce visible scanout. AT can affect
translation caches or hardware-managed access flags; it is not universally
side-effect-free. No instruction here disables a protection to obtain a result.

The fixture uses Cortex-A57, one TCG CPU, 4 KiB pages and 64-bit descriptors, a
39-bit VA space, 40-bit PA configuration, and hardware AF management disabled.
It contains ten cases: MMU-off, open-DAIF and TGE refusals; Normal-NC writable,
read-only fault, unmapped fault, Normal-WB writable, successful translation to a
different physical page, nonzero page offset, and access-flag fault. The runner
checks exact fault classes, successful attributes/PA, PAR restoration in every
case, poisoned capture bounds, unchanged candidate bytes and final table bytes.
The different-PA case is expected to translate successfully and fail the separate
expected-PA comparison. This is fixture logic, not a native framebuffer validator.
EL refusal and E2H refusal are present but not execution-covered by this fixture.

Root runs the actual instructions inside the isolated Linux VM:

```sh
python3 -I kernel/experiments/translation31ab/run.py \
  --output build/translation31ab-vm --cc cc --ld ld \
  --qemu /usr/bin/qemu-system-aarch64
```

The output must be fresh and outside the source directory. Existing Clang can
compile the original sources without linking or executing them:

```sh
python3 -I kernel/experiments/translation31ab/run.py \
  --output build/translation31ab-compile --cc clang \
  --target aarch64-none-elf --compile-only
```

The runner records all six source hashes, tool versions and bounded command
logs. ELF inspection rejects undefined symbols, retained relocations, overlapping
or out-of-bounds loads, and writable executable segments; it checks the exact AT
and PAR save/restore instruction words. QEMU is only started when `--qemu` is
explicit. It has no network, block storage, serial output, Apple firmware or
monitor emulation. A test PASS qualifies these original instructions in this
model, not native entry, framebuffer visibility or physical secondary startup.

The architectural basis and remaining observer contract are in
[the translation note](../../../research/native31ab-translation-probe.md).
