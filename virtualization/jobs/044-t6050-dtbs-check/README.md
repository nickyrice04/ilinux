# Job 044: DT schema validation of the draft t6050 (M5 Max, J716c) device tree (2026-10-16)

Test-plan step 4 of `kernel/patches/t6050/README.md`: `make dt_binding_check DT_SCHEMA_FILES=apple`
and `make CHECK_DTBS=y apple/t6050-j716c.dtb` on the pinned base `77cb8f24` with the seven patches
applied. Runs in the workspace VM with no network and installs nothing: like job 043 it takes a clean
`git worktree` of the tree job 020 fetched (`/var/tmp/t6050-build/linux`), and it uses the dtschema
venv job 020 created on 2026-10-13 (`/var/tmp/t6050-build/dtvenv`: dtschema 2026.9, pylibfdt
1.7.2.post2, jsonschema 4.26.0, Python 3.14.8), the one jobs 032, 038, 040, 041 and 042 already used
through `dt-validate`. Job 043 reported "dtschema not installed" only because it looked for
`dt-validate` on the default `PATH`. If the venv or the base tree is missing, the job stops instead of
fetching or installing. Nothing boots.

Two Asahi boards go through the same `CHECK_DTBS` so that tree-wide or pre-existing findings can be
told from ours: `t8132-j715` (M4 Max, 16-inch) and `t6031-j516c` (M3 Max, 16-inch).

## Result

| Check | Run 1 (series as exported 2026-10-16 00:59) | Run 2 (regenerated series, 01:26Z) |
|---|---|---|
| `git am` of the 7 patches on `77cb8f24` | 7 applied, exit 0 | 7 applied, exit 0 |
| `dt_binding_check DT_SCHEMA_FILES=apple` (every binding whose path contains `apple`, examples included) | exit 0; 2 lines, both pre-existing in the base tree in files the series does not touch (triage below) | the same 2 lines |
| `CHECK_DTBS=y apple/t6050-j716c.dtb` (full processed schema, 26.9 MB, rebuilt each run) | exit 0; **2 findings with one cause**: `smc@28c600000 (apple,t6050-smc): 'apple,t6050-smc' is not one of [...]` from `mfd/apple,smc.yaml`, plus the consequent `/soc/smc@28c600000: failed to match any schema` | exit 0; **0 findings** |
| `CHECK_DTBS=y apple/t8132-j715.dtb` (reference) | 0 findings | 0 findings |
| `CHECK_DTBS=y apple/t6031-j516c.dtb` (reference) | 181 findings, all pre-existing in the Asahi tree (`apple,t6031-dart`, `apple,t6031-asc-mailbox`, `apple,t6031-cluster-cpufreq` and others are not in their bindings; `apple,externally-clocked` and `apple,dma-range` are undocumented; the `ti,sn012776` compatible list is too long) | 181 |

About 60 s inside the VM (01:26:31 to 01:27:33 in `out/script.log`), about 3 minutes with the VM boot.

### Triage

| Finding | Where | Verdict |
|---|---|---|
| `'apple,t6050-smc' is not one of ['apple,t6020-smc', 'apple,t8122-smc']` and `/soc/smc@28c600000: failed to match any schema` | `mfd/apple,smc.yaml` against the DT's `smc` node (`apple,t6050-smc`, `apple,t8103-smc`) | **Real; fixed in patch 0006**: `apple,t6050-smc` added to the enum that takes the `apple,t8103-smc` fallback, next to t6020 and t8122 (the Asahi t6030/t6031 DTs use the same pattern without a binding entry, which is one reason the t6031 reference board is flagged). The DT node itself is unchanged. Gone in run 2. |
| `hwmon/apple,smc-hwmon.yaml:73:1: [warning] too many blank lines (2 > 1)` | yamllint on a base-tree file the series does not touch | Pre-existing in `asahi@77cb8f24`; not ours, left as is |
| `pci/apple,pcie.yaml: ^pci@: Missing additionalProperties/unevaluatedProperties constraint` | dt-doc-validate on a base-tree file the series does not touch | Pre-existing in `asahi@77cb8f24`; not ours, left as is |

The placeholder core compatibles `apple,sotra-m` / `apple,sotra-p` produce no finding: patch 0006 lists
them in `arm/cpus.yaml`, so the schema accepts them. They stay placeholders (see the 0006 row in
`kernel/patches/t6050/README.md`); that is a naming question, not a schema one.

What a clean `dtbs_check` does **not** say: nothing about addresses, interrupt numbers, power-domain
parents, register windows or whether a node works. Those keep their evidence labels in
`kernel/experiments/t6050-dt/README.md`.

## Files

* `in/patches/`: the series checked (run 2 = the regenerated `kernel/patches/t6050/000*.patch`;
  digests in `out/inputs-sha256.txt`).
* `out/` (ignored, wiped by each run): `RESULT.txt`; `toolchain.txt` (venv package versions);
  `dt_binding_check.log` and `dt_binding_check-findings.txt`; `dtbs-check.log` (raw),
  `dtbs-check-t6050.txt` (prefixed lines), `dtbs-check-t6050-full.txt` (with the `from schema`
  continuation lines) and `dtbs-check-t6050-summary.txt`; `dtbs-check-ref.log` and, per reference
  board, `dtbs-check-<board>.txt` and `-summary.txt`; `bindings/` (copies of the bindings the triage
  needed, GPL/BSD Linux docs, including the checked tree's `mfd/apple,smc.yaml`); `job020-*` (job
  020's own dtbs_check output as left in the VM, reference only); `run1-before-0006-fix/` (run 1's
  RESULT and findings).
* Run: `tools/vm-job.sh virtualization/jobs/044-t6050-dtbs-check <owner>` (takes the `vm` lock).
