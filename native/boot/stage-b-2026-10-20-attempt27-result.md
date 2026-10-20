# Attempt 27 — native two-stage Omarchy delivery and image fixes

**Observed, 2026-10-20:** one launcher invocation and one root send succeeded.
Stage one verified and unpacked the root, soft-rebooted into Omarchy, and the
USB link returned. Automatic keyboard startup and its single rerun passed.
The human typed `omarchy` without extra letters, but still reports a large
delay opening applications. The human confirmed returning to the usual
Macintosh HD desktop. No retry or boot/default/security/volume change occurred.

This establishes one native two-stage transition and the specific checks below.
It does not establish usable desktop performance, frequency scaling, SMP,
storage, trackpad support, GPU acceleration, efficiency or macOS parity.

## Provenance and offline results

Execution handoff: **`f4b44f006fe03d8df6ba7cf24f867dfa75befd1b`**.
Independent readiness was published in `eff1716`, with test-only fixes in
`c52b079`; see [offline evidence](attempt27-m1-offline-2026-10-20.md).
The user confirmed recording and explicitly started the attempt. The M1 had
restarted (uptime 557 s before preparation). Routine before/after policy
rechecks were omitted at the user's direction: original Full/lab Permissive
remain **last reported**, not newly verified. Macintosh HD was not changed as
the default. The normal live launcher identity and DT guards remained intact.

| Input | SHA-256 / size |
|---|---|
| Installed boot021 and clean client pin | `57a9339ffd1876e78297b17d34dece8cff8fa1ba` |
| boot042 archive | `a2e57c0ccddcd7c8e60affac0ffa033deb9db1639119a7aa93faaedea276a781`; 18,877,362 bytes |
| Package SHA256SUMS | `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd` |
| Stage one | `84c01f536516b85939f6ead55e37d0a9fa4838414edb84e033aef221f6006ed3`; 59,630,835 bytes |
| Omarchy root | `5eaa2fdb52dcbbaf20b4a9780f7d23e625535e3f5386f1659ed332fb7826d345`; 2,435,460,021 bytes |
| Image | `0b6df39566f12bcd5957e649946125a7bb0f42f31690933dc9896a2565b9b69c`; 44,616,192 bytes |
| Stage-B DT | `17c55af9eb39ea799e254335176e9748193237dce3735f59cd286a63ea0a0405`; 63,539 bytes |
| Unchanged launcher | `b14ec7a1d6957197d808609a9c4888995598e23ce4c63707db2a58476a9e0740` |

Archive/package, embedded pairing, launcher/sender dry runs and helper digests
passed offline. **215 test methods PASS, two legacy-fixture SKIPS**, with the
initial test assertion/race and system LibreSSL limitation retained in the
offline report. The proxy's 16 cases passed on the existing bundled OpenSSL
runtime. These are offline results, not additional native attempts.

## Native delivery and second link

* Read-only discovery: one primary candidate, two modem interfaces; no port
  opened by discovery. Target t6050, expected boot021 marker and no started
  secondary CPUs PASS. GPIO geometry/exclusions, final Hardware DT, both DAPF
  checkpoints (96-byte RAM correction/readback) and the 16-byte early framebuffer
  descriptor/readback PASS. No launcher or client change.
* Launcher **exit 0 in 21.836 s**. Payload upload checkpoint interval **19.736 s**
  for the stage-one/kernel/DT delivery. Handoff **04:42:12.682 UTC**
  (00:42:12 Eastern, October 20). This uses the small `ramroot` profile.
* Stage one's screen and USB journal arrived within the 120 s observation gate.
  Human confirmed `WAITING FOR STAGE TWO`; the panel fingerprint matched the
  local journal, and the sender's known-host record matched it too. No keys or
  fingerprints are published here. The MTP DART initialized unlocked with
  16 KiB pages; no fault was observed.
* Root sender started **04:46:12.285 UTC**. Exactly **2,435,460,021 bytes** sent
  in **86.7 s** as the M1 wrote them; receiver measured **86.8 s / 28.1 MB/s**.
  The M5 verified the exact published size/SHA-256. It unpacked **215,513 entries,
  about 10.3 GiB**, into RAM in **20.7 s**. Sender reported the switch request
  after **108.8 s**, exit **0** (host process interval 110.304 s including setup).
* Journal: switching at kernel **349.132836 s**, systemd soft-reboot at
  **351.883488 s**. Stage-one reader ended **04:48:04.306 UTC**, exit 0,
  **61,250 bytes**; disappearance during the switch was expected.
* Second reader opened successfully at **04:48:52.083 UTC**, with both USB
  interfaces available. This is the first second-link observation, **not the
  enumeration timestamp**: it was started after the first reader exited.
  It retained stage-one history plus new-root records and collected
  **213,761 bytes / 2,309 lines**, until the controller stopped it. Exit 0;
  the final aborted read follows that intentional stop, not a detected fault.
* New root key matched its unique root journal event and differed from stage
  one's. SSH worked as `omarchy`; sessions were sequential on interface 1,
  alongside the interface-0 reader. Clock helper PASS: corrected a **1.5-day**
  offset, then measured **3.7 ms ahead**, with 11.5 ms round trip.
