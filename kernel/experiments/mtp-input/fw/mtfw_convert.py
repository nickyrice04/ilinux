#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only OR MIT
"""Turn this Mac's own multi-touch firmware image into the file our Linux driver loads.

usage:
  python3 -I mtfw_convert.py INPUT.im4p OUTPUT.bin [--raw] [--force] [--allow-untracked-path]
  python3 -I mtfw_convert.py INPUT.im4p --info

INPUT is the IM4P macOS keeps next to its restore bundle (<BOARD>_Multitouch.im4p;
see README for where it lives). OUTPUT is the "HIDF" container
dockchannel-hid.c's dchid_get_firmware() expects (magic, version, header length,
data length, interface-offset) around the exact byte string macOS hands the MTP
bootloader. --raw writes that byte string without the container.

Original implementation from our own analysis of the macOS 26.6.2 drivers (see
README, evidence labels there). Nothing proprietary is embedded here and the
output must never be committed: the script refuses to write inside a git work
tree unless the path is git-ignored.

What macOS does and this reproduces (AppleInputDeviceSupport AIDImageDownloader,
AppleHIDTransportBootloaderCBOR::encodeObject):
  1. IM4P (DER) -> payload OCTET STRING
  2. payload = XML-serialised OSObject graph (NUL terminated), IDs/IDREFs
  3. object graph -> CBOR: OSNumber -> unsigned int (low 32 bits), OSBoolean ->
     0xf4/0xf5, OSString -> text string of strlen+1 bytes (NUL included), OSData ->
     byte string preceded by 0xd3 filler tags so the bytes start 4-aligned,
     OSArray -> array, OSDictionary -> map, in document order.
"""
import argparse
import base64
import hashlib
import re
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HIDF_MAGIC = 0x46444948         # "HIDF" little endian, as dockchannel-hid.c FW_MAGIC
HIDF_VERSION = 1
HIDF_HEADER = 20
MAX_PAYLOAD = 16 * 1024 * 1024  # sanity bound, real images are ~100 KiB
MAX_DEPTH = 64


class ConvertError(Exception):
    pass


# --------------------------------------------------------------------- IM4P (DER)

def der_read(buf, off):
    """Return (tag, content_offset, content_length); definite lengths only."""
    if off + 2 > len(buf):
        raise ConvertError("truncated DER header")
    tag = buf[off]
    first = buf[off + 1]
    off += 2
    if first & 0x80:
        n = first & 0x7f
        if n == 0 or n > 4 or off + n > len(buf):
            raise ConvertError("unsupported DER length")
        length = int.from_bytes(buf[off:off + n], "big")
        off += n
    else:
        length = first
    if off + length > len(buf):
        raise ConvertError("DER element exceeds its container")
    return tag, off, length


def parse_im4p(blob):
    """Return (type4cc, version, payload) of an IM4P with an uncompressed payload."""
    tag, off, length = der_read(blob, 0)
    if tag != 0x30:
        raise ConvertError("not a DER SEQUENCE")
    if off + length != len(blob):
        raise ConvertError("trailing bytes after the IM4P SEQUENCE")
    items = []
    end = off + length
    while off < end:
        t, so, sl = der_read(blob, off)
        if so + sl > end:
            raise ConvertError("element overruns the sequence")
        items.append((t, bytes(blob[so:so + sl])))
        off = so + sl
    if len(items) < 4 or items[0][0] != 0x16 or items[0][1] != b"IM4P":
        raise ConvertError("missing IM4P magic")
    if items[1][0] != 0x16 or len(items[1][1]) != 4:
        raise ConvertError("bad image type")
    if items[3][0] != 0x04:
        raise ConvertError("payload is not an OCTET STRING")
    if len(items) > 4:
        # KBAG (encryption) or compression descriptors: not seen on the multi-touch image
        raise ConvertError("IM4P has extra elements (encrypted or compressed?); unsupported")
    return items[1][1].decode("ascii"), items[2][1].decode("ascii", "replace"), items[3][1]


# --------------------------------------------------- XML object graph (OSSerialize)

class Obj:
    """Decoded object: kind in {'int','bool','str','data','arr','dict'}."""
    __slots__ = ("kind", "value")

    def __init__(self, kind, value):
        self.kind = kind
        self.value = value


