"""Attempt 28: exact boot042 DT delta and command-only CPU observation gates.

No USB or hardware access here. The shipped module is loaded explicitly with
writes disabled by the native collector; no voltage/frequency request is part
of this attempt. Existing launch profiles retain their disabled-DVFS checks.
"""
import hashlib
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "kernel/experiments/usb-gadget-dt"))
import fdtedit

BASE_SHA = "17c55af9eb39ea799e254335176e9748193237dce3735f59cd286a63ea0a0405"
DT_SHA = "aa9731d1ba8246a9441a85dcbf59bf65cfe82c7a8d33439e9d2cdc40cb0ee725"
IMAGE_SHA = "0b6df39566f12bcd5957e649946125a7bb0f42f31690933dc9896a2565b9b69c"
RECORDS = HERE / "attempt28"
CONTROLLERS = tuple("/soc/performance-controller@%xe20000" % (0x210 + i) for i in range(3))


def prepare_dt(blob):
    if hashlib.sha256(blob).hexdigest() != BASE_SHA:
        raise ValueError("CPU observation requires the exact boot042 base DT")
    tree = fdtedit.parse(blob)
    for i, path in enumerate(CONTROLLERS):
        node = tree.node(path)
        node.delete("status")
        node.set("compatible", b"apple,t6050-cluster-cpufreq\0")
        for j, row in enumerate(tree.node("/opp-table-%d" % i).children):
            row.set("opp-level", struct.pack(">I", j + 2))
    result = fdtedit.encode(tree)
    if hashlib.sha256(result).hexdigest() != DT_SHA:
        raise ValueError("CPU observation DT is not the reviewed candidate")
    return result


def check_tree(tree, reference):
    """Verify the exact controllers, OPPs and surviving CPU associations.

The prepared tree may contain m1n1's private properties; do not serialize it.
Reference bytes are pinned, so a caller cannot supply a permissive contract.
"""
    from fdt import properties, strings
    if hashlib.sha256(reference).hexdigest() != DT_SHA:
        raise ValueError("CPU observation reference DT digest differs")
    expected = properties(reference)
    actual = {p for p, n in tree.items() if any("cluster-cpufreq" in c for c in
              (strings(n["compatible"]) if "compatible" in n else []))}
    if actual != set(CONTROLLERS):
        raise ValueError("CPU controller set differs")
    for path, values in expected.items():
        if path in CONTROLLERS or path.startswith("/opp-table-"):
            if tree.get(path) != values:
                raise ValueError("CPU controller/OPP contract differs: " + path)
    if {p for p in tree if p.startswith("/opp-table-")} != {
            p for p in expected if p.startswith("/opp-table-")}:
        raise ValueError("OPP node set differs")
    for path, cpu in tree.items():
        if not path.startswith("/cpus/cpu@"):
            continue
        for key in ("reg", "compatible", "performance-domains", "operating-points-v2"):
            if cpu.get(key) != expected.get(path, {}).get(key):
                raise ValueError("CPU frequency association differs")
    return set(CONTROLLERS)


def check_payloads(files):
    import json
    record = json.loads((RECORDS / "ramroot-manifest.json").read_text())
    for name, expected in (("Image", IMAGE_SHA), ("t6050-j716c-stage-b.dtb", DT_SHA),
                           ("ramroot.cpio.zst", record["sha256"])):
        if hashlib.sha256(files[name]).hexdigest() != expected:
            raise ValueError("CPU observation payload digest differs: " + name)
