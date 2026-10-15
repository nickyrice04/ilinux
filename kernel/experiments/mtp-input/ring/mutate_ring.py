#!/usr/bin/env python3
"""Mutation check for dchid_ring.h: every deliberate mistake must make test_ring fail.

usage: python3 -I mutate_ring.py [CC]

Copies the header into a temporary directory, applies one textual mutation at a
time, builds test_ring.c against it and requires a non-zero test result (a
mutant that still compiles and passes means the tests are too weak).
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CC = sys.argv[1] if len(sys.argv) > 1 else "clang"

MUTANTS = [
    ("consumer reads write index from the read slot",
     "u32 w = DCHID_LOAD32(r->mem);\n\tu32 rr = DCHID_LOAD32(r->mem + 4);\n\n\tif (w >= r->cap || rr >= r->cap) {\n\t\tr->errors++;",
     "u32 w = DCHID_LOAD32(r->mem + 4);\n\tu32 rr = DCHID_LOAD32(r->mem);\n\n\tif (w >= r->cap || rr >= r->cap) {\n\t\tr->errors++;"),
    ("producer forgets the empty slot",
     "return rr > w ? (long)(rr - w - 1) : (long)r->cap - (long)w + (long)rr - 1;",
     "return rr > w ? (long)(rr - w) : (long)r->cap - (long)w + (long)rr;"),
    ("checksum is not complemented",
     "\treturn ~sum;\n}", "\treturn sum;\n}"),
    ("consumer publishes its index in the producer's slot",
     "DCHID_STORE32(r->mem + 4, rd);", "DCHID_STORE32(r->mem, rd);"),
    ("first segment length uses the total size",
     "first = r->cap - rd;", "first = r->size - rd;"),
    ("assembler asks for 8 bytes first",
     "#define DCHID_MIN_MSG\t\t12", "#define DCHID_MIN_MSG\t\t8"),
    ("checksum is never verified",
     "if (dchid_le32(a->buf + total - DCHID_CSUM_LEN) !=\n\t    dchid_frame_csum(a->buf, total - DCHID_CSUM_LEN))\n\t\treturn DCHID_ASM_E_CHECKSUM;",
     ""),
    ("fifo registration puts the size one byte early",
     "dchid_put_le32(out + 11, total_size);", "dchid_put_le32(out + 10, total_size);"),
    ("command body is not padded to 4 bytes",
     "size_t body = ((size_t)len + DCHID_SUBHDR_LEN + 3) & ~(size_t)3;",
     "size_t body = ((size_t)len + DCHID_SUBHDR_LEN);"),
    ("ring data starts right after one index",
     "#define DCHID_RING_HDR\t\t8", "#define DCHID_RING_HDR\t\t4"),
    ("wrap uses the wrong modulus",
     "rd = (u32)(((u64)rd + n) % r->cap);", "rd = (u32)(((u64)rd + n) % r->size);"),
    ("hdr_len above 8 is accepted",
     "if (a->buf[0] > DCHID_HDR_LEN || a->buf[0] < 6)", "if (a->buf[0] < 6)"),
]


def build_and_run(workdir):
    exe = workdir / "t"
    shutil.copy(HERE / "test_ring.c", workdir / "test_ring.c")
    cc = subprocess.run([CC, "-std=c11", "-O1", "-g", "-Wall", "-Wextra", "-Werror",
                         "-fsanitize=address,undefined", "-fno-sanitize-recover=undefined",
                         str(workdir / "test_ring.c"), "-o", str(exe)],
                        capture_output=True, text=True)
    if cc.returncode:
        return "compile-error", cc.stderr.strip().splitlines()[:3]
    try:
        run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return "fail", ["timeout (the mutant hangs the tests)"]
    return ("pass" if run.returncode == 0 else "fail"), run.stderr.strip().splitlines()[:1]


def main():
    original = (HERE / "dchid_ring.h").read_text()
    bad = 0
    with tempfile.TemporaryDirectory() as d:
        work = Path(d)
        (work / "dchid_ring.h").write_text(original)
        status, _ = build_and_run(work)
        print("baseline:", status)
        if status != "pass":
            return 2
        for name, old, new in MUTANTS:
            if original.count(old) != 1:
                print("MUTATION SITE NOT FOUND (header changed?):", name)
                bad += 1
                continue
            (work / "dchid_ring.h").write_text(original.replace(old, new))
            status, detail = build_and_run(work)
            ok = status == "fail"
            print("%-58s %s" % (name, "caught" if ok else "SURVIVED (%s)" % status))
            if not ok:
                bad += 1
        shutil.copy(HERE / "dchid_ring.h", work / "dchid_ring.h")
    print("mutants: %d, survived/invalid: %d" % (len(MUTANTS), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
