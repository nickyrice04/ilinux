#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Forward to isolated llvm-config, qualifying its relocatable path output."""
from pathlib import Path
import os
import subprocess
import sys

root = Path(os.environ["GPU31P_TOOLCHAIN"])
process = subprocess.run([str(root / "usr/bin/llvm-config"), *sys.argv[1:]],
                         capture_output=True, text=True, check=False)
sys.stderr.write(process.stderr)
# LLVM normally derives its installed prefix from its own executable. Handle
# compile-time /usr paths as well without rewriting already relocated paths.
for line in process.stdout.splitlines():
    tokens = []
    for token in line.split():
        if token == "/usr" or token.startswith("/usr/"):
            token = str(root) + token
        elif token.startswith(("-I/usr/", "-L/usr/")):
            token = token[:2] + str(root) + token[2:]
        tokens.append(token)
    print(" ".join(tokens))
sys.exit(process.returncode)
