# M5 dedicated boot entry: installed; original macOS return complete

**Stage A update (2026-10-13):** the controlled boot reached `Running proxy...`,
but the checker stopped at discovery because of a filename-suffix assumption.
No port was opened; P_NOP is NOT RUN. User confirms Macintosh HD return.
The local checker now identifies VID/PID and primary CDC interface via cached
macOS metadata; 20 offline tests pass. Live mapping remains unverified. Follow
[the revised checklist](../../tools/m1n1-client/stage-a-instructions.md) when
the user starts the next attempt; this repair performs no new boot/connection.
No Recovery/reinstallation. Linux and live target-version checks remain NOT RUN.

**Earlier post-install return review by B (before the interrupted Stage A):** M1 report `c6f2c6f` is integrated. Original build
26.6.2 / 25G83, FileVault, SIP and original authenticated-root are independently
checked; staged payload size/hash match. The user supplied a fresh policy read:
original Full/lab Permissive, both exit 0. Return checks are complete. The
csrutil OS list may reorder between queries; choose by name within the same
live prompt. Use the installed entry for the next separately authorized Stage
A test (now authorized above); do not repeat provisioning or change the default
from Macintosh HD.

## 2026-10-13 · M1: lab m1n1 installation and original macOS return complete

Evidence: human-entered commands on the M5, user-reported results and screen
photos reviewed by M1; no remote M5 query by M1. Only sanitized conclusions
are retained. Raw photographs, policy identifiers and credentials are not copied.

* Lab desktop build confirmed **26.6.2 / 25G83** before paired Recovery.
  Staged helper SHA-256 matched
  `e65636d03cfb7a7000f86810fdc8888e209b99bedaa1b36ca7a125de4bf72188`.
  Recovery lacked `shasum`; a temporary same-shell function accepted only
  `shasum -a 256 FILE` and delegated to `/sbin/sha256 -q`. No helper file
  or system tool was modified. The helper/payload checks then passed.
* Read-only preflight: **exit 0; original Full; lab Full; lab paired 1TR**.
  An initial mistyped readiness variable stopped the guarded operation;
  the corrected command subsequently reached authentication and succeeded.
* Authorized lab policy update succeeded: **lab Permissive, kernel CTRR
  Disabled**, with helper postcheck **original Full / lab Permissive / paired
  1TR**. The guarded installation rechecked policy and payload before kmutil.
* User reports **kmutil exit 0; Installed yes**, and final policy check
  **original Full / lab Permissive**. This completes boot-object installation.
* **Incidental m1n1 startup observed:** user released the power button early
  during the return sequence. Their photo shows m1n1 screen output/logo and
  `Running proxy...`. User reports promptly powering off, then successfully
  returning to the usual Macintosh HD desktop and selecting **Macintosh HD
  as the default startup disk**. This is screen evidence of m1n1 execution,
  not a completed Stage A test or evidence of Linux execution. Duration and
  exact running version were not verified; USB initialization text does not
  establish a controller connection or a successful P_NOP exchange.
* **NOT RUN:** live USB connection/P_NOP, live target-version check, Stage A
  controlled handshake, Stage B/native Linux and native Omarchy. No launcher
  was run by M1. No Linux boot, liveness or performance result is claimed.
* Boot021 package/ignored intake receipt are unchanged. M1 rechecked the clean
  client pin: `57a9339ffd1876e78297b17d34dece8cff8fa1ba`. No new offline
  test run was needed for this documentation-only update; prior results stand.
* Subsequent M5 review and post-return checks are recorded at the top. The
  Full/Permissive result in this M1 report was observed in Recovery; the user
  has since supplied the fresh post-return policy result. Do not repeat
  installation. Wait for explicit
  Stage A authorization before any controlled m1n1 boot or USB connection;
  Stage B requires its own approval.

<details>
<summary>Historical pre-execution handoff (do not repeat the completed installation)</summary>

## Current execution handoff — 2026-10-13

**Latest M1 handoff — lab setup and return succeeded (user-observed):** the
user reached the lab desktop and reported `sw_vers` **26.6.2 / 25G83**, then
confirmed return to the usual **Macintosh HD** desktop after startup-selection
guidance. Installation/setup and first lab boot are complete by user report.
M1 did not independently inspect the M5. B reviewed and fast-forwarded M1 commit
`f34970e`, then independently checked the original desktop and mounted lab:

