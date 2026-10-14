# Job 022: correct the framebuffer handoff without rebuilding Linux

This isolated ARM64 VM job copies verified boot021 payloads and adds only a
framebuffer placeholder to the Stage-B DT. It compiles pinned m1n1's actual
`dt_set_fb()` with libfdt and sanitizers, then exercises synthetic video data.
No Apple binary, real ADT, USB target, host installation or native boot is used.
Generated C and all build outputs stay under ignored `out/`.

Hold the shared `quiet` lock in both active repositories; confirm the existing
VM disk is not in use. Do not run simultaneously with another agent's VM. With
a fresh job output directory, run from the original research checkout:

```sh
caffeinate -i virtualization/bin/vzrun --cpus 2 --mem 4 \
  --kernel virtualization/images/alarm/Image-7.1.6-vzrun2-pkg \
  --cmdline 'console=hvc0 root=/dev/vda rootflags=subvol=@ rw rootwait quiet loglevel=3' \
  --disk virtualization/images/alarm/root-btrfs.img \
  --share /ABS/PUBLISHED-REPO/virtualization/jobs/022-framebuffer-handoff:job \
  --share /ABS/ORIGINAL-REPO/third_party/m1n1:m1n1-source:ro \
  --share /ABS/VERIFIED-BOOT021-DIRECTORY:boot021:ro \
  --share /ABS/PUBLISHED-REPO:ilinux:ro
```

The existing guest job service runs `run.sh`, records exit/times and powers off.
Guest dependencies already present: gcc, dtc/libfdt, Python, construct, pyserial.
The job refuses to reuse `out/export`; preserve old evidence before rerunning.
All base payloads are checked against `native/boot/boot021-package-manifest.json`.
A semantic comparison proves the single new node is the entire DT change.

After the VM stops, release the locks. From the published checkout, package into
a fresh destination (never overwrite a published archive):

```sh
python3 -I native/boot/make-package.py \
  --out virtualization/jobs/022-framebuffer-handoff/out \
  --destination build/native-boot022 --name ilinux-j716c-boot022
python3 -I native/boot/launch.py --package virtualization/jobs/022-framebuffer-handoff/out/export
python3 -I native/boot/test_framebuffer.py
```

The packager requires every payload except the Stage-B DT to match boot021.
It retains the verified symbol offsets because the m1n1 bytes are identical.
It updates the tracked manifest/checksums; review before commit/release. Job 021
is historical provenance, not the recipe for a current launchable package.
See [RESULTS.md](RESULTS.md) and [M1 checklist](../../../tools/m1n1-client/stage-b-instructions.md).
