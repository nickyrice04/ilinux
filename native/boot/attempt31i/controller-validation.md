# 31I offline validation

Reproduction: `virtualization/jobs/067-smp31i/run.sh`, using the existing isolated
ARM64 VM and pinned m1n1 client57a9339. Native31I/CPU1/Linux SMP NOT RUN.
Counts, source manifest and evidence hashes are recorded in `validation.json`.

The inherited367 full-symbol /344 image-only31H test methods remain part of the
intake. Added tests exercise the new controller and readback gate, source closure
and supervisor. The public31H classification fixture proves the previous
refusal and corrected address-only acceptance. All65,536 synthetic upper16
patterns are covered with full mirror equality; wrong known fields and malformed
reports still refuse. No upper-bit semantic value is inferred from these tests.

Controller tests compare target-operation traces to the frozen valid31H path,
including publication, exact starts, conditional timer requests and all fault/
deadline handling. Actual pinned proxy serialization and BootArgs/ADT parsing
run only in the VM with independent literal allowlists; the full success/timeout
cases carry matching nonzero upper fields. No serial transport is constructed.

The helper/recorder bytes are unchanged; prior assembly and width-harness evidence
remains applicable. No kernel rebuild is needed because only original helper-side
preflight/report validation changed. Native MMIO safety, reset firmware and cache
visibility cannot be established by these models. Separate M1 intake and a human
start remain necessary; offline `restart_ready:false` is intentional.
