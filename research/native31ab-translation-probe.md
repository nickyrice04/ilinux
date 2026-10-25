# 31AB: a bounded architectural check for an existing observer alias

Checked 2026-10-25. **An AT write translation is a useful next discriminator:**
it can test the current translation's write permission, output address and
attributes without storing into the candidate framebuffer. It cannot certify
every downstream protection or visible scanout. This is a finite way to narrow
the [observer gap](native31ab-observer.md), not a reason to require a complete
SPTM implementation before proceeding.

## What the instruction establishes

Arm defines `AT S1E2W` as an EL2 stage-1 translation checked for a write, with its
result in PAR_EL1. An ordinary translation fault is reported there. Instruction
access can itself be prohibited or trapped, so a permitted execution context is
still necessary. The initial component supports only ordinary AArch64 EL2 with
E2H/TGE clear, enabled stage-1 translation, all DAIF masks set and an externally
qualified 64-bit PAR format. It does not add EL1 or VHE by extrapolation.
[Arm register reference, S1E2W](https://documentation-service.arm.com/static/60df1943677cf7536a55ddef#page=150),
[Arm memory-management guide, address-translation instructions](https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/LearnTheArchitecture-MemoryManagement-101811_0100_00_en.pdf?revision=1fdc3375-d81c-4457-b786-04fb98557de0).

Preserve PAR, issue AT, synchronize with ISB, capture the raw result and restore
PAR on normal return. Upstream Linux's independent KVM selftest uses the
AT/ISB/PAR sequence and checks output address, memory attributes and access-flag
faults. Its context-reconfiguration workflow is for its own test VM; it is not a
resident-host procedure imported here. The retained comparator is
`03db5f05d4c76d76b32a9d26001e2ec6252f74f8`,3787 bytes,
SHA256 `20d0b6680ce0f520279a454553d115fb3d843f60dd41da086722901299f841a3`.
[Pinned Linux selftest](https://github.com/torvalds/linux/blob/03db5f05d4c76d76b32a9d26001e2ec6252f74f8/tools/testing/selftests/kvm/arm64/at.c#L26).

The successful PAR attribute fields can describe effective attributes rather
than reproduce the literal page-table descriptor. Decode only the qualified
format, and check each page touched by the proposed marker against its expected
physical framebuffer interval. A successful translation to a different physical
page must fail that independent binding check. A non-cacheable Normal-memory
profile can be an initial conservative scope; accepting a different memory type
requires its visibility contract, not silently changing MAIR or the mapping.
[Arm PAR_EL1 definition and effective-attribute qualification](https://documentation-service.arm.com/static/649ae5b238511951cb799288#page=434).

AT is not universally side-effect-free. With hardware access-flag management,
the reported result can assume an access flag is set, and speculative activity
may update that flag. AT does not update the AP/S2AP dirty-state permission bits
described in the architecture's write-permission rule. Thus “no candidate
store” is accurate; “guaranteed no translation-state changes” is too broad.
[Arm architectural AF and dirty-state rules, B4-40 and B4-43](https://documentation-service.arm.com/static/649b0eac38511951cb7993e1#page=40).
These older architectural supplements support the stated baseline behavior;
they do not establish every later extension or this Mac's native profile.

## Original instruction experiment

The new [translation component](../kernel/experiments/translation31ab/README.md)
separates a small stackless probe from a standard-QEMU-only fixture. The probe
has no output-pointer dereference or target load/store. It returns status and
raw PAR in x0/x1, preserves the 64-bit PAR on normal return, and never changes
TTBR, TCR, HCR, MAIR or a protection setting. Its early refusals are distinct
from a captured PAR.F translation fault. EL0 is excluded because even CurrentEL
access can trap; traps/nonreturn do not promise PAR restoration.

The fixture owns its synthetic page tables and uses one Cortex-A57 TCG CPU,
4 KiB pages and disabled hardware AF management. Ten recorded cases cover three
profile refusals plus writable Normal-NC, read-only, unmapped, Normal-WB,
different expected physical page, nonzero page offset and access-flag outcomes.
The runner also checks PAR preservation, unchanged candidate pages, unchanged
baseline table bytes and capture bounds. E2H and EL refusals are implemented
but are not execution-covered by this fixture. It uses no Apple firmware or
monitor emulation. Compilation is separate from root's recorded instruction
execution; neither is a physical Apple result.

## Practical next integration boundary

An accepted entry should first preserve its RAM evidence. Qualify the actual
execution profile, then bound and translate the data it needs before reading
the x1 video record or x2 helper pointers. A read-translation sibling would serve
that distinct prerequisite; the present write probe does not implement it.
Use the qualified PAPT lookup to derive the candidate alias, and check every
marker page's write translation, expected physical address and attributes.
Refuse unknown formats, failed translations, arithmetic overflow or unsupported
attributes; do not repair permissions or replace the monitor's tables to make a
probe succeed.

After those checks, a very small original marker is a meaningful physical
experiment, subject to the separate native review. AT has not exercised AMCC,
guarded-domain restrictions, actual target-store completion, display scanout or
the phase in which the display consumes those pages. Those are bounded residual
questions for the experiment, not a requirement to reverse engineer every
protection before designing it. A distinct visible marker establishes execution
through that point. A blank screen still cannot distinguish rejected entry,
refused descriptors, a trapped access and invisible output, or prove an
Apple-only limitation.

SDK service 45 is not a general alternative printf: the hash-bound 26.5 header
restricts `sptm_serial_putc(uint8_t)` to early panic dockchannel output and says
it is disabled after XNU serial initialization. A single character does not
remove that phase/use restriction or supply a listener. An early-panic
diagnostic could be considered only with those conditions and an actual
receiver qualified; it is not currently the stronger observer path.
[SDK provenance](native31z-public-contract.md),
[descriptor, console mapping and service scope](native31ab-observer.md).

No native AT, framebuffer access, monitor service, firmware patch or boot change
was performed in this investigation. The original fixture is intended for the
isolated Linux VM; the physical observer remains a subsequent integration step.
