#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Read-only two-file 31AI candidate intake; no extraction, execution or devices."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys
import zlib

SCHEMA = "ilinux-direct31ai-inline-candidate-v1"
TARGET = {"model": "Mac17,6", "board": "j716c", "chip_id": "0x6050"}
COMMIT = "bd9f3e8273dc79ae9095c19c2c4f32218446ad4e"
BASELINE = "2d272aa2b5551d27458826e88b3bdaf86684e2b4fff3aad4876de7021a1caaf3"
BASELINE_BYTES = 3997696
RAW_BYTES = 19639230
RAW_SHA256 = "5f351f1f4841f0d5fcee2d16a5eed71ed6be46c95b16ba92e0295440a725f8cc"
FROZEN_PAD = "0f3b95bc1075c35916963c30c37c4eee6642c2cae95f264ac4744154c84b6acf"
FILENAME = "aura-inline-128m.macho.gz"
MAX_COMPRESSED = 32 * 1024 * 1024
MAX_EXPANDED = 160 * 1024 * 1024
MAX_JSON = 128 * 1024
SOURCE_FILES = {
    "kernel/experiments/direct31ah/aura/pad_boot.py",
    "kernel/experiments/direct31ah/linux/fdt_read.py",
    "kernel/experiments/direct31ah/linux/check_dtb.py",
    "kernel/experiments/direct31ah/linux/check_config.py",
    "kernel/experiments/direct31ai/transport/inline.py",
    "kernel/experiments/direct31ai/transport/extend_exec.py",
    "kernel/experiments/direct31ai/diagnostic/package.py",
    "kernel/experiments/direct31ai/diagnostic/policy.py",
}


class Refusal(ValueError):
    pass


def require(value, reason):
    if not value:
        raise Refusal(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def is_sha(value):
    return type(value) is str and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def keys(value, expected, reason):
    require(type(value) is dict and set(value) == set(expected), reason)


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "duplicate_json_key")
        result[key] = value
    return result


def decode(data):
    require(len(data) <= MAX_JSON, "json_bound")
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=pairs)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise Refusal("invalid_json") from None


def read_regular(path, bound):
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= bound,
                "bounded_regular_file_required")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            data = stream.read(bound + 1)
        after = os.fstat(descriptor)
        stamp = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        require(len(data) == before.st_size and stamp(before) == stamp(after), "file_changed")
        return data
    finally:
        os.close(descriptor)


def validate_manifest(m):
    keys(m, {"schema", "target", "delivery", "native_authorized", "restart_ready",
             "firmware_change_authorized", "public_binary_release",
             "glibc_public_source_closure", "upstream_aura_commit",
             "baseline_aura_raw_sha256", "diagnostic_manifest_sha256",
             "source_sha256", "candidate"}, "manifest_fields")
    require(m["schema"] == SCHEMA and m["target"] == TARGET, "manifest_identity")
    require(m["delivery"] == "SAME_USER_LOCAL_HANDOFF_ONLY" and
            m["glibc_public_source_closure"] == "INCOMPLETE", "delivery_scope")
    for name in ("native_authorized", "restart_ready", "firmware_change_authorized",
                 "public_binary_release"):
        require(m[name] is False, "not_offline_local_handoff")
    require(m["upstream_aura_commit"] == COMMIT and
            m["baseline_aura_raw_sha256"] == BASELINE, "baseline_identity")
    require(is_sha(m["diagnostic_manifest_sha256"]), "diagnostic_manifest_digest")
    keys(m["source_sha256"], SOURCE_FILES, "source_inventory")
    require(all(is_sha(v) for v in m["source_sha256"].values()), "source_digest")
    require(m["source_sha256"]["kernel/experiments/direct31ah/aura/pad_boot.py"] ==
            FROZEN_PAD, "frozen_reader_changed")
    c = m["candidate"]
    keys(c, {"filename", "compressed_bytes", "compressed_sha256", "expanded_bytes",
             "expanded_sha256", "raw_inline_bytes", "raw_inline_sha256"}, "candidate_fields")
    require(c["filename"] == FILENAME, "candidate_filename")
    for key, bound in (("compressed_bytes", MAX_COMPRESSED), ("expanded_bytes", MAX_EXPANDED)):
        require(type(c[key]) is int and 0 < c[key] <= bound, "candidate_bounds")
    require(is_sha(c["compressed_sha256"]) and is_sha(c["expanded_sha256"]), "candidate_digest")
    require(type(c["raw_inline_bytes"]) is int and c["raw_inline_bytes"] == RAW_BYTES and
            c["raw_inline_sha256"] == RAW_SHA256, "inline_input_identity")
    return c


