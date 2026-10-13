#!/usr/bin/env python3
"""Extract selected static operational ACIPC facts. Never opens a device.

Only Alpha/Beta plists are accepted. This is not a hardware descriptor parser.
No raw plist, boot-stage, identity, log, firmware or authentication fields are
retained. A source digest identifies software content, not a physical device.
"""

import argparse
import hashlib
import json
import pathlib
import plistlib

ROOT = pathlib.Path("/System/DriverKit/System/Library/PrivateFrameworks/AirshipDK.framework")
MAX_INPUT = 256 * 1024
U64_MAX = (1 << 64) - 1
RINGS = {
    "CentauriAlpha": (
        "cmd-request", "cmd-response", "events", "management",
        "data-rx", "data-rx-llw", "data-tx", "monitor",
    ),
    "CentauriBeta": (
        "hci-tx", "hci-rx", "acl-tx", "acl-rx", "sco-tx", "sco-rx",
        "le-tx", "le-rx", "lea-tx", "lea-rx", "lla-tx", "lmp-rx",
        "tsi-tx", "tsi-rx",
    ),
}
DOORBELLS = {
    "CentauriAlpha": ("ringdb-control", "ringdb-data-rx", "ringdb-data-tx"),
    "CentauriBeta": ("ringdb",),
}
INTERRUPTS = {
    "CentauriAlpha": ("main", "control", "data-tx", "data-rx", "data-rx-llw"),
    "CentauriBeta": ("main",),
}
REGISTERS = (
    "context_info_address_hi", "context_info_address_lo", "ipc_control",
    "ipc_status", "sleep_control", "window_base_hi", "window_base_lo",
    "window_size",
)
RING_INTS = (
    "id", "index_array_vector", "ring_size", "nominal_transfer_size",
    "transfer_footer_size", "completion_footer_size", "footer_size",
)
RING_BOOLS = ("in_place", "out_of_order", "optimized_completion")


def integer(value, field, positive=False):
    if type(value) is not int or value < int(positive) or value > U64_MAX:
        raise ValueError(f"invalid integer field: {field}")
    return value


def obj(value, field):
    if type(value) is not dict:
        raise ValueError(f"invalid object field: {field}")
    return value


def numeric_fields(source, fields, *, positive=()):
    source = obj(source, "numeric record")
    return {key: integer(source[key], key, key in positive)
            for key in fields if key in source}


def boolean_fields(source, fields):
    out = {}
    for key in fields:
        if key in source:
            if type(source[key]) is not bool:
                raise ValueError(f"invalid boolean field: {key}")
            out[key] = source[key]
    return out


def reference(source, names, field):
    source = obj(source, field)
    name = source.get("name")
    if type(name) is not str or name not in names:
        raise ValueError(f"unrecognized reference: {field}")
    return {"name": name, **numeric_fields(source, ("selector",))}


def register(source):
    source = obj(source, "register")
    if "bank" not in source or "offset" not in source:
        raise ValueError("register lacks bank/offset")
    return numeric_fields(source, ("bank", "offset", "width"), positive=("width",))


def ring(source, role):
    source = obj(source, "ring")
    for required in ("id", "index_array_vector", "ring_size"):
        if required not in source:
            raise ValueError(f"ring lacks {required}")
    if source.get("exec_stage") != "os":
        raise ValueError("non-operational ring stage")
    out = numeric_fields(source, RING_INTS, positive=("ring_size",))
    out.update(boolean_fields(source, RING_BOOLS))
    if "doorbell" in source:
        out["doorbell"] = reference(source["doorbell"], DOORBELLS[role], "doorbell")
    if "multi" in source:
        multi = obj(source["multi"], "multi")
        out["multi"] = numeric_fields(multi, ("count",), positive=("count",))
        out["multi"].update(boolean_fields(multi, ("doorbell_stride", "interrupt_stride")))
    if "doorbell_moderation" in source:
        out["doorbell_moderation"] = numeric_fields(
            source["doorbell_moderation"], ("interval_usec", "leeway_usec"))
    for key, allowed in (("interrupt", INTERRUPTS[role]), ("completion_ring", RINGS[role])):
        if key in source:
            if type(source[key]) is not str or source[key] not in allowed:
                raise ValueError(f"unrecognized ring {key}")
            out[key] = source[key]
    return out


