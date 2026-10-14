# Job 031 — t6050 GPIO handoff

Run only in the existing isolated build VM with this directory mounted as
`job` and the repository read-only as `ilinux`. Requires the retained boot030
source/Image and host `build/native-boot030/verified` payload. No downloads,
new disks, native launch or host settings change. See
`kernel/experiments/gpio-handoff/README.md` for source pins and evidence.

The job preserves boot030, creates `/var/tmp/ilinux-boot031/linux`, runs two
ASan/UBSan suites, links Image, checks unchanged config and an ELF roundtrip,
and exports under ignored `out/`. It deliberately refuses an existing work
copy; inspect failed-run state before a separately pinned resume.
