#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build original AT fixture; execute only when --qemu explicitly names a tool.

Root runs QEMU inside the isolated Linux VM. No Apple files, networking, disks,
monitor services or physical device interfaces are opened by the fixture.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import socket
import struct
import subprocess
import time

HERE = Path(__file__).resolve().parent
FILES = ("probe.h", "probe.S", "fixture.S", "fixture.ld", "run.py", "README.md")
BASE, SIZE, CAPTURE = 0x40480000, 0x7000, 0x40483000
TARGET, TARGET_SIZE = 0x40200000, 0x6000
MAGIC = 0x3142413133525458


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def command(argv, output, name):
    p = subprocess.run(argv, cwd=HERE, stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, timeout=60)
    record = {"argv": argv, "returncode": p.returncode,
              "stdout": p.stdout, "stderr": p.stderr}
    save(output / (name + ".json"), record)
    if p.returncode:
        raise RuntimeError(name + " failed; inspect its JSON log")
    return record


def elf_payload(data):
    if len(data) < 64 or data[:7] != b"\x7fELF\x02\x01\x01":
        raise ValueError("expected little-endian ELF64")
    h = struct.unpack_from("<HHIQQQIHHHHHH", data, 16)
    kind, machine, version, entry, phoff, shoff, flags, ehsize, phsize, phnum, shsize, shnum, shstr = h
    if (kind, machine, version, entry, ehsize, phsize, shsize) != (2, 183, 1, BASE, 64, 56, 64):
        raise ValueError("unexpected fixture ELF identity/entry")
    if phoff + phnum * phsize > len(data) or shoff + shnum * shsize > len(data):
        raise ValueError("ELF tables outside file")
    payload = bytearray(SIZE)
    spans = []
    for i in range(phnum):
        typ, perm, off, va, pa, filesz, memsz, align = struct.unpack_from("<IIQQQQQQ", data, phoff + i * phsize)
        if typ != 1:
            continue
        if not (va == pa and BASE <= pa < BASE + SIZE and filesz <= memsz and
                pa + memsz <= BASE + SIZE and off + filesz <= len(data)):
            raise ValueError("load segment outside bounded fixture")
        if perm & 3 == 3:
            raise ValueError("writable executable fixture segment")
        if any(pa < end and start < pa + memsz for start, end in spans):
            raise ValueError("overlapping fixture load segments")
        spans.append((pa, pa + memsz))
        payload[pa - BASE:pa - BASE + filesz] = data[off:off + filesz]
    if len(spans) != 2 or payload[0x3000:0x4000] != b"\xa5" * 4096:
        raise ValueError("unexpected capture/segment initialization")
    symbols = {}
    for i in range(shnum):
        s = struct.unpack_from("<IIQQQQIIQQ", data, shoff + i * shsize)
        _, typ, _, _, off, size, link, _, _, entsize = s
        if typ in (4, 9) and size:
            raise ValueError("linked fixture retains relocations")
        if typ != 2:
            continue
        if entsize != 24 or size % 24 or off + size > len(data) or link >= shnum:
            raise ValueError("bad symbol table")
        strings = struct.unpack_from("<IIQQQQIIQQ", data, shoff + link * shsize)
        so, ss = strings[4:6]
        if so + ss > len(data):
            raise ValueError("bad string table")
        for j in range(size // 24):
            no, info, other, index, value, extent = struct.unpack_from("<IBBHQQ", data, off + j * 24)
            if no >= ss:
                raise ValueError("symbol name outside table")
            end = data.find(b"\x00", so + no, so + ss)
            if end < 0:
                raise ValueError("unterminated symbol name")
            name = data[so + no:end].decode("ascii")
            if name and index == 0:
                raise ValueError("undefined linked symbol: " + name)
            if name:
                symbols[name] = (value, extent)
    address, extent = symbols["translation31ab_s1e2w"]
    if not (BASE <= address < BASE + 0x3000 and 0 < extent <= 256 and extent % 4 == 0):
        raise ValueError("probe symbol outside code extent")
    words = struct.unpack("<" + "I" * (extent // 4), payload[address - BASE:address - BASE + extent])
    if words.count(0xd50c7822) != 1 or words.count(0xd5387403) != 1 or words.count(0xd5187403) != 1:
        raise ValueError("probe lacks exact single AT and PAR save/restore instructions")
    if words.count(0xd5033fdf) != 2:
        raise ValueError("probe lacks synchronization after AT and PAR restore")
    for name, wanted in (("fixture_capture", CAPTURE), ("fixture_l1", BASE + 0x4000),
                         ("fixture_l2", BASE + 0x5000), ("fixture_l3", BASE + 0x6000)):
        if symbols[name][0] != wanted:
            raise ValueError("fixture symbol geometry mismatch: " + name)
    return bytes(payload), {"elf_entry": hex(entry), "load_segments": len(spans),
                            "probe_bytes": extent, "probe_instructions": len(words),
                            "single_at_s1e2w": True, "par_save_restore_pair": True,
                            "relocations": 0, "undefined_symbols": 0}


class QMP:
    def __init__(self, path):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(3)
        try:
            self.sock.connect(str(path))
        except OSError:
            self.sock.close()
            raise
        self.file = self.sock.makefile("rb")
        if "QMP" not in json.loads(self.file.readline()):
            raise RuntimeError("missing QMP greeting")
        self.call("qmp_capabilities")

    def call(self, name, args=None):
        req = {"execute": name}
        if args is not None:
            req["arguments"] = args
        self.sock.sendall(json.dumps(req).encode() + b"\n")
        while True:
            line = self.file.readline()
            if not line:
                raise RuntimeError("QMP closed")
            reply = json.loads(line)
            if "error" in reply:
                raise RuntimeError(str(reply["error"]))
            if "return" in reply:
                return reply["return"]

    def memory(self, address, size, path):
        reply = self.call("human-monitor-command", {"command-line":
            f"pmemsave {address:#x} {size:#x} {json.dumps(str(path))}"})
        if reply:
            raise RuntimeError("QMP memory read failed: " + reply)
        data = path.read_bytes()
        if len(data) != size:
            raise RuntimeError("short QMP memory read")
        return data

    def close(self):
        self.file.close()
        self.sock.close()


def check_capture(raw):
    if len(raw) != 4096:
        raise ValueError("wrong capture size")
    header = struct.unpack_from("<16Q", raw)
    if header[:5] != (MAGIC, 2, 8, 0x80000000, 0x80823519):
        raise ValueError("wrong fixture phase/profile: " + str(header[:5]))
    if not header[5] & 1 or header[6:8] != (0xff44, 10) or any(header[8:]):
        raise ValueError("wrong MMU/MAIR/count/fault header")
    if raw[768:2048] != bytes(1280) or raw[2048:] != b"\xa5" * 2048:
        raise ValueError("capture clearing exceeded or missed its owned extent")
    names = ("mmu-off-refusal", "daif-open-refusal", "tge-refusal", "rw-normal-nc",
             "read-only-permission-fault", "unmapped-translation-fault", "rw-normal-wb",
             "different-physical-page", "nonzero-page-offset", "access-flag-fault")
    cases = []
    for i, name in enumerate(names):
        number, status, par, before, after, va, expected, attr = struct.unpack_from("<8Q", raw, 128 + i * 64)
        if number != i or before == 0 or before != after:
            raise ValueError(name + ": identity/PAR restoration failed")
        if status == 0 and par == before:
            raise ValueError(name + ": PAR seed did not distinguish the AT result")
        want_va = (0x80000000, 0x80000000, 0x80000000, 0x80000000,
                   0x80001000, 0x80002000, 0x80003000, 0x80004000, 0x80000fff, 0x80005000)[i]
        if va != want_va:
            raise ValueError(name + ": input address changed")
        result = {"case": name, "status": "PASS", "probe_status": status,
                  "par_raw": hex(par), "par_before": hex(before), "par_after": hex(after),
                  "virtual_address": hex(va)}
        if i < 3:
            if status != (4, 3, 2)[i] or par or expected or attr:
                raise ValueError(name + ": refusal did not preserve raw-result contract")
        elif i in (4, 5, 9):
            fault = {4: 15, 5: 7, 9: 11}[i]
            if status or not par & 1 or (par >> 1) & 0x3f != fault or expected or attr:
                raise ValueError(name + ": incorrect stage-1 fault class")
            result["fault_status"] = fault
        else:
            physical = (par & 0x000ffffffffff000) | (va & 0xfff)
            wanted = {3: (0x40200000, 0x44), 6: (0x40203000, 0xff),
                      7: (0x40204000, 0x44), 8: (0x40200fff, 0x44)}[i]
            if status or par & 1 or (physical, par >> 56) != wanted or attr != wanted[1]:
                raise ValueError(name + ": translation/attributes incorrect")
            if expected != (0x40304000 if i == 7 else wanted[0]):
                raise ValueError(name + ": fixture expected-PA binding changed")
            if (physical == expected) != (i != 7):
                raise ValueError(name + ": expected-PA comparison failed")
            result.update({"translated_physical_address": hex(physical), "attribute": hex(par >> 56),
                           "expected_pa_matches": physical == expected})
        cases.append(result)
    return cases


def emulate(qemu, output, report):
    sock = output / "qmp.sock"
    if len(str(sock).encode()) > 100:
        raise ValueError("output path too long for Unix QMP socket")
    target = bytes((i * 17 + 3) & 255 for i in range(TARGET_SIZE))
    (output / "target.bin").write_bytes(target)
    args = [qemu, "-machine", "virt,secure=off,virtualization=on", "-accel", "tcg",
            "-cpu", "cortex-a57", "-smp", "1", "-m", "64M", "-nodefaults",
            "-display", "none", "-nic", "none", "-serial", "none", "-monitor", "none",
            "-qmp", "unix:" + str(sock) + ",server=on,wait=off", "-S",
            "-device", f"loader,file={output / 'fixture.bin'},addr={BASE:#x},force-raw=on",
            "-device", f"loader,file={output / 'target.bin'},addr={TARGET:#x},force-raw=on",
            "-device", f"loader,addr={BASE:#x},cpu-num=0"]
    save(output / "qemu-command.json", args)
    monitor = None
    started = time.monotonic()
    with (output / "qemu.log").open("wb") as log:
        process = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 15
            while monitor is None:
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("QEMU monitor unavailable")
                try:
                    monitor = QMP(sock)
                except (FileNotFoundError, ConnectionRefusedError):
                    time.sleep(0.02)
            initial = monitor.memory(CAPTURE, 4096, output / "initial-capture.bin")
            if initial != b"\xa5" * 4096:
                raise RuntimeError("capture was not poisoned before execution")
            monitor.call("cont")
            report["payload_executed"] = True
            while True:
                raw = monitor.memory(CAPTURE, 4096, output / "capture.bin")
                phase = struct.unpack_from("<Q", raw, 8)[0]
                if phase in (2, 0xdead):
                    break
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("fixture did not complete within deadline")
                time.sleep(0.02)
            monitor.call("stop")
            if phase == 0xdead:
                raise RuntimeError("fixture took an exception; inspect capture header")
            raw = monitor.memory(CAPTURE, 4096, output / "capture.bin")
            cases = check_capture(raw)
            after = monitor.memory(TARGET, TARGET_SIZE, output / "target-after.bin")
            if after != target:
                raise RuntimeError("AT fixture changed candidate target bytes")
            tables = monitor.memory(BASE + 0x4000, 0x3000, output / "tables-after.bin")
            expected_tables = bytearray(0x3000)
            for offset, word in ((8, 0x40000701), (16, BASE + 0x5003),
                                 (0x1000, BASE + 0x6003), (0x2000, 0x40200703),
                                 (0x2008, 0x40201783), (0x2018, 0x40203707),
                                 (0x2020, 0x40204703), (0x2028, 0x40205303)):
                struct.pack_into("<Q", expected_tables, offset, word)
            if tables != expected_tables:
                raise RuntimeError("baseline page-table contents changed")
            return {"cases": cases, "case_count": len(cases), "cpu_model": "cortex-a57",
                    "acceleration": "tcg", "seconds": time.monotonic() - started,
                    "candidate_bytes_unchanged": len(target), "table_bytes_checked": len(tables),
                    "capture_sha256": sha(raw), "target_sha256": sha(target),
                    "tables_sha256": sha(tables), "hardware_af_management": False}
        finally:
            if monitor:
                try:
                    monitor.call("quit")
                except (OSError, RuntimeError, ValueError):
                    pass
                monitor.close()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--cc", default="cc")
    p.add_argument("--ld", default="ld")
    p.add_argument("--target")
    p.add_argument("--compile-only", action="store_true")
    p.add_argument("--qemu", help="explicit standard ARM QEMU executable; omit to avoid execution")
    a = p.parse_args()
    output = a.output.resolve()
    if output.exists() or HERE == output or HERE in output.parents or a.compile_only and a.qemu:
        p.error("use a fresh output outside sources; compile-only cannot use QEMU")
    output.mkdir(parents=True)
    report = {"schema": 1, "status": "FAIL", "scope": "ORIGINAL_STANDARD_ARM_TRANSLATION",
              "native": "NOT_RUN", "apple_firmware": False, "monitor_calls": 0,
              "payload_executed": False, "case_count": 0}
    try:
        bindings = [{"file": name, "bytes": len((HERE / name).read_bytes()),
                     "sha256": sha((HERE / name).read_bytes())} for name in FILES]
        save(output / "source-bindings.json", bindings)
        report["source_bindings_sha256"] = sha((output / "source-bindings.json").read_bytes())
        report["compiler"] = command([a.cc, "--version"], output, "compiler")["stdout"]
        objects = []
        for name in ("probe", "fixture"):
            obj = output / (name + ".o")
            args = [a.cc] + (["--target=" + a.target] if a.target else [])
            command(args + ["-ffreestanding", "-c", name + ".S", "-o", str(obj)], output, name + "-compile")
            objects.append(str(obj))
        report["objects"] = [{"file": Path(obj).name, "sha256": sha(Path(obj).read_bytes())} for obj in objects]
        if a.compile_only:
            report["status"] = "COMPILE_PASS_NOT_EXECUTED"
        else:
            report["linker"] = command([a.ld, "--version"], output, "linker")["stdout"]
            elf = output / "fixture.elf"
            command([a.ld, "--fatal-warnings", "--no-undefined", "--build-id=none",
                     "-z", "max-page-size=4096", "-T", "fixture.ld", *objects, "-o", str(elf)], output, "link")
            payload, audit = elf_payload(elf.read_bytes())
            (output / "fixture.bin").write_bytes(payload)
            report["audit"] = audit
            report["fixture_sha256"] = sha(payload)
            report["status"] = "LINK_PASS_NOT_EXECUTED"
            if a.qemu:
                report["status"] = "FAIL"
                report["qemu_version"] = command([a.qemu, "--version"], output, "qemu-version")["stdout"]
                report.update(emulate(a.qemu, output, report))
                report["status"] = "PASS"
        final_bindings = [{"file": name, "bytes": len((HERE / name).read_bytes()),
                           "sha256": sha((HERE / name).read_bytes())} for name in FILES]
        if final_bindings != bindings:
            raise RuntimeError("source files changed during the run")
        report["source_files_unchanged"] = True
    except Exception as e:
        report["status"] = "FAIL"
        report["error"] = str(e)
        raise
    finally:
        save(output / "results.json", report)
    print(json.dumps({k: report[k] for k in ("status", "case_count", "payload_executed", "native")}))


if __name__ == "__main__":
    main()
