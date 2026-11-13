# 31AJ native read-only Recovery companion

Original C, built using the installed macOS SDK. This closes the Python-free
parser/codec/snapshot/phase-check implementation gap; it does **not** establish
actual Recovery admission, successful enrollment, native entry or permission to
write anything. No live, capability-admission or private-group command was run
during development. Original Macintosh HD and boot/security settings were not
changed.

The source implements no mount, install, boot-policy write, Startup Disk,
firmware, network, camera or reboot operation. One explicit private-output mode
writes a new, original random comparison key to the caller's already-open empty
private file; this key comes from the system RNG, not Apple credentials or policy.
Its optional live backend runs
only fixed absolute-path `diskutil info/apfs list`, `sysctl -n hw.model` and
`bputil -d` queries. Fixture/control modes never run those commands.

## Build and offline verification

From the checkout root:

```sh
python3 -I tools/boot-object31aj-native/test_native.py
python3 -I tools/boot-object31aj-native/test_native.py --sanitize
python3 -I tools/boot-object31aj-native/build.py \
  --candidate-definition tools/boot-object31aj-native/candidate-definition.json \
  --output build/boot-object31aj-native/new-build
```

Output must be a new workspace directory. The builder records before/after
source bindings, candidate configuration, binary size/hash and false runtime
claims. It refuses changes during compilation and uses only `xcrun clang`,
CoreFoundation, CommonCrypto and libcompression. There is no install/download.
Output is **arm64**, minimum macOS **13.0**, dynamically using system libraries.
Actual Recovery execution remains NOT RUN; the deployment target alone does
not prove that Recovery permits or can run the binary.

The November 13 build used Apple clang 21.0.0 (`clang-2100.4.1.1`), installed
SDK 27.2, C11/O2 and `-Wall -Wextra -Werror`; the sanitizer control adds
AddressSanitizer/UBSan and frame pointers. The older deployment target uses only
the public APIs referenced here. SDK selection does not establish the actual
Recovery runtime's availability or the lab's boot-firmware pairing.

Sixty-four original methods pass normally and with AddressSanitizer/UBSan; an
independent agent repeated all 64 sanitizer methods and reviewed the v2 source.
The build/review receipts bind the source version. The methods
compile a separately labelled synthetic candidate profile and use synthetic
DER, policy text and CoreFoundation plists. They cover codec EOF/consumption,
bad framing, private-data suppression, target/volume/role/paired-Recovery guards,
policy drift, the keyless admission and five bound transaction phases, private
HMAC comparison, key-file/RNG output boundaries, fixture scope and strict profile/JSON
admission. The `--codec-selftest` control uses the real system codec with original
synthetic data; it performs no host query. No fixture identity is an approval or
actual observation of the machine.

Fixture paths are restricted to the producer checkout root compiled into that
binary, with no symlink components. Rebuild locally for fixture tests in a
different checkout. This restriction does not affect guarded Recovery paths or
exact-profile file verification. Build binaries/receipts contain local build
metadata and stay under ignored `build/`; no public binary Release is implied.

## Exact artifacts and compression boundary

The supplied candidate definition binds the new readable 31AJ Mach-O to
153,190,400 bytes and SHA-256
`1ea24f0de4aa7d3e82c70a1b35f815791a48342db1a060100226b84dca7d7d01`.
BOOT021 and 31AF retain their frozen size/hash identities; 31AI is recognized
separately and is not silently promoted to the new candidate.

The container parser handles a narrow canonical IMG4/IM4P subset: exact lengths,
bounded fields, printable four-character type, optional opaque keybag, documented
compression-size metadata and one final opaque context-0 field. Outer contexts
must be in the supported A0/A1 order. It never reads context/keybag contents.
Any keybag blocks decoding and yields no exact payload claim. Gzip is refused.
Exact contained bytes remain separate from signature authenticity, policy and
bootability; opaque properties do not imply PAYP or protection validation.

LZFSE input is capped at 32 MiB; decoded bytes at 160 MiB. The original framing
checker walks public raw/LZVN/LZFSE-v1/v2 block extents and requires exactly one
end marker at the end of the complete input. Then Apple's streaming decoder
hashes bounded output chunks, checks decoded size, progress, input consumption
and END. No decompressed file is written. Unknown payload hashes are never
printed. This extra framing pass is necessary: an actual synthetic test found
that the system decoder could consume a trailing byte and still return END.

