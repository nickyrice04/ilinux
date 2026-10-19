#!/usr/bin/env python3
"""Mutation check for boot042_modules.py and its entry in make-package.py: every mutant must make
test_boot042_rule.py or test_boot042_package.py fail.

usage: python3 -I mutate_boot042.py   (from native/boot/, once the boot042 entry is applied)

The modules and their tests are copied into a temporary tree laid out like the
repository (build/, kernel/, hardware/ and virtualization/ are linked, so the
real-package and packager tests still run against this checkout). One textual
mutation is applied at a time; the test runs must then fail. Exit status 1 if one
survives.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FILES = ("boot042_modules.py", "test_boot042_rule.py", "test_boot042_package.py", "make-package.py", "mtp_input.py",
         "kconfig_guard.py", "fdt.py", "gpio_guard.py", "control_channel.py", "usb_dt.py", "entry_guard.py",
         "boot041-package-manifest.json")
LINKS = ("build", "kernel", "hardware", "virtualization")
TESTS = ("test_boot042_rule.py", "test_boot042_package.py")
MODULE = "boot042_modules.py"
PACKAGER = "make-package.py"
MUTANTS = (
    # (name, text in boot042_modules.py, replacement); the packager's are in PACKAGER_MUTANTS
    ("DT rule not applied", "        mtp_input.check_delta(before, after, sids=SIDS)\n", "        pass\n"),
    ("DT: stream 1 alone", "SIDS = (0, 1, 2, 3, 4)", "SIDS = (1,)"),
    ("DT: streams 0-3", "SIDS = (0, 1, 2, 3, 4)", "SIDS = (0, 1, 2, 3)"),
    ("config: differences ignored", "    if problems:\n", "    if False:\n"),
    ("config: NVME_CORE may stay built in", '"NVME_CORE": ("y", "m"),', '"NVME_CORE": ("y", "y"),'),
    ("config: HIDRAW not in the delta", '    "HIDRAW": ("n", "y"),\n', ""),
    ("config: any revealed line accepted", ' and name in CONFIG_REVEALED:', ":"),
    ("config: kept drivers not checked", "        if after.get(name) != value:\n", "        if False:\n"),
    ("config: APPLE_DART not kept", '{"APPLE_DART": "y", ', "{"),
    ("image: digest not pinned", "    if hashlib.sha256(image).hexdigest() != IMAGE_SHA256:\n", "    if False:\n"),
    ("image: markers not required", "    if missing:\n", "    if False:\n"),
    ("image: built-in drivers accepted", "    if present:\n", "    if False:\n"),
    ("image: NVMe match table not looked for", ' b"apple,nvme-ans2\\0",', ""),
    ("image: read-only patch not looked for", ',\n               b"iLinux read-only mode")', ")"),
    ("package: flags not required", "    if previous_package is None or authorized_key_path is None:\n",
     "    if False:\n"),
    ("package: baseline digests not checked", '            raise ValueError("prior digest mismatch: " + name)\n',
     "            pass\n"),
    ("package: DT rule not called",
     '    check_delta(properties(prior["t6050-j716c-stage-b.dtb"]), properties(data["t6050-j716c-stage-b.dtb"]))\n', ""),
    ("package: config rule not called",
     '    check_config(prior["kernel.config"].decode(), data["kernel.config"].decode())\n', ""),
    ("package: Image rule not called", '    check_image(data["Image"])\n', ""),
    ("package: key not checked",
     'entries = control_channel.check_initramfs(data["initramfs-stage-b.cpio.gz"], authorized_key)',
     'entries = control_channel.cpio_entries(data["initramfs-stage-b.cpio.gz"])'),
)


PACKAGER_MUTANTS = (
    ("packager: boot042 rule not called",
     "            authorized_key = boot042_modules.check_package(args.previous_package, args.authorized_key, baseline, data)\n",
     "            authorized_key = args.authorized_key.read_bytes()\n"),
    ("packager: more files may change",
     'allowed_changes = {"Image", "t6050-j716c-stage-b.dtb", "kernel.config"}',
     'allowed_changes = {"Image", "t6050-j716c-stage-b.dtb", "kernel.config", "initramfs-stage-b.cpio.gz", "m1n1.bin"}'),
    ("packager: boot040 as the baseline", '"ilinux-j716c-boot042": "boot041"}', '"ilinux-j716c-boot042": "boot040"}'),
    ("packager: record fields dropped", "        manifest.update(boot042_modules.manifest_fields())\n", ""),
    ("packager: record history dropped", '        manifest["linux_patches"] += boot042_modules.LINUX_PATCHES\n', ""),
)


def run_tests(tree):
    lasts = []
    for name in TESTS:
        result = subprocess.run([sys.executable, "-B", "-I", str(tree / "native/boot" / name)],
                                capture_output=True, text=True)
        lines = (result.stdout + result.stderr).strip().splitlines()
        lasts.append("%s: %s" % (name, lines[-1] if lines else ""))
        if result.returncode:
            return result.returncode, "; ".join(lasts)
    return 0, "; ".join(lasts)


def main():
    module = (HERE / MODULE).read_text()
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
        if code or "skipped" in last:
            print("the unmutated tests fail or skip; nothing to check")
            return 2
        everything = [(name, MODULE, module, old, new) for name, old, new in MUTANTS]
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
