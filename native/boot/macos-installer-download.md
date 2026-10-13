# Matching macOS installer download — 2026-10-13

User authorization: download the matching installer, then resolve verification
without disabling security checks. Stop before volume creation, installer
launch, boot-setting changes or restart.

**Current result: package authenticity and installed-file integrity verified.**
The outer application's custom-resource-rule rejection remains unchanged;
it was neither suppressed nor converted to an application-assessment pass.
This clears the investigation into the downloaded contents. Subsequently the
user authorized lab-entry setup: the normal installer GUI launched successfully
without a bypass, and the new lab volume was selected. Installation is now in
progress; completion is unverified and boot-security changes remain unauthorized.
Current execution handoff:
[boot-entry setup](../../kernel/native-enablement/boot-entry-setup.md).

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

## Initial whole-app assessment and explanation

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

The local `Contents/_CodeSignature/CodeResources` has custom rules omitting
resources and empty sealed-file maps. Apple documents this error as
[errSecCSWeakResourceRules](https://developer.apple.com/documentation/security/errseccsweakresourcerules).
The [Apparency author's explanation](https://www.mothersruin.com/software/Apparency/faq.html)
specifically describes this macOS-installer packaging exception. We did not
adopt its error-suppression approach. Instead, the checks below authenticate
the package and compare the installed contents against its signed payload.

## Successful independent verification — 2026-10-13

**Observed:** the installed `SharedSupport.dmg` also contains the complete
original XAR `InstallAssistant.pkg`. Its header starts `xar!`; Apple's signed
postinstall script links/copies the entire package to that path. The script
was inspected as data, never executed. No second 18 GB download was necessary.

| Check | Observed result |
|---|---|
| Official catalog/distribution | Product `140-93587`, macOS **26.6.2 / 25G83** |
| Local package size | **18,384,624,402 bytes**, matches catalog |
| `pkgutil --check-signature` | Exit 0, **signed Apple Software** |
| Package certificate chain | Software Update → Apple Software Update Certification Authority → Apple Root CA |
| `spctl --assess --type install --verbose=4` | Exit 0, **accepted; source=Apple Installer** |
| Compressed XAR table | Matches catalog SHA-1 and stored signed checksum |
| Five XAR entries | Every archived and extracted checksum matches the signed table, including the complete embedded image |
| Installed app vs signed Payload | **695 regular files, 226 directories, 26 symlinks** match; zero mismatches or unexplained additions |
| Three executable signatures | `InstallAssistant`, `startosinstall`, `createinstallmedia`: strict, all-architecture, explicit Apple-anchor verification passes |
| Generic whole-app execution assessment | Still rejected for custom omit rules; not suppressed |

Installed regular files are compared byte-for-byte, directory/file types are
checked, and symlink destinations must match. Only the SharedSupport directory
and package are allowed beyond the Payload tree, as described by the signed
postinstall script. The package itself is separately verified above. This is
a content/type comparison, not an audit of installed ownership, ACLs or xattrs.

Reproducible identifiers:

```text
Whole-package SHA-256:
376923d7494cfa32b69f383bcfdce46aeedb609fe6a242ea12a6e015bfb77ba4
Catalog / compressed XAR-table SHA-1:
9545b959cab5c536998c45f0fdd4b5d3832dc6f7
Signed embedded SharedSupport.dmg entry SHA-1:
65adfb4192ad9e8b6282f3ecc480cd3cafdabfef
```

The catalog's `Digest` covers the compressed XAR table, **not the full package**.
An initial exploratory whole-file/catalog comparison used the wrong scope;
the subsequent correctly scoped comparisons all passed. The whole-file SHA-256
is a local reproducibility identifier, not an independently published Apple
hash. SHA-1 here follows the Apple-signed XAR format; we did not alter its
signature or select a weaker system assessment policy.

Source data came directly from Apple's HTTPS
[software-update catalog](https://swscan.apple.com/content/catalogs/others/index-26-15-14-13-12-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog).
The selected distribution and metadata are retained locally under ignored
`build/installer-verification/`. No third-party downloader was executed.

## Repeating the read-only checks

From the repository root, with the locally retained Apple catalog:

```sh
caffeinate -i python3 -I native/boot/verify-installer.py \
  --catalog build/installer-verification/catalog.plist
python3 -I native/boot/test_installer_verifier.py
```

The verifier is deliberately pinned to this product, package version **25.6.83**,
and installed app path. It requires successful system package trust checks,
signed-entry integrity, exact installed contents and the three executable
signatures. It never launches package code, extracts files to disk, mounts an
image, downloads, changes policy or modifies the app. The actual run returned
PASS; eleven synthetic regressions cover altered files/links/types, additions,
missing files, malformed archives, bounded decompression and failed system
checks. Local result: `build/installer-verification/verification-result.json`.

No re-signing, Gatekeeper exception, quarantine removal, security change or
installer execution was attempted. A future authorized launch must use the
normal Apple flow. If that launch is blocked, stop and investigate that actual
failure; this verification does not authorize overriding it.

## Handoff state

M1 published its offline report in commit
`dfdf8cf8a1d5b626536ec96adea0b24a7b5fa2ee`, now reviewed and integrated here.
The archive/manifest checks and all 13 files passed; 26 launcher/intake/fake-USB
tests and LLVM toolchain checks passed. Its client is clean at the agreed pin.
This is **offline readiness**, not a physical connection or native boot result.
See `progress.md` and `coordination.md` for its exact observations.

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
