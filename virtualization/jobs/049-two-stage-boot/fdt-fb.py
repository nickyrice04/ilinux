#!/usr/bin/env python3
"""fdt-fb.py IN.dtb OUT.dtb FB_ADDR WIDTH HEIGHT: QEMU's virt device tree as m1n1 presents the M5 to
Linux, for job 049's boot test on the Mac (which has no dtc). The same edits job 045's boot test makes
with dtc: the M5's root compatible and model (so Omarchy's platform detection answers as on the M5), a
reserved no-map region at FB_ADDR and a /chosen simple-framebuffer node there (x2r10g10b10, the
16-inch panel's 3456x2234), which simpledrm drives. A flattened device tree is parsed into nodes,
edited and written again (version 17, strings deduplicated, the memory reservations kept).
Standard library only.
"""
import struct
import sys

BEGIN, END, PROP, NOP, FINISH = 1, 2, 3, 4, 9


class Node:
    def __init__(self, name):
        self.name, self.props, self.children = name, [], []

    def child(self, name):
        for c in self.children:
            if c.name == name:
                return c
        c = Node(name)
        self.children.append(c)
        return c

    def set(self, name, value):
        for i, (n, _) in enumerate(self.props):
            if n == name:
                self.props[i] = (name, value)
                return
        self.props.append((name, value))

    def get(self, name):
        for n, v in self.props:
            if n == name:
                return v
        return None


def parse(blob):
    magic, total, off_struct, off_strings, off_rsv, version, _, _, size_strings, size_struct = struct.unpack_from(">10I", blob)
    if magic != 0xD00DFEED or version < 16 or total > len(blob):
        raise SystemExit("not a flattened device tree")
    rsv, o = [], off_rsv
    while True:
        addr, size = struct.unpack_from(">QQ", blob, o)
        o += 16
        if addr == 0 and size == 0:
            break
        rsv.append((addr, size))
    strings = blob[off_strings:off_strings + size_strings]
    o, end, stack, root = off_struct, off_struct + size_struct, [], None
    while o < end:
        token, = struct.unpack_from(">I", blob, o)
        o += 4
        if token == BEGIN:
            stop = blob.index(b"\0", o)
            node = Node(blob[o:stop].decode())
            o = (stop + 4) & ~3
            if stack:
                stack[-1].children.append(node)
            else:
                root = node
            stack.append(node)
        elif token == END:
            stack.pop()
        elif token == PROP:
            length, nameoff = struct.unpack_from(">II", blob, o)
            o += 8
            name = strings[nameoff:strings.index(b"\0", nameoff)].decode()
            stack[-1].props.append((name, blob[o:o + length]))
            o = (o + length + 3) & ~3
        elif token == NOP:
            continue
        elif token == FINISH:
            break
        else:
            raise SystemExit("unknown FDT token %d" % token)
    return root, rsv, struct.unpack_from(">I", blob, 28)[0]


def serialize(root, rsv, boot_cpuid):
    strings, offsets, body = bytearray(), {}, bytearray()

    def name_offset(name):
        if name not in offsets:
            offsets[name] = len(strings)
            strings.extend(name.encode() + b"\0")
        return offsets[name]

    def emit(node):
        body.extend(struct.pack(">I", BEGIN) + node.name.encode() + b"\0")
        body.extend(b"\0" * (-len(body) % 4))
        for name, value in node.props:
            body.extend(struct.pack(">III", PROP, len(value), name_offset(name)) + value)
            body.extend(b"\0" * (-len(body) % 4))
        for c in node.children:
            emit(c)
        body.extend(struct.pack(">I", END))

    emit(root)
    body.extend(struct.pack(">I", FINISH))
    reserve = b"".join(struct.pack(">QQ", a, s) for a, s in rsv) + struct.pack(">QQ", 0, 0)
    off_rsv = 40
    off_struct = off_rsv + len(reserve)
    off_strings = off_struct + len(body)
    total = off_strings + len(strings)
    header = struct.pack(">10I", 0xD00DFEED, total, off_struct, off_strings, off_rsv, 17, 16,
                         boot_cpuid, len(strings), len(body))
    return header + reserve + bytes(body) + bytes(strings)


def cells(*values):
    return b"".join(struct.pack(">I", v) for v in values)


def strlist(*items):
    return b"".join(s.encode() + b"\0" for s in items)


def main():
    src, dst, addr, width, height = sys.argv[1], sys.argv[2], int(sys.argv[3], 0), int(sys.argv[4]), int(sys.argv[5])
    root, rsv, boot_cpuid = parse(open(src, "rb").read())
    stride = width * 4
    size = stride * height
    phandles = []

    def walk(node):
        for n, v in node.props:
            if n in ("phandle", "linux,phandle"):
                phandles.append(struct.unpack(">I", v)[0])
        for c in node.children:
            walk(c)
    walk(root)
    ph = max(phandles + [0]) + 1
    root.set("compatible", strlist("apple,j716c", "apple,t6050", "apple,arm-platform"))
    root.set("model", strlist("Apple MacBook Pro (16-inch, M5 Max)"))
    rm = root.child("reserved-memory")
    rm.set("#address-cells", cells(2))
    rm.set("#size-cells", cells(2))
    rm.set("ranges", b"")
    fbmem = rm.child("framebuffer@%x" % addr)
    fbmem.set("reg", cells(addr >> 32, addr & 0xFFFFFFFF, 0, 0x2000000))
    fbmem.set("no-map", b"")
    fbmem.set("phandle", cells(ph))
    fb = root.child("chosen").child("framebuffer@%x" % addr)
    fb.set("compatible", strlist("simple-framebuffer"))
    fb.set("reg", cells(addr >> 32, addr & 0xFFFFFFFF, 0, size))
    fb.set("memory-region", cells(ph))
    fb.set("width", cells(width))
    fb.set("height", cells(height))
    fb.set("stride", cells(stride))
    fb.set("format", strlist("x2r10g10b10"))
    fb.set("status", strlist("okay"))
    out = serialize(root, rsv, boot_cpuid)
    open(dst, "wb").write(out)
    again, _, _ = parse(out)   # round trip
    assert again.child("chosen").child("framebuffer@%x" % addr).get("width") == cells(width)
    print("fdt-fb: %s -> %s, %d bytes; framebuffer %dx%d x2r10g10b10 at 0x%x (%d bytes, phandle %d)" % (
        src, dst, len(out), width, height, addr, size, ph))


if __name__ == "__main__":
    main()
