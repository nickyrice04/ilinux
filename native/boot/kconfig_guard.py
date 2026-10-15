"""A package's kernel.config must be the config its Image was built with.

The Images embed that config: CONFIG_IKCONFIG=y makes kernel/configs.c carry
the gzip-compressed build .config between the markers IKCFG_ST and IKCFG_ED.
So the check needs no build tree, only the two files the package ships.

Packages boot024-035 shipped job 020's kernel.config, while the tree that
built their Images had re-detected the toolchain (rustc). Their configs differ
in toolchain-detection lines only (native/boot/kernel-config-provenance-2026-10-15.md).
They are listed in DRIFTED; every other package must match byte for byte.

usage: python3 -I kconfig_guard.py IMAGE KERNEL_CONFIG [IMAGE KERNEL_CONFIG ...]
"""
import gzip
import re
import sys

START, END = b"IKCFG_ST", b"IKCFG_ED"
DRIFTED = frozenset("ilinux-j716c-boot%03d" % n for n in (24, 25, 27, 28, 29, 30, 31, 32, 33, 34, 35))
# Kconfig symbols computed from the toolchain ($(cc-option), version probes), not options.
TOOLCHAIN = re.compile(r"(CC_VERSION_TEXT|CC_IS_GCC|CC_IS_CLANG|GCC_VERSION|CLANG_VERSION|"
                       r"AS_IS_GNU|AS_IS_LLVM|AS_VERSION|LD_IS_BFD|LD_IS_LLD|LD_VERSION|"
                       r"LLD_VERSION|RUSTC_[A-Z0-9_]+|RUST_IS_AVAILABLE|BINDGEN_VERSION_TEXT|"
                       r"PAHOLE_VERSION|CC_CAN_[A-Z0-9_]+|CC_HAS_[A-Z0-9_]+|CC_HAVE_[A-Z0-9_]+|"
                       r"AS_HAS_[A-Z0-9_]+|LD_CAN_[A-Z0-9_]+|TOOLS_SUPPORT_[A-Z0-9_]+|"
                       r"ARM64_AS_HAS_[A-Z0-9_]+|HAVE_RUST)")


def parse_config(text):
    values = {}
    for line in text.splitlines():
        if line.startswith("CONFIG_") and "=" in line:
            name, value = line[7:].split("=", 1)
            values[name] = value
        elif line.startswith("# CONFIG_") and line.endswith(" is not set"):
            values[line[9:-11]] = "n"
    return values


def config_delta(before_text, after_text):
    """{name: (before, after)} for every symbol whose value differs; absent counts as n."""
    before, after = parse_config(before_text), parse_config(after_text)
    return {name: (before.get(name, "n"), after.get(name, "n")) for name in set(before) | set(after)
            if before.get(name, "n") != after.get(name, "n")}


def toolchain_differences(before_text, after_text):
    """Names that differ; raise if any of them is a real option, not toolchain detection."""
    delta = config_delta(before_text, after_text)
    options = sorted(name for name in delta if not TOOLCHAIN.fullmatch(name))
    if options:
        raise ValueError("kernel config differs beyond toolchain detection: %s" % options[:8])
    return sorted(delta)


def embedded_config(image):
    """The build .config an arm64 Image carries (CONFIG_IKCONFIG), as bytes."""
    start = image.find(START + b"\x1f\x8b")
    if start < 0:
        raise ValueError("Image embeds no config (CONFIG_IKCONFIG off?)")
    end = image.find(END, start)
    if end < 0 or image.find(START + b"\x1f\x8b", start + 1) >= 0:
        raise ValueError("Image must embed exactly one terminated config")
    return gzip.decompress(image[start + len(START):end])


def check(package, image, kernel_config):
    """Raise unless kernel_config is the config image was built with (DRIFTED: toolchain only)."""
    embedded = embedded_config(image)
    if embedded == kernel_config:
        return []
    if package in DRIFTED:
        return toolchain_differences(kernel_config.decode(), embedded.decode())
    names = sorted(config_delta(kernel_config.decode(), embedded.decode()))
    raise ValueError("kernel.config is not the config the Image was built with: %s" % (names[:8] or
                     ["formatting only"]))


def main(argv):
    if len(argv) < 3 or len(argv) % 2 == 0:
        raise SystemExit(__doc__)
    for image_path, config_path in zip(argv[1::2], argv[2::2]):
        image, config = open(image_path, "rb").read(), open(config_path, "rb").read()
        embedded = embedded_config(image)
        if embedded == config:
            print("MATCH            %s" % image_path)
            continue
        delta = config_delta(config.decode(), embedded.decode())
        options = sorted(n for n in delta if not TOOLCHAIN.fullmatch(n))
        kind = "DIFFERS IN OPTIONS" if options else "TOOLCHAIN ONLY  "
        print("%s %s: %s" % (kind, image_path, " ".join(options or sorted(delta)) or "formatting only"))


if __name__ == "__main__":
    main(sys.argv)
