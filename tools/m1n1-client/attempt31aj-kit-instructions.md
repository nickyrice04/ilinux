# M1: review the complete 31AJ kit offline

Read `native/boot/attempt31aj-kit/README.md` first. The earlier M1 component PASS
is incorporated; this handoff supplies the missing native reader, complete
actual-31AF transaction, readable Linux diagnostic and exact local artifacts.

Use an isolated clean checkout of the new M5 commit. Preserve the original
checkout's five unfinished status edits and unrelated work. Do not reset,
clean, stash or silently merge them. Verify the three older source inventories
unchanged; do not rerun their complete unchanged suites.

Transfer the whole four-file folder `build/ilinux-31aj-review/` locally from M5
to the same relative path in that clean checkout. Do not upload it publicly.
No M1 restart, camera test, USB/proxy session, live helper, Recovery command,
security change or native test is requested.

From the clean checkout root, this block performs only offline verification and
creates new workspace files. If either output already exists, choose a new
workspace basename after review; do not delete prior evidence to force a rerun.

```sh
python3 -I - <<'PY'
from pathlib import Path
import hashlib, subprocess, sys
root = Path.cwd()
for name in ('native/boot/attempt31ah/source-sha256.txt',
             'native/boot/attempt31ai/source-sha256.txt',
             'native/boot/attempt31aj-source-sha256.txt',
             'native/boot/attempt31aj-kit/source-sha256.txt'):
    rows = (root / name).read_text().splitlines()
    for row in rows:
        digest, path = row.split('  ', 1)
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != digest:
            raise SystemExit('STOP: source inventory mismatch')
    print(f'PASS: {name}: {len(rows)} entries')
checks = [
 ['tools/recovery31aj/test_recovery.py'],
 ['tools/recovery31aj/test_stage_lab.py'],
 ['tools/recovery31aj/test_serve.py'],
 ['tools/m1n1-client/direct31aj-kit/test_package.py'],
 ['tools/m1n1-client/direct31aj-kit/test_materialize.py'],
 ['kernel/experiments/direct31aj/test_collector.py'],
 ['tools/boot-object31aj-native/test_schema_probe.py'],
 ['tools/boot-object31aj-native/test_native.py', '--sanitize'],
 ['tools/m1n1-client/direct31aj-kit/package.py', '--manifest',
  'native/boot/attempt31aj-kit/manifest.json', '--folder', 'build/ilinux-31aj-review'],
 ['tools/m1n1-client/direct31aj-kit/materialize.py', '--manifest',
  'native/boot/attempt31aj-kit/manifest.json', '--folder', 'build/ilinux-31aj-review',
  '--profile', 'native/boot/attempt31aj-kit/recovery-profile.json',
  '--output', 'build/31aj-m1-prepared'],
 ['tools/recovery31aj/prepare.py', '--profile',
  'native/boot/attempt31aj-kit/recovery-profile.json', '--kit', 'build/31aj-m1-prepared',
  '--source-inventory', 'native/boot/attempt31aj-kit/source-sha256.txt',
  '--output', 'build/31aj-m1-pages'],
 ['tools/recovery31aj/serve.py', '--page',
  'build/31aj-m1-pages/recovery.html', '--check-only'],
]
for args in checks:
    subprocess.run([sys.executable, '-I', *args], check=True)
print('OFFLINE REVIEW COMMANDS COMPLETE. No live action authorized.')
PY
```

Inspect the resulting `build/31aj-m1-pages/recovery.html`, install/restore text
and receipt as data. Do not paste either block into Terminal. The prepared
four-file directory and sibling materialization receipt are workspace-only;
do not run the lab stager. The production helper is hash-inspected, not run in
its live/capability/private-group modes. The sanitizer suite builds its own
original synthetic fixture helper; it does not query policy or use root.

Review the v2 reader's bounded DER/LZFSE and supported metadata comparison,
initial admission versus bound baseline, the two complete blocks, spent markers,
fresh readback on command failure, and independent restoration when the candidate
is missing. Confirm `bputil -n` and automatic reboot/default-selection commands
are absent. Note that pairing and binary compatibility remain real Recovery
questions; there is no requirement to prove native entry before testing entry.

The provided M5 actual-byte C fixture receipt uses production v2 plus synthetic
CF policy/volume data. Its producer-workspace-bound fixture paths intentionally
prevent rerunning that delivered helper's fixture mode in another checkout.
Review that receipt; the local sanitizer suite independently exercises its
source. No need to rebuild or re-qualify unchanged Aura/Linux in this review.

The server tests include two brief synthetic loopback controls. If the agent's
sandbox refuses loopback binding, use the normal tool approval for that focused
test command; do not launch a real LAN server as a substitute. `--check-only`
validates the actual prepared page without opening a socket. The future server
supports only `/` and `/31aj`, holds exact reviewed HTML in memory, logs no
clients and serves no artifact or directory. It has an absolute lifetime and
short client deadlines. Default binding is loopback; for a later authorized
Recovery session M1 supplies its chosen literal private LAN address with
`--bind`, an explicit `--port` if desired, and `--seconds` at most 1800. Provide
the resulting local URL privately. Do not start that production service now.

Publish an original sanitized review in `native/boot/`, update the five shared
status documents without editing any frozen inventory member, and push the
review. Report independently run checks separately from reviewed M5 evidence.
Mark staging, Recovery, installation, native boot, restoration, defaults and
performance **NOT RUN**, with native HOLD pending separate human approval.
Do not include private paths, identifiers, keys, metadata tokens or media.

For a later authorized physical run, follow the existing camera handoff:
fresh framing after a move, real RECORDING confirmation before the human cue,
independent maximum90-second native timer, stop or cover the camera before
Recovery credentials. Do not start another quality clip now. If installation
readback fails, do not boot; use the reviewed independent restoration path.
There is one native observation, no automatic retry. After restoration the
human separately confirms Macintosh HD desktop and default Startup Disk.
