#!/bin/bash
# Original iLinux read-only helper. Source in the lab's Recovery Terminal.
# Defines checks only: no policy writes, mounts, boot installation or restart.
# Identifiers and raw policy text stay in shell memory; never enable xtrace.

ilinux_field() (
    set -o pipefail
    diskutil info -plist "$1" 2>/dev/null |
        plutil -extract "$2" raw -o - - 2>/dev/null
)

ilinux_mode() {
    awk '/^Security Mode:/ {print $3}'
}

ilinux_check_policies() {
    local expected="$1" original_policy lab_policy original_mode lab_mode
    case "$expected" in Full|Permissive) ;; *) return 1 ;; esac
    test -n "$ILINUX_ORIGINAL_VG" && test -n "$ILINUX_VG" || return 1
    test "$ILINUX_ORIGINAL_VG" != "$ILINUX_VG" || return 1
    original_policy=$(bputil --display-policy --vuid "$ILINUX_ORIGINAL_VG" 2>/dev/null) || return 1
    lab_policy=$(bputil --display-policy --vuid "$ILINUX_VG" 2>/dev/null) || return 1
    original_mode=$(printf '%s\n' "$original_policy" | ilinux_mode)
    lab_mode=$(printf '%s\n' "$lab_policy" | ilinux_mode)
    test "$original_mode" = Full && test "$lab_mode" = "$expected" || return 1
    case "$lab_policy" in *': Paired'*) ;; *) return 1 ;; esac
    case "$lab_policy" in *'one true recoveryOS'*) ;; *) return 1 ;; esac
    printf 'Policies verified: original Full; lab %s; lab paired 1TR.\n' "$expected"
}

ilinux_payload_ok() {
    local parent
    for parent in "$ILINUX_DATA" "$ILINUX_DATA/Users" "$ILINUX_DATA/Users/Shared" "$ILINUX_DATA/Users/Shared/iLinuxBoot" "$ILINUX_BOOT"; do
        test ! -L "$parent" || return 1
    done
    test -f "$ILINUX_BOOT" || return 1
    test "$(stat -f %z "$ILINUX_BOOT")" = 3932160 || return 1
    test "$(shasum -a 256 "$ILINUX_BOOT" | awk '{print $1}')" = "$ILINUX_HASH" || return 1
}

ilinux_preflight() {
    ILINUX_READY=no
    ILINUX_POLICY_OK=no
    ILINUX_INSTALLED=no
    ILINUX_VG=
    ILINUX_ORIGINAL_VG=
    ILINUX_OS='/Volumes/iLinux Boot Lab'
    ILINUX_DATA='/Volumes/iLinux Boot Lab - Data'
    ILINUX_ORIGINAL='/Volumes/Macintosh HD'
    ILINUX_BOOT="$ILINUX_DATA/Users/Shared/iLinuxBoot/m1n1.bin"
    ILINUX_HASH=ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664
    local volume data_group

    test "$(ilinux_field "$ILINUX_OS" VolumeName)" = 'iLinux Boot Lab' || return 1
    test "$(ilinux_field "$ILINUX_DATA" VolumeName)" = 'iLinux Boot Lab - Data' || return 1
    test "$(ilinux_field "$ILINUX_ORIGINAL" VolumeName)" = 'Macintosh HD' || return 1
    for volume in "$ILINUX_OS" "$ILINUX_DATA" "$ILINUX_ORIGINAL"; do
        test "$(ilinux_field "$volume" MountPoint)" = "$volume" || return 1
        test "$(ilinux_field "$volume" Internal)" = true || return 1
        test "$(ilinux_field "$volume" FilesystemType)" = apfs || return 1
    done
    ILINUX_VG=$(ilinux_field "$ILINUX_OS" APFSVolumeGroupID) || return 1
    data_group=$(ilinux_field "$ILINUX_DATA" APFSVolumeGroupID) || return 1
    ILINUX_ORIGINAL_VG=$(ilinux_field "$ILINUX_ORIGINAL" APFSVolumeGroupID) || return 1
    test -n "$ILINUX_VG" && test -n "$ILINUX_ORIGINAL_VG" || return 1
    test "$ILINUX_VG" = "$data_group" || return 1
    test "$ILINUX_VG" != "$ILINUX_ORIGINAL_VG" || return 1
    test "$(ilinux_field "$ILINUX_DATA" FileVault)" = false || return 1
    test "$(plutil -extract ProductBuildVersion raw -o - "$ILINUX_OS/System/Library/CoreServices/SystemVersion.plist")" = 25G83 || return 1
    ilinux_payload_ok || return 1
    ilinux_check_policies Full || return 1
    ILINUX_READY=yes
    echo 'Preflight passed: separate lab group, expected build/payload, paired 1TR, both Full.'
}
