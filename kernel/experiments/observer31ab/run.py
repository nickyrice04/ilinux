#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile/test original snapshot translation and RAM marker code; no devices."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OWN = ("observer.c", "observer.h", "test_observer.c", "run.py", "README.md")
CHECKER = "kernel/experiments/sptm31z-adapter/run.py"
CHECKER_SHA = "89b235a13b7c0614c4fb34a4ff26d77cafa205eb0632498956059f75018150bc"
FLAGS = ["-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic"]
MARKER = "OBSERVER31AB_PASS groups=12 translation_oracle_cases=1200 native=NOT_DEPLOYABLE"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def execute(command: list[str], output: Path, label: str) -> dict:
    done = subprocess.run(command, cwd=HERE, capture_output=True, text=True, timeout=60)
    record = {"command": command, "returncode": done.returncode,
              "stdout": done.stdout, "stderr": done.stderr}
    write(output / (label + ".json"), record)
    if done.returncode:
        raise RuntimeError(label + " failed; inspect its result log")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--sanitize", action="store_true")
    parser.add_argument("--freestanding", action="store_true")
    parser.add_argument("--clang", default="clang")
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or out == HERE or HERE in out.parents:
        parser.error("output must be fresh and outside the source directory")
    out.mkdir(parents=True, exist_ok=False)
    report = {"schema": 1, "status": "FAIL", "native": "NOT_DEPLOYABLE",
              "host": platform.platform(), "unique_c_groups": 0, "tests": [],
              "freestanding": {"requested": args.freestanding, "linked": False, "executed": False}}
    try:
        bindings = []
        paths = [HERE / name for name in OWN] + [ROOT / CHECKER]
        for path in paths:
            if path.is_symlink():
                raise ValueError("source symlink refused")
            data = path.read_bytes()
            relative = str(path.relative_to(ROOT))
            if relative == CHECKER and sha(data) != CHECKER_SHA:
                raise ValueError("frozen original ELF checker hash mismatch")
            bindings.append({"file": relative, "bytes": len(data), "sha256": sha(data)})
        write(out / "source-bindings.json", bindings)
        report["source_bindings_sha256"] = sha((out / "source-bindings.json").read_bytes())
        report["compiler"] = execute([args.cc, "--version"], out, "compiler")["stdout"]
        variants = [("optimized", ["-O2"])]
        if args.sanitize:
            variants.append(("sanitized", ["-O1", "-g", "-fsanitize=address,undefined",
                            "-fno-omit-frame-pointer", "-fno-sanitize-recover=all"]))
        for name, flags in variants:
            binary = out / ("observer-" + name)
            execute([args.cc, *FLAGS, *flags, "observer.c", "test_observer.c", "-o", str(binary)],
                    out, name + "-compile")
            result = execute([str(binary)], out, name + "-run")
            if result["stdout"].strip() != MARKER or result["stderr"]:
                raise ValueError("unexpected test output")
            report["tests"].append({"variant": name, "status": "PASS", "groups": 12,
                                    "translation_oracle_cases": 1200, "marker": MARKER})
            report["unique_c_groups"] = 12
        if args.freestanding:
            spec = importlib.util.spec_from_file_location("_observer_elf_checker", ROOT / CHECKER)
            if not spec or not spec.loader:
                raise ValueError("cannot load original ELF checker")
            checker = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(checker)
            report["freestanding"]["compiler"] = execute([args.clang, "--version"], out, "cross-compiler")["stdout"]
            obj = out / "observer-aarch64.o"
            execute([args.clang, *FLAGS, "--target=aarch64-none-elf", "-ffreestanding", "-O2",
                     "-fno-stack-protector", "-c", "observer.c", "-o", str(obj)], out, "cross-compile")
            symbols = checker.undefined_elf_symbols(obj)
            report["freestanding"].update({"symbol_check": "PASS", "undefined_symbols": symbols,
                                          "object_sha256": sha(obj.read_bytes())})
        for binding in bindings:
            if sha((ROOT / binding["file"]).read_bytes()) != binding["sha256"]:
                raise ValueError("source changed during test run")
        report["status"] = "PASS"
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        report["error"] = str(error)
    write(out / "results.json", report)
    print(json.dumps({"status": report["status"], "unique_c_groups": report["unique_c_groups"],
                      "native": report["native"], "results": str(out / "results.json")}, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
