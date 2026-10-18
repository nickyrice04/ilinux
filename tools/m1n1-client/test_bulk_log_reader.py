#!/usr/bin/env python3
"""Static and offline checks for bulk-log-reader.m, the read-only reader for the M5's bulk-only USB log port.

Run: python3 -I tools/m1n1-client/test_bulk_log_reader.py

* Static: the source must name none of the calls the read-only contract forbids (control requests,
  alternate-setting or configuration changes, clearing a stall, aborting, idle-timeout/power policy,
  device capture or seizure, opening the device object, the OUT direction, interface 1), must carry the
  fixed identity and the safe open options, and must accept no option that names a vendor, product,
  bcdDevice or endpoint.
* Refusals (need the built binary build/control/bulk-log-reader; skipped without it): they happen before
  any IOKit call, so they touch no USB device.
* Read loop (needs clang; skipped without it): test_bulk_log_reader_loop.m runs the shipped read_loop()
  against a fake pipe: data, timeouts, stalls, errors, limits. No USB is involved.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tools/m1n1-client/bulk-log-reader.m"
LOOP_TEST = ROOT / "tools/m1n1-client/test_bulk_log_reader_loop.m"
BINARY = ROOT / "build/control/bulk-log-reader"

# Every name here is a call or constant the read-only contract forbids; none may appear in the source,
# comments included.
FORBIDDEN = [
    "sendDeviceRequest", "enqueueDeviceRequest", "sendControlRequest", "enqueueControlRequest",
    "abortDeviceRequests", "abortWithOption", "abortWithError",
    "selectAlternateSetting", "clearStall", "setIdleTimeout", "adjustPipe",
    "DeviceCapture", "DeviceSeize",
    "kIOUSBEndpointDirectionOut",
    "IOUSBHostDevice",                       # the device object is never opened (or named)
    "IOUSBHostStream", "copyStream", "enqueueIORequest",
    "IOServiceOpen", "IOCreatePlugInInterfaceForService", "USBDeviceOpen", "ResetDevice", "ReEnumerate", "libusb",
    "descriptorWithType", "deviceDescriptor",   # these can fetch descriptors from the device
]
FORBIDDEN_PATTERNS = [
    (r"bInterfaceNumber\s*(==|!=|<|>|<=|>=)\s*[1-9]", "an interface number other than 0"),
    (r"interfaceNumber:\s*@\s*[1-9]", "matching interface 1"),
    (r"kInterfaceNumber\s*=\s*[1-9]", "the fixed interface number must be 0"),
]
REQUIRED = [
    "IOUSBHostObjectInitOptionsNone", "createMatchingDictionaryWithVendorID", "initWithIOService",
    "copyPipeWithAddress", "sendIORequestWithData", "ioDataWithCapacity", "kIOMessageServiceIsTerminated",
    "kUSBHostReturnPipeStalled", "0x1d6b", "0x0104", "0x0139", "0x0039", "MAX_SECONDS_ALLOWED", "3600",
    "[iface destroy]", "IOUSBGetNextEndpointDescriptor", "kIOUSBEndpointDirectionIn", "kIOUSBEndpointTypeBulk",
]
OPTIONS = {"--out", "--port", "--wait", "--seconds", "--dry-run"}


def source():
    return SOURCE.read_text()


class Static(unittest.TestCase):
    def test_source_exists(self):
        self.assertTrue(SOURCE.is_file())

    def test_no_forbidden_name_appears(self):
        text = source()
        found = [name for name in FORBIDDEN if name in text]
        self.assertEqual(found, [], "forbidden names in bulk-log-reader.m: %s" % found)

    def test_no_forbidden_pattern_appears(self):
        text = source()
        found = [why for pattern, why in FORBIDDEN_PATTERNS if re.search(pattern, text)]
        self.assertEqual(found, [], "forbidden patterns: %s" % found)

    def test_required_safe_constructs_present(self):
        text = source()
        missing = [name for name in REQUIRED if name not in text]
        self.assertEqual(missing, [], "missing: %s" % missing)

    def test_only_the_five_documented_options(self):
        literals = set(re.findall(r'"(--[a-z-]+)"', source()))
        self.assertEqual(literals, OPTIONS)

    def test_no_option_can_change_the_identity(self):
        text = source()
        for word in ("vendor", "product", "bcd", "endpoint", "address"):
            self.assertIsNone(re.search(r'"--[a-z-]*%s[a-z-]*"' % word, text), "an option mentions %s" % word)

    def test_files_are_created_exclusively(self):
        # the capture, the sidecar and the lock are all created with O_EXCL: never truncated or appended to
        self.assertGreaterEqual(source().count("O_EXCL"), 3)
        self.assertNotIn("O_TRUNC", source())
        self.assertNotIn("O_APPEND", source())

    def test_refusals_come_before_any_iokit_call(self):
        text = source()
        main = text[text.index("int main(int argc"):]
        positions = [main.find(token) for token in ("find_candidates(", "IOService", "IORegistry", "initWithIOService")]
        first_iokit = min(pos for pos in positions if pos >= 0)
        for refusal in ("--seconds is above 3600", "--out exists", "the sidecar file exists", "another instance holds the lock"):
            self.assertLess(main.index(refusal), first_iokit, refusal)

    def test_the_in_address_is_checked_before_the_pipe_is_copied(self):
        text = source()
        self.assertLess(text.index("in_addr & 0x80"), text.index("copyPipeWithAddress"))

    def test_the_pipe_is_never_given_an_out_address(self):
        # the only copyPipeWithAddress call takes the validated IN address
        calls = re.findall(r"copyPipeWithAddress:([^\s\]]+)", source())
        self.assertEqual(calls, ["in_addr"])


@unittest.skipUnless(BINARY.is_file(), "build/control/bulk-log-reader is not built")
class Refusals(unittest.TestCase):
    def run_reader(self, *args, cwd=ROOT):
        return subprocess.run([str(BINARY), *args], cwd=cwd, capture_output=True, text=True, timeout=30)

    def test_seconds_above_3600_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "cap.bin"
            r = self.run_reader("--out", str(out), "--seconds", "3601")
            self.assertEqual(r.returncode, 6, r.stderr)
            self.assertFalse(out.exists())
            self.assertFalse(Path(str(out) + ".txt").exists())

    def test_an_existing_out_is_refused_and_left_alone(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "cap.bin"
            out.write_bytes(b"keep me")
            r = self.run_reader("--out", str(out), "--dry-run", "--wait", "1")
            self.assertEqual(r.returncode, 6, r.stderr)
            self.assertEqual(out.read_bytes(), b"keep me")
            self.assertFalse(Path(str(out) + ".txt").exists())

    def test_an_unknown_option_is_refused(self):
        r = self.run_reader("--out", "/nonexistent/x.bin", "--vid", "1209")
        self.assertEqual(r.returncode, 6)

    def test_a_held_lock_refuses_a_second_instance(self):
        lock = ROOT / "build/native-intake/bulk-log-reader.lock"
        if lock.exists():
            self.skipTest("a lock file is present; not touching it")
        lock.write_text("test\n")
        try:
            with tempfile.TemporaryDirectory() as d:
                out = Path(d) / "cap.bin"
                r = self.run_reader("--out", str(out), "--dry-run", "--wait", "1")
                self.assertEqual(r.returncode, 6, r.stderr)
                self.assertFalse(out.exists())
                self.assertEqual(lock.read_text(), "test\n", "the refused instance must not remove another's lock")
        finally:
            lock.unlink()


@unittest.skipUnless(shutil.which("clang"), "clang is not available")
class ReadLoop(unittest.TestCase):
    def test_read_loop_against_a_fake_pipe(self):
        with tempfile.TemporaryDirectory() as d:
            exe = Path(d) / "loop-test"
            cc = subprocess.run(
                ["clang", "-fobjc-arc", "-O1", "-Wall", "-Wextra", "-Wno-unused-function", "-framework", "Foundation",
                 "-framework", "IOKit", "-framework", "IOUSBHost", "-I", str(ROOT / "tools/m1n1-client"),
                 "-o", str(exe), str(LOOP_TEST)], capture_output=True, text=True, timeout=240)
            self.assertEqual(cc.returncode, 0, cc.stderr)
            run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=120)
            self.assertEqual(run.returncode, 0, run.stdout[-2000:] + run.stderr[-2000:])
            self.assertIn("PASS: all read-loop scenarios", run.stdout)
            self.assertNotIn("FAIL", run.stdout)


if __name__ == "__main__":
    unittest.main()
