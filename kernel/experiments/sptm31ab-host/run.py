#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile/link and audit original31AB code. Never executes the AArch64 payload."""
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
FILES = ("entry.S", "transport.S", "transport.h", "layout.h", "image.ld", "audit.py",
         "test_audit.py", "run.py", "README.md")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def output_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def execute(command: list[str], output: Path, label: str) -> dict:
    result = subprocess.run(command, cwd=HERE, capture_output=True, text=True, check=False, timeout=60)
    record = {"command": command, "returncode": result.returncode,
              "stdout": result.stdout, "stderr": result.stderr}
    output_json(output / (label + ".json"), record)
    if result.returncode:
        raise RuntimeError(f"{label} failed; inspect its log")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--ld", default="ld")
    parser.add_argument("--target", help="optional Clang cross target")
    parser.add_argument("--compile-only", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or output == HERE or HERE in output.parents:
        parser.error("use a fresh output directory outside source")
    output.mkdir(parents=True, exist_ok=False)
    report = {"schema": 1, "status": "FAIL", "host": platform.platform(),
              "native": "NOT_DEPLOYABLE", "payload_executed": False,
              "compile_only": args.compile_only, "monitor_calls_executed": 0}
    try:
        bindings = [{"file": name, "bytes": len((HERE / name).read_bytes()),
                     "sha256": digest((HERE / name).read_bytes())} for name in FILES]
        output_json(output / "source-bindings.json", bindings)
        report["source_bindings_sha256"] = digest((output / "source-bindings.json").read_bytes())
        report["compiler"] = execute([args.cc, "--version"], output, "compiler")["stdout"]
        target = ["--target=" + args.target] if args.target else []
        objects = []
        for name in ("entry", "transport"):
            obj = output / (name + ".o")
            execute([args.cc, *target, "-ffreestanding", "-fno-stack-protector", "-c",
                     name + ".S", "-o", str(obj)], output, name + "-compile")
            objects.append(str(obj))
        report["objects"] = [{"file": Path(obj).name, "sha256": digest(Path(obj).read_bytes())} for obj in objects]
        if not args.compile_only:
            audit = load("audit")
            tests = load("test_audit")
            report["linker"] = execute([args.ld, "--version"], output, "linker")["stdout"]
            images = []
            canonical = None
            for label, base in (("canonical", 0), ("slid", 0x40000000)):
                elf = output / (label + ".elf")
                execute([args.ld, "--fatal-warnings", "--no-undefined", "--build-id=none",
                         "-z", "max-page-size=0x4000", "--defsym", f"host_image_base=0x{base:x}",
                         "-T", "image.ld", *objects, "-o", str(elf)], output, label + "-link")
                data = elf.read_bytes()
                payload, metadata = audit.inspect(data, base)
                metadata["elf_sha256"] = digest(data)
                metadata["payload_sha256"] = digest(payload)
                metadata["tests"] = tests.run(data, base)
                output_json(output / (label + "-layout.json"), metadata)
                images.append({"label": label, "base": base, "elf_sha256": digest(data),
                               "payload_sha256": digest(payload), "tests": metadata["tests"]})
                if canonical is None:
                    canonical = payload
                    (output / "payload.bin").write_bytes(payload)
                    output_json(output / "layout.json", metadata)
                elif payload != canonical:
                    raise ValueError("linked image bytes changed under aligned slide")
            report["images"] = images
            report["payload_sha256"] = digest(canonical)
            report["payload_bytes"] = len(canonical)
            report["slide_bytes_identical"] = True
            report["unique_audit_groups"] = 6
            report["mutation_refusals_per_image"] = 16
        for binding in bindings:
            if digest((HERE / binding["file"]).read_bytes()) != binding["sha256"]:
                raise ValueError("source changed during run: " + binding["file"])
        report["status"] = "PASS"
    except (OSError, ValueError, RuntimeError, AssertionError, subprocess.TimeoutExpired) as error:
        report["error"] = str(error)
    output_json(output / "results.json", report)
    print(json.dumps({"status": report["status"], "native": report["native"],
                      "compile_only": args.compile_only, "results": str(output / "results.json")}, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