def parse_integer(text):
    """strtoull(text, NULL, 0) with an optional leading '-' (two's complement)."""
    t = text.strip()
    if not t:
        raise ConvertError("empty <integer>")
    neg = t.startswith("-")
    if neg:
        t = t[1:]
    if re.fullmatch(r"0[xX][0-9a-fA-F]+", t):
        v = int(t, 16)
    elif re.fullmatch(r"0[0-7]*", t):
        v = int(t, 8) if len(t) > 1 else 0
    elif re.fullmatch(r"[1-9][0-9]*", t):
        v = int(t, 10)
    else:
        raise ConvertError("bad <integer> %r" % text[:24])
    if v >= 1 << 64:
        raise ConvertError("<integer> exceeds 64 bits")
    return (-v) & ((1 << 64) - 1) if neg else v


def build(elem, ids, depth, stats, open_ids):
    if depth > MAX_DEPTH:
        raise ConvertError("nesting too deep")
    ref = elem.attrib.get("IDREF")
    if ref is not None:
        if elem.attrib.get("ID") is not None or len(elem) or (elem.text or "").strip():
            raise ConvertError("IDREF element is not empty")
        if ref in open_ids:
            raise ConvertError("IDREF %r refers to an object under construction" % ref)
        if ref not in ids:
            raise ConvertError("unknown IDREF %r" % ref)
        stats["refs"] += 1
        return ids[ref]

    tag = elem.tag
    ident = elem.attrib.get("ID")
    if ident is not None:
        if ident in ids or ident in open_ids:
            raise ConvertError("duplicate ID %r" % ident)
        open_ids.add(ident)
    stats["elements"] += 1

    if tag == "dict":
        pairs = []
        index = {}
        children = list(elem)
        if len(children) % 2:
            raise ConvertError("<dict> with an odd number of children")
        for i in range(0, len(children), 2):
            k, v = children[i], children[i + 1]
            if k.tag != "key":
                raise ConvertError("<dict> child is not a <key>")
            if len(k):
                raise ConvertError("<key> has children")
            key = k.text or ""
            if k.attrib.get("IDREF") is not None or k.attrib.get("ID") is not None:
                raise ConvertError("ID attributes on <key> are not supported")
            val = build(v, ids, depth + 1, stats, open_ids)
            if key in index:
                pairs[index[key]] = (key, val)   # OSDictionary::setObject keeps the position
                stats["dup_keys"] += 1
            else:
                index[key] = len(pairs)
                pairs.append((key, val))
        obj = Obj("dict", pairs)
    elif tag == "array":
        obj = Obj("arr", [build(c, ids, depth + 1, stats, open_ids) for c in elem])
    elif tag == "string":
        if len(elem):
            raise ConvertError("<string> has children")
        obj = Obj("str", (elem.text or "").encode("utf-8"))
    elif tag == "integer":
        if len(elem):
            raise ConvertError("<integer> has children")
        bits = elem.attrib.get("size")
        size = int(bits, 0) if bits is not None else 32
        if not 1 <= size <= 64:
            raise ConvertError("bad <integer size>")
        v = parse_integer(elem.text or "") & ((1 << size) - 1)
        if v >> 32:
            stats["truncated"] += 1
        obj = Obj("int", v)
    elif tag == "data":
        if len(elem):
            raise ConvertError("<data> has children")
        text = "".join((elem.text or "").split())
        try:
            raw = base64.b64decode(text, validate=True)
        except Exception as exc:
            raise ConvertError("bad base64 in <data>: %s" % exc)
        obj = Obj("data", raw)
    elif tag in ("true", "false"):
        if len(elem) or (elem.text or "").strip():
            raise ConvertError("<%s> is not empty" % tag)
        obj = Obj("bool", tag == "true")
    else:
        raise ConvertError("unsupported element <%s>" % tag)

    if ident is not None:
        open_ids.discard(ident)
        ids[ident] = obj
    return obj


def parse_payload(payload):
    stripped = payload.rstrip(b"\0")
    if len(payload) - len(stripped) != 1:
        raise ConvertError("payload must end in exactly one NUL")
    try:
        text = stripped.decode("utf-8")
    except UnicodeDecodeError:
        raise ConvertError("payload is not UTF-8")
    if "<!DOCTYPE" in text or "<!ENTITY" in text or "<?" in text:
        raise ConvertError("DTD / processing instruction in payload")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ConvertError("payload is not well-formed XML: %s" % exc)
    stats = {"elements": 0, "refs": 0, "dup_keys": 0, "truncated": 0}
    obj = build(root, {}, 0, stats, set())
    if obj.kind != "dict":
        raise ConvertError("top-level object is not a dictionary")
    return obj, stats


# ------------------------------------------------------------------------ CBOR

