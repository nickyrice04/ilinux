import copy
import importlib.util
import json
import pathlib
import plistlib
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("extract_config", HERE / "extract_config.py")
extract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(extract)


def sample():
    return {
        "role": "CentauriBeta", "chipset": "t2026", "protocol": "acipc",
        "main_ipc_stages": {"os": {
            "version": 768, "tr_index_count": 16, "cr_index_count": 1,
            "registers": {"ipc_status": {"bank": 0, "offset": 0}},
        }},
        "transfer_rings": {"hci-tx": {
            "id": 1, "index_array_vector": 1, "ring_size": 5,
            "exec_stage": "os", "in_place": True, "transfer_footer_size": 260,
            "doorbell": {"name": "ringdb", "selector": 1},
        }},
        "doorbells": {"ringdb": {
            "ipc_stage": "os", "mode": "index", "multi": {"count": 16},
            "register": {"bank": 0, "offset": 4096}, "vector": 0,
        }},
    }


class ExtractionTests(unittest.TestCase):
    def test_non_power_of_two_static_fact_preserved(self):
        output = extract.normalize(sample(), "CentauriBeta")
        self.assertEqual(output["transfer_rings"]["hci-tx"]["ring_size"], 5)
        self.assertNotIn("slot_stride", output["transfer_rings"]["hci-tx"])

    def test_only_allowlisted_fields_leave(self):
        document = sample()
        document["boot_ipc_stages"] = {"rom": {"secret": "synthetic-canary"}}
        document["main_ipc_stages"]["boot"] = {"data": "synthetic-canary"}
        document["main_ipc_stages"]["os"]["registers"]["unrelated"] = {"data": "synthetic-canary"}
        document["transfer_rings"]["hci-tx"]["debug"] = {"data": "synthetic-canary"}
        document["transfer_rings"]["unlisted"] = {"data": "synthetic-canary"}
        encoded = json.dumps(extract.normalize(document, "CentauriBeta"))
        self.assertNotIn("synthetic-canary", encoded)
        self.assertNotIn("boot", encoded)
        self.assertNotIn("debug", encoded)

    def test_bool_is_not_integer(self):
        document = sample()
        document["transfer_rings"]["hci-tx"]["ring_size"] = True
        with self.assertRaises(ValueError):
            extract.normalize(document, "CentauriBeta")

    def test_invalid_sizes_and_offsets(self):
        for bad in (0, -1, 1 << 64, "5", 1.5):
            document = sample()
            document["transfer_rings"]["hci-tx"]["ring_size"] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                extract.normalize(document, "CentauriBeta")
        document = sample()
        document["doorbells"]["ringdb"]["register"]["offset"] = -1
        with self.assertRaises(ValueError):
            extract.normalize(document, "CentauriBeta")

    def test_vector_at_limit_rejected(self):
        document = sample()
        document["transfer_rings"]["hci-tx"]["index_array_vector"] = 16
        with self.assertRaises(ValueError):
            extract.normalize(document, "CentauriBeta")

    def test_missing_or_invalid_references(self):
        for mutate in (
            lambda d: d["doorbells"].clear(),
            lambda d: d["transfer_rings"]["hci-tx"]["doorbell"].update(selector=16),
            lambda d: d["transfer_rings"]["hci-tx"]["doorbell"].update(name="unlisted"),
        ):
            document = sample()
            mutate(document)
            with self.assertRaises(ValueError):
                extract.normalize(document, "CentauriBeta")

    def test_control_and_other_protocols_rejected(self):
        document = sample()
        document["role"] = "CentauriControl"
        with self.assertRaises(ValueError):
            extract.normalize(document, "CentauriControl")
        for key in ("protocol", "chipset", "role"):
            document = sample()
            document[key] = "other"
            with self.assertRaises(ValueError):
                extract.normalize(document, "CentauriBeta")

    def test_other_exec_stage_rejected(self):
        document = sample()
        document["transfer_rings"]["hci-tx"]["exec_stage"] = "rom"
        with self.assertRaises(ValueError):
            extract.normalize(document, "CentauriBeta")

    def test_read_limit_and_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "synthetic.plist"
            path.write_bytes(plistlib.dumps(sample()))
            result = extract.read_source(path, "CentauriBeta")
            self.assertEqual(result["source"]["bytes"], path.stat().st_size)
            self.assertEqual(len(result["source"]["sha256"]), 64)
            path.write_bytes(b"x" * (extract.MAX_INPUT + 1))
            with self.assertRaises(ValueError):
                extract.read_source(path, "CentauriBeta")

    def test_does_not_mutate_input(self):
        document = sample()
        original = copy.deepcopy(document)
        extract.normalize(document, "CentauriBeta")
        self.assertEqual(document, original)


if __name__ == "__main__":
    unittest.main()
