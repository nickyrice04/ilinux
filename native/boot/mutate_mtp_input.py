#!/usr/bin/env python3
"""Mutation check for mtp_input.py and its wiring in make-package.py: every mutant must make
test_mtp_input.py fail.

usage: python3 -I mutate_mtp_input.py

The module and its tests are copied into a temporary tree laid out like the
repository (build/, kernel/, hardware/ and virtualization/ are linked, so the
real-package and packager tests still run against this checkout). One textual
mutation is applied at a time; the test run must then fail. Exit status 1 if one
survives.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FILES = ("mtp_input.py", "test_mtp_input.py", "make-package.py", "kconfig_guard.py", "fdt.py", "gpio_guard.py",
         "control_channel.py", "usb_dt.py", "entry_guard.py", "boot036-package-manifest.json")
LINKS = ("build", "kernel", "hardware", "virtualization")
PACKAGER = "make-package.py"
MUTANTS = (
    # (name, text in mtp_input.py, replacement); the packager's are listed after PACKAGER_MUTANTS
    ("final comparison dropped", "    if expected != after:\n", "    if False:\n"),
    ("DART stays disabled in the contract", 'del expected[DART]["status"]', "pass"),
    ("dma-range not part of the contract", 'expected[DART]["apple,dma-range"] = cells(*DMA_RANGE)', "pass"),
    ("DART phandle not part of the contract", 'expected[DART]["phandle"] = cells(handle["dart"])', "pass"),
    ("keyboard alias not part of the contract", 'expected["/aliases"]["keyboard"] = strings(KEYBOARD)', "pass"),
    ("stream id 0", "SIDS = (1,)", "SIDS = (0,)"),
    ("two stream ids", "SIDS = (1,)", "SIDS = (0, 1)"),
    ("mailbox interrupts swapped", "(0x2a4, 0x2a5, 0x2a6, 0x2a7)", "(0x2a5, 0x2a4, 0x2a6, 0x2a7)"),
    ("fifo size", "FIFO_SIZE = 0x800", "FIFO_SIZE = 0x400"),
    ("dma-range window", "DMA_RANGE = (0x100, 0x4000, 0x0, 0xffff0000)", "DMA_RANGE = (0x100, 0x4000, 0x0, 0xfffe0000)"),
    ("dockchannel ranges base", '"ranges": cells(0, 0x2, 0x94b28000, 0x20000)', '"ranges": cells(0, 0x2, 0x94b2c000, 0x20000)'),
    ("hid reg", "cells(0x8000, 0x4000, 0xc000, 0x4000, 0x0, 0x4000, 0x4000, 0x4000)",
     "cells(0x8000, 0x4000, 0xc000, 0x4000, 0x0, 0x4000, 0x4000, 0x8000)"),
    ("interface dropped", '"tp_accel", "tp-accel")', '"tp_accel")'),
    ("firmware-name dropped", 'nodes[HID + "/multi-touch"]["firmware-name"] = strings(FIRMWARE_NAME)', "pass"),
    ("all-ones phandle accepted", "in (0, 0xffffffff)", "in (0,)"),
    ("zero phandle accepted", "in (0, 0xffffffff)", "in (0xffffffff,)"),
    ("duplicate phandle accepted", "    if len(set(final)) != len(final):", "    if False:"),
    ("DART power-domains accepted in the input", ' or "power-domains" in dart', ""),
    ("DART address not checked", 'dart.get("reg") != cells(*DART_REG) or ', ""),
    ("existing keyboard alias accepted", ' or "keyboard" in before["/aliases"]', ""),
    ("existing MTP node accepted", " or any(p in before for p in NEW_NODES)", ""),
    ("config: HIDRAW not required", 'CONFIG_SET = ("APPLE_RTKIT_HELPER", "HID_APPLE", "HID_MAGICMOUSE", "HIDRAW")',
     'CONFIG_SET = ("APPLE_RTKIT_HELPER", "HID_APPLE", "HID_MAGICMOUSE")'),
    ("config: revealed symbol list shortened", 'CONFIG_REVEALED = ("HID_CP2112", "HID_FT260")',
     'CONFIG_REVEALED = ("HID_CP2112",)'),
    ("config: module accepted", 'if delta[name] != ("n", "y"):', "if False:"),
    ("config: lost symbols accepted", "    if set(before) - set(after):", "    if False:"),
    ("config: driver stack not checked", "        if after.get(name) != value:", "        if False:"),
    ("config: driver stack list shortened", '"APPLE_RTKIT", "APPLE_MAILBOX", "APPLE_DART", ', '"APPLE_RTKIT", "APPLE_MAILBOX", '),
    ("config: toolchain always allowed", "toolchain = sorted(name for name in delta if allow_toolchain and TOOLCHAIN.fullmatch(name))",
     "toolchain = sorted(name for name in delta if TOOLCHAIN.fullmatch(name))"),
    ("image: poll parameter not required", ' b"dockchannel_hid.mtp_poll_ms\\0",', ""),
    ("image: t6050 compatible not required", ' b"apple,t6050-dockchannel-hid\\0",', ""),
    ("image: nothing required", "    if missing:", "    if False:"),
)


PACKAGER_MUTANTS = (
    ("packager: DT rule not called",
     '            mtp_input.check_delta(properties(prior["t6050-j716c-stage-b.dtb"]),\n'
     '                                  properties(data["t6050-j716c-stage-b.dtb"]))\n', ""),
    ("packager: config rule not called",
     '            mtp_input.check_config(prior["kernel.config"].decode(), data["kernel.config"].decode())\n', ""),
    ("packager: Image markers not checked", '            mtp_input.check_image(data["Image"])\n', ""),
    ("packager: initramfs contract not rechecked",
     '            control_channel.check_initramfs(data["initramfs-stage-b.cpio.gz"], authorized_key)\n'
     '        symbols = {', "        symbols = {"),
    ("packager: more files may change",
     'allowed_changes = {"Image", "kernel.config", "t6050-j716c-stage-b.dtb"}',
     'allowed_changes = {"Image", "kernel.config", "t6050-j716c-stage-b.dtb", "initramfs-stage-b.cpio.gz", "m1n1.bin"}'),
)


def run_tests(tree):
    result = subprocess.run([sys.executable, "-B", "-I", str(tree / "native/boot/test_mtp_input.py")],
                            capture_output=True, text=True)
    lines = (result.stdout + result.stderr).strip().splitlines()
    return result.returncode, (lines[-1] if lines else "")


def main():
    source = (HERE / "mtp_input.py").read_text()
    packager = (HERE / PACKAGER).read_text()
    survived = []
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp)
        (tree / "native/boot").mkdir(parents=True)
        for name in FILES:
            shutil.copy(HERE / name, tree / "native/boot" / name)
        for name in LINKS:
            (tree / name).symlink_to(ROOT / name)
        code, last = run_tests(tree)
        print("baseline: %s" % last)
        if code:
            print("the unmutated tests fail; nothing to check")
            return 2
        everything = [(name, "mtp_input.py", source, old, new) for name, old, new in MUTANTS]
        everything += [(name, PACKAGER, packager, old, new) for name, old, new in PACKAGER_MUTANTS]
        for name, target, text, old, new in everything:
            if text.count(old) != 1:
                print("%-48s NOT APPLICABLE (%d matches)" % (name, text.count(old)))
                survived.append(name)
                continue
            (tree / "native/boot" / target).write_text(text.replace(old, new))
            code, last = run_tests(tree)
            (tree / "native/boot" / target).write_text(text)
            print("%-48s %s" % (name, "caught" if code else "SURVIVED"))
            if not code:
                survived.append(name)
    print("%d mutants, %d survived or did not apply" % (len(everything), len(survived)))
    return 1 if survived else 0


if __name__ == "__main__":
    sys.exit(main())
