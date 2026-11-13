# 31AJ offline payload identity primitive

This small original component addresses M1's candidate-readback gap. It can
compare complete payload bytes with the frozen **153,190,400-byte 31AI**,
boot021 and 31AF size/SHA-256 bindings. It neither selects nor reads an actual
lab object. No live mode, Apple commands, `ctypes`, decryption, codec loading,
mount, write, policy/default change or installation is implemented.

The literal bindings come from the frozen 31AI candidate manifest and 31AG
reference reader. Fixture mode verifies both source-file hashes before reading
the fixture. No old source, artifact, manifest or consumed approval is modified.
Unknown-data hashes, paths, descriptions, four-character type contents,
keybag/context contents and exception details are never output.

## Identity and authority

`payload_label` is `31AI`, `BOOT021`, `31AF` or `UNKNOWN`. An exact label requires
the full payload size **and** SHA-256; a matching prefix, padded known payload
or same-sized foreign file is insufficient. No unknown digest is printed.

`EXACT_KNOWN_PAYLOAD` establishes only byte identity of that contained payload.
Opaque wrapper authenticity/semantics, actual selected-object provenance,
bootability, policy, default and restoration remain separate. Every output
keeps `container_authenticity_verified`, `opaque_semantics_verified`,
`selection_verified`, `restoration_verified`, `bootability_verified` and
`write_authorized` false. Exit zero can also mean `UNKNOWN`; callers must inspect
the explicit status/label and must not use exit status as a restoration gate.

The shallow strict DER subset supports IMG4 or IM4P with printable four-character
types, bounded description, one payload OCTET STRING, optional opaque keybag,
optional type-one/size compression SEQUENCE and one optional **final** opaque
context-0 field. IMG4 manifest/restore contexts stay opaque. Only the known
container and compression metadata is parsed; no manifest, keybag or property
contents are traversed. Duplicate/unknown/out-of-order fields, high tags,
noncanonical/indefinite lengths, truncation and any outer trailer are refused.
An unknown printable type does not prevent exact contained-byte comparison and
is never echoed. Keybag presence blocks comparison/decode and remains unknown;
the component does not claim to determine whether encryption was actually used.

## Bounds and codec contract

- Raw input and declared output: at most **160 MiB**; compressed input: at most
  **32 MiB** before any codec call. The workspace reader has the raw-size ceiling.
- At most seven direct root/IM4P fields and two compression integers; no generic
  recursive DER traversal. Opaque fields are capped at **64 KiB**.
- A compressed output size must match one of the three known reference sizes.
  LZFSE-family magic requires supported IM4P size metadata. Gzip's trailer size
  is only an untrusted allocation assertion until a provider validates it.
- No decompressor ships with this component. Without a provider, compressed
  inputs remain `UNKNOWN`. LZSS is unsupported. Nested decoding is not attempted.

The programmatic interface is:

```python
inspect_payload(data, codec=None)
# Trusted codec(family, encoded_bytes, exact_output_limit)
# returns (decoded_bytes, consumed_input_bytes, reached_stream_eof).
```

An injected provider must independently enforce allocation/work bounds and
certify complete input consumption and EOF. The component requires exact output
length, `bytes` output, complete consumption and literal `True` EOF, then checks
the full known digest. It rejects wrong sizes, partial/concatenated/trailing
streams and failures without printing exception contents. These checks validate
the provider's contract; they cannot sandbox a malicious/hung callback or prove
that an arbitrary provider truthfully implements a codec. A future provider
needs separate implementation/review and stream-end/remaining-input evidence.
The CLI has no provider option and never imports one from fixture data.

## Offline use and evidence

From the checkout root:

```sh
python3 -I tools/boot-object31aj/test_payload.py
python3 -I tools/boot-object31aj/payload.py --help
python3 -I tools/boot-object31aj/payload.py --fixture PATH_WITHIN_THIS_CHECKOUT
```

Default invocation/help performs no file reads. Fixture mode permits only a
bounded regular workspace file, walks every absolute component without following
symlinks, and checks file stability. It outputs sanitized JSON only. Do not copy
Apple artifacts, personal data or unknown live objects into the workspace just
to use this mode. This is a component for a later separately guarded in-memory
readback adapter, **not a live postcondition or complete restoration procedure**.

36 tests use tiny synthetic references and explicitly injected test providers.
They cover malformed DER, all three labels, OTHER fourcc handling, opaque
contexts/keybags, no-secret output, size/EOF/CRC/trailer failures, compressed
bounds, workspace/symlink guards and no live mode. No synthetic executable runs.
The standard-library gzip decoder exists only inside the test module.

A separate local check read the already authorized workspace 31AI raw candidate:
complete 153,190,400-byte comparison returned `31AI`, with all authority flags
false. Its 15,984,123-byte gzip returned `UNKNOWN` / `INJECTED_CODEC_REQUIRED`.
No live file, native boot, Apple codec or new hardware claim was involved.
