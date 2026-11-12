# Public Aura wrapper format experiment

Original experiment harness, MIT licensed. Public dependency:
`aurora-silicon/aura@bd9f3e8273dc79ae9095c19c2c4f32218446ad4e`,
`tools/macho_boot_object.py`, GPL-2.0-only. Its exact Git blob is
`0a3b111958e3319e743f1676ffbd6d7019f9930b`, SHA-256
`3e8fff2c09179fc34f89e6ef453e29f0b3bd7b488be296e9afce2257b67642d0`.
The dependency remains ignored research data, not vendored or executed on macOS.

The job expects that file at
`build/m5-route-nov12/upstream/macho_boot_object.py` on the project share.
Use the established isolated Linux job VM, exposing this directory as `job`
and the project read-only as `ilinux`. The VM has no NIC or physical-device
forwarding. Do not run `run.sh` on macOS. The dependency hash is checked before
import. No network downloads or package installations occur in the guest.

Three non-executable, synthetic raw inputs exercise aligned, unaligned and
larger layouts. Independent parsing checks command bounds, contiguous linear
file/VM offsets, segment inventory, outer/member agreement, raw-byte roundtrip,
entry/vector fields and deterministic output. Two invalid input cases must
refuse: missing load header and an already wrapped object.

The generated file is named `SYNTHETIC-NONEXECUTABLE.macho`. It contains no Aura
instruction payload. It must never be enrolled, installed, chainloaded or used
as a native test. It is solely input for trusted read-only format inspection.
No installer, boot policy, signature verification or security check is changed.

November 12 result: three fixtures and two expected refusals PASS in Linux
7.1.6-vzrun2 / Python 3.14.8; normal VM shutdown. macOS 26.6.2's read-only
`kmutil inspect` parsed the small synthetic output, exit 0, and derived `kcbz=0`.
It did not enroll, accept for native boot, or execute the object. Full numeric
results and harness bindings:
[format receipt](../../../research/m5-route-2026-11-12-format-check.json).

The 128 MiB padding procedure, real loader build, kernel/DT/module integration,
CTXR enforcement, actual entry and all physical CPU/GPU/power behavior remain
untested by this experiment. There is no new restart-ready package.
