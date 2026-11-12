# M1: 31AH independent offline review

Read `native/boot/attempt31ah/README.md` and the latest status entries first.
This supersedes the dormant 31AG handoff for **offline work only**. Preserve
unrelated local changes and all old attempt records. No install, firmware,
security, volume, Startup Disk, proxy, camera activation or restart is requested.

The M5 built the exact public Aura/kernel revisions reported for J716c, with
an explicitly reconstructed diagnostic configuration and a separate original
USB delta. Native entry and eighteen physical cores remain NOT RUN. Source and
artifact hashes, not an old attempt approval, identify the material to review.

## Pull and verify

From your existing iLinux checkout, run `git status --short` before updating.
Use a fast-forward update only if your local state permits it; preserve any
M1 work. Do not reset, clean, rewrite history or automatically resolve conflicts.

The user can AirDrop **ilinux-direct31ah-offline.tar.gz** from the M5's
`build/direct31ah-package/` directory. No binary Release was published. Never
substitute an older boot package. If AirDrop renames it, pass its actual path.
Do not unpack the tar, load its modules, execute Linux binaries or open USB.

One block, from the checkout root, after the file arrives in Downloads:

```sh
(
  set -eu
  shasum -a 256 -c native/boot/attempt31ah/source-sha256.txt
  python3 -I tools/m1n1-client/test_review31ah.py
  python3 -I tools/m1n1-client/direct31ah/test_timeline.py
  python3 -I kernel/experiments/direct31ah/linux/test_offline.py
  python3 -I virtualization/jobs/095-direct31ah-kernel/test_check_vm.py
  python3 -I tools/m1n1-client/review31ah.py \
    --manifest native/boot/attempt31ah/manifest.json \
    --package "$HOME/Downloads/ilinux-direct31ah-offline.tar.gz"
)
```

Expected: every inventory hash OK; **46 +24 +26 +18 methods PASS**; reader ends
`OFFLINE_INTEGRITY_PASS`, `read_only:true`, `extracted:false`,
`native_ready:false`. The additional 24 padding methods and six C policy
assertions ran inside the M5's isolated Linux build VM. M1 need not repeat a
kernel build or install a toolchain to review their evidence. Archive validation
checks strict USTAR metadata, complete gzip/CRC, member bounds and all hashes.
A PASS is artifact integrity, not permission to boot.

## Independent review

Check manifest/source pins against the external J716c report; preserve the
separate baseline/USB-delta identities. Review the resolved kernel config,
SEP/storage exclusion, sanitized DT, padded-image geometry and source binding.
Read the actual full-build/VM/Apple-inspector evidence in
`native/boot/attempt31ah/offline-validation.json`; distinguish what was run from
what was reviewed. The VM ran the actual Image and private diagnostic initramfs,
not Aura or the firmware. No macOS performance comparison was performed.

Read `tools/m1n1-client/direct31ah/camera-protocol.md`. Report whether an existing
webcam or M1 camera could frame the M5 screen and whether a human-operated
recorder is available. **Do not open it, trigger permissions or record yet.**
For a later separately approved attempt, it can record repeated screen summaries
alongside M1's timestamped controller events. Keep media private under ignored
`build/`; publish only a sanitized observation summary. Audio should be disabled.

Return a concise result with the exact reviewed Git commit, source inventory,
package digest/bytes, fresh test counts, any actionable issue, and unresolved
firmware/control/restoration gates. Native boot, USB handshake, physical CPUs,
N1/GPU/NVMe, camera recording, boot restoration and new policy checks remain
**NOT RUN / UNCONFIRMED** unless separately evidenced. Do not request another
routine desktop security command. Do not prepare a Recovery page or restart.

Public source/report: <https://github.com/aurora-silicon/linux/discussions/142>.
This project remains an independent Omarchy environment built on open Apple
Silicon enablement; source reuse replaces speculative startup sequences without
claiming upstream acceptance or performance parity.
