"""Assemble, link and disassemble ARM64 locally; no target connection."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "third_party/m1n1/proxyclient"))
from m1n1.asm import ARMAsm

code = ARMAsm("nop\nret", 0x80000000)
assert code.data == bytes.fromhex("1f2003d5c0035fd6"), code.data.hex()
disassembly = "\n".join(code.disassemble())
assert "nop" in disassembly and "ret" in disassembly, disassembly
print("ARM64 assembly/link/objcopy/nm/objdump: PASS (nop; ret)")
