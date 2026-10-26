#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the complete original immutable31AF payload in standard ARM QEMU.

This script never loads Apple firmware. Run it only in the isolated Linux build
environment. Omitting --qemu prepares fixtures; --self-test only checks the
fixture generators and executes neither a compiler nor an emulator.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
QMP_HELPER = ROOT / "kernel/experiments/translation31ab/run.py"
BASE, SIZE, ENTRY = 0x40400000, 0x60000, 0x5c000
RESERVED_START, RESERVED_END, RESERVED_SENTINEL = 0x4000, 0x58000, 0xa5
BOOTSTRAP, TABLES, ARGS, FB, VA = 0x42000000, 0x43000000, 0x45000000, 0x44000000, 0x80000000
SCRATCH, SCRATCH_MAGIC = 0x46000000, 0x31464133464c5446
OLD_SIZE, OLD_ENTRY = 0x24000, 0x14000
OLD_SHA256 = "35bcecdff17ca1b927fccdffd057c9f149577df5698f250b7dbe93f5c71fe13b"
REFUSALS = {
    "reason": 1, "reason-wide": 1, "mmu-off": 5, "mixed-hcr": 3,
    "boot-unmapped": 8, "monitor-unmapped": 9, "count-unmapped": 11,
    "table-unmapped": 13, "count-zero": 12, "count-large": 12,
    "helper-version": 10, "video-version": 15, "video-depth": 15,
    "video-small": 16, "video-stride": 15, "range-wrap": 14,
    "range-unaligned": 14, "range-overlap": 14, "range-va-overlap": 14,
    "range-uncovered": 16, "fb-ro-last": 17, "fb-unmapped-last": 17,
    "fb-wrong-pa": 18, "fb-device": 19, "image-alias": 20, "input-alias": 20,
}
FB_BYTES, WIDTH, HEIGHT, STRIDE = 0x20000, 256, 128, 1024
MARKER_WIDTH, MARKER_HEIGHT = 128, 64
MARKER_X, MARKER_Y = (WIDTH - MARKER_WIDTH) // 2, (HEIGHT - MARKER_HEIGHT) // 2
PAR_SEED = 0x400000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def emit(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def qword(data, offset, value):
    struct.pack_into("<Q", data, offset, value)


def model_payload(payload, old_control=False):
    """Model prepopulated monitor-owned state without altering linked inputs."""
    if old_control:
        return payload
    if len(payload) != SIZE:
        raise ValueError("wrong new payload size for reserved-state model")
    modeled = bytearray(payload)
    modeled[RESERVED_START:RESERVED_END] = bytes([RESERVED_SENTINEL]) * (RESERVED_END - RESERVED_START)
    return bytes(modeled)


def tables16k(cache):
    """39-bit VHE low VA with 16KiB tables and explicit image/FB L3 pages."""
    data = bytearray(0x14000)
    qword(data, 0, TABLES + 0x4003)       # L1[0] -> L2, 32MiB blocks
    for index in range(32, 40):
        qword(data, 0x4000 + index * 8, (index << 25) | 0x701)
    qword(data, 0x4000 + 32 * 8, TABLES + 0x8003)   # identity 0x40000000
    qword(data, 0x4000 + 34 * 8, TABLES + 0xc003)   # identity 0x44000000
    qword(data, 0x4000 + 64 * 8, TABLES + 0x10003)  # aperture VA 0x80000000
    for index in range(2048):
        physical = 0x40000000 + index * 0x4000
        flags = 0x783 if BASE <= physical < BASE + SIZE else 0x703
        qword(data, 0x8000 + index * 8, physical | flags)
        physical = 0x44000000 + index * 0x4000
        # Remove only the framebuffer's physical-address-as-VA mapping. ARGS
        # at 0x45000000 remains a readable identity-mapped fixture source.
        qword(data, 0xc000 + index * 8, 0 if FB <= physical < FB + FB_BYTES else physical | 0x703)
    attr = 0x707 if cache == "wb" else 0x703
    for index in range(FB_BYTES // 0x4000):
        qword(data, 0x10000 + index * 8, (FB + index * 0x4000) | attr)
    return bytes(data)


def tables(kind, cache, mode="non-vhe"):
    """39-bit low VA, 4KiB L1/L2/L3; complete payload mapping is read-only."""
    if mode == "16k-vhe":
        if kind != "valid":
            raise ValueError("16KiB fixture currently qualifies positive cases only")
        return tables16k(cache)
    data = bytearray(0x10000)
    qword(data, 8, TABLES + 0x1003)       # L1[1]: identity 0x40000000..0x7fffffff
    qword(data, 16, TABLES + 0x3003)      # L1[2]: framebuffer VA 0x80000000
    for index in range(128):
        qword(data, 0x1000 + index * 8, (0x40000000 + index * 0x200000) | 0x701)
    # The physical framebuffer address is deliberately not a usable CPU VA.
    # Only the supplied aperture alias can reach it, with one chosen attribute.
    qword(data, 0x1000 + ((FB - 0x40000000) // 0x200000) * 8, 0)
    qword(data, 0x1000 + 2 * 8, TABLES + 0x2003)
    for index in range(512):
        address = BASE + index * 0x1000
        # AP[2]=1 means EL2 read-only, even for the synthetic header/boot text.
        flags = 0x783 if index < SIZE // 0x1000 else 0x703
        qword(data, 0x2000 + index * 8, address | flags)
    qword(data, 0x3000, TABLES + 0x4003)
    attr = 0x707 if cache == "wb" else 0x703
    for index in range(FB_BYTES // 0x1000):
        physical = (BASE if kind == "image-alias" else ARGS if kind == "input-alias" else FB) + index * 0x1000
        qword(data, 0x4000 + index * 8, physical | attr)
    last = (MARKER_Y + MARKER_HEIGHT - 1) * STRIDE // 0x1000
    first = MARKER_Y * STRIDE // 0x1000
    if kind == "fb-ro-last":
        qword(data, 0x4000 + last * 8, (FB + last * 0x1000) | attr | 0x80)
    if kind == "fb-unmapped-last":
        qword(data, 0x4000 + last * 8, 0)
    if kind == "fb-wrong-pa":
        qword(data, 0x4000 + first * 8, (FB + (first + 1) * 0x1000) | attr)
    if kind == "fb-device":
        for index in range(FB_BYTES // 0x1000):
            qword(data, 0x4000 + index * 8, (FB + index * 0x1000) | 0x70b)
    return bytes(data)


def arguments(kind, depth):
    data = bytearray(0x10000)
    struct.pack_into("<HH", data, 0, 2, 2)
    for offset, value in ((8, 0x40000000), (16, 0x40000000), (24, 0x10000000),
                          (40, FB | 3), (48, 1), (56, STRIDE), (64, WIDTH),
                          (72, HEIGHT), (80, depth)):
        qword(data, offset, value)
    struct.pack_into("<I", data, 0x4000 + 416, 10)
    struct.pack_into("<QQ", data, 0x4000 + 424, ARGS + 0x8000, ARGS + 0xc000)
    struct.pack_into("<I", data, 0x8000, 1)
    struct.pack_into("<QQI", data, 0xc000, FB, VA, FB_BYTES // 0x4000)
    reason, boot, monitor = 0, ARGS, ARGS + 0x4000
    if kind == "reason":
        reason = 1
    if kind == "reason-wide":
        reason = 0x100000000
    if kind == "boot-unmapped":
        boot = 0xa0000000
    if kind == "monitor-unmapped":
        monitor = 0xa0004000
    if kind == "count-unmapped":
        qword(data, 0x4000 + 424, 0xa0008000)
    if kind == "table-unmapped":
        qword(data, 0x4000 + 432, 0xa000c000)
    if kind == "count-zero":
        struct.pack_into("<I", data, 0x8000, 0)
    if kind == "count-large":
        struct.pack_into("<I", data, 0x8000, 65)
    if kind == "helper-version":
        struct.pack_into("<I", data, 0x4000 + 416, 9)
    if kind == "video-version":
        struct.pack_into("<H", data, 0, 1)
    if kind == "video-depth":
        qword(data, 80, 24)
    if kind == "video-small":
        qword(data, 64, MARKER_WIDTH - 1)
    if kind == "video-stride":
        qword(data, 56, WIDTH * 4 - 4)
    if kind == "range-wrap":
        struct.pack_into("<QQI", data, 0xc000, 0xffffffffffffc000, VA, 2)
    if kind == "range-unaligned":
        qword(data, 0xc000, FB + 4)
    if kind in ("range-overlap", "range-va-overlap"):
        struct.pack_into("<I", data, 0x8000, 2)
        struct.pack_into("<QQI", data, 0xc000 + 24,
                         FB if kind == "range-overlap" else FB + FB_BYTES,
                         VA + FB_BYTES if kind == "range-overlap" else VA, 1)
    if kind == "range-uncovered":
        struct.pack_into("<I", data, 0xc000 + 16, 1)
    if kind in ("image-alias", "input-alias"):
        physical = BASE if kind == "image-alias" else ARGS
        qword(data, 40, physical | 3)
        qword(data, 0xc000, physical)
    return bytes(data), reason, boot, monitor


def registers(monitor):
    raw = monitor.call("human-monitor-command", {"command-line": "info registers"})
    values = {name.upper(): int(value, 16) for name, value in
              re.findall(r"\b(PC|SP|X\d{2}|PSTATE)\s*=\s*([0-9a-fA-F]+)", raw, re.I)}
    for name in ("PC", "SP", "X25", "X26", "X27", "X28"):
        if name not in values:
            raise RuntimeError("HMP register output lacks " + name + ": " + raw[:1000])
    return values, raw


def command(argv, output, label):
    result = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                            text=True, timeout=30)
    emit(output / (label + ".json"), {"argv": argv, "returncode": result.returncode,
                                    "stdout": result.stdout, "stderr": result.stderr})
    if result.returncode:
        raise RuntimeError(label + " failed; inspect its JSON log")


def verify_fixture_generators():
    for cache in ("nc", "wb"):
        raw = tables("valid", cache)
        if len(raw) != 0x10000:
            raise AssertionError("table size")
        for index in range(SIZE // 0x1000):
            word = struct.unpack_from("<Q", raw, 0x2000 + index * 8)[0]
            if word != (BASE + index * 0x1000) | 0x783:
                raise AssertionError("payload page is not explicitly read-only")
        for index in range(4, 0x58):
            if not struct.unpack_from("<Q", raw, 0x2000 + index * 8)[0] & 0x80:
                raise AssertionError("DATA_SPTM page writable")
        raw16 = tables16k(cache)
        if len(raw16) != 0x14000 or struct.unpack_from("<Q", raw16, 0)[0] != TABLES + 0x4003:
            raise AssertionError("16KiB root/table geometry")
        for address in range(BASE, BASE + SIZE, 0x4000):
            index = (address - 0x40000000) // 0x4000
            if struct.unpack_from("<Q", raw16, 0x8000 + index * 8)[0] != address | 0x783:
                raise AssertionError("16KiB image page is not read-only")
        for index in range(FB_BYTES // 0x4000):
            if struct.unpack_from("<Q", raw16, 0xc000 + index * 8)[0]:
                raise AssertionError("16KiB physical framebuffer has an identity alias")
            expected = (FB + index * 0x4000) | (0x707 if cache == "wb" else 0x703)
            if struct.unpack_from("<Q", raw16, 0x10000 + index * 8)[0] != expected:
                raise AssertionError("16KiB aperture alias does not map expected framebuffer")
        args_index = (ARGS - 0x44000000) // 0x4000
        if struct.unpack_from("<Q", raw16, 0xc000 + args_index * 8)[0] != ARGS | 0x703:
            raise AssertionError("16KiB boot arguments lost their identity mapping")
    raw, reason, boot, monitor = arguments("valid", 32)
    if (len(raw), reason, boot, monitor) != (0x10000, 0, ARGS, ARGS + 0x4000):
        raise AssertionError("argument geometry")
    if struct.unpack_from("<Q", tables("valid", "nc"), 0x1000 + 32 * 8)[0]:
        raise AssertionError("physical framebuffer unexpectedly has an identity alias")
    if MARKER_WIDTH * MARKER_HEIGHT * 4 != 32768:
        raise AssertionError("marker store-byte bound")
    original = bytes(SIZE)
    modeled = model_payload(original)
    if modeled[:RESERVED_START] != original[:RESERVED_START] or modeled[RESERVED_END:] != original[RESERVED_END:]:
        raise AssertionError("reserved-state model changed another segment")
    if modeled[RESERVED_START:RESERVED_END] != b"\xa5" * (RESERVED_END - RESERVED_START):
        raise AssertionError("reserved-state sentinel model missing")
    if model_payload(original, old_control=True) != original:
        raise AssertionError("old control payload model changed bytes")
    footprint = {y * STRIDE + x * 4 for y in range(MARKER_Y, MARKER_Y + MARKER_HEIGHT)
                 for x in range(MARKER_X, MARKER_X + MARKER_WIDTH)}
    if len(footprint) != 8192 or min(footprint) != 0x8100 or max(footprint) != 0x17efc:
        raise AssertionError("centered marker footprint")
    return {"status": "PASS", "payload_ro_pages_4k": SIZE // 0x1000,
            "reserved_sptm_ro_pages_4k": 0x54000 // 0x1000,
            "payload_ro_pages_16k": SIZE // 0x4000,
            "reserved_sptm_ro_pages_16k": 0x54000 // 0x4000,
            "reserved_sptm_sentinel_bytes": RESERVED_END - RESERVED_START,
            "reserved_sptm_sentinel_byte": hex(RESERVED_SENTINEL),
            "granules_tested_by_generators": [4096, 16384],
            "marker_pixels": len(footprint), "marker_store_bytes": 32768,
            "new_image_cases": len(trials()), "new_image_paint_cases": sum(trial[-1] for trial in trials()),
            "compiler_executed": False, "emulator_executed": False}


def trials():
    cases = []
    for mode in ("non-vhe", "vhe"):
        for cache in ("nc", "wb"):
            for depth in (30, 32):
                cases.append((mode + "-" + cache + "-" + str(depth), mode, cache, depth, "valid", True))
    for cache in ("nc", "wb"):
        for depth in (30, 32):
            cases.append(("16k-vhe-" + cache + "-" + str(depth), "16k-vhe", cache, depth, "valid", True))
    cases.append(("incoming-daif-open", "vhe", "wb", 32, "daif-open", True))
    cases.append(("incoming-daif-partial", "vhe", "wb", 32, "daif-partial", True))
    for kind in ("reason", "reason-wide", "mmu-off", "mixed-hcr", "boot-unmapped", "monitor-unmapped",
                 "count-unmapped", "table-unmapped", "count-zero", "count-large", "helper-version",
                 "video-version", "video-depth", "video-small", "video-stride", "range-wrap",
                 "range-unaligned", "range-overlap", "range-va-overlap", "range-uncovered",
                 "fb-ro-last", "fb-unmapped-last", "fb-wrong-pa", "fb-device", "image-alias", "input-alias"):
        cases.append((kind, "non-vhe", "nc", 32, kind, False))
    return cases


def case(qmp_class, qemu, payload, layout, output, trial, cc, ld, objcopy):
    label, mode, cache, depth, kind, paint = trial
    out = output / label
    out.mkdir()
    old_control = kind == "old31ae-ro-data"
    loaded_payload = model_payload(payload, old_control=old_control)
    (out / "payload.bin").write_bytes(loaded_payload)
    page_tables = tables(kind, cache, mode)
    (out / "tables.bin").write_bytes(page_tables)
    args, reason, boot, monitor = arguments(kind, depth)
    (out / "args.bin").write_bytes(args)
    target = bytes([0x35]) * FB_BYTES
    (out / "target.bin").write_bytes(target)
    scratch = b"\xa5" * 0x1000
    (out / "scratch.bin").write_bytes(scratch)
    hcr = 0x488000000 if mode in ("vhe", "16k-vhe") else 0x80000000
    if kind == "mixed-hcr":
        hcr |= 1 << 27
    tcr = 0x28099b519 if mode == "16k-vhe" else 0x280993519 if mode == "vhe" else 0x80823519
    compile_args = [cc, "-ffreestanding", "-mgeneral-regs-only", f"-DTEST_ENTRY={BASE + (OLD_ENTRY if old_control else ENTRY)}",
                    f"-DTEST_HCR={hcr}", f"-DTEST_TCR={tcr}", f"-DTEST_REASON={reason}",
                    f"-DTEST_BOOT={boot}", f"-DTEST_MONITOR={monitor}",
                    f"-DTEST_DAIF_CLEAR={15 if kind == 'daif-open' else 2 if kind == 'daif-partial' else 0}",
                    f"-DTEST_MMU={0 if kind == 'mmu-off' else 1}",
                    "-c", str(HERE / "bootstrap.S"), "-o", str(out / "bootstrap.o")]
    command(compile_args, out, "bootstrap-compile")
    command([ld, "--no-undefined", "--build-id=none", "-e", "test_bootstrap",
             f"-Ttext={BOOTSTRAP:#x}", str(out / "bootstrap.o"), "-o", str(out / "bootstrap.elf")], out, "bootstrap-link")
    command([objcopy, "-O", "binary", "-j", ".text", str(out / "bootstrap.elf"), str(out / "bootstrap.bin")], out, "bootstrap-objcopy")
    if not qemu:
        return {"case": label, "status": "PREPARED_NOT_EXECUTED", "native": "NOT_RUN"}
    sock = out / "q.sock"
    if len(str(sock).encode()) > 100:
        raise ValueError("QMP socket path too long")
    argv = [qemu, "-machine", "virt,secure=off,virtualization=on", "-cpu", "max", "-accel", "tcg",
            "-smp", "1", "-m", "256M", "-nodefaults", "-display", "none", "-nic", "none",
            "-serial", "none", "-monitor", "none", "-S", "-qmp", f"unix:{sock},server=on,wait=off"]
    for filename, physical in (("payload.bin", BASE), ("bootstrap.bin", BOOTSTRAP),
                               ("tables.bin", TABLES), ("args.bin", ARGS), ("target.bin", FB),
                               ("scratch.bin", SCRATCH)):
        argv += ["-device", f"loader,file={out / filename},addr={physical:#x},force-raw=on"]
    argv += ["-device", f"loader,addr={BOOTSTRAP:#x},cpu-num=0"]
    emit(out / "command.json", argv)
    process, qm = None, None
    started = time.monotonic()
    with (out / "qemu.log").open("wb") as log:
        try:
            process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + 15
            while qm is None:
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("QEMU startup failed")
                try:
                    qm = qmp_class(sock)
                except (FileNotFoundError, ConnectionRefusedError):
                    time.sleep(0.02)
            qm.call("cont")
            while True:
                regs, raw_registers = registers(qm)
                if regs["X27"] in (7, 0x80, 0xdead):
                    break
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("no terminal register phase: " + raw_registers[:1000])
                time.sleep(0.02)
            qm.call("stop")
            regs, raw_registers = registers(qm)
            (out / "registers.txt").write_text(raw_registers)
            expected_phase = 0xdead if old_control else 7 if paint else 0x80
            expected_status = 22 if old_control else 0 if paint else REFUSALS[kind]
            if regs["X27"] != expected_phase or regs["X28"] != expected_status:
                raise RuntimeError(f"phase/status mismatch: {regs['X27']:#x}/{regs['X28']:#x}")
            if regs["SP"] != 0:
                raise RuntimeError("payload changed incoming SP")
            if not old_control:
                expected_park = BASE + layout["symbols"]["native_park"]["offset"]
                if regs["PC"] != expected_park:
                    raise RuntimeError("terminal phase was not parked at the audited native_park")
                if kind == "daif-open" and regs.get("X18") != 0:
                    raise RuntimeError("incoming unmasked DAIF was not preserved in the diagnostic register")
                if kind == "daif-partial" and regs.get("X18") != 0x340:
                    raise RuntimeError("incoming partially masked DAIF was not preserved in the diagnostic register")
            after = qm.memory(FB, len(target), out / "target-after.bin")
            if qm.memory(BASE, len(loaded_payload), out / "payload-after.bin") != loaded_payload:
                raise RuntimeError("immutable payload was changed")
            if qm.memory(ARGS, len(args), out / "args-after.bin") != args:
                raise RuntimeError("input record was changed")
            if qm.memory(TABLES, len(page_tables), out / "tables-after.bin") != page_tables:
                raise RuntimeError("translation tables were changed")
            fault_capture = qm.memory(SCRATCH, len(scratch), out / "scratch-after.bin")
            if old_control:
                magic, esr, elr, far, spsr, incoming_sp, slot, phase = struct.unpack_from("<8Q", fault_capture)
                if (magic, elr, far, incoming_sp, slot, phase) != (SCRATCH_MAGIC, BASE + OLD_ENTRY + 0x1c,
                                                               BASE + 0x4000, 0, 4, 0xdead):
                    raise RuntimeError("old31AE first-store control did not capture the expected fault")
                if esr >> 26 != 0x25 or (esr & 0x3f) != 0x0f or not esr & (1 << 6):
                    raise RuntimeError("old31AE first store was not a current-EL write-permission abort")
                if fault_capture[64:] != scratch[64:]:
                    raise RuntimeError("fixture fatal capture exceeded its64-byte extent")
            elif fault_capture != scratch:
                raise RuntimeError("new payload entered fixture-owned early-fatal capture")
            expected = bytearray(target)
            if paint:
                if regs["X26"] != MARKER_WIDTH * MARKER_HEIGHT:
                    raise RuntimeError("incomplete paint pixel count")
                for y in range(MARKER_HEIGHT):
                    for x in range(MARKER_WIDTH):
                        offset = (MARKER_Y + y) * STRIDE + (MARKER_X + x) * 4
                        expected[offset:offset + 4] = after[offset:offset + 4]
                if bytes(expected) != after or after == target:
                    raise RuntimeError("paint footprint differs from centered128x64")
                for y in range(MARKER_HEIGHT):
                    for x in range(MARKER_WIDTH):
                        value = struct.unpack_from("<I", after, (MARKER_Y + y) * STRIDE + (MARKER_X + x) * 4)[0]
                        foreground = y < 4 or y >= 60 or x < 4 or x >= 124 or ((y ^ x) & 8)
                        wanted = (0x3fffffff if depth == 30 else 0x00ffffff) if foreground else 0
                        if value != wanted:
                            raise RuntimeError("marker pattern differs from independent expected pixels")
                if cache == "wb" and not regs["X25"]:
                    raise RuntimeError("WB paint completed without cache clean")
                if cache == "wb":
                    line = (regs["X24"] >> 16) & 0xffff
                    if not 16 <= line <= 2048 or line & (line - 1):
                        raise RuntimeError("invalid retained cache-line size")
                    expected_cleans = 0
                    for y in range(MARKER_HEIGHT):
                        start = VA + (MARKER_Y + y) * STRIDE + MARKER_X * 4
                        end = start + MARKER_WIDTH * 4
                        expected_cleans += (end - 1) // line - start // line + 1
                    if regs["X25"] != expected_cleans:
                        raise RuntimeError("WB cache-clean coverage differs from independent row intervals")
                if cache == "nc" and regs["X25"]:
                    raise RuntimeError("NC paint unexpectedly cleaned cache")
            elif after != target:
                raise RuntimeError("refusal performed a partial framebuffer operation")
            result = {"case": label, "status": "PASS", "phase": regs["X27"],
                      "diagnostic_status": regs["X28"], "mode": mode, "cache": cache,
                      "translation_granule": 16384 if mode == "16k-vhe" else 4096,
                      "fixture_tcr": hex(tcr), "fixture_hcr": hex(hcr),
                      "depth": depth, "painted_pixels": regs["X26"] if paint else 0,
                      "clean_lines": regs["X25"] if paint else 0,
                      "registers": {key: hex(value) for key, value in sorted(regs.items())},
                      "payload_unchanged": True, "reserved_sptm_readonly": True,
                      "original_payload_sha256": sha(payload), "loaded_model_sha256": sha(loaded_payload),
                      "reserved_sptm_sentinel": None if old_control else {
                          "offset": RESERVED_START, "bytes": RESERVED_END - RESERVED_START,
                          "pattern": "constant-byte", "byte": hex(RESERVED_SENTINEL), "unchanged": True},
                      "input_bytes_unchanged": len(args), "table_bytes_unchanged": len(page_tables),
                      "framebuffer_sha256": sha(after), "seconds": time.monotonic() - started,
                      "native": "NOT_RUN"}
            if old_control:
                result["old31ae_exact_payload_sha256"] = sha(payload)
                result["fault"] = {"esr": hex(esr), "elr": hex(elr), "far": hex(far),
                                   "spsr": hex(spsr), "vector_slot": slot,
                                   "conclusion": "Original first record store faults under synthetic read-only model; native cause unproven"}
            emit(out / "result.json", result)
            return result
        finally:
            if qm:
                try:
                    qm.call("quit")
                except (OSError, RuntimeError, ValueError):
                    pass
                qm.close()
            if process:
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path)
    parser.add_argument("--layout", type=Path)
    parser.add_argument("--old-payload", type=Path,
                        help="optional exact frozen31AE payload for a read-only-data first-store negative control")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--qemu")
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--ld", default="ld")
    parser.add_argument("--objcopy", default="objcopy")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    generator_check = verify_fixture_generators()
    if args.self_test:
        print(json.dumps(generator_check, sort_keys=True))
        return 0
    if not all((args.payload, args.layout, args.output)):
        parser.error("--payload, --layout and --output are required unless --self-test")
    output = args.output.resolve()
    if output.exists() or output == HERE or HERE in output.parents:
        parser.error("use a fresh output outside source directory")
    payload = args.payload.read_bytes()
    layout = json.loads(args.layout.read_text())
    if len(payload) != SIZE or layout.get("payload_sha256") != sha(payload):
        raise ValueError("payload/layout identity mismatch")
    if layout.get("symbols", {}).get("native_entry", {}).get("offset") != ENTRY:
        raise ValueError("immutable entry geometry mismatch")
    old_payload = args.old_payload.read_bytes() if args.old_payload else None
    if old_payload is not None and (len(old_payload) != OLD_SIZE or sha(old_payload) != OLD_SHA256):
        raise ValueError("old31AE negative control must match the exact frozen payload")
    output.mkdir(parents=True)
    bound = [HERE / "run.py", HERE / "bootstrap.S", HERE / "README.md", QMP_HELPER]
    bindings = [{"file": str(path.relative_to(ROOT)), "sha256": sha(path.read_bytes())} for path in bound]
    emit(output / "source-bindings.json", bindings)
    report = {"schema": "ilinux-immutable31af-runtime-v1", "status": "FAIL", "cases": [],
              "payload_sha256": sha(payload), "fixture_generators": generator_check,
              "apple_firmware": False, "native": "NOT_RUN", "monitor_calls": 0,
              "payload_executed": bool(args.qemu), "whole_payload_identity_readonly": True}
    spec = importlib.util.spec_from_file_location("qmp_immutable31af", QMP_HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        if args.qemu:
            report["qemu_version"] = subprocess.check_output([args.qemu, "--version"], text=True, timeout=30)
        for trial in trials():
            report["cases"].append(case(module.QMP, args.qemu, payload, layout, output,
                                        trial, args.cc, args.ld, args.objcopy))
        if old_payload is not None:
            report["cases"].append(case(module.QMP, args.qemu, old_payload, {}, output,
                                        ("old31ae-ro-data", "non-vhe", "nc", 32, "old31ae-ro-data", False),
                                        args.cc, args.ld, args.objcopy))
        report["status"] = "PASS" if args.qemu else "PREPARED_NOT_EXECUTED"
    finally:
        report["source_files_unchanged"] = all(sha(path.read_bytes()) == binding["sha256"]
                                             for path, binding in zip(bound, bindings))
        if not report["source_files_unchanged"]:
            report["status"] = "FAIL"
        report["source_bindings_sha256"] = sha((output / "source-bindings.json").read_bytes())
        emit(output / "results.json", report)
    print(json.dumps({"status": report["status"], "cases": len(report["cases"])}))
    return int(report["status"] == "FAIL")


if __name__ == "__main__":
    raise SystemExit(main())
