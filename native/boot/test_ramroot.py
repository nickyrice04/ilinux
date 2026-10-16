"""Offline tests for the launcher's two fixed profiles: Stage-B and the job 039 RAM root.

Synthetic data and fake transports only; nothing opens USB or touches a target. The
Stage-B tests run every case through the reviewed launcher as well (its git object,
checked against the digest that tools/m1n1-client/stage-b-instructions.md pins) and
require identical requests, uploads, printed lines and errors.
"""
import base64
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import launch
from test_launcher import FakeInterface, FakeProxy, FakeUtils, prepared

REVIEWED_COMMIT = "f2b2c4d327fa4d2cdc22b07eb47173b950023868"   # last change to launch.py before profiles
REVIEWED_SHA256 = "65ece2537fdb9ece0ed54dc234f8ee253bc2f3c44aac8c012014079b6366cfe0"
# Written out, not read from launch.py, so that a change to either string fails here.
STAGE_B_ARGS = ("console=tty0 fbcon=nodefer rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 "
                "idle=nop arm64.nowfxt pd_ignore_unused clk_ignore_unused loglevel=8 "
                "ignore_loglevel printk.time=1 panic=0 earlycon=ilinuxfb initcall_debug "
                "initcall_blacklist=clk_debug_init ilinux_probe_diag=1")
STAGE_B_CONFIRM = "BOOT-J716C-RAM-DIAGNOSTIC"
RAMROOT_ARGS = ("console=tty0 rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 "
                "pd_ignore_unused clk_ignore_unused quiet")
RAMROOT_CONFIRM = "BOOT-J716C-RAM-ROOT"
APPENDED = " idle=nop arm64.nowfxt"   # what the pinned m1n1 adds on M4 and later
RAMROOT = launch.PROFILES["ramroot"]
ZSTD = b"\x28\xb5\x2f\xfd"
MANIFEST = {"m1n1_version_marker": "version", "m1n1_version_offset": 0x100,
            "m1n1_dt_pointer_offset": 0x200}
