# Selected lab object: framing metadata only

This supplement addresses an `UNKNOWN` identity result from the frozen 31AG
reader. It does not change that reader, the 31AH/31AI candidates or their
manifests. `UNKNOWN` means exact identity was not established; it does not prove
that rollback failed or that the selected object is unbootable.

`selected_object.py` imports the exact original project helper only after
checking its frozen SHA-256
`0728fae7dd30fd2ef14dacdf9e25028614f239c254c8fc40c3f8866fde32dc47`.
Live mode preserves the existing local-root/Mac17,6, distinct lab System volume,
same-container Preboot, no-symlink and policy-selected-file guards. It neither
enumerates other boot objects nor chooses a replacement path. Private policy,
identifiers and file contents remain in memory. No mount, write, permission
change, Startup Disk selection, security change or restart is implemented.

The output contains only fixed enums, bounded sizes and false verification
flags. It distinguishes raw data from supported IMG4/IM4P framing; reports
opaque manifest/restore context presence; separates outer or known-payload
padding from nonzero trailers; and recognizes compression magic without
decoding it. Unknown payload types and descriptions are not printed. Neither
hashes of the selected personalized file nor paths/identifiers/bytes are output.

The original Asahi
[IM4P reader](https://github.com/AsahiLinux/asahi-installer/blob/main/asahi_firmware/img4.py)
provides a concrete explanation to test: after the payload OCTET STRING, a
SEQUENCE can declare compression type one and the decompressed size. That
implementation interprets it as LZFSE. The frozen 31AG parser instead accepts
only an optional OCTET STRING in the fifth position; the legitimate compression
SEQUENCE therefore gives `UNKNOWN`. This is source-confirmed behavior, not yet
an observation of the current selected file.

The new classifier recognizes that SEQUENCE, reporting at most a 160-MiB
declared output size. This size is an assertion in the container, not permission
to allocate/decode it. Its original parser never calls a codec or `ctypes`.
An optional keybag remains opaque; its presence prevents an exact-identity
claim. No encrypted data is decrypted and no key/nonce/credential is extracted.

The pinned public
[img4tool format comparator](https://github.com/tihmstar/img4tool/blob/381f5f755bdafe73eddec4eb83c25d21488621ab/img4tool/img4tool.cpp#L408-L450)
distinguishes optional keybag, compression and constructed context-0 fields.
Its printer treats context-0 as a wrapper around PAYP. This supports recognizing
a distinct field boundary; it does not identify this Mac's opaque contents or
establish their security effects. Our classifier never opens that wrapper or
claims PAYP validation.

A single final IM4P context-0 field is consequently labelled
`OPAQUE_CONTEXT_A0`, with fixed combination labels when preceded by the supported
optional keybag and/or compression-size fields. Its content is capped at 64 KiB
and stays opaque; duplicate fields, other tags and out-of-order forms remain
unsupported. An exact payload-byte comparison may report `EXACT_BOOT021` or
`EXACT_31AF` separately, while `match` remains `UNKNOWN` whenever any extra field
is present. `opaque_extra_semantics_verified` is always false. Contained payload
identity is not complete envelope, policy, bootability or restoration proof.

Compression labels follow the public
[LZFSE block magic definitions](https://github.com/lzfse/lzfse/blob/master/src/lzfse_internal.h#L276-L281):
`bvx2`, `bvx1`, `bvx-`, `bvxn` and `bvx$`. The classifier also recognizes
`complzss` and the gzip signature. A matching prefix alone proves neither a
valid compressed stream nor the identity of its decompressed output. A later
decode, if warranted and separately reviewed, belongs in a different bounded
tool; this utility does not enable it implicitly.

Raw or container payloads that exactly match the already hash-verified project
references can report BOOT021 or 31AF. A zero-padded known prefix, a nonzero
trailer, a keybag or compression metadata retains `UNKNOWN` and reports the
relationship separately. This prevents an unreviewed normalization from
silently turning a partial identity into exact restoration evidence. Even an
exact payload match does not verify the default boot selection, boot policy,
previous execution, physical bootability or restoration.

Offline checks:

```sh
python3 -I tools/m1n1-client/direct31ai/test_selected_object.py
python3 -I tools/m1n1-client/direct31ai/selected_object.py --help
```

Forty-nine synthetic test methods cover DER bounds, optional compression metadata,
opaque contexts/keybags, suffixes, unknown-data suppression, reference/helper
pins, default-help behavior, root/Mac guards and the exact guarded selection
flow. Test metadata and mock host commands are synthetic; no Apple
command is run by the suite. Default invocation only displays help. Fixture
mode can read a workspace binary fixture without Apple calls. A live command
requires the parent's review and the existing locally authorized root check;
do not run it just because these offline tests pass.

Unsupported DER now also reports a narrowly bounded `der_diagnostic`. It gives
the fixed failing stage, root/header extents, canonical-length facts, at most
eight top-level child headers and at most eight IM4P field headers. High tag
numbers are labelled `HIGH`; their numeric values and all field contents stay
private. Only booleans for the known IMG4/IM4P magic values are returned. The
outline does not recurse into manifests, keybags, payloads or extra metadata.

This helps distinguish a failure in the frozen recursive DER parser from a
later container/field constraint. It does not relax any identity guard. A high
tag inside an untagged opaque manifest, for example, can make the frozen tree
parser refuse while the shallow outline still describes the outer containers.
Such a result remains `UNKNOWN`. File size alone establishes no candidate
identity; a 445,430-byte file is not labelled 31AF merely because its size is
close to that artifact. Unsupported framing leaves normalization/restoration
unverified, even when a bounded outer extent can be measured.
