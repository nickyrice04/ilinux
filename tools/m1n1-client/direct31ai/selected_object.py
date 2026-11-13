#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Classify the guarded selected lab file's framing; never decode its payload.

Default: help. --fixture reads workspace data only. --live uses the immutable
31AG root/Mac/distinct-lab/selected-path guards. Output has fixed enums/sizes,
never file bytes, unknown-file hashes, identities, policy text or paths.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import types

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
HELPER = ROOT / "tools/boot-object31ag/read_selected.py"
HELPER_SHA256 = "0728fae7dd30fd2ef14dacdf9e25028614f239c254c8fc40c3f8866fde32dc47"
MAX_FILE = 8 * 1024 * 1024  # Preserve the frozen live-read cap.
MAX_DECLARED = 160 * 1024 * 1024
MAX_OPAQUE_EXTRA = 64 * 1024
SCHEMA = "ilinux-direct31ai-selected-framing-v1"
FAILURE_STAGES = {"OUTER_EXTENT", "FROZEN_DER_TREE", "ROOT_STRUCTURE", "ROOT_MAGIC",
                  "IMG4_FIELDS", "IM4P_MAGIC", "IM4P_FIELDS", "PAYLOAD_METADATA",
                  "PAYLOAD_FIELD", "IM4P_EXTRA_METADATA", "COMPRESSION_METADATA"}


class Refusal(ValueError):
    pass


def require(value):
    if not value:
        raise Refusal()


def load_helper():
    # Execute only this project's exact frozen original helper, from checked bytes.
    require(not HELPER.is_symlink() and HELPER.is_file())
    with HELPER.open("rb") as stream:
        before = os.fstat(stream.fileno())
        data = stream.read(64 * 1024 + 1)
        after = os.fstat(stream.fileno())
    stamp = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    require(len(data) <= 64 * 1024 and len(data) == before.st_size and stamp(before) == stamp(after))
    require(hashlib.sha256(data).hexdigest() == HELPER_SHA256)
    module = types.ModuleType("selected31ag_frozen")
    module.__file__ = str(HELPER)
    exec(compile(data, str(HELPER), "exec"), module.__dict__)
    return module


def empty_report(match="UNKNOWN"):
    return {"schema": SCHEMA, "read_only": True, "match": match,
            "framing": "NONE", "file_bytes": 0, "object_bytes": 0,
            "outer_trailer": "NOT_DETERMINED", "payload_bytes": 0,
            "payload_type": "NOT_APPLICABLE", "compression": "UNRECOGNIZED",
            "payload_relation": "NOT_KNOWN", "context_fields": [],
            "im4p_extra": "NONE", "declared_uncompressed_bytes": None,
            "opaque_extra_semantics_verified": False,
            "der_diagnostic": None,
            "decompressed": False, "decrypted": False,
            "configured_file_only": True, "default_selection_verified": False,
            "restoration_verified": False, "bootability_verified": False}


def compression_magic(payload, relation):
    for magic, label in ((b"bvx2", "LZFSE_BVX2"), (b"bvx1", "LZFSE_BVX1"),
                         (b"bvx-", "LZFSE_UNCOMPRESSED_BVX_MINUS"),
                         (b"bvxn", "LZVN_BVXN"), (b"bvx$", "LZFSE_END_MARKER"),
                         (b"complzss", "APPLE_LZSS_COMPLZSS"),
                         (b"\x1f\x8b\x08", "GZIP")):
        if payload.startswith(magic):
            return label
    if relation.startswith("EXACT_") or payload.startswith(b"\xcf\xfa\xed\xfe"):
        return "NONE_RECOGNIZED_BINARY"
    return "UNRECOGNIZED"


def relation_to_known(payload, references):
    for label in ("BOOT021", "31AF"):
        expected = references[label]
        if payload == expected:
            return "EXACT_" + label
        if payload.startswith(expected):
            return label + ("_ZERO_PADDED" if not any(payload[len(expected):])
                            else "_PREFIX_WITH_NONZERO_TRAILER")
    return "NOT_KNOWN"


