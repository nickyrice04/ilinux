# GPU 31P offline build

VM-only upstream compiler and driver foundation build. Native GPU operation is
**NOT RUN**. See `research/native31p-gpu-build.md` for evidence and limitations.

The coordinating agent must hold the shared VM locks. Use `--no-net`, 4 CPUs,
12 GiB, and read-only public inputs:

- `gpu31p-sources`: files listed in `sources.json` and `packages.json`, each
  package accompanied by its `.sig` file.
- `ilinux`: curated public project sources, excluding ignored/private content.
- `job`: this directory, read/write for `out/`.

Download each exact URL in the manifests; verify sizes and SHA-256 before use.
The signatures were taken from the official ALARM repository metadata and are
verified against the guest's existing trust policy before isolated extraction.
Run the original `verify-inputs.py JOB_DIR SOURCE_DIR` to check all 22 inputs.
It is not a signature verifier; the VM's strict GPG status check performs that step.

`run.sh` verifies every package signature against tmpfs copies of the existing
public keyring/trust database, requiring VALIDSIG plus full/ultimate trust. It
extracts only authenticated package payloads into a 6 GiB tmpfs compiler prefix,
then builds/tests Mesa there. No package installation, maintainer scripts, key
import, dependency bypass or global compiler change occurs. Exact Rust runtime
dependencies remain intact; the optional kernel recipe is explicitly deferred.
Read `out/summary.json`, individual test logs and `kernel-exit.txt`; never equate
a successful compiler test with native GPU compatibility.

Source archives, packages, generated executables and all `out/` content remain
ignored. Commit only these original scripts/manifests and reviewed findings.

Validated on 2026-10-22: 514 build actions; 396 individual compiler/layout/library
tests PASS; four upstream test-source warnings; no package changes.
See `validation.json` for exact versions, hashes, limitations and previous refusals.
