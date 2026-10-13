# M5 dedicated boot entry: reviewed procedure, NOT execution approval

Prepared by B on 2026-10-13 for **Mac17,6 / J716c / t6050 M5 Max**.
The user requested exact steps while the M1 verifies boot021, explicitly
prohibiting boot-setting changes. **Every installation/reboot/policy step below
is pending separate approval. None has been executed.**

**Verification update:** the matching 26.6.2 / 25G83 installer is downloaded.
Its original package passes Apple's signature and Gatekeeper install assessment;
all signed entries and installed app contents match. The outer app's custom-
resource-rule rejection remains unchanged, with no exception or bypass. See the
[verification record](../../native/boot/macos-installer-download.md). M1's
offline receipt is published and reviewed. All volume, installer-launch,
OS-installation, policy and reboot steps below remain on hold.

## Chosen route and observed prerequisites

Use a second, full macOS installation named **iLinux Boot Lab** as the initial
boot scaffold. Later replace only its boot object with the packaged m1n1.
This is an engineering proposal for this M5, not a validated M5 installer.
Apple supports an additional macOS installation on another APFS volume;
the [M5 support table](https://asahilinux.org/docs/platform/feature-support/m5/)
does not provide a supported Asahi installation route for this machine.

Read-only inspection on 2026-10-13 found:

| Item | Observation |
|---|---|
| Current OS | macOS 26.6.2, build 25G83 |
| Main APFS container | 1,995,165,736,960 bytes total; 1,016,906,117,120 bytes free |
| Original installation | System `Macintosh HD`, Data `Data`; FileVault enabled |
| Other boot environment | No dedicated Linux/m1n1 entry |
| Power | AC, battery 100% |
| Installer now present | `/Applications/Install macOS Tahoe.app`; download record above |
| Apple installer catalog | **26.6.2 / 25G83**, 17,953,734 KiB (about 18.4 GB) available |
| Backup | User reports completion; verify its latest dated backup before proceeding |
| Controller | M1 report `dfdf8cf`: archive/13 files verified, 26 tests pass; live checks NOT RUN |

The proposed volume shares the existing APFS container's free space. No
container shrink, new GPT partition, ESP or Linux root filesystem is needed
for this initial RAM diagnostic. Allow roughly **100 GB of working headroom**
for installation; that is a planning allowance, not a measured final footprint
or a reservation. Leave APFS reserve/quota fields blank for this scaffold.
Space sharing is convenient for this experiment; a future installed Linux
system needs a separate reviewed storage plan.

The operation still writes shared APFS/Preboot/Recovery metadata and boot
policy. Apple's installer may service firmware/recovery even when targeting
a second volume. Choosing the same OS build avoids a deliberate upgrade,
but is **not a guarantee of zero firmware changes**. Approval must cover
those installer effects; otherwise stop at preparation.

## 1. Finish readiness checks, then obtain installation approval

Before any host changes:

1. M1 has reported the package receipt, matching client pin and offline tests from
   [native/boot/README.md](../../native/boot/README.md). Successful verification
   does not authorize `--connect` or `--launch`. Recheck if artifacts change.
2. Confirm the external backup's latest completed date and that it can be
   opened. Eject/disconnect it before installation so it is not a destination.
3. Keep both Macs powered and the M1 instructions available independently.
   Save/quit M5 work and stop development VMs before the approved reboot.
4. The human must know the original Mac's administrator/FileVault password.
   Enter credentials only in Apple prompts, never in commands, chat or logs.
   Record the original entry's security mode before installation using a
   read-only policy view; retain only the mode/encryption/SIP outcomes, not
   the full policy or identifiers. Stop if the current mode is unclear.
5. The installer download/verification are complete. Obtain separate approval
   for the new lab installation, temporary startup-disk selection and subsequent
   **lab-only** boot policy.
   Stage A (m1n1/USB) and Stage B (Linux) remain separately identified actions.

## 2. Fetch the matching Apple installer — only after approval

**Completed under download-only authorization. Do not repeat the download.**
The subsequent read-only investigation verified package authenticity and app
contents without disabling security checks; see the verification record.
Installer launch remains untested and requires separate approval. The commands
below retain the acquisition recipe for reproducibility.

In the original M5 macOS, recheck the catalog and require the same version
**and build** before downloading:

```sh
softwareupdate --list-full-installers
softwareupdate --fetch-full-installer --full-installer-version 26.6.2
```

The second command downloads the installer into `/Applications`. Require
successful completion. Review the
downloaded installer metadata before starting it; do not infer the OS build
from the application bundle's own version. If the requested build is no
longer available or the installer proposes a different OS release, stop and
review it rather than substituting the newest installer.

Source: [Apple's installer download procedure](https://support.apple.com/en-us/102662).

## 3. Create and install the lab OS — only after approval

1. Open **Disk Utility**, select the existing internal APFS volume
   **Macintosh HD**, then **Edit → Add APFS Volume**.
2. Name the new volume **iLinux Boot Lab**, format **APFS**, with no quota or
   reserve. Check the name is unique. Choose **Add**, not Erase or Partition.
3. Open **Install macOS Tahoe**. At destination selection choose **Show All
   Disks → iLinux Boot Lab**. Stop if that exact destination is unavailable,
   an erase is proposed, or the selected destination is Macintosh HD/Data.
   If macOS blocks the launch, stop and investigate; do not override Gatekeeper,
   strip quarantine, re-sign the app or suppress signature verification.
4. Authorize with the original volume owner's credentials when Apple asks.
   Let the installer complete its reboots; do not interrupt installation.
5. Complete the new installation's setup with a local administrator account
   and a nonempty password. Skip migration and Apple Account/iCloud setup.
   This lab needs no personal data. Leave FileVault off **for the lab only**;
   preserve the original installation's encryption. If lab encryption is
   already enabled, stop and review before changing it.
6. From the lab desktop, verify `sw_vers` reports **26.6.2 / 25G83**, and Disk
   Utility shows the lab's System/Data volume group separately from the
   original. A plain empty APFS volume is not sufficient.
7. Shut down; hold the power button continuously until startup options load.
   Select **Macintosh HD → Continue**. Confirm the original macOS still boots.
   Check its recorded build and security/encryption state have not changed.

Source: [Apple's additional macOS volume procedure](https://support.apple.com/en-us/118282).

## 4. Stage the exact m1n1 binary on the lab's Data volume

While back in the original macOS, use Finder/Disk Utility to identify the
**lab Data** volume by its volume-group relationship. Expected mounted name:
`/Volumes/iLinux Boot Lab - Data`. Mount it if necessary after approval.
If the name differs, inspect the actual layout and revise the paths below;
do not guess a disk number or substitute the original Data volume.

The sender already verified this local payload:

```text
/Users/nickyrice/Documents/iLinux/ilinux-publish/build/native-boot-receipt-check/ilinux-j716c-boot021/m1n1.bin
```

Copy **only** that `m1n1.bin` into a new `Users/Shared/iLinuxBoot` folder on
the lab Data volume. The resulting expected path is:

```text
/Volumes/iLinux Boot Lab - Data/Users/Shared/iLinuxBoot/m1n1.bin
```

Verify the staged copy:

```sh
shasum -a 256 '/Volumes/iLinux Boot Lab - Data/Users/Shared/iLinuxBoot/m1n1.bin'
stat -f %z '/Volumes/iLinux Boot Lab - Data/Users/Shared/iLinuxBoot/m1n1.bin'
```

Require **3,932,160 bytes** and SHA-256:

```text
ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664
```

This is the unmodified `57a9339ffd1876e78297b17d34dece8cff8fa1ba` source
build with marker `ilinux-57a9339-boot021`, raw entry offset **2048**, lowest
virtual address **0**, and no appended Linux payload. Do not rebuild,
concatenate payloads, or substitute a release/chainloading image here.

## 5. Enter the lab's paired recoveryOS

Set **iLinux Boot Lab** as the default using **System Settings → General →
Startup Disk**. Boot it once and confirm the lab desktop/build. Then shut
down and hold the power button in **one continuous press** until startup
options appear; choose **Options → Continue**. If asked which installation
to recover, choose the lab and authenticate as its owner.

The default selection determines which paired recoveryOS starts. Selecting
a volume inside an already-running recovery environment is not proof of
pairing. Do not use the double-press fallback-recovery gesture.
Source: [Apple's recovery pairing rules](https://support.apple.com/guide/security/paired-recoveryos-restrictions-sec4cf9d63a6/web).

Open **Utilities → Terminal**. Use Disk Utility if necessary to mount the
lab System and Data volumes. The expected System path is
`/Volumes/iLinux Boot Lab`. Keep the original data locked when it is not
needed. Do not record full disk/policy dumps or machine identifiers.

Run this **read-only preflight** in Recovery Terminal. It uses built-in tools,
keeps volume-group identifiers only in shell memory and stops on mismatch.
If any path differs, stop and review the actual layout before editing it.

```sh
/bin/bash --noprofile --norc
set +o history

ilinux_preflight() {
    ILINUX_READY=no
    ILINUX_OS='/Volumes/iLinux Boot Lab'
    ILINUX_DATA='/Volumes/iLinux Boot Lab - Data'
    ILINUX_ORIGINAL='/Volumes/Macintosh HD'
    ILINUX_BOOT="$ILINUX_DATA/Users/Shared/iLinuxBoot/m1n1.bin"
    ILINUX_HASH=ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664

    test "$(diskutil info -plist "$ILINUX_OS" | plutil -extract VolumeName raw -o - -)" = 'iLinux Boot Lab' || return 1
    test "$(diskutil info -plist "$ILINUX_DATA" | plutil -extract VolumeName raw -o - -)" = 'iLinux Boot Lab - Data' || return 1
    test "$(diskutil info -plist "$ILINUX_ORIGINAL" | plutil -extract VolumeName raw -o - -)" = 'Macintosh HD' || return 1
    ILINUX_VG=$(diskutil info -plist "$ILINUX_OS" | plutil -extract APFSVolumeGroupID raw -o - -) || return 1
    ILINUX_DATA_VG=$(diskutil info -plist "$ILINUX_DATA" | plutil -extract APFSVolumeGroupID raw -o - -) || return 1
    ILINUX_ORIGINAL_VG=$(diskutil info -plist "$ILINUX_ORIGINAL" | plutil -extract APFSVolumeGroupID raw -o - -) || return 1
    test -n "$ILINUX_VG" && test -n "$ILINUX_ORIGINAL_VG" || return 1
    test "$ILINUX_VG" = "$ILINUX_DATA_VG" || return 1
    test "$ILINUX_VG" != "$ILINUX_ORIGINAL_VG" || return 1
    test "$(diskutil info -plist "$ILINUX_DATA" | plutil -extract FileVault raw -o - -)" = false || return 1
    test "$(plutil -extract ProductBuildVersion raw -o - "$ILINUX_OS/System/Library/CoreServices/SystemVersion.plist")" = 25G83 || return 1
    test "$(stat -f %z "$ILINUX_BOOT")" = 3932160 || return 1
    test "$(shasum -a 256 "$ILINUX_BOOT" | awk '{print $1}')" = "$ILINUX_HASH" || return 1
    ILINUX_POLICY=$(bputil --display-policy --vuid "$ILINUX_VG") || return 1
    case "$ILINUX_POLICY" in *': Paired'*) ;; *) return 1 ;; esac
    case "$ILINUX_POLICY" in *'one true recoveryOS'*) ;; *) return 1 ;; esac
    unset ILINUX_POLICY ILINUX_DATA_VG ILINUX_ORIGINAL_VG
    ILINUX_READY=yes
    echo 'Preflight passed: separate lab group, expected build/payload, paired 1TR.'
}
ilinux_preflight || echo 'STOP: preflight failed; do not change policy or boot objects.'
```

The plist keys and hash/size commands were checked on the running host;
pairing predicates match Asahi's installer. All five shell blocks pass Bash
syntax checking. With stand-ins for the system tools, the preflight accepts
one valid layout and rejects eleven identity, build, hash, encryption and
recovery failures; those checks invoke no real disk/policy operations.
This block has not been run in
the future lab Recovery. Different output, missing mounts, absent tools or
credentials errors require review, never bypassing a check. Disk numbers
can change across boots; none is hard-coded here.

## 6. Change only the lab policy and install its custom boot object

**This is the actual security-change gate. Not authorized by preparation.**
Require the preflight success line and the human's explicit authorization.
In the same Recovery Terminal shell, issue one command at a time:

```sh
test "$ILINUX_READY" = yes && bputil --permissive-security --disable-kernel-ctrr --vuid "$ILINUX_VG"
```

This selects **Permissive Security** and disables kernel CTRR enforcement
for the lab entry, following the relevant operations in
[Asahi's stage-two source](https://github.com/AsahiLinux/asahi-installer/blob/e93743d52178b3e26e428fa05174ef549abf30cb/src/step2/step2.sh).
It is more than merely selecting Reduced Security. Authenticate interactively
with an owner of the **lab** installation. On any error, stop; do not proceed
to the next command or retry automatically.

Only after that succeeds:

```sh
test "$ILINUX_READY" = yes && kmutil configure-boot \
  --custom-boot-object "$ILINUX_BOOT" \
  --raw --entry-point 2048 --lowest-virtual-address 0 \
  --volume "$ILINUX_OS"
```

Require a successful exit and the correct lab destination in any prompt.
This replaces the lab's boot object; it does not delete its macOS files.
The command/offsets follow the [m1n1 installation guide](https://asahilinux.org/docs/sw/m1n1-user-guide/)
and this host's `kmutil configure-boot --help`. No SIP/authenticated-root
change on the original OS, global `nvram boot-args`, upstream shell, or
Asahi installer model-check bypass belongs in this procedure. Do not run
the full upstream stage-two script: it also performs stub-specific writes.

**Stop here unless Stage A boot has also been approved.** Installation alone
is not proof that m1n1 runs on this unit. On a pairing/policy error, leave
the original entry alone and return for review.

## 7. Stage A acceptance and normal macOS return

After Stage A approval, shut down and use the power-button startup picker
to select **iLinux Boot Lab**. The M1 discovers the actual primary USB path
and runs only the bounded P_NOP check in the package README. Record visible
m1n1 output and handshake result. Stop after one failed attempt; neither a
logo nor a successful P_NOP establishes Linux support.

After the observation, shut the M5 down; if m1n1 is unresponsive, hold power
until it turns off. Start with power held for startup options, choose
**Macintosh HD → Continue**, and check the original macOS works. Restore
**Macintosh HD** as the default in Startup Disk settings. Recheck its build,
FileVault and previously recorded security state; report only sanitized
outcomes. Future lab boots use the picker, leaving macOS as the normal default.

This return procedure is supported by [Apple's startup selection guide](https://support.apple.com/guide/mac-help/change-your-mac-startup-disk-mchlp1034/mac),
but is not a guarantee against every experimental hardware failure. If the
original entry is absent or cannot boot, stop and use the M1 recovery plan.
Do not erase, delete volume groups, restore firmware, or reset policies as
an automatic troubleshooting step. Reverting/removing the lab entry is a
separate task; a power cycle does not undo installation or policy changes.

Only then consider the separately approved **Stage B** one-core RAM Linux
diagnostic in [first-boot-plan.md](first-boot-plan.md). Its first goals are
visible PID 1, one online CPU, 60 seconds of heartbeat and return to macOS.
It contains no desktop, SSH or Linux agent. The Linux configuration agent
starts after native input/network and a persistent Linux environment exist.

## M1 handoff for this preparation

Pull the latest Git changes with `git pull --ff-only`, retain the existing
boot021 receipt/pin, and read this procedure. Do not run its M5 commands on
the M1. Report offline receipt readiness and keep the Stage A instructions
available while the M5 is in Recovery. All boot/policy/live actions remain
on hold. GitHub receives this procedure and public-source payloads only,
never Apple's installer, boot policies, identifiers or personal data.
