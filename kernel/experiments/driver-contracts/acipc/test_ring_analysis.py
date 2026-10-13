import hashlib
import importlib.util
import io
import pathlib
import struct
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("extract_ring_analysis", HERE / "extract_ring_analysis.py")
extract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(extract)


def uleb(value):
    result = bytearray()
    while True:
        byte = value & 127
        value >>= 7
        result.append(byte | (128 if value else 0))
        if not value:
            return bytes(result)


def fixture():
    """Original synthetic cache-shaped data; no Apple instruction bytes."""
    data = bytearray(0x2c0000)
    data[:16] = b"dyld_v1  arm64e".ljust(16, b"\0")
    struct.pack_into("<II", data, 16, 512, 1)
    struct.pack_into("<II", data, 448, 1024, 1)
    struct.pack_into("<QQQII", data, 512, 0x180000000, len(data), 0, 5, 5)
    struct.pack_into("<QQQII", data, 1024, extract.IMAGE_VM, 0, 0, 1152, 0)
    path = extract.IMAGE.encode("ascii") + b"\0"
    data[1152:1152 + len(path)] = path
    text_base = 0x18022a000
    text_size = 586216
    segment = struct.pack("<II16sQQQQIIII", 0x19, 152, b"__TEXT", extract.IMAGE_VM,
                          0xac2ca, 0x226000, 0xac2ca, 5, 5, 1, 0)
    section = struct.pack("<16s16sQQIIIIIIII", b"__text", b"__TEXT", text_base,
                          text_size, 0x22a000, 2, 0, 0, 0x80000400, 0, 0, 0)
    starts = sorted({text_base, *(t[1] for t in extract.TARGETS),
                     *(t[1] + t[2] for t in extract.TARGETS)})
    previous = extract.IMAGE_VM
    encoded = bytearray()
    for address in starts:
        encoded.extend(uleb(address - previous))
        previous = address
    encoded.append(0)
    data[0x1000:0x1000 + len(encoded)] = encoded
    commands = segment + section + struct.pack("<IIII", 0x26, 16, 0x1000, len(encoded))
    mh = struct.pack("<8I", 0xfeedfacf, 0x100000c, 2, 6, 2, len(commands), 0, 0)
    data[0x226000:0x226020] = mh
    data[0x226020:0x226020 + len(commands)] = commands
    for index, (_, address, length) in enumerate(extract.TARGETS, 1):
        offset = address - 0x180000000
        data[offset:offset + length] = bytes([index]) * length
    return data


def ranges(data):
    return extract.extract_ranges(io.BytesIO(data), hashlib.sha256(data).hexdigest())


class AnalysisCarrierTests(unittest.TestCase):
    def test_extracts_exact_selected_bytes(self):
        result = ranges(fixture())
        self.assertEqual(sum(len(f["data"]) for f in result), 524)
        for index, function in enumerate(result, 1):
            self.assertEqual(function["data"], bytes([index]) * extract.TARGETS[index - 1][2])

    def test_source_pin_rejects_unknown_cache(self):
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            extract.extract_ranges(io.BytesIO(fixture()))

    def test_elf_sections_symbols_and_no_load_headers(self):
        functions = ranges(fixture())
        data = extract.make_elf(functions)
        h = struct.unpack_from("<16sHHIQQQIHHHHHH", data)
        self.assertEqual(h[0][:7], b"\x7fELF\x02\x01\x01")
        self.assertEqual(h[2], 183)
        self.assertEqual((h[4], h[5], h[10]), (0, 0, 0))
        shoff = h[6]
        sections = [struct.unpack_from("<IIQQQQIIQQ", data, shoff + i * 64)
                    for i in range(h[12])]
        for i, function in enumerate(functions, 1):
            s = sections[i]
            self.assertEqual((s[1], s[2], s[3], s[5]),
                             (1, 6, function["address"], len(function["data"])))
            self.assertEqual(data[s[4]:s[4] + s[5]], function["data"])
        symtab, strtab = sections[4], sections[5]
        self.assertEqual((symtab[6], symtab[7], symtab[9]), (5, 1, 24))
        for i, function in enumerate(functions, 1):
            name, info, other, section, address, size = struct.unpack_from(
                "<IBBHQQ", data, symtab[4] + i * 24)
            start = strtab[4] + name
            end = data.index(b"\0", start)
            self.assertEqual(data[start:end].decode(), function["symbol"])
            self.assertEqual((info, other, section, address, size),
                             (0x12, 0, i, function["address"], len(function["data"])))

    def test_rejects_ambiguous_mapping(self):
        data = fixture()
        struct.pack_into("<I", data, 20, 2)
        data[544:576] = data[512:544]
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            ranges(data)

    def test_rejects_architecture_and_text_mismatch(self):
        data = fixture()
        struct.pack_into("<I", data, 0x226000 + 4, 0x1000007)
        with self.assertRaisesRegex(ValueError, "architecture"):
            ranges(data)
        data = fixture()
        # Section_64 offset field, after 32-byte header and 72-byte segment.
        struct.pack_into("<I", data, 0x226000 + 32 + 72 + 48, 0x22a004)
        with self.assertRaisesRegex(ValueError, "mapping mismatch"):
            ranges(data)

    def test_function_starts_rejects_truncation_overflow_and_padding(self):
        for data in (b"\x80", b"\x80" * 10, b"\x00\x01", b"\x01"):
            with self.subTest(data=data), self.assertRaises(ValueError):
                extract.function_starts(data, 0)
        with self.assertRaises(ValueError):
            extract.function_starts(b"\x01\x00", (1 << 64) - 1)

    def test_rejects_changed_function_interval(self):
        data = fixture()
        # Replace the starts table with only one entry and a terminator.
        table = uleb(extract.TARGETS[0][1] - extract.IMAGE_VM) + b"\0"
        data[0x1000:0x1000 + 64] = table + bytes(64 - len(table))
        with self.assertRaisesRegex(ValueError, "interval changed"):
            ranges(data)

    def test_refuses_unselected_functions(self):
        functions = ranges(fixture())
        with self.assertRaises(ValueError):
            extract.make_elf(functions[:1])
        functions[0]["address"] += 4
        with self.assertRaises(ValueError):
            extract.make_elf(functions)


if __name__ == "__main__":
    unittest.main()
