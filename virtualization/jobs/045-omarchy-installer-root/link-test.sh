# link-test.sh: the USB link's VM test (LINK=1), sourced by boot-test.sh in the job VM. Job 046's way:
# dummy_hcd makes the guest's kernel the host of its own gadget, so the one boot holds the M5 (the root as
# built) and the M1 (test-overlay-link/usr/local/bin/ilinux045-link-test, which the probe runs once the
# desktop has settled). Everything here goes into the test overlay only, never into the image:
#  * dummy_hcd and usbserial (with the generic driver, which the tree leaves out) as modules for the exact
#    Image, built against its read-only tree (KTREE) as job 039 builds its modules;
#  * the Linux usb-pipe (tools/m1n1-client/usb-pipe, the same relay as on the M1, with the --tty backend);
#  * a VM-only SSH key for omarchy and a certificate for web.test, kept on the work disk / made per run;
#  * the M1's tools from the working tree (connect-proxy.py, m5-clock.py, m5-ssh-config) and job 046's
#    test pieces (its HTTPS server, the drop-in that gives sshd a private network namespace, debug logs).

# link_modules DIR: dummy_hcd.ko and usbserial.ko for the Image under test into DIR (cached per Image)
link_modules() {
    local dir=$1 km=$W/linkmods/$IMAGE_SHA m vermagic
    [ -n "$KTREE" ] || { echo "LINK=1 needs KTREE in out/job.env: the tree that built $KERNEL"; return 1; }
    [ "$(sha256sum < "$KTREE/arch/arm64/boot/Image" | cut -d' ' -f1)" = "$IMAGE_SHA" ] ||
        { echo "$KTREE does not hold the Image $IMAGE_SHA"; return 1; }
    if [ ! -f "$km/dummy_hcd.ko" ] || [ ! -f "$km/usbserial.ko" ]; then
        rm -rf "$km"
        mkdir -p "$km/udc" "$km/serial"
        cp "$KTREE/drivers/usb/gadget/udc/dummy_hcd.c" "$km/udc/"
        echo 'obj-m := dummy_hcd.o' > "$km/udc/Kbuild"
        cp "$KTREE"/drivers/usb/serial/{usb-serial.c,generic.c,bus.c} "$km/serial/"
        printf '%s\n' 'ccflags-y := -DCONFIG_USB_SERIAL_GENERIC' 'obj-m := usbserial.o' \
            'usbserial-y := usb-serial.o generic.o bus.o' > "$km/serial/Kbuild"
        # The tree's Module.symvers predates its gadget-stack change; unresolved symbols would show at insmod.
        for m in udc serial; do
            make -C "$KTREE" M="$km/$m" KBUILD_MODPOST_WARN=1 -j"$(nproc)" modules >> "$OUT/test/linkmods-build.log" 2>&1 ||
                { tail -30 "$OUT/test/linkmods-build.log"; return 1; }
        done
        cp "$km/udc/dummy_hcd.ko" "$km/serial/usbserial.ko" "$km/"
        strip --strip-debug "$km/dummy_hcd.ko" "$km/usbserial.ko"
    fi
    for m in dummy_hcd usbserial; do
        vermagic=$(modinfo -F vermagic "$km/$m.ko")
        strings -n 20 "$KERNEL" | grep -qxF "$vermagic" || { echo "$m.ko: vermagic '$vermagic' is not the Image's"; return 1; }
        install -D -m 0644 "$km/$m.ko" "$dir/$m.ko"
    done
    { echo "kernel release $(cat "$KTREE/include/config/kernel.release"), tree $KTREE"
      echo "vermagic $vermagic"
      (cd "$km" && sha256sum dummy_hcd.ko usbserial.ko)
      grep -i 'warning' "$OUT/test/linkmods-build.log" 2> /dev/null | sort -u | head -20 || true; } > "$OUT/test/linkmods.txt"
}

