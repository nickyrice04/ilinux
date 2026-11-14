# 31AJ portable closure correction

M1's review at `8352602` passed the four artifacts, 247 focused methods, display
assertions and exact rendered shell/HTML bytes. It found one delivery defect:
the original 57-entry source inventory accidentally required an ignored local
test executable. That executable is neither source nor a fifth delivery file.
The original inventory, all its original member files and its preparation
receipt are preserved. `producer-output.json` records the executable's hash as
producer evidence only. No candidate, helper or Recovery command is rebuilt.

The new `source-sha256.txt` retains all 56 portable original bindings unchanged
and adds only the new portable adapter, tests and handoff documentation/evidence.
The producer executable is excluded by exact identity, not a general skip rule.
Every new required file comes from Git. The four delivery files remain the
same 36 MB `build/ilinux-31aj-review/` folder already verified on M1.

`tools/recovery31aj_portable/adapter.py` selects this new fixed inventory for the
frozen lab stager and page server. It verifies original source hashes before
loading code. It changes only the inventory selector; fixed hardware/volume
targets, no-overwrite behavior, artifact pins, policy and transaction guards
remain those reviewed on M1. Default invocation cannot stage or start a server.
The original `prepare.py` already accepts the new inventory explicitly.

Validation reconstructs a clean Git-delivered workspace, confirms the producer
executable is absent, and provides exactly the same four delivery files. It then
verifies every portable source, performs actual intake/materialization/page
preparation and checks the real page without opening a socket. The canonical
profile, install block, restore block and HTML must retain all four previously
reviewed hashes. `clean-export-verification.json` and `page-preparation.json`
are generated receipts excluded from the input inventory to avoid a hash cycle;
Git records them separately. The unchanged M1 tests and artifact review are
reused rather than rerun.

This correction qualifies portable preparation only. Lab Data staging is a
separate operation after the corrected closure passes, under the user's current
conditional authorization. It copies only the four prepared files into the new
lab kit directory. It does not install a boot object or select Startup Disk.
Actual Recovery admission still happens before any enrollment write. Macintosh
HD must remain Full Security. No restart follows a failed or unconfirmed stage.

Current handoff: `tools/m1n1-client/attempt31aj-portable-instructions.md`.
