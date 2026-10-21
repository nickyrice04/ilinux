# 31D review: isolate diagnostic console waits, retain CPU1 progress

M5 offline preparation PASS; M1 independent intake pending. Native 31D NOT RUN.
31C is consumed and its source/evidence/receipts remain frozen.

The next experiment addresses a real unbounded dependency in installed
boot021's early secondary code. It is a testable cause of 31C's timeout, not
a confirmed diagnosis. See `reverse-engineering/findings/cpu-startup-2026-10-21/`.

## Exact change from 31C

`native/boot/smp31d.py` subclasses the frozen 31C controller. Before allocating
it checks direct USB proxy identity and that both diagnostic UART RAM base
variables contain zero or their exact translated ADT addresses. If both are
already zero, it refuses: repeating the experiment would not test this hypothesis.
After the existing helper/CPU1 RAM setup, it zeros both variables and cache-cleans
each 8-byte range to PoC. No UART flush is called. Readback must be zero.

The compiled zero-base path returns before peripheral access. Every changed
RAM word is inside the pinned loaded image's BSS, outside code/boot/security
storage. The cache operation covers the enclosing hardware cache line; all
this occurs before CPU1 start. USB/framebuffer device configuration and the
active proxy variable are untouched. Muting low-level diagnostic UARTs reduces
that fallback logging for this session, including any early CPU1 fault output.
USB controller results, the human timer and available exception counters
remain, but faults before exception-vector initialization may be invisible.

After start intent, it adds only reads of CPU1's existing reset record via
the unchanged guard-free helper. The observed stages are saved as classifications
without addresses or raw memory. Sequential reads may see the intermediate
stack-before-MPIDR publication. Missing records do not prove no instructions ran.
Timeout snapshots retain the last successfully sampled stage, not a final
post-timeout or atomic state. Receipt journaling happens only on stage changes.

No installed code/RVBAR change, cluster power control, additional core, CPU
frequency change, timer IRQ/IPI test or Linux boot. The two CPU1 startup writes
and the two bounded timer requests are unchanged. Successful full run: 15
mutation requests (11 prior + 2 RAM writes + 2 cache cleans); arrival timeout
after both starts: 13. Intent counts do not prove operation completion.

## Validation and remaining limits

Job 061: 73 Python methods PASS, actual pinned-client serialization and real
BootArgs/ADT parsing at M5 addresses PASS (success and partial-timeout paths),
compiled public-source UART harness 9 cases PASS normal and ASan/UBSan. New
host controller methods 10 PASS; exact image/source audit PASS. Initial VM
harness compile stopped on GCC's longjmp/clobbered warning; fixed the harness
loop variable with `volatile`, kept `-Werror`, and reran successfully. No live
controller or hardware operation was invoked. Detail: `validation.json`.

The source harness substitutes MMIO, and the controller fixture simulates
startup/cache publication. Neither exposes Apple CPU reset, actual UART FIFO
state, WFE, exception levels, cache visibility or PMGR behavior. New REA is
static evidence only. No performance gain or native CPU1 success is claimed.

## Next gate

M1 verifies the new manifest/package, runs its offline tests and publishes
readiness. Then the human authorizes **one** 31D start with a new receipt and
timer. Existing boot021/Boot Lab only; no files to AirDrop. Immediately after
any outcome return to Macintosh HD. No automatic Linux continuation.
The existing independent 65-second supervisor and 90-second human timer remain;
USB read/write 2 s, controller 60 s, arrival 3 s, each timer request 1 s.

If successful, two-core Linux validation and renderer threading are next,
followed by expansion across clusters. Efficient idle, GPU acceleration,
networking, storage and measured energy/performance remain separate work.
