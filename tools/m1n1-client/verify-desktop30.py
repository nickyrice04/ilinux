#!/usr/bin/env python3
"""Verify the small pinned original-code bundle without extracting/executing it."""
import importlib.util
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('receiver',ROOT/'kernel/experiments/desktop30/receive.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
if __name__=='__main__':
    pin=json.loads((ROOT/'native/boot/attempt30/bundle.json').read_text())
    p=Path(sys.argv[1])
    if p.stat().st_size!=pin['size_bytes']:raise ValueError('bundle size differs')
    files=r.validate(p.read_bytes(),pin['size_bytes'],pin['sha256'])
    if json.loads(files['assets.json']) != json.loads((ROOT/'native/boot/attempt30/assets.json').read_text()):
        raise ValueError('embedded/public asset pins differ')
    if files['collect.py'] != (ROOT/'kernel/experiments/desktop30/collect.py').read_bytes():
        raise ValueError('bundled collector differs from reviewed repository source')
    print('PASS attempt30 exact bundle, four regular members and source equality; no extraction/execution/SSH')
