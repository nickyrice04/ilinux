# 31P: isolate private firmware analysis from public GPU builds

Date: 2026-10-22. This note corrects an environment claim and records the
separation used for the new offline work. It does not change native boot policy.

## Correction to earlier network metadata

The prior 31O validation said `network: false`. Inspection of the workspace
Virtualization.framework runner shows that its default is NAT enabled and that
the earlier host wrapper omitted `--no-net`. That field did not accurately
describe the configured virtual network device. The offline job did not request
network operations, but that is different from demonstrating network isolation.
The earlier run has no packet capture and cannot establish absence of all traffic.
Frozen receipts are retained unchanged; this is the superseding qualification.

The first 31P guest tool inventory also used that inherited default. It handled
tool versions only. Subsequent private REA and final offline validation runs
explicitly pass `--no-net` and check that `/sys/class/net` contains only `lo`.
Record the actual check result, rather than inferring isolation from job intent.

## Separate environments

Private firmware analysis uses the existing diskless REA/Ghidra VM. Generic
firmware, decompiler output and private instruction comparisons remain under
ignored local research storage. The VM has no physical USB or other native
Apple hardware interface. Only original behavioral findings and validation
metadata are eligible for publication.

GPU foundation builds use a separate existing Linux guest and public source
archives. The completed build also disabled networking and verified loopback only.
That VM receives only a curated public source staging tree, the original build
job and public archives. It must not receive the whole workspace containing
ignored firmware or private disassembly. An initial signed-package transaction
stopped during dependency resolution, before installation. The successful build
instead verified signatures and full trust for ten pinned packages, then
extracted tools into a dedicated guest tmpfs. Installed package lists before and
after are identical. No host package installation is part of this work.

Final offline source/codec tests run without networking or physical USB. Neither
environment emulates Apple's reset state, GPU firmware, coherency or power
sequencing. Compile and unit-test success cannot establish native operation.

## Curated-source validation correction

The first final VM integration failed because the frozen 31O runner invokes
`kernel/experiments/smp31l-analysis/entry_contract.py` without including that
original file in its source closure. Full-checkout host and M1 reviews passed,
but a minimal staged tree exposed the missing dependency. A diagnostic run
confirmed all 122 Python methods passed before the prior intake reached that
missing script. 31P adds the unchanged file to its own 379-file closure and
checks that closure before and after execution. Frozen 31O remains untouched.
The final validation record distinguishes the preceding failures from the
corrected host and curated-VM results. No failed run is counted as a pass.
