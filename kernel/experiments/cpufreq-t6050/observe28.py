#!/usr/bin/env python3
"""Attempt 28 native CPU observation; explicitly NO DVFS writes or new cores.

Installed in the pinned RAM root. Run once, as root, through the bounded M1
collector. Output is JSONL; raw journals/CPU serials are never emitted. Module
loading is the sole hardware-affecting action; only reviewed command reads are
permitted by its explicit immutable no-write parameters.
"""
import hashlib
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import measurement

MODULE = "apple_soc_cpufreq"
REQUIRED = {"maxcpus=1", "nr_cpus=1", "idle=nop", "arm64.nowfxt",
            "cpufreq.default_governor=userspace", "pd_ignore_unused", "clk_ignore_unused"}


def emit(event, **values):
    print(json.dumps(dict(event=event, monotonic_s=time.monotonic(), **values), sort_keys=True), flush=True)


def read(path):
    try:
        return path.read_text().strip()
    except (OSError, UnicodeError):
        return None


def identity(root=Path("/")):
    base = root / "sys/firmware/devicetree/base"
    compatible = (base / "compatible").read_bytes().rstrip(b"\0").split(b"\0")
    words = (root / "proc/cmdline").read_text().split()
    if not {b"apple,j716c", b"apple,t6050"}.issubset(compatible):
        raise ValueError("not this J716c/t6050")
    if any(words.count(x) != 1 for x in REQUIRED) or any(x.startswith("cpufreq.off=") for x in words):
        raise ValueError("CPU observation command-line guards differ")
    if read(root / "sys/devices/system/cpu/online") != "0":
        raise ValueError("expected CPU 0 alone")
    # Linux's actual CPU0 node, rather than assuming the first ADT node booted.
    node = root / "sys/devices/system/cpu/cpu0/of_node"
    mpidr, = struct.unpack(">Q", (node / "reg").read_bytes())
    if mpidr not in {*range(0x40000, 0x40006), *range(0x40100, 0x40106), *range(0x10200, 0x10206)}:
        raise ValueError("unexpected boot CPU MPIDR")
    fields = {}
    for line in (root / "proc/cpuinfo").read_text().splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() in ("CPU implementer", "CPU architecture", "CPU variant", "CPU part", "CPU revision"):
            fields[key.strip()] = value.strip()
    return {"mpidr": hex(mpidr), "cluster": (mpidr >> 8) & 255,
            "core": mpidr & 255, "part_fields": fields,
            "kernel": read(root / "proc/sys/kernel/osrelease"), "cmdline": words}


def verify_assets(directory=HERE):
    manifest = json.loads((directory / "assets.json").read_text())
    if manifest.get("attempt") != 28 or manifest.get("frequency_writes") is not False:
        raise ValueError("wrong CPU observation asset policy")
    expected = {"apple-soc-cpufreq.ko", "cpubench", "membench", "chase_short", "measurement.py", "observe28.py"}
    if set(manifest.get("sha256", {})) != expected:
        raise ValueError("CPU asset set differs")
    for name, digest in manifest["sha256"].items():
        p = directory / name
        if p.is_symlink() or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            raise ValueError("CPU asset mismatch: " + name)
    return manifest


def command(argv, timeout):
    proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, start_new_session=True)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return proc.returncode, stdout, stderr
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()


def benchmarks(label):
    tasks = [("freq", [str(HERE / "cpubench"), "freq", "-t", "1", "-r", "3", "-s", "0.2", "-c", "0"], 15),
             ("fma_asm", [str(HERE / "cpubench"), "fma_asm", "-t", "1", "-r", "3", "-s", "0.2", "-c", "0"], 15),
             ("intmix", [str(HERE / "cpubench"), "intmix", "-t", "1", "-r", "3", "-s", "0.2", "-c", "0"], 15),
             ("stream", [str(HERE / "membench"), "stream", "-t", "1", "-m", "128", "-r", "3"], 20),
             ("chase_short", [str(HERE / "chase_short")], 50)]
    for name, argv, bound in tasks:
        start = time.monotonic()
        rc, output, _ = command(argv, bound)
        if rc:
            raise ValueError("benchmark failed: %s exit %d" % (name, rc))
        rows = [json.loads(line) for line in output.splitlines() if line.strip()]
        if not rows:
            raise ValueError("benchmark produced no results")
        emit("benchmark", phase=label, name=name, wall_s=time.monotonic()-start, results=rows)
        time.sleep(1)


def driver_state(root=Path("/")):
    params = root / "sys/module" / MODULE / "parameters"
    if read(params / "ilinux_enable_writes") != "N" or read(params / "ilinux_max_pstate") != "0":
        raise ValueError("module is not explicitly no-write/cap-zero")
    policies = measurement.snapshot(root)["policies"]
    if policies and (set(policies) != {"policy0"} or
                     policies["policy0"]["scaling_governor"] != "userspace"):
        raise ValueError("unexpected CPU policy or governor")
    return policies


def collect():
    if os.geteuid() != 0:
        raise ValueError("root is required for the single explicit no-write module load")
    ident = identity()
    assets = verify_assets()
    if Path("/sys/module/" + MODULE).exists():
        raise ValueError("CPU module was already loaded; no repeat or reload")
    fd = os.open("/run/ilinux-cpu28.started", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    os.sched_setaffinity(0, {0})
    emit("identity", identity=ident, assets=assets, semantics="observe only; no frequency or idle-state writes")
    emit("snapshot", phase="before", snapshot=measurement.snapshot())
    benchmarks("before_module")
    rc, _, _ = command(["/usr/bin/insmod", str(HERE / "apple-soc-cpufreq.ko"),
                        "ilinux_enable_writes=0", "ilinux_max_pstate=0"], 15)
    # Only our reviewed driver's command/state messages; no complete kernel log.
    _, logs, _ = command(["/usr/bin/dmesg", "--color=never"], 5)
    relevant = [s for s in logs.splitlines() if "t6050 command " in s or "boot p-state absent from OPP table" in s]
    emit("module_load", exit=rc, observations=relevant[-8:])
    if rc:
        raise ValueError("no-write module load failed; retain baseline, no retry")
    policies = driver_state()
    emit("snapshot", phase="after", snapshot=measurement.snapshot())
    # Unknown state is an informative outcome, not permission to invent a rate.
    if not policies:
        emit("done", status="OBSERVED_NO_POLICY", frequency_writes=False,
             reason="retain command/init evidence; state mapping or policy initialization unresolved")
        return 0
    benchmarks("after_no_write_module")
    driver_state()
    emit("snapshot", phase="final", snapshot=measurement.snapshot())
    emit("done", status="OBSERVED_WITH_POLICY", frequency_writes=False,
         actual_clock="benchmark estimate only; cpufreq reports requested state")
    return 0


def main():
    def expired(*_):
        raise TimeoutError("180-second CPU collection deadline")
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(180)
    try:
        return collect()
    except (OSError, ValueError, TimeoutError, subprocess.SubprocessError) as exc:
        emit("stop", reason=str(exc), frequency_writes=False)
        return 3
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    sys.exit(main())
