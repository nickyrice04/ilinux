#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build and audit the original immutable assembly probe; never execute it."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
OWN = ("entry.S", "layout.h", "image.ld", "audit.py", "run.py", "README.md")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def bindings():
    result = []
    for name in OWN:
        p = HERE / name
        if p.is_symlink():
            raise ValueError("source symlink")
        b = p.read_bytes()
        result.append({"file": name, "bytes": len(b), "sha256": sha(b)})
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--cc", default="cc")
    p.add_argument("--ld", default="ld")
    p.add_argument("--target")
    p.add_argument("--compile-only", action="store_true")
    a = p.parse_args()
    out = a.output.resolve()
    if out.exists() or out == HERE or HERE in out.parents:
        p.error("fresh output outside sources required")
    out.mkdir(parents=True)
    report = {"schema": "ilinux-immutable31af-build-v1", "status": "FAIL", "native": "NOT_RUN", "payload_executed": False, "monitor_calls": 0, "images": []}
    def command(args, name):
        r = subprocess.run(args, cwd=HERE, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
        save(out / (name + ".json"), {"argv": args, "returncode": r.returncode, "stdout": r.stdout, "stderr": r.stderr})
        if r.returncode:
            raise RuntimeError(name + " failed")
        return r.stdout
    try:
        before = bindings()
        save(out / "source-bindings.json", before)
        report["source_bindings_sha256"] = sha((out / "source-bindings.json").read_bytes())
        report["compiler"] = command([a.cc, "--version"], "compiler")
        obj = out / "entry.o"
        command([a.cc] + (["--target=" + a.target] if a.target else []) + ["-ffreestanding", "-c", str(HERE / "entry.S"), "-o", str(obj)], "entry-compile")
        report["object_sha256"] = sha(obj.read_bytes())
        if a.compile_only:
            report["status"] = "COMPILE_PASS_NOT_LINKED"
        else:
            spec = importlib.util.spec_from_file_location("immutable_audit", HERE / "audit.py")
            checker = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(checker)
            report["linker"] = command([a.ld, "--version"], "linker")
            constants = {m.group(1): int(m.group(2), 0) for m in re.finditer(r"^#define (IF31_[A-Z0-9_]+) (0x[0-9a-fA-F]+|[0-9]+)$", (HERE / "layout.h").read_text(), re.M)}
            canonical = None
            for label, base in (("canonical", 0), ("slid", 0x40400000)):
                elf = out / (label + ".elf")
                command([a.ld, "--fatal-warnings", "--no-undefined", "--build-id=none", "-z", "max-page-size=0x4000", "--defsym", f"immutable_image_base={base}", "-T", str(HERE / "image.ld"), str(obj), "-o", str(elf)], label + "-link")
                payload, metadata = checker.audit(elf.read_bytes(), base)
                if canonical is None:
                    canonical = payload
                elif payload != canonical:
                    raise ValueError("payload bytes differ across aligned slide")
                metadata["record_fields"] = constants
                metadata["constants"] = constants
                save(out / (label + "-layout.json"), metadata)
                (out / (label + "-payload.bin")).write_bytes(payload)
                report["images"].append({"label": label, "base": base, "elf_sha256": sha(elf.read_bytes()), "audit": metadata})
            (out / "payload.bin").write_bytes(canonical)
            save(out / "layout.json", report["images"][0]["audit"])
            report["payload_sha256"] = sha(canonical)
            report["slide_bytes_identical"] = True
            report["status"] = "LINK_PASS_NOT_EXECUTED"
        if bindings() != before:
            raise ValueError("sources changed during build")
        report["source_files_unchanged"] = True
    except Exception as error:
        report["error"] = str(error)
        report["status"] = "FAIL"
    save(out / "results.json", report)
    print(json.dumps({"status": report["status"], "results": str(out / "results.json")}))
    return int(report["status"] == "FAIL")

if __name__ == "__main__":
    raise SystemExit(main())
