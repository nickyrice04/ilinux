# Attempt 27: new image pair, offline verification and M1 handoff

2026-10-19 local date; build/test timestamps below are UTC on October 20.
Baseline `75411ec`. **Commit/publication approved on 2026-10-20. Native
attempt 27 and live checks NOT RUN.** No boot, security, volume, firmware or host-setting
change was made. The M1 uses [the current checklist](../../tools/m1n1-client/stage-b-instructions.md)
after publication and independent intake; a draft is not a restart instruction.

## Exact deliverables

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Stage one, `stage1.cpio.zst` | 59,630,835 | `84c01f536516b85939f6ead55e37d0a9fa4838414edb84e033aef221f6006ed3` |
| Omarchy root, `ramroot.cpio.zst` | 2,435,460,021 | `5eaa2fdb52dcbbaf20b4a9780f7d23e625535e3f5386f1659ed332fb7826d345` |
| Unchanged boot042 Image | 44,616,192 | `0b6df39566f12bcd5957e649946125a7bb0f42f31690933dc9896a2565b9b69c` |
| Unchanged Stage-B DT | 63,539 | `17c55af9eb39ea799e254335176e9748193237dce3735f59cd286a63ea0a0405` |
| Unchanged launcher | — | `b14ec7a1d6957197d808609a9c4888995598e23ce4c63707db2a58476a9e0740` |

Both images stay private and ignored. The existing boot042 release/package,
installed boot021 m1n1 and client commit `57a9339ffd1876e78297b17d34dece8cff8fa1ba`
are reused. No new launcher allowance. NVMe and cpufreq remain disabled;
`nr_cpus=1`, `idle=nop arm64.nowfxt` remain. Storage is attempt 28, independently
reviewed; frequency/SMP experiments are not included.

Root build: `2026-10-20T02:57:20Z`; Omarchy
`4.0.0.r7028.g33783b1-1`, 865 packages, Claude executable 2.1.304 signed out.
The [image completion record](subagent-review-2026-10-19.md) covers its exact
boot042 VM test and the repeat-delay, menu-poller, weather, automatic keyboard,
keyboard-rerun and SSH changes. This delivery change does not fix the measured
0.47-second native frame cost or establish higher CPU frequency.

Stage-one build: `2026-10-20T03:35:39Z`; job049, 115 packages, 10,326 paths,
337,524,317 payload bytes. Compression `zstd --ultra -22 --long=27`, 81.7 seconds.
Its pin names the exact root/kernel above, 215,513 entries, and
11,012,489,216 bytes occupied on a tmpfs with 16 KiB pages. This tmpfs usage
measurement differs from job045's sum of per-file page allocations; neither
is a desktop working-set measurement. Build unpack took 10.40 seconds.

The build checked both password fields locked, no private/SSH host keys,
empty stage-one machine-id and the operator's public keys owned by root with
0644 permissions. The ELF page check found zero files unmappable on 16 KiB
pages; three existing optional dependency references were already absent
before pruning. The root's separate content checks and limitations remain in
the image completion record. VM-only keys and probes are separate test
artifacts and must never be delivered or published.

## Software checks

* New `verify-two-stage.py`: independently hashes both images, then reads the
  embedded stage-two pin from verified stage one, without unpacking to disk or
  running any image content. It requires agreement among both public records,
  the embedded pin, kernel digest, entry count and unpacked-size metadata.
  Eight tests PASS: matching pair, corruption/truncation before archive access,
  an authentic stage one with a wrong root pin, kernel mismatch, duplicate pin
  fields, metadata drift, symlinks and malformed values. The real pair passes.
* Sender: 18 tests PASS. Launcher RAM-root suite: 45 tests PASS, no skips in
  this workspace. The unchanged launcher accepts the candidate through a
  scratch manifest, reports OFFLINE ONLY and opens no USB device.
* m1n1's upload is now 104,310,566 bytes including Image and DT: an estimate
  of 20.9 seconds at 5 MB/s. Attempt 26 uploaded its entire root in 473.4
  seconds. The remaining 2.44 GB transfer now uses Linux's link; the new total
  native boot time has not been measured.

## Job049 VM evidence

Full rejection/switch run: **PASS**, 695.68 seconds to the final guest verdict.
The deliberately wrong image was refused before transfer (6.0 seconds); the
short transfer stopped at 67,108,864 bytes; the corrupt full-size image was
refused by SHA-256 after 307.4 seconds receiving. Stage one stayed available
with a visible reason each time. The valid transfer then took 307.3 seconds
at 7.9 MB/s; unpack took 10.0 seconds. Stage two's systemd started at 660.02
seconds, its gadget bound at 662.06, the desktop was ready at 669.13, SSH was
verified at 695.62 and all post-switch image checks passed at 695.66. Used
memory at that point was 15,238 MiB. Failure-panel and desktop screenshots were
inspected. Only the two expected system failed units were present:
`omarchy-provision-hardware.service` and `ufw.service`.

Fresh normal-path timing run: **PASS**, 365.06 seconds to the final guest
verdict, 369.0 seconds host wall time. Desktop ready at **338.51 seconds**
after kernel entry, including 307.3 seconds receiving. The remaining 31.21
seconds includes initial link/login, unpack, switch and desktop startup.
Used memory at the final check was 15,058 MiB. Desktop screenshot inspected.
Both runs report only the expected two system failed units; job045's earlier
user document-portal failure is still an unresolved limitation.

