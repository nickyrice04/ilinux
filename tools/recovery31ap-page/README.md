# 31AP page preparation from Git sources

This adapter prepares the already reviewed page from the canonical public
profile and exact frozen renderer. It does not need a helper binary, kit,
build cache or private transfer on M1. It preserves all 140 frozen sources.

```sh
python3 -I tools/recovery31ap-page/prepare.py --prepare --output build/31ap-source-profile-page
python3 -I tools/recovery31ap/package.py --page build/31ap-source-profile-page/recovery.html --check-only
```

Both commands are offline. The first writes only the public profile, paste
block, HTML and receipt into a new workspace `build/` directory. The second
reuses the original exact-page validator without starting its server. Neither
stages files, queries either Mac, mounts anything or changes boot/security
settings. Default and help do not admit sources or prepare an output.

The adapter hash-checks the admitted package and inventory before import,
verifies all 140 source pins, validates the canonical Git profile, and requires
the exact reviewed profile/paste/page sizes and hashes. Output traversal,
symlinks, an existing destination and a destination outside workspace `build/`
are refused. Source and profile bindings are checked again before publication.

Its receipt explicitly says `SOURCE_PROFILE_PAGE_ONLY` and
`binary_delivery_verified_on_M1=false`. This is not a claim that M1 received or
verified the helper. The unchanged Recovery block verifies the actual helper
and profile staged on M5 before running them. The owner already supplied that
stage receipt; M1 does not need another copy merely to display the page.

Later service, Recovery and any further operation retain their separate
authorization and handoff requirements. A prepared page does not grant boot or
installation permission.

Run the focused controls with:

```sh
python3 -I tools/recovery31ap-page/test_prepare.py
```
