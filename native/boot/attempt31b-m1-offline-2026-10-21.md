# Attempt31B — independent M1 offline readiness

**OFFLINE READY, 2026-10-21. Native/live, CPU1 starts and hardware writes NOT RUN.**

M1 pulled **`7d505fd`**; all **36** new source pins, boot042's **13** files,
exact boot021/192-byte helper/offline controller and clean client `57a9339`
PASS. **46 Python methods PASS** (19 controller, 3 supervisor, 11 census, 5 audit,
8 renderer), zero skips/fixes. No live-use receipt existed before/after tests;
no USB, target allocation or start. Native31B/hardware writes/CPU1/Linux SMP
**NOT RUN**, live attempts 0. Human reports M1 restart/M5 Running proxy and
confirms cable/power/unlocked/lid/90s timer. Publish readiness before one
supervised CPU1 entry/two-request test. Existing boot021, macOS/default/security/
volumes unchanged; routine policy checks waived. No Linux continuation or retry.
Evidence: `native/boot/attempt31b-m1-offline-2026-10-21.md`.

## Verified inputs and required checks

* Handoff revision `7d505fd`; no local tracked work was changed by the pull.
* All 36 entries in `attempt31b/source-sha256.txt` match; reviewed the 449-line
  controller, 192-byte original helper, 79-line supervisor, unit tests, static
  layout audit and M5 validation. Default controller verifies the complete
  boot021 image/helper and eight text-relocation literals without USB access.
* Boot042 package manifest SHA-256
  `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd`, 13 files.
  Existing 3,932,160-byte m1n1 image
  `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`;
  clean client `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
* Controller SHA-256
  `9fea909adeb0bdef74a5c544af6c0b95f1ecda4740a95d4ff683c91238a6bced`;
  supervisor `2f66b7d0d51ffaaeef0dbe55b02c00e49fa45e9f3f5b27027d86b6514d2eb6aa`;
  helper `dc046b303191b9a4fcb26a9e689fa4ec7b936dd1ae67dc5fd9b81c4edf4bf8aa`.
* Exact offline message:
  `OFFLINE PASS: boot021 and helper verified; no USB, allocation or CPU start`.
  No image download/transfer, new VM, host install or helper execution on M1.
* `supervisor-once.json`, `consumed.jsonl`, `controller.json`, `controller.stderr`
  and `supervisor-result.json` absent before and after tests. No evidence reset.

| M1 suite | Methods PASS | Skips |
|---|---:|---:|
|Controller |19 |0 |
|Independent supervisor |3 |0 |
|Unchanged census |11 |0 |
|Static layout audit |5 |0 |
|Renderer regression |8 |0 |

All seven requested subprocesses exit 0; no failures, skips, fixes or native
mutations. Supervisor tests launched and terminated only their own dummy
children. Temporary test data stayed under ignored build. A bounded caffeine
assertion is owned for this session. M5's separate GCC/Clang helper equivalence,
actual ARM64 helper, pinned-client serialization, normal/sanitized secondary
loop and real parser VM checks were read as offline evidence, not rerun or
relabeled native. Rejected REA pseudocode was not used as implementation.

## Authorized next step and limits

The human already reported restarting M1, booted the existing lab to Running
proxy, and confirmed direct cable/power/unlocked/open-lid/90s timer readiness.
Publishing this report precedes the authorized live supervisor. Live attempts 0,
no real receipt, hardware writes/CPU1 entry/Linux **NOT RUN** at this milestone.

One run only: fixed supervisor 65s, controller 60s, serial 2s, arrival 3s and each
request 1s, with independent human 90s timer. Controller reserves durable state,
checks exact identity/topology/relocated code and fresh RAM, then allocates
16 KiB, uploads the 192-byte helper and prepares CPU1's existing dedicated stack.
WFE is selected while no secondary is alive; two CPU1 start-register writes
follow. It verifies identity/arrival, two timer completions and final parked
state. It is not read-only hardware; inherited secondary initialization writes
architectural CPU state. No other core or Linux boot is included.

Post-start RAM reads/request publication avoid global exception-guard mutation
and counter clearing; no installed unbounded SMP call or generic CPU stop.
Record attempted versus acknowledged mutations without assuming a lost reply
means zero writes. Keep allocations/stack reserved until human power-off;
no rollback, target cleanup, retry, reconnect or gate edit. Return immediately
after PASS/STOP/deadline. Full Security/default/volume/settings remain untouched;
routine policy checks stay waived. Success is a bootloader request path only,
not Linux SMP, timer IRQ/IPI/coherency, stability, renderer, frequency, energy
or macOS-parity evidence. Old copy31/full-image candidate remain held.
