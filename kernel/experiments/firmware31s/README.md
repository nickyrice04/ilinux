# Bounded relative-dispatch resolver

Original static-analysis tool for signed32-bit little-endian dispatch tables.
It accepts a hash-bound immutable image and an explicit layout. It executes no
input instruction, service, firmware call or target operation.

The CPU31S trace exposed a practical analysis hazard: the table's address is not
necessarily the base used to calculate a branch target. Confusing the two can
assign a service to the wrong owner. This resolver keeps the **table file offset**
and **target anchor** separate, then checks the selected branch targets against
independently supplied address mappings and allowlisted code ranges.

The caller must first establish the table layout, bound, anchor, source mappings
and target ranges from independent evidence. A valid layout is a premise, not
proof those are the firmware's effective runtime values. The resolver does not
identify instruction semantics, authenticate the image, choose a CPU entry,
infer permissions or validate an arbitrary firmware version automatically.

`resolve(image, expected_sha256, layout)` validates the full table extent, signed
arithmetic without64-bit wrap, selectors, distinct nonoverlapping mappings,
whole four-byte target containment and alignment. File aliases and ambiguous
virtual mappings are conservatively rejected. It returns only addresses, offsets,
counts and source identity; no input code bytes or decompiler output. Failure
produces no partial result and does not modify either input.

The command-line form requires explicit input paths and source identity:

```sh
python3 -I kernel/experiments/firmware31s/dispatch.py \
  --image PATH_TO_AUTHORIZED_LOCAL_IMAGE \
  --sha256 EXPECTED_SHA256 --layout PATH_TO_VERIFIED_LAYOUT_JSON
```

Keep private images, layouts and result files in ignored build storage. This
command does not download, extract or execute third-party content. Input errors
are reported without echoing local paths or arbitrary argument strings.

Run the synthetic tests with:

```sh
python3 -I kernel/experiments/firmware31s/test_dispatch.py
```

The22 methods cover independent target/file-offset expectations, negative signed
displacements, the signed32-bit minimum,64-bit wrap refusal,1,024 grid targets,
hash mismatches, complete table bounds, code/file alignment, whole-instruction
containment, ambiguous mappings, strict JSON schema and private CLI errors.
These tests do not emulate CPU startup or firmware protections.

A separate private integration resolves five previously checked selectors in the
retained generic image. Its source/derivative relationship, layout bound, result
hash and limitations are in
[`cpu-startup31s/validation.json`](../../../reverse-engineering/findings/cpu-startup31s/validation.json).
Public findings contain behavioral metadata only. See
[`native31s-firmware.md`](../../../research/native31s-firmware.md).