* Current root is **Macintosh HD**, build **26.6.2 / 25G83**; FileVault, SIP and
  authenticated-root protection are enabled. The authenticated-root query now
  prompts for an OS; B selected the observed **Macintosh HD** entry and checked
  its result, rather than interpreting the selection prompt as a status.
* Lab System/Data share one volume group distinct from the original; both are
  mounted at the expected paths, with FileVault off for the lab. Its installed
  SystemVersion.plist independently confirms **26.6.2 / 25G83**.
* **Post-return policy check passed:** the user ran the administrator-only
  read-only helper and supplied JSON reporting original **Full / exit 0** and
  lab **Full / exit 0**, with `read_only: true`. B reviewed the user-provided
  result, not an independent privileged rerun. The earlier Terminal automation
  block was respected; no policy write or workaround was attempted.
* **Staging complete:** after explicit user authorization, B copied the exact
  `m1n1.bin` to the lab Data volume's `Users/Shared/iLinuxBoot/m1n1.bin`.
  Rechecked lab System/Data roles, matching group and separation from original.
  Exclusive creation overwrote nothing; reread bytes match the source and
  tracked manifest (3,932,160 bytes; SHA-256 in section 4). It is an ordinary
  file, not an installed custom boot object. No startup/security setting changed.

Boot021 and its client pin are unchanged.
Live USB/P_NOP, live target-version check, native m1n1/Linux/Omarchy remain
**NOT RUN**. The authorized next operation is lab Recovery/custom-boot setup;
stop after installation/policy verification and return to original macOS.

### Next sequence and observation plan

1. **DONE:** the user's administrator-only, **read-only** boot-policy check
   reports Full for both installations, both exit 0. Only sanitized labels
   and outcomes were recorded, not identifiers or raw policy dumps.
   A local original helper is available on the M5 at
   `build/installer-verification/check-boot-policies.py` (ignored, not in Git).
   The user can review it and run it in their own M5 Terminal:
   `sudo /usr/bin/python3 -I /Users/nickyrice/Documents/iLinux/ilinux-publish/build/installer-verification/check-boot-policies.py`.
   It identifies the two volume groups in memory, invokes only display-policy,
   and prints sanitized JSON. The user-provided output has now been reviewed.
2. **DONE:** exact `m1n1.bin` staged and verified using section 4. No restart is
   needed for the copy. Do not repeat installation or substitute another binary.
3. **AUTHORIZED, execution pending:** lab-only **Permissive Security / kernel
   CTRR change and custom boot object** in section 6. Enter the lab's paired
   Recovery and run the section-5 identity/pairing checks before any policy write.
   Original macOS is never the target. Do not repeat the approval request for
   this scope; stop and investigate a failed prerequisite or changed target.
4. After Stage A authorization, boot m1n1 alone. M1 discovers the actual primary
   USB port and runs one bounded P_NOP check. Record screen/version observations
   and return to original macOS. This establishes the bootloader/proxy path.
5. After reviewing Stage A and obtaining Stage B authorization, use the corrected
   one-core RAM launcher. Record pre-Linux controller output and M5 screen
   milestones as specified in the first-boot plan and result template. No Linux
   desktop, disk installation, network or configuration agent is part of this test.

Data record: [boot-result-template.md](../../tools/m1n1-client/boot-result-template.md).
The first kernel has no persistent USB console. Screen output is the Linux
observation channel; blank output cannot identify the failed hardware subsystem.
If that happens, establish a usable logging path before another blind attempt.

### Current human and M1 handoff

The policy check and staging are complete, and the user has now explicitly
authorized the lab policy/custom-boot task. M5 rechecked the payload, separate
volume groups and AC power. No project VM processes were found. System Settings
currently shows **iLinux Boot Lab** selected and the **Restart…** button; B
opened that pane but has not clicked Restart or changed its selection.