| Event, seconds since kernel entry | Full failure/switch run | Fresh normal-path run |
|---|---:|---:|
| Stage-one link ready | 3.57 | 3.56 |
| Valid root reception starts | 340.40 | 7.33 |
| Root verified | 647.72 | 314.67 |
| Unpack complete | 657.84 | 324.80 |
| Stage-two systemd starts | 660.02 | 326.96 |
| Stage-two gadget bound | 662.06 | 328.98 |
| Desktop ready | 669.13 | 338.51 |
| Stage-two SSH verified | 695.62 | 365.00 |
| Effective image fixes verified | 695.66 | 365.04 |

The harness intentionally waits 20 seconds after desktop readiness for the
screenshot, then checks the link; the SSH-check timestamp is not the earliest
possible login time. Both real transfers were 307.3 seconds at 7.9 MB/s and
both unpack operations 10.0 seconds. These are VM measurements, not predictions
of the native M1-to-M5 transfer or desktop performance.

Local evidence is preserved under job049 `out/runs/` in
`attempt27-full-20261020T0337Z` and `attempt27-timing-20261020T0350Z`, including
input hashes, setup, console, journal, markers, timeline, wall time and images.
The test overlay SHA-256 was
`c311999635a8b79bf73fb40077f71015dfed2336aee6178e7fe9c23146dab08c`.
Do not publish those directories: the test base carries VM-only credentials
and journals contain identifiers. Both VMs exited; no build-VM lock is held.

Reproduce with job049's documented build inputs, then `run-qemu.sh` and, after
preserving that run, `NEGATIVES=0 run-qemu.sh`. The separate `out/job.env` pins
boot042 and the new root record. The public image records now name this exact
pair together. Final intake was repeated on the private transfer copies using
those actual public records: pair verifier PASS, unchanged launcher OFFLINE
ONLY/PASS, sender dry-run PASS. Nothing opened USB.

Test method: QEMU 11.1.1 with Hypervisor.framework (`hvf,kernel-irqchip=on`),
one host-type vCPU with PMU disabled, 32 GiB, GICv3, 3456×2234 x2r10g10b10
simple framebuffer, no network. The root's source disk is read-only. Job041's
`Image-test` (`a1ecd7f899097dc70870678281e3b99b69120412e5bad7bad01e55b43b1a6bbc`)
adds `dummy_hcd` and generic USB serial. It shares boot042's release string
but is **not the exact boot042 kernel**; job045 separately tested that kernel.
Matching module release is not evidence of hardware compatibility.

The M1-side sender and M5-side receiver run on the same vCPU using dummy_hcd.
Each successful run must reach Omarchy, recreate the gadget, carry its journal
and newly generated host key on interface 0, accept SSH as `omarchy` with sudo
on interface 1, report the pinned root/build and one soft-reboot, and satisfy
all required markers. Added post-switch checks require effective repeat delay
1000 ms, valid runtime shell JSON without weather, an enabled keyboard unit
skipping the absent MTP controller, and CPU `0` only. A missing query is failure.
The full run also rejects a different offered image, a transfer cut after
64 MiB and one changed byte in a full-size transfer before accepting the root.
The fresh timing run sends the real image without those preceding failures.

## What remains for the native attempt

The VM cannot prove the real USB controller's second bind or automatic keyboard
initialization timing. Attempt 26 proved manual keyboard loading, not this
startup ordering. The M1 records transfer/check/unpack timings, USB disappearance
and return, first desktop, automatic keyboard and rerun, human typing, effective
repeat delay, menu-poller cleanup and weather observation. Known earlier failed
services (hardware provisioning, UFW, user document portal) remain unresolved;
new faults must not be dismissed as these known failures.

The first native test sends once. Intentional bad transfers are VM tests only.
A refusal/failure, stalled progress, reset, panic or hardware fault ends this
attempt; preserve evidence and return to Macintosh HD. A missing second link
is recorded separately from a visible desktop, without reloading drivers or
retrying. Keep Macintosh HD Full/default and lab Permissive. On 2026-10-20 the user
omitted further routine policy rechecks; the last reported policies are retained
without claiming fresh verification.

No claim of GPU support, all-core operation, DVFS, power efficiency, trackpad
support or macOS performance parity follows from this delivery test. The
[continuation plan](resume-plan-2026-10-19.md) keeps those experiments separate.

## Approved publication scope

The user approved committing and pushing this reviewed scope on 2026-10-20.
Publication contains the completed image fixes (job045), the public-key mode
fix and related VM coverage (jobs039/046), two-stage receiver/sender/build/test
code (job049), the independent pair verifier, both image records, and these
handoff/status documents. The completed offline cpufreq/job051 and SMP findings
belong in a separate research commit; they enable nothing in attempt 27.

The inherited `kernel/experiments/omarchy-kconfig/` and jobs047/048 are outside
this review and must not be swept into a broad `git add`. No images, VM test
keys/overlays built as artifacts, raw diagnostics or proprietary material are
publication candidates. Test-overlay **source code** is included; generated
archives and runtime keys are not. No new release or boot042 rebuild is needed.
