# 31AV offline decoder investigation

This is an original, workspace-only codec differential and a **proposal**, not a
Recovery controller or a boot package. It has no policy, selected-object, mount,
writer or live dispatch. It reads only explicitly supplied workspace fixtures;
the candidate mode additionally requires the exact project's own candidate pin.
Frozen AU/AT/AJ sources and all historical state remain unchanged.

## Confirmed desktop result, November 15, 2026

The existing decoder can reject a valid input on this desktop. A deterministic
1,048,576-byte xorshift32 sequence (initial state `0x19671234`, shifts 13/17/5,
one low byte after each update) was compressed separately with Apple's buffer
and streaming encoders. Both 1,059,159-byte outputs pass the frozen frame walker
and decode byte-exact through Apple's buffer API. With all input supplied at
once and `FINALIZE`, the frozen 65,536-byte streaming decoder returns an error.
All six destination sizes tested (31, 4096, 65535, 65536, 65537, 262144) show the
same first-call error. There are 272,727 input bytes left at that point.
The credited output count excludes bytes from a call returning ERROR, just as
the frozen implementation does.

The same inputs decode exactly with 65,536-byte output and source chunks of
4096, 32768, 131072, 262144 or 786432, finalizing only after the last input chunk
has been supplied. Supplying all input without finalization also decodes these
valid controls. Neither observation establishes a general solution or justifies
dropping finalization: the installed SDK explicitly supports finalizing a
complete input and recommends doing so for detecting truncated input.

The exact 153,190,400-byte project candidate was also compressed with both Apple
encoders. Both versions decode exactly through the frozen **65536-byte** path on
this desktop. Both fail with the diagnostic **65535-byte** destination instead.
The new buffer proposal decodes both exactly and identifies their known size and
SHA-256 correctly. These are generated own carriers, not the historical selected
Recovery file.

**Limits:** the AU result established `DECODE_REJECTED`, but did not preserve a
decode subreason or a qualified Recovery library identity. No historical or live
selected carrier was read here. A desktop counterexample establishes a real
compatibility defect in the existing strategy, not the cause of that particular
AU refusal, firmware acceptance, successful candidate installation, Linux boot,
SMP or performance. The separately failed AU CTRR requirement is untouched.

## Bounded original proposal

`buffer_proposal.c` reuses the unchanged, SHA-pinned strict DER and LZFSE frame
helpers. It retains compressed/input/output bounds, declaration checks, keybag
blocking and exact known **size plus SHA-256** identity. It allocates the frame's
declared output total **plus one byte**, checks the allocation bound, decodes, and
requires the returned output count to equal the exact framed/declaration total
before hashing. It never infers identity from decoder success alone.

The extra byte matters: Apple's buffer API may return the destination capacity
after truncating output. An allocation exactly equal to the expected length
would make saturation ambiguous. Strict framing is also mandatory: both Apple
APIs accepted a trailing-byte control, while the proposal rejected it before
decoding. A forged frame total smaller than the actual expansion is rejected by
the proposal's returned-count check, including the capacity-saturation case.

This uses at most **160 MiB plus one byte** of temporary output storage, compared
with the frozen streaming decoder's 64 KiB output buffer, plus library scratch.
For the candidate, temporary output is 153,190,401 bytes. Allocation failure is
a refusal. No policy or admission guard has been changed. Integration would need
its own review, frozen-source closure and Recovery environment controls.

## Reproduction

From the repository root, using only the installed SDK:

```sh
/usr/bin/python3 -I tools/codec31av/test_codec.py
/usr/bin/python3 -I tools/codec31av/test_codec.py --sanitize
```

Both suites passed **12 methods**, zero skips, on macOS **26.6.2 / 25G83**, Apple
clang **21.0.0 (clang-2100.4.1.1)**, active Xcode SDK **27.2**, arm64, `-O2`, minimum
deployment macOS 13.0. Sanitized builds add AddressSanitizer and UBSan. They link
the installed `libcompression`; its concrete shared-cache implementation/version
is not separately qualified. The installed Command Line Tools header was also
read for the stream API contract; it was not substituted into the Xcode build.

Each suite executes a 77-case generated C matrix, both genuine-candidate encoder
round trips, and negative controls for source/output bounds, truncation,
trailing/duplicate EOS, malformed or noncanonical declarations, DER, keybag,
wrong hashes, a same-known-size wrong-hash raw control, unsupported CLI and path
aliases. The matrix makes 474 traced streaming trials; 12 intentionally reproduce
the two valid synthetic failures across six output sizes. Candidate comparisons
make 22 trials and reproduce two 65535-byte output failures. Proposal assertions
pass despite those recorded frozen/API failures. The suite's PASS refers to its
control expectations and proposal behavior, not success of every stream call.

All generated fixtures, binaries, build receipts and detailed finite matrix
results stay under ignored `build/codec31av/`. No third-party source was executed.
The public LZFSE header layouts were cross-checked as data against the frozen
frame walker's offsets; that check found no corresponding offset defect.

Sources: [Apple stream API](https://developer.apple.com/documentation/compression/compression_stream_process(_:_:)),
[Apple buffer API](https://developer.apple.com/documentation/compression/compression_decode_buffer(_:_:_:_:_:_:)),
[public LZFSE layout](https://github.com/lzfse/lzfse/blob/e634ca58b4821d9f3d560cdc6df5dec02ffc93fd/src/lzfse_internal.h).
