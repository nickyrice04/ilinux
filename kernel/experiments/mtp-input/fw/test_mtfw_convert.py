# SPDX-License-Identifier: GPL-2.0-only OR MIT
"""Offline tests for mtfw_convert.py. Synthetic data only; the optional real-image
test runs when MTFW_REAL_IM4P points at the Mac's own file (never committed).

usage: python3 -I -m unittest -v test_mtfw_convert   (from this directory)
"""
import base64
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mtfw_convert as M  # noqa: E402


# ---------------------------------------------------------------- test helpers

def der(tag, content):
    n = len(content)
    if n < 0x80:
        head = bytes([tag, n])
    elif n < 0x100:
        head = bytes([tag, 0x81, n])
    elif n < 0x10000:
        head = bytes([tag, 0x82]) + n.to_bytes(2, "big")
    else:
        head = bytes([tag, 0x83]) + n.to_bytes(3, "big")
    return head + content


def im4p(typ, payload, version="1", extra=b""):
    body = der(0x16, b"IM4P") + der(0x16, typ.encode()) + der(0x16, version.encode()) + \
        der(0x04, payload) + extra
    return der(0x30, body)


def xml_payload(text):
    return text.encode() + b"\0"


def cbor_decode(buf):
    """Independent strict decoder for the subset macOS emits. Returns (value, notes).

    notes collects the offsets at which byte-string contents start, so tests can
    assert the 4-byte alignment guarantee, and counts the 0xd3 filler tags."""
    notes = {"data_offsets": [], "fillers": 0}

    def head(off):
        b = buf[off]
        major, ai = b & 0xe0, b & 0x1f
        off += 1
        if ai <= 0x17:
            return major, ai, off
        width = {0x18: 1, 0x19: 2, 0x1a: 4}.get(ai)
        if width is None:
            raise ValueError("unsupported additional info 0x%02x" % ai)
        return major, int.from_bytes(buf[off:off + width], "big"), off + width

    def item(off):
        while buf[off] == 0xd3:        # filler tag
            notes["fillers"] += 1
            off += 1
        b = buf[off]
        if b in (0xf4, 0xf5):
            return b == 0xf5, off + 1
        major, val, off = head(off)
        if major == 0x00:
            return val, off
        if major == 0x40:
            notes["data_offsets"].append(off)
            return bytes(buf[off:off + val]), off + val
        if major == 0x60:
            s = bytes(buf[off:off + val])
            if not s.endswith(b"\0"):
                raise ValueError("text string without NUL")
            return s[:-1].decode(), off + val
        if major == 0x80:
            out = []
            for _ in range(val):
                v, off = item(off)
                out.append(v)
            return out, off
        if major == 0xa0:
            out = []
            for _ in range(val):
                k, off = item(off)
                v, off = item(off)
                out.append((k, v))
            return out, off
        raise ValueError("unexpected major 0x%02x" % major)

    value, end = item(0)
    if end != len(buf):
        raise ValueError("trailing bytes")
    return value, notes


def convert_xml(text):
    return M.convert(im4p("mtfw", xml_payload(text)))


class Der(unittest.TestCase):
    def test_roundtrip(self):
        typ, ver, payload = M.parse_im4p(im4p("mtfw", b"hello\0"))
        self.assertEqual((typ, ver, payload), ("mtfw", "1", b"hello\0"))

    def test_long_form_lengths(self):
        big = b"x" * 70000
        self.assertEqual(M.parse_im4p(im4p("ipdf", big))[2], big)

    def test_errors(self):
        good = im4p("mtfw", b"a\0")
        for name, blob in [
            ("empty", b""),
            ("truncated", good[:-1]),
            ("trailing", good + b"\0"),
            ("not a sequence", b"\x31" + good[1:]),
            ("wrong magic", good.replace(b"IM4P", b"IM4X")),
            ("extra element (kbag/compression)", im4p("mtfw", b"a\0", extra=der(0x04, b"kbag"))),
            ("payload not octets", der(0x30, der(0x16, b"IM4P") + der(0x16, b"mtfw") +
                                       der(0x16, b"1") + der(0x16, b"zz"))),
            ("type not 4 chars", im4p("mtfwx", b"a\0")),
            ("length overruns", good[:2] + b"\x81\xff" + good[4:]),
            ("indefinite length", bytes([0x30, 0x80]) + good[2:]),
        ]:
            with self.subTest(name):
                with self.assertRaises(M.ConvertError):
                    M.parse_im4p(blob)