* Root **`ilinux-stage2-root`, tmpfs, 63.2 GiB capacity / 10.3 GiB used**;
  **`SoftRebootsCount=1`**; online CPUs **`0` (one CPU)**; kernel
  **`7.1.9-g863199d8b4a3-dirty`**, build **`2026-10-20T02:57:20Z`**,
  Omarchy **`4.0.0.r7028.g33783b1-1`**, expected boot042 Image hash.
  Hyprland's desktop-ready journal event is kernel **362.944016 s**, about
  **13.81 s after switching was requested**.

## Keyboard, desktop and image checks

* **Automatic keyboard PASS:** unit active/exited, successful result at kernel
  **355.594790 s**, four modules loaded (`apple_rtkit_helper`,
  `apple_dockchannel`, `hid_apple`, `dockchannel_hid`), all expected bindings and
  `/dev/input/event0` Apple MTP keyboard. One `sudo ilinux-keyboard --no-typing`
  rerun passed steps 0–5 on the already-loaded path, including the previously
  troublesome step 4. No manual repair or unloading.
* **Human typing:** `omarchy` appeared without extra letters. Human still
  reports a massive response delay, especially opening applications. This is
  one typing observation, not a repeat-rate or latency benchmark. No trackpad
  device was established.
* Effective **repeat delay 1000 ms**, rate 40. Six-second CPU sample: **1% busy**,
  no menu process in the before snapshot. The display remains **3456×2160,
  scale 1, XRGB8888, reported 60 Hz**; software-rendering libraries remain
  mapped. Full-screen background and notification layers remain present.
  Reported 60 Hz is not measured frame throughput; no new per-frame timing or
  clock-frequency measurement was made. Attempt 26's rendering measurements
  remain separate evidence for investigating the ongoing delay.
* Runtime shell-config query: valid JSON **version 1**, nonempty `bar.layout`,
  **no `omarchy.weather` item**. The initial noninteractive SSH query lacked
  `OMARCHY_PATH` and failed; a command-scoped environment corrected the read-only
  query without editing target configuration. The relay logged **zero CONNECT
  requests** during its approximately 8.5-minute window; no weather-reference
  line was found in the captured journal. A longer weather interval was not tested.
* **Menu cleanup INCONCLUSIVE:** video shows a keybindings window; the complete
  requested Super+K twice / Super+Space / close sequence was not independently
  confirmed, and `desktop-after.txt` was not captured before ending the attempt.
  No claim that replaced-menu poller cleanup passed natively.
* Stage two has **zero unused-port sshd status-3 exits** and no SSH auth-timeout
  lines in the capture. **Stage one still has 18 unused-port status-3 exits**;
  the root's SSH change does not remove stage one's noise. Keyring sync produced
  no captured lines. Failed units match the known VM set: system
  `omarchy-provision-hardware.service`, `ufw.service`; user
  `xdg-document-portal.service`. These remain unresolved.
* Soft-reboot teardown logged two udev `SYSTEMD_WANTS`/transaction conflicts
  while stopping the old gadgets. The new gadgets and root still came up;
  record the messages rather than treating the transition as warning-free.
* Kernel-only scan found **zero BUSERR, translation-fault, nobody-cared,
  kernel-panic or unhandled-fault lines**. Qt `QDBusError` warnings are not DMA
  bus errors. No M1 panic was observed. No reset or unexplained link loss was
  reported during desktop use.
  The early `cs` PMGR domain still reports failure to reach state `0xf`,
  `pm_genpd_init failed` and probe error `-22`; its effect remains unresolved.
  A successful desktop is not evidence that this warning is harmless.

## Video, process errors, bounds and return

The private recording is **415.007 s**. Sampled frames show Running proxy,
stage-one waiting/receive/unpack, root startup, a black display transition,
then Omarchy wallpaper, bar/notifications and a keybindings window near the
end. The desktop is visible by clip **400 s**; samples at 385/390 s are still
black. This bounds the first visible frame coarsely and is later than the
journal's readiness notification. The clip does **not** document ten minutes
of desktop behavior or the later typing test. No media or screen key is pushed.

The first local root-key parser mistakenly selected the retained stage-one
tag; root key generation uses a different journal tag. Its assertion failed,
but a shell command separator allowed the read-only baseline SSH collection
to run before that local assertion was corrected. The actual root key matched
its unique root journal event when checked correctly; there was no actual
key mismatch, host-key policy relaxation, transfer retry or target repair.
Future collection must enforce that verification dependency in one checked
process before launching SSH observations.

**Bound exception:** the controller ended desktop observation roughly one
minute beyond the requested ten-minute desktop cap while processing evidence.
This is a procedure overrun, not a new permitted limit. Reader stopped at
**04:59:16.316 UTC**, about **17 min 4 s after handoff**; proxy and this run's
`caffeinate` were also stopped, and no SSH session remained. The last retained
journal record is kernel **992.007639 s**, about **10 min 29 s after the
desktop-ready notification**. The human confirmed return to Macintosh HD
before **05:01:14 UTC**, within the 20-minute overall bound. A future run needs
an independently enforced desktop deadline so evidence review cannot extend it.

**Consumed:** one launch, one image send, no automatic retries. Both images,
receipts and raw evidence remain private under ignored `build/`. Fresh
policy verification was deliberately **NOT RUN** per user direction; no new
Full/Permissive/default claim. Storage/NVMe, CPU-frequency hardware tests, SMP,
GPU/trackpad enablement, agent sign-in and additional setup **NOT RUN**.
The next work is M5's review of the response-delay blocker and incomplete menu
check, with storage and CPU work still separately reviewed. No new live attempt
is authorized by this report.
