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


def check_framebuffer(tree, prepared=False):
    chosen = tree.get("/chosen", {})
    two = struct.pack(">I", 2)
    if any(chosen.get(k) != two for k in ("#address-cells", "#size-cells")) or chosen.get("ranges") != b"":
        raise ValueError("boot framebuffer needs chosen 64-bit cells and identity ranges")
    frames = [(p, n) for p, n in tree.items() if "simple-framebuffer" in
              (strings(n["compatible"]) if "compatible" in n else [])]
    if len(frames) != 1 or frames[0][0].rsplit("/", 1)[0] != "/chosen":
        raise ValueError("expected one boot framebuffer under chosen")
    path, node = frames[0]
    if not prepared:
        if path not in ("/chosen/framebuffer", "/chosen/framebuffer@0"):
            raise ValueError("m1n1 framebuffer placeholder has unexpected name")
        if node.get("status") != b"disabled\0" or node.get("reg") != bytes(16):
            raise ValueError("framebuffer placeholder must be disabled with zero reg")
        return
    if node.get("status", b"okay\0") not in (b"okay\0", b"ok\0"):
        raise ValueError("boot framebuffer still disabled after m1n1 fixup")
    if len(node.get("reg", b"")) != 16:
        raise ValueError("boot framebuffer reg must contain one 64-bit range")
    base, size = struct.unpack(">QQ", node["reg"])
    dims = []
    for key in ("width", "height", "stride"):
        value = node.get(key, b"")
        if len(value) != 4:
            raise ValueError("boot framebuffer geometry missing or malformed")
        dims.append(struct.unpack(">I", value)[0])
    width, height, stride = dims
    bpp = {b"x8r8g8b8\0": 4, b"x2r10g10b10\0": 4, b"r5g6b5\0": 2}.get(node.get("format"))
    if not bpp or not all((base, size, width, height, stride)) or stride < width * bpp or size < stride * height or base + size > 1 << 64:
        raise ValueError("boot framebuffer geometry/format/range invalid")


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
    check_framebuffer(tree, prepared=prepared)
    if prepared:
        cpus = [n for p, n in tree.items() if p.startswith("/cpus/cpu@")
                and n.get("status", b"okay\0") in (b"okay\0", b"ok\0")]
        if len(cpus) != 1:
            raise ValueError("prepared DT must expose exactly one CPU")
    return tree
