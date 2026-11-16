#!/usr/bin/env python3
"""Read two generic firmware versions from the running OS's chosen node only.

No registry enumeration, policy/volume/boot-object access, writes or subprocess.
Unexpected input yields a fixed UNKNOWN, never raw bytes or exception strings.
The running OS's firmware does not identify a different installation's firmware.
"""

import ctypes
import json
import re
import sys


SCHEMA = "ilinux31ay-public-firmware-versions-v1"
CHOSEN_PATH = b"IODeviceTree:/chosen"
PROPERTY_KEYS = (b"firmware-version", b"system-firmware-version")
MAX_VERSION_BYTES = 128
UTF8 = 0x08000100
UNKNOWN = "UNKNOWN"
VERSION = re.compile(
    r"(?:mBoot|iBoot)-(?:0|[1-9][0-9]{0,9})"
    r"(?:\.(?:0|[1-9][0-9]{0,9})){1,7}\Z", re.ASCII
)
BUILD_SUFFIX_SHAPE = re.compile(VERSION.pattern[:-2] + r"~[0-9]{1,10}\Z", re.ASCII)


def parse_version(raw):
    """Admit bounded ASCII firmware versions, with at most one final NUL."""
    if not isinstance(raw, bytes) or not 1 <= len(raw) <= MAX_VERSION_BYTES + 1:
        return UNKNOWN
    if raw.endswith(b"\0"):
        raw = raw[:-1]
    if not 1 <= len(raw) <= MAX_VERSION_BYTES:
        return UNKNOWN
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError:
        return UNKNOWN
    return text if VERSION.fullmatch(text) else UNKNOWN


def _shape(kind="NOT_READ", length=None, raw=None):
    """Fixed metadata only; this never widens version admission."""
    shape = {
        "type": kind,
        "bounded_length": length if isinstance(length, int) and 0 <= length <= 129
        else "OUT_OF_BOUNDS" if length is not None else None,
        "length_unit": "UTF16_UNITS" if kind == "CFSTRING" else
        "BYTES" if kind == "CFDATA" else "NOT_READ",
        "ascii_only": None,
        "nul_count": None,
        "trailing_nul_count": None,
        "known_version_prefix": False,
        "strict_numeric_version": False,
        "numeric_version_if_nul_padding_removed": False,
        "numeric_version_with_build_suffix": False,
    }
    if not isinstance(raw, bytes) or not 1 <= len(raw) <= MAX_VERSION_BYTES + 1:
        return shape
    shape["ascii_only"] = all(byte < 128 for byte in raw)
    shape["nul_count"] = raw.count(b"\0")
    shape["trailing_nul_count"] = len(raw) - len(raw.rstrip(b"\0"))
    shape["known_version_prefix"] = raw.startswith((b"mBoot-", b"iBoot-"))
    shape["strict_numeric_version"] = parse_version(raw) != UNKNOWN
    shape["numeric_version_if_nul_padding_removed"] = parse_version(raw.rstrip(b"\0")) != UNKNOWN
    suffix_input = raw[:-1] if raw.endswith(b"\0") else raw
    try:
        shape["numeric_version_with_build_suffix"] = bool(
            BUILD_SUFFIX_SHAPE.fullmatch(suffix_input.decode("ascii"))
        )
    except UnicodeDecodeError:
        pass
    return shape


def _bind(lib, name, result, arguments):
    fn = getattr(lib, name)
    fn.restype = result
    fn.argtypes = arguments


def load_apis():
    """Load fixed system frameworks and bind only read/release functions."""
    cf = ctypes.CDLL(
        "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
    )
    io = ctypes.CDLL("/System/Library/Frameworks/IOKit.framework/IOKit")
    ptr, index, u32 = ctypes.c_void_p, ctypes.c_long, ctypes.c_uint32
    _bind(cf, "CFStringCreateWithCString", ptr, [ptr, ctypes.c_char_p, u32])
    _bind(cf, "CFGetTypeID", ctypes.c_ulong, [ptr])
    _bind(cf, "CFDataGetTypeID", ctypes.c_ulong, [])
    _bind(cf, "CFStringGetTypeID", ctypes.c_ulong, [])
    _bind(cf, "CFDataGetLength", index, [ptr])
    _bind(cf, "CFDataGetBytePtr", ctypes.POINTER(ctypes.c_uint8), [ptr])
    _bind(cf, "CFStringGetLength", index, [ptr])
    _bind(cf, "CFStringGetCString", ctypes.c_ubyte,
          [ptr, ctypes.POINTER(ctypes.c_char), index, u32])
    _bind(cf, "CFRelease", None, [ptr])
    _bind(io, "IORegistryEntryFromPath", u32, [u32, ctypes.c_char_p])
    _bind(io, "IORegistryEntryCreateCFProperty", ptr, [u32, ptr, ptr, u32])
    _bind(io, "IOObjectRelease", ctypes.c_int, [u32])
    return cf, io


