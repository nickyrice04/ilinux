#!/bin/sh
# Job 004: (a) real pacman resolution of Omarchy's aarch64 default package
# set, Omarchy edge templates vs Arch Linux ARM alone; (b) omarchy-qos
# functional test in a real systemd user session.  Upstream Omarchy scripts
# are executed only here, inside the disposable VM.
OUT=/mnt/job/out
mkdir -p /mnt/omarchy /mnt/qos
mount -t virtiofs omarchy /mnt/omarchy && mount -t virtiofs qos /mnt/qos || exit 1
export OMARCHY_PATH=/mnt/omarchy
( cd /mnt/omarchy && git log -1 --format='%H %ad' 2>/dev/null ) > $OUT/omarchy-commit.txt
# DNS can lag network-online right after boot; wait for both repo hosts.
for i in $(seq 1 30); do
  getent hosts pkgs.omarchy.org >/dev/null && getent hosts arm-mirror.omarchy.org >/dev/null && break
  sleep 2
done
PKGS=$(bash /mnt/omarchy/bin/omarchy-pkg-defaults aarch64)
echo "$PKGS" > $OUT/aarch64-default-packages.txt
echo "default set: $(echo "$PKGS" | wc -l) names"
EXTRA="linux-aarch64 limine snapper btrfs-progs efibootmgr omarchy omarchy-settings vulkan-swrast"

resolve() {  # label conf mirrorlist
  # Print-only resolution in a throwaway DB: nothing is installed, so
  # signature checks are disabled here (the [omarchy] DB is signed with a key
  # the ALARM keyring does not have).
  db=/tmp/resolve-$1; rm -rf $db; mkdir -p $db
  sed -e 's/^SigLevel.*/SigLevel = Never/' -e '/^DownloadUser/d' "$2" > /tmp/pacman-$1.conf
  sed -i "s#Include = /etc/pacman.d/mirrorlist#Include = /tmp/mirrorlist-$1#" /tmp/pacman-$1.conf
  cp "$3" /tmp/mirrorlist-$1
  pacman --config /tmp/pacman-$1.conf --dbpath $db -Sy > $OUT/sync-$1.log 2>&1 ||
    { sleep 5; pacman --config /tmp/pacman-$1.conf --dbpath $db -Sy >> $OUT/sync-$1.log 2>&1; } ||
    { echo "$1: sync failed"; tail -3 $OUT/sync-$1.log; return; }
  pacman --config /tmp/pacman-$1.conf --dbpath $db -Sp --print-format '%r/%n %v' $PKGS $EXTRA > $OUT/plan-$1.txt 2> $OUT/plan-$1.err
  rc=$?
  echo "$1: exit=$rc packages=$(wc -l < $OUT/plan-$1.txt) unresolved=$(grep -c 'target not found' $OUT/plan-$1.err)"
  cut -d/ -f1 $OUT/plan-$1.txt | sort | uniq -c > $OUT/plan-$1-by-repo.txt
}
[ -f /root/pacman.conf.alarm ] || { cp /etc/pacman.conf /root/pacman.conf.alarm; cp /etc/pacman.d/mirrorlist /root/mirrorlist.alarm; }
cp /root/pacman.conf.alarm /etc/pacman.conf; cp /root/mirrorlist.alarm /etc/pacman.d/mirrorlist
resolve omarchy-edge /mnt/omarchy/default/pacman/aarch64/pacman-edge.conf /mnt/omarchy/default/pacman/aarch64/mirrorlist-edge
resolve alarm-only /root/pacman.conf.alarm /root/mirrorlist.alarm
grep 'target not found' $OUT/plan-alarm-only.err | sed 's/.*: //' | sort > $OUT/unresolved-alarm-only.txt
# closure size of the resolvable subset against ALARM alone
OK=$(echo "$PKGS $EXTRA" | tr ' ' '\n' | grep -vxF -f $OUT/unresolved-alarm-only.txt)
pacman --config /tmp/pacman-alarm-only.conf --dbpath /tmp/resolve-alarm-only -Sp --print-format '%r/%n %v' $OK > $OUT/plan-alarm-only-subset.txt 2>> $OUT/plan-alarm-only.err
echo "alarm-only resolvable subset closure: $(wc -l < $OUT/plan-alarm-only-subset.txt)"

# (b) omarchy-qos mechanics
sh /mnt/qos/install.sh / > $OUT/qos-install.log 2>&1
systemctl daemon-reload
id tester >/dev/null 2>&1 || useradd -m tester
loginctl enable-linger tester
sleep 3
U=$(id -u tester)
runuser -u tester -- env XDG_RUNTIME_DIR=/run/user/$U DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$U/bus \
  sh -c 'systemctl --user daemon-reload; /mnt/qos/tests/test-qos.sh' > $OUT/qos-test.log 2>&1
echo "qos test exit=$?"
cat /sys/fs/cgroup/user.slice/user-$U.slice/user@$U.service/cgroup.subtree_control > $OUT/qos-user-controllers.txt 2>&1
