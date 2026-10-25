#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline stub tests. No real kmutil, network, policy or disk tool is invoked."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("render31ad", HERE / "render.py")
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


class Workflow(unittest.TestCase):
    def profile(self):
        return {"schema": "ilinux31ad-diagnose-v1", "images": {
            "flat31ac": {"bytes": render.ORIGINAL[0], "sha256": render.ORIGINAL[1],
                         "url": "https://example.invalid/flat31ac"},
            "nested31ad": {"bytes": 196608, "sha256": "a" * 64,
                           "url": "https://example.invalid/nested31ad"},
            "rawboot021": {"bytes": render.ROLLBACK[0], "sha256": render.ROLLBACK[1],
                           "url": "https://example.invalid/rawboot021"}}}

    def test_strict_profile_refusals(self):
        for change in ("pin", "role", "url", "size", "hash", "schema", "extra"):
            p = self.profile()
            if change == "pin": p["images"]["flat31ac"]["sha256"] = "b" * 64
            if change == "role": del p["images"]["rawboot021"]
            if change == "url": p["images"]["nested31ad"]["url"] = "https://user:secret@example.invalid/a"
            if change == "size": p["images"]["nested31ad"]["bytes"] = True
            if change == "hash": p["images"]["nested31ad"]["sha256"] = "bogus"
            if change == "schema": p["schema"] = "unknown"
            if change == "extra": p["authorize_write"] = True
            with self.subTest(change=change), self.assertRaises(ValueError):
                render.render(p)

    def test_single_complete_block_and_html(self):
        block = render.render(self.profile())
        self.assertEqual(block.count("/bin/bash <<'ILINUX31AD_DIAGNOSE_END'"), 1)
        self.assertTrue(block.endswith("ILINUX31AD_DIAGNOSE_END\n"))
        self.assertNotIn("/usr/bin/kmutil configure-boot", block)
        self.assertNotIn("bputil", block)
        self.assertNotIn("diskutil", block)
        self.assertNotIn("reboot", block)
        self.assertIn("No installation", block)
        self.assertIn("&lt;", render.page(block))
        self.assertIn("NOT RUN", render.page(block))
        result = subprocess.run(["/bin/bash", "-n"], input=block, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def stub_run(self, mode="normal"):
        with tempfile.TemporaryDirectory(prefix="recovery31ad-test-") as tmp:
            root = Path(tmp)
            fixtures = root / "fixtures"
            fixtures.mkdir()
            images = {role: ("ORIGINAL_TEST_DATA_" + role).encode() for role in render.ROLES}
            for name, data in images.items(): (fixtures / name).write_bytes(data)
            pins = {role: (len(data), hashlib.sha256(data).hexdigest()) for role, data in images.items()}
            profile = {"schema": "ilinux31ad-diagnose-v1", "images": {
                role: {"bytes": pins[role][0], "sha256": pins[role][1],
                       "url": "https://example.invalid/" + role} for role in render.ROLES}}
            with patch.object(render, "ORIGINAL", pins["flat31ac"]), patch.object(render, "ROLLBACK", pins["rawboot021"]):
                block = render.render(profile)
            stub = {
                "curl": '''#!/bin/bash
out=''
while test "$#" -gt 0; do
 case "$1" in --output) out="$2"; shift 2;; *) url="$1"; shift;; esac
done
role="${url##*/}"
case "$STUB_MODE" in transfer) exit 22;; symlink) ln -s "$FIXTURES/$role" "$out";; corrupt) printf bad >"$out";; hash) cp "$FIXTURES/$role" "$out"; printf X | dd of="$out" bs=1 count=1 conv=notrunc 2>/dev/null;; *) cp "$FIXTURES/$role" "$out";; esac
''',
                "kmutil": '''#!/bin/bash
printf '%s\\0' "$@" >>"$CALL_LOG"
test "$1" = inspect || exit 99
while test "$#" -gt 0; do
 if test "$1" = -B; then image="$2"; shift 2; else shift; fi
done
case "$image" in *nested31ad.macho) printf 'fixture properties\\n'; exit 0;; *) printf 'fixture fileset rejection\\n' >&2; exit 71;; esac
''',
                "mktemp": '#!/bin/bash\nmkdir "$EVIDENCE" || exit 1\nprintf "%s\\n" "$EVIDENCE"\n',
                "sw_vers": '#!/bin/bash\nprintf "FIXTURE_VERSION_ONLY\\n"\n',
            }
            for name, text in stub.items():
                file = root / name
                file.write_text(text)
                file.chmod(0o700)
                block = block.replace("/usr/bin/" + name, str(file))
            env = dict(os.environ, FIXTURES=str(fixtures), EVIDENCE=str(root / "evidence"),
                       CALL_LOG=str(root / "calls"), STUB_MODE=mode)
            run = subprocess.run(["/bin/bash"], input=block, text=True, capture_output=True, env=env)
            evidence = {p.name: p.read_bytes() for p in (root / "evidence").iterdir() if p.is_file()}
            calls = (root / "calls").read_bytes() if (root / "calls").exists() else b""
            return run, evidence, calls, pins

    def test_parser_rejection_preserved_and_remaining_controls_run(self):
        run, files, calls, pins = self.stub_run()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(calls.count(b"inspect\0"), 3)
        self.assertNotIn(b"configure-boot", calls)
        self.assertEqual(files["flat31ac.exit"], b"71\n")
        self.assertEqual(files["nested31ad.exit"], b"0\n")
        self.assertEqual(files["rawboot021.exit"], b"71\n")
        self.assertEqual(files["flat31ac.stderr"], b"fixture fileset rejection\n")
        self.assertEqual(files["nested31ad.stdout"], b"fixture properties\n")
        self.assertEqual(files["recovery-build.txt"], b"FIXTURE_VERSION_ONLY\n")
        for role in render.ROLES:
            argv = files[role + ".argv.txt"].decode().splitlines()
            image = argv[argv.index("-B") + 1]
            self.assertIn("image=" + image + "\n", files[role + ".input.txt"].decode())
            self.assertIn(pins[role][1], files[role + ".input.txt"].decode())
            self.assertIn(image.encode() + b"\0", calls)

    def test_input_failures_never_call_parser(self):
        for mode in ("transfer", "corrupt", "hash", "symlink"):
            with self.subTest(mode=mode):
                run, files, calls, _ = self.stub_run(mode)
                self.assertNotEqual(run.returncode, 0)
                self.assertEqual(calls, b"")
                self.assertNotIn("flat31ac.exit", files)

    def test_rollback_scaffold_is_default_denied(self):
        block = (HERE / "rollback-scaffold.sh").read_text()
        syntax = subprocess.run(["/bin/bash", "-n"], input=block, text=True, capture_output=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        # Gate exits before the first hash/tool/volume call; no stubs needed.
        run = subprocess.run(["/bin/bash"], input=block, text=True, capture_output=True)
        self.assertEqual(run.returncode, 78)
        self.assertIn("no Recovery write is qualified", run.stdout)
        self.assertIn("</dev/tty", block)
        self.assertIn('statuses=("${PIPESTATUS[@]}")', block)
        self.assertIn('rc=${statuses[0]}', block)
        self.assertIn("--entry-point 2048 --lowest-virtual-address 0", block)
        self.assertNotIn("curl", block)


if __name__ == "__main__":
    unittest.main(verbosity=2)
