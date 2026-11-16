# M1: matched J716c source/build review, offline only

This follows the accepted 31AX review `ee4f70c`. Preserve that controller and
all prior closed/consumed transaction evidence. Do not start a page server,
restart either Mac, enter a proxy session, stage a kit, query policy or run a
firmware/boot installer. Prior boot021/Original desktop/default confirmations
stand; no repeated manual security check is requested.

The current task adopts the community's **exact J716c** integration, rather
than repeating old single-core or unaccelerated-stack experiments. Read:

- `native/stack/j716c-community/README.md` and `manifest.json`;
- `research/attempt31ay-firmware-2026-11-15.md` and its evidence JSON;
- `research/attempt31ay-installer-availability-2026-11-16.md`, distinguishing
  Apple's public board advertisement from actual signing/installer verification;
- `research/attempt31ay-stage1-storage-2026-11-16.md`, distinguishing blank
  proxy mode, NVMe/FAT loading and unqualified partition-free RAM options;
- jobs `096-j716c-community-kernel` and `097-j716c-community-graphics`, their
  source-admission rules and the new reproduction receipts named in the status
  documents. Distinguish actual builds, partial builds and blocked tests.

Actual results: kernel build PASS (1,749 modules); both Aura variants and full
Mesa compilation PASS. Untouched Mesa tests are 175 PASS/4 FAIL, from a stale
transfer-capability assertion. The separate test-only correction is 179/179
PASS, with CPU BGRA/RGBA round trips and no shipping-driver change. Read its
`kernel/experiments/j716c-mesa-blit-tests/` findings. Keep baseline and derivative
counts separate. The source-build DESTDIR is not a drop-in Omarchy package.

Run only the lightweight new pure tests with an installed Python:

```sh
python3 -I native/stack/j716c-community/validate.py native/stack/j716c-community/manifest.json
python3 -I -m unittest discover -s native/stack/j716c-community -p 'test_*.py' -v
python3 -I -m unittest discover -s tools/firmware31ay -p 'test_*.py' -v
python3 -I -m unittest discover -s virtualization/jobs/096-j716c-community-kernel -p 'test_*.py' -v
python3 -I -m unittest discover -s virtualization/jobs/097-j716c-community-graphics -p 'test_*.py' -v
```

Verify the 63 `source_sha256` entries in
`native/boot/attempt31ay-offline-2026-11-16.json`, the component producer bindings
and the 22 unchanged AX pins. The four lightweight groups total 99 methods on
M5. These are new tests; replaying historical transaction suites is unnecessary.

The firmware tests are fake-API/pure-byte tests. Do not invoke its live reader
on M1: that would inventory M1, not qualify M5. Do not install or execute the
ALPM hook templates on either macOS installation. Actual ALPM runtime and
physical watchdog renewal are separate from these pure decisions.

Review these boundaries independently:

1. Kernel `a59e709c`, full config `3c11e751…d7dbe8`, matching Image/modules/DT,
   Aura graphics `9da61857` and Mesa `10161a78` remain a coherent pinned set.
   A partial build or matching version label is not a successful whole build.
2. A source-built generic Stage1 is a new candidate. It does not establish the
   publisher's installed Stage1 identity, successful enrollment or current
   firmware bootability. Retain its Mach-O/kcbz/window/path checks.
   Its factory configuration is blank/proxy-only. An ESP boot path cannot read
   Stage2 from Lab APFS Data; matching RAM-chainload or direct-composite options
   require their own transport/ABI/layout qualification.
3. Publication Image/package hashes are historical identities, not claims that
   our outputs match. Distinguish repository checksum/PGPSIG-byte comparison
   from actual cryptographic signature verification and key-trust provenance.
4. The M5 observation admits only current **system** `mBoot-20457.1.29`; running
   OS firmware and Lab firmware remain unknown to the narrow reader. GPU/DCP
   consume the selected OS firmware and their loaded-image identity checks.
   The publisher's `20457.41.3` is not a separately published two-layer inventory.
5. The required OS firmware baseline is 27.2.1/26B131. Updating Original alone
   does not qualify Lab; refreshing Lab can still update shared firmware.
   Exact supported installer availability and transition/rescue must be settled
   before the owner is asked for a concrete update decision. No update is
   authorized, and Macintosh HD must remain at Full Security.
   The inspected community automatic updater is unfinished and its policy
   excludes this exact board/build. Do not run it or substitute the Pro recipe.
6. Foreign per-unit DT/DROM and Apple firmware stay out of public artifacts
   and deployment. J714s/K114s hardware profiles are not J716c profiles. Private
   local firmware provisioning, new root/module integration, runtime DT gates,
   guardian and manual rescue remain explicit deployment requirements.
7. The initial J716c ALPM guard freezes critical packages and paths with no
   guessed version allowance or environment bypass. It prevents accidental
   update replacement, not arbitrary package scriptlets/direct root writes.
   Do not confuse it with the physical-watchdog guardian.
8. The reference's approximately 2 GHz ceiling, checked temperature, firmware
   fan control, default-off shallow WFI, disabled RTC/external ATC2 and
   unqualified suspend/USB remain visible. Source/build success is not native
   CPU/GPU operation or macOS performance/efficiency parity.

Already-held genuine build artifacts can be compared to their receipt hashes;
otherwise explicitly mark artifact-byte verification NOT RUN. No automatic
large download or VM rebuild is requested on M1. Report actionable source or
recipe findings and the exact tests run. Keep native Linux/SMP/GPU/performance,
firmware transition, enrollment, live reset/rescue and current policy claims
NOT RUN. The next owner proposal should be one complete matched deployment and
informative RAM-root acceptance test, after the remaining concrete gates close.
