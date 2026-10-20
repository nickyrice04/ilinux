# T6050 CPU frequency experiment: offline candidate

2026-10-19 driver candidate; **attempt-28 integration prepared 2026-10-20**.
The user authorized the CPU package and M1 handoff. Attempt 28 is explicitly
command-state observation with writes disabled, retaining one core and the
working two-stage root. See [exact validation/pins](../../../native/boot/attempt28/validation.md)
and [M1 instructions](../../../tools/m1n1-client/attempt28-instructions.md).
Native initialization/transitions remain NOT RUN; M1 intake and human start
precede a reboot. No macOS setting or volume changes. This is original
downstream work; no Apple code, pseudocode or extracted bytes are published.

The first objective is to determine whether a bounded request can change the
single boot core's useful throughput. It does not require starting secondary
cores. It also cannot establish macOS efficiency: native power/thermal
telemetry, idle behavior and accelerated graphics remain unresolved.

## Evidence and limits

The existing behavior findings in `../cpu-power-smp/README.md` §4 are the input
to this implementation. They describe REA/Ghidra plus assembly/ADT checks of
this machine's macOS 26.6.2 build 25G83. This continuation reviewed those
findings and the public Linux driver; it did not open new Apple decompiler
output or claim a new REA run.

| Finding | Evidence locator | Interpretation |
|---|---|---|
| Three DVFS blocks at `0x210e20000`, `0x211e20000`, `0x212e20000`; command offset `0x20` | Sanitized ADT PMGR ranges, AppleT6050PMGR `readACCReg` at `0xfffffe0009884934` | Confirmed static address mapping; native Linux behavior untested |
| Requested state bits 4:0, SET bit 25, BUSY bit 31 | AppleT6050PMGR `setPerfState` at `0xfffffe0009883554`, existing assembly cross-check | Reuse the public driver's masked command update |
| CPU domain state translates to `2 + row` | `getPerfStateTableIndex` at `0xfffffe00098838b0`; ApplePMGR table initialization at `0xfffffe000948be34`; ADT tables | Offset supported by static findings; mapping of the first ADT row to state zero remains Likely until measured |
| 15 M states (1.344–4.380 GHz), 20 P states (1.308–4.608 GHz) | ADT voltage-state/SRAM pairs, F-022 | Candidate OPP frequencies; not measured Linux clocks |
| APSC disable/busy bits 23/7 | AppleT6050PMGR `enableAPSC` at `0xfffffe0009880b30` | Refuse requests while either is set; never change these bits |
| STATUS register layout unknown | No established t6050 layout in reviewed findings | Never read it. Absence of a read in an inspected routine is not proof that all macOS code never reads it |

