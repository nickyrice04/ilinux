#!/usr/bin/env python3
"""fb2png.py RAW WIDTH HEIGHT STRIDE FORMAT OUT.png [SCALE]: convert a raw framebuffer dump
(QEMU 'pmemsave' of the simple-framebuffer region) to an 8-bit RGB PNG. FORMAT is the
simple-framebuffer format string, x2r10g10b10 or x8r8g8b8 (little-endian words). SCALE=2
keeps every second pixel in both directions. Standard library only.
"""
import array
import struct
import sys
import zlib


def main():
    raw, width, height, stride, fmt, out = sys.argv[1:7]
    width, height, stride = int(width), int(height), int(stride)
    scale = int(sys.argv[7]) if len(sys.argv) > 7 else 1
    data = open(raw, "rb").read()
    rows = []
    for y in range(0, height, scale):
        words = array.array("I", data[y * stride:y * stride + width * 4])
        if sys.byteorder != "little":
            words.byteswap()
        words = words[::scale]
        if fmt == "x2r10g10b10":
            rgb = bytes(c for v in words for c in ((v >> 22) & 0xFF, (v >> 12) & 0xFF, (v >> 2) & 0xFF))
        elif fmt == "x8r8g8b8":
            rgb = bytes(c for v in words for c in ((v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF))
        else:
            raise SystemExit(f"unsupported format {fmt}")
        rows.append(b"\0" + rgb)
    w, h = len(rows[0]) // 3, len(rows)

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(b"".join(rows), 6)) + chunk(b"IEND", b"")
    with open(out, "wb") as f:
        f.write(png)


if __name__ == "__main__":
    main()
