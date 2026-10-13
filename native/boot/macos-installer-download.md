# Matching macOS installer download — 2026-10-13

User authorization: download the matching installer only. Stop before volume
creation, installer launch, boot-setting changes or restart.

## Observed result

* `caffeinate -i softwareupdate --fetch-full-installer --full-installer-version 26.6.2`
  completed with exit 0 and `Install finished successfully`. That operation
  places the installer application on disk; no OS installation was launched.
* Location: `/Applications/Install macOS Tahoe.app`.
* Apple catalog selected **26.6.2 / 25G83**. A complete embedded XML asset
  plist parsed from the uncompressed SharedSupport disk image independently
  reports `OSVersion=26.6.2`, `Build=25G83`. The image was read as a regular
  file; no image attachment or mounting was used.
* `Contents/SharedSupport/SharedSupport.dmg`: **18,384,624,402 bytes**.
  `hdiutil verify` returned exit 0 and a valid checksum, aggregate CRC32
  `C5FA1550`. This is corruption detection, not a signature/authenticity proof.
* The app's own version is **21.6.01 / 21601**. Its SDK/platform version is
  not the OS payload version and was not used to select the build.
* After download, the running OS remains **26.6.2 / 25G83** and the observed
  APFS volume names/roles are unchanged. There is no `iLinux Boot Lab` entry.

## Unresolved installer assessment

`codesign --verify --deep --strict` returned exit 1:

```text
resource envelope is obsolete (custom omit rules)
```

Repeating without the explicit strict flag and checking the main executable
with an Apple-anchor requirement produced the same error. Gatekeeper's
`spctl --assess --type execute --verbose=4` returned exit 3 with the same
resource-envelope rejection. Signature *display* names macOS Software Signing,
Apple Code Signing Certification Authority and Apple Root CA, with a stapled
ticket; displaying those fields does not establish successful verification.

**Download complete; version and image checksum match; application trust
assessment unresolved.** Investigate this before launching the installer.
No re-signing, Gatekeeper exception, quarantine removal, security change or
installer execution was attempted. Do not claim either a successful trust
assessment or proven malicious/corrupt content from these results.

## Handoff state

The user reports that the M1 has finished offline verification. Its detailed
results have not yet appeared in GitHub as of the final fetch for this entry.
The M1 agent should publish its own observed hashes, revision and test results
in `progress.md` and `coordination.md`, describing itself as **offline ready**.

* Live USB/P_NOP: **NOT RUN**.
* Native m1n1 boot: **NOT RUN**.
* Native Linux diagnostic: **NOT RUN**.
* Native Omarchy desktop: **NOT RUN**.

The next native attempt still requires a separately approved dedicated OS
entry, paired Recovery/custom boot object and Stage A USB verification; see
[the setup procedure](../../kernel/native-enablement/boot-entry-setup.md).
The first Linux payload is a one-core RAM diagnostic, with no desktop,
network access or configuration agent. All Apple installer contents remain
local and outside Git; this record contains only sanitized results.