REVIEWED_LINES = [
    "Target PASS: t6050, packaged m1n1 marker, no started secondaries.",
    "Initializing controller RAM utilities.",
    "Reading target ADT root compatibility.",
    "GPIO ADT PASS: main controller 221 pins/7 groups; exclusions 5,6,7,112,141 match.",
    "Board/framebuffer PASS; allocating RAM for diagnostic payloads.",
    "DAPF layout PASS: AOP has DART/GAPF only; RAM correction planned.",
    "Uploading DT, initramfs and kernel to RAM.",
    "RAM upload complete; preparing effective DT and hardware handoff.",
    "Hardware DT PASS: J716c/t6050 CPU topology, AIC3 and timer routes verified.",
    "DAPF RAM table corrected: omitted absent AOP DAPF; other entries retained.",
    "Early framebuffer PASS: kernel RAM descriptor checked and populated.",
    "Preflight PASS; handing off. Observe the M5 display; USB console ends here.",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def package_files(text_offset=0):
    image = bytearray(64)
    struct.pack_into("<QQ", image, 8, text_offset, 4096)
    image[56:60] = b"ARM\x64"
    image.extend(launch.entry_guard.MAGIC + bytes(16))
    return {"Image": bytes(image), "t6050-j716c-stage-b.dtb": prepared(),
            "initramfs-stage-b.cpio.gz": b"initrd", "m1n1.bin": b"fixture"}


class Recorder:
    """Log every method call on a fake, in order, then delegate to it."""

    def __init__(self, target, label, log):
        self._target, self._label, self._log = target, label, log

    def __getattr__(self, name):
        value = getattr(self._target, name)
        if not callable(value):
            return value

        def call(*args):
            self._log.append((self._label, name) + args)
            return value(*args)
        return call


def run_session(module, case, *profile):
    """One launch_session with fakes: (requests in order, printed lines, error or None)."""
    log = []
    proxy, iface = FakeProxy(), FakeInterface(case.get("tree", prepared()))
    proxy.chip = case.get("chip", proxy.chip)
    proxy.alive = case.get("alive", proxy.alive)
    proxy.dt_result = case.get("dt_result", proxy.dt_result)
    iface.marker = case.get("marker", iface.marker)
    files = package_files(case.get("text_offset", 0))
    files.update(case.get("files", {}))

    def factory(p):
        utils = FakeUtils(p)
        if "compatible" in case:
            utils.adt.compatible = case["compatible"]
        if "video_base" in case:
            utils.ba.video.base = case["video_base"]
        if "gpio_pins" in case:
            utils.adt.gpio["no-restore-gpio-pins"] = case["gpio_pins"]
        log.append(("utils", "created"))
        return Recorder(utils, "utils", log)

    def prepare(_iface, base, m1n1, _adt):
        log.append(("dapf", "prepare", base, m1n1))
        return "plan"

    out, error = io.StringIO(), None
    with contextlib.redirect_stdout(out), \
         patch.object(launch.dapf_guard, "prepare", side_effect=prepare), \
         patch.object(launch.dapf_guard, "apply", side_effect=lambda _i, plan: log.append(("dapf", "apply", plan))), \
         patch.object(launch.entry_guard, "apply", side_effect=lambda _i, k, d: log.append(("entry", "apply", k, d))):
        try:
            module.launch_session(Recorder(iface, "iface", log), Recorder(proxy, "proxy", log),
                                  factory, MANIFEST, files, *profile)
        except Exception as exc:   # compared by type and message
            error = "%s: %s" % (type(exc).__name__, exc)
    return log, out.getvalue().splitlines(), error


def run_main(module, argv, files=None):
    """main() with the package check and USB faked: (result, stdout, last stderr line, launches)."""
    out, err = io.StringIO(), io.StringIO()
    with patch.object(module, "verify_package", return_value=(MANIFEST, files or package_files())), \
         patch.object(module.usb_identity, "discover", side_effect=AssertionError("USB discovery")), \
         patch.object(module, "connect_and_launch") as connect, \
         contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            result = module.main(argv)
        except SystemExit as exc:
            result = "exit %s" % exc.code
    return result, out.getvalue(), err.getvalue().strip().splitlines()[-1:], connect.call_args_list


def run_connect(module, *profile):
    """connect_and_launch with fake modules: (alarms, deadline message, opens, closed, sessions)."""
    port = launch.usb_identity.Port("/dev/cu.usbmodemSYNTHETIC1", 0x1209, 0x316d, 1, 10)
    transport = SimpleNamespace(closed=False)
    transport.close = lambda: setattr(transport, "closed", True)
    opens, alarms, handlers, sessions = [], [], [], []

    class Interface:
        DEFAULT_BAUD_RATE = 115200

        def __init__(self, device):
            self.dev = device

    modules = {"m1n1": SimpleNamespace(),
               "m1n1.proxy": SimpleNamespace(Serial=lambda d, b: opens.append((d, b)) or transport,
                                             UartInterface=Interface, M1N1Proxy=lambda iface: "proxy"),
               "m1n1.proxyutils": SimpleNamespace(ProxyUtils="utils")}
    with patch.dict(sys.modules, modules), \
         patch.object(module.subprocess, "check_output", side_effect=[launch.M1N1_COMMIT, ""]), \
         patch.object(module.usb_identity, "discover", return_value=[port]), \
         patch.object(Path, "lstat", return_value=SimpleNamespace(st_mode=stat.S_IFCHR)), \
         patch.object(module.signal, "signal", side_effect=lambda _s, h: handlers.append(h) or "old"), \
         patch.object(module.signal, "alarm", side_effect=alarms.append), \
         patch.object(module, "launch_session", side_effect=lambda *a: sessions.append(a[3:5])), \
         contextlib.redirect_stdout(io.StringIO()):
        module.connect_and_launch("auto", Path("/fake-client"), MANIFEST, {"Image": b"x"}, *profile)
    try:
        handlers[0]()
    except TimeoutError as exc:
        message = str(exc)
    return alarms, message, opens, transport.closed, sessions, handlers[1:]


def reviewed_launcher():
    """The reviewed launch.py as a separate module, or None without its git object."""
    try:
        source = subprocess.run(["git", "-C", str(HERE), "show", REVIEWED_COMMIT + ":native/boot/launch.py"],
                                capture_output=True, check=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    if sha(source) != REVIEWED_SHA256:
        raise AssertionError("git object is not the reviewed launcher")
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader("reviewed_launch", loader=None))
    module.__file__ = str(HERE / "launch.py")
    exec(compile(source, "reviewed launch.py", "exec"), module.__dict__)
    return module


STAGE_B_CASES = {
    "boot": {},
    "nonzero text offset": {"text_offset": 0x80000},
    "m1n1 append": {"tree": prepared(bootargs=STAGE_B_ARGS + APPENDED)},
    "wrong chip": {"chip": 0x8103},
    "wrong m1n1": {"marker": b"wrong\0"},
    "started secondary": {"alive": 31},
    "wrong board": {"compatible": ["J714cAP"]},
    "no boot framebuffer": {"video_base": 0},
    "changed GPIO exclusions": {"gpio_pins": struct.pack("<5I", 5, 6, 8, 112, 141)},
    "DT preparation fails": {"dt_result": -1},
    "two CPUs": {"tree": prepared(cpu_count=2)},
    "storage enabled": {"tree": prepared(storage=True)},
    "framebuffer missing": {"tree": prepared(framebuffer=False)},
    "bad DT header": {"tree": bytes(8)},
    "foreign append": {"tree": prepared(bootargs=STAGE_B_ARGS + " root=/dev/nvme0n1")},
    "probe diagnostics off": {"tree": prepared(bootargs=STAGE_B_ARGS.replace("diag=1", "diag=0"))},
    "RAM-root arguments": {"tree": prepared(bootargs=RAMROOT_ARGS + APPENDED)},
}
STAGE_B_ARGV = [
    ["--package", "/fake"],
    ["--package", "/fake", "--launch", "--device", "auto", "--confirm", STAGE_B_CONFIRM],
    ["--package", "/fake", "--launch"],
    ["--package", "/fake", "--launch", "--device", "auto", "--confirm", RAMROOT_CONFIRM],
    ["--package", "/fake", "--device", "auto"],
    ["--package", "/fake", "--confirm", STAGE_B_CONFIRM],
]


class ReviewedStageBTests(unittest.TestCase):
    """Stage-B is byte-for-byte the reviewed launcher's: every case, compared whole."""

    @classmethod
    def setUpClass(cls):
        cls.reviewed = reviewed_launcher()

    def setUp(self):
        if self.reviewed is None:
            self.skipTest("reviewed launcher's git object unavailable")

    def test_sessions_match_reviewed_launcher(self):
        booted = 0
        for name, case in STAGE_B_CASES.items():
            with self.subTest(case=name):
                ours = run_session(launch, case)
                self.assertEqual(ours, run_session(self.reviewed, case))
                booted += any(event[1] == "kboot_boot" for event in ours[0])
        self.assertEqual(booted, 3)   # the comparison covers handoffs and refusals

    def test_cli_matches_reviewed_launcher(self):
        for argv in STAGE_B_ARGV:
            with self.subTest(argv=argv):
                ours, theirs = run_main(launch, argv), run_main(self.reviewed, argv)
                self.assertEqual(ours[:3], theirs[:3])
                self.assertEqual([c.args[:4] for c in ours[3]], [c.args[:4] for c in theirs[3]])

    def test_controller_matches_reviewed_launcher(self):
        ours, theirs = run_connect(launch), run_connect(self.reviewed)
        self.assertEqual(ours[:4], theirs[:4])
        self.assertEqual(ours[0], [180, 0])


class StageBUnchangedTests(unittest.TestCase):
    """The same facts without git: Stage-B stays the default and keeps its fixed values."""

    def test_exactly_two_profiles(self):
        self.assertEqual(sorted(launch.PROFILES), ["ramroot", "stage-b"])
        self.assertEqual(launch.PROFILES["stage-b"],
                         ("initramfs-stage-b.cpio.gz", STAGE_B_ARGS, "diagnostic", STAGE_B_CONFIRM, 180, False))
        self.assertEqual(RAMROOT, ("ramroot.cpio.zst", RAMROOT_ARGS, "RAM-root", RAMROOT_CONFIRM, 300, True))
        self.assertEqual((launch.BOOTARGS, launch.CONFIRM), (STAGE_B_ARGS, STAGE_B_CONFIRM))

    def test_default_session_is_stage_b(self):
        log, lines, error = run_session(launch, {})
        files = package_files()
        self.assertIsNone(error)
        self.assertEqual(lines, REVIEWED_LINES)
        self.assertEqual([e[3] for e in log if e[:2] == ("iface", "writemem")],
                         [files["t6050-j716c-stage-b.dtb"], b"initrd", files["Image"]])
        self.assertIn(("proxy", "kboot_set_chosen", "bootargs", STAGE_B_ARGS), log)
        self.assertEqual([e[3] for e in log if e[1] == "kboot_set_initrd"], [len(b"initrd")])
        self.assertEqual([e for e in log if e[1] == "kboot_boot"], [("proxy", "kboot_boot", 0x200000)])

    def test_offline_output_and_no_ramroot_record(self):
        with patch.object(launch, "RAMROOT_RECORD", Path("/nonexistent/ramroot-manifest.json")):
            result, out, _, launches = run_main(launch, ["--package", "/fake"])
        self.assertEqual((result, launches), (0, []))
        self.assertEqual(out.splitlines(), ["Package PASS: all files match the repository manifest.",
                                            "Mode: OFFLINE ONLY; USB not opened",
                                            "Boot arguments: " + STAGE_B_ARGS])

    def test_live_stage_b_keeps_its_token_and_deadline(self):
        argv = ["--package", "/fake", "--launch", "--device", "auto", "--confirm", STAGE_B_CONFIRM]
        result, _, _, launches = run_main(launch, argv)
        self.assertEqual(result, 0)
        self.assertEqual(launches[0].args[0], "auto")
        self.assertEqual(launches[0].args[3]["initramfs-stage-b.cpio.gz"], b"initrd")
        self.assertIs(launches[0].args[4], launch.STAGE_B)
        alarms, message, opens, closed, sessions, restored = run_connect(launch)
        self.assertEqual((alarms, closed, restored), ([180, 0], True, ["old"]))
        self.assertEqual(message, "launch exceeded 180 seconds; do not automatically retry")

    def test_stage_b_refuses_ramroot_inputs(self):
        for extra in (["--ramroot", "/x/ramroot.cpio.zst"], ["--operator-key", "/x/id.pub"],
                      ["--profile", "stage-b", "--ramroot", "/x/ramroot.cpio.zst"]):
            with self.subTest(extra=extra):
                result, out, err, launches = run_main(launch, ["--package", "/fake"] + extra)
                self.assertEqual((result, out, launches), ("exit 2", "", []))
                self.assertIn("require --profile ramroot", err[0])

    def test_stage_b_refuses_ramroot_token(self):
        argv = ["--package", "/fake", "--launch", "--device", "auto", "--confirm", RAMROOT_CONFIRM]
        result, _, err, launches = run_main(launch, argv)
        self.assertEqual((result, launches), ("exit 2", []))
        self.assertIn("--confirm " + STAGE_B_CONFIRM, err[0])

    def test_stage_b_refuses_ramroot_arguments(self):
        log, _, error = run_session(launch, {"tree": prepared(bootargs=RAMROOT_ARGS + APPENDED)})
        self.assertEqual(error, "ValueError: prepared DT bootargs differ from fixed diagnostic arguments")
        self.assertFalse([e for e in log if e[1] == "kboot_boot"])

    def test_unknown_profile_refused_before_any_request(self):
        for profile in (RAMROOT._replace(bootargs=RAMROOT_ARGS + " init=/bin/sh"),
                        launch.STAGE_B._replace(initrd="ramroot.cpio.zst")):
            with self.subTest(profile=profile):
                log, lines, error = run_session(launch, {}, profile)
                self.assertEqual(error, "ValueError: unknown launch profile; only stage-b and ramroot exist")
                self.assertEqual((log, lines), ([], []))
                with patch.object(launch.subprocess, "check_output") as git, self.assertRaises(ValueError):
                    launch.connect_and_launch("auto", Path("/fake-client"), {}, {}, profile)
                git.assert_not_called()
        result, _, err, _ = run_main(launch, ["--package", "/fake", "--profile", "other"])
        self.assertEqual(result, "exit 2")
        self.assertIn("invalid choice", err[0])


class RamrootSessionTests(unittest.TestCase):
    def setUp(self):
        self.initrd = launch.ramroot_initrd(ZSTD + b"frame", launch.newc_cpio([("x", 0o100600, b"y")]))
        self.tree = prepared(bootargs=RAMROOT_ARGS + APPENDED)

    def session(self, **case):
        case.setdefault("tree", self.tree)
        case["files"] = {"ramroot.cpio.zst": self.initrd}
        return run_session(launch, case, RAMROOT)

    def test_uploads_ramroot_and_fixed_arguments(self):
        log, lines, error = self.session()
        files = package_files()
        self.assertIsNone(error)
        self.assertEqual([e[3] for e in log if e[:2] == ("iface", "writemem")],
                         [files["t6050-j716c-stage-b.dtb"], self.initrd, files["Image"]])
        initrd_addr = [e[2] for e in log if e[:2] == ("iface", "writemem")][1]
        self.assertIn(("proxy", "kboot_set_chosen", "bootargs", RAMROOT_ARGS), log)
        self.assertIn(("proxy", "kboot_set_initrd", initrd_addr, len(self.initrd)), log)
        self.assertEqual([e for e in log if e[1] == "kboot_boot"], [("proxy", "kboot_boot", 0x200000)])
        self.assertEqual(lines, [line.replace("diagnostic payloads", "RAM-root payloads")
                                 for line in REVIEWED_LINES])

    def test_requires_m1n1s_exact_append(self):
        for tail in ("", " idle=nop", " arm64.nowfxt idle=nop", APPENDED + " idle=nop",
                     APPENDED + " init=/bin/sh", " loglevel=8" + APPENDED):
            with self.subTest(tail=tail):
                log, _, error = self.session(tree=prepared(bootargs=RAMROOT_ARGS + tail))
                self.assertEqual(error, "ValueError: prepared DT lacks m1n1's exact idle=nop arm64.nowfxt append")
                self.assertFalse([e for e in log if e[1] == "kboot_boot"])

    def test_refuses_other_fixed_arguments(self):
        for args in (STAGE_B_ARGS, RAMROOT_ARGS.replace(" quiet", ""), "init=/bin/sh " + RAMROOT_ARGS,
                     RAMROOT_ARGS.replace("maxcpus=1", "maxcpus=2")):
            with self.subTest(args=args):
                log, _, error = self.session(tree=prepared(bootargs=args + APPENDED))
                self.assertEqual(error, "ValueError: prepared DT bootargs differ from fixed RAM-root arguments")
                self.assertFalse([e for e in log if e[1] == "kboot_boot"])

    def test_keeps_every_stage_b_gate(self):
        before_upload = {"wrong chip": {"chip": 0x8103}, "wrong m1n1": {"marker": b"wrong\0"},
                         "started secondary": {"alive": 31}, "wrong board": {"compatible": ["J714cAP"]},
                         "no boot framebuffer": {"video_base": 0},
                         "changed GPIO exclusions": {"gpio_pins": struct.pack("<5I", 5, 6, 8, 112, 141)}}
        after_upload = {"DT preparation fails": {"dt_result": -1},
                        "two CPUs": {"tree": prepared(cpu_count=2, bootargs=RAMROOT_ARGS + APPENDED)},
                        "storage enabled": {"tree": prepared(storage=True, bootargs=RAMROOT_ARGS + APPENDED)},
                        "framebuffer missing": {"tree": prepared(framebuffer=False, bootargs=RAMROOT_ARGS + APPENDED)},
                        "bad DT header": {"tree": bytes(8)}}
        for name, case in list(before_upload.items()) + list(after_upload.items()):
            with self.subTest(case=name):
                log, _, error = self.session(**case)
                self.assertIsNotNone(error)
                self.assertFalse([e for e in log if e[1] == "kboot_boot"])
                if name in before_upload:
                    self.assertFalse([e for e in log if e[1] == "writemem"])

    def test_deadline(self):
        alarms, message, opens, closed, sessions, restored = run_connect(launch, RAMROOT)
        self.assertEqual((alarms, len(opens), closed, restored), ([300, 0], 1, True, ["old"]))
        self.assertEqual(message, "launch exceeded 300 seconds; do not automatically retry")


def ed25519_line(seed=b"operator", comment=" operator@host"):
    blob = struct.pack(">I", 11) + b"ssh-ed25519" + struct.pack(">I", 32) + hashlib.sha256(seed).digest()
    return "ssh-ed25519 " + base64.b64encode(blob).decode() + comment, blob


def parse_newc(blob):
    entries, pos = [], 0
    while True:
        assert pos % 4 == 0 and blob[pos:pos + 6] == b"070701"
        fields = [int(blob[pos + 6 + 8 * i:pos + 14 + 8 * i], 16) for i in range(13)]
        end = pos + 110 + fields[11]
        name = blob[pos + 110:end - 1].decode()
        assert blob[end - 1] == 0
        body = (end + 3) & ~3
        data = blob[body:body + fields[6]]
        pos = (body + fields[6] + 3) & ~3
        if name == "TRAILER!!!":
            assert pos == len(blob)
            return entries
        entries.append((name, fields[1], fields[2], fields[3], fields[4], fields[5], data))


def kernel_cpio_offset(initrd, compressed_end):
    """init/initramfs.c after a compressed member: skip zero bytes; a newc cpio is
    accepted only where its first byte sits at a 4-byte offset."""
    pos = compressed_end
    while pos < len(initrd) and initrd[pos] == 0:
        pos += 1
    if initrd[pos:pos + 1] == b"0" and pos % 4 == 0:
        return pos
    raise ValueError("invalid magic at start of compressed archive")


class OperatorKeyTests(unittest.TestCase):
    def test_layout_matches_job_039_overlay(self):
        line, blob = ed25519_line()
        cpio, prints = launch.operator_key_cpio((line + "\n").encode())
        key = line.rsplit(" ", 1)[0] + "\n"   # comment dropped
        self.assertEqual(parse_newc(cpio), [
            ("etc", 0o40755, 0, 0, 2, 0, b""), ("etc/ssh", 0o40755, 0, 0, 2, 0, b""),
            ("etc/ssh/authorized_keys.d", 0o40755, 0, 0, 2, 0, b""),
            ("etc/ssh/authorized_keys.d/root", 0o100600, 0, 0, 1, 0, key.encode())])
        fingerprint = base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip("=")
        self.assertEqual(prints, ["ssh-ed25519 SHA256:" + fingerprint])
        self.assertNotIn(b"operator@host", cpio)

    def test_several_keys_and_blank_lines(self):
        first, _ = ed25519_line(b"a")
        second, _ = ed25519_line(b"b", comment="")
        cpio, prints = launch.operator_key_cpio(("\n%s\n\n%s\n" % (first, second)).encode())
        self.assertEqual(len(prints), 2)
        self.assertEqual(parse_newc(cpio)[-1][-1].count(b"ssh-ed25519 "), 2)

    def test_refuses_anything_but_plain_public_keys(self):
        line, blob = ed25519_line()
        mismatched = "ecdsa-sha2-nistp256 " + line.split()[1]
        cases = {"empty": b"\n\n", "private key": b"-----BEGIN OPENSSH PRIVATE KEY-----\nb3Blbg==\n",
                 "options": ('from="10.0.0.1" ' + line).encode(), "DSA": line.replace("ssh-ed25519", "ssh-dss").encode(),
                 "type only": b"ssh-ed25519\n", "bad base64": b"ssh-ed25519 AAAA!!!!\n",
                 "type mismatch": mismatched.encode(), "nine keys": ("\n".join([line] * 9)).encode(),
                 "non-ASCII": (line + " é").encode(), "oversized": (line + " " + "x" * 16384).encode()}
        for name, text in cases.items():
            with self.subTest(case=name), self.assertRaisesRegex(ValueError, "operator key"):
                launch.operator_key_cpio(text)


class InitrdTests(unittest.TestCase):
    def test_overlay_lands_where_linux_finds_it(self):
        overlay = launch.operator_key_cpio(ed25519_line()[0].encode())[0]
        for extra in range(4):
            image = ZSTD + b"f" * (9 + extra)
            initrd = launch.ramroot_initrd(image, overlay)
            start = kernel_cpio_offset(initrd, len(image))
            self.assertEqual(initrd[:len(image)], image)
            self.assertEqual(initrd[start:], overlay)
            self.assertEqual(start - len(image), -len(image) % 4)
            if len(image) % 4:   # job 039 problem 3: unpadded, Linux rejects the overlay
                with self.assertRaisesRegex(ValueError, "invalid magic"):
                    kernel_cpio_offset(image + overlay, len(image))

    def test_without_overlay_the_image_is_unchanged(self):
        image = ZSTD + b"abc"
        self.assertIs(launch.ramroot_initrd(image), image)

    def test_upload_estimate(self):
        class Size:
            def __init__(self, n):
                self.n = n

            def __len__(self):
                return self.n
        files = {"Image": Size(44599808), "ramroot.cpio.zst": Size(182092876),
                 "t6050-j716c-stage-b.dtb": Size(60363)}
        total, seconds = launch.upload_estimate(files, RAMROOT)
        self.assertEqual(total, 226753047)
        self.assertEqual(["%.1f" % s for s in seconds], ["45.4", "56.7"])


class RamrootFileTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.files = package_files()
        self.data = ZSTD + b"synthetic frame"
        self.path = self.root / "ramroot.cpio.zst"
        self.path.write_bytes(self.data)
        self.record = {"size": len(self.data), "sha256": sha(self.data), "source": "synthetic run",
                       "image_sha256": sha(self.files["Image"])}
        self.write_record()
        recorded = patch.object(launch, "RAMROOT_RECORD", self.root / "ramroot-manifest.json")
        recorded.start()
        self.addCleanup(recorded.stop)

    def write_record(self):
        (self.root / "ramroot-manifest.json").write_text(json.dumps(self.record))

    def refuse(self, message, path=None, image=None):
        with self.assertRaisesRegex(ValueError, message):
            launch.verify_ramroot(path or self.path, image or self.files["Image"])

    def test_recorded_build_passes(self):
        record, data = launch.verify_ramroot(self.path, self.files["Image"])
        self.assertEqual((record["source"], data), ("synthetic run", self.data))

    def test_refusals(self):
        self.refuse("Image the RAM root was built for", image=self.files["Image"] + b"x")
        self.refuse("missing", path=self.root / "absent.zst")
        (self.root / "link.zst").symlink_to(self.path)
        self.refuse("not a regular file", path=self.root / "link.zst")
        self.refuse("not a regular file", path=self.root)
        self.path.write_bytes(self.data + b"x")
        self.refuse("size mismatch")
        self.path.write_bytes(self.data[:-1] + b"X")
        self.refuse("checksum mismatch")
        self.path.write_bytes(b"\x1f\x8b" + self.data[2:])
        self.record["sha256"] = sha(self.path.read_bytes())
        self.write_record()
        self.refuse("not a zstd frame")

    def test_repository_record(self):
        record = json.loads((HERE / "ramroot-manifest.json").read_text())
        self.assertEqual((record["profile"], record["file"], record["native_tested"]),
                         ("ramroot", "ramroot.cpio.zst", False))
        self.assertIsInstance(record["size"], int)
        self.assertGreater(record["size"], 0)
        for key in ("sha256", "image_sha256"):
            self.assertRegex(record[key], "^[0-9a-f]{64}$")

    def main(self, *extra):
        argv = ["--package", "/fake", "--profile", "ramroot", "--ramroot", str(self.path)] + list(extra)
        return run_main(launch, argv, self.files)

    def test_dry_run_reports_estimate_and_stays_offline(self):
        key = self.root / "id.pub"
        key.write_text(ed25519_line()[0] + "\n")
        result, out, _, launches = self.main("--operator-key", str(key))
        lines = out.splitlines()
        self.assertEqual((result, launches), (0, []))
        self.assertEqual(lines[0], "Package PASS: all files match the repository manifest.")
        self.assertEqual(lines[1], "RAM root PASS: 19 bytes match ramroot-manifest.json (synthetic run).")
        self.assertRegex(lines[2], r"^Operator key for root: ssh-ed25519 SHA256:[A-Za-z0-9+/]{43}$")
        self.assertEqual(lines[3:6], ["Mode: OFFLINE ONLY; USB not opened", "Boot arguments: " + RAMROOT_ARGS,
                                      "m1n1 must append: idle=nop arm64.nowfxt"])
        initrd = len(launch.ramroot_initrd(self.data, launch.operator_key_cpio(key.read_bytes())[0]))
        dtb, image = len(self.files["t6050-j716c-stage-b.dtb"]), len(self.files["Image"])
        sizes = [format(n, ",") for n in (image + initrd + dtb, image, initrd, dtb)]
        self.assertEqual(lines[6], "Upload estimate: %s bytes (Image %s, initrd %s, DT %s): %.1f s at 5 MB/s, "
                                   "%.1f s at 4 MB/s (Inferred: size / observed proxy rate). Deadline 300 s."
                         % tuple(sizes + [(image + initrd + dtb) / 5e6, (image + initrd + dtb) / 4e6]))
        self.assertEqual(len(lines), 7)

    def test_without_operator_key(self):
        result, out, _, _ = self.main()
        self.assertEqual(result, 0)
        self.assertIn("Operator key: none; only keys built into the image can log in.", out.splitlines())

    def test_live_launch_needs_ramroot_token(self):
        live = ["--launch", "--device", "auto", "--confirm"]
        result, out, err, launches = self.main(*live, STAGE_B_CONFIRM)
        self.assertEqual((result, out, launches), ("exit 2", "", []))
        self.assertIn("--confirm " + RAMROOT_CONFIRM, err[0])
        result, out, _, launches = self.main(*live, RAMROOT_CONFIRM)
        self.assertEqual(result, 0)
        self.assertIn("Mode: LIVE RAM LAUNCH", out.splitlines())
        device, _, _, files, profile = launches[0].args
        self.assertEqual((device, profile, files["ramroot.cpio.zst"]), ("auto", RAMROOT, self.data))
        self.assertEqual(files["initramfs-stage-b.cpio.gz"], b"initrd")   # carried, never uploaded

    def test_ramroot_needs_its_image(self):
        result, out, err, _ = run_main(launch, ["--package", "/fake", "--profile", "ramroot"])
        self.assertEqual((result, out), ("exit 2", ""))
        self.assertIn("--profile ramroot requires --ramroot", err[0])

    def test_refused_image_stops_the_launcher(self):
        self.path.write_bytes(self.data + b"x")
        with self.assertRaisesRegex(ValueError, "size mismatch"):
            self.main("--launch", "--device", "auto", "--confirm", RAMROOT_CONFIRM)


if __name__ == "__main__":
    unittest.main()