First have M1 pull this handoff. Save work, leave the M5 on power, then restart
into the lab macOS through that Startup Disk pane. At the lab desktop confirm
26.6.2 / 25G83 and the lab identity, then shut down. Hold power continuously
to startup options and choose **Options → Continue** for paired Recovery.
The M5 desktop agent will not run in Recovery; M1 guides the human entering the
commands on the M5. The actual pairing check must pass before a policy write.

After section 6 succeeds, shut down and select **Macintosh HD → Continue** in
the startup picker. Restore Macintosh HD as the default in Startup Disk,
then report the result here. Do not select the converted lab entry for a live
m1n1 test yet. Installing it changes what the lab entry boots; it no longer
boots the lab macOS normally. The original macOS entry is preserved.

Send M1:

> I authorize the lab-only Recovery setup, Permissive Security, disabling
> kernel CTRR and verified m1n1 installation, preserving Macintosh HD at Full
> Security. Pull latest main with `git pull --ff-only`; read this document's
> current handoff and sections 5–6, plus `coordination.md`. Guide me on the M5
> through lab startup, shutdown/held-power paired Recovery, the read-only
> helper and the two gated operations, one at a time. Do not run M5 policy
> commands on the M1. No further approval is needed for this exact scope.
> Stop on identity, pairing, hash, policy or command errors; no bypass/retry
> loops. Record sanitized preflight, bputil and kmutil outcomes, final original
> Full/lab Permissive, and successful return to Macintosh HD. Restore Macintosh
> HD as default afterward. Commit/push the observed results to progress.md and
> coordination.md. Keep the verified boot021 package/client pin unchanged.
> Stage A/P_NOP and Linux boots are not authorized by this setup: no --connect,
> --launch or upstream linux.py; keep all live native checks NOT RUN.

</details>

### Earlier installer handoff (historical; completion updated above)

* Created the unique, empty **iLinux Boot Lab** APFS volume in the existing
  internal container, with no quota/reserve or partition resize. It is mounted
  at `/Volumes/iLinux Boot Lab`. The original volumes' names, roles and FileVault
  states match their pre-creation values. **An empty volume is not bootable.**
* Original macOS is **26.6.2 / 25G83**. Read-only policy inspection reports
  **Full Security**; SIP/authenticated-root are enabled and FileVault is on.
  No boot-security or startup-disk setting has been changed.
* About **997.93 GB** of container space remained after creation. AC attached,
  battery 100%; no project QEMU/vzrun processes were running. Backup completion
  is user-reported; its destination is disconnected, so no content recheck was
  possible in this session. Keep the backup disconnected during installation.
* Repeated the full installer verifier: PASS. The normal Apple GUI launch
  succeeded without a security override. User authorized the displayed license;
  the installer then reached disk selection. B selected the lab and observed:
  **“macOS Tahoe will be installed on the disk ‘iLinux Boot Lab’.”**
* OS installation, the lab's first boot and return-to-original verification
  are not yet complete. **The installer has since advanced to installation
  progress and still explicitly targets iLinux Boot Lab.** Completion/bootability
  are unverified. No custom boot object or live native test has run.

**Human restart handoff:** installation is now in progress. Save/quit remaining
work and enter any requested credentials only into Apple's prompts. Let the
installer initiate and complete its restarts; do not perform a
manual reboot during preparation or interrupt installation. If it proposes a
different destination, erase, OS upgrade or security downgrade, stop.

At the new lab desktop, complete a local administrator setup with a nonempty
password, skip migration and Apple Account/iCloud setup, and check `sw_vers`
for **26.6.2 / 25G83**. Do not open Startup Security Utility or run `bputil`
policy-changing commands, `kmutil configure-boot`, or any m1n1 launcher.
Shut down, hold power for startup options, select **Macintosh HD → Continue**
and return to this M5 checkout. Verify original macOS and security state before
any later work. Installation may make the lab the default; restoring the
original default in Startup Disk is a separate ordinary startup selection,
not a security downgrade. This session has not performed that selection.

Send the M1 agent:

