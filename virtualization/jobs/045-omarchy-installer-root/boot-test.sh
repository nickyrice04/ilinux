# boot-test.sh: stage 4 of job 045, sourced by run.sh. Boot the RAM root the way m1n1 boots the
# M5, in QEMU (TCG, one vCPU) with the exact boot035 Image: direct kernel entry, the launcher's
# RAM-root arguments plus m1n1's append, and a device tree with the M5's root compatible (so
# Omarchy's platform detector answers as it will on the M5) and a /chosen simple-framebuffer
# (3456x2234 x2r10g10b10, the 16-inch panel) in reserved RAM, which simpledrm drives. No
# firmware, no virtio-gpu, no network to the outside. The test-only probe (test-overlay/,
# appended as a second cpio) marks the boot on the virtio console and drives the session; the
# harness captures the framebuffer when asked and collects the 9p results share.
# The initrd goes in as m1n1 puts it on the M5: the blob written into RAM and its bounds in
# /chosen (linux,initrd-start/end). QEMU's -initrd refuses files of 2 GiB or more (11.1.2:
# 2047 MiB loads, 2049 MiB does not; out/qprobe.txt), so the blob is loaded in 1 GiB pieces by
# QEMU's generic loader. Job 039's harness pieces are reused read-only: fb2png.py and
# tools/qemumon.py.

FB_ADDR=0x220000000                 # inside the guest's 32 GiB, reserved (no-map)
INITRD_ADDR=0x100000000             # 3 GiB into RAM, below the framebuffer for initrds up to 4.5 GiB
FB_W=3456 FB_H=2234 FB_FMT=x2r10g10b10
FB_STRIDE=$((FB_W * 4))
FB_SIZE=$((FB_STRIDE * FB_H))
FB2PNG=/mnt/ilinux/virtualization/jobs/039-omarchy-ram-root/fb2png.py
# The launcher's RAM-root arguments, then what the pinned m1n1 appends on M4 and later; the VM
# adds console=hvc0 for the markers.
CMDLINE="console=tty0 console=hvc0 rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 pd_ignore_unused clk_ignore_unused quiet idle=nop arm64.nowfxt"

# electron_apps ROOT: "name class-regex command" for every installed app that runs on Electron
# (a package depending on an electron runtime, or shipping its own resources/app.asar), launched
# as Omarchy's bindings launch apps (uwsm-app --).
electron_apps() {
    local root=$1 pkg desktop exe cls
    { pac "$root" -Qi | awk -F': ' '/^Name/ {n=$2} /^Depends On/ {if ($2 ~ /(^| )electron[0-9]*([ ><=]|$)/) print n}'
      pac "$root" -Ql | awk -v r="$root" '$2 ~ /\/resources\/app\.asar$/ {print $1}'
    } | sort -u | grep -v -E '^electron[0-9]*$' | while read -r pkg; do
        desktop=$(pac "$root" -Ql "$pkg" | awk '{print $2}' | grep -E '/usr/share/applications/[^/]+\.desktop$' | head -1)
        [ -n "$desktop" ] || continue
        exe=$(sed -n 's/^Exec=\([^ ]*\).*/\1/p' "$desktop" | head -1)
        cls=$(sed -n 's/^StartupWMClass=//p' "$desktop" | head -1)
        echo "$pkg ${cls:-$(basename "$exe")} uwsm-app -- $exe"
    done
}

