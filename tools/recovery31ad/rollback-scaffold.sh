# SPDX-License-Identifier: MIT
# OFFLINE REVIEW SCAFFOLD ONLY. NOT A NATIVE-RUN INSTRUCTION.
# Deliberately refuses execution. Root must separately qualify/authorize and
# publish a new exact self-contained block before this gate is ever replaced.
/bin/bash <<'ILINUX31AD_ROLLBACK_END'
set -u
umask 077
PATH=/usr/bin:/bin:/usr/sbin:/sbin
export PATH
readonly ILINUX31AD_WRITE_QUALIFIED=no
if test "$ILINUX31AD_WRITE_QUALIFIED" != yes; then
    printf '%s\n' 'STOP: offline scaffold only; no Recovery write is qualified or authorized.'
    exit 78
fi
hash_file() {
    if test -x /sbin/sha256; then /sbin/sha256 -q "$1"
    else /usr/bin/shasum -a 256 "$1" | /usr/bin/awk '{print $1}'; fi
}
base_guard() {
    ILINUX_OS='/Volumes/iLinux Boot Lab'
    ILINUX_DATA='/Volumes/iLinux Boot Lab - Data'
    ILINUX_ORIGINAL='/Volumes/Macintosh HD'
    ILINUX_BOOT="$ILINUX_DATA/Users/Shared/iLinuxBoot/m1n1.bin"
    local helper p data_group
    helper="$ILINUX_DATA/Users/Shared/iLinuxBoot/recovery-preflight.sh"
    for p in "$ILINUX_OS" "$ILINUX_DATA" "$ILINUX_ORIGINAL" \
        "$ILINUX_DATA/Users" "$ILINUX_DATA/Users/Shared" \
        "$ILINUX_DATA/Users/Shared/iLinuxBoot" "$ILINUX_BOOT" "$helper"; do
        test ! -L "$p" || return 1
    done
    test -f "$helper" || return 1
    test "$(hash_file "$helper")" = \
        e65636d03cfb7a7000f86810fdc8888e209b99bedaa1b36ca7a125de4bf72188 || return 1
    . "$helper" || return 1
    test "$(ilinux_field "$ILINUX_OS" VolumeName)" = 'iLinux Boot Lab' || return 1
    test "$(ilinux_field "$ILINUX_DATA" VolumeName)" = 'iLinux Boot Lab - Data' || return 1
    test "$(ilinux_field "$ILINUX_ORIGINAL" VolumeName)" = 'Macintosh HD' || return 1
    for p in "$ILINUX_OS" "$ILINUX_DATA" "$ILINUX_ORIGINAL"; do
        test "$(ilinux_field "$p" MountPoint)" = "$p" || return 1
        test "$(ilinux_field "$p" Internal)" = true || return 1
        test "$(ilinux_field "$p" FilesystemType)" = apfs || return 1
    done
    ILINUX_VG=$(ilinux_field "$ILINUX_OS" APFSVolumeGroupID) || return 1
    data_group=$(ilinux_field "$ILINUX_DATA" APFSVolumeGroupID) || return 1
    ILINUX_ORIGINAL_VG=$(ilinux_field "$ILINUX_ORIGINAL" APFSVolumeGroupID) || return 1
    test -n "$ILINUX_VG" && test -n "$ILINUX_ORIGINAL_VG" || return 1
    test "$ILINUX_VG" = "$data_group" || return 1
    test "$ILINUX_VG" != "$ILINUX_ORIGINAL_VG" || return 1
    test "$(ilinux_field "$ILINUX_DATA" FileVault)" = false || return 1
    test "$(/usr/bin/plutil -extract ProductBuildVersion raw -o - \
        "$ILINUX_OS/System/Library/CoreServices/SystemVersion.plist")" = 25G83 || return 1
    test -f "$ILINUX_BOOT" || return 1
    test "$(/usr/bin/stat -f %z "$ILINUX_BOOT")" = 3932160 || return 1
    test "$(hash_file "$ILINUX_BOOT")" = \
        ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664 || return 1
    ilinux_check_policies Permissive || return 1
}
main() {
    base_guard || { printf '%s\n' 'STOP: guard failed; no write.'; return 1; }
    local evidence rc tee_rc actual
    local -a statuses
    evidence=$(/usr/bin/mktemp -d /tmp/ilinux31ad-rollback.XXXXXX) || return 1
    readonly ILINUX_BOOT ILINUX_OS
    # Pin the same pathname used by configure, immediately before invocation.
    actual=$(hash_file "$ILINUX_BOOT") || return 1
    test "$actual" = \
        ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664 || return 1
    printf '%s\n' "$actual" >"$evidence/input.sha256" || return 1
    printf '%s\n' '/usr/bin/kmutil' 'configure-boot' '--custom-boot-object' \
        "$ILINUX_BOOT" '--raw' '--entry-point' '2048' \
        '--lowest-virtual-address' '0' '--volume' "$ILINUX_OS" >"$evidence/argv.txt" || return 1
    # Explicit tty input prevents Apple's confirmation from consuming heredoc code.
    # tee keeps prompts visible; PIPESTATUS preserves configure's own exit code.
    /usr/bin/kmutil configure-boot --custom-boot-object "$ILINUX_BOOT" \
        --raw --entry-point 2048 --lowest-virtual-address 0 --volume "$ILINUX_OS" \
        </dev/tty 2>&1 | /usr/bin/tee "$evidence/configure.log"
    statuses=("${PIPESTATUS[@]}")
    rc=${statuses[0]}
    tee_rc=${statuses[1]}
    printf '%s\n' "$rc" >"$evidence/configure.exit"
    printf '%s\n' "$tee_rc" >"$evidence/capture.exit"
    printf 'Rollback configure exit: %s; private evidence: %s\n' "$rc" "$evidence"
    test "$rc" = 0 || { printf '%s\n' 'STOP: no retry or reboot.'; return "$rc"; }
    test "$tee_rc" = 0 || { printf '%s\n' 'STOP: output capture failed; no retry or reboot.'; return 1; }
    ilinux_check_policies Permissive >"$evidence/postcheck.txt" 2>&1
    rc=$?
    printf '%s\n' "$rc" >"$evidence/postcheck.exit"
    test "$rc" = 0 || {
        printf '%s\n' 'STOP: postcheck failed; no reboot.'; return 1; }
    printf '%s\n' 'Exact rollback and Full/Permissive postcheck passed. Return/default restoration is human-run.'
}
main
ILINUX31AD_RC=$?
exit "$ILINUX31AD_RC"
ILINUX31AD_ROLLBACK_END