# link_test_overlay O: the link test's files into the test overlay O
link_test_overlay() {
    local o=$1 d=$1/usr/local/lib/ilinux045-link I=/mnt/ilinux S=/mnt/ilinux/tools/m1n1-client/usb-pipe
    local P46=/mnt/ilinux/virtualization/jobs/046-usb-ssh-pipe/test-overlay
    log "link test: modules, usb-pipe, keys, certificate"
    mkdir -p "$d/www"
    link_modules "$d"
    gcc -O2 -Wall -Wextra -pthread -static -o "$d/usb-pipe" "$S/usb-pipe.c" "$S/relay.c" > "$OUT/test/usb-pipe-build.log" 2>&1 ||
        gcc -O2 -Wall -Wextra -pthread -o "$d/usb-pipe" "$S/usb-pipe.c" "$S/relay.c" >> "$OUT/test/usb-pipe-build.log" 2>&1 ||
        { cat "$OUT/test/usb-pipe-build.log"; return 1; }
    "$d/usb-pipe" --version >> "$OUT/test/usb-pipe-build.log" 2>&1
    [ -f "$W/testkey/link_ed25519" ] || ssh-keygen -q -t ed25519 -N '' -C ilinux045-link-vm-test -f "$W/testkey/link_ed25519"
    install -m 0600 "$W/testkey/link_ed25519" "$d/link-key"
    install -m 0644 "$W/testkey/link_ed25519.pub" "$d/link-key.pub"
    # The web server's certificate, made now: valid from this moment, so a clock two days behind refuses it.
    printf '%s\n' '[req]' 'distinguished_name = dn' 'x509_extensions = v3' 'prompt = no' '[dn]' 'CN = ilinux-test-web' \
        '[v3]' 'subjectAltName = DNS:web.test, IP:127.0.0.1' 'basicConstraints = critical, CA:TRUE' > "$OUT/test/cert.cnf"
    openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -keyout "$d/key.pem" \
        -out "$d/cert.pem" -days 30 -config "$OUT/test/cert.cnf" > "$OUT/test/openssl.log" 2>&1
    chmod 0600 "$d/key.pem"; chmod 0644 "$d/cert.pem"
    install -m 0644 "$I/tools/m1n1-client/connect-proxy.py" "$I/tools/m1n1-client/m5-clock.py" \
        "$I/tools/m1n1-client/m5-ssh-config" "$d/"
    install -m 0644 "$P46/usr/local/lib/ilinux-test/https_server.py" "$d/"
    install -m 0644 "$P46/usr/local/lib/ilinux-test/www/hello.txt" "$d/www/"
    install -m 0644 "$OUT/build/authorized-keys-fingerprints.txt" "$d/operator-fingerprints.txt" 2> /dev/null ||
        { echo "no out/build/authorized-keys-fingerprints.txt: was the image built with LINK=1?"; return 1; }
    install -D -m 0644 "$P46/etc/systemd/system/ilinux-sshd-tty@.service.d/test-private-network.conf" \
        "$o/etc/systemd/system/ilinux-sshd-tty@.service.d/test-private-network.conf"
    install -D -m 0644 "$P46/etc/ssh/sshd_config.d/00-ilinux-test-debug.conf" "$o/etc/ssh/sshd_config.d/00-ilinux-test-debug.conf"
    install -D -m 0755 "$J/test-overlay-link/usr/local/bin/ilinux045-link-test" "$o/usr/local/bin/ilinux045-link-test"
    # what this run built and expects; the test checks it against the image's own build-info.txt
    printf 'LINK=%s CLAUDE=%s NOPASSWD=%s\n' "$LINK" "$CLAUDE" "$NOPASSWD" > "$d/expected-options"
    (cd "$d" && sha256sum usb-pipe connect-proxy.py m5-clock.py m5-ssh-config https_server.py dummy_hcd.ko usbserial.ko) > "$OUT/test/link-inputs.txt"
    cat "$OUT/test/linkmods.txt" "$OUT/test/link-inputs.txt"
}