def read_candidate(path, c):
    compressed = read_regular(path, MAX_COMPRESSED)
    require(len(compressed) == c["compressed_bytes"] and
            sha(compressed) == c["compressed_sha256"], "compressed_identity")
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        data = decoder.decompress(compressed, MAX_EXPANDED + 1)
    except zlib.error:
        raise Refusal("candidate_gzip_crc") from None
    require(len(data) <= MAX_EXPANDED and decoder.eof and not decoder.unused_data and
            not decoder.unconsumed_tail, "candidate_gzip_bounds")
    require(len(data) == c["expanded_bytes"] and sha(data) == c["expanded_sha256"],
            "expanded_identity")
    return data


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def dependencies(repo, source_bindings):
    # These are the project's own pinned Python helpers, never downloaded code.
    for name, expected in source_bindings.items():
        require(sha(read_regular(repo / name, 4 * 1024 * 1024)) == expected,
                "checkout_helper_changed")
    diagnostic = load_module("candidate31ai_diagnostic",
                             repo / "kernel/experiments/direct31ai/diagnostic/package.py")
    extended = load_module("candidate31ai_extended",
                           repo / "kernel/experiments/direct31ai/transport/extend_exec.py")
    return diagnostic, extended


def inspect_candidate(data, c, files, diagnostic, extended):
    pad, inline = extended.pad, extended.inline
    before = pad.inspect(data)
    code = before["code"]
    require(code["off"] == 0x10000 and code["size"] == pad.CODE_SIZE,
            "candidate_execute_geometry")
    require(c["raw_inline_bytes"] <= code["size"], "raw_exceeds_code_segment")
    raw = data[code["off"]:code["off"] + c["raw_inline_bytes"]]
    require(len(raw) == c["raw_inline_bytes"] and sha(raw) == c["raw_inline_sha256"],
            "raw_inline_identity")
    require(raw[0x808:0x810] == b"AURALOAD" and len(raw) >= BASELINE_BYTES and
            struct.unpack_from("<Q", raw, 0x818)[0] == BASELINE_BYTES and
            sha(raw[:BASELINE_BYTES]) == BASELINE, "baseline_prefix_identity")
    require(not any(data[code["off"] + len(raw):code["off"] + code["size"]]),
            "nonzero_execute_padding")
    extended.wrapper_identity(data, raw, before)
    root = diagnostic.p.ROOT
    payload = inline.verify_payload(raw[BASELINE_BYTES:], files[root + "linux/Image"],
                                    files[root + "linux/t6050-j716c-diagnostic.dtb"],
                                    files[root + "diagnostic/initramfs.cpio.gz"])
    return {"segment_count": len(before["segments"]), "expected_kcbz": 0,
            "expected_kcrz": code["off"] + code["size"],
            "entry_offset": before["entry"] - before["base"],
            "baseline_prefix_verified": True, "canonical_metadata_verified": True,
            "zero_execute_padding_verified": True, "exact_diagnostic_payload_verified": True,
            "payload_bytes": payload["payload_bytes"],
            "payload_sha256": payload["payload_sha256"]}


def review(manifest, candidate_path, diagnostic_manifest_path, diagnostic_path, repo):
    c = validate_manifest(manifest)
    diagnostic_bytes = read_regular(diagnostic_manifest_path, MAX_JSON)
    require(sha(diagnostic_bytes) == manifest["diagnostic_manifest_sha256"],
            "diagnostic_manifest_identity")
    diagnostic, extended = dependencies(Path(repo), manifest["source_sha256"])
    dm = decode(diagnostic_bytes)
    diagnostic_result = diagnostic.review(dm, diagnostic_path, repo)
    files, _ = diagnostic.read_archive(diagnostic_path, diagnostic.validate_manifest(dm))
    candidate = read_candidate(candidate_path, c)
    detail = inspect_candidate(candidate, c, files, diagnostic, extended)
    return {"schema": "ilinux-direct31ai-candidate-review-v1",
            "status": "OFFLINE_CANDIDATE_INTEGRITY_PASS", "read_only": True,
            "extracted": False, "executed": False, "device_opened": False,
            "camera_opened": False, "native_authorized": False, "native_ready": False,
            "public_binary_release": False, "glibc_public_source_closure": "INCOMPLETE",
            "kmutil_inspection_performed": False, "native_execution_proven": False,
            "candidate_gzip_sha256": c["compressed_sha256"],
            "candidate_sha256": c["expanded_sha256"],
            "raw_inline_sha256": c["raw_inline_sha256"],
            "diagnostic_manifest_sha256": manifest["diagnostic_manifest_sha256"],
            "diagnostic_package_sha256": diagnostic_result["package_sha256"], **detail}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    for name in ("manifest", "candidate", "diagnostic-manifest", "diagnostic-package"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    m = decode(read_regular(args.manifest, MAX_JSON))
    print(json.dumps(review(m, args.candidate, args.diagnostic_manifest,
                            args.diagnostic_package, args.repo), indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, RecursionError, EOFError,
            UnicodeError, struct.error):
        # Helper exceptions can contain paths. Never echo them or input values.
        print(json.dumps({"status": "REFUSED", "read_only": True, "extracted": False,
                          "executed": False, "native_ready": False,
                          "native_authorized": False, "public_binary_release": False}))
        raise SystemExit(2)