def outer_extent(data):
    require(len(data) >= 2 and data[0] == 0x30)
    length = data[1];start = 2
    if length & 0x80:
        count = length & 0x7f
        require(1 <= count <= 4 and start + count <= len(data) and data[start] != 0)
        length = int.from_bytes(data[start:start+count], "big")
        require(length >= 128)
        start += count
    require(start + length <= len(data))
    return start + length


def integer(data, node):
    require(node[0] == 0x02 and not node[3])
    raw = data[node[1]:node[2]]
    require(1 <= len(raw) <= 9 and not raw[0] & 0x80)
    require(len(raw) == 1 or raw[0] != 0 or raw[1] & 0x80)
    return int.from_bytes(raw, "big")


def shallow_header(data, position, end):
    """Bounded TLV header metadata only; high-tag numbers are never printed."""
    if not (0 <= position < end <= len(data)):
        return None, None, None
    first = data[position];cursor = position + 1
    number = first & 31
    canonical_tag = True
    if number == 31:
        number = "HIGH";count = 0;numeric = 0
        while True:
            if cursor >= end or count >= 6:
                return None, None, None
            word = data[cursor];cursor += 1;count += 1
            if count == 1 and word == 0x80:
                canonical_tag = False
            numeric = (numeric << 7) | (word & 0x7f)
            if not word & 0x80:
                break
        canonical_tag = canonical_tag and numeric >= 31
    if cursor >= end:
        return None, None, None
    length_byte = data[cursor];cursor += 1
    info = {"tag_class": ("UNIVERSAL", "APPLICATION", "CONTEXT", "PRIVATE")[first >> 6],
            "constructed": bool(first & 32), "tag_number": number,
            "tag_canonical": canonical_tag, "length_form": "SHORT",
            "length_octets": 1, "content_bytes": None,
            "length_canonical": False, "fits_parent": False}
    if length_byte == 0x80:
        info.update(length_form="INDEFINITE", header_bytes=cursor-position)
        return info, None, None
    if length_byte & 0x80:
        count = length_byte & 0x7f
        info.update(length_form="LONG", length_octets=count+1)
        if not 1 <= count <= 4 or cursor + count > end:
            info["header_bytes"] = cursor-position
            return info, None, None
        length = int.from_bytes(data[cursor:cursor+count], "big")
        canonical = data[cursor] != 0 and length >= 128
        cursor += count
    else:
        length = length_byte;canonical = True
    stop = cursor + length
    info.update(header_bytes=cursor-position, content_bytes=length,
                length_canonical=canonical, fits_parent=stop <= end)
    return info, cursor, stop


def shallow_fields(data, start, end):
    """At most eight direct headers; never descend into a manifest or payload."""
    result = [];position = start
    while position < end and len(result) < 8:
        info, content, stop = shallow_header(data, position, end)
        if info is None:
            return result, False
        result.append((info, content, stop))
        if not (info["tag_canonical"] and info["length_canonical"] and info["fits_parent"]):
            return result, False
        position = stop
    return result, position == end


def shallow_outline(data, failure_stage):
    """Only fixed labels, tags and sizes; no arbitrary field value is returned."""
    require(type(failure_stage) is str and failure_stage in FAILURE_STAGES)
    result = {"failure_stage": failure_stage, "root_header": None,
              "top_fields": [], "top_fields_complete": False,
              "root_magic_is_img4": False, "root_magic_is_im4p": False,
              "im4p_magic_matches": False, "im4p_fields": [],
              "im4p_fields_complete": False, "child_limit": 8,
              "framed_extent_bytes": None, "outer_trailer": "NOT_DETERMINED",
              "manifest_or_payload_descended": False}
    info, start, stop = shallow_header(data, 0, len(data))
    result["root_header"] = info
    if info is None or not (info["tag_class"] == "UNIVERSAL" and
            info["tag_number"] == 16 and info["constructed"] and info["tag_canonical"] and
            info["length_canonical"] and info["fits_parent"]):
        return result
    tail = data[stop:]
    result["framed_extent_bytes"] = stop
    result["outer_trailer"] = ("NONE" if not tail else "ZERO_PADDING"
                               if not any(tail) else "NONZERO_TRAILER")
    fields, complete = shallow_fields(data, start, stop)
    result["top_fields"] = [entry[0] for entry in fields]
    result["top_fields_complete"] = complete
    def magic(entry, expected):
        header, content, end = entry
        return (header["tag_class"] == "UNIVERSAL" and header["tag_number"] == 22 and
                not header["constructed"] and header["tag_canonical"] and
                header["length_canonical"] and header["fits_parent"] and
                header["content_bytes"] == 4 and data[content:end] == expected)
    if not fields:
        return result
    result["root_magic_is_img4"] = magic(fields[0], b"IMG4")
    result["root_magic_is_im4p"] = magic(fields[0], b"IM4P")
    im4p = []
    if result["root_magic_is_im4p"]:
        im4p = fields;im4p_complete = complete
    elif result["root_magic_is_img4"] and len(fields) >= 2:
        header, content, end = fields[1]
        if (header["tag_class"] == "UNIVERSAL" and header["tag_number"] == 16 and
                header["constructed"] and header["tag_canonical"] and
                header["length_canonical"] and header["fits_parent"]):
            first, first_content, first_end = shallow_header(data, content, end)
            if first is not None and magic((first, first_content, first_end), b"IM4P"):
                im4p, im4p_complete = shallow_fields(data, content, end)
    if im4p:
        result["im4p_magic_matches"] = magic(im4p[0], b"IM4P")
        result["im4p_fields"] = [entry[0] for entry in im4p]
        result["im4p_fields_complete"] = im4p_complete
    return result


