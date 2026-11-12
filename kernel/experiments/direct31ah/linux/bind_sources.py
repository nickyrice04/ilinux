#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind build outputs to unchanged original recipe/helper bytes."""
import hashlib
import json
import sys
from pathlib import Path

root=Path(sys.argv[1]).resolve();record=Path(sys.argv[2])
paths=[Path('virtualization/jobs/095-direct31ah-kernel')/name for name in ('run.sh','diagnostic.config')]
directory=Path('kernel/experiments/direct31ah/linux')
paths+=sorted(p.relative_to(root) for p in (root/directory).iterdir() if p.suffix in ('.py','.c'))
files={str(p):hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
if len(sys.argv)==4 and sys.argv[3]=='--verify':
    previous=json.loads(record.read_text())
    if previous.get('files')!=files:raise ValueError('recipe/helpers changed during the build; rerun with final sources')
else:
    if len(sys.argv)!=3:raise ValueError('unexpected arguments')
    record.write_text(json.dumps({'scope':'OFFLINE_BUILD_SOURCE_BINDING','algorithm':'sha256','files':files},indent=2)+'\n')
