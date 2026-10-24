#!/usr/bin/env python3
"""Build/test only the original portable adapter; no SDK or native operations."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import struct
import subprocess
import sys


HERE = Path(__file__).resolve().parent
SOURCES = ("entry.c", "entry.h", "memory.c", "memory.h", "test_entry.c",
           "test_memory.c", "run.py", "README.md")
COMMON = ["-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic"]
MARKERS = {
    "entry": "SPTM31Z_ENTRY_PASS groups=8 length_cases=854 byte_position_cases=848 native=NOT_DEPLOYABLE",
    "memory": "SPTM31Z_MEMORY_PASS groups=8 bitmap_cases=2304 native=NOT_DEPLOYABLE",
}


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def execute(command: list[str], directory: Path, label: str) -> dict:
    completed = subprocess.run(command, cwd=HERE, capture_output=True, text=True,
                               timeout=60, check=False)
    record = {"command": command, "returncode": completed.returncode,
              "stdout": completed.stdout, "stderr": completed.stderr}
    write_json(directory / (label + ".json"), record)
    if completed.returncode:
        raise RuntimeError(f"{label} exited {completed.returncode}; see its JSON log")
    return record


def undefined_elf_symbols(path: Path) -> list[str]:
    """Inspect bounded ELF64 LE relocatable symbols without an external tool.

    This checks the compiler's object format and inventories undefined symbols;
    it is not a linker, loader, instruction validator or native qualification.
    Extended section numbering and unfamiliar object forms fail explicitly.
    """
    data = path.read_bytes()

    def span(offset: int, size: int) -> bytes:
        if offset < 0 or size < 0 or offset > len(data) or size > len(data) - offset:
            raise ValueError("ELF span outside object")
        return data[offset:offset + size]

    if span(0, 7) != b"\x7fELF\x02\x01\x01":
        raise ValueError("not ELF64 little endian version1")
    if struct.unpack("<HHI", span(16, 8)) != (1, 183, 1):
        raise ValueError("not an AArch64 relocatable object")
    section_offset = struct.unpack("<Q", span(40, 8))[0]
    entry_size, count = struct.unpack("<HH", span(58, 4))
    if entry_size != 64 or not count:
        raise ValueError("unsupported ELF section numbering")
    span(section_offset, entry_size * count)
    sections = [struct.unpack("<IIQQQQIIQQ", span(section_offset + i * entry_size, 64))
                for i in range(count)]
    names: set[str] = set()
    symbol_tables = 0
    for section in sections:
        if section[1] != 2:  # SHT_SYMTAB
            continue
        symbol_tables += 1
        offset, size, link, symbol_size = section[4], section[5], section[6], section[9]
        if symbol_size != 24 or size % symbol_size or link >= count:
            raise ValueError("invalid ELF symbol table")
        strings = sections[link]
        if strings[1] != 3:
            raise ValueError("ELF symbol strings are not SHT_STRTAB")
        table = span(strings[4], strings[5])
        span(offset, size)
        for cursor in range(offset, offset + size, symbol_size):
            name, info, _, index, _, _ = struct.unpack("<IBBHQQ", span(cursor, 24))
            if index != 0 or (info >> 4) not in (1, 2) or name == 0:
                continue
            if name >= len(table):
                raise ValueError("ELF symbol name outside string table")
            end = table.find(b"\0", name)
            if end < 0:
                raise ValueError("unterminated ELF symbol name")
            names.add(table[name:end].decode("ascii"))
    if not symbol_tables:
        raise ValueError("ELF symbol table missing")
    return sorted(names)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="fresh output directory; use ignored build/ on the host")
    parser.add_argument("--cc", default="cc", help="one C compiler executable, no shell command")
    parser.add_argument("--sanitize", action="store_true", help="repeat using ASan and UBSan")
    parser.add_argument("--freestanding", action="store_true", help="also compile AArch64 ELF objects")
    parser.add_argument("--clang", default="clang", help="compiler for freestanding objects")
    args = parser.parse_args()
    output = args.output.resolve()
    if output == HERE or HERE in output.parents:
        parser.error("output must not be inside the source directory")
    if output.exists():
        parser.error("output must be a fresh, nonexistent directory")
    output.mkdir(parents=True, exist_ok=False)
    report: dict = {"schema": 1, "status": "FAIL", "native": "NOT_DEPLOYABLE",
                    "host": platform.platform(), "unique_c_groups": 16,
                    "tests": [], "freestanding": {"requested": args.freestanding,
                    "linked": False, "executed": False}}
    try:
        bindings = []
        for name in SOURCES:
            data = (HERE / name).read_bytes()
            bindings.append({"file": name, "bytes": len(data),
                             "sha256": hashlib.sha256(data).hexdigest()})
        write_json(output / "source-bindings.json", bindings)
        report["source_bindings_sha256"] = hashlib.sha256(
            (output / "source-bindings.json").read_bytes()).hexdigest()
        report["compiler"] = execute([args.cc, "--version"], output, "compiler")["stdout"]
        variants = [("optimized", ["-O2"])]
        if args.sanitize:
            variants.append(("sanitized", ["-O1", "-g", "-fsanitize=address,undefined",
                                          "-fno-omit-frame-pointer", "-fno-sanitize-recover=all"]))
        for variant, flags in variants:
            for name in MARKERS:
                executable = output / (name + "-" + variant)
                sources = ["entry.c", "memory.c", "test_entry.c"] if name == "entry" else [
                    "memory.c", "test_memory.c"]
                execute([args.cc, *COMMON, *flags, *sources, "-o", str(executable)],
                        output, name + "-" + variant + "-compile")
                run = execute([str(executable)], output, name + "-" + variant + "-run")
                if run["stdout"].strip() != MARKERS[name] or run["stderr"]:
                    raise RuntimeError(f"unexpected output from {name}-{variant}")
                report["tests"].append({"name": name, "variant": variant, "groups": 8,
                                        "marker": MARKERS[name], "status": "PASS"})
        if args.freestanding:
            report["freestanding"]["compiler"] = execute([args.clang, "--version"], output,
                                                        "cross-compiler")["stdout"]
            report["freestanding"]["objects"] = []
            for name in ("entry", "memory"):
                obj = output / (name + "-aarch64.o")
                execute([args.clang, *COMMON, "--target=aarch64-none-elf", "-ffreestanding",
                         "-fno-stack-protector", "-O2", "-c", name + ".c", "-o", str(obj)],
                        output, name + "-cross-compile")
                try:
                    undefined = undefined_elf_symbols(obj)
                except (ValueError, UnicodeError, struct.error) as error:
                    report["freestanding"]["symbol_check"] = "UNSUPPORTED_OR_INVALID"
                    raise RuntimeError(f"ELF symbol inspection refused: {error}") from error
                report["freestanding"]["objects"].append({"file": obj.name,
                    "sha256": hashlib.sha256(obj.read_bytes()).hexdigest(),
                    "undefined_symbols": undefined})
            report["freestanding"]["symbol_check"] = "PASS"
        # Detect source mutation across this run instead of issuing a stale receipt.
        for binding in bindings:
            if hashlib.sha256((HERE / binding["file"]).read_bytes()).hexdigest() != binding["sha256"]:
                raise RuntimeError("source changed during run: " + binding["file"])
        report["status"] = "PASS"
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as error:
        report["error"] = str(error)
    write_json(output / "results.json", report)
    print(json.dumps({"status": report["status"], "unique_c_groups": report["unique_c_groups"],
                      "native": report["native"], "results": str(output / "results.json")}, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
