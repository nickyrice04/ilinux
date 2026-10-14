# Job 023 — exact handoff symbolization and DAPF guard validation

Run only in the existing isolated ARM64 job VM. Hold `quiet` in both active
repositories and ensure the existing VM disk is not attached elsewhere.
No native device or host installation is accessed. Run from the original
research checkout, using the actual publish/source paths:

```sh
caffeinate -i virtualization/bin/vzrun --cpus 2 --mem 4 \
  --kernel virtualization/images/alarm/Image-7.1.6-vzrun2-pkg \
  --cmdline 'console=hvc0 root=/dev/vda rootflags=subvol=@ rw rootwait quiet loglevel=3' \
  --disk virtualization/images/alarm/root-btrfs.img \
  --share /ABS/PUBLISH/virtualization/jobs/023-dapf-handoff:job \
  --share /ABS/PUBLISH:ilinux:ro \
  --share /ABS/ORIGINAL/third_party/m1n1:m1n1-source:ro
```

Preserve previous `out/` evidence before a full rerun. The guest service runs
`run.sh` and powers off. It checks the retained job-021 source pin/clean state,
verifies its raw binary hash and exports the matching ELF, symbols and bounded
DAPF disassembly. GNU objcopy must reproduce the exact installed raw binary.
It copies the existing build to a fresh temporary guest directory, applies the
original instance guard, runs baseline/patched synthetic MMIO cases with
ASan/UBSan, links full m1n1, and runs the controller regressions. The generated
binary remains an ignored proof-of-build artifact, not a boot-entry update.

REA uses the existing separate diskless lab, after this VM stops. Follow
`reverse-engineering/rea-lab/README.md`; copy only this matching ELF into the
ignored lab directory. Run by **symbol name** (Ghidra rebases PIE by 0x100000):

```sh
rea function /mnt/lab/dapf-boot023/m1n1-raw.elf dapf_init --provider ghidra --format json
```

Retain its JSON locally. On macOS, from the publish repo, verify the extraction,
relocations, function boundaries and independent instruction decoding:

```sh
python3 -I kernel/experiments/dapf-handoff/audit.py --repo . \
  --rea /ABS/ORIGINAL/build/rea-lab/dapf-boot023/dapf-init-symbol.json \
  --out kernel/experiments/dapf-handoff/evidence.json
```

This produces a minimal ignored analysis-only Mach-O wrapper for Apple's
existing LLVM decoder; it never executes the target. The published evidence
contains only public code offsets, hashes and sanitized hardware layout facts.
Read [findings/results](../../../kernel/experiments/dapf-handoff/README.md).