> Pull the latest `main` with `git pull --ff-only` and read the current execution
> handoff in `kernel/native-enablement/boot-entry-setup.md`, `progress.md` and
> `coordination.md`. The M5 has a new iLinux Boot Lab APFS volume and the verified
> matching macOS installer is now showing installation progress targeting it.
> This is macOS boot-scaffold provisioning,
> not a Linux boot. Keep the verified boot021 package and existing client pin.
> Help the user through installer-managed restarts and local lab setup, then
> return to Macintosh HD and report the observed build and successful return.
> Do not change boot security, configure a custom boot object, erase/resize
> disks, enter DFU, run a restore/revive, open a live USB proxy connection, or
> run any native launcher. Keep live USB/m1n1/Linux checks NOT RUN. A later
> explicit authorization is required for the security/custom-boot stage.

**Verification update:** the matching 26.6.2 / 25G83 installer is downloaded.
Its original package passes Apple's signature and Gatekeeper install assessment;
all signed entries and installed app contents match. The outer app's custom-
resource-rule rejection remains unchanged, with no exception or bypass. See the
[verification record](../../native/boot/macos-installer-download.md). M1's
offline receipt is published and reviewed. The execution handoff above records
the subsequent volume/GUI work. The earlier security/custom-boot hold recorded
in this historical section is superseded by the current authorization at top.

## Chosen route and observed prerequisites

Use a second, full macOS installation named **iLinux Boot Lab** as the initial
boot scaffold. Later replace only its boot object with the packaged m1n1.
This is an engineering proposal for this M5, not a validated M5 installer.
Apple supports an additional macOS installation on another APFS volume;
the [M5 support table](https://asahilinux.org/docs/platform/feature-support/m5/)
does not provide a supported Asahi installation route for this machine.

Historical read-only observations before lab installation (current state is
at the top; do not repeat provisioning):

| Item | Observation |
|---|---|
| Current OS | macOS 26.6.2, build 25G83 |
| Main APFS container | 1,995,165,736,960 bytes total; 1,016,906,117,120 bytes free |
| Original installation | System `Macintosh HD`, Data `Data`; FileVault enabled |
| Other boot environment | Empty iLinux Boot Lab volume created; OS install and bootability pending |
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

## 1. Readiness checks and authorization scope

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
5. Download, volume creation and lab installation are complete. The user now
   authorizes **lab-only** Recovery/policy/custom-object installation under
   sections 5–6. Stage A (m1n1/USB) and Stage B (Linux) remain on hold.

## 2. Fetch the matching Apple installer — only after approval

**Completed under download-only authorization. Do not repeat the download.**
The subsequent read-only investigation verified package authenticity and app
contents without disabling security checks; see the verification record.
The later normal GUI launch and OS installation succeeded. The commands below
retain the acquisition recipe for reproducibility; do not run them again.

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

## 3. Create and install the lab OS — complete; historical procedure

The lab OS is installed and has booted successfully: **do not repeat this
section**. These steps retain the historical procedure. Continue at section 5
for the currently authorized Recovery setup.

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

## 4. Stage the exact m1n1 binary on the lab's Data volume — after verified installation

**Completed on 2026-10-13 with explicit user authorization.** The destination
below was newly created on verified lab Data, then reread and compared with
the source and tracked manifest. No boot installation was performed. Retain
the procedure below for reference; do not repeat the copy over an existing file.

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

## 5. Enter the lab's paired recoveryOS — authorized, human execution pending

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

The original read-only helper is staged next to m1n1. Its reviewed source is
[recovery-preflight.sh](recovery-preflight.sh); it defines checks and performs
no writes, mounts or restart. First check its hash, then source it and run
the preflight. It requires distinct original/lab groups, exact internal APFS
mounts, expected lab build/payload, Full policy for both entries and paired
1TR for the lab. Identifiers/policy text stay in shell memory. If paths differ
or an expected tool/output is absent, stop; do not bypass a check.

```sh
/bin/bash --noprofile --norc
set +o history
ILINUX_HELPER='/Volumes/iLinux Boot Lab - Data/Users/Shared/iLinuxBoot/recovery-preflight.sh'
ILINUX_HELPER_HASH=e65636d03cfb7a7000f86810fdc8888e209b99bedaa1b36ca7a125de4bf72188
if test "$(shasum -a 256 "$ILINUX_HELPER" | awk '{print $1}')" = "$ILINUX_HELPER_HASH"; then
    source "$ILINUX_HELPER"
else
    echo 'STOP: helper hash mismatch; do not continue.'
fi
ilinux_preflight || echo 'STOP: preflight failed; do not change policy or boot objects.'
```

The helper's Bash syntax and 21 synthetic preflight cases pass (valid plus
20 failures); policy postchecks also reject original downgrade and wrong lab
mode. Stand-ins invoke no real disk or policy operations. Tests:
`python3 -I kernel/native-enablement/test_recovery_preflight.py`.
Actual paired-Recovery checks remain NOT RUN. Disk numbers are not hard-coded.

