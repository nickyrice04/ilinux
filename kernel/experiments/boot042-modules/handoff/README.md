# boot042: what is left for the handoff (2026-10-19)

**Applied with the user's approval (2026-10-19), uncommitted:** the boot042 entry in
`native/boot/make-package.py`, `native/boot/boot041-package-manifest.json` (boot041's record, `0bd25282…`,
the entry's baseline), `native/boot/test_boot042_package.py` and `native/boot/mutate_boot042.py`. boot042 is
packaged in the ignored `build/native-boot042/`. What boot042 is and every result:
`native/boot/boot042-keyboard-modules-2026-10-19.md`.

The entry, additive only: the name joins the `--name` choices and the 14 cumulative lists boot041 is in, and
the baseline map gets boot042 → boot041 (16 existing lines extended); 9 new lines: the allowed changes
(`Image`, the Stage-B DT, `kernel.config`), one call to `boot042_modules.check_package`, and the record's
history line and fields from `boot042_modules`. `check_stage_b`, every other entry, the help strings and
every controller file are unchanged, and so are the four places the attempt-27 launcher patch changes: the
two apply together in either order with the same result (checked on copies). The package carries no
storage: no storage module or script, and an Image without NVMe, SART or nvme-core code.

| Package (`build/native-boot042/`) | |
|---|---|
| `ilinux-j716c-boot042.tar.gz` | 18,877,362 bytes, SHA-256 `a2e57c0ccddcd7c8e60affac0ffa033deb9db1639119a7aa93faaedea276a781` |
| SHA-256 of its `SHA256SUMS` (the intake digest) | `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd` |
| records | `build/native-boot042/records/` (`package-manifest.json`, `archive-sha256.txt`, `intake-manifest-sha256.txt`) |
| the root's pin | `build/boot042/records/omarchy-root-manifest.json` |

**The handoff's records, pin and pin-bound test change** have been in `native/boot/` since 19:35 on
2026-10-19, put there by another session in the shared checkout (this session left them, as the user asked);
they equal `build/native-boot042/records/*`, `build/boot042/records/omarchy-root-manifest.json` and
`test_ramroot-boot042.diff` byte for byte. With them, the committed launcher's offline run from the
repository passes:

```sh
python3 -I native/boot/launch.py --package build/native-boot042/verified --profile omarchy \
    --ramroot virtualization/jobs/045-omarchy-installer-root/out/ramroot.cpio.zst
```

Left for the handoff: the suites, the prerelease `native-j716c-boot042`, the draft checklist as
`stage-b-instructions.md`, and `coordination.md` / `progress.md`. `test_ramroot-boot042.diff` (the one
pin-bound assertion: the Omarchy pin is built for boot042's Image) and the attempt-27 launcher patch's
changes to `test_ramroot.py` apply together.
