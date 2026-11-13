# 31AJ complete offline kit — M1 review next

This replaces the seven-file **component-only** 31AJ handoff. It completes the
candidate, Python-free Recovery reader, guarded two-visit transaction and
camera-facing Linux status display. It does not authorize a live operation.
Native readiness remains **HOLD pending M1 review and separate human approval**.
Older 31AH, 31AI and component-31AJ sources and their inventories are unchanged.

## What the next physical test answers

The actual initial lab payload is 31AF. The proposed experiment installs the
new direct Mach-O Aura candidate, observes one autonomous RAM-only Linux run for
at most **90 seconds**, then restores exact raw boot021 with disabled kernel
CTRR and returns to Macintosh HD as the default Startup Disk. This final state
is the intended restoration, not a byte-for-byte return to the initial 31AF.

The pinned Aura/Linux pair is the existing public reproduction:
Aura `bd9f3e8273dc79ae9095c19c2c4f32218446ad4e`, Linux
`dc8f6f77934b471a13c91e7780e2d91ebc904b3d`. Sources and archives are identified
in the unchanged `../attempt31ah/manifest.json`. Aura's runtime, Image, config
and sanitized J716c diagnostic DT are unchanged. The new original Linux init
adds a six-line block-letter panel at the existing five-tick summaries; it
does not change CPU work, affinity, checksums, timer deadlines or liveness.
`Txx` is a loop tick, not an independent wall clock. No framebuffer, font engine
or backlight register is accessed by this addition.

The candidate embeds the exact kernel, DT and root. The M1 does not upload a
root or need a working Linux USB connection. It supplies the independent timer
and, if requested, the already-built camera recorder. The new test can separate
firmware/loader-visible progress, Linux entry, online-core count and the
CPU/RAM/timer results. A logo-only result still does not prove an Apple-only
barrier. Native 18-core operation, performance, GPU, storage and networking are
not established by this offline package.

## Local delivery and workspace preparation

The same user's four-file delivery folder is `build/ilinux-31aj-review/`:

| File | Bytes | Purpose |
|---|---:|---|
| `aura-31aj-inline.macho.gz` | 15,985,266 | Exact padded, self-contained candidate |
| `runtime-31aj.tar.gz` | 16,031,216 | Fifteen bounded diagnostic/source/relink/evidence/notice members |
| `readback31aj` | 89,312 | New arm64 native v2 Recovery helper |
| `m1n1-boot021.bin` | 3,932,160 | Exact intended raw restoration object |

`manifest.json` binds all delivery bytes and production dependencies. The
candidate expands to **153,190,400 bytes**, SHA-256
`1ea24f0de4aa7d3e82c70a1b35f815791a48342db1a060100226b84dca7d7d01`.
The v2 helper is SHA-256
`3c86c03873f89ec8d55c880812f6861bddedee61cb4f996a3110fffc2119cba5`.
The canonical `recovery-profile.json` binds that helper and candidate to exact
boot021. The helper's candidate pins are compiled in; its self-hash is checked
against the profile without a circular build dependency.

Follow `tools/m1n1-client/attempt31aj-kit-instructions.md` from the checkout
root. Intake reads and validates the archive without extraction or execution.
Materialization creates four explicit files in a new workspace build directory;
its receipt is a sibling sidecar, outside those four files. Page preparation
then creates two complete paste blocks and escaped HTML, verified against the
new source inventory. Each phase has its own read-only text box: click inside,
Command+A, Command+C, quit the browser and paste once into Terminal. It invokes
no Recovery commands. The fixed-page server has a socket-free `--check-only`
mode; later authorized M1 serving exposes just the reviewed page at `/31aj`,
with bounded lifetime/client deadlines and no access logs, artifact downloads
or directory listing. No production page server is started during preparation.

Artifacts stay in ignored build directories for local same-user transfer.
No binary GitHub Release: full static glibc source/notice closure remains
incomplete. Apple binaries, decompiler output, policy values, comparison keys
and camera media are not published.

## Recovery transaction and metadata correction

The renderer and native reader are under `tools/recovery31aj/` and
`tools/boot-object31aj-native/`. Their READMEs specify the full interface and
limits. The install block uses normal Mach-O `configure-boot --compress`.
The independent restore block needs only helper, profile and boot021, so a
missing candidate cannot block restoration. It uses only the existing lab's
documented CTRR operation, then exact raw enrollment; it never uses policy-reset
`bputil -n`, creates volumes or changes firmware. Atomic markers prevent replay
of an attempted mutation. Every returned mutation, including failure, gets
fresh readback before any next decision. Authentication remains in Terminal.

