# 31AC: prepared native acceptance test

The original image and exact boot021 rollback are pinned in `manifest.json`.
The archive contains only original project/open-source artifacts and their
licenses. Download it as data; bind it to this independently reviewed Git
revision before extraction or native use.

From the repository root, with existing Python:

```sh
shasum -a 256 -c native/boot/attempt31ac/source-sha256.txt
python3 -I native/boot/attempt31ac/verify.py \
  --archive build/ilinux-31ac-entry-test.tar.gz
python3 -I native/boot/attempt31ac/test_verify.py
```

The verifier reads the archive without extraction or execution and checks all
members, sizes, hashes, namespace, duplicate/link refusal and checksum inventory.
The manifest itself is trusted through the reviewed Git commit, not through a
copy downloaded alongside the archive. Successful delivery does not authorize
installation or establish firmware acceptance.

M1 follows the [complete review and Recovery sequence](../../../tools/m1n1-client/attempt31ac-instructions.md).
The test requires a separately approved, temporary replacement of the lab's
custom boot object, a bounded screen observation, and exact boot021 rollback.
Original macOS stays intact and Full Security. No new volume or security downgrade
is part of the plan. The candidate does not start Linux or a secondary CPU.

The [validation receipt](validation.json) records the complete26-case execution,
tool versions, image-format result, source bindings and remaining native unknowns.
An unmistakable marker establishes entry reached its store/display path; it does
not prove final cache-clean/park completion. A blank result remains inconclusive
between acceptance, profile, input, mapping, fault and visibility failures.
