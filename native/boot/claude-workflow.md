# Agent handoff: M5 implementation, M1 controller, later Linux configuration

Continue the existing Boot Lab entry and installed boot021. Do not restart the
installation process. Read AGENTS.md, coordination.md and the current Stage-B
checklist; historical milestones are not current authorization or results.

M5 owns offline diagnosis/build/package work. M1 owns independent intake,
readiness, one human-started USB handoff, screen-evidence review and sanitized
report publication. Coordinate file ownership and quiet locks before work.
The next Linux-side agent can handle configuration and desktop tests once a
usable native Linux control channel/root exists; the current diagnostic init
has no shell, SSH, network or resident agent. Existing Omarchy VM work is separate.

Each cycle: consume the report, define one falsifiable question, inspect exact
source/binary evidence, implement original Linux changes, test in isolation,
publish a pinned private package and explicit one-attempt instructions. Preserve
all old artifacts/results. Controller success and VM boot are not native success.

Use REA for specific authorized driver/interface questions: function discovery,
cross-references, call/control flow, disassembly and pseudocode where supported.
Keep binaries and raw analysis local in the isolated lab. Verify significant
claims against original bytes, independent disassembly, public source or native
observations. Reject out-of-body decompiler flow and label unresolved behavior.
Do not copy proprietary code, extract secrets, bypass protections or disguise a
request to evade a tool's safety restrictions. If blocked, report the restriction
and continue with allowed source/observation work. More decompilation is useful
only when it resolves a current engineering uncertainty.

At this handoff attempt 14 reached native diagnostic PID 1 and then reset
silently. Boot034 tests genpd sync_state as the trigger (Image only; the cmdline
already carries `pd_ignore_unused`). Keep boot032's five GPIO exclusions.
Native attempt 15 remains NOT RUN until M1 readiness and the human's start.
The hypervisor track is separate and currently blocked at the chainload.
