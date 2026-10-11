#!/bin/sh
# Customize an extracted Arch Linux ARM rootfs for use as a disposable vzrun
# test VM.  Runs inside the image-build container against $1 (the rootfs).
#
# Adds a "job runner": at boot the guest mounts the virtiofs tag "job" (a
# workspace directory shared by vzrun), runs job/run.sh as root, writes
# job/out/run.log, and powers off.  This gives fully scripted, non-interactive
# test runs without SSH or stored credentials.
set -eu
R="$1"

echo "alarm-vz" > "$R/etc/hostname"
cat > "$R/etc/fstab" <<'EOF'
/dev/vda  /  ext4  rw,relatime  0 1
EOF

# HTTPS mirror (same one Omarchy's aarch64 templates use); packages stay
# signature-checked by pacman.
cat > "$R/etc/pacman.d/mirrorlist" <<'EOF'
Server = https://arm-mirror.omarchy.org/$arch/$repo
EOF

install -d "$R/usr/local/sbin"
cat > "$R/usr/local/sbin/vzjob" <<'EOF'
#!/bin/sh
# Run the host-provided job (virtiofs tag "job"), then power off.
mkdir -p /mnt/job
modprobe virtiofs 2>/dev/null || true
if mount -t virtiofs job /mnt/job 2>/dev/null && [ -x /mnt/job/run.sh ]; then
  mkdir -p /mnt/job/out
  start=$(date -u +%FT%TZ)
  ( cd /mnt/job && ./run.sh ) > /mnt/job/out/run.log 2>&1
  rc=$?
  echo "vzjob: start=$start end=$(date -u +%FT%TZ) exit=$rc" >> /mnt/job/out/run.log
  sync
  if [ ! -e /mnt/job/no-poweroff ]; then systemctl poweroff; fi
fi
EOF
chmod 755 "$R/usr/local/sbin/vzjob"

cat > "$R/etc/systemd/system/vzjob.service" <<'EOF'
[Unit]
Description=Run host-provided job from virtiofs tag "job"
Wants=network-online.target
After=network-online.target local-fs.target systemd-modules-load.service

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/vzjob
TimeoutStartSec=infinity
StandardOutput=journal+console
StandardError=journal+console

[Install]
WantedBy=multi-user.target
EOF
ln -sf /etc/systemd/system/vzjob.service "$R/etc/systemd/system/multi-user.target.wants/vzjob.service"

# Interactive debugging only: root autologin on the virtio console (hvc0).
# The VM is NAT-only with no listening services we enable; sshd is masked.
install -d "$R/etc/systemd/system/serial-getty@hvc0.service.d"
cat > "$R/etc/systemd/system/serial-getty@hvc0.service.d/autologin.conf" <<'EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty -o '-p -f -- \\u' --noclear --autologin root --keep-baud 115200,57600,38400,9600 %I $TERM
EOF
ln -sf /dev/null "$R/etc/systemd/system/sshd.service"
rm -f "$R/etc/systemd/system/multi-user.target.wants/sshd.service"

# Wait for network only on the virtio NIC.
install -d "$R/etc/systemd/system/systemd-networkd-wait-online.service.d"
cat > "$R/etc/systemd/system/systemd-networkd-wait-online.service.d/any.conf" <<'EOF'
[Service]
ExecStart=
ExecStart=/usr/lib/systemd/systemd-networkd-wait-online --any --timeout=60
EOF
echo "customized $R"
