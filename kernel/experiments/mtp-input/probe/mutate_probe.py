#!/usr/bin/env python3
"""Mutation check for mtp_probe.py: every deliberate mistake must fail the tests.

usage: python3 -I mutate_probe.py
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent

MUTANTS = [
    ("wrapper reads any address",
     "        if not any(lo <= address and address + 4 <= hi for lo, hi in self._spans):\n"
     "            raise Forbidden(\"read outside the declared regions: 0x%x\" % address)\n", ""),
    ("wrapper forwards unknown attributes (writes possible)",
     "        raise Forbidden(\"the probe's proxy has no %r (read-only)\" % name)",
     "        return getattr(self._proxy, name)"),
    ("plan reads a DockChannel RX data register",
     "    plan.append((\"dockchannel\", \"irq_mask\", dock[1] + DOCK_IRQ[\"irq_mask\"]))",
     "    plan.append((\"dockchannel\", \"rx32\", dock[3] + 0x28))\n"
     "    plan.append((\"dockchannel\", \"irq_mask\", dock[1] + DOCK_IRQ[\"irq_mask\"]))"),
    ("plan reads a mailbox RECV register",
     "    mbox = reg[\"asc\"] + MBOX_BASE_OFFSET\n",
     "    mbox = reg[\"asc\"] + MBOX_BASE_OFFSET\n    plan.append((\"mailbox\", \"recv\", mbox + 0x830))\n"),
    ("alternative DART base is 0x4000", "DART_ALT_BASE = 0x8000", "DART_ALT_BASE = 0x4000"),
    ("prefers the +0x8000 block", "    for tag in (\"plus0\", \"plus8000\"):\n        if candidates",
     "    for tag in (\"plus8000\", \"plus0\"):\n        if candidates"),
    ("TCR offset wrong", "DART_TCR, DART_TTBR = 0x1000, 0x1400", "DART_TCR, DART_TTBR = 0x1004, 0x1400"),
    ("any version accepted as plausible", "return (decoded[\"ver_major\"] != 0 and 1 <= decoded[\"num_sids\"] <= 256",
     "return (1 <= decoded[\"num_sids\"] <= 256"),
    ("CPU control offset wrong", "ASC_CPU_CONTROL = 0x44 ", "ASC_CPU_CONTROL = 0x48 "),
    ("mailbox base offset wrong", "MBOX_BASE_OFFSET = 0x8000 ", "MBOX_BASE_OFFSET = 0x0 "),
    ("SID reads uncapped", "DART_MAX_SIDS_READ = 32", "DART_MAX_SIDS_READ = 4096"),
    ("any translating stream set accepted", "            translating == [0])", "            True)"),
    ("dockchannel differences ignored",
     "    if repo[\"dock\"] != live[\"dock\"]:\n        diffs.append(\"dockchannel regs differ\")\n", ""),
    ("confirm token not enforced", "    if args.device is None or args.confirm != CONFIRM_READ:",
     "    if args.device is None:"),
    ("existing JSON file accepted",
     "    if os.path.lexists(path):\n        raise argparse.ArgumentTypeError(\"file exists; choose a new name\")\n", ""),
    ("fault flag ignored",
     "            if proxy.faulted():\n                entry.update(status=\"trapped\")\n            else:\n",
     "            if False:\n                entry.update(status=\"trapped\")\n            else:\n"),
]


def run_tests(probe_dir):
    r = subprocess.run([sys.executable, "-I", str(probe_dir / "test_mtp_probe.py")],
                       capture_output=True, text=True, timeout=120)
    return r.returncode


def main():
    original = (HERE / "mtp_probe.py").read_text()
    root = HERE.parents[3]
    bad = 0
    with tempfile.TemporaryDirectory() as d:
        # same relative layout as the repo, so ROOT / "hardware/adt/..." resolves
        work = Path(d)
        exp = work / "kernel" / "experiments" / "mtp-input"
        probe = exp / "probe"
        probe.mkdir(parents=True)
        (work / "hardware" / "adt").mkdir(parents=True)
        shutil.copy(root / "hardware" / "adt" / "adt-sanitized.json",
                    work / "hardware" / "adt" / "adt-sanitized.json")
        shutil.copy(EXP / "mtp_adt.py", exp / "mtp_adt.py")
        shutil.copy(HERE / "test_mtp_probe.py", probe / "test_mtp_probe.py")
        (probe / "mtp_probe.py").write_text(original)
        base_ok = run_tests(probe) == 0
        print("baseline:", "pass" if base_ok else "FAIL")
        if not base_ok:
            return 2
        for name, old, new in MUTANTS:
            if original.count(old) != 1:
                print("MUTATION SITE NOT FOUND:", name)
                bad += 1
                continue
            (probe / "mtp_probe.py").write_text(original.replace(old, new))
            try:
                caught = run_tests(probe) != 0
            except subprocess.TimeoutExpired:
                caught = True
            print("%-56s %s" % (name, "caught" if caught else "SURVIVED"))
            bad += 0 if caught else 1
    print("mutants: %d, survived/invalid: %d" % (len(MUTANTS), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