stage_boot_test() {
    mkdir -p "$OUT/test"
    TOOLS=$W/tools
    log "test tools"
    if [ ! -x "$TOOLS/usr/bin/qemu-system-aarch64" ]; then
        rm -rf "$TOOLS"
        mkdir -p "$TOOLS/var/lib/pacman" "$TOOLS/var/log" "$TOOLS/etc/pacman.d/hooks"
        chroot_up "$TOOLS"
        pac_retry "$TOOLS" "$OUT/test/tools-install.log" -y qemu-system-aarch64 openssh
        chroot_down "$TOOLS"
    fi
    pac "$TOOLS" -Q qemu-system-aarch64 openssh > "$OUT/test/tools.txt"
    X=$T/test
    rm -rf "$X"
    mkdir -p "$X/results"
    cp "$KERNEL" "$X/Image"
    chroot_up "$TOOLS"
    mkdir -p "$TOOLS/work"
    mount --bind "$X" "$TOOLS/work"
    mkdir -p "$W/testkey"
    if [ ! -f "$W/testkey/id_ed25519" ]; then   # VM-test keys; they stay on the work disk
        chroot "$TOOLS" ssh-keygen -q -t ed25519 -N '' -C ilinux045-vm-test -f /work/id_ed25519
        chroot "$TOOLS" ssh-keygen -q -t ed25519 -N '' -C ilinux045-vm-test-host -f /work/host_ed25519
        cp "$X"/id_ed25519* "$X"/host_ed25519* "$W/testkey/"
    fi
    install -m 0600 "$W/testkey/id_ed25519" "$X/id_ed25519"

    # The test-only cpio, appended after the image (4-byte aligned, as the kernel requires).
    O=$T/test-overlay
    rm -rf "$O"
    cp -R "$J/test-overlay" "$O"
    install -m 0600 "$W/testkey/host_ed25519" "$O/etc/ssh/ilinux045_host_ed25519_key"
    install -m 0600 "$W/testkey/id_ed25519.pub" "$O/etc/ssh/ilinux045_authorized_keys"
    mkdir -p "$O/usr/local/share/ilinux045"
    electron_apps "$C" > "$O/usr/local/share/ilinux045/electron-apps.txt"
    cp "$O/usr/local/share/ilinux045/electron-apps.txt" "$OUT/test/electron-apps.txt"
    ( cd "$O" && find . -mindepth 1 -printf '%P\n' | LC_ALL=C sort |
      cpio --quiet -o -H newc --reproducible -R 0:0 ) > "$X/test-overlay.cpio"
    cp "$OUT/ramroot.cpio.zst" "$X/initrd"
    head -c $(( (4 - $(stat -c %s "$X/initrd") % 4) % 4 )) /dev/zero >> "$X/initrd"
    cat "$X/test-overlay.cpio" >> "$X/initrd"
    local isize part off=0
    isize=$(stat -c %s "$X/initrd")
    [ $((INITRD_ADDR + isize)) -le $((FB_ADDR)) ] || { echo "initrd too large for the test layout"; return 1; }
    split -b 1G -d "$X/initrd" "$X/initrd.part"
    rm -f "$X/initrd"
    LOADERS=()
    for part in "$X"/initrd.part*; do
        LOADERS+=(-device "loader,file=/work/${part##*/},addr=$(printf '0x%x' $((INITRD_ADDR + off))),force-raw=on")
        off=$((off + $(stat -c %s "$part")))
    done
    INITRD_END=$((INITRD_ADDR + isize))

    QARGS=(-accel tcg,thread=multi,tb-size=1024 -cpu max,sve=off,sme=off,pauth=off -smp 1 -m 32G
           -device virtio-serial-pci,id=vser -chardev file,id=hvc0,path=/work/console.log
           -device virtconsole,chardev=hvc0,bus=vser.0
           -netdev "user,id=n0,restrict=on,net=10.0.2.0/24,hostfwd=tcp:127.0.0.1:2245-10.0.2.15:22"
           -device virtio-net-pci,netdev=n0,mac=52:54:00:45:00:01
           -virtfs local,path=/work/results,mount_tag=results,security_model=none,id=results)
    MACHINE=virt,gic-version=3
    chroot "$TOOLS" qemu-system-aarch64 -machine "$MACHINE,dumpdtb=/work/virt.dtb" "${QARGS[@]}" \
        -display none > "$X/dumpdtb.log" 2>&1
    hi=$(printf '0x%x' $((FB_ADDR >> 32))) lo=$(printf '0x%08x' $((FB_ADDR & 0xffffffff)))
    { dtc -q -I dtb -O dts "$X/virt.dtb"
      cat <<DTS

/ {
	compatible = "apple,j716c", "apple,t6050", "apple,arm-platform";
	model = "Apple MacBook Pro (16-inch, M5 Max)";
	reserved-memory {
		#address-cells = <2>;
		#size-cells = <2>;
		ranges;
		fbmem: framebuffer@${FB_ADDR#0x} {
			reg = <$hi $lo 0x0 0x2000000>;
			no-map;
		};
	};
	chosen {
		linux,initrd-start = /bits/ 64 <$INITRD_ADDR>;
		linux,initrd-end = /bits/ 64 <$(printf '0x%x' $INITRD_END)>;
		framebuffer@${FB_ADDR#0x} {
			compatible = "simple-framebuffer";
			reg = <$hi $lo 0x0 $(printf '0x%x' $FB_SIZE)>;
			memory-region = <&fbmem>;
			width = <$FB_W>;
			height = <$FB_H>;
			stride = <$FB_STRIDE>;
			format = "$FB_FMT";
			status = "okay";
		};
	};
};
DTS
    } > "$X/virt-fb.dts"
    dtc -q -I dts -O dtb -o "$X/virt-fb.dtb" "$X/virt-fb.dts"
    cp "$X/virt-fb.dts" "$OUT/test/"
    { echo "accel tcg; cpu max (sve, sme, pauth off); machine $MACHINE; 1 vCPU; 32 GiB (the root unpacks into a tmpfs that may use half)"
      echo "root compatible: the M5's (apple,j716c apple,t6050 apple,arm-platform)"
      echo "framebuffer ${FB_W}x${FB_H} $FB_FMT stride $FB_STRIDE at $FB_ADDR (DT simple-framebuffer)"
      echo "network: one VM-only virtio NIC, user mode with restrict=on (no outside access), unmanaged by NetworkManager"
      echo "initrd: ramroot.cpio.zst ($(stat -c %s "$OUT/ramroot.cpio.zst") bytes) + test overlay ($(stat -c %s "$X/test-overlay.cpio") bytes), at $(printf '0x%x' $INITRD_ADDR)-$(printf '0x%x' $INITRD_END) in $((${#LOADERS[@]} / 2)) loader pieces, bounds in /chosen as m1n1 sets them"
      echo "cmdline $CMDLINE"; } > "$OUT/test/qemu-setup.txt"

    log "boot (tcg, 1 vCPU, ${FB_W}x${FB_H} $FB_FMT)"
    t0=$(date +%s.%N)
    chroot "$TOOLS" qemu-system-aarch64 -name ilinux045 -machine "$MACHINE" "${QARGS[@]}" \
        -dtb /work/virt-fb.dtb -kernel /work/Image "${LOADERS[@]}" -append "$CMDLINE" \
        -serial file:/work/serial.log -display none -monitor unix:/work/hmp.sock,server,nowait \
        -no-reboot > "$X/qemu.log" 2>&1 &
    QPID=$!
    hmp() { python3 -I /mnt/ilinux/tools/qemumon.py "$X/hmp.sock" "$@"; }
    fbshot() {  # fbshot NAME [SCALE]: the simple-framebuffer bytes in guest RAM, what the panel shows
        rm -f "$X/fb.raw"
        hmp "pmemsave $FB_ADDR $FB_SIZE \"/work/fb.raw\"" >> "$OUT/test/hmp.log" 2>&1 || true
        for _ in $(seq 40); do [ "$(stat -c %s "$X/fb.raw" 2>/dev/null)" = "$FB_SIZE" ] && break; sleep 0.5; done
        python3 -I "$FB2PNG" "$X/fb.raw" $FB_W $FB_H $FB_STRIDE $FB_FMT "$OUT/test/$1.png" "${2:-2}" ||
            echo "fbshot $1 failed" >&2
    }
    # QEMU has read the pieces once its monitor answers; free their tmpfs copy
    for _ in $(seq 120); do hmp "info status" > /dev/null 2>&1 && break; sleep 1; done
    rm -f "$X"/initrd.part*
    local timeout=${TIMEOUT:-9000} every=300 shot=0 shots_done=0 done_marker=
    SECONDS=0
    while [ "$SECONDS" -lt "$timeout" ] && kill -0 "$QPID" 2>/dev/null; do
        cp "$X/console.log" "$OUT/test/console.log" 2>/dev/null || true
        if [ "$SECONDS" -ge $((shot * every + every)) ]; then   # progress frames, quarter scale
            shot=$((shot + 1)); fbshot "progress-$((shot * every))s" 4
        fi
        # captures the probe asks for, in order
        mapfile -t shots < <(grep -a -o -E '^ILINUX045-SHOT [0-9.]+ [A-Za-z0-9_-]+' "$X/console.log" 2>/dev/null | awk '{print $3}')
        while [ "$shots_done" -lt "${#shots[@]}" ]; do
            fbshot "${shots[$shots_done]}" 2
            shots_done=$((shots_done + 1))
        done
        if grep -a -q '^ILINUX045-DONE' "$X/console.log" 2>/dev/null; then done_marker=1; break; fi
        sleep 0.5
    done
    echo "wall_s $(calc "$(date +%s.%N) - $t0")" > "$OUT/test/wall.txt"
    fbshot final 2
    [ -n "$done_marker" ] && log "probe finished" || log "probe did not finish (timeout ${timeout}s or QEMU exit)"
    gssh() {   # bounded: a hung step must not hold the vm lock
        timeout --kill-after=10 300 chroot "$TOOLS" ssh -i /work/id_ed25519 -p 2245 -o BatchMode=yes \
            -o ConnectTimeout=20 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
            root@127.0.0.1 "$@"
    }
    if [ -z "$done_marker" ]; then   # the probe's own collection did not run: take what we can
        gssh journalctl -b -o short-monotonic --no-pager > "$OUT/test/journal-ssh.txt" 2>&1 || true
        gssh 'systemctl --failed --no-pager; ps -eo pid,user,rss,pcpu,etimes,args --sort=-pcpu | head -40; free -m' \
            > "$OUT/test/state-ssh.txt" 2>&1 || true
    fi
    gssh systemctl poweroff > /dev/null 2>&1 || hmp system_powerdown > /dev/null 2>&1 || true
    for _ in $(seq 90); do kill -0 "$QPID" 2>/dev/null || break; sleep 1; done
    kill "$QPID" 2>/dev/null || true
    wait "$QPID" 2>/dev/null || true
    QPID=
    cp "$X/console.log" "$X/serial.log" "$X/qemu.log" "$X/dumpdtb.log" "$OUT/test/" 2>/dev/null || true
    cp -R "$X/results" "$OUT/test/results" 2>/dev/null || true
    chroot_down "$TOOLS"
    { echo "milestones (seconds since kernel start, from the probe):"
      grep -a -E '^ILINUX045-' "$OUT/test/console.log" | grep -v -E '^ILINUX045-SHOT' | cut -c1-300
    } > "$OUT/test/summary.txt"
    cat "$OUT/test/summary.txt"
    [ -n "$done_marker" ] || { echo "FAIL: the probe did not finish"; return 1; }
    grep -q '^ILINUX045-READY' "$OUT/test/console.log" || { echo "FAIL: Omarchy's session never came up"; return 1; }
    echo "PASS: the probe ran to the end; see out/test/summary.txt"
}
