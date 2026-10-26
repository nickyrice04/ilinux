#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic, host-safe tests. No diskutil, bputil, model query or live mode."""
from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("selected31ag", HERE / "read_selected.py")
reader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reader)
TEMP_ROOT = reader.ROOT / "build/boot-object31ag-tests"
LAB_GROUP = "11111111-1111-1111-1111-111111111111"
ROOT_GROUP = "22222222-2222-2222-2222-222222222222"
LAB_UUID = "33333333-3333-3333-3333-333333333333"
ROOT_UUID = "44444444-4444-4444-4444-444444444444"
PREBOOT_UUID = "55555555-5555-5555-5555-555555555555"
COIH, NSIH = "ab" * 48, "cd" * 48
POLICY = f"Custom OS Image Hash (coih): {COIH}\nNext Stage Image Hash (nsih): {NSIH}\n".encode()
REFERENCES = {"31AF": b"original test observer", "BOOT021": b"original test rollback"}


def metadata(mount):
    lab = {"VolumeName": reader.LAB_NAME, "MountPoint": reader.LAB_MOUNT,
           "APFSVolumeGroupID": LAB_GROUP, "VolumeUUID": LAB_UUID,
           "APFSContainerReference": "disk9", "DeviceIdentifier": "disk9s1"}
    current = {"VolumeName": "Macintosh HD", "MountPoint": "/",
               "APFSVolumeGroupID": ROOT_GROUP, "VolumeUUID": ROOT_UUID}
    vols = [{"APFSVolumeUUID": LAB_UUID, "DeviceIdentifier": "disk9s1",
             "Name": reader.LAB_NAME, "Roles": ["System"]},
            {"APFSVolumeUUID": PREBOOT_UUID, "DeviceIdentifier": "disk9s2",
             "Name": "Preboot", "Roles": ["Preboot"]}]
    apfs = {"Containers": [{"ContainerReference": "disk9", "Volumes": vols}]}
    preboot = {"APFSContainerReference": "disk9", "VolumeUUID": PREBOOT_UUID,
               "DeviceIdentifier": "disk9s2", "VolumeName": "Preboot", "MountPoint": str(mount)}
    return lab, current, apfs, preboot


def tlv(tag, value):
    if len(value) < 128:
        length = bytes([len(value)])
    else:
        n = (len(value).bit_length() + 7) // 8
        length = bytes([128 + n]) + len(value).to_bytes(n, "big")
    return bytes([tag]) + length + value


def im4p(payload, trailer=b""):
    return tlv(0x30, tlv(0x16, b"IM4P") + tlv(0x16, b"krnl") +
               tlv(0x16, b"synthetic") + tlv(0x04, payload) + trailer)


def img4(payload, trailer=b""):
    return tlv(0x30, tlv(0x16, b"IMG4") + im4p(payload) + trailer)


class PolicyTests(unittest.TestCase):
    def test_selected_keys(self):
        self.assertEqual(reader.parse_policy(POLICY), {"coih": COIH, "nsih": NSIH})

    def test_hex_case_is_preserved_in_selected_path(self):
        upper = POLICY.replace(COIH.encode(), COIH.upper().encode()).replace(NSIH.encode(), NSIH.upper().encode())
        selected = reader.parse_policy(upper)
        lab, root, apfs, _ = metadata("/Volumes/SyntheticPreboot")
        path = reader.selected_path(reader.guard_target(lab, root, apfs), "/Volumes/SyntheticPreboot", selected)
        self.assertIn(NSIH.upper(), str(path))
        self.assertEqual(path.name, "kernelcache.custom." + COIH.upper())

    def test_absent_custom(self):
        data = POLICY.replace(COIH.encode(), b"absent")
        self.assertIsNone(reader.parse_policy(data)["coih"])

    def test_absent_next_with_custom_refused(self):
        with self.assertRaises(reader.Refused):
            reader.parse_policy(POLICY.replace(NSIH.encode(), b"absent"))

    def test_duplicate_even_with_malformed_second_label(self):
        for tail in [POLICY, b"extra (coih): absent\n", b"extra (nsih) bad\n"]:
            with self.subTest(tail=tail), self.assertRaises(reader.Refused):
                reader.parse_policy(POLICY + tail)

    def test_unsafe_component_and_size_refused(self):
        for value in [b"../escape", b"aa/aa", b"a" * 33, b"aa" * 65, b"aa", b"aZ" * 48, COIH.encode() + b" "]:
            with self.subTest(value=value), self.assertRaises(reader.Refused):
                reader.parse_policy(POLICY.replace(COIH.encode(), value))

    def test_missing_or_malformed_label_refused(self):
        for value in [b"", POLICY.replace(b"(coih): ", b"(coih) = "), POLICY.splitlines()[0], POLICY + b"\0"]:
            with self.subTest(value=value), self.assertRaises(reader.Refused):
                reader.parse_policy(value)

    def test_prefixes_not_interpreted_or_emitted(self):
        private_prefix = b"\xffprivate synthetic prefix "
        self.assertEqual(reader.parse_policy(private_prefix + POLICY), {"coih": COIH, "nsih": NSIH})


