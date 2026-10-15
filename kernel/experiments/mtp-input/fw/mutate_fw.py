#!/usr/bin/env python3
"""Mutation check for mtfw_convert.py: every deliberate mistake must fail the tests.

usage: python3 -I mutate_fw.py
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

MUTANTS = [
    ("filler pads to 8 instead of 4", "pad = (-len(out) - len(head)) & 3", "pad = (-len(out) - len(head)) & 7"),
    ("filler ignores the head size", "pad = (-len(out) - len(head)) & 3", "pad = (-len(out)) & 3"),
    ("filler tag is not 0xd3", 'out.extend(b"\\xd3" * pad)', 'out.extend(b"\\xd2" * pad)'),
    ("text length excludes the NUL", "out.extend(varuint_head(0x60, len(o.value) + 1))",
     "out.extend(varuint_head(0x60, len(o.value)))"),
    ("text has no terminating NUL", "            out.extend(o.value)\n            out.append(0)\n",
     "            out.extend(o.value)\n"),
    ("integers keep all 32+ bits unmasked", "out.extend(varuint_head(0x00, o.value & 0xffffffff))",
     "out.extend(varuint_head(0x00, o.value & 0xffffffffff))"),
    ("true and false swapped", "out.append(0xf5 if o.value else 0xf4)", "out.append(0xf4 if o.value else 0xf5)"),
    ("one-byte head threshold off by one", "    if value <= 0x17:\n        return bytes([major | value])",
     "    if value <= 0x18:\n        return bytes([major | value])"),
    ("two-byte form uses little endian", "return bytes([major | 0x19]) + value.to_bytes(2, \"big\")",
     "return bytes([major | 0x19]) + value.to_bytes(2, \"little\")"),
    ("dictionary written in reverse order", "            for key, val in o.value:\n                rec(Obj(\"str\"",
     "            for key, val in reversed(o.value):\n                rec(Obj(\"str\""),
    ("octal read as decimal", "        v = int(t, 8) if len(t) > 1 else 0", "        v = int(t, 10) if len(t) > 1 else 0"),
    ("integer size attribute ignored", "        v = parse_integer(elem.text or \"\") & ((1 << size) - 1)",
     "        v = parse_integer(elem.text or \"\")"),
    ("IDREF to unknown id accepted", "        if ref not in ids:\n            raise ConvertError(\"unknown IDREF %r\" % ref)\n",
     "        if ref not in ids:\n            return Obj(\"int\", 0)\n"),
    ("DOCTYPE accepted", '    if "<!DOCTYPE" in text or "<!ENTITY" in text or "<?" in text:\n        raise ConvertError("DTD / processing instruction in payload")\n',
     ""),
    ("payload NUL check removed", "    if len(payload) - len(stripped) != 1:\n        raise ConvertError(\"payload must end in exactly one NUL\")\n",
     ""),
    ("HIDF header length wrong", "struct.pack(\"<5I\", HIDF_MAGIC, HIDF_VERSION, HIDF_HEADER, len(data), iface_offset)",
     "struct.pack(\"<5I\", HIDF_MAGIC, HIDF_VERSION, HIDF_HEADER + 4, len(data), iface_offset)"),
    ("duplicate key appended instead of replaced", "                pairs[index[key]] = (key, val)   # OSDictionary::setObject keeps the position\n",
     "                pairs.append((key, val))\n"),
    ("data in dictionary keys forbidden check removed", "            if k.tag != \"key\":\n                raise ConvertError(\"<dict> child is not a <key>\")\n",
     ""),
    ("depth limit removed", "    if depth > MAX_DEPTH:\n        raise ConvertError(\"nesting too deep\")\n    ref = elem.attrib.get(\"IDREF\")",
     "    ref = elem.attrib.get(\"IDREF\")"),
]


def main():
    original = (HERE / "mtfw_convert.py").read_text()
    bad = 0
    with tempfile.TemporaryDirectory() as d:
        work = Path(d)
        shutil.copy(HERE / "test_mtfw_convert.py", work / "test_mtfw_convert.py")
        (work / "mtfw_convert.py").write_text(original)
        base = subprocess.run([sys.executable, "-I", str(work / "test_mtfw_convert.py")],
                              capture_output=True, text=True, cwd=work)
        print("baseline:", "pass" if base.returncode == 0 else "FAIL")
        if base.returncode:
            print(base.stderr[-800:])
            return 2
        for name, old, new in MUTANTS:
            if original.count(old) != 1:
                print("MUTATION SITE NOT FOUND:", name)
                bad += 1
                continue
            (work / "mtfw_convert.py").write_text(original.replace(old, new))
            try:
                r = subprocess.run([sys.executable, "-I", str(work / "test_mtfw_convert.py")],
                                   capture_output=True, text=True, cwd=work, timeout=120)
                caught = r.returncode != 0
            except subprocess.TimeoutExpired:
                caught = True
            print("%-52s %s" % (name, "caught" if caught else "SURVIVED"))
            bad += 0 if caught else 1
    print("mutants: %d, survived/invalid: %d" % (len(MUTANTS), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
