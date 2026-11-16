# Exact J716c 27.2.1 installer availability and refresh options

Observed November 16, 2026, using public primary-source documentation and
bounded public metadata only. No host software-update command, TSS request,
device identifier, image-body download, installer, volume, policy or setting
operation ran.

**The exact build is publicly advertised for this board and its Apple restore
object is reachable.** This answers a missing planning question; it does not
prove current personalization/signing success or make an update authorized.

## Direct Apple evidence

Apple Developer lists **macOS 27.2.1, build 26B131**, released November 9, 2026.
[Official release](https://developer.apple.com/news/releases/?id=11092026d).

A HEAD-only request to the exact public
[Apple restore object](https://updates.cdn-apple.com/2026FallFCS/c202a724-db7e-4d56-917b-110aa0226507/UniversalMac_27.2.1_26B131_Restore.ipsw)
returned HTTP 200 and these selected public metadata fields:

| Field | Observed value |
| --- | --- |
| Content-Length | 25,595,954,706 bytes |
| Accept-Ranges | bytes |
| Advertised SHA-256 | `233e85a09887579d47d0b195e7db72be7f204261059c6946f719acf6b300814f` |

No body was read. That digest is server-advertised metadata, **not a digest
computed over downloaded bytes**. Availability of the URL is not evidence
that Apple will issue every required ticket for an actual installation.

A separately bounded read of Apple's public
[GDMF version metadata](https://gdmf.apple.com/v2/pmv) returned 85,107 bytes.
Both `PublicAssetSets.macOS` and `AssetSets.macOS` list 27.2.1 / 26B131.
The SupportedDevices namespace here is board identifiers: the reference
board is listed as **J716cAP**, not the product identifier Mac17,6.
The same-version device-specific builds 26B7131 and 26B8132 do not list
J716cAP. The initial product-name lookup was corrected before drawing a
compatibility conclusion. Two small metadata reads were performed; no
restore archive member or firmware payload was retrieved.

This establishes a current generic Apple OS-advertisement match, not a
board-specific IPSW BuildManifest selection or a live TSS result. Exact
restore manifest identity, package trust, full-installer availability on
this Mac and signing/personalization remain unqualified.

## The inspected community installer is not an exact-build updater

At the inspected `aurora-installer` revision
`832788c858f7bc5db8ba67d1232844977ffa8489`:

- Its general pinned entry is **27.2 / 26B123**, with minimum system iBoot
  mBoot-20457.41.3, minimum macOS 27.2 and minimum Recovery
  26.2.123.0.0,0. Its admitted models list is empty at that revision.
- Its qualification test explicitly requires **27.2.1 / 26B131 not to be
  admitted**. J716c is not a listed device in this policy.
- Existing K114/K116 T6050 rows select a device-specific 27.2 / 26B8125
  image. They are not the exact J716c reference tuple.
- The startup-firmware slots planner exists, but its executor and app
  action are explicitly **not wired**. It is not an implemented supported
  refresh button we can invoke.
- Its documentation explicitly explains that 26B123 and 26B131 share the
  same mBoot string while DCP and SEP firmware differ. Relabeling its
  existing row or replacing its URL would defeat the exact-build pin.

[Sealed selection policy](https://github.com/aurora-silicon/aurora-installer/blob/832788c858f7bc5db8ba67d1232844977ffa8489/macOS/Sources/AuroraAppleInstaller/NativeInspectionPolicySource.swift),
[qualification rules](https://github.com/aurora-silicon/aurora-installer/blob/832788c858f7bc5db8ba67d1232844977ffa8489/macOS/scripts/tests/test_firmware_qualification.py),
[qualified-build record](https://github.com/aurora-silicon/aurora-installer/blob/832788c858f7bc5db8ba67d1232844977ffa8489/macOS/scripts/firmware-qualification.json),
[startup-firmware design and unfinished executor](https://github.com/aurora-silicon/aurora-installer/blob/832788c858f7bc5db8ba67d1232844977ffa8489/macOS/docs/startup-firmware-update.md).

## A concrete future option for this existing Lab

The most direct option to qualify is an **Apple-supported full macOS
installation/upgrade targeting the existing iLinux Boot Lab**, using the
exact compatible 27.2.1 installer. Apple documents obtaining compatible full
installers and choosing an additional volume as the installation target.
This could refresh Lab's OS iBoot, coprocessor firmware and paired Recovery
without introducing a new Linux partition or replacing Original's files.
It is a proposal to investigate, not a qualified operation on this current
Lab or a command to run.
[Apple installer acquisition](https://support.apple.com/en-us/102662),
[Apple installation on another volume](https://support.apple.com/en-us/118282).

Before an owner decision, the concrete installer package and its exact build,
compatibility, trust verification, destination-space needs, current external
backup and manual rescue must be established. The existing Lab's custom boot
state and re-enrollment after refresh require their own reviewed sequence.
Original must remain at Full Security. A Lab-only destination still may
advance shared system firmware; retaining Original does not mean global
firmware is unchanged.

After an approved refresh, first validate the stock Lab OS and separate
Original return. Take new experiment baselines after that transition; do
not reuse old policy anchors or consumed transactions. Qualify boot021's
physical fallback on the new firmware independently from its known bytes.
Then enroll the reviewed matching Aura/CTXR/kernel stack under its own
approval. Do not use Finder's whole-Mac IPSW Restore as a Lab refresh, run
the J714s partitioner, or present the unfinished slots executor as a ready
alternative.

No update, download of the OS image, native kit, restart or boot test is
authorized or ready from these metadata observations.