class Integers(unittest.TestCase):
    def test_bases(self):
        self.assertEqual(M.parse_integer("0"), 0)
        self.assertEqual(M.parse_integer("17"), 17)
        self.assertEqual(M.parse_integer("0x10003000"), 0x10003000)
        self.assertEqual(M.parse_integer("0XfF"), 255)
        self.assertEqual(M.parse_integer("010"), 8)
        self.assertEqual(M.parse_integer("-1"), (1 << 64) - 1)
        self.assertEqual(M.parse_integer(" 0x2 "), 2)

    def test_rejects(self):
        for t in ["", "0x", "08", "1.5", "abc", "0x1g", "18446744073709551616", "--1", "+1"]:
            with self.subTest(t):
                with self.assertRaises(M.ConvertError):
                    M.parse_integer(t)


class Cbor(unittest.TestCase):
    def enc(self, kind_value):
        return M.encode(M.Obj(*kind_value))

    def test_integers(self):
        cases = {0: "00", 1: "01", 23: "17", 24: "1818", 255: "18ff", 256: "190100",
                 65535: "19ffff", 65536: "1a00010000", 0xffffffff: "1affffffff"}
        for v, hexs in cases.items():
            with self.subTest(v):
                self.assertEqual(self.enc(("int", v)).hex(), hexs)

    def test_64bit_value_keeps_low_32_bits(self):
        self.assertEqual(self.enc(("int", 0x1_0000_0005)).hex(), "05")

    def test_bool_and_string(self):
        self.assertEqual(self.enc(("bool", True)).hex(), "f5")
        self.assertEqual(self.enc(("bool", False)).hex(), "f4")
        self.assertEqual(self.enc(("str", b"")).hex(), "6100")
        self.assertEqual(self.enc(("str", b"A")).hex(), "624100")
        long = b"s" * 23                    # 24 bytes with the NUL: one length byte
        self.assertEqual(self.enc(("str", long)).hex()[:4], "7818")

    def test_dict_and_array(self):
        d = M.Obj("dict", [("A", M.Obj("int", 1)), ("B", M.Obj("arr", [M.Obj("bool", True),
                                                                        M.Obj("bool", False)]))])
        self.assertEqual(M.encode(d).hex(), "a1".replace("a1", "a2") + "62410001" + "624200" + "82f5f4")

    def test_data_alignment_for_every_phase(self):
        # whatever precedes the byte string, its content must start on a 4-byte boundary
        for lead in range(0, 9):
            for n in (0, 1, 3, 17, 23, 24, 255, 256, 300):
                with self.subTest(lead=lead, n=n):
                    items = [M.Obj("str", b"p" * (lead - 1))] if lead else []
                    items.append(M.Obj("data", bytes(range(256)) * 2 if n > 256 else bytes(range(n))))
                    out = M.encode(M.Obj("arr", items))
                    value, notes = cbor_decode(out)
                    self.assertEqual(len(notes["data_offsets"]), 1)
                    self.assertEqual(notes["data_offsets"][0] % 4, 0)
                    self.assertLessEqual(notes["fillers"], 3)
                    self.assertEqual(value[-1], items[-1].value)

    def test_known_filler_example(self):
        # {"k": <3 bytes>}: a1 62 6b 00 | d3 d3 d3 | 43 aa bb cc  -> content at offset 8
        d = M.Obj("dict", [("k", M.Obj("data", b"\xaa\xbb\xcc"))])
        self.assertEqual(M.encode(d).hex(), "a162" "6b00" "d3d3d3" "43" "aabbcc")

    def test_decoder_agrees_with_encoder_on_a_tree(self):
        tree = M.Obj("dict", [
            ("Name", M.Obj("str", "Zürich".encode())),
            ("Steps", M.Obj("arr", [
                M.Obj("dict", [("Address", M.Obj("int", 0x10003000)), ("Skip", M.Obj("bool", True))]),
                M.Obj("dict", [("Payload", M.Obj("data", b"\x01\x02\x03\x04\x05")),
                               ("Tag", M.Obj("str", b"TCAL"))]),
            ])),
            ("Empty", M.Obj("arr", [])),
        ])
        value, notes = cbor_decode(M.encode(tree))
        self.assertEqual(value[0], ("Name", "Zürich"))
        steps = value[1][1]
        self.assertEqual(steps[0], [("Address", 0x10003000), ("Skip", True)])
        self.assertEqual(steps[1][0], ("Payload", b"\x01\x02\x03\x04\x05"))
        self.assertEqual(value[2], ("Empty", []))
        self.assertTrue(all(o % 4 == 0 for o in notes["data_offsets"]))


