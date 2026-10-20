# Interrupted side sessions: completion and review

2026-10-19 local date. Baseline `75411ec`. This is offline work, kept
uncommitted for the user's review. No native boot, module loading on the M5,
boot-policy/volume change, launcher allowance or public artifact upload.
The attempt ordering is in [the continuation plan](resume-plan-2026-10-19.md).
Subsequent pairing and handoff evidence is recorded separately in
[the attempt-27 validation](attempt27-two-stage-validation.md). The image/pin
and next-step statements below describe this earlier completion milestone.

## Omarchy root, job045

Candidate root: **2,435,460,021 bytes**, SHA-256
`5eaa2fdb52dcbbaf20b4a9780f7d23e625535e3f5386f1659ed332fb7826d345`.
Boot042 Image remains
`0b6df39566f12bcd5957e649946125a7bb0f42f31690933dc9896a2565b9b69c`.
The existing attempt-26 root and build records were preserved locally before
the rebuild. Neither the delivered root manifest nor stage one's embedded
root pin has been switched to this candidate.

Changes complete the interrupted image track:

* A 1000 ms key-repeat delay, with rate still 40. Attempt 26 measured this
  workaround on hardware; it does not reduce the cost of drawing a frame.
* Finish an abandoned Omarchy menu request so its waiting process exits.
* Enable the keyboard service for the expected MTP DT node and make a manual
  rerun recognize already bound devices. Failure leaves the system up.
* Remove the weather widget while preserving the installed user configuration.
* Set the byte-pipe SSH grace period to 180 seconds and classify sshd exit 255
  as a clean service exit. This also classifies other causes of exit 255, so
  the journal remains necessary for diagnosis.

The first resumed build exposed an assumption in the interrupted draft:
the installer already creates a user `shell.json`, with five bar sections.
The new stdlib helper changes only weather entries and preserves every other
field. Two host unit tests pass. Independent review also found a test that
could mistake failed IPC output for runtime weather verification. The test
now parses the expected JSON and rejects observed weather requests; missing
runtime evidence is explicitly marked unverified.

Build: zstd `--ultra -22 --long=27`, 610.1 seconds compression, 6.01 seconds
single-thread decompression in the build VM. Root payload 8,815,335,175 bytes,
215,513 files; 11,064,311,808 bytes when counted in 16 KiB pages. These are
build/delivery measurements, not native desktop benchmarks.

VM run **PASS**, guest job exit 0, completed `2026-10-20T03:25:25Z`.
Probe wall time 946.3 seconds. Desktop ready at 198.70 seconds; user first-run
done at 203.79 seconds. Menu, Chromium and Obsidian rendered and their saved
screenshots were inspected. No coredumps were recorded. Settled RAM usage was
14,034 MiB in this 32 GiB VM.

SSH/clock/HTTPS and the signed-out agent executable passed; 18 SSH logins,
20 clean sshd exits, zero failed sshd results. A refused-key session recovered
after 183.4 seconds, matching the 180-second grace bound. Effective repeat
delay is 1000. Both abandoned menu requests exited without remaining pollers.
Keyboard absent-device skip/failure handling passed. Parsed runtime shell
configuration has no weather; no matching weather request was observed during
the test window. The packed image's SHA-256 was independently rechecked on the
host after testing.

This is not a completely healthy systemd boot: hardware provisioning, UFW and
the user's document portal still fail, exactly as in the preserved preceding
VM run. The logs show missing nft support and the deferred Apple platform setup
failing. These remain kernel/platform integration work; the test PASS does not
erase them. User first-run completion is distinct from hardware provisioning.

The test uses QEMU TCG, one vCPU, 32 GiB, the exact boot042 Image and a
3456×2234 simple framebuffer. It does not emulate the MTP controller, Apple's
USB controller, GPU, DVFS, thermal behavior or CPU secondary startup. Automatic
keyboard initialization ordering and USB reconnection after a two-stage switch
remain native NOT RUN.

Build content checks report no SSH host/private key or agent credentials,
locked passwords and only the operator's public key. The existing approved
passwordless-sudo grant remains. The root also contains the build machine-id
and stays local/private; only pins and sanitized findings belong in Git.

Local candidate clone and candidate pin:
`build/resume-2026-10-19/root-candidate/`. Local evidence:
`virtualization/jobs/045-omarchy-installer-root/out/`
(`run.log`, `sizes.txt`, `compression.txt`, `build/private-contents.txt`,
`build/desktop-files.txt`, and `test/`).

## Frequency scaling, job051

The candidate and provenance are in
[`kernel/experiments/cpufreq-t6050/`](../../kernel/experiments/cpufreq-t6050/README.md).
Its module defaults to no writes and refuses unknown requested states rather
than inventing a clock rate. Write-enabled use needs a separate reviewed
attempt, an explicit immutable state cap, the correct board/SoC, and one
online CPU. It avoids the unknown STATUS layout and preserves existing
non-frequency safeguards.

The VM module build passed against boot042 with `W=1`, no compiler warnings.
Sixteen actual-callback cases passed under ASan/UBSan; six deliberate regression
mutations were rejected. Twelve Python test methods and the narrow DT/schema
checks passed. The first schema-doc invocation emitted a path warning despite
exit 0; the job now stages the binding under its matching schema path and
requires empty diagnostic logs. The rerun completed `2026-10-20T03:26:57Z`,
guest exit 0, both schema logs empty. The initial output is preserved locally.

Module SHA-256:
`97e358b27e94be5efd0d3d7d2c1c99ff314e22da9c2586de713dd8299ee17054`.
Candidate DT:
`aa9731d1ba8246a9441a85dcbf59bf65cfe82c7a8d33439e9d2cdc40cb0ee725`.
Toolchain: GCC 16.1.1, binutils 2.46.0, dtc 1.8.1, Python 3.14.8, Linux
7.1.6-vzrun2 build VM. The baseline Image and config match before and after.
Native behavior, actual frequency, power and thermals remain NOT RUN.
The candidate is not included in this root or any boot package, and the
production launcher remains unchanged.

## Secondary CPU evidence

The completed behavior-only handoff is
[`cpu-startup-2026-10-19`](../../reverse-engineering/findings/cpu-startup-2026-10-19/README.md).
It recovers existing REA/assembly evidence and independently checks the bounded
register-group function against its carrier bytes; it does not claim a new
REA invocation.

The misc-cores group resolves to physical `0x280688000` and cluster control to
`0x280620000`. Descriptor-based six-core fields give 18 unique start bits;
the existing four-bit stride aliases four pairs. This is a real arithmetic
problem, but cannot explain failures within the first cluster, where bit
positions are unchanged. Raw-boot reset entry, initial CPU state and stable
residency remain unknown. MacOS SPTM entry is not a raw Linux boot contract.

The next proposed SMP step is a separately reviewed, bounded observation of
one secondary's entry-related state, followed by a one-secondary experiment.
No CPU-start or security-register sequence was executed or copied into Linux.
All-core enablement must demonstrate timer/IRQ/IPI, shared-memory coherency and
load execution as well as CPU enumeration; idle/hotplug are separate work.

## Next main-agent work

After reviewing these deliverables, pair a newly built stage one with this
root's exact hash and size, repeat job049's corruption/truncation/wrong-image
refusals and full switch/desktop/link tests, and update the attempt-27 handoff.
The earlier stage-one evidence names the old root and is not a certification
of this pair. The current draft checklist is not a restart instruction.

Keep attempt 27 limited to two-stage delivery and these image fixes.
Storage remains attempt 28 behind its own reviewed launcher change; DVFS and
SMP stay separate. No reboot is ready from this completion record alone.
