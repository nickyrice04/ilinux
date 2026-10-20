# Attempt30 offline evidence — 2026-10-20

**Offline preparation PASS. Native attempt30/live timing NOT RUN. M1 intake
pending.** Starting report: M1 `1b1153d`, attempt29 consumed and Macintosh HD
return confirmed. Existing working boot/images retained. No native performance
improvement, power saving or macOS parity claim follows from this preparation.

## What was established

Attempt29 observed normal sampled cache/table-walk/stack memory attributes,
actual huge backing and little base/huge difference in its fixed-order test.
It did not identify desktop causality. CPU0 is an M core around 2.65 GHz by the
dependent-ADD estimate. Hyprland software rendering and a single online core
remain major constraints; neither a broken memory controller nor a safe maximum
clock is established. Accurate input does not imply prompt event processing.

REA6.4.0/Ghidra12.1.4/JDK21 analyzed three CPU-policy driver entries in the
existing isolated lab. All 443 ARM64 instruction words independently matched
the carrier and LLVM. Two whole-function decompilations failed boundary checks
and were rejected; the third still requires manual interpretation. Findings
distinguish work-interval feedback, cluster-performance requests and scheduler
preferences without importing Apple's policy or code. See `rea-findings.md`,
`rea-plan.json`, `rea-validation.json`. Raw artifacts stayed private locally;
no proprietary content was uploaded or committed.

The original Linux implementation observes frame work, event-loop service,
CPU usage and software samples. It does not replay Apple requests. Linux
schedutil/utilization clamping are later integration points once frequency,
capacity, thermal and secondary-core prerequisites work on this hardware.

## Built and exercised

Job054 compiles the client/sampler with GCC16.1.1, `-O2 -Wall -Wextra -Werror`.
It also builds `-O1 -g -fsanitize=address,undefined` variants. Wayland1.26.0,
protocols1.49; exact xdg-shell XML hash and build metadata are recorded in
`vm-observation.json`. The executable bundle is four regular files, 163,840
bytes, pinned by `bundle.json` and `assets.json`. It contains no module, key,
image or Apple code. The collector is byte-identical to the repository source.

The VM unpacks the **exact retained attempt28 root** into RAM and uses its
Hyprland0.56.2-7, Mesa26.2.4 and Omarchy configuration. Hyprland hash is
`a9e57097798b2e815c8e91a0a4472d287573c4f7ce177b72a5b0907562a68da9`;
upstream commit `efb50993780079460b0cbed1363e2166a2de1d9f`. Client runs uid1000
with no supplementary groups. VM-only seat/Virtual-1 configuration enables a
3456x2160 scale1 virtual display; it is absent from the shipped bundle/root.
Compositor, collector and client are pinned to vCPU0, LP_NUM_THREADS=0 and
software GL. The build VM has 12 vCPUs/24 GiB and its existing 7.1.6 kernel; its
kernel, clock placement and virtual display differ from native boot042.

Final run 23:52:06–23:52:38 UTC, guest/wrapper exit 0:

* Two real user-session workloads each completed 20 callbacks. One 2s observation
  phase completed without human input; native human phase remains 45s/NOT RUN.
* Software CPU-clock sampling produced counts with zero lost events. Unmapped
  and anonymous-executable categories remain explicitly separate; no automatic
  attribution of those addresses to Mesa.
* Frame client passed ASan/UBSan with 20 callbacks and empty sanitizer stderr.
  Sampler ring tests passed wrapped records, lost counts, invalid sizes/heads,
  unknown IPs and live mapping classification under ASan/UBSan.
* Exact native entry point refused generic VM identity before the start marker.
  End-to-end receiver verified the shipping archive, created only root-owned
  RAM files with reviewed permissions, and reached that same native refusal.
  uid1000 can execute the client but cannot read mode600 collector source.
  A second delivery refused the existing directory; no retry ran a workload.
* **129 Python methods PASS:** 14 bundle/frame/timeout/native-guard, 13 M1
  helper/key/deadline, 57 CPU/memory/desktop-profile, 45 legacy RAM-root methods.
  Timeout test verifies both owned process groups are stopped and partial
  CPU/profile observations are emitted rather than discarded.
* Host verifies the final archive without extraction/execution; retained pair,
  package and desktop-latency offline launcher/sender checks pass. No live
  connection or target operation was performed.

Final VM control medians, **not native results**:

| Run | Small damage callback | Full damage callback | Compositor CPU / phase wall |
|---|---:|---:|---:|
| 1 |18.249 ms|132.142 ms|1.57 / 2.051 s|
| 2 |20.781 ms|129.039 ms|1.92 / 2.412 s|

All 40 callback rows, IPC samples, sample categories and short clock estimates
are retained in `vm-observation.json`. Some small-damage outliers exceed 130ms;
do not omit them or infer a guaranteed response time. The VM clock estimate
changes across phases; these values are workload controls, not a matched
frequency-normalized OS comparison. Callbacks are not photon timestamps.

## Candidate rejected and failures retained

A preliminary minimal-config VM comparison using Hyprland0.56.2-5 (same
upstream commit, different package binary) measured full-damage callback
medians 132.759ms with color management and 133.583ms without. No useful gain
was established, so **no color-management change ships**. This is preliminary
VM evidence, not native proof that color management can never matter.

Initial harness runs failed for absent/misconfigured seatd, an occupied VM DRM
device, wrong Lua position type, initial tiled-surface resize, missing runtime
environment and the retained user not belonging to the video group. Final
VM-only setup uses its wheel group for the seat socket and a fullscreen client.
The retained binary mismatch was caught and its exact hash replaced the build
VM's different Hyprland pin. Early legacy profile-list test expectation was
updated for the additive profile. None was a native hardware test failure.
Private failed-run records remain under ignored build/attempt30; earlier
successful exact-root run was retained before the final receiver/partial-
evidence changes. VM cleanup's initial tmpfs unmount reported busy; the reviewed
recursive lazy fallback completed and the bounded VM powered off. Locks released.

## Reproduction and remaining gate

With the existing VM/toolchain and exact private attempt28 root present:

```sh
tools/lock.sh acquire quiet desktop30-review 'Exact-root desktop validation' 5
VZRUN_EXTRA='--gui --size 3456x2160' caffeinate -i \
  tools/vm-job.sh virtualization/jobs/054-desktop-latency desktop30-review
tools/lock.sh release quiet desktop30-review
```

Check **both** wrapper status and `out/run.log` guest exit; the wrapper alone
does not establish job success. Raw output is private. No VM image is published.
For intake and native steps use `tools/m1n1-client/attempt30-instructions.md`.
M1 readiness precedes the human restart. Keep the fixed 600s root-switch return
window, existing entry, original macOS and waived routine policy checks.
The result table in the experiment README selects the next causal experiment;
SMP, GPU, CPU DVFS/thermal/idle, networking and storage remain separate work.
