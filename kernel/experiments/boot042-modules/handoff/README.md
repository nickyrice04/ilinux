# boot042 packaging record (2026-10-19)

boot042 was packaged with the user's approval of one edit to `native/boot/make-package.py`: a boot042 entry,
additive only, as boot036 to boot041 each added theirs. The name joins the `--name` choices and the 14
cumulative lists boot041 is in, and the baseline map gets boot042 → boot041 (16 existing lines extended); 9
lines are new: the allowed changes (`Image`, the Stage-B DT, `kernel.config`), one call to
`boot042_modules.check_package`, and the record's history line and fields from `boot042_modules`.
`check_stage_b`, every other entry, the help strings and every controller file are unchanged, and so are the
four places the attempt-27 launcher patch changes: the two apply together in either order with the same result
(checked on copies). The package carries no storage: no storage module or script, and an Image without NVMe,
SART or nvme-core code. What boot042 is and every result: `native/boot/boot042-keyboard-modules-2026-10-19.md`.

Reproduce, from the repository root, with VM job 050's export in `build/boot042/package/out/export/` and boot041
extracted in `build/native-boot041/verified/`:

```sh
mkdir -p build/native-boot042/records
python3 -I native/boot/make-package.py --out build/boot042/package/out --destination build/native-boot042 \
    --name ilinux-j716c-boot042 --previous-package build/native-boot041/verified \
    --authorized-key kernel/experiments/usb-gadget/authorized_keys --record-dir build/native-boot042/records
python3 -I native/boot/test_boot042_package.py
python3 -I native/boot/mutate_boot042.py
```

Expect `ilinux-j716c-boot042.tar.gz`, 18,877,362 bytes, SHA-256
`a2e57c0ccddcd7c8e60affac0ffa033deb9db1639119a7aa93faaedea276a781`, and `SHA256SUMS` with SHA-256
`60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd` (the intake digest). The packager is
deterministic: another digest means another input or entry.

At the handoff the records (`package-manifest.json`, `archive-sha256.txt`, `intake-manifest-sha256.txt`) and the
root's pin (`omarchy-root-manifest.json`) were copied into `native/boot/`, and `test_ramroot.py`'s one pin-bound
assertion was changed: the Omarchy pin is built for boot042's Image (job 050's, `0b6df395…b69c`).
