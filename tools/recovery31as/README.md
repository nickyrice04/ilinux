# 31AS: remove the unavailable Recovery comparator

The actual 31AR paste stopped before its controller because `/usr/bin/cmp` was
unavailable. Neither installation nor rollback ran. Macintosh HD desktop and
default return were human-confirmed; boot021 restoration remains outstanding.

This new source-only adapter preserves all 162 frozen 31AR inputs and proves
four reversible substitutions in each complete operation block:

1. Check executable availability of the fifteen fixed shell/native tool paths
   before any scratch creation or controller call. Missing tools produce a
   finite dependency-refusal record naming only the fixed public tool path.
2. Keep the existing SHA-256/shasum/OpenSSL preference, but explicitly check the
   producer exit before returning a digest. Parse with Bash builtins, removing
   the awk dependency. Require exactly 64 lowercase hexadecimal characters.
3. Replace the first cmp call with exact profile mode, length and pinned SHA-256
   checks for both the embedded expected profile and the staged profile.
4. Replace the copied-profile cmp call with the same exact profile checks.

There is no cmp fallback or renamed comparator assumption. A producer returning
the correct digest with a nonzero exit is refused. These hashes provide the
same cryptographic binding already used for the artifacts; native profile/self
binding remains intact. The complete blocks otherwise reverse byte-for-byte to
the frozen renderer.

The original helper (125168 bytes), profile (823 bytes), candidate, boot021,
`ilinux31ar.` scratch prefix, `31ar-kit` and `ilinux31ar-state` remain unchanged.
Restore still does not require the candidate file. Native result labels remain
31AR intentionally. The new page title and route identify the repaired wrapper:
**31AS Recovery profile verification**, `/31as`.

## Inert preparation and review

```bash
python3 -I tools/recovery31as/package.py --prepare --output build/31as-page
python3 -I tools/recovery31as/package.py \
  --page build/31as-page/recovery.html --check-only
python3 -I tools/recovery31as/test_package.py
```

Default/help, prepare and check-only never stage files, dispatch a controller,
query host hardware or open a socket. No staging mode exists. Output refuses
existing directories. The 167-file closure contains all old 162 files, their
unchanged inventory and the four new adapter/test/doc/handoff files. The public
offline-verification receipt is excluded from its own input closure.

An explicitly requested later bounded page service uses `--page`, an explicit
private `--bind`, `--port` and `--seconds` of at most 1800. It serves only the
reviewed fixed page, with no downloads, uploads, directory listing or shell API.
Private URLs and process details stay out of Git. No server runs during tests.

## What the tests establish

The executed shell harness maps every absolute utility path to original
workspace fixtures. It verifies genuine production helper/candidate/boot021
bytes as data, but intercepts both controller invocations with a deliberately
synthetic fixture. No real controller, mount, policy or Apple writer runs.
Positive install and candidate-free restore reach only that fixture without cmp
or awk. Each hash branch, nonzero producer with correct output, malformed digest,
profile/artifact corruption, symlink profile, missing hashes and each missing
required utility are checked. New source/whole-box/route/preparation checks are
separate from the shell controls. Missing production artifacts cause an explicit
skip on a review machine, never manufactured matching bytes.

Actual 31AP demonstrated at least one branch of the retained hash preference;
it did not qualify every alternative. Availability preflight proves only an
executable path exists, not runtime behavior, authentication, Recovery ABI,
APFS RW transitions, native entry, SMP or performance. Those remain physical
observations. No macOS or firmware update is performed or required by this repair.
