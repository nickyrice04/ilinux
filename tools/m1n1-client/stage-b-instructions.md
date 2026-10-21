# Current native handoff — 31B CPU1 entry and request test

Read [attempt31b-instructions.md](attempt31b-instructions.md).
M5 offline preparation passes; M1 must verify the new source pins, retained
boot042 package and tests, publish readiness, then wait for the human start.
**Native 31B is NOT RUN.** Census 31A is consumed; do not replay it separately.

Use the existing Boot Lab/installed boot021. A small RAM-only controller starts
CPU1 once, verifies entry and two completed requests, then the human returns
to Macintosh HD. No Linux launch, new root/image transfer, chainload,
installation or security/default/volume change. Routine policy checks waived.

The new controller uploads a 192-byte original helper to an allocated 16 KiB RAM
block and issues two CPU1 start writes. It is not a read-only census. The old
copy-only 31 pair/profile and rebuilt m1n1 candidate remain held. Successful
bootloader entry does not establish native Linux SMP, speed or efficiency.

Use `native/boot/attempt31b/source-sha256.txt`. The 31A manifest remains historical
and intentionally pins an older version of this pointer; do not regenerate it.