The user's latest probe showed both policy commands succeeded but the initial
parser rejected two `rpnh` rows. Both roles also have `ronh`, `spih` and `stng`.
This was a parser limitation, not a security-mode failure. Static REA-assisted
interface analysis qualified their display formats. The v2 reader supports this
bounded shape rather than discarding those fields or requesting raw values.

After keyless target/paired-Recovery/31AF admission, the future block creates a
new original random comparison key in a private lab Data state directory.
Keyed, role/profile-bound commitments compare the two ordered RPNH values and
RONH/SPIH/STNG across both visits, alongside eight typed semantic policy flags.
The key and commitments remain private. No Apple credential, secret key or raw
policy hash is extracted into a record. Unsupported metadata still refuses.
This is preservation of supported fields, not all LocalPolicy bytes. Apple
documents a policy-wide anti-replay hash change on policy updates; that expected
field and the deliberately replaced object reference are excluded from equality.
[Apple's field descriptions](https://support.apple.com/en-gb/guide/security/secc745a0845/web).

Only `before-restore` permits an unknown, unreadable or temporarily absent
selected object under intact target/policy/private-metadata guards. Initial
31AF, installed candidate and final boot021 must each match exactly. The helper
separates contained-byte identity from wrapper authenticity and bootability.
The protected key/baseline storage and fresh collection sequence are required;
the JSON comparison is not cryptographic attestation of arbitrary assertions.

## Evidence and remaining physical gates

* `readable-build.json`: isolated Linux build, exact object relink, ordinary and
  intentional-timeout controls; 9,263 display assertions and four collector
  source-boundary methods. These are not 9,263 independent tests.
* `generic-vm.json`: exact Image/new root ran diskless with four vCPUs, checksums,
  timers and complete heartbeats for 60.543060153 monotonic seconds. The runner
  then stopped the VM externally. No physical M5 or bootloader was tested.
* `inline-layout.json`, `public-parser-controls.json`, `apple-inspection.json`:
  exact layout, eight public C parser controls with hardware hooks mocked,
  and read-only Apple format inspection. No enrollment was performed.
* `native-helper-build.json`, `owned-codec-controls.json`: SDK-only arm64 helper,
  64 normal and 64 sanitizer methods, independent sanitizer/source review and
  six actual original-artifact codec controls. Trailing compressed input refuses.
* `native-phase-controls.json`: production C reader plus actual own artifact
  bytes and synthetic policy/volume fixtures. No live state is manufactured.
* `policy-interface-evidence.json`: one bounded REA xref and four independently
  decoded words, no mismatch; static display formats, not whole-function or
  live Recovery qualification. Extracted Apple bytes remain ignored.
* `intake.json` and `offline-verification.json`: final four-file review and
  focused procedure/staging/intake/materializer verification summaries.

`source-sha256.txt` binds the new original code, docs, manifest, profile,
sanitized receipts and required frozen dependencies. The generated
`page-preparation.json` is excluded from its own input inventory to avoid a
hash cycle; its output/profile/inventory hashes are recorded and Git covers it.

Actual Recovery helper execution, paired-1TR admission, owner authentication,
lab Data staging, enrollment, native entry, physical core utilization, camera
readability, restoration and default return are **NOT RUN for this kit**.
The first separately authorized Recovery visit performs admission before any
transaction write; failure is a recorded outcome, never permission to weaken
the guard. No repeated desktop policy command or camera-quality session is
needed now. M1 review concerns the changed software and complete procedure.

Future lab Data staging has a fixed target, no destination override and refuses
any existing kit/state. It is a separate authorized write, not done here.
Temporary lab Startup Disk selection may be needed for its paired Recovery;
include that and final Macintosh HD default restoration in the future approval.
Macintosh HD must remain Full Security throughout. No restart is ready from an
offline PASS alone.

After physical SMP/RAM success, measure frequency, latency and bandwidth against
the existing macOS baseline, then bring up network/NVMe and an agent control
channel. GPU acceleration and power/suspend remain separate performance work;
online CPU count alone is not macOS-class performance or efficiency.
