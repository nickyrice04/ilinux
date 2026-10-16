# RAM-root launch profile (job 039), prepared offline

2026-10-15, M5 side session. **Native RAM-root boot NOT RUN.** Nothing here touched
hardware, USB or a live session. Not committed. Labels: Confirmed / Likely /
Hypothesis / Unknown.

`launch.py --profile ramroot` boots the Omarchy-style RAM root from VM job 039
([report](../../omarchy-arm64/ram-root-report-2026-10-15.md)) instead of the
302 KB diagnostic initramfs. It uses the same package (boot035 Image, Stage-B DT
and m1n1) and every preflight gate of the Stage-B path. Without `--profile`, the
launcher is the reviewed Stage-B launcher, byte for byte (see Evidence).

| | `stage-b` (default, unchanged) | `ramroot` |
|---|---|---|
| initrd | `initramfs-stage-b.cpio.gz` from the package | `--ramroot` file, size and SHA-256 checked against [`ramroot-manifest.json`](ramroot-manifest.json), plus an optional key cpio |
| Fixed arguments | the diagnostic set | `console=tty0 rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 pd_ignore_unused clk_ignore_unused quiet` |
| m1n1's `idle=nop arm64.nowfxt` | tolerated (already in the fixed set) | **required, exactly**: the pinned m1n1 appends it on M4 and later (`kboot.c`), and WFI loses state without it |
| Confirmation | `BOOT-J716C-RAM-DIAGNOSTIC` | `BOOT-J716C-RAM-ROOT` |
| Deadline | 180 s | 300 s |
| Upload | about 45 MB | 226.7 MB: 45.3 s at 5 MB/s, 56.7 s at 4 MB/s (Inferred) |

The launcher refuses:

* a RAM root whose size or SHA-256 differs from the record;
* a package whose Image is not the one the RAM root was built for (its modules
  match that Image only);
* Stage-B arguments under `ramroot`, and RAM-root arguments under `stage-b`;
* any third profile.

## Before anyone starts it

1. **Attempt 16 first.** The boot035 Image arms the genpd release ladder
   whenever `pd_ignore_unused` is set, so the ladder also runs here, from about
   19 s to about 94 s of kernel time. `quiet` hides its lines. Run this profile only
   after attempt 16 has reached `ladder complete` with the panel still lit and
   heartbeats to 180 s. A reset or a dark panel during this profile cannot be
   attributed; use Stage-B for that.
2. **Use the recorded build.** The record pins job 039 run 22
   (182,089,436 bytes, `c4b1daf7…`, built for the boot035 Image `1131a1af…`;
   the digest is kept in `out/runs/run22/`). Every rebuild changes the digest,
   because the image records its build time. After a later run, the launcher
   refuses the new file until `size` and `sha256` are copied from
   `out/ramroot.cpio.zst.sha256` into `ramroot-manifest.json` and `source` is
   updated.
3. **Move the image privately** to the controller, for example to
   `build/ramroot/ramroot.cpio.zst` (ignored). Never use Git or a release: the
   image holds its SSH host key.
4. **Operator key (optional):** the controller's public key, for example
   `~/.ssh/id_ed25519.pub`. The launcher writes plain public keys, without
   comments, to `/etc/ssh/authorized_keys.d/root` (0600, root) in a cpio
   zero-padded to a 4-byte boundary, and prints each key's SHA256 fingerprint.
   The boot035 Stage-B DT has no USB device-mode controller, so SSH is not
   reachable on boot035 anyway. The key matters once a DT with dwc3 is used
   (boot036): then `ssh root@10.66.0.2`, or `root@fe80::69:6cff:fe69:6e0N%<interface>`
   on port N, as in boot036.
5. **Controller digests.** `launch.py` no longer matches the digest
   `65ece253…` that `tools/m1n1-client/stage-b-instructions.md` pins for
   attempt 16. Commit this after attempt 16, or update that digest in the same
   commit. `entry_guard.py`, `fdt.py` and the other controller files are
   unchanged.

## Starting it (a human, with separate authorization)

Offline on the controller first; this opens no USB:

```sh
python3 -I native/boot/launch.py --package build/native-boot035-download/ilinux-j716c-boot035 \
  --profile ramroot --ramroot build/ramroot/ramroot.cpio.zst --operator-key ~/.ssh/id_ed25519.pub
python3 -I native/boot/test_ramroot.py
```

Expect `RAM root PASS`, the boot arguments, `m1n1 must append: idle=nop
arm64.nowfxt` and the upload estimate, then 30 tests OK.

The live run uses the physical procedure from the Stage-B checklist: restart the
controller fresh and keep it awake, film the M5 panel, choose **iLinux Boot Lab →
Continue**, and wait for the proxy. Then run this once:

```sh
tools/m1n1-client/run.sh native/boot/launch.py \
  --package build/native-boot035-download/ilinux-j716c-boot035 \
  --profile ramroot --ramroot build/ramroot/ramroot.cpio.zst \
  --operator-key ~/.ssh/id_ed25519.pub \
  --launch --device auto --confirm BOOT-J716C-RAM-ROOT
```

What to expect:

* After `Uploading DT, initramfs and kernel to RAM.` there is no output for
  about 45–57 s.
* Then the usual checkpoints and the handoff.
* On the panel (Hypothesis, from the VM):
  * the three pre-MMU rectangles at the top left (the framebuffer descriptor is
    filled as in Stage-B);
  * little or no text;
  * then Hyprland with waybar and a foot status window, 8–16 s after kernel
    start. In the VM under TCG this took 67.9 s.
* Stop at a reset, a dark panel, or 180 s from the handoff.
* Return to Macintosh HD.

## Evidence (offline, this Mac)

* **Tests:** `test_ramroot.py` has 30 tests, all OK. The existing suites still
  pass with unchanged counts: 37 launcher, 6 entry, 10 GPIO, 16 DAPF,
  5 framebuffer and 19 hardware.
* **Stage-B is unchanged (Confirmed):**
  * Each case runs through both the new launcher and the reviewed one (git
    object `f2b2c4d`, SHA-256 `65ece253…`). The test compares every proxy
    request, upload, printed line and error. That covers 17 session cases,
    6 command lines and the controller deadline.
  * The real boot035 package's offline output is byte-identical between the
    two.
* **Mutation checks:** 19 deliberate mutations, all caught by `test_ramroot.py`.
  Four of the eight Stage-B mutations pass the existing `test_launcher.py`:
  Stage-B arguments gaining `quiet`, a swapped upload order, a changed
  confirmation token, and an extra printed line.
* **Real dry run (Confirmed offline):** the real boot035 package and the run-22
  image give `RAM root PASS`. The upload is 226,749,607 bytes: 45.3 s at
  5 MB/s, 56.7 s at 4 MB/s. A key adds a 724-byte cpio with no padding, since
  182,089,436 is a multiple of 4.
* **Real-size run:** the real boot035 package plus a synthetic 182,081,015-byte
  file. The RAM-root offline path took 0.25 s. The upload is 226,741,911 bytes
  with a 724-byte key cpio after 1 pad byte.
* **Client checksum:** the launcher never negotiates m1n1's
  `DISABLE_DATA_CSUMS`, so the client computes m1n1's per-byte checksum in
  Python. That runs at 17.5 MB/s on this Mac, about 13 s of a RAM-root upload.
  The roadmap's 4–5 MB/s figure does not say whether it includes this; the time
  grows with size either way (Inferred).
* **NOT RUN:** hardware, USB, the two ADT suites (they need the controller venv)
  and a native RAM-root boot.
