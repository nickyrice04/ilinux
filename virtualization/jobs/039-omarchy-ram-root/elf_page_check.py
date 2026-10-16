#!/usr/bin/env python3
"""elf_page_check.py ROOT: static checks of every ELF file under ROOT.

1. 16 KiB pages: loadable segments a 16 KiB-page kernel cannot map (PT_LOAD alignment below
   16 KiB, or file offset and address not congruent modulo 16 KiB).
2. Allocators with a build-time page size (jemalloc, tcmalloc) in DT_NEEDED.
3. Shared libraries named in DT_NEEDED that are nowhere in ROOT (catches over-pruning; a
   library loaded through another object's RUNPATH counts as present).
Reads files; never runs them. Standard library only.
"""
import glob
import os
import struct
import sys

PAGE = 16384
ALLOCATORS = ("libjemalloc", "libtcmalloc")


def inspect(path):
    """Return (problems, needed, runpaths) for an ELF64 file, or None if not ELF."""
    with open(path, "rb") as f:
        head = f.read(64)
        if len(head) < 64 or head[:4] != b"\x7fELF":
            return None
        if head[4] != 2 or head[5] != 1:
            return (["not ELF64 little-endian"], [], [])
        phoff = struct.unpack_from("<Q", head, 32)[0]
        phentsize, phnum = struct.unpack_from("<HH", head, 54)
        f.seek(phoff)
        table = f.read(phentsize * phnum)
        loads, dynamic = [], None
        for i in range(phnum):
            p_type, _, off, vaddr, _, filesz, _, align = struct.unpack_from("<IIQQQQQQ", table, i * phentsize)
            if p_type == 1:
                loads.append((off, vaddr, filesz, align))
            elif p_type == 2:
                dynamic = (off, filesz)
        problems = []
        for off, vaddr, _, align in loads:
            if align < PAGE:
                problems.append(f"PT_LOAD align {align:#x}")
            elif (off - vaddr) % PAGE:
                problems.append("PT_LOAD offset and address differ modulo 16 KiB")
        needed, runpaths = [], []
        if dynamic:
            f.seek(dynamic[0])
            dyn = f.read(dynamic[1])
            strtab, need, run = None, [], []
            for i in range(0, len(dyn) - 15, 16):
                tag, val = struct.unpack_from("<qQ", dyn, i)
                if tag == 0:
                    break
                if tag == 1:
                    need.append(val)
                elif tag == 5:
                    strtab = val
                elif tag in (15, 29):  # DT_RPATH, DT_RUNPATH
                    run.append(val)
            base = None
            for off, vaddr, filesz, _ in loads:
                if strtab is not None and vaddr <= strtab < vaddr + filesz:
                    base = strtab - vaddr + off

            def string(o):
                f.seek(base + o)
                return f.read(4096).split(b"\0", 1)[0].decode(errors="replace")

            if base is not None:
                needed = [string(o) for o in need]
                for o in run:
                    runpaths += [p for p in string(o).split(":") if p]
        return problems, needed, runpaths


def default_dirs(root):
    dirs = ["/usr/lib"]
    for conf in sorted(glob.glob(os.path.join(root, "etc/ld.so.conf.d/*.conf"))):
        with open(conf) as f:
            dirs += [l.strip() for l in f if l.strip().startswith("/")]
    return dirs


def present(root, directory, name):
    # Arch's library symlinks are relative, so they resolve inside ROOT.
    return os.path.exists(os.path.join(root, directory.lstrip("/"), name))


def main():
    root = sys.argv[1]
    dirs = default_dirs(root)
    anywhere = set()
    for dirpath, _, files in os.walk(os.path.join(root, "usr/lib")):
        anywhere.update(n for n in files if os.path.exists(os.path.join(dirpath, n)))
    elf = 0
    bad, alloc, missing = [], [], []
    for dirpath, _, files in os.walk(root):
        for name in files:
            path = os.path.join(dirpath, name)
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            try:
                result = inspect(path)
            except (OSError, struct.error):
                continue
            if result is None:
                continue
            elf += 1
            problems, needed, runpaths = result
            rel = "/" + os.path.relpath(path, root)
            if problems:
                bad.append((rel, problems))
            libs = [n for n in needed if n.startswith(ALLOCATORS)]
            if libs:
                alloc.append((rel, libs))
            origin = os.path.dirname(rel)
            search = [p.replace("$ORIGIN", origin).replace("${ORIGIN}", origin) for p in runpaths] + dirs
            gone = [n for n in needed if "/" not in n and n not in anywhere
                    and not any(present(root, d, n) for d in search)]
            if gone:
                missing.append((rel, gone))
    print(f"elf_files {elf}")
    print(f"segments_not_16k_mappable {len(bad)}")
    for rel, why in bad:
        print(f"  {rel}: {'; '.join(sorted(set(why)))}")
    print(f"links_page_size_sensitive_allocator {len(alloc)}")
    for rel, libs in alloc:
        print(f"  {rel}: {', '.join(libs)}")
    print(f"needs_missing_library {len(missing)}")
    for rel, libs in missing:
        print(f"  {rel}: {', '.join(libs)}")


if __name__ == "__main__":
    main()
