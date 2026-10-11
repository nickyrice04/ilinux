#!/usr/bin/env python3
"""Extract IOKit matching personalities from macOS kext Info.plists (read-only)
and join them with the sanitized ADT compatibles of this machine.

Output TSV columns: adt_compatible, adt_nodes, kext_bundle, io_class, provider
— i.e. which Apple driver claims each device-tree compatible string.  Only
plist metadata is read; no kext code is touched (on Apple Silicon the kext
binaries live in the sealed boot kernel collection, not on disk).

Usage: kext_personalities.py ADT_NODES_TSV OUT_TSV
"""
import glob
import os
import plistlib
import sys


def personalities():
    plists = glob.glob("/System/Library/Extensions/*.kext/Contents/Info.plist")
    plists += glob.glob("/System/Library/Extensions/*.kext/Contents/PlugIns/*.kext/Contents/Info.plist")
    for p in plists:
        try:
            d = plistlib.load(open(p, "rb"))
        except Exception:
            continue
        bundle = d.get("CFBundleIdentifier", os.path.basename(os.path.dirname(os.path.dirname(p))))
        for _, pers in (d.get("IOKitPersonalities") or {}).items():
            if not isinstance(pers, dict):
                continue
            names = pers.get("IONameMatch") or pers.get("IOCompatibilityMatch") or []
            if isinstance(names, str):
                names = [names]
            for n in names:
                yield n, bundle, pers.get("IOClass", ""), pers.get("IOProviderClass", "")


def main():
    adt_tsv, out = sys.argv[1], sys.argv[2]
    compat_nodes = {}
    for line in open(adt_tsv).read().splitlines()[1:]:
        cols = line.split("\t")
        for c in filter(None, cols[1].split(";")):
            compat_nodes.setdefault(c, []).append(cols[0].split("/")[-1])
    rows = []
    for name, bundle, cls, prov in personalities():
        if name in compat_nodes:
            rows.append((name, ",".join(sorted(set(compat_nodes[name])))[:120], bundle, cls, prov))
    rows.sort()
    with open(out, "w") as f:
        f.write("adt_compatible\tadt_nodes\tkext_bundle\tio_class\tprovider\n")
        for r in rows:
            f.write("\t".join(r) + "\n")
    print("matched personalities:", len(rows), "distinct compatibles:",
          len({r[0] for r in rows}), "of", len(compat_nodes), file=sys.stderr)


if __name__ == "__main__":
    main()