class MetadataTests(unittest.TestCase):
    def test_exact_target(self):
        lab, root, apfs, preboot = metadata("/Volumes/SyntheticPreboot")
        target = reader.guard_target(lab, root, apfs)
        self.assertEqual(reader.guard_preboot(target, preboot), "/Volumes/SyntheticPreboot")

    def test_wrong_name_mount_current_group_or_uuid(self):
        for key, value in [("VolumeName", "Macintosh HD"), ("MountPoint", "/"),
                           ("APFSVolumeGroupID", ROOT_GROUP), ("VolumeUUID", ROOT_UUID),
                           ("APFSVolumeGroupID", "../group")]:
            lab, root, apfs, _ = metadata("/Volumes/SyntheticPreboot")
            lab[key] = value
            with self.subTest(key=key), self.assertRaises(reader.Refused):
                reader.guard_target(lab, root, apfs)

    def test_system_role_required(self):
        for roles in [[], ["Data"], ["System", "Data"]]:
            lab, root, apfs, _ = metadata("/Volumes/SyntheticPreboot")
            apfs["Containers"][0]["Volumes"][0]["Roles"] = roles
            with self.subTest(roles=roles), self.assertRaises(reader.Refused):
                reader.guard_target(lab, root, apfs)

    def test_wrong_or_duplicate_container(self):
        for duplicate in (False, True):
            lab, root, apfs, _ = metadata("/Volumes/SyntheticPreboot")
            if duplicate:
                apfs["Containers"] *= 2
            else:
                apfs["Containers"][0]["ContainerReference"] = "disk8"
            with self.subTest(duplicate=duplicate), self.assertRaises(reader.Refused):
                reader.guard_target(lab, root, apfs)

    def test_duplicate_preboot_or_identifier(self):
        for duplicate_id in (False, True):
            lab, root, apfs, _ = metadata("/Volumes/SyntheticPreboot")
            extra = copy.deepcopy(apfs["Containers"][0]["Volumes"][1])
            if not duplicate_id:
                extra["DeviceIdentifier"] = "disk9s3"
                extra["APFSVolumeUUID"] = "66666666-6666-6666-6666-666666666666"
            apfs["Containers"][0]["Volumes"].append(extra)
            with self.subTest(duplicate_id=duplicate_id), self.assertRaises(reader.Refused):
                reader.guard_target(lab, root, apfs)

    def test_unmounted_mismatched_or_unsafe_preboot(self):
        for key, value in [("MountPoint", ""), ("MountPoint", "/"), ("MountPoint", "/Volumes/../secret"),
                           ("APFSContainerReference", "disk8"), ("VolumeUUID", LAB_UUID),
                           ("DeviceIdentifier", "disk9s99"), ("VolumeName", "Different")]:
            lab, root, apfs, preboot = metadata("/Volumes/SyntheticPreboot")
            preboot[key] = value
            with self.subTest(key=key), self.assertRaises(reader.Refused):
                reader.guard_preboot(reader.guard_target(lab, root, apfs), preboot)