def normalize(document, role):
    document = obj(document, "document")
    if role not in RINGS or document.get("role") != role:
        raise ValueError("unsupported or mismatched role")
    if document.get("protocol") != "acipc" or document.get("chipset") != "t2026":
        raise ValueError("unsupported protocol/chipset")
    stage = obj(obj(document.get("main_ipc_stages"), "main_ipc_stages").get("os"), "os")
    out_stage = numeric_fields(stage, ("version", "tr_index_count", "cr_index_count"),
                               positive=("tr_index_count", "cr_index_count"))
    if len(out_stage) != 3:
        raise ValueError("missing version/index-count field")
    registers = obj(stage.get("registers"), "registers")
    out_stage["registers"] = {name: register(registers[name])
                              for name in REGISTERS if name in registers}
    for name in ("mtr", "mcr"):
        if name in stage:
            s = obj(stage[name], name)
            out_stage[name] = numeric_fields(s, ("ring_size", "footer_size"),
                                              positive=("ring_size",))
            out_stage[name].update(boolean_fields(s, ("in_place",)))
    out = {"role": role, "chipset": "t2026", "protocol": "acipc", "os_stage": out_stage}
    for category, limit in (("transfer_rings", "tr_index_count"),
                            ("completion_rings", "cr_index_count")):
        source = obj(document.get(category, {}), category)
        out[category] = {name: ring(source[name], role)
                         for name in RINGS[role] if name in source}
        for value in out[category].values():
            # Check only the explicit vector; contiguity of multi vectors is
            # an unverified interpretation and intentionally not assumed.
            if value["index_array_vector"] >= out_stage[limit]:
                raise ValueError("ring vector outside declared index array")
    out["doorbells"] = {}
    doorbells = obj(document.get("doorbells"), "doorbells")
    for name in DOORBELLS[role]:
        if name not in doorbells:
            continue
        source = obj(doorbells[name], name)
        if source.get("ipc_stage") != "os" or source.get("mode") not in ("index", "shared_constant"):
            raise ValueError("unsupported operational doorbell")
        d = {"mode": source["mode"], "register": register(source.get("register")),
             **numeric_fields(source, ("vector", "value", "min_interval_usec"))}
        if "multi" in source:
            d["multi"] = numeric_fields(source["multi"], ("count",), positive=("count",))
        out["doorbells"][name] = d
    for category in ("transfer_rings", "completion_rings"):
        for value in out[category].values():
            if "doorbell" not in value:
                continue
            ref = value["doorbell"]
            if ref["name"] not in out["doorbells"]:
                raise ValueError("referenced doorbell missing")
            count = out["doorbells"][ref["name"]].get("multi", {}).get("count", 1)
            if ref.get("selector", 0) >= count:
                raise ValueError("doorbell selector outside declared count")
    return out


def read_source(path, role):
    path = pathlib.Path(path)
    with path.open("rb") as file:
        data = file.read(MAX_INPUT + 1)
    if len(data) > MAX_INPUT:
        raise ValueError("input exceeds static-config size limit")
    document = plistlib.loads(data)
    return {"source": {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(),
                        "bytes": len(data)},
            "operational_facts": normalize(document, role)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alpha", type=pathlib.Path, default=ROOT / "t2026-CentauriAlpha.plist")
    parser.add_argument("--beta", type=pathlib.Path, default=ROOT / "t2026-CentauriBeta.plist")
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    result = {"format_version": 1, "evidence": "observed_static_configuration",
              "hardware_semantics": "unvalidated",
              "sources": [read_source(args.alpha, "CentauriAlpha"),
                          read_source(args.beta, "CentauriBeta")]}
    # Exclusive output prevents accidental replacement of prior evidence.
    with args.output.open("x") as file:
        json.dump(result, file, indent=2, sort_keys=True)
        file.write("\n")
    print("Extracted allowlisted Alpha/Beta operational configuration; no hardware access")


if __name__ == "__main__":
    main()
