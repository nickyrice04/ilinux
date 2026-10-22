# M1 now: host-only discovery diagnosis; do not restart M5

31I is consumed. **Native31J HOLD / NOT RUN.** This handoff is safe to complete
while M5 remains in Macintosh HD. No boot, Recovery, security, image transfer,
serial open or target request is needed. Do not rerun any consumed supervisor.

Preserve local work, pull main with `git pull --ff-only`, stop on divergence.
Read `research/native31j-host-discovery.md` and record the revision. From repo root:

```sh
shasum -a 256 -c native/boot/attempt31j-host/source-sha256.txt
python3 -I tools/m1n1-client/test_usb_discovery31j.py
python3 -I tools/m1n1-client/usb-discovery31j.py
```

Expect 6 manifest entries and 19 tests to pass. The separate M5 validation
record includes 16 passing historical USB identity tests and one actual cached
registry query; it does not substitute for this M1 check.

Run the last command once. Report its exit code and complete sanitized JSON,
plus test count and pin-check outcome. Do not copy raw `ioreg` output, callout
paths, identifiers, stdout/stderr from the underlying command, or tracebacks.
The diagnostic itself only emits fixed fields and counts; unexpected failure
is a stop for M5 review, not permission to repair settings or guess a port.

Default diagnostic completion is not proxy readiness. With M5 in macOS, zero
matching primary interfaces is expected; exact empty stdout also has its own
category. Distinguish empty output, malformed plist, valid empty registry and
absent/ambiguous/stale primary metadata. Never convert an error to a PASS.
`native_ready:false` is intentional in every result.

Do not use `--require-primary` as a reason to boot M5 now. That diagnostic mode
will be used only in a later released fresh-proxy procedure, before any native
experiment is consumed. It verifies metadata and lstat but performs no handshake.

Publish a short `native/boot/attempt31j-host-m1-...md` report and sanitized JSON,
update progress/coordination, and push. Keep native31J/CPU1/Linux SMP NOT RUN and
31I receipts/sources intact. Then wait for M5's separately reviewed controller
handoff; no new native boot is ready from this host-diagnostic commit alone.
