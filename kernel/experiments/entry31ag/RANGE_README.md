# Conditional reserved-range audit

This original, standard-library-only tool checks one explicitly supplied
producer contract:

```
BootKC-rs base = applicable affine image load base + kcrz
BootKC-rs bytes = kcsz
```

The contract requires a nonzero, 16-KiB-aligned reserved extent. The caller must
explicitly supply the applicable **materialized affine image extent** and its
declared reserved-segment offset/size. File length, a Mach-O mapping, `kclo`, or
an inspector result do not establish that premise by themselves. The tool does
not inspect a binary or running machine, determine a configure mode, infer
load-address semantics, install anything, or select a native experiment.

Fourteen uint64 metadata values are required. Duplicate/unknown/missing keys,
Boolean integers and invalid caller extents are rejected. Conditional producer
misalignment, overflow, zero size, segment disagreement and out-of-image extents
are reported without wrapping or silently rounding. **kcsf is not interpreted**
or substituted for kcrz; other range formulas are deliberately outside scope.

For the original 31AF candidate's recorded legacy inspector properties, the
conditional RS offset is `0x64000` and size `0x54000`, ending at `0xb8000`.
Given a materialized image extent of `0x6c000` and declared reserved region
`0x8000..0x5c000`, those values are inconsistent under this stated producer.
The intended producer's actual configure/firmware binding remains unverified.
The result therefore cannot diagnose the human's logo-only boot.

Run offline tests:

```sh
python3 -I kernel/experiments/entry31ag/test_range_audit.py
```

Given an independently reviewed JSON object containing exactly the fourteen
integer properties (not a raw diagnostic stream):

```sh
python3 -I kernel/experiments/entry31ag/range_audit.py --properties /path/to/original-image-properties.json --image-bytes 0x6c000 --load-base 0xfffffe0007000000 --reserved-offset 0x8000 --reserved-bytes 0x54000
```

Exit0 means the finite evaluation completed; inspect `status` for
`CONDITIONAL_CONSISTENCY` or `CONDITIONAL_INCONSISTENCY`. Neither is unconditional
image acceptance. Every result explicitly leaves native binding, native cause,
image acceptance and new-boot readiness unproven. The canonical metadata digest
binds the provided values, not their provenance. Source or candidate validation
and the other BootKC ranges remain separate obligations.

These three new files do not modify the already executed entry-profile runner,
bootstrap, classifier, classifier tests or their README/source bindings.
