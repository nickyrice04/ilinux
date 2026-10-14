# Stage B attempt: preflight stopped; Linux NOT RUN

Session: 2026-10-13 local (America/New_York), 2026-10-14 UTC.
One attempt authorized by `b06c56e`; controller readiness published as `fff8b95`.
Execution commit: `fff8b95005cb5d581f2e3ad6877611de52e23413`.

## Observed result

* Start UTC: **2026-10-14T01:38:53.644283+00:00**.
  End UTC: **2026-10-14T01:38:54.779211+00:00**.
  **Exit 1, elapsed 1.135 seconds**, no retry.
* Package checks and unique primary USB identity passed. Target preflight
  passed **t6050 chip, packaged m1n1 marker and no started secondaries**.
  Live packaged-marker verification is therefore now **PASS**, not NOT RUN;
  this is the specified marker check, not a full runtime binary attestation.
* Last checkpoint: `Target PASS: t6050, packaged m1n1 marker, no started secondaries.`
  Next result: **KeyError** before board/framebuffer PASS, payload upload or
  handoff. No kernel/PID 1/CPU/liveness result exists: **Linux NOT RUN**.
* User saw “heap limit.” Pinned `src/heapblock.c` prints this normally from
  `heapblock_set_limit`; exhaustion uses a different panic message. RAM utility
  initialization is part of the approved preflight and can set a heap limit.
  Do not label the session read-only or infer an out-of-memory failure.
* User confirms return to the usual **Macintosh HD desktop** after the guided
  power-off/picker return. Fresh post-attempt build/default/protection checks
  have not been reported. Earlier Full/Permissive/protection results are baseline.
  No volume/security changes were requested or performed by M1.
* The controller cleanup path closes its transport; no close error was reported.
  No port was reopened during investigation. Boot021 and clean client pin
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba` remain unchanged.

Local sanitized evidence remains ignored at
`build/native-intake/results/boot021-stage-b-authorized.json` and `.md`.
The controller output filter retained exception type but not the raw KeyError
argument/traceback. No target ADT, raw registry, serial-containing path or
photograph was saved. This limits certainty about the precise live throw site.

## Offline finding and narrow fix

**Confirmed defect:** `launch.py` accessed `utils.adt["/"].compatible`.
In pinned `proxyutils.py`, `LazyADT` already wraps the root. In `adt.py`,
`ADTNode.__getitem__` strips slashes and searches children; `"/"` becomes an
empty child name and raises `KeyError: Child node '' not found` for a normal
root. Root properties must be read as `utils.adt.compatible`.

The old dictionary-based test double incorrectly supplied a `"/"` key, hiding
this API mismatch. A new regression uses the actual pinned `LazyADT`, binary
ADT decoder and PMGR initialization with wholly synthetic bytes and fake
transport. It reproduces the old lookup error before the fix. After the fix,
a matching board can continue through the fake session, while a wrong or
missing root compatibility stops before payload upload. Scalar/substring board
matches are rejected. No target/secondary/framebuffer/DT checks were removed.
Two sanitized checkpoints now distinguish RAM utility setup from root ADT access.

**Likely explanation of the live failure:** this root-lookup defect occurs at
the observed checkpoint and reproduces its exception type. Without the saved
live argument/traceback, an earlier ADT-decoding/PMGR KeyError cannot be ruled
out. The offline fix is not hardware-verified and does not prove Linux will boot.

## Validation and handoff

* **31 launcher tests + 4 new pinned-ADT tests PASS**, all offline.
* Actual unchanged boot021 package verifies in offline launcher mode, exit 0.
* The 20 USB and 7 intake cases passed at readiness; those components are
  unchanged and were not redundantly rerun during this board-gate fix.
* Upstream checkout remains unmodified at the agreed pin. Only the local
  launcher/test/docs changed. Do not rebuild/reinstall the boot object.
* M5 agent: review the failure and offline correction, and perform planned
  read-only return checks. Current direction is **no retries**. Any future
  attempt needs a new user instruction and a fresh evidence record; this
  consumed session must not be reused. Linux remains **NOT RUN**.