## 6. Change only the lab policy and install its custom boot object

**Explicitly authorized by the user on 2026-10-13.** Require the preflight
success line before proceeding. No repeat authorization is needed for this
exact lab target and package. Preserve Macintosh HD at Full Security.
In the same Recovery Terminal shell, issue one command at a time:

```sh
ILINUX_POLICY_OK=no
if test "$ILINUX_READY" = yes && bputil --permissive-security --disable-kernel-ctrr --vuid "$ILINUX_VG"; then
    if ilinux_check_policies Permissive; then
        ILINUX_POLICY_OK=yes
        echo 'Lab policy change succeeded; original remains Full.'
    else
        echo 'STOP: policy postcheck failed; do not install the boot object.'
    fi
else
    echo 'STOP: preflight or lab policy command failed; do not continue.'
fi
```

This selects **Permissive Security** and disables kernel CTRR enforcement
for the lab entry, following the relevant operations in
[Asahi's stage-two source](https://github.com/AsahiLinux/asahi-installer/blob/e93743d52178b3e26e428fa05174ef549abf30cb/src/step2/step2.sh).
It is more than merely selecting Reduced Security. Authenticate interactively
with an owner of the **lab** installation. On any error, stop; do not proceed
to the next command or retry automatically.

Only after that succeeds:

```sh
ILINUX_INSTALLED=no
if test "$ILINUX_READY" = yes && test "$ILINUX_POLICY_OK" = yes &&
   ilinux_check_policies Permissive && ilinux_payload_ok; then
    kmutil configure-boot --custom-boot-object "$ILINUX_BOOT" \
      --raw --entry-point 2048 --lowest-virtual-address 0 --volume "$ILINUX_OS"
    ILINUX_KMUTIL_EXIT=$?
    printf 'kmutil exit: %s\n' "$ILINUX_KMUTIL_EXIT"
    if test "$ILINUX_KMUTIL_EXIT" = 0 && ilinux_check_policies Permissive; then
        ILINUX_INSTALLED=yes
        echo 'Custom boot installation reported success; original remains Full.'
    else
        echo 'STOP: installation or final policy check failed; record the partial result.'
    fi
else
    echo 'STOP: policy/payload prerequisites failed; no installation attempted.'
fi
```

Require a successful exit and the correct lab destination in any prompt.
This replaces the lab's boot object; it does not delete its macOS files.
The command/offsets follow the [m1n1 installation guide](https://asahilinux.org/docs/sw/m1n1-user-guide/)
and this host's `kmutil configure-boot --help`. No SIP/authenticated-root
change on the original OS, global `nvram boot-args`, upstream shell, or
Asahi installer model-check bypass belongs in this procedure. Do not run
the full upstream stage-two script: it also performs stub-specific writes.

**Stop native testing here; Stage A has not been approved.** Record the command
outcomes and sanitized original Full / lab Permissive result. Successful kmutil
exit is an installation result, not proof that m1n1 runs. Shut down and use the
held-power picker to choose **Macintosh HD → Continue**, then restore it as the
default Startup Disk and report original build/FileVault/SIP/authenticated-root
and Full Security. Do not reboot blindly into the now-converted lab entry.
On a pairing/policy/command error, preserve the original entry and report the
partial state; no retries, policy resets, removal or firmware recovery.

## 7. Stage A acceptance and normal macOS return — one session authorized

Stage A approval is now recorded above. Shut down and use the power-button startup picker
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

Use the current execution handoff at the top. Do not run this document's M5
commands on the M1. Lab-only Recovery/policy/custom-boot installation is now
authorized; live Stage A/P_NOP and Stage B/Linux tests remain on hold.
GitHub receives this procedure and public-source payloads only, never Apple's
installer, raw boot policies, identifiers or personal data.
