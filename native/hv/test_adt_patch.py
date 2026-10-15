"""Offline tests for the raw ADT walker/patcher: synthetic blobs only."""
from pathlib import Path
import struct
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adt_patch as A  # noqa: E402


def prop(name, value, flag=0):
    raw = name.encode().ljust(32, b"\0") + struct.pack("<I", len(value) | flag << 31) + value
    return raw + b"\0" * (-len(raw) % 4)


def node(name, props=(), children=()):
    plist = [("name", name.encode() + b"\0", 0)] if name is not None else []
    plist += list(props)
    body = struct.pack("<II", len(plist), len(children))
    body += b"".join(prop(n, v, f) for n, v, f in plist)
    return body + b"".join(children)


def u64s(*v):
    return struct.pack("<%dQ" % len(v), *v)


def sample():
    mm = node("memory-map", [("SEPFW", u64s(0x10000100000, 0x400000), 0),
                             ("TrustCache", u64s(0x10000600000, 0x20000), 0),
                             ("Missing", u64s(0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF), 0),
                             ("odd", b"abc", 0)])
    chosen = node("chosen", [("firmware-version", b"iBoot-1\0", 0), ("placeholder", b"\1\2\3\4", 1)], [mm])
    cpus = node("cpus", [("#address-cells", struct.pack("<I", 1), 0)], [node("cpu0"), node("cpu1")])
    return node("device-tree", [("compatible", b"J716cAP\0apple,t6050\0", 0)], [chosen, cpus]) + b"\0" * 16


class WalkerTests(unittest.TestCase):
    def test_parse_and_locate(self):
        blob = sample()
        root, end = A.parse(blob)
        self.assertEqual(root.path, "/")
        self.assertEqual(end, len(blob) - 16)
        off, size, flags = A.locate(blob, "/chosen/memory-map", "SEPFW")
        self.assertEqual((size, flags), (16, 0))
        self.assertEqual(struct.unpack_from("<QQ", blob, off), (0x10000100000, 0x400000))
        self.assertEqual(A.locate(blob, "/chosen", "placeholder")[2], 1)

    def test_memory_map_only_16_byte_entries(self):
        mm = A.memory_map(sample())
        self.assertEqual(mm["SEPFW"], (0x10000100000, 0x400000))
        self.assertEqual(mm["Missing"], (0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF))
        self.assertNotIn("odd", mm)
        self.assertNotIn("name", mm)

    def test_odd_sized_property_is_aligned(self):
        # "odd" is 3 bytes; the next node/property must still parse.
        root, _ = A.parse(sample())
        self.assertEqual([c.path for c in root.children], ["/chosen", "/cpus"])
        self.assertEqual([c.path for c in root.children[1].children], ["/cpus/cpu0", "/cpus/cpu1"])

    def test_missing_and_duplicate(self):
        blob = sample()
        with self.assertRaises(A.ADTError):
            A.locate(blob, "/chosen/memory-map", "nope")
        with self.assertRaises(A.ADTError):
            A.locate(blob, "/chosen/nonexistent", "SEPFW")
        dup = node("device-tree", children=[node("chosen"), node("chosen")])
        with self.assertRaises(A.ADTError):
            A.locate(dup, "/chosen", "name")
        dupprop = node("device-tree", [("x", b"1234", 0), ("x", b"5678", 0)])
        with self.assertRaises(A.ADTError):
            A.locate(dupprop, "/", "x")

    def test_malformed_inputs(self):
        blob = sample()
        for bad in (b"", blob[:6], blob[:100], b"\xff" * 64):
            with self.subTest(len=len(bad)):
                with self.assertRaises(A.ADTError):
                    A.parse(bad)
        # property size runs past the end
        broken = bytearray(blob)
        broken[8 + 32:8 + 36] = struct.pack("<I", 0x7FFFFFF0)
        with self.assertRaises(A.ADTError):
            A.parse(bytes(broken))
        # unterminated 32-byte property name
        broken = bytearray(blob)
        broken[8:8 + 32] = b"A" * 32
        with self.assertRaises(A.ADTError):
            A.parse(bytes(broken))

    def test_depth_and_node_limits(self):
        deep = node("leaf")
        for i in range(A.MAX_DEPTH + 2):
            deep = node("n%d" % i, children=[deep])
        with self.assertRaises(A.ADTError):
            A.parse(deep)


class PatchTests(unittest.TestCase):
    def test_patch_changes_only_the_value(self):
        blob = sample()
        new = u64s(0x10000200000, 0x400000)
        out, off, old = A.patch_value(blob, "/chosen/memory-map", "SEPFW", new)
        self.assertEqual(old, u64s(0x10000100000, 0x400000))
        self.assertEqual(len(out), len(blob))
        diff = [i for i in range(len(blob)) if blob[i] != out[i]]
        self.assertTrue(diff and min(diff) >= off and max(diff) < off + 16, diff)
        self.assertEqual(A.memory_map(out)["SEPFW"], (0x10000200000, 0x400000))
        self.assertEqual(A.memory_map(out)["TrustCache"], A.memory_map(blob)["TrustCache"])
        # size/flag word untouched
        self.assertEqual(A.locate(out, "/chosen/memory-map", "SEPFW")[1:], (16, 0))

    def test_flag_bit_preserved(self):
        blob = sample()
        out, _, _ = A.patch_value(blob, "/chosen", "placeholder", b"\x09" * 4)
        self.assertEqual(A.locate(out, "/chosen", "placeholder")[2], 1)

    def test_wrong_length_rejected(self):
        with self.assertRaises(A.ADTError):
            A.patch_value(sample(), "/chosen/memory-map", "SEPFW", b"\0" * 8)

    def test_input_not_mutated(self):
        blob = sample()
        keep = bytes(blob)
        A.patch_value(blob, "/chosen/memory-map", "SEPFW", u64s(1, 2))
        self.assertEqual(blob, keep)


if __name__ == "__main__":
    unittest.main()
