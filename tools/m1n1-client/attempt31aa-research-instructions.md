# M1: 31AA research supplement and final adapter verification

**Offline only. No restart, proxy session, monitor call or native boot is ready.**
The registration planner and its focused test instructions were published in
`d2df23b`. This supplement completes the separate local REA investigation left
unpublished at that checkpoint. It does not replace or modify the frozen planner.

Preserve local work and pull with `git pull --ff-only`. Record the reviewed commit.
From the repository root:

```sh
shasum -a 256 -c native/boot/attempt31aa-research/source-sha256.txt
```

Read these additions and the existing public-contract note:

- `research/native31aa-handoff.md`
- `reverse-engineering/findings/cpu-startup31aa/validation.json`
- `native/boot/attempt31aa-research/validation.json`
- `research/native31aa-public-contract.md`

The findings distinguish three things: a local utility copying version-dependent
helper fields; a valid image with no chained fixup work; and fixed monitor
dispatch surrounded by kernel-specific hooks. None establishes acceptance of an
original host image or a successful physical-secondary start. Unused monitor
fields can remain opaque; every service and referenced object actually used
still needs a qualified lifetime, mapping and execution contract.

If the 31AA planner review has not been completed, follow
`tools/m1n1-client/attempt31aa-instructions.md` once. It runs 11 unique C groups
optimized and with ASan/UBSan, plus an AArch64 compile-only check. Expect the
released 12-file source-binding hash:

`dc9177156a783fc08a74a54926f7c00f3e3788a68badca9f5d039f2534f2b87e`.

The fixture retains all 18 CPU records and their source class tags. Width/order
checks cannot authenticate a diagnostic MPIDR as an ADT affinity. The planner's
logical ordinals are predictions, and no registration service is executed.
If that exact review was already recorded, verify unchanged bindings and cite
its report rather than repeating the executable suites. Preserve the original
31AA manifest and instructions unchanged.

Report this supplement in a dated Markdown/JSON pair:

- `native/boot/attempt31aa-research-m1-offline-YYYY-MM-DD.md`
- `native/boot/attempt31aa-research-m1-offline-YYYY-MM-DD.json`

Record the commit, manifest result, whether the planner tests ran or which exact
prior report is reused, and any actionable finding. Distinguish upstream evidence
review from independent reproduction. Local Apple binary analysis, REA, SDK
compile-only measurements and Linux VM results remain NOT RUN on M1 unless
actually reproduced. Raw analysis outputs, monitor records and Apple artifacts
must remain private; public reports contain behavioral findings and metadata only.

Update progress/coordination and push under the established workflow. No external
outreach is authorized. Keep native startup, physical-secondary observation and
performance checks NOT RUN. The next design target is a minimal original image
with qualified placement, entry stack/vectors, monitor transport and exception
continuation. This supplement does not authorize any boot/security/volume change.
