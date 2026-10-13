# Video conversion and NV12 experiment records

Method, implementation and limitations:
[engineering report](../../../reports/video-download-and-nv12-2026-10-12.md).

* `validation-final.json`: experimental final source build, 1,440 hardware
  frames compared with software decode, all pass.
* `validation-installed.json`: installed package repeats that matrix,
  1,440 hardware frames, all pass.
* `validation-profiles-strict.json`: installed package, Constrained Baseline
  and Main, another 240 hardware frames, all pass; validator exit 0.
* `validation-stock-strict.json`: unmodified build, one-frame checks,
  cross-format failures reproduced; strict validator exit 1.
* `validation-before-download-fix.json`: exploratory build including the
  rejected dirty-state patch; not an unmodified-stock comparison.
* `roundtrip-{stock,installed}.jsonl`: real VA image uploads/downloads;
  stock has 37,008 incorrect bytes; installed passes all 18 cases.
* `decode-ab-installed/`: final packaged driver with Arch `-O2` flags;
  two ABBA blocks, four observations per setting, 960 frames/run.
* `decode-ab-final/`: earlier experimental `-O3` driver, same ABBA design.
* `decode-ab/`: environment only, from an initial shell-launch error;
  excluded from all performance calculations.
* `summary.json`: separate CPU means/ranges and reduction percentages for
  the two builds. Formula: `100 * (1 - mean_on / mean_off)`.
* `runner-guard-check.json`: intentionally sleeping guest process confirms
  owned-process cleanup and independent wall-clock timeout.
* `mpv-installed.log`: 120-frame VA-API/NV12 OpenGL smoke test, exit 0.
* `package-build.log`, `package-buildinfo.txt`, `package-info.txt`,
  `selected-compile-commands.json`, `installed-package-check.txt` and
  `host-build-identity.json`: build, dependency and artifact identities.

The local package is
`build/mesa-virgl-video-ilinux-26.2.4-1-aarch64.pkg.tar.xz`, SHA-256
`671b62b680dfa5222ef0a30aa54907475c0528f95c777ae7e2f10b55f3bd8429`.
It is intentionally excluded from git; the source recipe is tracked.

No native Linux hardware support or whole-SoC power saving is established.
