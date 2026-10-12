#!/usr/bin/env python3
"""Convert a binary PPM (P6, from QEMU 'screendump') to PNG; stdlib only."""
import struct, sys, zlib

def read_ppm(path):
    data = open(path, "rb").read()
    tokens, i = [], 0
    while len(tokens) < 4:
        while data[i:i+1].isspace(): i += 1
        if data[i:i+1] == b"#":
            while data[i:i+1] not in (b"\n", b""): i += 1
            continue
        j = i
        while not data[j:j+1].isspace(): j += 1
        tokens.append(data[i:j]); i = j
    i += 1
    assert tokens[0] == b"P6" and int(tokens[3]) == 255
    return int(tokens[1]), int(tokens[2]), data[i:]

def write_png(path, w, h, rgb):
    raw = b"".join(b"\x00" + rgb[y*w*3:(y+1)*w*3] for y in range(h))
    def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    open(path, "wb").write(png)

if __name__ == "__main__":
    w, h, rgb = read_ppm(sys.argv[1]); write_png(sys.argv[2], w, h, rgb); print(f"{w}x{h} -> {sys.argv[2]}")
