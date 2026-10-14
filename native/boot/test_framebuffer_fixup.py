#!/usr/bin/env python3
"""Linux-only integration: compile pinned dt_set_fb verbatim, use synthetic video.

Generated third-party C stays under ignored out/. No real ADT/hardware is read.
This tests the DT contract, not physical display operation or Linux execution.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fdt import properties, check_stage_b, check_framebuffer

PIN = "57a9339ffd1876e78297b17d34dece8cff8fa1ba"

PREAMBLE = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libfdt.h>
typedef uint64_t u64;
static void *dt;
static struct { struct { u64 base, width, height, stride, depth; } video; } cur_boot_args;
#define bail(...) do { fprintf(stderr, __VA_ARGS__); return -1; } while (0)
static void get_notchless_fb(u64 *base, u64 *height)
{
    /* Synthetic notch crop; no device data or actual display routine. */
    *base = cur_boot_args.video.base + 16 * cur_boot_args.video.stride;
    *height = cur_boot_args.video.height - 16;
}
'''

MAIN = r'''
int main(int argc, char **argv)
{
    if (argc != 5) return 2;
    FILE *in = fopen(argv[1], "rb");
    if (!in) return 3;
    unsigned char source[262144];
    size_t count = fread(source, 1, sizeof(source), in);
    fclose(in);
    if (count < sizeof(struct fdt_header) || fdt_check_header(source)) return 4;
    dt = calloc(1, 524288);
    if (!dt || fdt_open_into(source, dt, 524288)) return 5;
    unsigned depth = strtoul(argv[3], NULL, 0);
    cur_boot_args.video.base = strtoull(argv[4], NULL, 0);
    cur_boot_args.video.width = 640;
    cur_boot_args.video.height = 480;
    cur_boot_args.video.stride = 640 * (depth == 16 ? 2 : 4);
    cur_boot_args.video.depth = depth;
    if (dt_set_fb() || fdt_pack(dt)) return 6;
    FILE *out = fopen(argv[2], "wb");
    if (!out) return 7;
    size_t size = fdt_totalsize(dt);
    int ok = fwrite(dt, 1, size, out) == size;
    fclose(out);
    free(dt);
    return ok ? 0 : 8;
}
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("m1n1", "baseline", "corrected", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    if sys.platform != "linux":
        p.error("run third-party integration only in the isolated Linux VM")
    pin = subprocess.check_output(["git", "-C", str(a.m1n1), "rev-parse", "HEAD"], text=True).strip()
    if pin != PIN:
        raise ValueError("m1n1 pin mismatch")
    subprocess.run(["git", "-C", str(a.m1n1), "diff", "--exit-code", "HEAD", "--", "src/kboot.c"], check=True)
    a.out.mkdir(parents=True, exist_ok=False)
    source = (a.m1n1 / "src/kboot.c").read_text()
    start = source.index("static int dt_set_fb(void)")
    stop = source.index("\nstatic ", start + 1)
    function = source[start:stop]
    unit = a.out / "framebuffer.c"
    unit.write_text(PREAMBLE + function + MAIN)
    exe = a.out / "framebuffer-test"
    subprocess.run(["gcc", "-std=c11", "-O1", "-g", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                    str(unit), "-lfdt", "-o", str(exe)], check=True)
    before = properties(a.baseline.read_bytes())
    after = properties(a.corrected.read_bytes())
    template = after.pop("/chosen/framebuffer@0")
    assert before == after, "the correction must only add the framebuffer template"
    assert template == {"compatible": b"apple,simple-framebuffer\0simple-framebuffer\0",
                        "reg": bytes(16), "status": b"disabled\0"}
    check_stage_b(a.corrected.read_bytes())
    try:
        check_stage_b(a.baseline.read_bytes())
    except ValueError as e:
        assert "framebuffer" in str(e)
    else:
        raise AssertionError("old package must fail before any USB access")
    results = []
    cases = [("old-missing", a.baseline, 32, "0x10000000", False),
             ("rgb32", a.corrected, 32, "0x10000000", True),
             ("rgb30", a.corrected, 30, "0x10000000", True),
             ("rgb16", a.corrected, 16, "0x10000000", True),
             ("unsupported-depth", a.corrected, 24, "0x10000000", False),
             ("unavailable", a.corrected, 32, "0", False)]
    formats = {32: b"x8r8g8b8\0", 30: b"x2r10g10b10\0", 16: b"r5g6b5\0"}
    for name, dtb, depth, base, good in cases:
        output = a.out / (name + ".dtb")
        result = subprocess.run([str(exe), str(dtb), str(output), str(depth), base],
                                check=True, capture_output=True, text=True, timeout=10)
        tree = properties(output.read_bytes())
        try:
            check_framebuffer(tree, prepared=True)
        except ValueError:
            if good:
                raise
        else:
            assert good, "unusable framebuffer passed"
        if good:
            stride = 640 * (2 if depth == 16 else 4)
            node = tree["/chosen/framebuffer@%x" % (0x10000000 + 16 * stride)]
            assert node["reg"] == struct.pack(">QQ", 0x10000000 + 16 * stride, stride * 464)
            assert node["format"] == formats[depth]
            assert struct.unpack(">I", node["height"])[0] == 464
            assert "status" not in node
        elif name == "old-missing":
            assert "No framebuffer found" in result.stdout
        results.append({"case": name, "result": "PASS", "prepared_gate_accepts": good})
    summary = {"m1n1_pin": pin, "function_sha256": hashlib.sha256(function.encode()).hexdigest(),
               "dt_only_change": True, "cases": results, "physical_display_tested": False}
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
