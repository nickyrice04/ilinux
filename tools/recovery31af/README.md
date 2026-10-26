# 31AF reviewed Recovery pages

From the independently reviewed Git checkout, prepare both full Recovery phases:

```sh
python3 -I tools/recovery31af/prepare.py --output build/31af-reviewed-pages
```

The command reads `native/boot/attempt31af/source-sha256.txt` and verifies every
listed source before importing the pinned sibling renderer. The manifest,
renderer and preparation source must be included. Pin paths must be canonical
repository-relative regular files; symlinks, duplicate entries and an inventory
that pins itself are refused. The inventory is trusted through the reviewed Git
commit, rather than through a circular self-hash.

The manifest supplies the exact candidate size, SHA-256 and URL, which must agree
with its candidate file inventory. No manual profile or candidate pin is needed.
The output must be an absent directory beneath this repository's `build/`, with
no symlink components. Preparation rechecks all sources before writing output.

The new directory contains `install-paste.txt`, `rollback-paste.txt`,
`recovery.html`, `profile.json` and `render.json`. The report records input hashes,
the verified source count and hashes of all four rendered artifacts. Both blocks
include their independent fresh guards. Rendering performs no network access,
Recovery command, installation, restart or policy change. Running either phase
still requires independent M1 review and explicit human authorization of that
exact phase; generating the page is not authorization.

Run the synthetic preparation checks with:

```sh
python3 -I tools/recovery31af/test_prepare.py
```

These tests use temporary repositories and original renderer text. They check
complete blocks and digest bindings, security/renderer/manifest pin failures,
malformed inventories and candidate metadata, and output traversal, existing
directory and symlink refusals. They never execute the rendered shell blocks or
contact a device or network service.