class Xml(unittest.TestCase):
    DOC = (
        '<dict><key>CHIP,1</key><array>'
        '<dict><key>Address</key><integer size="64">0x10003000</integer>'
        '<key>Mask</key><integer ID="0" size="64">0xffffffff</integer>'
        '<key>Type</key><string ID="1">ReadModifyWrite</string>'
        '<key>Value</key><integer size="64">0x2</integer></dict>'
        '<dict><key>Address</key><integer size="64">0x10003060</integer>'
        '<key>Mask</key><integer IDREF="0"/>'
        '<key>Type</key><string IDREF="1"/>'
        '<key>Value</key><integer size="32">6</integer></dict>'
        '<dict><key>Address</key><integer IDREF="0"/><key>Description</key><string>a &amp; b &lt; c</string>'
        '<key>Payload</key><data>AQID\nBAUG</data><key>Type</key><string>Binary</string>'
        '<key>SkipCheck</key><true/><key>Other</key><false/></dict>'
        '</array></dict>'
    )

    def test_conversion(self):
        cbor, info = convert_xml(self.DOC)
        self.assertEqual(info["im4p_type"], "mtfw")
        self.assertEqual(info["top_level_keys"], ["CHIP,1"])
        self.assertEqual(info["refs"], 3)
        self.assertEqual(info["truncated"], 0)
        value, notes = cbor_decode(cbor)
        steps = value[0][1]
        self.assertEqual(steps[0], [("Address", 0x10003000), ("Mask", 0xffffffff),
                                    ("Type", "ReadModifyWrite"), ("Value", 2)])
        self.assertEqual(steps[1], [("Address", 0x10003060), ("Mask", 0xffffffff),
                                    ("Type", "ReadModifyWrite"), ("Value", 6)])
        self.assertEqual(steps[2][0], ("Address", 0xffffffff))      # IDREF resolved to the integer
        self.assertEqual(steps[2][1], ("Description", "a & b < c"))
        self.assertEqual(steps[2][2], ("Payload", b"\x01\x02\x03\x04\x05\x06"))
        self.assertEqual(steps[2][4], ("SkipCheck", True))
        self.assertEqual(steps[2][5], ("Other", False))
        self.assertTrue(all(o % 4 == 0 for o in notes["data_offsets"]))

    def test_idref_to_container_is_expanded(self):
        doc = ('<dict><key>a</key><dict ID="5"><key>x</key><integer>1</integer></dict>'
               '<key>b</key><dict IDREF="5"/></dict>')
        value, _ = cbor_decode(convert_xml(doc)[0])
        self.assertEqual(value[0][1], value[1][1])

    def test_integer_wider_than_32_bits_is_truncated_and_counted(self):
        _, info = convert_xml('<dict><key>n</key><integer size="64">0x100000007</integer></dict>')
        self.assertEqual(info["truncated"], 1)
        value, _ = cbor_decode(convert_xml(
            '<dict><key>n</key><integer size="64">0x100000007</integer></dict>')[0])
        self.assertEqual(value[0][1], 7)

    def test_size_attribute_masks_before_truncation(self):
        value, _ = cbor_decode(convert_xml('<dict><key>n</key><integer size="8">0x1ff</integer></dict>')[0])
        self.assertEqual(value[0][1], 0xff)

    def test_duplicate_key_replaces_in_place(self):
        doc = ('<dict><key>a</key><integer>1</integer><key>b</key><integer>2</integer>'
               '<key>a</key><integer>3</integer></dict>')
        cbor, info = convert_xml(doc)
        value, _ = cbor_decode(cbor)
        self.assertEqual(value, [("a", 3), ("b", 2)])
        self.assertEqual(info["dup_keys"], 1)

    def test_rejections(self):
        bad = {
            "doctype": '<!DOCTYPE x><dict/>',
            "entity": '<!ENTITY a "b"><dict/>',
            "pi": '<?xml version="1.0"?><dict/>',
            "unknown tag": '<dict><key>a</key><real>1.0</real></dict>',
            "date": '<dict><key>a</key><date>2020</date></dict>',
            "odd dict": '<dict><key>a</key></dict>',
            "non-key": '<dict><string>a</string><integer>1</integer></dict>',
            "unknown idref": '<dict><key>a</key><integer IDREF="9"/></dict>',
            "duplicate id": '<dict><key>a</key><integer ID="1">1</integer><key>b</key><integer ID="1">2</integer></dict>',
            "cycle": '<dict ID="1"><key>a</key><dict IDREF="1"/></dict>',
            "not a dict": '<array><integer>1</integer></array>',
            "bad base64": '<dict><key>a</key><data>!!!</data></dict>',
            "bad int": '<dict><key>a</key><integer>zz</integer></dict>',
            "huge int": '<dict><key>a</key><integer size="64">0x1ffffffffffffffff</integer></dict>',
            "bad size": '<dict><key>a</key><integer size="65">1</integer></dict>',
            "empty idref with content": '<dict><key>a</key><integer ID="1">1</integer><key>b</key>'
                                        '<integer IDREF="1">2</integer></dict>',
            "true with text": '<dict><key>a</key><true>yes</true></dict>',
            "child in string": '<dict><key>a</key><string><b/></string></dict>',
            "malformed": '<dict><key>a</key>',
        }
        for name, doc in bad.items():
            with self.subTest(name):
                with self.assertRaises(M.ConvertError):
                    convert_xml(doc)

    def test_depth_limit(self):
        doc = "<dict><key>a</key>" + "<array>" * 80 + "</array>" * 80 + "</dict>"
        with self.assertRaises(M.ConvertError):
            convert_xml(doc)
        # the parser enforces it on its own, not only the encoder
        with self.assertRaises(M.ConvertError):
            M.parse_payload(xml_payload(doc))
        ok = "<dict><key>a</key>" + "<array>" * 40 + "</array>" * 40 + "</dict>"
        M.parse_payload(xml_payload(ok))

    def test_payload_framing(self):
        with self.assertRaises(M.ConvertError):
            M.convert(im4p("mtfw", b"<dict/>"))              # no NUL
        with self.assertRaises(M.ConvertError):
            M.convert(im4p("mtfw", b"<dict/>\0\0"))          # two NULs
        with self.assertRaises(M.ConvertError):
            M.convert(im4p("mtfw", b"\xff\xfe\0"))           # not UTF-8
        self.assertEqual(M.convert(im4p("mtfw", b"<dict/>\0"))[0].hex(), "a0")


