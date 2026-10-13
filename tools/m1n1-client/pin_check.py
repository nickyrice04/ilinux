"""Check the agreed m1n1 revision without updating or importing the client."""
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def check_pin():
    expected = (HERE / "m1n1-revision.txt").read_text().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", expected):
        raise ValueError("Invalid pinned m1n1 revision")
    checkout = ROOT / "third_party/m1n1"
    def git(*args):
        return subprocess.check_output(
            ["git", "-C", str(checkout), *args], text=True).strip()
    if git("rev-parse", "HEAD") != expected:
        raise ValueError("Client revision differs from the agreed pin; do not auto-update")
    if git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Client checkout has local changes; review before use")
    return expected


if __name__ == "__main__":
    print("m1n1 client pin verified:", check_pin())
