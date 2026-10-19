#!/usr/bin/env python3
"""check_config_delta.py BEFORE AFTER: boot042's kernel config is boot041's with exactly one change set.

The contract itself is native/boot/boot042_modules.py (check_config, CONFIG_DELTA), which the packager's
boot042 rule uses too; this wrapper lets VM job 050 check its own build against it and prints the delta.
The keyboard path and the storage drivers become modules, HIDRAW is switched on, and nothing else changes.
Standard library only; runs on the Mac and in the job VM.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "native/boot"))
import boot042_modules  # noqa: E402
from kconfig_guard import config_delta  # noqa: E402


def main(argv):
    if len(argv) != 3:
        raise SystemExit(__doc__.splitlines()[0])
    before, after = open(argv[1]).read(), open(argv[2]).read()
    for name, (b, a) in sorted(config_delta(before, after).items()):
        print("delta: %s: %s -> %s" % (name, b, a))
    try:
        boot042_modules.check_config(before, after)
    except ValueError as exc:
        print("FAIL:", exc)
        raise SystemExit(1)
    print("config delta PASS: exactly the %d boot042 symbols changed (native/boot/boot042_modules.py)"
          % len(boot042_modules.CONFIG_DELTA))


if __name__ == "__main__":
    main(sys.argv)
