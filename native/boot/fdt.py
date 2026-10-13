"""Small, bounded read-only flattened-device-tree decoder (no dependencies)."""
import struct


def properties(blob):
    if len(blob) < 40:
        raise ValueError("short FDT")
    magic, total, off, strings, _, version, _, _, strsize, size = struct.unpack_from(
        ">10I", blob)
    if magic != 0xD00DFEED or version != 17 or total != len(blob):
        raise ValueError("invalid FDT header")
    end = off + size
    if off < 40 or strings < 40 or end > total or strings + strsize > total:
        raise ValueError("FDT block out of bounds")
    names = blob[strings:strings + strsize]
    stack, result = [], {}
    while off + 4 <= end:
        token, = struct.unpack_from(">I", blob, off)
        off += 4
        if token == 1:
            stop = blob.find(b"\0", off, end)
            if stop < 0:
                raise ValueError("unterminated node")
            name = blob[off:stop].decode("ascii")
            if "/" in name or (not stack and name):
                raise ValueError("invalid node name")
            stack.append(name)
            path = "/" + "/".join(stack[1:])
            if path in result:
                raise ValueError("duplicate node")
            result[path] = {}
            off = (stop + 4) & ~3
        elif token == 2:
            if not stack:
                raise ValueError("unbalanced node")
            stack.pop()
        elif token == 3:
            if not stack or off + 8 > end:
                raise ValueError("invalid property")
            length, nameoff = struct.unpack_from(">2I", blob, off)
            off += 8
            stop = names.find(b"\0", nameoff)
            if stop < 0 or off + length > end:
                raise ValueError("property out of bounds")
            name = names[nameoff:stop].decode("ascii")
            node = result["/" + "/".join(stack[1:])]
            if name in node:
                raise ValueError("duplicate property")
            node[name] = blob[off:off + length]
            off = (off + length + 3) & ~3
        elif token == 4:
            continue
        elif token == 9:
            if stack or "/" not in result:
                raise ValueError("incomplete FDT")
            return result
        else:
            raise ValueError("unknown FDT token")
    raise ValueError("missing FDT end")


def strings(value):
    if not value or not value.endswith(b"\0"):
        raise ValueError("invalid FDT string")
    return value[:-1].decode("ascii").split("\0")


def check_stage_b(blob, prepared=False):
    tree = properties(blob)
    if "apple,j716c" not in strings(tree["/"].get("compatible", b"")):
        raise ValueError("DT is not J716c")
    disabled = []
    for path, node in tree.items():
        comps = strings(node["compatible"]) if "compatible" in node else []
        if any("nvme" in c or "cluster-cpufreq" in c for c in comps):
            if node.get("status") != b"disabled\0":
                raise ValueError("storage or cpufreq enabled: " + path)
            disabled.append(path)
    if len(disabled) != 4:
        raise ValueError("expected NVMe plus three disabled cpufreq controllers")
    if prepared:
        cpus = [n for p, n in tree.items() if p.startswith("/cpus/cpu@")
                and n.get("status", b"okay\0") in (b"okay\0", b"ok\0")]
        if len(cpus) != 1:
            raise ValueError("prepared DT must expose exactly one CPU")
        frames = [n for n in tree.values() if b"simple-framebuffer\0" in
                  n.get("compatible", b"") and n.get("status", b"okay\0") in
                  (b"okay\0", b"ok\0")]
        if not frames:
            raise ValueError("no enabled boot framebuffer; observation path absent")
    return tree
