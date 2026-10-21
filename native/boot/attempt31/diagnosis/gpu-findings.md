# G17 queue follow-up, 2026-10-21

Static REA6.4.0/Ghidra12.1.4 in the existing diskless ARM64 lab. Original
macOS artifacts remained read-only; raw analysis is private. No firmware,
register, security or hardware operation was performed.

The [pinned plan](../../../../kernel/experiments/latency31/gpu-rea-plan.json)
asks whether the G17 queue setup/submission routines establish enough of an
interface to implement a first Linux submission. Both queries completed;
[independent validation](gpu-rea-validation.json) checked152 ARM64 instruction
words against the original kernel collection using Apple LLVM.

| Target | Bounded evidence | Engineering consequence |
|---|---|---|
| AGXKSMKickQueue::configureHardware, `0xfffffe00089959ac`,268bytes |67 matching instructions; includes acquire loads and shared call sites. Ghidra's high-pcode crosses the function boundary and warns about truncated control flow. | Reject whole-function pseudocode. The physical register destination, queue ownership and completion semantics are not established by this dossier. No Linux MMIO sequence can safely be derived from it alone. |
| G17-family KSMKickQueue::addKicks, `0xfffffe0008986470`,340bytes |85 matching instructions; no out-of-body high-pcode, but unresolved authenticated indirect dispatch remains. | A branch-boundary pass is not semantic verification. Resolve the concrete dispatch targets and their shared-memory/notification contracts before implementing queue submission. Do not infer that memory ordering is unnecessary from the lack of an explicit barrier in this bounded caller. |

This is useful negative evidence: a GPU device-ID addition or an isolated
doorbell constant is insufficient for a working driver. It does not imply a
calendar estimate or require deferring GPU work until after all other devices.
Original Linux implementation should proceed in reviewable pieces: verified
firmware ownership/role and memory mapping, bounded command/completion schema,
one checked submission, then one checked render and compositor integration.

The current public Asahi implementation was independently checked at
[`94fb23346d522edf53722357c426a3e58030beea`](https://github.com/AsahiLinux/linux/tree/94fb23346d522edf53722357c426a3e58030beea/drivers/gpu/drm/asahi).
Its hardware enum is G13/G14; device matching has no t6050, and its firmware
compatibility dispatch covers12.3/12.4/13.5. This is a concrete starting-point
gap, not a claim about every external fork or the completeness of Mesa's ISA
support. The macOS26.6.2 release number is not itself a firmware ABI version.
The existence of two ASC nodes does not prove both are needed for a minimal
draw. Earlier blanket schedule/dual-role assertions were corrected in
the [G17 research note](../../../../kernel/experiments/gpu-g17/README.md).
