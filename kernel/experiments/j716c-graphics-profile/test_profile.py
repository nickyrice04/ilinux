#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline tests against the real immutable published config, plus mutations.

Run from the repository root. --reference is mandatory: absence of the real
third-party test data is an error, not a skipped or synthetic integration pass.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location("j716c_profile", HERE / "profile.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
REFERENCE = None
BASELINE = None


def replace_value(data, symbol, value):
    """Mutation operator; require exactly one complete source record."""
    lines = data.decode().splitlines()
    prefixes = ("CONFIG_" + symbol + "=", "# CONFIG_" + symbol + " is not set")
    found = [i for i, line in enumerate(lines)
             if line.startswith(prefixes[0]) or line == prefixes[1]]
    if len(found) != 1:
        raise AssertionError("mutation requires exactly one existing symbol")
    lines[found[0]] = ("# CONFIG_" + symbol + " is not set" if value == "n"
                       else "CONFIG_" + symbol + "=" + value)
    return ("\n".join(lines) + "\n").encode()


class ReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = p.read_config(REFERENCE)
        if hashlib.sha256(cls.raw).hexdigest() != p.REFERENCE_SHA256:
            raise AssertionError("real reference file digest does not match immutable publication")
        cls.config = p.parse(cls.raw)

    def test_real_reference_has_exact_full_hash_and_no_runtime_claim(self):
        result = p.report(self.raw)
        self.assertEqual(len(self.raw), 330809)
        self.assertEqual(len(self.config), 10123)
        self.assertTrue(result["reference_config_accepted"])
        self.assertTrue(result["critical_config_invariants_pass"])
        for key in ("native_ready", "restart_ready", "kernel_or_modules_built",
                    "Kconfig_resolved_with_matching_toolchain",
                    "performance_or_efficiency_parity_demonstrated"):
            self.assertFalse(result[key])
        self.assertEqual(set(result["runtime_gates"].values()), {"NOT_VERIFIED_BY_CONFIG"})

    def test_base_m5_option_is_unset_in_real_max_config(self):
        self.assertEqual(self.config["DRM_ASAHI_M5"], "n")
        result = p.report(replace_value(self.raw, "DRM_ASAHI_M5", "y"))
        self.assertFalse(result["reference_config_accepted"])
        self.assertIn("CONFIG_DRM_ASAHI_M5", {e["symbol"] for e in result["configuration_errors"]})

    def test_smp_and_confinement_and_page_size_fail_closed(self):
        for symbol in ("SMP", "ARM64_CTXR_EXECMEM", "ARM64_ACTLR_STATE", "ARM64_16K_PAGES"):
            with self.subTest(symbol=symbol):
                result = p.report(replace_value(self.raw, symbol, "n"))
                self.assertFalse(result["reference_config_accepted"])
                self.assertFalse(result["critical_config_invariants_pass"])
        result = p.report(replace_value(self.raw, "ARM64_4K_PAGES", "y"))
        self.assertFalse(result["critical_config_invariants_pass"])

    def test_rust_and_gpu_provider_chain_cannot_be_dropped(self):
        for symbol in ("RUST", "DRM_ASAHI", "DRM_APPLE", "RUST_DRM_GPUVM",
                       "APPLE_PMP", "APPLE_CLPC", "RUST_APPLE_RTKIT"):
            with self.subTest(symbol=symbol):
                result = p.report(replace_value(self.raw, symbol, "n"))
                self.assertFalse(result["reference_config_accepted"])
                self.assertIn("CONFIG_" + symbol,
                              {e["symbol"] for e in result["configuration_errors"]})

    def test_module_modes_are_reference_requirements(self):
        for symbol in ("DRM_ASAHI", "DRM_APPLE", "ARM_APPLE_SOC_CPUFREQ"):
            with self.subTest(symbol=symbol):
                result = p.report(replace_value(self.raw, symbol, "y"))
                self.assertFalse(result["critical_config_invariants_pass"])

    def test_nr_cpus_capacity_is_not_online_count_or_worker_count(self):
        result = p.report(self.raw)
        self.assertEqual(result["CPU_capacity"]["configured_maximum_logical_ID_count"], "512")
        self.assertEqual(result["CPU_capacity"]["published_board_physical_CPU_count"], 18)
        self.assertIsNone(result["CPU_capacity"]["observed_online_CPU_count"])
        self.assertIsNone(result["CPU_capacity"]["measurement_worker_count"])
        for count in ("18", "64", "4096"):
            with self.subTest(count=count):
                alternate = p.report(replace_value(self.raw, "NR_CPUS", count))
                self.assertTrue(alternate["critical_config_invariants_pass"])
                self.assertFalse(alternate["reference_config_accepted"])
        for count in ("17", "4097"):
            with self.subTest(count=count):
                alternate = p.report(replace_value(self.raw, "NR_CPUS", count))
                self.assertFalse(alternate["critical_config_invariants_pass"])

    def test_published_config_has_no_embedded_runtime_payload_or_commandline(self):
        for symbol in p.REQUIRED_EMPTY:
            self.assertEqual(self.config[symbol], '""')
            result = p.report(replace_value(self.raw, symbol, '"unreviewed-input"'))
            self.assertFalse(result["critical_config_invariants_pass"])

    def test_benign_unchecked_symbol_change_is_not_exact_admission(self):
        result = p.report(replace_value(self.raw, "DEFAULT_HOSTNAME", '"different"'))
        self.assertTrue(result["critical_config_invariants_pass"])
        self.assertFalse(result["exact_reference_bytes_match"])
        self.assertFalse(result["reference_config_accepted"])

    def test_missing_required_symbol_and_duplicate_are_not_implicit_disabled(self):
        data = self.raw.replace(b"CONFIG_SMP=y\n", b"", 1)
        self.assertFalse(p.report(data)["critical_config_invariants_pass"])
        with self.assertRaises(p.ConfigError):
            p.parse(self.raw + b"CONFIG_SMP=y\n")
        with self.assertRaises(p.ConfigError):
            p.parse(self.raw + b"# CONFIG_SMP is not set\n")

    def test_comparison_uses_real_31ah_config_and_is_deterministic(self):
        if BASELINE is None:
            self.fail("--diagnostic-config required for real delta integration test")
        baseline = p.read_config(BASELINE)
        self.assertEqual(hashlib.sha256(baseline).hexdigest(), p.DIAGNOSTIC_SHA256)
        a = p.report(self.raw, baseline, True)
        b = p.report(self.raw, baseline, True)
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        delta = a["diagnostic_delta"]
        self.assertTrue(delta["baseline_matches_31AH_published_manifest"])
        self.assertEqual(delta["changed_symbol_count"], len(delta["all_changes"]))
        self.assertEqual(delta["changed_symbol_count"],
                         delta["added"] + delta["removed"] + delta["changed_existing"])
        changes = {x["symbol"]: (x["before"], x["after"]) for x in delta["focused_changes"]}
        self.assertEqual(changes["CONFIG_RUST"], ("n", "y"))
        self.assertEqual(changes["CONFIG_DRM_ASAHI"], (None, "m"))
        self.assertEqual(changes["CONFIG_NR_CPUS"], ("64", "512"))
        self.assertEqual(changes["CONFIG_NVME_APPLE"], ("m", "y"))
        self.assertEqual(changes["CONFIG_ARM_APPLE_SOC_CPUFREQ"], ("y", "m"))

    def test_provenance_hashes_and_source_pins_match_tool(self):
        provenance = json.loads((HERE / "provenance.json").read_text())
        reference = provenance["reference"]
        self.assertEqual(reference["config_sha256"], p.REFERENCE_SHA256)
        self.assertEqual(reference["qualified_kernel_commit"], p.KERNEL)
        self.assertEqual(reference["publication_commit"], p.PUBLICATION)
        self.assertEqual(reference["graphics_Stage2_commit"], p.AURA_GRAPHICS_STAGE2)

    def test_cli_success_failure_and_read_only_input(self):
        with tempfile.TemporaryDirectory(prefix="j716c-profile-test-", dir=ROOT / "build") as td:
            config = Path(td) / "config"
            config.write_bytes(self.raw)
            cmd = [sys.executable, "-I", str(HERE / "profile.py"), "--config", str(config)]
            good = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertEqual(good.returncode, 0, good.stderr)
            self.assertTrue(json.loads(good.stdout)["reference_config_accepted"])
            self.assertEqual(config.read_bytes(), self.raw)
            config.write_bytes(replace_value(self.raw, "RUST", "n"))
            bad = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertEqual(bad.returncode, 1)
            self.assertFalse(json.loads(bad.stdout)["reference_config_accepted"])
            self.assertEqual(set(Path(td).iterdir()), {config})


class InputTests(unittest.TestCase):
    def test_invalid_config_input_is_data_never_an_executable(self):
        for data in (b"", b"CONFIG_X=y", b"CONFIG_X=y\x00\n", b"\xff\n",
                     b"CONFIG_X=y\r\n", b"CONFIG_X=$(touch ignored)\n",
                     b"CONFIG_X='quoted'\n", b"# CONFIG_X is not\n",
                     b"#!/bin/sh\ntouch ignored\n", b"CONFIG_X=n\n"):
            with self.subTest(data=data):
                with self.assertRaises(p.ConfigError):
                    p.parse(data)

    def test_same_symbol_in_enabled_and_disabled_form_is_duplicate(self):
        with self.assertRaises(p.ConfigError):
            p.parse(b"CONFIG_SMP=y\n# CONFIG_SMP is not set\n")

    def test_final_symlink_and_directory_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="j716c-profile-test-", dir=ROOT / "build") as td:
            root = Path(td)
            original = root / "original"
            original.write_text("CONFIG_SMP=y\n")
            link = root / "link"
            link.symlink_to(original)
            for path in (link, root):
                with self.subTest(path=path.name):
                    with self.assertRaises(p.ConfigError):
                        p.read_config(path)

    def test_overlimit_file_and_data_are_rejected(self):
        data = b"#" * (p.MAX_BYTES + 1)
        with self.assertRaises(p.ConfigError):
            p.parse(data)
        with tempfile.TemporaryDirectory(prefix="j716c-profile-test-", dir=ROOT / "build") as td:
            path = Path(td) / "oversize"
            path.write_bytes(data)
            with self.assertRaises(p.ConfigError):
                p.read_config(path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--diagnostic-config", type=Path, required=True)
    options, remaining = ap.parse_known_args()
    REFERENCE, BASELINE = options.reference, options.diagnostic_config
    unittest.main(argv=[sys.argv[0]] + remaining)
