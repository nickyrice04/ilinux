#!/usr/bin/env python3
"""Copy only the readable IM4P krnl payload, excluding IMG4 personalization.

No signature, encryption, security service or access-control operation occurs.
The locator is kept in memory; identifier-bearing Preboot paths are not saved.
The result is a compressed research input, not a bootable or verified image.
"""
import argparse
import glob
import hashlib
import json
from pathlib import Path

LIMIT = 128 * 1024 * 1024
LOCATOR = "/System/Volumes/Preboot/*/boot/*/System/Library/Caches/com.apple.kernelcaches/kernelcache"


def tlv(data, offset, end):
    if offset + 2 > end:
        raise ValueError("truncated DER header")
    tag, size = data[offset:offset + 2]
    offset += 2
    if size & 0x80:
        n = size & 0x7f
        if not 1 <= n <= 4 or offset + n > end or data[offset] == 0:
            raise ValueError("unsupported DER length")
        size = int.from_bytes(data[offset:offset + n], "big")
        offset += n
        if size < 128:
            raise ValueError("noncanonical DER length")
    stop = offset + size
    if stop > end:
        raise ValueError("truncated DER value")
    return tag, offset, stop


def kernel_payload(data):
    if len(data) > LIMIT:
        raise ValueError("carrier exceeds bounded input size")
    tag, start, end = tlv(data, 0, len(data))
    if tag != 0x30 or end != len(data):
        raise ValueError("expected one DER sequence")
    tag, a, b = tlv(data, start, end)
    if tag != 0x16 or data[a:b] != b"IMG4":
        raise ValueError("expected IMG4 carrier")
    tag, a, b = tlv(data, b, end)
    if tag != 0x30:
        raise ValueError("expected IM4P sequence")
    sequence_end = b
    for expected in (b"IM4P", b"krnl"):
        tag, a, b = tlv(data, a, sequence_end)
        if tag != 0x16 or data[a:b] != expected:
            raise ValueError("unexpected payload type")
        a = b
    tag, a, b = tlv(data, a, sequence_end)
    if tag != 0x16:
        raise ValueError("expected payload description")
    tag, a, b = tlv(data, b, sequence_end)
    if tag != 0x04 or data[a:a + 4] != b"bvx2":
        raise ValueError("expected unencrypted LZFSE v2 krnl payload")
    return data[a:b], a


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output_directory", type=Path)
    args = p.parse_args()
    paths = glob.glob(LOCATOR)
    if len(paths) != 1:
        p.error("expected exactly one readable carrier; do not guess a boot identity")
    # No path is printed, including in OS exception text.
    try:
        with open(paths[0], "rb") as f:
            carrier = f.read(LIMIT + 1)
        payload, offset = kernel_payload(carrier)
    except (OSError, ValueError) as e:
        p.error(f"payload unavailable ({type(e).__name__})")
    out = args.output_directory
    out.mkdir(parents=True, exist_ok=True)
    with (out / "kernelcache.lzfse").open("xb") as f:
        f.write(payload)
    manifest = {
        "source": "readable Preboot IMG4 krnl payload; unique locator omitted",
        "running_boot_identity_verified": False,
        "payload_offset": offset,
        "payload_bytes": len(payload),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "personalization_copied": False,
        "operation": "read and copy unencrypted compressed payload only",
    }
    (out / "payload-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
