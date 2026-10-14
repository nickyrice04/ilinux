# Job 021: export, package and test the first native RAM payload

**Historical recipe:** boot021 lacks the framebuffer placeholder. Current launches
require the DT-only [job 022 correction](../022-framebuffer-handoff/README.md);
the strengthened current verifier intentionally rejects the original Stage-B DT.
Do not rebuild or republish boot021 to prepare the next attempt.

Runs in the existing ARM64 job VM, never as a native M5 boot. All VM disks and
build outputs stay ignored. Hold the shared `quiet` lock; verify the VM disk
is not attached to another running VM before starting it.

The existing job-020 tree must remain at `/var/tmp/t6050-build`. `run.sh`
exports it without rebuilding it. In the original research checkout, run:

```sh
caffeinate -i virtualization/bin/vzrun --cpus 6 --mem 16 \
  --kernel virtualization/images/alarm/Image-7.1.6-vzrun2-pkg \
  --cmdline 'console=hvc0 root=/dev/vda rootflags=subvol=@ rw rootwait quiet loglevel=3' \
  --disk virtualization/images/alarm/root-btrfs.img \
  --share /ABS/PUBLISHED-REPO/virtualization/jobs/021-native-boot-package:job \
  --share /ABS/ORIGINAL-REPO/third_party/m1n1:m1n1-source:ro \
  --share /ABS/PUBLISHED-REPO:ilinux:ro
```

Substitute the actual repository directories, not raw disk devices. The
`no-poweroff` marker keeps this isolated guest available after export for
commands at its console. Inside the guest only:

```sh
pacman -S --needed --noconfirm rust rust-src dtc imagemagick python-construct python-pyserial
bash /mnt/job/build.sh > /mnt/job/out/package-build.log 2>&1
```

`build.sh` uses a disposable copy of pinned m1n1, cleans its build directory,
links the complete raw image and verifies the source stays unchanged. Rust
`BUILDSTD=1` uses the guest's matching `rust-src`; no host toolchain install.
It compiles a separate diagnostic initramfs and adjusts a copy of the DT.
It never loads a native payload onto the physical M5.

On the host, from the published repository:

```sh
python3 -I native/boot/make-package.py --out virtualization/jobs/021-native-boot-package/out --destination build/native-boot
python3 -I native/boot/launch.py --package virtualization/jobs/021-native-boot-package/out/export
python3 -I native/boot/test_launcher.py
```

The packager checks all three original job-020 hashes, derives target symbol
offsets from the built ELF, checks the version marker against actual binary
bytes, and archives only an explicit list of nonsensitive files. It rewrites
the tracked manifest/checksum: review any changes before publishing a new
version. Do not replace a previously published asset under the same tag.

In the Linux guest, run the offline unit and real serializer tests:

```sh
python3 -I /mnt/ilinux/native/boot/test_launcher.py
M1N1_SOURCE=/var/tmp/ilinux-boot021/m1n1 python3 -I /mnt/ilinux/native/boot/test_protocol.py
python3 -I /mnt/ilinux/native/boot/launch.py --package /mnt/job/out/export
```

Then `systemctl poweroff` that VM, wait for it to stop, and release its lock.

The kernel/initramfs can additionally be booted with `vzrun --cpus 1 --mem 4
--no-net`, using `out/export/Image`, `out/export/initramfs-stage-b.cpio.gz`,
no disk and `--cmdline 'console=hvc0 rdinit=/init maxcpus=1 nr_cpus=1 panic=0'`.
Bound the run to 65 seconds and terminate only that test process. This uses
Virtualization.framework's DT/console, not the physical J716c DT/framebuffer.
It tests generic ARM64 boot/PID 1, never Apple native interfaces.

See [RESULTS.md](RESULTS.md) and the [M1 handoff](../../../native/boot/README.md).
