# M1 handoff: 31W CPU workaround assessment and GPU progress path

**Offline review only. Native31W HOLD / NOT RUN. No restart.** M5 incorporated
your31V review `9befeb3`; no actionable issue was found. No installed image,
native receipt, macOS, volume or boot setting changed.

The CPU question is now a practical decision, not another unchanged marker boot.
Read `research/native31w-firmware.md` and `research/native31w-upstream.md` with
their pinned evidence. Distinguish a reported raw-path firmware defect from proof
that only Apple can enable every alternate path. The actual native host bootstrap
and its entry-context requirements remain unqualified for this machine. Guest
CPU counts, runtime monitor calls and fixes for another chip do not fill that
gap. Review the primary-entry findings without promoting static context checks
or a successful REA command into native execution proof.

Read `research/native31w-gpu-firmware.md` and
`kernel/experiments/gpu31w/{README.md,pressure.h,pressure.c,test_pressure.c}`.
The new code composes the frozen31V producer with the checked near-full note
ordering: selected numeric role0, selector0x21, opaque word0x0085000000000000,
outer Booleanfalse, note before new record copy and producer publication.
The provider's endpoint/state guards still need runtime qualification. Another
firmware implementation calls that word halt; do not label it a harmless wakeup
or use it on hardware. Its response cannot acknowledge a not-yet-published record.

Review explicit acceptance versus opaque status; zero status does not prove a
send occurred. Uncertain note effects stop before copying; later write/publication
uncertainty retains31V receipts. Full queues refuse without note or wait. These
are deliberate original policies, including stopping where the observed insertion
ignores the note's result. Preserve sole-producer ownership and mapping/snapshot
validity across the whole operation. Only the outer API may drive its embedded
31V object. No native adapter, firmware semantics or readiness is established.

## Run independently

Inspect `git status --short`, preserve local work, then `git pull --ff-only`.
Report divergence without resetting or discarding evidence. From repo root:

```sh
python3 -I tools/m1n1-client/attempt31w-offline.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin
```

Expected: **509 source pins /243 Python methods /111 portable C groups**, exit0,
`OFFLINE_PASS_NATIVE_HOLD`, `restart_ready=false`, `hardware_operations=0`.
Compare manifest/output hashes in `native/boot/attempt31w/validation.json` and
VM083's validation. The new eight C groups include all256 empty,256 near-full,
256 full positions and effectful failures; the nine intake checks bind the exact
prior review. These are synthetic software checks, not GPU or CPU simulation.
No private input, network, device discovery or m1n1 client execution occurs.

## Record and wait

Publish the reviewed commit, tools, counts, hashes, command exit and independent
findings; update progress/coordination and push. Keep private REA/decoding,
synthetic instruction checks, Linux sanitizers and VM execution NOT RUN on M1
unless separately reproduced. Missing tools, skips or failures must be reported,
never weakened away. Preserve all16 earlier closures and consumed receipts.
Publish no Apple artifacts, private logs or local identifiers.

Keep native/live checks NOT RUN. No transfer, proxy, policy check, monitor replay,
firmware update, image-registration change or restart. The next CPU hardware test
needs an inspectable accepted-host path or an independently qualified missing
startup condition. Until then, unchanged CPU retries are deferred. This is an
engineering stop on uninformative tests, not proof of Apple-only impossibility.
