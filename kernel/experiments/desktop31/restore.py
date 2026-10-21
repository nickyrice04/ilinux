#!/usr/bin/env python3
"""Independent end-of-unit reset to the original draw path. RAM only."""
import importlib.util
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('copy31', HERE/'collect.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
if __name__ == '__main__':
    assets = json.loads((HERE/'assets.json').read_text())
    _, ipc, _ = c.find_desktop(assets['sha256']['Hyprland-copy31'])
    c.set_mode(ipc, 0)
    print('COPY31_REFERENCE_PATH_RESTORED', flush=True)