def framed_payload(data, base, trace=None):
    def stage(name):
        if trace is not None:
            trace["stage"] = name
    stage("OUTER_EXTENT")
    extent = outer_extent(data)
    stage("FROZEN_DER_TREE")
    root = base.der_tree(data[:extent])
    stage("ROOT_STRUCTURE")
    require(root[0] == 0x30 and root[3])
    def text(node):
        require(node[0] == 0x16 and not node[3])
        raw = data[node[1]:node[2]]
        require(all(c < 128 for c in raw))
        return raw
    stage("ROOT_MAGIC")
    children = root[3];magic = text(children[0]);contexts = []
    if magic == b"IMG4":
        stage("IMG4_FIELDS")
        require(len(children) >= 2 and children[1][0] == 0x30)
        tags = [node[0] for node in children[2:]]
        require(all(tag in (0xa0, 0xa1) for tag in tags) and len(set(tags)) == len(tags))
        contexts = ["MANIFEST_A0" if tag == 0xa0 else "RESTORE_A1" for tag in tags]
        children = children[1][3]
        stage("IM4P_MAGIC")
        require(children and text(children[0]) == b"IM4P")
        framing = "IMG4"
    else:
        require(magic == b"IM4P")
        framing = "IM4P"
    stage("IM4P_FIELDS")
    require(4 <= len(children) <= 7)
    stage("PAYLOAD_METADATA")
    kind = text(children[1]);description = text(children[2])
    require(len(kind) == 4 and all(32 <= c < 127 for c in kind) and len(description) <= 4096)
    stage("PAYLOAD_FIELD")
    payload = children[3]
    require(payload[0] == 0x04 and not payload[3])
    # A keybag is opaque. We neither parse keys nor attempt a decode/decrypt.
    stage("IM4P_EXTRA_METADATA")
    extras = children[4:];keybag = False;declared = None;extra = "NONE"
    # A final context-0 field is reported only as opaque framing. Its contents
    # and security effects are not interpreted, and its presence forbids match.
    opaque_a0 = bool(extras and extras[-1][0] == 0xa0)
    if opaque_a0:
        require(not extras[-1][3] and 0 <= extras[-1][2]-extras[-1][1] <= MAX_OPAQUE_EXTRA)
        extras = extras[:-1]
    if extras and extras[0][0] == 0x04:
        require(not extras[0][3]);keybag = True;extra = "OPAQUE_KEYBAG_PRESENT"
        extras = extras[1:]
    if extras:
        stage("COMPRESSION_METADATA")
        require(len(extras) == 1 and extras[0][0] == 0x30)
        numbers = extras[0][3]
        require(len(numbers) == 2 and integer(data, numbers[0]) == 1)
        declared = integer(data, numbers[1])
        require(0 < declared <= MAX_DECLARED)
        extra = ("OPAQUE_KEYBAG_AND_LZFSE_SIZE" if keybag else "LZFSE_SIZE_DECLARED")
    if opaque_a0:
        extra = "OPAQUE_CONTEXT_A0"
        if keybag and declared is not None:
            extra += "_WITH_KEYBAG_AND_LZFSE_SIZE"
        elif keybag:
            extra += "_WITH_KEYBAG"
        elif declared is not None:
            extra += "_WITH_LZFSE_SIZE"
    payload_bytes = data[payload[1]:payload[2]]
    tail = data[extent:]
    return {"framing": framing, "object_bytes": extent,
            "outer_trailer": "NONE" if not tail else "ZERO_PADDING" if not any(tail) else "NONZERO_TRAILER",
            "payload_type": kind.decode("ascii") if kind in (b"krnl", b"rkrn", b"ibot") else "OTHER",
            "context_fields": contexts, "im4p_extra": extra,
            "declared_uncompressed_bytes": declared}, payload_bytes, keybag


