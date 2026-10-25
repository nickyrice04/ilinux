#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute original 31AB instructions on QEMU's standard ARM virt model.

No Apple firmware, monitor emulation, physical USB, network or block device.
Root orchestration must hold workspace VM/quiet locks. This is an instruction
and fault-path test, not Apple boot or CPU-start evidence.
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


class QMP:
    def __init__(self, path: Path):
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.settimeout(3)
        try:
            self.socket.connect(str(path))
        except OSError:
            self.socket.close()
            raise
        self.stream = self.socket.makefile("rb")
        greeting = json.loads(self.stream.readline())
        if "QMP" not in greeting:
            raise RuntimeError("missing QMP greeting")
        self.call("qmp_capabilities")

    def call(self, command, arguments=None):
        request = {"execute": command}
        if arguments is not None:
            request["arguments"] = arguments
        self.socket.sendall(json.dumps(request).encode() + b"\n")
        while True:
            line = self.stream.readline()
            if not line:
                raise RuntimeError("QMP closed")
            response = json.loads(line)
            if "error" in response:
                raise RuntimeError(str(response["error"]))
            if "return" in response:
                return response["return"]

    def close(self):
        self.stream.close()
        self.socket.close()


def run_case(qemu: Path, payload: bytes, bootstrap: Path, output: Path,
             label: str, base: int, el: int, park_offset: int, fault: bool, vhe: bool):
    run = output / label
    run.mkdir()
    code = bytearray(payload)
    # The recorder must initialize its own storage, not depend on loader zeros.
    code[0x4000:0x4100] = b"\xa5" * 256
    if fault:
        # Deliberate standard BRK in a test-only copy after vectors are installed.
        if struct.unpack_from("<I", code, park_offset)[0] != 0x14000000:
            raise ValueError("park symbol is not the expected self-branch")
        struct.pack_into("<I", code, park_offset, 0xD4200000)
    binary = run / "test-payload.bin"
    binary.write_bytes(code)
    sock = run / "qmp.sock"
    # macOS sockaddr_un has a short pathname limit; root supplies a short build dir.
    if len(str(sock).encode()) > 100:
        raise ValueError("output path too long for portable Unix socket")
    args = [str(qemu), "-machine", "virt,secure=off,virtualization=" + ("on" if el == 2 else "off"),
            "-accel", "tcg", "-cpu", "max", "-smp", "1", "-m", "64M",
            "-nodefaults", "-display", "none", "-nic", "none", "-serial", "none",
            "-monitor", "none", "-qmp", "unix:" + str(sock) + ",server=on,wait=off", "-S",
            "-device", f"loader,file={binary},addr={base:#x},force-raw=on",
            "-device", f"loader,file={bootstrap},addr=0x42000000,force-raw=on",
            "-device", "loader,addr=0x42000000,cpu-num=0"]
    qmp = None
    started = time.monotonic()
    with (run / "qemu.log").open("wb") as log:
        proc = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 10
            while not sock.exists():
                if proc.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("QEMU did not expose its monitor")
                time.sleep(0.02)
            while qmp is None:
                try:
                    qmp = QMP(sock)
                except (ConnectionRefusedError, FileNotFoundError):
                    if proc.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError("QEMU monitor never became ready")
                    time.sleep(0.02)
            qmp.call("cont")
            capture = run / "capture.bin"
            expected_phase = 3 if fault else 2
            while True:
                response = qmp.call("human-monitor-command", {"command-line":
                    f"pmemsave {base + 0x4000:#x} 0x100 {json.dumps(str(capture))}"})
                if response:
                    raise RuntimeError("memory observation failed: " + str(response))
                raw = capture.read_bytes()
                if len(raw) != 256:
                    raise RuntimeError("wrong capture size")
                words = struct.unpack("<32Q", raw)
                if words[2] == expected_phase:
                    break
                if time.monotonic() > deadline:
                    raise RuntimeError("entry did not reach expected diagnostic phase")
                time.sleep(0.02)
            qmp.call("stop")
            expected = {0: 0x424131334d545053, 1: 1, 2: expected_phase,
                        3: el * 4, 4: 0x3c0, 5: 0x40301000,
                        6: 0x100000000, 7: 0xaaaa111122223333, 8: 0xbbbb444455556666,
                        9: base + 0xc000, 10: base + 0xc800, 12: int(el == 2)}
            expected[11] = (0x488000000 if vhe else 0x80000000) if el == 2 else 0
            for index in range(21 if fault else 13, 32):
                expected[index] = 0
            if fault:
                expected.update({13: 4, 14: el * 4, 16: base + park_offset,
                                 19: base + 0xc000, 20: 0x3c0})
                if words[15] >> 26 != 0x3c:
                    raise RuntimeError("fault is not an AArch64 BRK")
                if words[18] & 0x3cf != 0x3c0 | (el * 4) | 1:
                    raise RuntimeError("fault saved status lost the current EL/SPx/DAIF")
            for index, value in expected.items():
                if words[index] != value:
                    raise RuntimeError(f"capture word{index}: {words[index]:#x} != {value:#x}")
            result = {"case": label, "status": "PASS", "model_el": el,
                      "base": hex(base), "phase": words[2], "capture_words": [hex(x) for x in words],
                      "vhe_fixture": vhe, "capture_preinitialized_with": "a5",
                      "test_payload_sha256": hashlib.sha256(code).hexdigest(),
                      "bootstrap_sha256": hashlib.sha256(bootstrap.read_bytes()).hexdigest(),
                      "seconds": time.monotonic() - started, "apple_firmware": False,
                      "native_cpu_start": "NOT_RUN", "monitor_calls": "NOT_RUN"}
            (run / "result.json").write_text(json.dumps(result, indent=2) + "\n")
            return result
        finally:
            if qmp:
                try:
                    qmp.call("quit")
                except (OSError, RuntimeError, ValueError):
                    pass
                qmp.close()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qemu", type=Path, required=True)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--bootstrap-dir", type=Path, required=True)
    parser.add_argument("--park-offset", type=lambda v: int(v, 0), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    raw = args.payload.read_bytes()
    if len(raw) != 0x14000 or not 0xc000 <= args.park_offset < 0xc800 or args.park_offset % 4:
        raise ValueError("unexpected payload or park geometry")
    report = {"status": "FAIL", "scope": "STANDARD_ARM_INSTRUCTION_EXECUTION",
              "native": "NOT_RUN", "apple_firmware": False, "cases": []}
    try:
        report["qemu_version"] = subprocess.check_output([str(args.qemu.resolve()), "--version"], text=True)
        report["payload_sha256"] = hashlib.sha256(raw).hexdigest()
        for el, base, fault, vhe in ((1,0x40400000,False,False),(2,0x40400000,False,False),
                (1,0x41000000,False,False),(2,0x41000000,False,False),
                (1,0x40400000,True,False),(2,0x40400000,True,False),
                (2,0x40400000,False,True),(2,0x41000000,False,True),(2,0x40400000,True,True)):
            label = f"e{el}-{base >> 20:x}-" + ("f" if fault else "e") + ("v" if vhe else "")
            report["cases"].append(run_case(args.qemu.resolve(), raw,
                (args.bootstrap_dir / (f"bootstrap-{base:x}" + ("-vhe" if vhe else "") + ".bin")).resolve(),
                args.output, label, base, el, args.park_offset, fault, vhe))
        report["status"] = "PASS"
    finally:
        (args.output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "cases": len(report["cases"]), "native": "NOT_RUN"}))


if __name__ == "__main__":
    main()
