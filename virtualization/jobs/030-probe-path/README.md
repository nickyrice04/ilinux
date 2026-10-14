# Job 030 — deferred-device attribution and probe checkpoints

The existing VM job runner mounts the repository read-only as `ilinux` and this
directory writable as `job`. `run.sh` copies retained boot029 to the absent
`/var/tmp/ilinux-boot030/linux`, validates exact source digests, and applies the
original diagnostic patch. It never modifies the retained predecessor.

Actual helper/panel/identity/platform-probe and DT-mapper tests run under
ASan/UBSan, using the retained kernel's libfdt. Full `make -j2 Image`, unchanged
config comparison and ELF-to-Image roundtrip follow. Export replaces only Image
over boot029. `out/`, objects, logs and release archives remain ignored.

Final validation used the same tests/build after an unsigned-bound warning was
fixed, via an ignored guarded resume job at `build/native-probe-retry/run.sh`.
That job checked five patched-source hashes before replacing the corrected
renderer; it did not make another source copy. Its passing outputs are under
`build/native-probe-retry/out/`. The tracked fresh-copy recipe uses final code.
No native hardware or host settings are accessed. See
`kernel/experiments/probe-path/README.md` and `validation.json` for evidence.
