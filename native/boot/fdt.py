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
    check_hardware(tree)
    return tree


def check_hardware(tree):
    """Validate this board's CPU family and AIC/timer route, not just its name.

    These are public/sanitized layout facts from the packaged J716c tree.
    This does not claim that an interrupt has actually been delivered.
    """
    def cells(*values):
        return struct.pack('>' + 'I' * len(values), *values)

    def enabled(path):
        while path:
            if tree.get(path, {}).get('status', b'okay\0') not in (b'okay\0', b'ok\0'):
                return False
            path = path.rsplit('/', 1)[0]
        return True

    if 'apple,t6050' not in strings(tree['/'].get('compatible', b'')):
        raise ValueError('DT chip is not t6050')
    aics = [(p, n) for p, n in tree.items() if 'apple,t6050-aic3' in
            (strings(n['compatible']) if 'compatible' in n else [])]
    if len(aics) != 1:
        raise ValueError('expected one t6050 AIC3')
    path, aic = aics[0]
    if not enabled(path) or aic.get('interrupt-controller') != b'' or aic.get('#interrupt-cells') != cells(3):
        raise ValueError('AIC3 interrupt controller disabled or malformed')
    if aic.get('reg') != struct.pack('>4Q', 0x280400000, 0x1cc000, 0x280440000, 0x4000):
        raise ValueError('AIC3 core/event layout differs from this board')
    parent = tree.get(path.rsplit('/', 1)[0], {})
    if parent.get('#address-cells') != cells(2) or parent.get('#size-cells') != cells(2) or parent.get('ranges') != b'':
        raise ValueError('AIC3 parent address translation differs')
    phandle = aic.get('phandle')
    if not phandle or len(phandle) != 4 or phandle in (cells(0), cells(0xffffffff)) or sum(n.get('phandle') == phandle for n in tree.values()) != 1:
        raise ValueError('AIC3 phandle missing or ambiguous')
    timers = [(p, n) for p, n in tree.items() if 'arm,armv8-timer' in
              (strings(n['compatible']) if 'compatible' in n else [])]
    if len(timers) != 1 or not enabled(timers[0][0]):
        raise ValueError('expected one enabled architectural timer')
    timer = timers[0][1]
    if timer.get('interrupt-parent') != phandle:
        raise ValueError('timer is not routed to t6050 AIC3')
    if timer.get('interrupt-names') != b'phys\0virt\0hyp-phys\0hyp-virt\0' or timer.get('interrupts') != cells(1, 2, 4, 1, 3, 4, 1, 0, 4, 1, 1, 4):
        raise ValueError('timer host/guest FIQ routes differ from this board')
    cpus = tree.get('/cpus', {})
    if cpus.get('#address-cells') != cells(2) or cpus.get('#size-cells') != cells(0):
        raise ValueError('CPU address encoding differs')
    seen = set()
    for path, cpu in tree.items():
        if not path.startswith('/cpus/cpu@'):
            continue
        reg = cpu.get('reg', b'')
        if cpu.get('device_type') != b'cpu\0' or len(reg) != 8:
            raise ValueError('CPU identity missing or malformed')
        mpidr, = struct.unpack('>Q', reg)
        family = ('apple,sotra-m' if mpidr in {*range(0x40000, 0x40006), *range(0x40100, 0x40106)}
                  else 'apple,sotra-p' if mpidr in range(0x10200, 0x10206) else None)
        if not family or mpidr in seen or family not in strings(cpu.get('compatible', b'')):
            raise ValueError('CPU MPIDR/family is not this J716c topology')
        seen.add(mpidr)
    if not seen:
        raise ValueError('CPU topology missing')
