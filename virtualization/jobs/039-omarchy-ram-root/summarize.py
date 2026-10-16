#!/usr/bin/env python3
"""summarize.py OUT: collect job 039's measurements into one JSON object on stdout.

Reads OUT/sizes.txt, OUT/compression.txt, OUT/packages.txt, OUT/elf-16k-check.txt and,
when the boot test ran, OUT/test/{serial.log,guest-measure.txt,journal.txt,dmesg.txt,
hyprland.log,wall.txt} and test/console.log. Standard library only.
"""
import json
import pathlib
import re
import sys


def num(text):
    try:
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return text


def read(path):
    try:
        return path.read_text(errors="replace")
    except OSError:
        return ""


def first_time(text, pattern):
    """Seconds since kernel start of the first '[   12.345678] ...' line matching pattern."""
    for line in text.splitlines():
        if re.search(pattern, line):
            m = re.match(r"\[\s*([0-9]+\.[0-9]+)\]", line)
            if m:
                return float(m.group(1))
    return None


def meminfo(text):
    values = {}
    for line in text.splitlines():
        m = re.match(r"(\w+(?:\(\w+\))?):\s+(\d+) kB", line)
        if m:
            values[m.group(1)] = int(m.group(2))
    return values


def main():
    out = pathlib.Path(sys.argv[1])
    res = {}
    for line in read(out / "sizes.txt").splitlines():
        key, _, value = line.partition(" ")
        res[key] = num(value.strip())
    res["compression"] = []
    for line in read(out / "compression.txt").splitlines():
        m = re.match(r"zstd (.*?)\s+bytes\s+(\d+)\s+compress_s\s+([\d.]+)\s+decompress_1thread_s\s+([\d.]+)", line)
        if m:
            res["compression"].append({"args": m.group(1), "bytes": int(m.group(2)),
                                       "compress_s": float(m.group(3)),
                                       "decompress_1thread_s": float(m.group(4))})
    res["packages"] = len(read(out / "packages.txt").splitlines())
    elf = read(out / "elf-16k-check.txt").splitlines()
    res["elf_16k_check"] = {l.split()[0]: num(l.split()[1]) for l in elf if l and not l.startswith(" ")}
    res["jemalloc_page_size"] = read(out / "jemalloc-page-size.txt").splitlines()[:2]
    for line in read(out / "build" / "bench-vm.txt").splitlines():
        key, _, value = line.partition(" ")
        res[key] = num(value.strip())

    test = out / "test"
    serial = read(test / "console.log") or read(test / "serial.log")
    if not serial:
        print(json.dumps(res, indent=2))
        return
    t = {}
    m = re.search(r"ILINUX-DESKTOP-READY ([0-9.]+)", serial)
    t["desktop_ready_s_after_kernel_start"] = float(m.group(1)) if m else None
    m = re.search(r"ILINUX-MEMINFO-BEGIN uptime ([0-9.]+)\n(.*?)ILINUX-MEMINFO-END", serial, re.S)
    if m:
        mi = meminfo(m.group(2))
        t["meminfo_at_s"] = float(m.group(1))
        t["mem_total_mib"] = round(mi.get("MemTotal", 0) / 1024, 1)
        t["mem_used_mib"] = round((mi.get("MemTotal", 0) - mi.get("MemFree", 0)) / 1024, 1)
        t["mem_total_minus_available_mib"] = round((mi.get("MemTotal", 0) - mi.get("MemAvailable", 0)) / 1024, 1)
        for key in ("MemFree", "MemAvailable", "Shmem", "AnonPages", "Cached", "Slab",
                    "KernelStack", "PageTables", "Percpu"):
            t[key + "_mib"] = round(mi.get(key, 0) / 1024, 1)
    for line in read(test / "wall.txt").splitlines():
        key, _, value = line.partition(" ")
        t[key] = num(value.strip())

    dmesg = read(test / "dmesg.txt")
    t["kernel_initramfs_unpack_start_s"] = first_time(dmesg, r"Trying to unpack rootfs image as initramfs")
    t["kernel_initrd_freed_s"] = first_time(dmesg, r"Freeing initrd memory")
    t["kernel_run_init_s"] = first_time(dmesg, r"Run /init as init process")
    t["simpledrm_s"] = first_time(dmesg, r"simpledrm|simple-framebuffer")
    journal = read(test / "journal.txt")
    t["hyprland_unit_started_s"] = first_time(journal, r"Started .*Hyprland")
    t["waybar_bar_configured_s"] = first_time(journal, r"waybar.*Bar configured")
    t["desktop_ready_logged_s"] = first_time(journal, r"desktop ready")
    t["sshd_socket_listening_s"] = first_time(journal, r"Listening on .*SSH on the USB")
    t["hyprland_restarts"] = journal.count("ilinux-desktop.service: Scheduled restart")
    t["swaybg_image_load_failed"] = "Failed to load background image" in journal

    sections, name = {}, None
    for line in read(test / "guest-measure.txt").splitlines():
        if line.startswith("=== "):
            name = line[4:].strip()
            sections[name] = []
        elif name:
            sections[name].append(line)
    sa = " ".join(sections.get("systemd-analyze", []))
    m = re.search(r"Startup finished in (.*?)$", sa)
    t["systemd_analyze"] = m.group(1).strip() if m else None
    t["page_size"] = num("".join(sections.get("pagesize", [""])).strip() or "0")
    t["nproc"] = num("".join(sections.get("nproc", [""])).strip() or "0")
    t["failed_units"] = [l for l in sections.get("failed-units", []) if l.strip()]
    t["drm"] = sections.get("drm", [])
    mon = "\n".join(sections.get("hyprctl-monitors", []))
    m = re.search(r"(\d+x\d+)@([\d.]+) at", mon)
    t["output_mode"] = m.group(0)[:-3] if m else None
    m = re.search(r"scale: ([\d.]+)", mon)
    t["output_scale"] = float(m.group(1)) if m else None
    t["cpu_10s_at_desktop"] = sections.get("cpu-10s", [])
    t["top_processes_pss"] = sections.get("processes", [])[:12]
    t["usb_gadget_check"] = sections.get("usb-gadget-check", [])
    for line in sections.get("bench", []):
        key, _, value = line.partition(" ")
        if key.startswith("bench_"):
            t[key] = num(value.strip())
    for tool in ("gzip", "zstd"):
        vm, guest = res.get(f"bench_{tool}_llvm_s_vm"), t.get(f"bench_{tool}_llvm_s_guest")
        if isinstance(vm, float) and isinstance(guest, float) and vm > 0:
            t[f"tcg_slowdown_{tool}"] = round(guest / vm, 2)
    rend = sections.get("renderer", [])
    t["renderer_threads"] = [l.strip() for l in rend if "llvmpipe" in l or "softpipe" in l]
    t["renderer_libraries"] = [l.strip() for l in rend if l.strip().startswith("/usr/lib/")]
    m = re.search(r"Renderer: ([^\n]+)", read(test / "hyprland.log"))
    t["gl_renderer"] = m.group(1).strip() if m else None
    m = re.search(r"Using: ([^\n]+)", read(test / "hyprland.log"))
    t["gl_version"] = m.group(1).strip() if m else None
    t["bubblewrap"] = " ".join(sections.get("bwrap", [])).strip()
    t["root_mount"] = sections.get("root-mount", [])
    res["boot_test"] = t
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
