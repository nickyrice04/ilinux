#!/usr/bin/env python3
"""Test original ordered registration preparation; no monitor or device calls."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import sys

# Importing the frozen original ELF helper must not create a cache beside it.
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OWN = ("registration.c", "registration.h", "test_registration.c", "run.py", "README.md")
FROZEN = {
    "kernel/experiments/sptm31z-adapter/entry.c": "432c34367b59ce404abf95f9c82ae4ac4ef0315376711080920a732ed7e17982",
    "kernel/experiments/sptm31z-adapter/entry.h": "9d33e198ed5bbb89b84b28d4c6976f5a9a03f8d214536f05707bb5ddb6b5337c",
    "kernel/experiments/sptm31z-adapter/memory.c": "352bed8641220c2846b269bb4ad52331d22d50f170413a688f8508bf5f2e5d2c",
    "kernel/experiments/sptm31z-adapter/memory.h": "b249bb1f11543fb9abbef7ba6be99efcbf32fb7a47cd582f2f95b12e4351c434",
    "kernel/experiments/sptm31z-adapter/run.py": "89b235a13b7c0614c4fb34a4ff26d77cafa205eb0632498956059f75018150bc",
    "hardware/adt/adt-sanitized.json": "6f143434d2f05310067559f8fa3836ae564dd9934ebc5912660f2a9f5a8a73af",
    "native/boot/attempt31g/topology-observation.json": "b055f570f79c6b423fb917afcd73a2c9a87aded2cf6057f9dc708048eae2db42",
}
FLAGS = ["-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic"]
MARKER = "SPTM31AA_REGISTRATION_PASS groups=11 permutations=120 duplicate_cases=56 project_cpus=18 native=NOT_DEPLOYABLE"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def fixture(pinned: dict[str, bytes], output: Path) -> dict:
    """Extract only whitelisted, already public topology data in original order."""
    nodes: list[dict] = []

    def walk(node: dict) -> None:
        path = node["path"]
        if path.startswith("/Root/device-tree/cpus/cpu"):
            nodes.append(node)
        for child in node.get("children", []):
            walk(child)

    walk(json.loads(pinned["hardware/adt/adt-sanitized.json"]))
    observation = json.loads(pinned["native/boot/attempt31g/topology-observation.json"])
    require(observation["read_only"] is True and observation["edt_property_ver"] == 2,
            "unexpected topology observation provenance")
    observed = observation["topology"]
    require(len(nodes) == len(observed) == 18, "expected pinned18-CPU topology")
    records = []
    boot = None
    for index, (node, check) in enumerate(zip(nodes, observed)):
        values = node["values"]
        source_id = values["cpu-id"]
        require(type(source_id) is int and 0 <= source_id <= 0xffffffff,
                "invalid source CPU label")
        require(node["path"] == "/Root/device-tree/cpus/cpu" + str(source_id),
                "source CPU path mismatch")
        require(values["logical-cpu-id"] == source_id, "unexpected source logical label")
        reg = values["reg"]
        require(len(reg) == 1 and set(reg[0]) == {"addr", "size"}, "unexpected ADT reg shape")
        affinity = int(reg[0]["addr"], 16)
        require(int(reg[0]["size"], 16) == 0 and 0 <= affinity <= 0xffffffff,
                "invalid ADT affinity record")
        require(check["cpu-id"] == source_id and check["reg"] == affinity,
                "independent topology observation mismatch")
        core_class = values["cluster-type"]
        require(core_class in (["M"], ["P"]), "unqualified source core-class label")
        state = values["state"]
        require(state in (["running"], ["waiting"]), "unexpected source CPU state")
        record = {"source_cpu_id": source_id, "source_class": ord(core_class[0]),
                  "adt_reg": affinity}
        records.append(record)
        if state == ["running"]:
            require(boot is None and index == 0, "boot CPU is not uniquely first in source")
            boot = {"source_cpu_id": source_id, "adt_reg": affinity}
    require(boot is not None, "source has no boot CPU")
    require(len({row["source_cpu_id"] for row in records}) == 18 and
            len({row["adt_reg"] for row in records}) == 18, "duplicate source topology")
    header = ["/* Generated synthetic-test input from hash-pinned public topology. */",
              "#define PROJECT_CPU_COUNT 18u",
              "static const struct sptm31aa_cpu_record project_cpus[PROJECT_CPU_COUNT] = {"]
    for row in records:
        header.append("    {%du, %du, UINT64_C(0x%x)}," % (
            row["source_cpu_id"], row["source_class"], row["adt_reg"]))
    header.extend(["};", "static const struct sptm31aa_boot_identity project_boot = {%du, UINT64_C(0x%x)};" % (
        boot["source_cpu_id"], boot["adt_reg"]), ""])
    generated = "\n".join(header).encode("ascii")
    (output / "topology_fixture.h").write_bytes(generated)
    result = {"source": "pinned_ADT_reg_in_source_order", "records": records, "boot": boot,
              "generated_header_sha256": digest(generated), "native_binding_proved": False}
    write_json(output / "fixture.json", result)
    return result


def execute(command: list[str], output: Path, label: str) -> dict:
    done = subprocess.run(command, cwd=HERE, capture_output=True, text=True, check=False, timeout=60)
    record = {"command": command, "returncode": done.returncode, "stdout": done.stdout, "stderr": done.stderr}
    write_json(output / (label + ".json"), record)
    if done.returncode:
        raise RuntimeError(f"{label} failed: exit{done.returncode}; inspect its log")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="fresh result directory; host uses ignored build/")
    parser.add_argument("--cc", default="cc", help="single compiler executable")
    parser.add_argument("--sanitize", action="store_true")
    parser.add_argument("--freestanding", action="store_true")
    parser.add_argument("--clang", default="clang")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or output == HERE or HERE in output.parents:
        parser.error("output must be nonexistent and outside the source directory")
    output.mkdir(parents=True, exist_ok=False)
    report = {"schema": 1, "status": "FAIL", "native": "NOT_DEPLOYABLE",
              "host": platform.platform(), "expected_unique_c_groups": 11,
              "unique_c_groups": 0, "tests": [],
              "freestanding": {"requested": args.freestanding, "linked": False, "executed": False}}
    try:
        bindings = []
        pinned = {}
        paths = [HERE / name for name in OWN] + [ROOT / name for name in FROZEN]
        for path in paths:
            relative = str(path.relative_to(ROOT))
            require(not path.is_symlink(), "input must not be a symlink: " + relative)
            raw = path.read_bytes()
            actual = digest(raw)
            if relative in FROZEN:
                require(actual == FROZEN[relative], "frozen source mismatch: " + relative)
                pinned[relative] = raw
            bindings.append({"file": relative, "bytes": len(raw), "sha256": actual})
        write_json(output / "source-bindings.json", bindings)
        report["source_bindings_sha256"] = digest((output / "source-bindings.json").read_bytes())
        report["fixture"] = fixture(pinned, output)
        report["compiler"] = execute([args.cc, "--version"], output, "compiler")["stdout"]
        variants = [("optimized", ["-O2"])]
        if args.sanitize:
            variants.append(("sanitized", ["-O1", "-g", "-fsanitize=address,undefined",
                "-fno-omit-frame-pointer", "-fno-sanitize-recover=all"]))
        sources = ["registration.c", "test_registration.c", "../sptm31z-adapter/entry.c",
                   "../sptm31z-adapter/memory.c"]
        for variant, flags in variants:
            executable = output / ("registration-" + variant)
            execute([args.cc, *FLAGS, *flags, "-I", str(output), *sources, "-o", str(executable)],
                    output, variant + "-compile")
            run = execute([str(executable)], output, variant + "-run")
            require(run["stdout"].strip() == MARKER and not run["stderr"], "unexpected test output")
            report["tests"].append({"variant": variant, "groups": 11, "marker": MARKER, "status": "PASS"})
            report["unique_c_groups"] = 11
        if args.freestanding:
            # Reuse only the original, hash-verified31Z bounded ELF inspector.
            spec = importlib.util.spec_from_file_location("_frozen31z_runner", ROOT / "kernel/experiments/sptm31z-adapter/run.py")
            require(spec is not None and spec.loader is not None, "cannot load frozen ELF inspector")
            checker = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(checker)
            report["freestanding"]["compiler"] = execute([args.clang, "--version"], output, "cross-compiler")["stdout"]
            obj = output / "registration-aarch64.o"
            execute([args.clang, *FLAGS, "--target=aarch64-none-elf", "-ffreestanding",
                "-fno-stack-protector", "-O2", "-c", "registration.c", "-o", str(obj)], output, "cross-compile")
            try:
                symbols = checker.undefined_elf_symbols(obj)
            except (ValueError, UnicodeError) as error:
                report["freestanding"]["symbol_check"] = "UNSUPPORTED_OR_INVALID"
                raise ValueError("ELF inspection refused: " + str(error)) from error
            report["freestanding"].update({"symbol_check": "PASS", "object_sha256": digest(obj.read_bytes()),
                                          "undefined_symbols": symbols})
        for binding in bindings:
            require(digest((ROOT / binding["file"]).read_bytes()) == binding["sha256"],
                    "source changed during run: " + binding["file"])
        report["status"] = "PASS"
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        report["error"] = str(error)
    write_json(output / "results.json", report)
    print(json.dumps({"status": report["status"], "unique_c_groups": report["unique_c_groups"],
                      "native": report["native"], "results": str(output / "results.json")}, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