def _property_version(cf, io, entry, name, shape=None):
    # Callers cannot turn this into an arbitrary-property reader.
    if name not in PROPERTY_KEYS:
        return UNKNOWN
    key = cf.CFStringCreateWithCString(None, name, UTF8)
    if not key:
        return UNKNOWN
    value = None
    try:
        value = io.IORegistryEntryCreateCFProperty(entry, key, None, 0)
        if not value:
            if shape is not None:
                shape.update(_shape("MISSING"))
            return UNKNOWN
        kind = cf.CFGetTypeID(value)
        if kind == cf.CFDataGetTypeID():
            count = cf.CFDataGetLength(value)
            if shape is not None:
                shape.update(_shape("CFDATA", count))
            if not 1 <= count <= MAX_VERSION_BYTES + 1:
                return UNKNOWN
            pointer = cf.CFDataGetBytePtr(value)
            if not pointer:
                return UNKNOWN
            raw = ctypes.string_at(pointer, count)
            if shape is not None:
                shape.update(_shape("CFDATA", count, raw))
            return parse_version(raw)
        if kind == cf.CFStringGetTypeID():
            count = cf.CFStringGetLength(value)
            if shape is not None:
                shape.update(_shape("CFSTRING", count))
            if not 1 <= count <= MAX_VERSION_BYTES:
                return UNKNOWN
            buffer = ctypes.create_string_buffer(MAX_VERSION_BYTES + 1)
            if not cf.CFStringGetCString(value, buffer, len(buffer), UTF8):
                return UNKNOWN
            # Use the full stated length, not buffer.value: embedded NULs refuse.
            raw = buffer.raw[:count]
            if shape is not None:
                shape.update(_shape("CFSTRING", count, raw))
            if b"\0" in raw:
                return UNKNOWN
            return parse_version(raw)
        if shape is not None:
            shape.update(_shape("OTHER"))
        return UNKNOWN
    finally:
        if value:
            cf.CFRelease(value)
        cf.CFRelease(key)


def result(versions=(UNKNOWN, UNKNOWN), failure=None, shapes=None):
    known = sum(version != UNKNOWN for version in versions)
    return {
        "schema": SCHEMA,
        "scope": "RUNNING_OS_AND_SYSTEM_FIRMWARE_ONLY_NOT_LAB",
        "read_only": True,
        "settings_changed": False,
        "lab_firmware_queried": False,
        "os_firmware_version": versions[0],
        "system_firmware_version": versions[1],
        "property_shapes": dict(zip(("os_firmware", "system_firmware"),
                                    shapes if shapes is not None else (_shape(), _shape()))),
        "status": "OBSERVED" if known == 2 else "PARTIAL" if known else UNKNOWN,
        "failure": failure,
    }


def read_versions(apis=None, platform=None):
    if (sys.platform if platform is None else platform) != "darwin":
        return result(failure="PLATFORM_UNSUPPORTED")
    if apis is None:
        try:
            apis = load_apis()
        except (OSError, AttributeError):
            return result(failure="API_UNAVAILABLE")
    cf, io = apis
    entry = 0
    try:
        entry = io.IORegistryEntryFromPath(0, CHOSEN_PATH)
        if not entry:
            return result(failure="CHOSEN_UNAVAILABLE")
        shapes = ({}, {})
        versions = tuple(_property_version(cf, io, entry, name, shape)
                         for name, shape in zip(PROPERTY_KEYS, shapes))
        return result(versions, "UNEXPECTED_PROPERTY" if UNKNOWN in versions else None, shapes)
    except (OSError, ValueError, TypeError, ctypes.ArgumentError):
        return result(failure="READ_UNAVAILABLE")
    finally:
        if entry:
            io.IOObjectRelease(entry)


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if args:
        print(json.dumps(result(failure="NO_ARGUMENTS_ACCEPTED"), sort_keys=True))
        return 2
    observation = read_versions()
    print(json.dumps(observation, sort_keys=True))
    return 0 if observation["status"] == "OBSERVED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
