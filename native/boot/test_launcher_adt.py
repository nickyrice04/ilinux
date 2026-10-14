"""Offline board-gate regression using the pinned upstream ADT implementation.

Only synthetic ADT bytes and fake transport are used; no USB or target reads.
Run with tools/m1n1-client/run.sh in the prepared controller environment.
"""
import contextlib
import io
import os
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(os.environ.get("M1N1_SOURCE", HERE.parents[1] / "third_party/m1n1")) / "proxyclient"))
from m1n1.adt import PMGRDevices
from m1n1.proxyutils import LazyADT
import launch
from test_launcher import FakeInterface, FakeProxy, FakeUtils, prepared


def synthetic_adt(compatible=b"J716cAP\0"):
    def node(props, children=()):
        result = struct.pack("<II", len(props), len(children))
        for name, value in props.items():
            result += name.encode().ljust(32, b"\0") + struct.pack("<I", len(value))
            result += value + b"\0" * (-len(value) % 4)
        return result + b"".join(children)

    # The actual load_adt() initializes PMGR metadata. Supply a minimal valid
    # synthetic pair; do not patch that loader or feed it a real device dump.
    device_size = 48  # Pinned PMGRDevices record; union branches both occupy 4 bytes.
    devices = bytearray(2 * device_size)
    devices[3], devices[device_size + 3] = 1, 2  # id1
    assert [d.id1 for d in PMGRDevices.parse(bytes(devices))] == [1, 2]
    pmgr = node({"name": b"pmgr\0", "compatible": b"pmgr,synthetic\0",
                 "devices": bytes(devices)})
    arm_io = node({"name": b"arm-io\0"}, (pmgr,))
    root = {"name": b"device-tree\0"}
    if compatible is not None:
        root["compatible"] = compatible
    return node(root, (arm_io,))


class PinnedADTTests(unittest.TestCase):
    def lazy(self, compatible=b"J716cAP\0"):
        blob = synthetic_adt(compatible)
        return LazyADT(SimpleNamespace(get_adt=lambda: blob))

    def run_session(self, compatible=b"J716cAP\0"):
        self.proxy = FakeProxy()
        self.iface = FakeInterface(prepared())
        manifest = {"m1n1_version_marker": "version", "m1n1_version_offset": 0x100,
                    "m1n1_dt_pointer_offset": 0x200}
        image = bytearray(64)
        struct.pack_into("<QQ", image, 8, 0, 4096)
        files = {"Image": bytes(image), "t6050-j716c-stage-b.dtb": prepared(),
                 "initramfs-stage-b.cpio.gz": b"synthetic-initrd", "m1n1.bin": b"fixture"}

        def factory(proxy):
            utils = FakeUtils(proxy)
            utils.adt = self.lazy(compatible)
            return utils

        with contextlib.redirect_stdout(io.StringIO()), \
             patch.object(launch.dapf_guard, "prepare", return_value="test-plan"), \
             patch.object(launch.dapf_guard, "apply"):
            launch.launch_session(self.iface, self.proxy, factory, manifest, files)

    def test_old_root_lookup_reproduces_keyerror(self):
        tree = self.lazy()
        self.assertEqual(list(tree.compatible), ["J716cAP"])
        with self.assertRaisesRegex(KeyError, "Child node '' not found"):
            tree["/"].compatible

    def test_actual_root_allows_matching_board(self):
        self.run_session()
        self.assertEqual(len(self.iface.writes), 3)
        self.assertEqual(len(self.proxy.boots), 1)

    def test_wrong_board_stops_before_upload(self):
        with self.assertRaisesRegex(ValueError, "board"):
            self.run_session(b"J714cAP\0")
        self.assertEqual(self.iface.writes, [])
        self.assertEqual(self.proxy.boots, [])

    def test_missing_compatible_stops_before_upload(self):
        with self.assertRaisesRegex(ValueError, "compatibility unavailable"):
            self.run_session(None)
        self.assertEqual(self.iface.writes, [])
        self.assertEqual(self.proxy.boots, [])


if __name__ == "__main__":
    unittest.main()
