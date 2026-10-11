# Decisions Log

Format: date, decision, context, alternatives, consequences. Newest last.

## D-001 · 2026-10-11 · Workspace location

**Decision:** The workspace lives at
`~/Documents/iLinux/apple-silicon-linux-research/`, inside the folder the
user opened for this project, rather than at `~/apple-silicon-linux-research/`.

**Context:** The mission suggested `~/apple-silicon-linux-research/` "such
as". The session's project folder is `~/Documents/iLinux`. iCloud Drive has
a `Documents` folder, but `~/Documents/iLinux` is not present in it and has a
different inode, so the workspace is not iCloud-synced (checked 2026-10-11).

**Consequences:** Large artifacts (VM disks, models) can stay in the
workspace. If iCloud "Desktop & Documents" sync is ever enabled, move
`virtualization/images/` and `benchmarks/ai/models/` out of `~/Documents`.

## D-002 · 2026-10-11 · Sanitized device-tree capture only

**Decision:** Never store raw `ioreg` dumps. Use `hardware/scripts/adt_extract.py`
(property names for every node, values only for whitelisted
hardware-description keys).

**Context:** The raw IODeviceTree plane contains serial numbers, UUIDs,
die IDs, boot nonces, entropy and MAC addresses. A first pass leaked `die-id`
through the whitelist; it was removed and added to the denylist.

## D-003 · 2026-10-11 · Portable, libc-independent benchmarks

**Decision:** Write our own small C benchmarks (`benchmarks/src/*.c`) whose
hot loops make no libc calls, plus a Metal benchmark for macOS. The same C
sources build on Linux.

**Context:** macOS-vs-Linux parity must compare hardware and kernel, not
libc `memcpy` or `qsort` implementations. Off-the-shelf suites (Geekbench,
fio, sysbench) are not installed, and installing them needs approval.

**Consequences:** Results aren't comparable with published Geekbench
numbers. They are comparable across OSes on this machine.

## D-004 · 2026-10-11 · Synthetic-weight GGUF models for LLM benchmarking

**Decision:** Generate models with real architecture shapes and random
weights (`tools/synth_gguf.py`) instead of downloading weights.

**Context:** llama.cpp throughput depends on shapes and quant types, not
weight values. No GGUF models were present locally, and downloads need
approval. A bit-identical file can be benchmarked on macOS and Linux.

**Limitations:** Output text is meaningless. Speculative or
quality-dependent features such as MTP and early exit cannot be measured. MLX
comparisons need real MLX models (some exist in the user's HF cache) plus an
approved MLX install.

## D-005 · 2026-10-11 · No background benchmark contention

**Decision:** While the baseline suite runs, agents do only light work
(documentation, web research) so measurements aren't perturbed.

## D-006 · 2026-10-11 · REA not installed until approved

**Decision:** Analyze REA statically and propose a project-scoped
integration, but run `npx rea-agents setup` only after explicit user approval.

**Context:** Setup may modify Claude Code configuration and install
host-level dependencies such as a JDK/Ghidra, both of which require
approval under the mission rules. Details are in
`research/rea/rea-analysis.md`.

## D-007 · 2026-10-11 · No upstream Asahi contributions from this (AI-driven) project

**Decision:** Treat everything produced in this workspace as **local research
and tooling**. Do not submit any of it to Asahi Linux projects (m1n1, linux,
docs, issues): the device-tree draft, findings, or analyses.

**Context:** Asahi's generative-AI policy (asahilinux.org/llm-policy,
2026-09-08) "broadly forbid[s]" generative AI for material contributions.
m1n1 PR templates require certifying no generative-AI use. Interpreting
hypervisor traces with an LLM earns a final warning. Separately, the
copyright policy restricts code written alongside binary disassembly to
trusted contributors and forbids disassembling Metal and the shader compiler.

**Consequences:**
* Upstream value flows only through **human** contributors working
  independently, or through projects whose policies allow AI assistance.
  Omarchy's repo ships an `AGENTS.md`; check its contribution policy before
  any PR.
* Hardware *data* the user personally collects with Asahi's own tools, such as
  ADT dumps, is the user's decision to share. This project won't send
  anything externally.
* REA use stays at the interface/metadata level and never touches Metal or
  the shader compiler.

## D-008 · 2026-10-11 · Disposable Linux VM: vzrun + Arch Linux ARM, built via Docker

**Decision:** Boot an Arch Linux ARM rootfs with the workspace-built `vzrun`
(Virtualization.framework, ad-hoc signed). Use direct kernel boot (the ALARM
7.1.6 kernel has virtio-blk/pci/console and ext4 built in, so no initramfs is
needed) on a 32 GB sparse ext4 image. Docker Desktop, already installed, is
used only as a Linux userland to GPG-verify the tarball against the pinned
ALARM key `68B3537F39A313B3E574D06777193F152BDBE6A6` and to run
`mkfs.ext4 -d`. Jobs run non-interactively through a virtiofs-shared
`job/run.sh`, and the guest powers off when done.

**Alternatives:** UTM, Lima, try-omarchy and QEMU (all host installs; not
approved). Apple `container` (not installed). krunkit for GPU (host install;
later, with approval).

**Consequences:** 2D graphics only (no GPU acceleration). CPU, memory and
storage measurements are valid as *VM* numbers. SME2 is exposed to the guest.
MIDR is masked (part 0x000).

## D-009 · 2026-10-11 · Same compiler target flags on both OSes for parity runs

**Decision:** Parity comparisons use `-O3 -mcpu=apple-m4` on both macOS
(Apple clang 21) and Linux (ALARM clang). `-mcpu=native` resolves
differently: Apple clang knows the host, while Linux clang sees the masked
MIDR. `-march=armv9*` must never be used, because it implies SVE, which this
CPU lacks.
