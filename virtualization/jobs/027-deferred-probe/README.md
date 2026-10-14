# Job 027: deferred-probe and timer-progress diagnostics

Hold the shared quiet lock and ensure the build disk is not in use. From the
original research checkout, using actual absolute PUBLISH/ORIGINAL paths:

```sh
caffeinate -i virtualization/bin/vzrun --cpus 2 --mem 4 \
  --kernel virtualization/images/alarm/Image-7.1.6-vzrun2-pkg \
  --cmdline 'console=hvc0 root=/dev/vda rootflags=subvol=@ rw rootwait quiet loglevel=3' \
  --disk virtualization/images/alarm/root-btrfs.img \
  --share /ABS/PUBLISH/virtualization/jobs/027-deferred-probe:job \
  --share /ABS/PUBLISH:ilinux:ro
```

The job requires the retained `/var/tmp/ilinux-boot025/linux` and stops if its
independent `/var/tmp/ilinux-boot027-v3/linux` output already exists. Preserve
previous results; do not overwrite published payloads. It verifies the old
Image, copies the tree, applies digest-gated diagnostics, runs actual-helper
sanitizer tests, links Image, checks config and exact ELF/Image roundtrip.
Only ignored outputs and the workspace-contained guest disk are written.

Package with the original stdlib tool:

```sh
python3 -I native/boot/make-package.py \
  --out virtualization/jobs/027-deferred-probe/out \
  --destination build/native-boot027 --name ilinux-j716c-boot027
```

It permits only Image to differ from `boot025-package-manifest.json`.
Run all eight controller test scripts listed in the current M1 checklist;
real parser/serializer tests need `M1N1_SOURCE` set to the clean pinned m1n1.

Diskless one-CPU validation uses the exact packaged Image/initramfs and:

```text
console=hvc0 fbcon=nodefer rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 idle=nop arm64.nowfxt pd_ignore_unused clk_ignore_unused loglevel=8 ignore_loglevel printk.time=1 panic=0 earlycon=ilinuxfb initcall_debug initcall_blacklist=clk_debug_init ilinux_probe_diag=1
```

Use `vzrun --cpus 1 --mem 4 --no-net --kernel ... --initrd ... --cmdline ...`
with no disk/shares. Require timer PASS/nonzero ticks, phases 1–9 and diagnostic
PID 1/one CPU/60-second heartbeat. Stop that owned diskless VM afterward.
This verifies generic Linux paths, not native M5 interrupt routing or driver
compatibility. [Evidence and phase definitions](../../../kernel/experiments/deferred-probe/README.md).
