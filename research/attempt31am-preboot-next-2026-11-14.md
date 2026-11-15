# After 31AL: deployment blocker and existing 18-core code

November 14, 2026. Offline interpretation and six focused regression controls;
no new Recovery visit, mount, installation, firmware or settings operation.

## Actual result

M1's `6fb1023` records the safe emitted refusal
`AUX_IDENTITIES / GUARD / PREBOOT_MOUNT_PATH`. The pinned original predicate is
`!safe_path(mount)` for the role-selected Preboot volume's `MountPoint`.
The actual path was not returned. Missing or non-string input would have produced
a different format error. An empty string is one possible explanation, alongside
other lexically invalid strings; an unmounted volume is not yet a physical finding.

The command exit0 is metadata capture context. It is not target admission.
Policy, pairing, security, selected-object and native startup phases were not
reached. Macintosh HD desktop and default return are human-confirmed. Boot021
restoration remains outstanding. No repeated policy check is needed here.

## We already use the reported multicore implementation

The November 11 comment in the
[J716c hardware discussion](https://github.com/aurora-silicon/linux/discussions/142)
reports Linux CPUs0–17 using Aura `bd9f3e8273dc` and Linux `dc8f6f77934b` on
the same Mac17,6/J716c/T6050 board. These are the exact sources built by our
31AH jobs and retained by the current inline candidate. Its baseline Aura CPU
startup implementation is already reused; no replacement CPU routine is needed
to get past the present deployment check.

| Item | Comparison with that report |
| --- | --- |
| Aura and Linux source commits | Exact pair already built locally. |
| CPU startup code | Baseline Aura secondary-start path retained. |
| Local additions | Diagnostic config/DT, RAM observer and inline loading/package. |
| Transport | Reporter's small USB2 CDC patch is unpublished; autonomous screen-observed candidate avoids depending on it. |
| Paired firmware | Our recorded25G83/18000.161.10 differs from reported26B131/20457.41.3. Runtime compatibility remains unqualified. |
| Reproduction completeness | Exact resolved reporter config/toolchain/artifact hashes were not supplied. |

The public report is hardware evidence attributed to its author, not a local
performance result. Eighteen online bits do not alone demonstrate simultaneous
work or macOS-equivalent efficiency. Our existing observer is prepared to test
distinct overlapping workers once deployment and native entry succeed.

The new Aura virtualized-SPTM
[Aff2 correction](https://github.com/aurora-silicon/aura/commit/6749cbb7e1193d0b6584ee5ec4d2c1221921a2d8)
changes macOS guest-reset preparation, a different execution path. Do not mix it
into the direct-Linux candidate as an unexplained fix for this Preboot refusal.

## The reusable preparation step

Asahi installer revision `e93743d52178b3e26e428fa05174ef549abf30cb` selects
volumes by APFS role, prepares Preboot, and refreshes its `info -plist` response:
[enumeration](https://github.com/AsahiLinux/asahi-installer/blob/e93743d52178b3e26e428fa05174ef549abf30cb/src/osenum.py#L183-L188),
[mount and fresh observation](https://github.com/AsahiLinux/asahi-installer/blob/e93743d52178b3e26e428fa05174ef549abf30cb/src/diskutil.py#L195-L198).
Our collector omits preparation and assumes a mounted safe path. That is the
concrete deployment difference to address before changing the working source pair.

Borrow the identity-selection/preparation/re-observation sequence, with original
project-specific code and retained notices for any copied open-source component.
Do not run the full installer or transplant its normal mount operation: our
protected reference requires an explicitly scoped read-only approach. The lab
and Original share this container's Preboot volume.

## Next engineering step, before another restart

Prepare a small, separately reviewed Preboot preflight with this behavior:

1. Use existing target/role/device/UUID/container checks. Return only finite
   mount-state/path-class labels, never the actual private path or identifiers.
2. For an already mounted valid path, retain descriptor/no-follow checks and
   leave its mount untouched. For a positively unmounted volume with empty path,
   offer one identity-bound read-only mount only after explicit authorization.
   Other invalid paths or inconsistent metadata remain stops.
3. After an authorized mount, refresh APFS/device metadata and verify identity,
   actual read-only state and safe mounted-directory binding. Do not guess a
   `/Volumes/Preboot` name, repair a filesystem, force/remount a live volume or
   broaden the old path predicate. The installed `diskutil(8)` manual documents
   `mount readOnly` and possible preliminary filesystem checks; qualify that
   behavior before proposing exact production commands.
4. In the same Recovery visit, run the unchanged31AL read-only collector once
   through the remaining checks and retain the safe result. Release only a
   mount created by the new operation, with identity rechecks and no force.
   A passing snapshot still grants no installation or Linux-boot permission.

This combines diagnosis and a narrowly authorized remedy where the evidence
supports it, rather than spending a reboot just identifying another generic stop.
No such preflight/controller or live mount is implemented or authorized by this
note. No new physical test is ready. Frozen31AL code, source inventory, helper,
pages, receipts, deployment state and native candidate remain unchanged.

## Work completed now

`tools/preboot31am/test_preboot.py` composes the existing original C fixture
harness without inheriting its old29 methods. Six new controls exercise empty
and invalid paths, missing/non-string fields, valid-path progression and the
irrelevance of a `Mounted` boolean to the lexical predicate. Six normal and the
same six ASan/UBSan controls pass, repeated independently. All inputs are synthetic;
no live disk/policy commands run. Details are in `tools/preboot31am/README.md`.

M1 can review this finding and the new six-method controls offline, reusing its
86-method review and existing artifact verification. Do not restage, restart,
rerun31AL, start a page/proxy or change settings from this handoff. The next
meaningful milestone remains safe deployment of the already-matched candidate,
then actual Aura entry, Linux entry and18 concurrent physical workers. CPU/RAM
speed, N1/storage, matched GPU/Mesa/Omarchy and energy measurements follow.
