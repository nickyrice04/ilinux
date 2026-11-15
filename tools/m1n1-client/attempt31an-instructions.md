# M1: 31AM result accepted; review 31AN offline only

M5 reviewed the physical report in commit `2a28915`. Read-only Preboot
mount/verification/cleanup passed. The unchanged collector then refused lab
policy at `UNSUPPORTED_METADATA`, before a snapshot or native admission.
The exact tag remains unknown. Macintosh HD desktop/default return is
human-confirmed; Original Full Security remains required and unchanged.
Boot021 restoration is still outstanding. Do not describe it as completed.

## Current assignment

Review only the new desktop observation tool and sanitized analysis:

- `tools/policy31an/probe.py`, `test_probe.py` and `README.md`;
- `research/attempt31an-policy-schema-2026-11-14.md`;
- `native/boot/attempt31an/`.

The tool is for the owner's current M5 macOS desktop. **Do not run its live
mode on M1.** M5 requested local administrator authentication there; that
observation is pending. No raw policy, identifier or proprietary diagnostic
is to be shared. The tool emits only the finite redacted JSON.

Verify the three new source hashes and retained 111-source inventory. If an
independent M1 test run is useful, run the 20 focused synthetic controls once:

```bash
python3 -I tools/policy31an/test_probe.py
```

M5's producer and independent auditor already passed those 20 methods. Do not
repeat old native/capture suites, builds, staging or artifact transfer. Check
in particular that imported source is hash-checked before execution, unknown
names and scalar values cannot reach output, reads are bounded, identity is
observed freshly afterward, and the CLI does not change parser acceptance.

Record any review findings and distinguish synthetic tests from live evidence.
No page server, camera, proxy, M1 restart, Recovery visit, mount, installation,
rollback, Startup Disk or security change is requested. Old receipts, source,
profiles, kits and state stay frozen. No new native window is ready.

## What happens after the desktop observation

M5 will qualify the actual rejected field before implementing a narrow typed
reader extension. The successful 31AM Preboot engine is retained. Unknown
fields are not ignored and existing safeguards are not weakened. A future kit
and handoff will explicitly state what it can test; this document authorizes
no physical operation and is not another boot instruction.
