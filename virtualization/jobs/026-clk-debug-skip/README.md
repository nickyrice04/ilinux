# Job 026: one clock-debug initializer skip

No new kernel build or release package. Reuse boot025 and the existing build VM.
Run executable `run.sh` with this folder shared writable as `job` and the repo
read-only as `ilinux`. It runs 69 offline/real-client cases and package verification;
outputs stay ignored. `M1N1_SOURCE` points to the guest's retained clean pin.

For the separate diskless/networkless generic VM, use the existing vzrun:

```sh
caffeinate -i virtualization/bin/vzrun \
  --kernel /ABS/PUBLISH/build/native-boot025/verified/Image \
  --initrd /ABS/PUBLISH/build/native-boot025/verified/initramfs-stage-b.cpio.gz \
  --cpus 1 --mem 4 --no-net \
  --cmdline 'console=hvc0 fbcon=nodefer rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 idle=nop arm64.nowfxt pd_ignore_unused clk_ignore_unused loglevel=8 ignore_loglevel printk.time=1 panic=0 earlycon=ilinuxfb initcall_debug initcall_blacklist=clk_debug_init'
```

Use the real absolute publish path. Do not attach a disk or run simultaneous
disk-backed jobs against the same image. Require exactly
`initcall clk_debug_init blacklisted`, no `calling clk_debug_init`, subsequent
initcall completion, PID 1, one CPU and the 60-second message. Stop this owned
diskless VM after the check; diagnostic PID 1 has no exit path. Generic VZ is
not an M5 AIC/display test. See the
[evidence and limitations](../../../kernel/experiments/clock-debug/README.md).