class FileTests(unittest.TestCase):
    def setUp(self):
        TEMP_ROOT.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="unit-", dir=str(TEMP_ROOT))
        self.base = Path(self.temp.name).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def test_regular_bounded_read(self):
        p = self.base / "object"
        p.write_bytes(b"hello")
        self.assertEqual(reader.secure_read(p, 5), b"hello")
        with self.assertRaises(reader.Refused):
            reader.secure_read(p, 4)

    def test_symlink_file_and_parent_refused(self):
        target = self.base / "target"
        target.mkdir()
        (target / "object").write_bytes(b"hello")
        (self.base / "file-link").symlink_to(target / "object")
        (self.base / "dir-link").symlink_to(target, target_is_directory=True)
        for p in [self.base / "file-link", self.base / "dir-link/object"]:
            with self.subTest(path=p), self.assertRaises(OSError):
                reader.secure_read(p)

    def test_nonregular_and_traversal_refused(self):
        for p in [self.base, str(self.base) + "/../outside"]:
            with self.subTest(path=p), self.assertRaises((reader.Refused, OSError)):
                reader.secure_read(p)
        fifo = self.base / "fifo"
        os.mkfifo(fifo)
        with self.assertRaises(reader.Refused):
            reader.secure_read(fifo)

    def test_reference_pins_and_workspace(self):
        paths, pins = {}, {}
        for label, data in REFERENCES.items():
            p = self.base / label
            p.write_bytes(data)
            paths[label] = p
            pins[label] = (len(data), hashlib.sha256(data).hexdigest())
        with mock.patch.object(reader, "KNOWN", pins):
            self.assertEqual(reader.load_references(paths, self.base), REFERENCES)
            paths["31AF"].write_bytes(b"changed")
            with self.assertRaises(reader.Refused):
                reader.load_references(paths, self.base)
            with self.assertRaises(reader.Refused):
                reader.load_references(paths, self.base / "other-workspace")

    def test_complete_offline_fixture(self):
        preboot = self.base / "preboot"
        preboot.mkdir()
        lab, root, apfs, pi = metadata(preboot)
        target = reader.guard_target(lab, root, apfs)
        selected = reader.parse_policy(POLICY)
        obj = reader.selected_path(target, str(preboot), selected)
        obj.parent.mkdir(parents=True)
        obj.write_bytes(img4(REFERENCES["31AF"]))
        fixture = self.base / "fixture.json"
        fixture.write_text(json.dumps({"lab_info": lab, "root_info": root, "apfs_list": apfs,
                                       "preboot_info": pi, "policy_text": POLICY.decode()}))
        with mock.patch.object(reader, "capture", side_effect=AssertionError("must remain offline")):
            self.assertEqual(reader.fixture(fixture, REFERENCES), "31AF")


class DerTests(unittest.TestCase):
    def test_exact_whole_objects(self):
        for label, payload in REFERENCES.items():
            self.assertEqual(reader.identify(payload, REFERENCES), label)

    def test_im4p_and_img4_exact_payload(self):
        for label, payload in REFERENCES.items():
            for wrapped in [im4p(payload), img4(payload), img4(payload, tlv(0xa0, tlv(0x30, b"")))]:
                with self.subTest(label=label):
                    self.assertEqual(reader.identify(wrapped, REFERENCES), label)

    def test_keybag_is_ignored_not_decrypted(self):
        self.assertEqual(reader.identify(im4p(REFERENCES["BOOT021"], tlv(0x04, b"synthetic ignored keybag")), REFERENCES), "BOOT021")

    def test_manifest_private_high_tags_stay_opaque(self):
        private = b"synthetic metadata not for output"
        private_tlv = b"\xdf\x41" + bytes([len(private)]) + private
        manifest = tlv(0x30, tlv(0x16, b"IM4M") + tlv(0x31, private_tlv))
        wrapped = img4(REFERENCES["31AF"], tlv(0xa0, manifest))
        label = reader.identify(wrapped, REFERENCES)
        self.assertEqual(label, "31AF")
        self.assertNotIn(private.decode(), json.dumps({"read_only": True, "match": label}))

    def test_opaque_manifest_outer_length_still_bounded(self):
        malformed = b"\xa0\x82\x01\x00short"
        self.assertEqual(reader.identify(img4(REFERENCES["31AF"], malformed), REFERENCES), "UNKNOWN")

    def test_unknown_compressed_or_embedded_bytes(self):
        for data in [b"prefix" + REFERENCES["31AF"], im4p(b"comp" + REFERENCES["31AF"]),
                     im4p(b"unrecognized"), img4(b"unrecognized")]:
            self.assertEqual(reader.identify(data, REFERENCES), "UNKNOWN")

    def test_truncated_indefinite_nonminimal_or_trailing(self):
        valid = im4p(REFERENCES["31AF"])
        for data in [b"", valid[:-1], valid + b"extra", b"\x30\x80\0\0", b"\x30\x81\x01\0", b"\x30\x82\0\x80" + b"x" * 128,
                     b"\x3f\0", b"\x30\x84\xff\xff\xff\xff"]:
            with self.subTest(data=data[:8]):
                self.assertEqual(reader.identify(data, REFERENCES), "UNKNOWN")

    def test_depth_and_node_caps(self):
        deep = b""
        for _ in range(reader.MAX_DER_DEPTH + 2):
            deep = tlv(0x30, deep)
        many = tlv(0x30, tlv(0x04, b"") * (reader.MAX_DER_NODES + 1))
        for data in [deep, many]:
            with self.assertRaises(reader.Refused):
                reader.der_tree(data)

    def test_grammar_must_identify_direct_im4p(self):
        wrong = tlv(0x30, tlv(0x16, b"IMG4") + tlv(0x04, im4p(REFERENCES["31AF"])))
        duplicate = img4(REFERENCES["31AF"], im4p(REFERENCES["BOOT021"]))
        extra = im4p(REFERENCES["31AF"], tlv(0x16, b"unexpected"))
        for data in [wrong, duplicate, extra]:
            self.assertEqual(reader.identify(data, REFERENCES), "UNKNOWN")