class Hidf(unittest.TestCase):
    def test_header_matches_the_driver_contract(self):
        data = b"\x01\x02\x03\x04" * 5
        c = M.hidf(data)
        magic, version, hdr_len, data_len, iface_off = struct.unpack("<5I", c[:20])
        self.assertEqual(c[:4], b"HIDF")
        self.assertEqual((version, hdr_len, data_len, iface_off), (1, 20, 20, 0))
        # the checks dchid_get_firmware() makes
        self.assertTrue(len(c) >= 20 and magic == 0x46444948 and version == 1)
        self.assertTrue(hdr_len >= 20 and hdr_len <= len(c))
        self.assertTrue(hdr_len + data_len <= len(c) and iface_off < data_len)
        self.assertEqual(c[hdr_len:hdr_len + data_len], data)

    def test_iface_offset_bounds(self):
        with self.assertRaises(M.ConvertError):
            M.hidf(b"1234", iface_offset=4)
        self.assertEqual(struct.unpack("<I", M.hidf(b"1234", iface_offset=3)[16:20])[0], 3)


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-I", str(Path(M.__file__)), *map(str, args)],
                              capture_output=True, text=True)

    def test_info_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "in.im4p"
            src.write_bytes(im4p("mtfw", xml_payload(Xml.DOC)))
            r = self.run_cli(src, "--info")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("cbor_bytes", r.stdout)
            self.assertEqual(sorted(p.name for p in Path(d).iterdir()), ["in.im4p"])

    def test_write_and_overwrite_protection(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "in.im4p"
            out = Path(d) / "out.bin"
            src.write_bytes(im4p("mtfw", xml_payload(Xml.DOC)))
            r = self.run_cli(src, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = out.read_bytes()
            self.assertEqual(data[:4], b"HIDF")
            self.assertEqual(cbor_decode(data[20:])[0][0][0], "CHIP,1")
            r = self.run_cli(src, out)
            self.assertEqual(r.returncode, 1)
            self.assertIn("exists", r.stderr)
            self.assertEqual(self.run_cli(src, out, "--force").returncode, 0)
            raw = Path(d) / "raw.bin"
            self.assertEqual(self.run_cli(src, raw, "--raw").returncode, 0)
            self.assertEqual(raw.read_bytes(), data[20:])

    def test_refuses_a_tracked_path(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / ".gitignore").write_text("build/\n")
            src = repo / "build" / "in.im4p"
            src.parent.mkdir()
            src.write_bytes(im4p("mtfw", xml_payload(Xml.DOC)))
            ok = self.run_cli(src, repo / "build" / "fw.bin")
            self.assertEqual(ok.returncode, 0, ok.stderr)
            bad = self.run_cli(src, repo / "fw.bin")
            self.assertEqual(bad.returncode, 1)
            self.assertIn("not ignored", bad.stderr)
            self.assertFalse((repo / "fw.bin").exists())
            forced = self.run_cli(src, repo / "fw.bin", "--allow-untracked-path")
            self.assertEqual(forced.returncode, 0, forced.stderr)

    def test_bad_input_exit_code(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "junk.im4p"
            src.write_bytes(b"not an im4p")
            self.assertEqual(self.run_cli(src, "--info").returncode, 1)


@unittest.skipUnless(os.environ.get("MTFW_REAL_IM4P"), "set MTFW_REAL_IM4P to the Mac's own image")
class RealImage(unittest.TestCase):
    """Structural checks only; nothing from the image is printed or stored."""

    def test_real_image(self):
        blob = Path(os.environ["MTFW_REAL_IM4P"]).read_bytes()
        cbor, info = M.convert(blob)
        self.assertEqual(info["im4p_type"], "mtfw")
        self.assertEqual(info["truncated"], 0)
        value, notes = cbor_decode(cbor)
        self.assertEqual(len(value), 1)
        self.assertTrue(all(o % 4 == 0 for o in notes["data_offsets"]))
        steps = value[0][1]
        types = [dict(s).get("Type") for s in steps]
        self.assertIn("Binary", types)
        self.assertIn("RequestCalibration", types)
        self.assertEqual(types[-1], "Config")


if __name__ == "__main__":
    unittest.main()
