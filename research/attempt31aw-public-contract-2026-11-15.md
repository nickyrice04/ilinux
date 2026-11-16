# 31AW: documented policy reset versus Mach-O enrollment expectations

November 15, 2026. Public project source and an installed Apple manual were read
as data. No policy, private transaction, selected object, device or mount was
queried. No command below was executed, and this note authorizes no host action.

## The supported distinction

**Confirmed documentation:** the installed Apple `bputil(1)` manual describes
`--permissive-security` (`-n`) as reconstructing LocalPolicy without preserving
existing security options. Only options specified in that invocation are included
in the resulting policy. It separately defines `--disable-kernel-ctrr` (`-c`) as
the Kernel CTRR downgrade. The manual identifies paired power-button Recovery as
the required environment for these operations. The generic manual is
`/usr/share/man/man1/bputil.1`, SHA-256
`dacc771e3c49f0ec86feb582ba64e23b0e71c4ee49b1da647ec7f0f77d0a5a1b`.
Root independently observed the same distinction in `bputil --help`; this
research pass read the manual and did not run that executable.

**Inferred design lead:** reconstructing a lab policy in Permissive mode without
requesting the CTRR downgrade could remove an inherited disabled-CTRR option.
This is a supported whole-policy reconstruction mechanism, **not an enable-only
operation**. The documentation does not establish preservation of an existing
custom boot reference, auxiliary policy commitments, or every field required by
our current transaction. Consequently it is not a direct command recommendation
or permission to substitute a writer in the frozen AU controller.

A future strategy would need an explicit new reconstruction phase, an independently
justified field-change allowlist, exact Original-policy preservation, target and
owner binding, and an independent boot021 restore. Rebuild/fixture tests can
qualify its state machine; they cannot establish the actual policy transition.
The present exact-candidate and enabled-CTRR conditions remain unchanged. Owner
authorization would be required before any such lab policy operation.

## What current Aura source does and does not establish

The [Mach-O guide at current Aura `52af355c`](https://github.com/aurora-silicon/aura/blob/52af355ca2c3b814f7610003bcefda16f6bfb943/docs/macho-boot-object.md)
expects Mach-O enrollment to restore enabled Kernel CTRR, including when it was
previously disabled. It distinguishes that LocalPolicy observation from CTXR
execution confinement and warns about subsequently enrolling a raw image.
This is a project-reported behavior, not proof of the service semantics in the
unqualified Recovery runtime used by AU.

The [hand-enrollment script](https://github.com/aurora-silicon/aura/blob/52af355ca2c3b814f7610003bcefda16f6bfb943/tools/recovery/enroll-stage1.sh)
checks disabled CTRR before raw enrollment. Its Mach-O branch checks object
properties, runs the writer and checks the exit; it does not read back an enabled
CTRR postcondition. Its [status documentation](https://github.com/aurora-silicon/aura/blob/52af355ca2c3b814f7610003bcefda16f6bfb943/docs/recovery-enroll.md#status)
also distinguishes stubbed desktop testing from an actual run of this general
script in Recovery.

The current installer has the same ordering expectation. At
[`832788c8`, `BootSelection.swift`](https://github.com/aurora-silicon/aurora-installer/blob/832788c858f7bc5db8ba67d1232844977ffa8489/macOS/Recovery/Sources/BootSelection.swift#L57),
its policy authorization includes both Permissive and CTRR-disable options, then
its Mach-O enrollment uses compression. The
[setup and update paths](https://github.com/aurora-silicon/aurora-installer/blob/832788c858f7bc5db8ba67d1232844977ffa8489/macOS/Recovery/Sources/RecoveryActions.swift#L584)
call those helpers in that order. Neither this source nor the guide qualifies an
additional enable-only writer. AU's disabled-CTRR result therefore remains a
separate unresolved postcondition, even after repairing its decoder.

## A fresh exact-board source lead

Erik Bourget publicly points to
[`ewb/j716c-daily`](https://github.com/betizzel/omarchy-m5/issues/12#issuecomment-6904255259)
as his working 16-inch M5 Max setup. At observation the branch resolves to
[`4e1f8e6a`](https://github.com/aurora-silicon/linux/commit/4e1f8e6a13191c42b3ce1bb1519e48440c06d79a).
That source adds a J716c-specific ANE preload identity for firmware 27.0/26A428
and names iBoot 20457.1.29; it explicitly distinguishes board-patched firmware
identity from a shared release/layout. This is useful evidence against choosing
hardware tables solely by release name. It is not an ANE workload result or an
installed Stage 1/LocalPolicy recipe.

The branch's J716c tree contains an explicitly unit-derived Thunderbolt DROM.
Do not copy that per-unit data into this project. Review generic changes and
retain our independently obtained board/unit data and admission checks.

The earlier [J716c engineering report](https://github.com/cameroncooper/linux/blob/5e11068a1c6d8fccb155bc6e0159cc16107e53ec/Documentation/arch/arm64/apple-j716c-bringup/README.rst)
still provides a different, bounded all-18-core/GPU/network baseline on firmware
27.2.1/26B131 and mBoot 20457.41.3. It expressly excludes an enrollment recipe.
These are distinct baselines, not interchangeable guarantees for our current
26.6.2 environment. No source reviewed here establishes an Apple-only CPU blocker
or makes an OS/firmware update authorized.
