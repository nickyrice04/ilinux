#!/usr/bin/env python3
"""module_sets.py MODDIR KREL OUTDIR IMAGE: boot042's module sets, from `make modules_install`'s tree.

Three sets, each with every module it depends on (modules.dep):
  keyboard  (shipped in the attempt-26 root): apple-rtkit-helper, apple-dockchannel, dockchannel-hid,
            hid-apple;
  trackpad  (kept apart, not in the attempt-26 root): hid-magicmouse;
  storage   (kept apart, not in the attempt-26 root): apple-sart, nvme-core (with the iLinux read-only
            patch, refused unless its read-only mode cannot be turned off), nvme-apple, and nvme (the PCI
            transport, for the VM test only).
OUTDIR gets <set>/<name>.ko (flat copies), <set>/SHA256SUMS, keyboard-root/ (the files the attempt-26
root takes under /usr/lib/modules/KREL: the keyboard set at its tree paths, modules.order for them,
modules.builtin and modules.builtin.modinfo; the root's own depmod makes the index) and manifest.json
(release, vermagic, the Image's SHA-256, per module its path, digest, size, dependencies and OF
aliases). Every module's vermagic must be the Image's. Standard library only.
"""
import hashlib
import json
import shutil
import struct
import sys
from pathlib import Path

SETS = {
    "keyboard": ["apple-rtkit-helper", "apple-dockchannel", "dockchannel-hid", "hid-apple"],
    "trackpad": ["hid-magicmouse"],
    "storage": ["apple-sart", "nvme-core", "nvme-apple", "nvme"],
}


def norm(name):
    return name.replace("-", "_")


def modinfo(path):
    """The .modinfo strings of an ELF64 little-endian module, as a list of (key, value)."""
    data = path.read_bytes()
    if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
        raise ValueError("%s is not an ELF64 little-endian file" % path)
    shoff, = struct.unpack_from("<Q", data, 0x28)
    shentsize, shnum, shstrndx = struct.unpack_from("<HHH", data, 0x3A)
    sections = []
    for i in range(shnum):
        name, _type, _flags, _addr, off, size = struct.unpack_from("<IIQQQQ", data, shoff + i * shentsize)
        sections.append((name, off, size))
    strtab_off = sections[shstrndx][1]
    for name, off, size in sections:
        end = data.index(b"\0", strtab_off + name)
        if data[strtab_off + name:end] == b".modinfo":
            out = []
            for item in data[off:off + size].split(b"\0"):
                if b"=" in item:
                    k, v = item.decode("ascii", "replace").split("=", 1)
                    out.append((k, v))
            return out
    raise ValueError("%s has no .modinfo" % path)


def main(argv):
    if len(argv) != 5:
        raise SystemExit(__doc__.splitlines()[0])
    moddir, krel, outdir, image = Path(argv[1]), argv[2], Path(argv[3]), Path(argv[4])
    image_bytes = image.read_bytes()
    deps, paths = {}, {}
    for line in (moddir / "modules.dep").read_text().splitlines():
        target, _, rest = line.partition(":")
        name = norm(Path(target).name[:-3])
        paths[name] = target
        deps[name] = [norm(Path(d).name[:-3]) for d in rest.split()]

    def closure(names):
        seen, todo = [], [norm(n) for n in names]
        while todo:
            n = todo.pop(0)
            if n in seen:
                continue
            if n not in paths:
                raise SystemExit("module %s is not in modules.dep (not built as a module?)" % n)
            seen.append(n)
            todo.extend(deps[n])
        return seen

    if outdir.exists():
        shutil.rmtree(outdir)
    manifest = {"kernel_release": krel, "image_sha256": hashlib.sha256(image_bytes).hexdigest(), "sets": {}}
    vermagics = set()
    members = {}
    for set_name, wanted in SETS.items():
        mods = closure(wanted)
        members[set_name] = set(mods)
        d = outdir / set_name
        d.mkdir(parents=True)
        rows, sums = [], []
        for n in mods:
            src = moddir / paths[n]
            info = modinfo(src)
            vermagic = [v for k, v in info if k == "vermagic"]
            if len(vermagic) != 1:
                raise SystemExit("%s: no single vermagic" % n)
            vermagics.add(vermagic[0])
            if n == "nvme-core":   # only the build whose read-only mode cannot be turned off
                parm = [v for k, v in info if k == "parm" and v.startswith("ilinux_read_only:")]
                if (len(parm) != 1 or "always on: a load that asks for 0 fails" not in parm[0]
                        or "control build" in parm[0]):
                    raise SystemExit("nvme-core: not the always-on iLinux read-only build: %r" % parm)
            data = src.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            flat = d / (Path(paths[n]).name)
            flat.write_bytes(data)
            sums.append("%s  %s" % (digest, flat.name))
            depends = [d for k, v in info if k == "depends" for d in v.split(",") if d]
            rows.append({"name": n, "path": paths[n], "sha256": digest, "size": len(data),
                         "depends": depends,
                         "of_aliases": sorted(v for k, v in info if k == "alias" and v.startswith("of:"))})
        (d / "SHA256SUMS").write_text("\n".join(sums) + "\n")
        manifest["sets"][set_name] = rows
        print("%s: %s" % (set_name, " ".join(Path(paths[n]).name for n in mods)))
    if members["keyboard"] & (members["storage"] | members["trackpad"]):
        raise SystemExit("the keyboard set shares modules with a set kept apart: %s" %
                         sorted(members["keyboard"] & (members["storage"] | members["trackpad"])))
    if len(vermagics) != 1:
        raise SystemExit("modules disagree on vermagic: %s" % sorted(vermagics))
    vermagic = vermagics.pop()
    if vermagic.encode() + b"\0" not in image_bytes:
        raise SystemExit("vermagic %r is not the Image's" % vermagic)
    manifest["vermagic"] = vermagic

    # The attempt-26 root's tree: the keyboard set and the index sources for its own depmod.
    root = outdir / "keyboard-root" / "usr" / "lib" / "modules" / krel
    root.mkdir(parents=True)
    order = []
    for row in manifest["sets"]["keyboard"]:
        dst = root / row["path"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(moddir / row["path"], dst)
    keep = {row["path"] for row in manifest["sets"]["keyboard"]}
    for line in (moddir / "modules.order").read_text().splitlines():
        if line.strip() in keep or line.strip().replace("kernel/", "", 1) in keep:
            order.append(line)
    (root / "modules.order").write_text("\n".join(order) + "\n")
    for f in ("modules.builtin", "modules.builtin.modinfo"):
        shutil.copyfile(moddir / f, root / f)
    (outdir / "keyboard-root" / "SHA256SUMS").write_text("".join(
        "%s  usr/lib/modules/%s/%s\n" % (row["sha256"], krel, row["path"]) for row in manifest["sets"]["keyboard"]))
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print("vermagic %s (in the Image); keyboard-root: %d modules, modules.order %d lines" % (
        vermagic, len(keep), len(order)))


if __name__ == "__main__":
    main(sys.argv)