def varuint_head(major, value):
    if value < 0 or value >> 32:
        raise ConvertError("length/value does not fit 32 bits")
    if value <= 0x17:
        return bytes([major | value])
    if value <= 0xff:
        return bytes([major | 0x18, value])
    if value <= 0xffff:
        return bytes([major | 0x19]) + value.to_bytes(2, "big")
    return bytes([major | 0x1a]) + value.to_bytes(4, "big")


def encode(obj):
    out = bytearray()

    def rec(o, depth):
        if depth > MAX_DEPTH:
            raise ConvertError("nesting too deep")
        k = o.kind
        if k == "int":
            out.extend(varuint_head(0x00, o.value & 0xffffffff))
        elif k == "bool":
            out.append(0xf5 if o.value else 0xf4)
        elif k == "str":
            out.extend(varuint_head(0x60, len(o.value) + 1))
            out.extend(o.value)
            out.append(0)
        elif k == "data":
            head = varuint_head(0x40, len(o.value))
            # filler tags so the byte string content starts on a 4-byte boundary
            pad = (-len(out) - len(head)) & 3
            out.extend(b"\xd3" * pad)
            out.extend(head)
            out.extend(o.value)
        elif k == "arr":
            out.extend(varuint_head(0x80, len(o.value)))
            for e in o.value:
                rec(e, depth + 1)
        elif k == "dict":
            out.extend(varuint_head(0xa0, len(o.value)))
            for key, val in o.value:
                rec(Obj("str", key.encode("utf-8")), depth + 1)
                rec(val, depth + 1)
        else:
            raise ConvertError("internal: unknown kind " + k)

    rec(obj, 0)
    return bytes(out)


def hidf(data, iface_offset=0):
    if iface_offset and iface_offset >= len(data):
        raise ConvertError("iface_offset outside the data")
    return struct.pack("<5I", HIDF_MAGIC, HIDF_VERSION, HIDF_HEADER, len(data), iface_offset) + data


# --------------------------------------------------------------------- driver

def convert(blob):
    """IM4P bytes -> (cbor bytes, info dict)."""
    typ, ver, payload = parse_im4p(blob)
    if len(payload) > MAX_PAYLOAD:
        raise ConvertError("payload too large")
    obj, stats = parse_payload(payload)
    cbor = encode(obj)
    top = obj.value
    info = {
        "im4p_type": typ, "im4p_version": ver, "payload_bytes": len(payload),
        "top_level_keys": [k for k, _ in top],
        "cbor_bytes": len(cbor), "cbor_sha256": hashlib.sha256(cbor).hexdigest(),
    }
    info.update(stats)
    return cbor, info


def refuse_tracked_path(path):
    """Never write a blob into something git would commit."""
    parent = path.resolve().parent
    r = subprocess.run(["git", "-C", str(parent), "check-ignore", "-q", str(path.resolve())],
                       capture_output=True)
    if r.returncode == 1:
        raise ConvertError("%s is inside a git work tree and not ignored; pick an ignored path "
                           "(e.g. build/) or pass --allow-untracked-path" % path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path, nargs="?")
    ap.add_argument("--info", action="store_true", help="print structure facts only, write nothing")
    ap.add_argument("--raw", action="store_true", help="write the bare CBOR, not the HIDF container")
    ap.add_argument("--force", action="store_true", help="overwrite an existing output file")
    ap.add_argument("--allow-untracked-path", action="store_true",
                    help="skip the git-ignore safety check (a non-repo path is always fine)")
    args = ap.parse_args()
    try:
        cbor, info = convert(args.input.read_bytes())
    except ConvertError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    for k in ("im4p_type", "im4p_version", "payload_bytes", "elements", "refs", "dup_keys",
              "truncated", "cbor_bytes", "cbor_sha256"):
        print("%-14s %s" % (k, info[k]))
    print("%-14s %s" % ("top_level_keys", ",".join(info["top_level_keys"])))
    if args.info:
        return 0
    if args.output is None:
        print("error: OUTPUT required (or --info)", file=sys.stderr)
        return 2
    try:
        if not args.allow_untracked_path:
            refuse_tracked_path(args.output)
        if args.output.exists() and not args.force:
            raise ConvertError("%s exists; pass --force" % args.output)
    except ConvertError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    data = cbor if args.raw else hidf(cbor)
    args.output.write_bytes(data)
    print("%-14s %s (%d bytes, sha256 %s)" % ("wrote", args.output, len(data),
                                              hashlib.sha256(data).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
