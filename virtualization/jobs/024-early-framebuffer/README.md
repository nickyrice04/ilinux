# Job 024 — observable kernel handoff

Run only in the existing ARM64 Linux build VM. `run.sh` copies the retained
job-020 tree into its own build path, applies the original early framebuffer
instrumentation, tests the real C renderer/parser and AArch64 marker macros
with sanitizers, and links Image. The original kernel is hash-checked and
unchanged. `out/` is ignored and contains build/test/disassembly evidence.

See `kernel/experiments/early-framebuffer/README.md` for scope, results,
reproduction, REA evidence, package provenance and native-test limitations.
The current native checklist is `tools/m1n1-client/stage-b-instructions.md`.
