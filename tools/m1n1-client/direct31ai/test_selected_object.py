#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Original synthetic framing/guard tests; no Apple calls or payload decoding."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("selected_object31ai_test", HERE / "selected_object.py")
tool = importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(tool)
BASE = tool.load_helper()  # Hash-checked original project source, pure definitions.
REFS = {"BOOT021": b"synthetic-public-boot021", "31AF": b"synthetic-public-31af"}


def der(tag, content):
    n = len(content)
    length = bytes([n]) if n < 128 else bytes([0x80 + (n.bit_length()+7)//8]) + n.to_bytes((n.bit_length()+7)//8, "big")
    return bytes([tag]) + length + content


def integer(n):
    raw = n.to_bytes(max(1, (n.bit_length()+7)//8), "big")
    if raw[0] & 0x80:raw = b"\0" + raw
    return der(2, raw)


def im4p(payload, extras=b"", kind=b"krnl", description=b"synthetic-only"):
    return der(0x30, der(0x16, b"IM4P") + der(0x16, kind) + der(0x16, description) +
               der(4, payload) + extras)


def img4(payload, contexts=b""):
    return der(0x30, der(0x16, b"IMG4") + payload + contexts)


class Framing(unittest.TestCase):
    def classify(self, data):
        return tool.classify(data, REFS, BASE)

    def test_exact_raw_references(self):
        for name, data in REFS.items():
            with self.subTest(name=name):
                r = self.classify(data)
                self.assertEqual(r["match"], name);self.assertEqual(r["framing"], "RAW")

    def test_raw_reference_starting_with_sequence_byte_is_still_exact(self):
        refs = dict(REFS, BOOT021=b"\x30-not-DER-public-fixture")
        self.assertEqual(tool.classify(refs["BOOT021"], refs, BASE)["match"], "BOOT021")

    def test_unknown_raw_no_bytes_or_hash_or_identifier_output(self):
        marker = b"SYNTHETIC_PRIVATE_MARKER"
        r = self.classify(marker);encoded = json.dumps(r)
        self.assertEqual(r["match"], "UNKNOWN")
        self.assertNotIn(marker.decode(), encoded)
        self.assertFalse(any("hash" in key or "sha" in key or "path" in key for key in r))

    def test_exact_im4p_payload(self):
        r = self.classify(im4p(REFS["BOOT021"]))
        self.assertEqual((r["match"], r["framing"], r["payload_type"]), ("BOOT021", "IM4P", "krnl"))

    def test_signed_contexts_are_opaque_not_recursed(self):
        # Deliberately not DER: context bytes must remain opaque.
        r = self.classify(img4(im4p(REFS["31AF"]), der(0xa0, b"synthetic-manifest-not-parsed") +
                              der(0xa1, b"synthetic-restore-not-parsed")))
        self.assertEqual(r["match"], "31AF")
        self.assertEqual(r["context_fields"], ["MANIFEST_A0", "RESTORE_A1"])

    def test_duplicate_or_unknown_signed_context_refused(self):
        for fields in (der(0xa0, b"one") + der(0xa0, b"two"), der(0xa2, b"not-accepted")):
            with self.subTest(fields=len(fields)):
                r = self.classify(img4(im4p(REFS["31AF"]), fields))
                self.assertEqual(r["match"], "UNKNOWN")
                self.assertEqual(r["framing"], "MALFORMED_OR_UNSUPPORTED_DER")

    def test_declared_lzfse_size_is_recognized_without_decode(self):
        extra = der(0x30, integer(1) + integer(3932160))
        r = self.classify(im4p(b"bvx2not-a-valid-compressed-stream", extra))
        self.assertEqual(r["im4p_extra"], "LZFSE_SIZE_DECLARED")
        self.assertEqual(r["declared_uncompressed_bytes"], 3932160)
        self.assertEqual(r["compression"], "LZFSE_BVX2")
        self.assertEqual(r["match"], "UNKNOWN")
        self.assertFalse(r["decompressed"])

    def test_frozen_helper_explains_unknown_for_valid_compression_sequence(self):
        data = im4p(b"bvx2synthetic", der(0x30, integer(1) + integer(3932160)))
        self.assertEqual(BASE.identify(data, REFS), "UNKNOWN")
        self.assertEqual(self.classify(data)["im4p_extra"], "LZFSE_SIZE_DECLARED")

    def test_opaque_keybag_never_parsed_or_claimed_decoded(self):
        r = self.classify(im4p(REFS["BOOT021"], der(4, b"SYNTHETIC_SECRET_MARKER")))
        self.assertEqual(r["im4p_extra"], "OPAQUE_KEYBAG_PRESENT")
        self.assertEqual(r["match"], "UNKNOWN")
        self.assertFalse(r["decompressed"]);self.assertFalse(r["decrypted"])
        self.assertNotIn("SYNTHETIC_SECRET_MARKER", json.dumps(r))

    def test_keybag_and_compression_sequence_only_report_metadata(self):
        extra = der(4, b"opaque-fixture") + der(0x30, integer(1) + integer(4096))
        r = self.classify(im4p(b"bvx1not-valid", extra))
        self.assertEqual(r["im4p_extra"], "OPAQUE_KEYBAG_AND_LZFSE_SIZE")
        self.assertEqual(r["declared_uncompressed_bytes"], 4096)
        self.assertEqual(r["match"], "UNKNOWN")

    def test_outer_zero_padding_is_explicit_not_an_exact_match(self):
        r = self.classify(img4(im4p(REFS["BOOT021"])) + bytes(32))
        self.assertEqual(r["outer_trailer"], "ZERO_PADDING")
        self.assertEqual(r["payload_relation"], "EXACT_BOOT021")
        self.assertEqual(r["match"], "UNKNOWN")

    def test_outer_nonzero_trailer_not_stripped_into_match(self):
        r = self.classify(im4p(REFS["31AF"]) + b"not-ignored")
        self.assertEqual(r["outer_trailer"], "NONZERO_TRAILER")
        self.assertEqual(r["match"], "UNKNOWN")

    def test_known_payload_padding_or_nonzero_suffix_is_only_a_relation(self):
        for suffix, expected in ((bytes(10), "BOOT021_ZERO_PADDED"),
                                 (b"not-ignored", "BOOT021_PREFIX_WITH_NONZERO_TRAILER")):
            with self.subTest(expected=expected):
                r = self.classify(im4p(REFS["BOOT021"] + suffix))
                self.assertEqual(r["payload_relation"], expected)
                self.assertEqual(r["match"], "UNKNOWN")

    def test_compression_magics_only(self):
        for magic, label in ((b"bvx2", "LZFSE_BVX2"), (b"bvx1", "LZFSE_BVX1"),
                             (b"bvx-", "LZFSE_UNCOMPRESSED_BVX_MINUS"), (b"bvxn", "LZVN_BVXN"),
                             (b"bvx$", "LZFSE_END_MARKER"), (b"complzss", "APPLE_LZSS_COMPLZSS"),
                             (b"\x1f\x8b\x08", "GZIP")):
            with self.subTest(label=label):
                r = self.classify(im4p(magic + b"not-valid-compression"))
                self.assertEqual(r["compression"], label);self.assertFalse(r["decompressed"])

    def test_unknown_type_and_private_description_not_echoed(self):
        r = self.classify(im4p(b"unknown", kind=b"abcd", description=b"SYNTHETIC_PRIVATE_DESCRIPTION"))
        self.assertEqual(r["payload_type"], "OTHER")
        self.assertNotIn("SYNTHETIC_PRIVATE_DESCRIPTION", json.dumps(r))
        self.assertNotIn("abcd", json.dumps(r))

    def test_invalid_der_length_forms_refused(self):
        for data in (b"\x30\x80\x00\x00", b"\x30\x81\x01\x00", b"\x30\x82\x00\x80" + bytes(128),
                     b"\x30\x85" + bytes(5), b"\x30\x7fshort"):
            with self.subTest(size=len(data)):
                self.assertEqual(self.classify(data)["framing"], "MALFORMED_OR_UNSUPPORTED_DER")

    def test_declared_size_and_negative_or_noncanonical_integer_refused(self):
        for second in (integer(tool.MAX_DECLARED+1), integer(0), der(2, b"\x80"), der(2, b"\0\x01")):
            with self.subTest(second=len(second)):
                data = im4p(b"bvx2x", der(0x30, integer(1)+second))
                self.assertEqual(self.classify(data)["framing"], "MALFORMED_OR_UNSUPPORTED_DER")

    def test_unknown_compression_metadata_not_treated_as_decode_authority(self):
        data = im4p(b"bvx2x", der(0x30, integer(2)+integer(4096)))
        self.assertEqual(self.classify(data)["match"], "UNKNOWN")

    def test_compression_metadata_prevents_plaintext_exact_match_claim(self):
        data = im4p(REFS["BOOT021"], der(0x30, integer(1)+integer(len(REFS["BOOT021"]))))
        self.assertEqual(self.classify(data)["match"], "UNKNOWN")

    def test_final_opaque_a0_reports_exact_payload_relation_without_envelope_claim(self):
        opaque = b"SYNTHETIC_PRIVATE_A0" + bytes(300-len(b"SYNTHETIC_PRIVATE_A0"))
        r = self.classify(img4(im4p(REFS["31AF"], der(0xa0, opaque)), der(0xa0,b"outer-opaque")))
        self.assertEqual(r["framing"], "IMG4")
        self.assertEqual(r["im4p_extra"], "OPAQUE_CONTEXT_A0")
        self.assertEqual(r["payload_relation"], "EXACT_31AF")
        self.assertEqual(r["match"], "UNKNOWN")
        self.assertFalse(r["opaque_extra_semantics_verified"])
        self.assertFalse(r["restoration_verified"])
        self.assertIsNone(r["der_diagnostic"])
        self.assertNotIn("SYNTHETIC_PRIVATE_A0", json.dumps(r))

    def test_opaque_a0_is_never_traversed_even_when_not_valid_inner_der(self):
        r = self.classify(im4p(REFS["BOOT021"], der(0xa0,b"\xff\x80not-valid-DER")))
        self.assertEqual(r["im4p_extra"], "OPAQUE_CONTEXT_A0")
        self.assertEqual(r["payload_relation"], "EXACT_BOOT021")
        self.assertEqual(r["match"], "UNKNOWN")
        self.assertNotIn("not-valid", json.dumps(r))

    def test_opaque_a0_after_supported_optional_forms(self):
        keybag = der(4,b"private-keybag-fixture")
        size = der(0x30,integer(1)+integer(4096))
        for prefix, suffix in ((b"",""),(keybag,"_WITH_KEYBAG"),
                               (size,"_WITH_LZFSE_SIZE"),
                               (keybag+size,"_WITH_KEYBAG_AND_LZFSE_SIZE")):
            with self.subTest(suffix=suffix):
                r = self.classify(im4p(REFS["BOOT021"],prefix+der(0xa0,b"opaque")))
                self.assertEqual(r["im4p_extra"],"OPAQUE_CONTEXT_A0"+suffix)
                self.assertEqual(r["payload_relation"],"EXACT_BOOT021")
                self.assertEqual(r["match"],"UNKNOWN")

    def test_duplicate_opaque_a0_is_still_unsupported(self):
        r = self.classify(im4p(REFS["31AF"],der(0xa0,b"one")+der(0xa0,b"two")))
        self.assertEqual(r["framing"],"MALFORMED_OR_UNSUPPORTED_DER")
        self.assertEqual(r["match"],"UNKNOWN")
        self.assertIsNotNone(r["der_diagnostic"])

    def test_other_context_tags_or_primitive_context_zero_not_admitted(self):
        for tag in (0xa1,0x80,0x60):
            with self.subTest(tag=tag):
                r=self.classify(im4p(REFS["BOOT021"],der(tag,b"opaque")))
                self.assertEqual(r["framing"],"MALFORMED_OR_UNSUPPORTED_DER")
                self.assertEqual(r["match"],"UNKNOWN")

    def test_opaque_a0_must_be_final_and_prior_optional_order_stays_strict(self):
        a0=der(0xa0,b"opaque");keybag=der(4,b"opaque-keybag")
        size=der(0x30,integer(1)+integer(4096))
        for extras in (a0+keybag,a0+size,size+keybag+a0):
            with self.subTest(size=len(extras)):
                r=self.classify(im4p(REFS["31AF"],extras))
                self.assertEqual(r["framing"],"MALFORMED_OR_UNSUPPORTED_DER")
                self.assertEqual(r["match"],"UNKNOWN")

    def test_opaque_a0_has_conservative_content_bound(self):
        r=self.classify(im4p(REFS["BOOT021"],der(0xa0,bytes(tool.MAX_OPAQUE_EXTRA+1))))
        self.assertEqual(r["framing"],"MALFORMED_OR_UNSUPPORTED_DER")
        self.assertEqual(r["der_diagnostic"]["failure_stage"],"IM4P_EXTRA_METADATA")
        self.assertEqual(r["match"],"UNKNOWN")

    def test_empty_opaque_a0_still_never_becomes_an_identity_match(self):
        r=self.classify(im4p(REFS["BOOT021"],der(0xa0,b"")))
        self.assertEqual(r["im4p_extra"],"OPAQUE_CONTEXT_A0")
        self.assertEqual(r["payload_relation"],"EXACT_BOOT021")
        self.assertEqual(r["match"],"UNKNOWN")

    def test_unknown_payload_with_a0_never_echoes_content_or_hash(self):
        r=self.classify(im4p(b"SYNTHETIC_PRIVATE_PAYLOAD",der(0xa0,b"SYNTHETIC_PRIVATE_PROPERTIES")))
        self.assertEqual(r["match"],"UNKNOWN")
        self.assertEqual(r["payload_relation"],"NOT_KNOWN")
        self.assertNotIn("SYNTHETIC_PRIVATE",json.dumps(r))
        self.assertFalse(any("hash" in key or "sha" in key or "path" in key for key in r))

    def test_der_node_budget(self):
        data = der(0x30, b"".join(der(0x16, b"x") for _ in range(BASE.MAX_DER_NODES+1)))
        self.assertEqual(self.classify(data)["framing"], "MALFORMED_OR_UNSUPPORTED_DER")

    def test_high_tag_in_untagged_manifest_reports_only_shallow_container(self):
        high = b"\x7f\x81\x48\x03ABC"
        manifest = der(0x30, der(0x16, b"IM4M") + high)
        r = self.classify(img4(im4p(REFS["BOOT021"]), manifest))
        d = r["der_diagnostic"]
        self.assertEqual(r["match"], "UNKNOWN")
        self.assertEqual(d["failure_stage"], "FROZEN_DER_TREE")
        self.assertTrue(d["root_magic_is_img4"]);self.assertTrue(d["im4p_magic_matches"])
        self.assertEqual(len(d["top_fields"]), 3)
        self.assertEqual(d["top_fields"][2]["tag_number"], 16)
        self.assertFalse(d["manifest_or_payload_descended"])
        self.assertNotIn("IM4M", json.dumps(d));self.assertNotIn("ABC", json.dumps(d))

    def test_direct_high_tag_number_is_hidden_but_framing_is_measured(self):
        r = self.classify(img4(im4p(REFS["31AF"]), b"\xbf\x1f\x03ABC"))
        last = r["der_diagnostic"]["top_fields"][-1]
        self.assertEqual(last["tag_number"], "HIGH")
        self.assertTrue(last["tag_canonical"])
        self.assertEqual(last["content_bytes"], 3)
        self.assertEqual(r["match"], "UNKNOWN")

    def test_noncanonical_high_tag_does_not_relax_matching(self):
        r = self.classify(img4(im4p(REFS["BOOT021"]), b"\x9f\x80\x1f\x01x"))
        d = r["der_diagnostic"]
        self.assertFalse(d["top_fields"][-1]["tag_canonical"])
        self.assertFalse(d["top_fields_complete"])
        self.assertEqual(r["match"], "UNKNOWN")

    def test_noncanonical_root_length_has_explicit_failure_stage(self):
        r = self.classify(b"\x30\x81\x01x")
        d = r["der_diagnostic"]
        self.assertEqual(d["failure_stage"], "OUTER_EXTENT")
        self.assertFalse(d["root_header"]["length_canonical"])
        self.assertEqual(d["root_header"]["content_bytes"], 1)
        self.assertEqual(d["top_fields"], [])

    def test_child_length_noncanonical_or_escaping_stops_outline(self):
        for field in (b"\x16\x81\x04IMG4", b"\x16\x7fshort"):
            with self.subTest(size=len(field)):
                r = self.classify(der(0x30, field))
                d = r["der_diagnostic"]
                self.assertEqual(d["failure_stage"], "FROZEN_DER_TREE")
                self.assertFalse(d["top_fields_complete"])
                self.assertEqual(len(d["top_fields"]), 1)
                self.assertEqual(r["match"], "UNKNOWN")

    def test_shallow_child_lists_stop_at_eight(self):
        r = self.classify(img4(im4p(REFS["BOOT021"]), der(0x16, b"not-printed")*20))
        d = r["der_diagnostic"]
        self.assertEqual(d["failure_stage"], "IMG4_FIELDS")
        self.assertEqual(len(d["top_fields"]), 8)
        self.assertFalse(d["top_fields_complete"])
        self.assertNotIn("not-printed", json.dumps(d))

    def test_unsupported_fields_still_never_expose_description_payload_or_keybag(self):
        extras = (der(4, b"SYNTHETIC_PRIVATE_KEYBAG") + der(0x30, integer(1)+integer(4096)) +
                  der(4, b"SYNTHETIC_PRIVATE_EXTRA"))
        r = self.classify(im4p(b"SYNTHETIC_PRIVATE_PAYLOAD", extras,
                               description=b"SYNTHETIC_PRIVATE_DESCRIPTION"))
        d = r["der_diagnostic"]
        self.assertEqual(d["failure_stage"], "COMPRESSION_METADATA")
        self.assertTrue(d["root_magic_is_im4p"])
        self.assertLessEqual(len(d["im4p_fields"]), 8)
        self.assertNotIn("SYNTHETIC_PRIVATE", json.dumps(r))
        self.assertEqual(r["match"], "UNKNOWN")

    def test_unsupported_compression_metadata_only_reports_field_headers(self):
        r = self.classify(im4p(b"not-printed", der(0x30, integer(2)+integer(0x123456))))
        d = r["der_diagnostic"]
        self.assertEqual(d["failure_stage"], "COMPRESSION_METADATA")
        self.assertEqual(len(d["im4p_fields"]), 5)
        self.assertNotIn(str(0x123456), json.dumps(d))

    def test_unsupported_outline_records_extent_and_trailer_without_normalizing(self):
        value = img4(im4p(REFS["BOOT021"]), der(0x16,b"unsupported"))
        r = self.classify(value + bytes(12))
        d = r["der_diagnostic"]
        self.assertEqual(d["framed_extent_bytes"], len(value))
        self.assertEqual(d["outer_trailer"], "ZERO_PADDING")
        self.assertEqual(r["match"], "UNKNOWN")

    def test_excess_length_octets_only_report_header_facts(self):
        r = self.classify(b"\x30\x85"+bytes(5))
        d = r["der_diagnostic"]
        self.assertEqual(d["failure_stage"], "OUTER_EXTENT")
        self.assertEqual(d["root_header"]["length_octets"],6)
        self.assertIsNone(d["root_header"]["content_bytes"])
        self.assertEqual(d["top_fields"], [])

    def test_unknown_file_size_is_not_an_identity(self):
        r = self.classify(bytes(445430))
        self.assertEqual(r["file_bytes"],445430)
        self.assertEqual(r["match"],"UNKNOWN")

    def test_empty_or_oversize_input_refused(self):
        for data in (b"", bytes(tool.MAX_FILE+1)):
            with self.assertRaises(tool.Refusal):self.classify(data)

    def test_all_output_is_only_metadata_not_hardware_authority(self):
        r = self.classify(im4p(REFS["BOOT021"]))
        for key in ("restoration_verified", "bootability_verified", "default_selection_verified",
                    "decompressed", "decrypted"):
            self.assertIs(r[key], False)


class Guards(unittest.TestCase):
    def test_default_help_never_loads_helper_or_calls_host(self):
        with mock.patch.object(tool, "load_helper") as loader, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(tool.main([]), 0)
            loader.assert_not_called()

    def test_helper_hash_mismatch_stops_before_execution(self):
        with mock.patch.object(tool, "HELPER_SHA256", "0"*64):
            with self.assertRaises(tool.Refusal):tool.load_helper()

    def test_live_nonroot_guard_precedes_host_query(self):
        with mock.patch.object(tool.sys, "platform", "darwin"), mock.patch.object(tool.os, "geteuid", return_value=501), \
             mock.patch.object(BASE, "capture") as capture:
            with self.assertRaises(BASE.Refused):tool.live(BASE, REFS)
            capture.assert_not_called()

    def test_live_wrong_machine_stops_before_volume_access(self):
        with mock.patch.object(tool.sys, "platform", "darwin"), mock.patch.object(tool.os, "geteuid", return_value=0), \
             mock.patch.object(BASE, "capture", return_value=b"Mac14,2\n") as capture, \
             mock.patch.object(BASE, "secure_open") as opened:
            with self.assertRaises(BASE.Refused):tool.live(BASE, REFS)
            opened.assert_not_called();self.assertEqual(capture.call_count, 1)

    def test_live_uses_same_guarded_selected_path(self):
        target = {"group":"synthetic-group","preboot":{"DeviceIdentifier":"synthetic-device"}}
        base = types.SimpleNamespace(require=BASE.require, Refused=BASE.Refused,
            LAB_MOUNT=BASE.LAB_MOUNT, MAX_POLICY=BASE.MAX_POLICY, der_tree=BASE.der_tree,
            capture=mock.Mock(side_effect=[b"Mac17,6\n", b"synthetic-apfs", b"synthetic-policy"]),
            disk_info=mock.Mock(side_effect=["lab","original","preboot"]),
            guard_target=mock.Mock(return_value=target),guard_preboot=mock.Mock(return_value="synthetic-mount"),
            secure_open=mock.Mock(return_value=99),parse_policy=mock.Mock(return_value={"coih":"synthetic","nsih":"synthetic"}),
            selected_path=mock.Mock(return_value="synthetic-selected-only"),secure_read=mock.Mock(return_value=im4p(b"bvx2fixture")),
            plistlib=types.SimpleNamespace(loads=mock.Mock(return_value="synthetic-apfs-parsed")))
        with mock.patch.object(tool.sys,"platform","darwin"),mock.patch.object(tool.os,"geteuid",return_value=0), \
             mock.patch.object(tool.os,"close"):
            r=tool.live(base,REFS)
        base.guard_target.assert_called_once_with("lab","original","synthetic-apfs-parsed")
        base.guard_preboot.assert_called_once_with(target,"preboot")
        base.secure_read.assert_called_once_with("synthetic-selected-only",tool.MAX_FILE)
        self.assertEqual(r["compression"],"LZFSE_BVX2")
        self.assertNotIn("synthetic-selected-only",json.dumps(r))

    def test_fixture_outside_workspace_is_refused_without_read(self):
        base=types.SimpleNamespace(load_references=mock.Mock(return_value=REFS),DEFAULT_REFERENCES={},secure_read=mock.Mock())
        out=io.StringIO()
        with mock.patch.object(tool,"load_helper",return_value=base),contextlib.redirect_stdout(out):
            self.assertEqual(tool.main(["--fixture","/synthetic-outside-workspace/file"]),2)
        base.secure_read.assert_not_called();self.assertNotIn("synthetic-outside",out.getvalue())

    def test_private_exception_details_suppressed(self):
        out=io.StringIO()
        with mock.patch.object(tool,"load_helper",side_effect=RuntimeError("SYNTHETIC_PRIVATE_PATH")),contextlib.redirect_stdout(out):
            self.assertEqual(tool.main(["--live"]),2)
        r=json.loads(out.getvalue());self.assertEqual(r["match"],"REFUSED")
        self.assertNotIn("SYNTHETIC_PRIVATE_PATH",out.getvalue())


if __name__ == "__main__":
    unittest.main()