class CliTests(unittest.TestCase):
    def test_default_is_help_without_any_query(self):
        out = io.StringIO()
        with mock.patch.object(reader, "capture", side_effect=AssertionError("query forbidden")), contextlib.redirect_stdout(out):
            self.assertEqual(reader.main([]), 0)
        self.assertIn("--live", out.getvalue())

    def test_nonroot_refuses_before_commands(self):
        with mock.patch.object(reader.sys, "platform", "darwin"), mock.patch.object(reader.os, "geteuid", return_value=501), \
             mock.patch.object(reader, "capture") as capture:
            with self.assertRaises(reader.Refused):
                reader.live(REFERENCES)
            capture.assert_not_called()

    def test_wrong_hardware_refuses_before_policy(self):
        with mock.patch.object(reader.sys, "platform", "darwin"), mock.patch.object(reader.os, "geteuid", return_value=0), \
             mock.patch.object(reader, "capture", return_value=b"MacBookPro18,3\n") as capture:
            with self.assertRaises(reader.Refused):
                reader.live(REFERENCES)
            self.assertEqual(capture.call_args_list, [mock.call(["/usr/sbin/sysctl", "-n", "hw.model"], 64)])

    def test_private_errors_do_not_escape(self):
        private = "/private/synthetic/identifier/not-for-output"
        for error in [OSError(private), ValueError(COIH), reader.Refused()]:
            out, err = io.StringIO(), io.StringIO()
            with mock.patch.object(reader, "load_references", side_effect=error), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(reader.main(["--live"]), 2)
            self.assertEqual(json.loads(out.getvalue()), {"read_only": True, "match": "REFUSED"})
            self.assertEqual(err.getvalue(), "")

    def test_success_output_only_label(self):
        out = io.StringIO()
        with mock.patch.object(reader, "load_references", return_value=REFERENCES), \
             mock.patch.object(reader, "live", return_value="BOOT021"), contextlib.redirect_stdout(out):
            self.assertEqual(reader.main(["--live"]), 0)
        self.assertEqual(json.loads(out.getvalue()), {"read_only": True, "match": "BOOT021"})

    def test_mock_live_queries_only_validated_lab_policy(self):
        lab, root, apfs, preboot = metadata("/Volumes/SyntheticPreboot")
        target = reader.guard_target(lab, root, apfs)
        expected_path = reader.selected_path(target, preboot["MountPoint"], reader.parse_policy(POLICY))
        queries = []

        def capture(argv, cap=reader.MAX_METADATA):
            queries.append(argv)
            if argv == ["/usr/sbin/sysctl", "-n", "hw.model"]:
                return b"Mac17,6\n"
            if argv == ["/usr/sbin/diskutil", "apfs", "list", "-plist"]:
                import plistlib
                return plistlib.dumps(apfs)
            if argv == ["/usr/bin/bputil", "-d", "-v", LAB_GROUP]:
                return POLICY
            raise AssertionError("unexpected command")

        info = {reader.LAB_MOUNT: lab, "/": root, "disk9s2": preboot}
        with mock.patch.object(reader.sys, "platform", "darwin"), mock.patch.object(reader.os, "geteuid", return_value=0), \
             mock.patch.object(reader, "capture", side_effect=capture), \
             mock.patch.object(reader, "disk_info", side_effect=lambda name: info[name]), \
             mock.patch.object(reader, "secure_open", side_effect=lambda *a, **kw: os.open(reader.ROOT, os.O_RDONLY | os.O_DIRECTORY)), \
             mock.patch.object(reader, "secure_read", return_value=im4p(REFERENCES["BOOT021"])) as read:
            self.assertEqual(reader.live(REFERENCES), "BOOT021")
        read.assert_called_once_with(expected_path)
        self.assertEqual([q for q in queries if q[0] == "/usr/bin/bputil"],
                         [["/usr/bin/bputil", "-d", "-v", LAB_GROUP]])


if __name__ == "__main__":
    unittest.main()