The public implementation baseline is Asahi Linux `77cb8f24`, file
`drivers/cpufreq/apple-soc-cpufreq.c`, SHA-256
`e4efe79b653dc07c18a2bacc607fe69f8144ead11bf10cd4ef9407396ca808d2`.
The job verifies the actual boot042 copy before patching. Upstream source:
[Asahi CPU frequency driver](https://github.com/AsahiLinux/linux/blob/77cb8f24c2381a8abb7272d7bbdec548d6426a8a/drivers/cpufreq/apple-soc-cpufreq.c).

The interrupted draft overstated two points. A requested command value is not
an independently measured rate, and an unknown boot state must not be reported
as the lowest OPP. It also read the unknown STATUS register at initialization,
allowed writes by default and reported dry-run transitions as successful.
Those behaviors are removed.

## Candidate behavior

* The module defaults to **no writes**. Target requests return `-EPERM`, so
  cpufreq does not record a transition that never happened. No dry-run success.
* A write-enabled load must explicitly specify both
  `ilinux_enable_writes=1` and a nonzero `ilinux_max_pstate`. Both parameters
  are immutable for that module instance (0444). There is no default high cap.
  The cap bounds requested states, not a pre-existing firmware frequency.
* Policy initialization requires J716c, t6050, exactly one online CPU and
  policy CPU 0. Every table state must be 2..31. An unknown current requested
  state logs the raw command then refuses policy creation with `-ERANGE`.
  It does not fabricate a clock rate to force initialization to succeed.
* Requests outside the cap, during APSC disable/busy or with another CPU
  online are refused. Existing command BUSY polling remains bounded at 400 µs.
  The masked update preserves unrelated bits. A bounded post-write command
  readback checks BUSY clear and the requested-state field. This can pass before
  an unobserved hardware transition begins; it proves neither completion nor
  the resulting clock rate. Failure
  after a write is reported, with no blind retry or automatic rollback.
* The experimental policy disables fast-switch. STATUS, PLL, voltage,
  cluster-init, reset-vector and idle registers are never touched.
* The driver's reported rate is an OPP lookup of the **requested state**.
  Firmware limits, thermal throttling, voltage setup or an unimplemented PMC
  floor may mean the actual rate differs. The existing transition latency
  property is a placeholder, not a measured t6050 latency.

The candidate DT changes exactly three controller `status`/`compatible` pairs
and 50 `opp-level` values. Every other property, including storage, USB, MTP,
CPU topology, timer and GPIO guards, is unchanged. It pins the boot042 DT
SHA-256 `17c55af9eb39ea799e254335176e9748193237dce3735f59cd286a63ea0a0405`.
The new single compatible is `apple,t6050-cluster-cpufreq`: removing the t8112
fallback prevents an old module selecting its unknown t6050 STATUS layout.
All three tables are prepared, but this driver only permits one online CPU;
no offline sibling cluster is exercised. Attempt 28 includes this exact candidate through its separate `cpu-observe`
profile; all earlier profiles continue to reject it.

`allowance_model.py` remains a historical unit-tested input-DT proposal.
The actual integrated gates are `native/boot/cpu_observe.py` and the explicit
profile in `launch.py`: exact payload pins, final prepared DT validation,
one-core/idle/storage/USB/MTP safeguards and a fixed userspace governor.
The shipping module is outside module autoload indices and loads only through
the bounded collector with `ilinux_enable_writes=0 ilinux_max_pstate=0`.
Job052 rebuilds the same driver source against boot042 and adds the collector
and short CPU/memory workloads to the exact attempt-27 root. It also repins
stage one. Its new module digest is in `native/boot/attempt28/assets.json`;
the job051 pins below remain the historical offline build, not the new image.

## Reproduction and validation

Host stdlib checks (read inputs, write only temporary workspace data):

```sh
python3 -I kernel/experiments/cpufreq-t6050/test_make_cpufreq_dt.py
python3 -I kernel/experiments/cpufreq-t6050/test_allowance.py
python3 -I kernel/experiments/cpufreq-t6050/test_measurement.py
```

VM job `virtualization/jobs/051-cpufreq-t6050/run.sh` builds an external module
against the exact existing boot042 tree, checks W=1 output, and runs the actual
extracted get/target callbacks with mocked MMIO under ASan/UBSan. Sixteen cases
exercise disabled writes, caps, CPU gates, unsupported states, APSC gates,
pre/post timeouts, field preservation, readback mismatch, unknown-state rate
and absence of STATUS reads. Six deliberately broken variants must fail these
tests (fake dry-run success, writes enabled by default, cap ignored, wrong
state encoding, fabricated unknown-state frequency and ignored readback). The source checks also enforce guarded SoC
selection, immutable parameters and refusal of unknown boot states.

The job runs the Python suites, compiles the candidate DT and validates the
narrow downstream cpufreq binding. Full-board schema cleanliness is not a
claim. It never loads the module or changes the kernel Image/config. Module
build results alone cannot validate Apple hardware, firmware constraints or
performance. The isolated build completed on 2026-10-19 at 23:26:57 Eastern (2026-10-20
03:26:57 UTC), exit 0: W=1 clean module, 16 ASan/UBSan callback cases, all six
regression mutants rejected, 12 Python test methods, dtc with no warnings,
and both schema-document and narrow cpufreq validation logs empty. The first
pass exposed a schema `$id`/path warning; the rerun stages the binding in a
matching path and treats any such warning as a failure. First-run logs remain
local. The Python tests retain the inherited ADT loader ResourceWarning; no
new shared-source changes were made to suppress it.

Build tools: GCC 16.1.1 (20260430), binutils 2.46.0, DTC 1.8.1, Python 3.14.8.
Target module vermagic: `7.1.9-g863199d8b4a3-dirty SMP preempt mod_unload aarch64`.
Full record: `validation.json`. Output pins:

* Module, 84,824 bytes: `97e358b27e94be5efd0d3d7d2c1c99ff314e22da9c2586de713dd8299ee17054`.
* Candidate DT, 63,383 bytes: `aa9731d1ba8246a9441a85dcbf59bf65cfe82c7a8d33439e9d2cdc40cb0ee725`.

**Native testing remains NOT RUN.** No module was loaded, and no hardware
frequency or thermal/power/efficiency result follows from these offline tests.

## Proposed measurement ladder, after a separate reviewed attempt

1. Preserve a clean one-core baseline. Record exact Image/root/module/DT hashes,
   power source, energy mode, CPU identity, online CPU list and idle args.
   Use the existing USB SSH channel; keep a log and a known return route.
2. Capture `measurement.py --samples 3` before any module load. It reads only
   CPU-policy/thermal sysfs and uptime, never `/dev/mem`. Missing power or
   thermal data is `null`, never a zero or a successful thermal check.
3. Load the experimental module in its default no-write mode only after the
   specific attempt permits it. Record the command value and policy outcome.
   If state/mapping/CPU identity differs from reviewed expectations, stop and
   analyze. Never rewrite unknown state to make it fit a table.
4. Before the first write, review the observed boot state and an explicit cap.
   Start at that verified state or a reviewed adjacent OPP, not the maximum.
   Unload/reload is needed to alter immutable parameters. Unloading does not
   restore a prior speed state. A default governor can request transitions at
   registration once writes are enabled; its requests remain cap-bounded.
   Select userspace at boot before registration, as attempt 28 now does; do
   not rely on changing governor after a write-enabled load.
5. Request a single reviewed state. Capture command readback separately
   from workload rate. Compare the existing `cpubench freq -t 1 -r 3 -s 0.2 -c 0`
   estimator (dependent ADDs, assumes one-cycle latency), an independent fixed
   instruction workload, and frame/update timing. Use identical compiler/flags,
   core and short workload in each A/B run; include a cooldown between runs.
   A PMU cycles/time reference, when validated, is stronger than the estimator.
6. Stop on timeout, reset, kernel error, keyboard/USB loss, unexplained slowdown,
   thermal anomaly or missing required monitoring. Do not extend to sustained
   high OPPs without reliable thermal/power observation and an explicit plan.
   Return through the established lab→Macintosh HD procedure if needed.

Keep `idle=nop arm64.nowfxt`, the one-core limit and the existing domain policy.
Frequency scaling does not repair idle state retention. An accepted request
plus throughput improvement establishes only that bounded configuration; it
is not measured efficiency, thermal stability, all-core readiness or parity.
Follow-up work is native state validation, dependable power/thermal telemetry,
SMP with the separately researched entry protocol, and graphics acceleration.
