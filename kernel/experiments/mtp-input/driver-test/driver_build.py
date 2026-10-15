"""Build helpers shared by check_driver.py and mutate_driver.py (stdlib only)."""
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Every <...> include dockchannel-hid.c and dchid-ring.h make; the shim supplies the declarations.
STUB_HEADERS = [
    "linux/bitfield.h", "linux/delay.h", "linux/device.h", "linux/dma-mapping.h",
    "linux/firmware.h", "linux/gpio/consumer.h", "linux/hid.h", "linux/platform_device.h",
    "linux/slab.h", "linux/soc/apple/dockchannel.h", "linux/string.h", "linux/unaligned.h",
    "linux/of.h", "linux/moduleparam.h", "linux/mutex.h", "linux/property.h", "linux/sizes.h",
    "linux/workqueue.h", "linux/types.h", "linux/compiler.h", "asm/barrier.h",
]
WARN_OFF = ["-Wno-unused-parameter", "-Wno-sign-compare", "-Wno-missing-field-initializers",
            "-Wno-gnu-statement-expression", "-Wno-unused-function"]


def prepare_tree(work, driver_c, ring_h):
    """Lay out drivers/hid/dockchannel-hid/ plus stub headers under @work; return the dirs.

    @driver_c is a Path (a file, copied) or a str holding the SOURCE TEXT (the mutation
    harness passes mutated text). A str that names an existing file is almost certainly a
    mistake, so it is refused."""
    work = Path(work)
    tree = work / "tree" / "drivers" / "hid" / "dockchannel-hid"
    inc = work / "inc"
    tree.mkdir(parents=True, exist_ok=True)
    (tree.parent / "hid-ids.h").write_text("#define HOST_VENDOR_ID_APPLE 0x05ac\n")
    if isinstance(driver_c, str):
        if "\n" not in driver_c and Path(driver_c).exists():
            raise ValueError("pass a Path for a file; a str is taken as the source text")
        (tree / "dockchannel-hid.c").write_text(driver_c)
    else:
        shutil.copy(driver_c, tree / "dockchannel-hid.c")
    shutil.copy(ring_h, tree / "dchid-ring.h")
    for name in STUB_HEADERS:
        stub = inc / name
        stub.parent.mkdir(parents=True, exist_ok=True)
        stub.write_text("")
    return tree, inc


def compile_cmd(cc, tree, inc, source, out, sanitize=True, syntax_only=False):
    cmd = [cc, "-std=gnu11", "-g", "-Wall", "-Wextra"] + WARN_OFF
    cmd += ["-include", str(HERE / "kshim.h"), "-I", str(inc), "-I", str(tree)]
    if syntax_only:
        cmd += ["-fsyntax-only", "-Werror=implicit-function-declaration",
                "-Werror=incompatible-pointer-types", "-Werror=return-type"]
    else:
        cmd += ["-O1"]
        if sanitize:
            cmd += ["-fsanitize=address,undefined", "-fno-sanitize-recover=undefined"]
    cmd += [str(source)]
    if not syntax_only:
        cmd += ["-o", str(out)]
    return cmd


def run(cmd, timeout=300):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    return r.returncode, r.stdout, r.stderr
