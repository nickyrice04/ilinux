# Candidate readback: what the frozen collector establishes

Source-only audit, November 15, 2026. No live/private transaction state, policy,
selected object or volume was accessed for this note. The owner result supplied
through the parent agent reports a valid initial baseline and candidate
common/parse/binding/semantic/private-commitment predicates, with only selected
payload exactness/identity and lab CTRR phase requirements false. The preserved
restored-phase predicates pass. These observations concern saved captures.

## Path provenance

The production helper uses qualified generated 31AO `state.c` in
`build/boot-object31ar-native/production-v2/sources`. Its source digest is
`bee973746052f6562a9d2d4817bb5014abb6994a7629944e75b7265f9e76d036`.
The selected-file logic retains the original implementation in
[state.c](../boot-object31aj-native/state.c:129).

The collector obtains the lab and Original volume groups from guarded APFS
metadata, binds the lab's Data and same-container Preboot roles, and reads both
installations' policies. It builds the selected custom-object path using the
lab's current `coih` and `nsih`:

```text
<guarded Preboot>/<lab volume group>/boot/<lab NSIH>/System/Library/Caches/com.apple.kernelcaches/kernelcache.custom.<lab COIH>
```

It reads both policies again after the object access and requires the entire
parsed Policy structures to remain equal. The surrounding controller also
rechecks the bound target and mount before/after collection. It does not assume
that the scratch candidate is installed, reuse the baseline's selected object
path, select a filename by prefix scan, or confuse current selection with the
default Startup Disk.

This formula matches the primary Asahi installer comparator already qualified
in [the retained path review](../../research/native31ag-asahi-m4.md):
[osenum.py at e93743d](https://github.com/AsahiLinux/asahi-installer/blob/e93743d52178b3e26e428fa05174ef549abf30cb/src/osenum.py#L235).
The bounded earlier kmutil REA also qualified a volume-group/boot/active-identity
root and type-selected custom prefix. This supports the generic path strategy;
it does not prove that every installed Mach-O variant uses exactly the same
chosen Preboot context as raw objects on this Recovery version.

The retained generic kmutil string inventory mentions both OS Preboot and iSC
Preboot and a chosen Preboot volume. It is a useful writer-call-path lead, not
evidence that the collector chose the wrong volume. That distinction needs a
bounded writer-call/argument qualification or an actual guarded diagnostic.

## Deliberate information loss in saved snapshots

The collector initializes selection to `NONE` and exactness false. With a custom
object policy reference present, it attempts the fixed selected path. It records
`UNKNOWN` if the read fails or recognition fails, and also excludes the prior
31AI payload. It still returns a successfully collected snapshot in those cases.

Consequently, controller `POSTCONDITION` rather than `READBACK` establishes
successful snapshot collection/save, **not successful object opening, reading,
decompression or recognition**. The v1 preserved-state result only narrows the
selection to `NONE` or `UNKNOWN`, because its exactness-consistency predicate
passes while selected exactness is false. V2 reports those two finite classes
separately. Its CTRR information similarly distinguishes saved `disabled` from
`unknown`; neither is inferred from a failed enabled comparison alone.

The snapshot contains no private selected-path components or carrier/read error
diagnostics. Both are intentionally discarded. After the successful independent
rollback, a fresh current-selection query would examine boot021 rather than the
historical candidate. It cannot reconstruct why the saved candidate was unknown.
An old object's presence in Preboot would also not prove historical selection.

## Recognizer versus writer contracts

The writer command is exactly the non-raw, compressed Mach-O configure path in
[controller.c](../boot-object31ar-native/controller.c:343): `configure-boot`,
`--custom-boot-object ./candidate.macho`, `--volume` the fixed lab,
`--compress`. Raw boot021 restoration is a distinct command with explicit raw
entry point and lowest virtual address. The observed writer zero plus the
human-observed validity/compression/wrapping/done messages establishes a completed
invocation, not byte identity of the installed decoded payload.

[core.c](../boot-object31aj-native/core.c:141) recognizes exact known own payload
sizes/hashes, directly or beneath supported bounded framing. It supports raw,
canonical IM4P, IMG4 with ordered optional opaque context fields, and fully
consumed LZFSE blocks. It accepts optional declared LZFSE size metadata and an
opaque IM4P context-A0 field within its bound. A keybag is classified as blocked,
without decryption. Gzip, unsupported DER, noncanonical or contradictory metadata,
outer trailers, incomplete/extra compressed bytes and limit violations refuse.
The decoded payload must match the entire original candidate byte-for-byte.
An equivalent but transformed Mach-O is unknown.

Relevant bounds are 160 MiB uncompressed, 32 MiB compressed and 161 MiB carrier;
the candidate is 153,190,400 bytes. Owned raw/LZFSE/synthetic-wrapper tests prove
those specific formats. They do not prove the carrier produced by the actual
Recovery writer is supported. No present evidence identifies a compression,
path, transformation, encryption or firmware cause. The lab CTRR mismatch is an
independent failed contract and must be qualified separately.

## Narrow next evidence

Use only the audited v2 saved-state classification first. It performs no fresh
policy/object query, changes no state and requires no reboot.

If the saved class is `UNKNOWN`, a later separately justified candidate
transaction should add a **finite object-read diagnostic at the existing bound
read site**, before rollback: reference present; open/read success; regular file
and size-bound success; recognized carrier and codec classes; keybag presence;
declared-size and stream-completion validity; and exact own-candidate equality.
No selected path, policy reference, identifier, hash, carrier byte or decompiler
text needs to leave memory. Its diagnostics must not relax acceptance or retry a
spent transaction. Private historical-object scans are unnecessary.

Before preparing that transaction, qualify the actual Mach-O writer's chosen
Preboot and CTRR behavior through bounded source/REA evidence and test the new
diagnostic on owned synthetic carriers. A new Linux boot window is not justified
by writer zero or this source audit alone.