def classify(data, references, base):
    require(type(data) is bytes and 0 < len(data) <= MAX_FILE)
    require(set(references) == {"31AF", "BOOT021"} and
            all(type(v) is bytes and 0 < len(v) <= MAX_FILE for v in references.values()))
    result = empty_report();result["file_bytes"] = len(data)
    payload = data;keybag = False
    if data[:1] == b"\x30" and not any(data == v for v in references.values()):
        trace = {"stage": "OUTER_EXTENT"}
        try:
            detail, payload, keybag = framed_payload(data, base, trace)
        except (Refusal, base.Refused, ValueError, IndexError, TypeError):
            result["framing"] = "MALFORMED_OR_UNSUPPORTED_DER"
            result["der_diagnostic"] = shallow_outline(data, trace["stage"])
            return result
        result.update(detail)
    else:
        result.update(framing="RAW", object_bytes=len(data), outer_trailer="NONE")
    relation = relation_to_known(payload, references)
    result.update(payload_bytes=len(payload), payload_relation=relation,
                  compression=compression_magic(payload, relation))
    # Only exact known bytes under fully understood, unpadded framing match.
    if (relation.startswith("EXACT_") and not keybag and result["outer_trailer"] == "NONE"
            and result["im4p_extra"] == "NONE"):
        result["match"] = relation[len("EXACT_"):]
    return result


def live(base, references):
    # The same exact frozen target/selection guards, not a new selector or mount.
    base.require(sys.platform == "darwin" and os.geteuid() == 0)
    base.require(base.capture(["/usr/sbin/sysctl", "-n", "hw.model"], 64).strip() == b"Mac17,6")
    fd = base.secure_open(base.LAB_MOUNT, directory=True);os.close(fd)
    lab, current = base.disk_info(base.LAB_MOUNT), base.disk_info("/")
    apfs = base.plistlib.loads(base.capture(["/usr/sbin/diskutil", "apfs", "list", "-plist"]))
    target = base.guard_target(lab, current, apfs)
    mount = base.guard_preboot(target, base.disk_info(target["preboot"]["DeviceIdentifier"]))
    fd = base.secure_open(mount, directory=True);os.close(fd)
    selected = base.parse_policy(base.capture(["/usr/bin/bputil", "-d", "-v", target["group"]], base.MAX_POLICY))
    if selected["coih"] is None:
        return empty_report("NO_CUSTOM_OBJECT")
    path = base.selected_path(target, mount, selected)
    return classify(base.secure_read(path, MAX_FILE), references, base)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true", help="Root on M5 only, same guarded selected file")
    mode.add_argument("--fixture", type=Path, help="Workspace binary fixture only; no Apple calls")
    args = parser.parse_args(argv)
    if not args.live and args.fixture is None:
        parser.print_help();return 0
    try:
        base = load_helper()
        references = base.load_references(base.DEFAULT_REFERENCES)
        if args.live:
            result = live(base, references)
        else:
            path = args.fixture.absolute()
            require(ROOT in path.parents)
            result = classify(base.secure_read(path, MAX_FILE), references, base)
    except BaseException:
        result = empty_report("REFUSED")
        print(json.dumps(result, sort_keys=True));return 2
    print(json.dumps(result, sort_keys=True));return 0


if __name__ == "__main__":
    raise SystemExit(main())
