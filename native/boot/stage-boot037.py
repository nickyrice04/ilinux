#!/usr/bin/env python3
"""Stage boot037's export directory: boot036 plus job 042's Image, its config and the MTP DT.

usage: python3 -I stage-boot037.py --previous build/native-boot036/verified \\
           --job-out virtualization/jobs/042-mtp-input/out --destination build/native-boot037/stage \\
           [--adt hardware/adt/adt-sanitized.json] [--expect-image-sha256 HEX]

Writes DESTINATION/export/ (what make-package.py reads with --out DESTINATION) and
DESTINATION/stage-record.json. Nothing is invented here:

* every file the Image does not change is boot036's, checked against the repository's
  boot036-package-manifest.json first;
* Image: job 042's, accepted only if the job passed on the boot036 tree and the file is
  the digest the job recorded (and --expect-image-sha256, when given);
* kernel.config: the config embedded in that Image, i.e. the build config (kconfig_guard);
* Stage-B DT: kernel/experiments/mtp-input/make_mtp_dt.py on boot036's Stage-B DT, which
  must be byte-identical to the DT the job built in the VM.

Packaging then applies the exact contract (mtp_input.py). No hardware is involved.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import kconfig_guard

FILES = ("Image", "t6050-j716c.dtb", "initramfs.cpio.gz", "kernel.config", "t6050-j716c-stage-b.dtb",
         "initramfs-stage-b.cpio.gz", "m1n1.bin", "m1n1-build-config.h", "m1n1-LICENSE",
         "m1n1-revision.txt", "diag-init.c", "toolchain.txt")
TOOL = ROOT / "kernel/experiments/mtp-input/make_mtp_dt.py"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--previous", type=Path, required=True, help="verified boot036 package directory")
    parser.add_argument("--job-out", type=Path, required=True, help="VM job 042 out directory")
    parser.add_argument("--destination", type=Path, required=True, help="new directory; must not exist")
    parser.add_argument("--adt", type=Path, default=ROOT / "hardware/adt/adt-sanitized.json")
    parser.add_argument("--sids", default="1", help="MTP DART stream ids for the DT tool (default 1)")
    parser.add_argument("--expect-image-sha256", help="digest the Image must have (reproducibility pin)")
    args = parser.parse_args()

    baseline = json.loads((HERE / "boot036-package-manifest.json").read_text())
    if baseline["package"] != "ilinux-j716c-boot036":
        raise ValueError("boot036-package-manifest.json is not boot036's")
    previous = {}
    for name in FILES:
        path = args.previous / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("boot036 package lacks " + name)
        previous[name] = path.read_bytes()
        info = baseline["files"][name]
        if len(previous[name]) != info["size"] or sha256(previous[name]) != info["sha256"]:
            raise ValueError("not the published boot036 file: " + name)

    build = args.job_out / "build"
    if (args.job_out / "job.status").read_text().strip() != "PASS":
        raise ValueError("job 042 did not pass")
    if not (build / "base-tree.txt").read_text().startswith("base tree: boot036 "):
        raise ValueError("job 042 did not build on the boot036 tree")
    image = (build / "Image-mtp-input-boot036").read_bytes()
    recorded = (build / "image-sha256.txt").read_text().split()[0]
    if sha256(image) != recorded:
        raise ValueError("Image differs from the digest job 042 recorded")
    if args.expect_image_sha256 and sha256(image) != args.expect_image_sha256.lower():
        raise ValueError("Image is not the expected build: %s" % sha256(image))
    if image == previous["Image"]:
        raise ValueError("job 042's Image is boot036's Image")
    kernel_config = kconfig_guard.embedded_config(image)

    # The job records its own toolchain; the package's toolchain.txt must already say the same.
    wanted = (args.job_out / "toolchain.txt").read_text().splitlines()
    have = previous["toolchain.txt"].decode().splitlines()
    missing = [line for line in wanted if line not in have]
    if missing:
        raise ValueError("job 042's toolchain is not boot036's: %s" % missing)

    args.destination.mkdir(parents=True, exist_ok=False)
    delta = args.destination / "mtp-delta.json"
    built = args.destination / "t6050-j716c-stage-b.dtb"
    result = subprocess.run([sys.executable, "-I", str(TOOL), str(args.previous / "t6050-j716c-stage-b.dtb"),
                             str(args.adt), str(built), str(delta), "--sids", args.sids],
                            capture_output=True, text=True)
    if result.returncode:
        raise ValueError("DT tool failed: " + result.stderr.strip().splitlines()[-1])
    dtb = built.read_bytes()
    if dtb != (build / "mtp.dtb").read_bytes():
        raise ValueError("DT built here differs from the DT job 042 built in the VM")
    built.unlink()

    export = args.destination / "export"
    export.mkdir()
    out = dict(previous, **{"Image": image, "kernel.config": kernel_config, "t6050-j716c-stage-b.dtb": dtb})
    for name in FILES:
        (export / name).write_bytes(out[name])
    record = {
        "package": "ilinux-j716c-boot037 (staged)",
        "previous": baseline["package"],
        "image": {"sha256": sha256(image), "bytes": len(image), "source": "job 042 (VM, boot036 tree)"},
        "stage_b_dtb": {"sha256": sha256(dtb), "bytes": len(dtb), "base_sha256": sha256(previous["t6050-j716c-stage-b.dtb"]),
                        "equal_to_vm_built": True, "sids": args.sids},
        "kernel_config": {"sha256": sha256(kernel_config), "bytes": len(kernel_config), "source": "embedded in the Image"},
        "unchanged_from_boot036": [n for n in FILES if out[n] == previous[n]],
    }
    (args.destination / "stage-record.json").write_text(json.dumps(record, indent=2) + "\n")
    for name in FILES:
        print("%-28s %10d  %s  %s" % (name, len(out[name]), sha256(out[name]),
                                      "boot036" if out[name] == previous[name] else "NEW"))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("STOP:", type(exc).__name__, str(exc), file=sys.stderr)
        sys.exit(1)
