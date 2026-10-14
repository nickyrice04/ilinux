"""Populate only the diagnostic Image's framebuffer descriptor in target RAM.

No framebuffer address is guessed, logged or persisted. No code is patched.
"""
import struct
from fdt import check_framebuffer

MAGIC = b"ILINUX-FB024-V1\0"


def descriptor_offset(image):
    start = image.find(MAGIC)
    if start < 0 or image.find(MAGIC, start + 1) >= 0 or start % 8:
        raise ValueError("missing, duplicate or unaligned early framebuffer descriptor")
    offset = start + len(MAGIC)
    if image[offset:offset + 16] != bytes(16):
        raise ValueError("early framebuffer descriptor is not zero-initialized")
    return offset


def plan(image, tree):
    offset = descriptor_offset(image)
    check_framebuffer(tree, prepared=True)
    frames = [n for p, n in tree.items() if p.startswith("/chosen/framebuffer")]
    if len(frames) != 1:
        raise ValueError("ambiguous early framebuffer")
    node = frames[0]
    base, size = struct.unpack(">QQ", node["reg"])
    width, height, stride = [struct.unpack(">I", node[k])[0]
                             for k in ("width", "height", "stride")]
    if (node["format"] not in (b"x8r8g8b8\0", b"x2r10g10b10\0") or
            base % 4 or not 320 <= width <= 8192 or not 200 <= height <= 8192 or
            stride % 4 or not width * 4 <= stride <= 32768 or
            not stride * height <= size <= 256 * 1024**2 or base + size >= 1 << 64):
        raise ValueError("framebuffer outside reviewed early-console limits")
    return offset, struct.pack("<QQ", base, stride)


def apply(iface, kernel, descriptor):
    offset, data = descriptor
    address = kernel + offset
    if iface.readmem(address, 16) != bytes(16):
        raise ValueError("live early framebuffer descriptor differs; fresh boot required")
    iface.writemem(address, data)
    if iface.readmem(address, 16) != data:
        raise ValueError("early framebuffer descriptor readback failed; fresh boot required")
