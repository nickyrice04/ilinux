# Job 043: offline compile/validation check of the revised t6050 patch series (2026-10-16)

Checks `kernel/patches/t6050/0001`–`0007` after the 2026-10-16 revision of 0005 (per-TCB NVMMU status
array, lo/hi 32-bit base stores on M4+) and 0007 (SMC + mailbox DT nodes). Runs in the workspace VM with
no network: a clean `git worktree` of the pinned base `77cb8f24` is created from the tree job 020 fetched
(`/var/tmp/t6050-build/linux`), the series is applied with `git am`, `drivers/nvme/host/apple.o` and
`drivers/soc/apple/sart.o` are built with `W=1`, the t6050 DTB is built, `checkpatch --strict` runs on
0005/0007 (informational) and the probe audit maps each compatible to a driver. Nothing boots.

Result (run 3, 2026-10-16T04:59Z, after tightening the SMC comment lines; `out/RESULT.txt`):

| Check | Result |
|---|---|
| `git am` of the 7 patches on `77cb8f24` | 7 applied, exit 0 |
| `apple.o` + `sart.o`, `W=1` (gcc 16.1.1) | exit 0, 0 warnings in our files |
| `apple/t6050-j716c.dtb` (in-kernel dtc 1.8.1) | exit 0, 0 dtc warnings, 61902 bytes |
| `CHECK_DTBS` / `dt-validate` | skipped: dtschema not installed in the VM (`pip install dtschema` needs network) |
| `checkpatch --strict` | 0 findings in `apple.c` and none in the new SMC hunk except the expected "`apple,t6050-smc` appears un-documented" (binding file outside the sparse clone); the rest are pre-existing generated DT comment lines and the `Co-Authored-By` form |
| probe audit | `apple,t6050-smc` → `drivers/mfd/macsmc.c` (via `apple,t8103-smc`), `apple,smc-gpio` → `gpio-macsmc.c`, `apple,smc-hwmon` → `macsmc-hwmon.c`, `apple,t6050-asc-mailbox` → `soc/apple/mailbox.c`, `apple,t6050-nvme-ans2` → `nvme/host/apple.c` |

Inputs: `in/patches/` (the exported series), `in/probe-audit.sh` (copy of `kernel/experiments/t6050-dt/probe-audit.sh`).
Run: `tools/vm-job.sh virtualization/jobs/043-nvme-smc-patches <owner>`.
