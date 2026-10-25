# 31AC: M1 review and one human-run visible-entry attempt

**PREPARATION ONLY until the published package is independently reviewed and
the user explicitly approves the lab boot-object replacement, one diagnostic
boot, boot021 rollback and temporary Startup Disk changes.** Do not run the
Recovery write commands merely because this document exists. The agents prepare
and review; the human operates the M5. These are never M1 boot-policy commands.

The experiment is an original resident-entry diagnostic. It does not start Linux
or a secondary CPU, contact USB proxy mode, or call SPTM services. Read
[the launch rationale](../../research/native31ac-launch.md) and the final
`native/boot/attempt31ac/manifest.json` before the following sequence.

## 1. Freeze and review the package

Preserve local changes; pull with `git pull --ff-only` and record the exact
reviewed commit. Check the manifest's source bindings, original-image
hash/size, build and emulator outcomes, and rollback hash. Reuse the unchanged
31AB review. Do not install tools, repeat old suites or reinterpret emulation as
native acceptance. The tested candidate has 26 complete-payload QEMU cases,
host compilation and read-only Mach-O property derivation recorded separately.
M1 must review the exact source-bound receipts; tool limitations remain explicit.
These are not a native acceptance result.

Fetch the original-only archive from the
[31AC release](https://github.com/nickyrice04/ilinux/releases/download/native-j716c-31ac/ilinux-31ac-entry-test.tar.gz)
into a fresh ignored M1 intake directory. If the release is not yet available,
wait for publication; do not substitute a development image. Compare the archive
size and SHA-256 to the independently pulled manifest before extraction. Inspect
the member list: reject absolute paths, `..` components, links or unexpected
content. Extract only the reviewed original files into that fresh workspace
directory, then verify every manifest-listed file. Keep the archive and receipt.
This is data handling, not execution of a downloaded setup script.

Required review inputs include:

| File | Purpose | Required binding |
|---|---|---|
| `ilinux-31ac.macho` | Original diagnostic | 180,224 bytes; SHA-256 `261d44447442f32ba6c41bbf0f69179e8c9eb4c33507b60762f0ea8c2e54ab72` |
| `m1n1-boot021.bin` | Spare exact rollback file | 3,932,160 bytes; SHA-256 below |
| `native/boot/attempt31ac/manifest.json` | Public repository source/artifact receipt | Exact reviewed revision; archive binding comes from this separately pulled file |

The existing staged rollback file remains
`/Volumes/iLinux Boot Lab - Data/Users/Shared/iLinuxBoot/m1n1.bin`.
Its SHA-256 is
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
Do not overwrite it. Its source is m1n1
`57a9339ffd1876e78297b17d34dece8cff8fa1ba`, marker
`##m1n1_ver##ilinux-57a9339-boot021`.

Using existing M1 tools, run the new packaging tests and compile-only check from
the repository root, with a fresh output directory:

```sh
python3 -I -m unittest discover -s kernel/experiments/bootimage31ac -p 'test_image.py'
python3 -I kernel/experiments/visible31ac/run.py \
    --output build/31ac-visible-m1-review --cc clang \
    --target aarch64-none-elf --compile-only
```

Expect eight packaging methods and five original AArch64 object compilations;
compare source bindings with the released receipt. On an M1 without an existing
ELF linker/QEMU, record link/audit and all 26 runtime cases as NOT RUN on M1 and
review their separate M5 VM evidence. Do not install tools to fill that gap or
pretend the Mach-O parser check is a boot. Report the exact commit, hashes,
commands, tool versions, actual outcomes and actionable review findings.

Complete the independent M1 package/source review and publish its sanitized
result before asking for the concrete human approval. That approval
must acknowledge that `configure-boot` changes the **lab's** custom-object
policy/hash. The existing original-Full/lab-Permissive security levels are to be
preserved. No new downgrade, CTRR change, SIP change, APFS layout operation,
OS installation, firmware update or DFU action belongs to this attempt.

## 2. Enter the lab's paired Recovery

Save work and connect AC power. Keep the M1 available for instructions and a
clock. In the M5's original macOS, select **iLinux Boot Lab as Startup Disk**
using Apple's confirmed default-change flow. Its documented flow includes
Restart: if needed to apply the selection, allow the already installed boot021
screen to appear, make no proxy connection, and hold power to shut down. Merely
highlighting an icon is not recorded as a confirmed default change.
Then hold power continuously from shutdown until startup options appear; choose
**Options → Continue**. Default selection is intentional: Apple associates the
held-power Recovery with the default OS.
Do not select Macintosh HD as default until after rollback; selecting it once
to return to the desktop is a separate action. This possible preparatory boot021
start must be included in the human approval; it is not a new SMP attempt.
[Apple's Startup Disk flow](https://support.apple.com/en-qa/guide/mac-help/mchlp1034/mac).

Open Terminal in Recovery. Do not enable shell tracing or publish raw policy,
disk-list or identifier output. If the expected existing lab volumes are not
mounted, mount those existing volumes using Disk Utility; do not create, erase,
resize or unlock unrelated volumes. If target identity or pairing cannot be
established, stop before any write.

The following is a new read-only guard. The frozen helper it sources defines
functions only; **do not invoke its old `ilinux_preflight`**, which expects the
pre-install Full/Full state.

```sh
ilinux31ac_sha256() {
    if test -x /sbin/sha256; then
        /sbin/sha256 -q "$1"
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        return 1
    fi
}

ilinux31ac_base() {
    ILINUX31AC_READY=no
    ILINUX_OS='/Volumes/iLinux Boot Lab'
    ILINUX_DATA='/Volumes/iLinux Boot Lab - Data'
    ILINUX_ORIGINAL='/Volumes/Macintosh HD'
    ILINUX_BOOT="$ILINUX_DATA/Users/Shared/iLinuxBoot/m1n1.bin"
    ILINUX_HASH=ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664
    local helper p data_group
    helper="$ILINUX_DATA/Users/Shared/iLinuxBoot/recovery-preflight.sh"
    for p in "$ILINUX_OS" "$ILINUX_DATA" "$ILINUX_ORIGINAL" \
        "$ILINUX_DATA/Users" "$ILINUX_DATA/Users/Shared" \
        "$ILINUX_DATA/Users/Shared/iLinuxBoot" "$ILINUX_BOOT" "$helper"; do
        test ! -L "$p" || return 1
    done
    test -f "$helper" || return 1
    test "$(ilinux31ac_sha256 "$helper")" = \
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
    test "$(plutil -extract ProductBuildVersion raw -o - \
        "$ILINUX_OS/System/Library/CoreServices/SystemVersion.plist")" = 25G83 || return 1
    test -f "$ILINUX_BOOT" || return 1
    test "$(stat -f %z "$ILINUX_BOOT")" = 3932160 || return 1
    test "$(ilinux31ac_sha256 "$ILINUX_BOOT")" = "$ILINUX_HASH" || return 1
    ilinux_check_policies Permissive || return 1
    ILINUX31AC_READY=yes
    printf '%s\n' '31AC base PASS: separate lab, build, rollback, Full/Permissive, paired 1TR.'
}

ilinux31ac_base
```

Continue only on the explicit PASS, with exit zero. Identifiers stay in shell
memory. If the helper is missing or changed, stop and review it; do not fetch and
execute a replacement. Do not infer pairing from the volume's name alone.

## 3. Transfer and bind the original diagnostic

Prefer an already available, reviewed package transfer. One concrete option is
an M1 local-network server serving **only** the verified extracted package
directory, never the repository or private research tree. Set
`ILINUX31AC_SERVE` to that directory, containing the verified candidate directly.
In an M1 terminal, after setting
`ILINUX31AC_M1` to that machine's actual local address:

```sh
python3 -I -m http.server 8031 --bind "$ILINUX31AC_M1" \
    --directory "$ILINUX31AC_SERVE"
```

Keep it in the foreground and stop it with Control-C after transfer. On the M5
Recovery terminal, set the same local address and download **data, not a shell
script**, into a fresh temporary directory. No proprietary content travels back.

```sh
ILINUX31AC_TMP=$(mktemp -d /tmp/ilinux31ac.XXXXXX)
test -n "$ILINUX31AC_TMP" && test -d "$ILINUX31AC_TMP" && \
    curl --fail --max-time 60 --output "$ILINUX31AC_TMP/ilinux-31ac.macho" \
    "http://${ILINUX31AC_M1}:8031/ilinux-31ac.macho"
ILINUX31AC_IMAGE="$ILINUX31AC_TMP/ilinux-31ac.macho"

# Exact tested candidate; compare these again to the independently reviewed manifest.
ILINUX31AC_BYTES=180224
ILINUX31AC_SHA256=261d44447442f32ba6c41bbf0f69179e8c9eb4c33507b60762f0ea8c2e54ab72

ilinux31ac_candidate() {
    ilinux31ac_base || return 1
    test "$ILINUX31AC_BYTES" -gt 0 || return 1
    test "${#ILINUX31AC_SHA256}" = 64 || return 1
    test ! -L "$ILINUX31AC_IMAGE" && test -f "$ILINUX31AC_IMAGE" || return 1
    test "$(stat -f %z "$ILINUX31AC_IMAGE")" = "$ILINUX31AC_BYTES" || return 1
    test "$(ilinux31ac_sha256 "$ILINUX31AC_IMAGE")" = "$ILINUX31AC_SHA256" || return 1
    printf '%s\n' '31AC candidate PASS: exact reviewed original image.'
}
ilinux31ac_candidate
```

A fresh download is not a new trust source: compare against the independently
reviewed hash, not a hash
received from the same network transfer alone. Do not put the candidate at the
staged boot021 path. Recovery temporary files may disappear on restart; rollback
uses the pre-existing verified lab file and does not depend on this download.

## 4. Authorized lab-object replacement only

After the final approval and both PASS results, run this block **once** on M5
Recovery. Enter credentials only into Apple's own prompt.

```sh
ILINUX31AC_INSTALLED=no
if ilinux31ac_candidate; then
    kmutil configure-boot --custom-boot-object "$ILINUX31AC_IMAGE" \
        --volume "$ILINUX_OS"
    ILINUX31AC_INSTALL_RC=$?
    printf '31AC configure exit: %s\n' "$ILINUX31AC_INSTALL_RC"
    if test "$ILINUX31AC_INSTALL_RC" = 0 && ilinux_check_policies Permissive; then
        ILINUX31AC_INSTALLED=yes
        printf '%s\n' '31AC installed; native execution still unobserved.'
    else
        printf '%s\n' 'STOP: no diagnostic boot; review error and use the verified rollback.'
    fi
else
    printf '%s\n' 'STOP: no write attempted; prerequisite failed.'
fi
```

No `--raw`, entry-point override, compression switch or security command belongs
to this installation. If rejected, preserve the sanitized error and exit code;
do not retry with altered options. A failure is not assumed atomic. If identity
and policy checks still pass, use section 6 to restore the known object. If those
checks fail, stop rather than guessing a new target or changing security.

## 5. One bounded physical observation

Only after `ILINUX31AC_INSTALLED=yes`, shut down. Hold power until startup options
and select the lab entry once. Observe the built-in screen for **30 seconds**
from selection. The current marker is a small **32 by 16 pixel bordered
checkerboard at the top-left**; its foreground is pink for the accepted 32-bit
format, with a separately encoded 30-bit variant. Record the actual appearance,
not an assumed color. A close view may be needed on the high-resolution panel.

Record whether the expected pattern appeared, remained stable, or never appeared;
also record a displayed firmware error separately. No M1 `--connect`, proxy
request or RAM launcher is part of this attempt. The diagnostic parks rather
than automatically restarting. End the attempt after observation by holding
power to shut down. There is no unchanged second boot.

An absent marker leaves the cause unknown: firmware rejection, entry not reached,
an explicit profile/input refusal, a later fault, or display visibility can all
produce it. This does not prove an Apple-only obstacle. A marker proves this
original entry/display path, not Linux, monitor-service readiness or SMP.

## 6. Restore exact boot021 and return to original macOS

With the lab still the default, hold power continuously from shutdown and select
Options to return to its paired Recovery. Re-enter section 2's function
definitions in the new Terminal; no old shell variable or PASS survives a boot.
Run `ilinux31ac_base` again. The rollback does not need the candidate image.

```sh
ILINUX31AC_RESTORED=no
if ilinux31ac_base; then
    kmutil configure-boot --custom-boot-object "$ILINUX_BOOT" \
        --raw --entry-point 2048 --lowest-virtual-address 0 --volume "$ILINUX_OS"
    ILINUX31AC_RESTORE_RC=$?
    printf 'boot021 restore exit: %s\n' "$ILINUX31AC_RESTORE_RC"
    if test "$ILINUX31AC_RESTORE_RC" = 0 && ilinux_check_policies Permissive; then
        ILINUX31AC_RESTORED=yes
        printf '%s\n' 'Exact boot021 reinstall succeeded; original Full and lab Permissive.'
    else
        printf '%s\n' 'STOP: rollback incomplete; no automatic retry or security change.'
    fi
else
    printf '%s\n' 'STOP: no rollback write attempted; prerequisite failed.'
fi
```

After successful rollback, shut down, hold power for startup options and select
**Macintosh HD → Continue**. At the usual desktop, apply **Macintosh HD as the
default Startup Disk**, including its ordinary restart if requested by the UI,
then verify the expected OS/build and protection state
using the existing read-only return workflow. Do not silently leave the lab as
default. If original macOS or paired Recovery is unavailable, stop; this plan
does not authorize erase, policy resets, DFU, revive or restore operations.

A boot021 reinstallation receipt is not a new execution/version observation.
If a separate boot021 visual check is desired, include it in the concrete
approval first; no USB handshake is necessary for rollback completion.

## 7. Sanitized result

Record the reviewed commit and exact candidate hash, preflight PASS/failure,
configure exit, human-observed screen outcome and elapsed window, rollback
exit/checks, return to Macintosh HD, and final default selection. Publish no
identifiers, raw policy/disk output or unredacted Recovery photographs. Keep
`native_entry_observed` separate from installation success and leave physical
secondary startup, Linux, GPU and performance NOT RUN. On a silent attempt,
review the new evidence before proposing any changed experiment.
