# M1 offline intake — attempt 27 two-stage delivery

2026-10-20. Reviewed handoff **`4b63b82`** (includes published `37fd9b5`).
**Both transferred files PASS. Offline intake complete with test limits below.**
Native attempt 27, live checks and stage-two transfer are **NOT RUN**.
Keep the M5 in macOS until fresh preboot prerequisites and human start.

## Verified files

Both files arrived at the repository root. Verified their size and SHA-256
against the published records, then renamed them into ignored `build/attempt27/`.
Prior images were preserved; neither file is tracked or published.

| File | Bytes | SHA-256 |
|---|---:|---|
| `stage1.cpio.zst` | 59,630,835 | `84c01f536516b85939f6ead55e37d0a9fa4838414edb84e033aef221f6006ed3` |
| `ramroot.cpio.zst` | 2,435,460,021 | `5eaa2fdb52dcbbaf20b4a9780f7d23e625535e3f5386f1659ed332fb7826d345` |

The independent pair verifier hashes both before reading stage one's embedded
pin with macOS tar. It passes exact root/kernel/size agreement, **215,513
entries** and **11,012,489,216 unpacked bytes in 16 KiB pages**. This is pin
verification; the M1 did not unpack or execute either image or independently
repeat M5's complete content/VM inspection.

Reverified the retained boot042 archive: **18,877,362 bytes**, SHA-256
`a2e57c0ccddcd7c8e60affac0ffa033deb9db1639119a7aa93faaedea276a781`.
All **13 package files** pass, SHA256SUMS digest
`60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd`.
Image remains `0b6df39566f12bcd5957e649946125a7bb0f42f31690933dc9896a2565b9b69c`.
Installed boot021 and clean client pin
`57a9339ffd1876e78297b17d34dece8cff8fa1ba` are unchanged.

The launcher digest is unchanged:
`b14ec7a1d6957197d808609a9c4888995598e23ce4c63707db2a58476a9e0740`.
Its offline RAM-root check emits exactly seven expected lines, including
package/root PASS, no operator-key, OFFLINE ONLY and **104,310,566 upload bytes /
300-second deadline**. The 20.9-second estimate at 5 MB/s is not native timing.
The sender dry-run verifies the root and reports **no session opened**.

## Independent tests and qualifications

| Suite | Final result |
|---|---|
| Existing controller cases | 102 PASS |
| Pair verifier | 8 PASS |
| Stage-two sender | 18 PASS |
| RAM-root profiles | 43 PASS, 2 SKIPPED of 45 |
| USB pipe | 15 PASS, handshake-only limitation below |
| CONNECT proxy | 16 PASS under bundled Python/OpenSSL; system-runtime TLS failure below |
| Clock helper | 13 PASS |

**215 methods pass, 2 skip** after two small test-only repairs. Initial logs and
failure details are retained privately rather than replaced by passing reruns.

* The RAM-root suite initially had one failure: its provenance assertion expected
  `VM job 045`, while the reviewed new record says `VM job045`. The test now
  permits the optional space and its stale attempt-26 comment is corrected;
  all checksum/kernel/profile guards remain. Two legacy fixture tests still
  skip because boot035/boot040 are absent at their expected test paths. Those
  image-size/DT checks were **not executed**, not counted as passed.
* USB-pipe initially reproduced the known close race: 14 pass, one assertion
  fails because its helper closes SSH stdin while device EOF is also pending.
  The test now waits, bounded to five seconds, for device EOF to terminate the
  relay before closing its stdin. Final 15 pass; source/binary used on hardware
  is unchanged. Two-port unprivileged sshd tests on this macOS report
  **handshake only** after authentication stalls. ResourceWarnings remain in
  logs; this suite does not prove their post-authentication tunnel behavior.
* System Python **3.9.6 / LibreSSL 2.8.3** produced 15 proxy passes and one
  trusted TLS handshake error. A direct local TLS connection without the proxy
  also fails `NO_SHARED_CIPHER` / handshake failure. The unchanged 16-case
  suite passes using the already bundled Python **3.12.14 / OpenSSL 3.5.8**,
  including verified HTTPS through CONNECT. No host install, proxy change,
  certificate-verification weakening or global runtime change was made.

## Reused controller-side helpers

The retained reader, USB-pipe binary/source, CONNECT proxy and clock helper
match the attempt-26 digests. The operator key's derived public half matches
both the recorded public key and authorized_keys; no key material is published.
Reviewed sender/receiver source and switch/udev-cleanup service ordering.

Offline `ssh -G` confirms **m5s=root** with stage-one known_hosts and no
forwarding, **m5o=omarchy** with its distinct known_hosts and loopback web relay,
key-only selection, no agent forwarding or connection multiplexing. OpenSSH's
bracketed loopback-address output required a correction to the local checking
script, not the config. No M5 SSH session opened; existing known_hosts retained
until the authorized boot. Private receipts/logs/hashes are under
`build/native-intake/attempt27/`.

## Ready for the preboot procedure; live attempt still pending

Next: fresh M1 restart, cable re-seat, unlocked/open lid and power, recording
and caffeinate for the live run. Fresh read-only M5 checks must confirm original
**Full**, lab **Permissive** and **Macintosh HD as default**. Then the human
starts one attempt under `tools/m1n1-client/stage-b-instructions.md`.

The first native run permits one launcher invocation and one stage-two send,
with its documented switch/re-enumeration/desktop and stop bounds. The new
hardware-facing uncertainties are USB rebinding and automatic keyboard-start
ordering. No failure injection, automatic retry or repair on hardware.
Boot042/NVMe-disabled guards/fixed single-core arguments stay. Storage remains
attempt28; CPU/SMP changes are separate. No policy, partition, firmware, host
network or package setting changed. Desktop slowness/GPU/trackpad/efficiency
remain outside this delivery result.
