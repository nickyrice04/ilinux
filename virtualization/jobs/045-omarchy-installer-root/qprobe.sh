# qprobe.sh: QPROBE=1 in out/job.env. How large an -initrd QEMU's arm loader accepts here:
# sparse files of several sizes, QEMU started paused (-S) and stopped after 8 s. Changes nothing.
stage_qprobe() {
    local P=/run/ilinux-045/qprobe TOOLS=$W/tools s rc
    mkdir -p "$P"; mountpoint -q /run/ilinux-045 || { mkdir -p /run/ilinux-045; mount -t tmpfs -o size=9G tmpfs /run/ilinux-045; mkdir -p "$P"; }
    cp "$KERNEL" "$P/Image"
    chroot_up "$TOOLS"; mkdir -p "$TOOLS/work"; mount --bind "$P" "$TOOLS/work"
    : > "$OUT/qprobe.txt"
    for s in 1900M 2047M 2049M 3100M; do
        rm -f "$P/initrd"; truncate -s "$s" "$P/initrd"
        rc=0
        chroot "$TOOLS" timeout 8 qemu-system-aarch64 -machine virt,gic-version=3 -accel tcg -cpu max -m 20G \
            -kernel /work/Image -initrd /work/initrd -append console=ttyAMA0 -display none -S > "$P/out.txt" 2>&1 || rc=$?
        echo "initrd $s: exit $rc ($( [ $rc = 124 ] && echo loaded || echo refused)) $(tr '\n' ' ' < "$P/out.txt")" >> "$OUT/qprobe.txt"
    done
    rm -f "$P/initrd"
    chroot_down "$TOOLS"
    cat "$OUT/qprobe.txt"
}
