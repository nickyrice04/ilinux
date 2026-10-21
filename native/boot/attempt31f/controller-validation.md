# 31F offline validation — 2026-10-21

**Offline implementation/review PASS; native31F, CPU1 entry and Linux SMP NOT RUN.**
M1 must complete the current intake before the human starts the existing lab
entry. All hardware operations in this preparation were zero. macOS, boot
objects, policies, volumes and the pinned client were not changed.

## Reproduction and evidence

The original job `virtualization/jobs/064-smp31f/run.sh` ran in the existing
isolated ARM64 VM: 12 vCPUs, 24 GiB RAM, Linux7.1.6-vzrun2, Python3.14.8,
GCC16.1.1 (20260430), Clang23.1.1. Guest start/end: 2026-10-21T23:04:10Z to
23:04:15Z, **guest exit0**, all final markers PASS. This is offline correctness
validation, not a native timing or energy benchmark. Outputs stay in ignored
`virtualization/jobs/064-smp31f/out/`; sanitized hashes are in `validation.json`.

| Check | Result |
|---|---|
| Full-symbol intake in ARM64 VM | 217 distinct Python methods PASS, no skips |
| Same full-symbol intake with own stdlib models on host | 217 PASS |
| M1-style image-only intake on host | 194 PASS; full-symbol checks explicitly NOT RUN |
| Source/fixture closure | 138 pins PASS; independent import/file-access audit found no missing executed dependency |
| Controller with real pinned BootArgs/ADT parser | 19 methods PASS (same methods repeated with real parser) |
| Real M1N1Proxy wire integration | EL1 success, EL2/VHE success, partial timeout PASS; 12 malformed/forbidden packets rejected |
| Recorder instruction model | 23 methods, 13 scenarios, 160 NZCV variants, 332 instruction-boundary fault stops PASS |
| Telemetry publication model | 29 methods, 2,376 supported +462 unsupported interleavings PASS |
| Controller mutation fault matrix | 213 cases: before/trap/lost-reply-after each of 71 intents PASS; no retry |
| Supervisor | 15 methods PASS, including actual bounded original dummy children |
| New permission binding | 11 methods PASS; hook0, final body word0xaa4, all16 probes |
| Topology and read-only Linux collector | 32 methods PASS; both exact retained boot042 DTBs structurally PASS |
| GNU and Clang independent assembly | Recorder, frozen permission tail and frozen startup helper byte-identical to original Python encoders |
| Ordinary first-frame store | Four cases each in GCC, Clang and GCC ASan/UBSan builds PASS; no privileged native reset execution |

Counts distinguish unique test methods from additional integration executions.
The successful controller path has71 mutation intentions; a normal timeout
after publication and both starts has63. Sampling between the two starts adds
reads only. Any early progress/error stops before the second store. Recorded
intent is not proof of an acknowledged or completed operation.

## Exact bindings

- Existing boot021: 3,932,160 bytes,
  `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
- Full symbols: `751a9643a2196eda44efba4789aa789465b2b75e9546be460946d2fa4c70ac11`.
- Client/source: `57a9339ffd1876e78297b17d34dece8cff8fa1ba`, clean checkout checked
  before importing it inside the VM. No third-party client execution on M5 host.
- Original recorder: 168 bytes,
  `52f9d1b312725cdc9261e0fbf1c31991e9078a663827734b9ba54c9d171106bc`.
- Existing 160-byte permission helper:
  `44dfcab7a9c4aa49f7e18b4e635061f2c3f5da2bf1b928862785e8bd485ca0db`.
- Existing 16-byte startup helper:
  `7d94bfad2f4b776492b17a5c594fc0aefff7ceb865e289401dabc42a27de3e3f`.
  Its internal return marker remains0x31e; both the tested controller and
  assembler bind that unchanged helper rather than changing its bytes.

## Review and limits

Independent entry review, startup review and controller/supervisor review are
adjacent. Review added two useful stops: observe immediately after the first
startup store, and classify unsupported EL explicitly. Local tests caught an
accidental inherited helper-return expectation before any native run; it was
corrected to match the unchanged independently assembled helper.

The public bootloader audit identifies the recorder's pre-store identity filter
as an information gap; it is not a proven hardware root cause. Earlier REA found
no evidence for extra CPU1 power operations, so none were added. No proprietary
code, pseudocode, binaries or raw diagnostics are published.

VMs and the narrow instruction model cannot prove Apple's reset routing,
firmware behavior, secondary-cache visibility, coherence, interrupts or native
SMP. Vector+0 also serves a synchronous exception slot. A marker is not reset
provenance; a complete record is not arrival; callback round trips include USB
and host overhead and are not CPU performance measurements. No throughput,
latency, thermal or efficiency gain is claimed.

Topology confirms12 Performance +6 Super, three six-wide clusters. DT capacity
768/1024 and power coefficients are **UNCALIBRATED**; both source DTs preserve
identities, but native online CPUs/frequency domains must be measured later.
