#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run generated phases against explicit private stubs, never real host tools."""
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("write_render31ae", HERE / "write_render.py")
writer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writer)


class WritePhases(unittest.TestCase):
    def profile(self):
        return {"schema": "ilinux31ae-write-v1", "candidate": {
            "bytes": 196608, "sha256": "a" * 64,
            "url": "https://example.invalid/ilinux-31ae.macho"}}

    def test_profile_and_phase_refusals(self):
        for field, value in (("bytes", True), ("bytes", 0), ("bytes", 180224),
                             ("sha256", "short"), ("sha256", writer.ROLLBACK_SHA),
                             ("url", "file:///system/file"),
                             ("url", "https://user:secret@example.invalid/a")):
            p = self.profile()
            p["candidate"][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                writer.render(p, "install")
        with self.assertRaises(ValueError): writer.render(self.profile(), "auto")
        p = self.profile()
        p["allow_security_change"] = True
        with self.assertRaises(ValueError): writer.render(p, "install")

    def test_both_blocks_are_independent_and_syntactically_complete(self):
        for phase in ("install", "rollback"):
            block = writer.render(self.profile(), phase)
            with self.subTest(phase=phase):
                result = subprocess.run(["/bin/bash", "-n"], input=block, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("base_guard()", block)
                self.assertIn("ilinux_check_policies Permissive", block)
                self.assertIn("</dev/tty", block)
                self.assertEqual(block.count("/usr/bin/kmutil configure-boot"), 1)
                self.assertNotIn("reboot\n", block)
                if phase == "install":
                    self.assertNotIn("--raw", block)
                else:
                    self.assertNotIn("curl", block)
                    self.assertNotIn("source_url", block)
                    self.assertIn("--entry-point 2048 --lowest-virtual-address 0", block)
        self.assertIn("Select COMPLETE rollback block", writer.page(
            writer.render(self.profile(), "install"), writer.render(self.profile(), "rollback")))

    def run_fixture(self, phase, mode="normal"):
        with tempfile.TemporaryDirectory(prefix="write31ae-test-") as tmp:
            root = Path(tmp)
            lab = root / "lab-system"
            data = root / "lab-data"
            original = root / "original-system"
            lab.mkdir(); data.mkdir(); original.mkdir()
            staging = data / "Users/Shared/iLinuxBoot"
            staging.mkdir(parents=True)
            raw = b"FIXTURE_RAW_ONLY" + bytes(3932160 - len(b"FIXTURE_RAW_ONLY"))
            (staging / "m1n1.bin").write_bytes(raw)
            candidate = b"FIXTURE_CANDIDATE_ONLY" + bytes(196608 - len(b"FIXTURE_CANDIDATE_ONLY"))
            (root / "candidate").write_bytes(candidate)
            helper = staging / "recovery-preflight.sh"
            helper.write_text('''ilinux_field() {
 case "$2" in
  VolumeName) case "$1" in *lab-system) printf 'iLinux Boot Lab\\n';; *lab-data) printf 'iLinux Boot Lab - Data\\n';; *) printf 'Macintosh HD\\n';; esac;;
  MountPoint) printf '%s\\n' "$1";;
  Internal) printf 'true\\n';;
  FilesystemType) printf 'apfs\\n';;
  APFSVolumeGroupID) case "$1" in *original-system) printf 'fixture-original-group\\n';; *) printf 'fixture-lab-group\\n';; esac;;
  FileVault) printf 'false\\n';;
  *) return 1;;
 esac
}
ilinux_check_policies() {
 test "$1" = Permissive || return 1
 test "$STUB_MODE" != guard || return 17
 local n=0
 test ! -f "$POLICY_COUNT" || read n <"$POLICY_COUNT"
 n=$((n+1)); printf '%s\\n' "$n" >"$POLICY_COUNT"
 if test "$STUB_MODE" = postcheck && test "$n" -gt 1; then return 18; fi
 printf 'fixture policy guard PASS\\n'
}
''')
            profile = self.profile()
            profile["candidate"]["sha256"] = hashlib.sha256(candidate).hexdigest()
            block = writer.render(profile, phase)
            block = block.replace("/Volumes/iLinux Boot Lab - Data", str(data))
            block = block.replace("/Volumes/iLinux Boot Lab", str(lab))
            block = block.replace("/Volumes/Macintosh HD", str(original))
            block = block.replace(writer.HELPER_SHA, hashlib.sha256(helper.read_bytes()).hexdigest())
            block = block.replace(writer.ROLLBACK_SHA, hashlib.sha256(raw).hexdigest())
            stubs = {
                "plutil": '#!/bin/bash\nprintf "25G83\\n"\n',
                "sw_vers": '#!/bin/bash\nprintf "FIXTURE_BUILD\\n"\n',
                "stat": '#!/bin/bash\nn=$(/usr/bin/wc -c <"$3") || exit 1\nprintf "%s\\n" "${n// /}"\n',
                "mktemp": '#!/bin/bash\nmkdir "$EVIDENCE" || exit 1\nprintf "%s\\n" "$EVIDENCE"\n',
                "curl": '''#!/bin/bash
printf 'curl\\n' >>"$TRANSFER_CALLS"
out=''
while test "$#" -gt 0; do
 if test "$1" = --output; then out="$2"; shift 2; else shift; fi
done
test "$STUB_MODE" != transfer || exit 22
cp "$CANDIDATE" "$out" || exit 1
if test "$STUB_MODE" = hash; then printf X | dd of="$out" bs=1 count=1 conv=notrunc 2>/dev/null; fi
if test "$STUB_MODE" = size; then printf bad >"$out"; fi
''',
                "kmutil": '''#!/bin/bash
printf '%s\\0' "$@" >>"$CALL_LOG"
test "$1" = configure-boot || exit 99
read -r answer
printf '%s\\n' "$answer" >"$TTY_READ"
printf 'fixture configure stdout\\n'
printf 'fixture configure stderr\\n' >&2
test "$STUB_MODE" != configure71 || exit 71
exit 0
''',
                "tee": '''#!/bin/bash
/usr/bin/tee "$@"
test "$STUB_MODE" != capture || exit 23
''',
            }
            for name, text in stubs.items():
                file = root / name
                file.write_text(text); file.chmod(0o700)
                block = block.replace("/usr/bin/" + name, str(file))
            tty_input = root / "tty-input"
            tty_input.write_text("FIXTURE_AUTH_INPUT_ONLY\n")
            block = block.replace("</dev/tty", '<"' + str(tty_input) + '"')
            env = dict(os.environ, STUB_MODE=mode, EVIDENCE=str(root / "evidence"),
                       CANDIDATE=str(root / "candidate"), CALL_LOG=str(root / "calls"),
                       TRANSFER_CALLS=str(root / "transfers"), POLICY_COUNT=str(root / "policy-count"),
                       TTY_READ=str(root / "tty-read"))
            run = subprocess.run(["/bin/bash"], input=block, text=True, capture_output=True, env=env)
            files = {p.name: p.read_bytes() for p in (root / "evidence").iterdir() if p.is_file()}
            calls = (root / "calls").read_bytes() if (root / "calls").exists() else b""
            transfers = (root / "transfers").read_bytes() if (root / "transfers").exists() else b""
            tty = (root / "tty-read").read_bytes() if (root / "tty-read").exists() else b""
            return run, files, calls, transfers, tty

    def test_install_uses_pinned_same_path_and_no_raw(self):
        run, files, calls, transfers, tty = self.run_fixture("install")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("INSTALL_SUCCESS_ENTRY_NOT_OBSERVED", run.stdout)
        self.assertEqual(calls.count(b"configure-boot\0"), 1)
        self.assertNotIn(b"--raw", calls)
        self.assertIn(b"--volume\0", calls)
        argv = files["argv.txt"].decode().splitlines()
        image = argv[argv.index("--custom-boot-object") + 1]
        self.assertIn(image.encode() + b"\0", calls)
        self.assertIn("image=" + image + "\n", files["input.txt"].decode())
        self.assertTrue(image.endswith("/ilinux-31ae.macho"))
        self.assertEqual(files["configure.exit"], b"0\n")
        self.assertEqual(files["postcheck.exit"], b"0\n")
        self.assertIn(b"fixture configure stdout\n", files["configure.log"])
        self.assertIn(b"fixture configure stderr\n", files["configure.log"])
        self.assertEqual(tty, b"FIXTURE_AUTH_INPUT_ONLY\n")
        self.assertEqual(transfers, b"curl\n")

    def test_input_or_guard_refusal_never_configures(self):
        for mode in ("guard", "hash", "size", "transfer"):
            with self.subTest(mode=mode):
                run, files, calls, transfers, tty = self.run_fixture("install", mode)
                self.assertNotEqual(run.returncode, 0)
                self.assertEqual(calls, b"")
                self.assertEqual(tty, b"")
                self.assertNotIn("configure.exit", files)
                if mode == "guard": self.assertEqual(transfers, b"")

    def test_configure71_keeps_full_evidence_and_exact_exit(self):
        run, files, calls, _, _ = self.run_fixture("install", "configure71")
        self.assertEqual(run.returncode, 71)
        self.assertEqual(files["configure.exit"], b"71\n")
        self.assertEqual(files["capture.exit"], b"0\n")
        self.assertNotIn("postcheck.exit", files)
        self.assertIn(b"fixture configure stderr\n", files["configure.log"])
        self.assertEqual(calls.count(b"configure-boot\0"), 1)
        self.assertNotIn("INSTALL_SUCCESS", run.stdout)

    def test_capture_and_postcheck_failures_do_not_claim_success(self):
        for mode, expected in (("capture", 74), ("postcheck", 18)):
            with self.subTest(mode=mode):
                run, files, calls, _, _ = self.run_fixture("install", mode)
                self.assertEqual(run.returncode, expected)
                self.assertEqual(files["configure.exit"], b"0\n")
                self.assertEqual(calls.count(b"configure-boot\0"), 1)
                self.assertNotIn("INSTALL_SUCCESS", run.stdout)
                if mode == "capture": self.assertEqual(files["capture.exit"], b"23\n")
                else: self.assertEqual(files["postcheck.exit"], b"18\n")

    def test_rollback_fresh_shell_no_download_no_prior_variables(self):
        run, files, calls, transfers, tty = self.run_fixture("rollback")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(transfers, b"")
        self.assertIn(b"\0".join((b"--raw", b"--entry-point", b"2048", b"--lowest-virtual-address", b"0")) + b"\0", calls)
        self.assertIn("ROLLBACK_SUCCESS_EXECUTION_NOT_OBSERVED", run.stdout)
        self.assertIn(b"/m1n1.bin\n", files["input.txt"])
        self.assertEqual(tty, b"FIXTURE_AUTH_INPUT_ONLY\n")
        self.assertEqual(files["guard.exit"], b"0\n")
        self.assertEqual(files["postcheck.exit"], b"0\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
