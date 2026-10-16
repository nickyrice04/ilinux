# RAM-root launch profile (job 039), prepared offline

2026-10-15, updated 2026-10-16, M5 side session. **Native RAM-root boot NOT RUN.**
Nothing here touched hardware, USB or a live session. The launcher change is in
`9ee6b2f`. Labels: Confirmed / Likely / Hypothesis / Unknown.

`launch.py --profile ramroot` boots the Omarchy-style RAM root from VM job 039
([report](../../omarchy-arm64/ram-root-report-2026-10-15.md)) instead of the
diagnostic initramfs. It uses the current handoff's package (Image, Stage-B DT
and m1n1, checked against `package-manifest.json`) and every preflight gate of the
Stage-B path. Without `--profile`, the launcher is the reviewed Stage-B launcher,
byte for byte (see Evidence).

| | `stage-b` (default, unchanged) | `ramroot` |
|---|---|---|
| initrd | `initramfs-stage-b.cpio.gz` from the package | `--ramroot` file, size and SHA-256 checked against [`ramroot-manifest.json`](ramroot-manifest.json), plus an optional key cpio |
| Fixed arguments | the diagnostic set | `console=tty0 rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 pd_ignore_unused clk_ignore_unused quiet` |
| m1n1's `idle=nop arm64.nowfxt` | tolerated (already in the fixed set) | **required, exactly**: the pinned m1n1 appends it on M4 and later (`kboot.c`), and WFI loses state without it |
| Confirmation | `BOOT-J716C-RAM-DIAGNOSTIC` | `BOOT-J716C-RAM-ROOT` |
| Deadline | 180 s | 300 s |
| Upload | about 45 MB | about 227 MB: 45–57 s at 5–4 MB/s (Inferred) |

The launcher refuses:

* a RAM root whose size or SHA-256 differs from the record;
* a package whose Image is not the one the RAM root was built for (its modules
  match that Image only);
* Stage-B arguments under `ramroot`, and RAM-root arguments under `stage-b`;
* any third profile.

## Before anyone starts it

1. **Baseline: met.** Attempt 16 (boot035) completed its release ladder with no
   reset, and attempt 17 (boot036) held that baseline. The Images since boot034
   arm the genpd release ladder whenever `pd_ignore_unused` is set, so it also
   runs in a RAM-root boot. `quiet` hides its lines, so a reset or a dark panel
   under this profile cannot be attributed; use Stage-B for that.
2. **A RAM root built for the package's Image.** The record pins job 039 run 30
   (182,092,876 bytes, `58bdc6ce…`, built for the boot035 Image `1131a1af…`; the
   image and its digest are kept in `out/runs/run30/`). The handoff manifest is
   now boot038's (Image `e0e53113…`), so the launcher refuses this pairing:
   `package Image differs from the Image the RAM root was built for` (Confirmed
   offline, 2026-10-16). Attempt 19, a RAM root on boot038's kernel and DT, needs
   a job 039 build for that Image (`KTREE`, `KERNEL` and `IMAGE_SHA` in
   `out/job.env`). Pin it here with `image_sha256` set to that Image.

   Every rebuild changes the digest, because the image records its build time.
   After a later run, the launcher refuses the new file until `size` and `sha256`
   are copied from `out/ramroot.cpio.zst.sha256` into `ramroot-manifest.json` and
   `source` is updated.
3. **Move the image privately** to the controller, for example to
   `build/ramroot/ramroot.cpio.zst` (ignored). Never use Git or a release: the
   image holds its SSH host key.
4. **Operator key (optional):** the controller's public key, for example
   `~/.ssh/id_ed25519.pub`. The launcher writes plain public keys, without
   comments, to `/etc/ssh/authorized_keys.d/root` (0600, root) in a cpio
   zero-padded to a 4-byte boundary, and prints each key's SHA256 fingerprint.
   The boot035 Stage-B DT has no USB device-mode controller. The boot036/038 DT
   has three. The RAM root's gadget follows boot038's Stage-B: one configuration
   with CDC-ACM (a read-only journal; macOS shows `/dev/cu.usbmodem*`) and then
   CDC-ECM (network), using the same port table and MACs; `bcdDevice` 0x0039.
   SSH is then `ssh root@10.66.0.2`, or `root@fe80::69:6cff:fe69:6e0N%<interface>`
   on port N.
5. **Controller digests: done.** `9ee6b2f` committed the profile, and the Stage-B
   checklist has pinned `launch.py` at `4d55f0c9…` since `0363bd5`.

## Starting it (a human, with separate authorization)

The commands assume the planned attempt-19 package, boot038. They pass only once
the record pins a RAM root built for that package's Image (point 2).

Offline on the controller first; this opens no USB:

```sh
python3 -I native/boot/launch.py --package build/native-boot038-download/ilinux-j716c-boot038 \
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
  --package build/native-boot038-download/ilinux-j716c-boot038 \
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
  * then Hyprland with the wallpaper, waybar and a foot status window, 8–16 s
    after kernel start. In the VM under TCG this took 68.4 s (run 30).
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
* **Real dry runs with run 30 (Confirmed offline, 2026-10-16):**
  * At HEAD, with the boot038 manifest, the boot038 package stops on the Image
    check, and the boot035 package fails the package check.
  * A scratch copy of the launcher carrying boot035's manifest gives
    `RAM root PASS`, so the record itself is right. The upload is 226,753,047
    bytes: 45.4 s at 5 MB/s, 56.7 s at 4 MB/s.
  * A key adds a 724-byte cpio; 182,092,876 is a multiple of 4, so there is no
    padding.
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