Reference contracts: [public LZFSE block layouts](https://github.com/lzfse/lzfse/blob/master/src/lzfse_internal.h),
[Apple streaming API](https://developer.apple.com/documentation/compression/compression_stream_process(_:_:)),
and [the pinned IM4P comparator](https://github.com/tihmstar/img4tool/blob/381f5f755bdafe73eddec4eb83c25d21488621ab/img4tool/img4tool.cpp#L408-L450).
Implementation is original; no Apple decompilation or extracted bytes are here.

Actual owned-artifact controls additionally pass: new raw 31AJ candidate,
system-LZFSE encoding of that candidate, an original synthetic IMG4/LZFSE wrapper,
trailing-byte refusal, actual 31AF under a printable OTHER type and opaque
context-0 wrapper, and raw BOOT021. These are file/codec controls, not live
selected-object, owner-authentication or firmware execution evidence.

## Recovery interface and profile binding

The parent renderer supplies a strict
`ilinux31aj-recovery-profile-v1` JSON profile. Candidate and rollback identities
must equal the compiled pins; the helper record must match this running binary.
Only then is the profile's complete SHA-256 used to bind cross-reboot snapshots.
The renderer separately anchors that profile and helper to its reviewed hashes.
Compiling the whole profile hash would be circular because it contains the
helper's hash; that is deliberately avoided.

Supported production interfaces, for the separately reviewed renderer:

| Interface | Meaning |
|---|---|
| `--capability-check recovery-transaction-v2 --profile FILE` | Require local root/Mac17,6/Recovery and successful synthetic codec control; target state still needs a snapshot |
| `--verify-file FILE --expected-bytes N --expected-sha256 H --profile FILE` | Exact profile candidate/rollback/helper identity only, never an arbitrary hash oracle |
| `--snapshot --target-volume LAB --original-volume ORIGINAL --profile FILE [--comparison-key KEY]` | Fresh guarded policy-selected object and documented semantic state; omit key only for initial admission |
| `--validate-snapshot FILE --phase PHASE --baseline BASE --profile FILE --comparison-key KEY` | Compare strict bound snapshots; omit baseline for initial, and omit both baseline/key for initial-admission |
| `--snapshot-value FILE --key lab_ctrr --profile FILE --comparison-key KEY` | One fixed lowercase enum, from a valid bound production-scope snapshot |
| `--generate-comparison-key --profile FILE` | Exactly 32 new random bytes to an empty, single-link, current-owner 0600 regular stdout file, followed by fsync |

Default invocation only displays help. Production capability/snapshot execution
is not a desktop test command. Do not invoke it merely because compilation or
fixture controls pass. A first already-authorized Recovery preflight must admit
the real environment before any separately authorized write.

There are two narrow private-output exceptions. `--target-group-private` repeats
the same guarded Recovery selection and returns only the validated lab group to
the reviewed renderer's xtrace-off shell command substitution. The renderer
keeps it in a local readonly variable for the owner-authorized system command.
Never run it unadorned, echo it, save it, include it in a receipt or publish it.
Errors use a fixed refusal, not the private value. Normal JSON/snapshots never
contain group IDs, paths, nonces, raw policy or unknown-file hashes. It requires
the transaction's `--comparison-key` and bound snapshot collection.

The RNG mode accepts no comparison key or other operation, never prints JSON,
and rejects pipes, terminals, nonempty output, wrong permissions/owner and
multiple links before writing. The renderer creates the future transaction key
with noclobber after keyless initial admission, under the guarded lab Data's new
0700 state directory. A key read requires a root-owned, single-link, regular
0600 file of exactly 32 bytes, with no symlink components and stable same-fd
metadata. Fixture modes instead require current ownership and a workspace path.
The newly generated random key is unrelated to Keychain, SEP credentials, Apple
anti-replay values or encryption keys. It remains private on the lab Data volume;
neither it nor actual commitments belong in Git, public receipts or chat.

## Snapshot guards and semantic limits

The live path requires root, Recovery and Mac17,6, then validates mounted,
internal APFS System volumes for the exact lab/original names, distinct group
and volume identities, their common container, unique volumes/roles and the
container's Preboot. The lab Data volume must have its expected name/mount and
the lab's group. All existing directories/files are opened read-only without
symlink traversal; no missing volume is mounted automatically. The selected
path is derived only from that guarded target's `coih`/`nsih` policy fields.
Lab and original policies are read again after identity work to detect a
changed selection or semantic state during collection.

The snapshot requires lab-paired power-button Recovery, original Full/CTRR
enabled and existing lab Permissive; no automatic downgrade is attempted.
`Security Mode` may carry the joint SMB0/SMB1 Permissive row; Full/Reduced imply
SMB1 absent when it has no separate row. The parser handles documented numeric
one/absent flags and bare-hex SIP0. Unknown, duplicate, contradictory or malformed
security fields refuse. CTRR status crosschecks the SIP2 flag when present.
An initially unknown lab CTRR is representable; later phase guards are stricter.

Documented nonidentifying semantic values enter snapshots: SMB0–4 and
SIP0/1/3 for both policies, with the intended **lab** SIP2 transition separate.
Original CTRR must stay enabled. Global anti-replay nonce/hash and guarded
identity values remain private and are not treated as unchanged policy bytes.
The code does not hash raw policy or store per-unit IDs.

The read-only human metadata-shape probe found two ordered RPNH rows and one
each of RONH, SPIH and STNG, all present, in both policies. Version 2 preserves
these security-relevant values in memory and compares keyed commitments across
the transaction. RPNH/RONH/SPIH accept only 96 contiguous hex characters or
explicit absent; STNG accepts only decimal uint64 or explicit absent, reflecting
the separately checked formatter interface. Hash case and decimal leading zeros
canonicalize. Missing/extra occurrences, invalid scalars and duplicate flag rows
refuse. The two RPNH rows form an ordered vector; their order is not discarded.

Each policy HMAC-SHA256 uses the new private random comparison key and a
NUL-separated domain containing `ilinux31aj-private-policy-v2`, exact profile
SHA-256, LAB/ORIGINAL role, fixed tag/count labels and canonical values. Snapshot
v2 stores only `metadata_bound`, SHA-256 of the new random key as key ID, and
separate lab/original HMACs. Without a key these three strings are exactly NONE;
such a snapshot can pass only `initial-admission`. Every bound initial/later
phase requires the same key ID; later phases also require both commitments to
equal the initial baseline. No raw Apple hash/counter/nonce is stored or printed.
LPNH is intentionally excluded because any policy operation rotates it; COIH is
the intended custom-object transition. This does not claim policy files stay
byte-for-byte unchanged.

Non-absent unqualified fields—auxp/auxi/auxr and prot/hrlp/losv—still refuse with
fixed `unsupportedPolicyMetadata`; unknown security keys also refuse. They are
not silently discarded. Actual paired-Recovery output grammar and full live
admission remain unverified; unsupported real fields may stop the initial
preflight before writes. No additional live probe was run by the tests.

Primary policy reference: [Apple LocalPolicy contents](https://support.apple.com/en-gb/guide/security/secc745a0845/web).
Static bputil interface findings and system manual review are retained separately
by the parent. This implementation does not claim a live policy read occurred.

## Phase behavior and evidence scope

| Phase | Required result beyond unchanged target/profile/original/lab semantics |
|---|---|
| `initial-admission` | Exact contained 31AF and unbound metadata; no baseline or comparison key; admits only fresh state/key creation |
| `initial` | Exact contained 31AF, bound private metadata; lab CTRR may be unknown |
| `candidate` | Exact compiled candidate and lab CTRR enabled |
| `before-restore` | Known or unknown current object, including NONE after a failed operation |
| `raw-policy` | Lab CTRR disabled; a transient missing custom reference is allowed |
| `restored` | Exact BOOT021 and lab CTRR disabled |

Every later phase requires a valid bound initial baseline, this exact profile
and the same private key/metadata commitments. The renderer owns fresh snapshot production and protected atomic
0600/0700 baseline storage. Validation is a check of supplied assertions, not
cryptographic attestation or independent proof of their provenance/freshness.
The HMACs detect differences between freshly collected trusted-helper snapshots;
they do not authenticate arbitrary JSON assertions or make a copied stale
snapshot fresh. Protected baseline/key storage and the renderer's fresh collection
sequence are required.
Original/default desktop return remains a separate human confirmation.

`--snapshot-fixture` and `--validate-fixture-snapshot` are offline controls.
Their scope is always `SYNTHETIC_CONTROL`; fixture phase success explicitly has
`phase_valid:false`. The production validator refuses them. No test changes
their scope to manufacture a real observation. All normal outputs retain
`read_only:true`, `writes_authorized:false`, and no native readiness is inferred.

Recovery authentication, real selected-file framing/metadata admission, live
guard results, actual installation/restoration, physical CPU/CTXR behavior,
camera readability and performance parity remain **NOT RUN / unverified**.
