#!/usr/bin/env python3
"""seccomp_bpf.py PROGRAM [UNISTD_H]: decode a classic-BPF seccomp program by running it.

PROGRAM is the raw sock_filter array (8 bytes per instruction), for example glycin's, as the
test overlay's bwrap wrapper records it; a file ending in .b64, or "-" for base64 on stdin, is
decoded first. The program is run for every aarch64 syscall number, with all arguments 0 and
again with other argument patterns. Prints the action for a non-aarch64 caller, the default
action, the syscalls that get any other action (grouped by action), and those whose action
depends on the arguments. UNISTD_H, an asm-generic unistd.h (the generic table arm64 uses),
names the numbers.
Standard library only.
"""
import base64
import re
import struct
import sys

AUDIT_ARCH_AARCH64 = 0xC00000B7
ACTIONS = {0x80000000: "KILL_PROCESS", 0x00000000: "KILL_THREAD", 0x00030000: "TRAP",
           0x00050000: "ERRNO", 0x7FC00000: "USER_NOTIF", 0x7FF00000: "TRACE",
           0x7FFC0000: "LOG", 0x7FFF0000: "ALLOW"}
ARG_PATTERNS = ([0] * 6, [0xFFFFFFFFFFFFFFFF] * 6, [0x5555555555555555] * 6,
                [0xAAAAAAAAAAAAAAAA] * 6, [1] * 6)


def load(path):
    data = sys.stdin.buffer.read() if path == "-" else open(path, "rb").read()
    if path == "-" or path.endswith(".b64"):
        data = base64.b64decode(data.strip())
    if not data or len(data) % 8:
        sys.exit(f"{len(data)} bytes is not a whole number of 8-byte instructions")
    return [struct.unpack_from("<HBBI", data, i) for i in range(0, len(data), 8)]


def run(prog, nr, args, arch=AUDIT_ARCH_AARCH64):
    """Return the 32-bit seccomp return value for this seccomp_data (little endian)."""
    pkt = struct.pack("<iIQ6Q", nr, arch, 0, *args)
    a = x = pc = 0
    mem = [0] * 16
    for _ in range(100000):
        code, jt, jf, k = prog[pc]
        cls = code & 0x07
        if cls == 0x00:                                   # BPF_LD
            mode = code & 0xE0
            if mode == 0x00:
                a = k
            elif mode == 0x20:
                a = struct.unpack_from("<I", pkt, k)[0]    # seccomp allows W|ABS only
            elif mode == 0x60:
                a = mem[k]
            elif mode == 0x80:
                a = len(pkt)
            else:
                raise ValueError(f"pc {pc}: load mode {mode:#x}")
        elif cls == 0x01:                                 # BPF_LDX
            mode = code & 0xE0
            x = k if mode == 0x00 else mem[k] if mode == 0x60 else len(pkt)
        elif cls == 0x02:                                 # BPF_ST
            mem[k] = a
        elif cls == 0x03:                                 # BPF_STX
            mem[k] = x
        elif cls == 0x04:                                 # BPF_ALU
            op, src = code & 0xF0, x if code & 0x08 else k
            ops = {0x00: lambda: a + src, 0x10: lambda: a - src, 0x20: lambda: a * src,
                   0x30: lambda: a // src, 0x40: lambda: a | src, 0x50: lambda: a & src,
                   0x60: lambda: a << src, 0x70: lambda: a >> src, 0x80: lambda: -a,
                   0x90: lambda: a % src, 0xA0: lambda: a ^ src}
            a = ops[op]() & 0xFFFFFFFF
        elif cls == 0x05:                                 # BPF_JMP
            op, src = code & 0xF0, x if code & 0x08 else k
            if op == 0x00:
                pc += k
            else:
                cond = {0x10: a == src, 0x20: a > src, 0x30: a >= src, 0x40: bool(a & src)}[op]
                pc += jt if cond else jf
        elif cls == 0x06:                                 # BPF_RET
            rval = code & 0x18
            return k if rval == 0x00 else a if rval == 0x10 else x
        else:                                             # BPF_MISC: TAX / TXA
            if code & 0xF8:
                a = x
            else:
                x = a
        pc += 1
    raise ValueError("program did not return")


def action(ret):
    name = ACTIONS.get(ret & 0xFFFF0000, f"{ret & 0xFFFF0000:#x}")
    return f"{name}({ret & 0xFFFF})" if name in ("ERRNO", "TRACE", "TRAP") else name


def names(path):
    table = {}
    if path:
        for m in re.finditer(r"#define\s+__NR(?:3264)?_(\w+)\s+(\d+)\b", open(path).read()):
            if m.group(1) != "syscalls":
                table.setdefault(int(m.group(2)), m.group(1))
    return table


def main():
    prog = load(sys.argv[1])
    table = names(sys.argv[2] if len(sys.argv) > 2 else None)
    label = lambda nr: table.get(nr, f"nr{nr}")
    print(f"instructions {len(prog)}")
    print(f"non-aarch64 caller: {action(run(prog, 0, ARG_PATTERNS[0], arch=0x40000003))}")
    default = run(prog, 4000, ARG_PATTERNS[0])
    print(f"default (unknown syscall 4000): {action(default)}")
    groups, dependent = {}, []
    for nr in range(0, 1024):
        results = {run(prog, nr, p) for p in ARG_PATTERNS}
        if len(results) > 1:
            dependent.append(f"{label(nr)}[{nr}] " + "/".join(sorted(action(r) for r in results)))
        else:
            groups.setdefault(results.pop(), []).append(f"{label(nr)}[{nr}]")
    for ret, members in sorted(groups.items()):
        if ret == default:
            print(f"{action(ret)}: the other {len(members)} of numbers 0-1023 (the default)")
        else:
            print(f"{action(ret)} ({len(members)}): {' '.join(members)}")
    print(f"depends on arguments ({len(dependent)}): {', '.join(dependent)}")


if __name__ == "__main__":
    main()
