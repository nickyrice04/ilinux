# Next work after 31N: establish prerequisites before another physical run

Date: 2026-10-22. 31O is an offline checkpoint. Native 31O is **HOLD / NOT RUN**.
The user-facing goal remains usable Omarchy on this exact T6050 machine, then
measured macOS-class throughput, latency and efficiency. These goals are not yet
met. The current work does not alter macOS or authorize a new hardware operation.

## CPU first-entry track

The first unresolved milestone is verified secondary execution, before Linux
SMP or scheduler tuning. The [31N audit](native31o-controller-audit.md) found no
new entry-prefix, mask or local-pair encoding defect. Negative records cannot
distinguish failed fetch, another entry path, or invisible stores by themselves.

Next, trace the matching firmware's raw-image and kernel-collection preparation
paths, using retained sanitized layout evidence and the new RCfg structural
decoder. Establish the caller, branch condition and initialization order for
each candidate prerequisite. The [fresh REA findings](native31o-firmware.md)
show why unconditional restore-program replay is not justified. Record the
missing facts rather than assuming a captured value predates vector setup.

A new physical test needs a specific predicate that changes the next engineering
decision. One possible component is a post-power comparison of an already
qualified reset-mirror location with its pre-start value. A changed value would
be useful; an unchanged mirror still would not establish CPU1's effective PC.
This observation alone does not justify another restart. A bounded local state
trace is similarly conditional on a firmware-derived question, access-width
qualification and complete fault handling. No new controller is released here.

Once one secondary demonstrates identity and a bounded return, qualify coherent
memory and timers/IPIs, then one representative of each distinct cluster/core
type, then all 18 cores. Preserve the discovered 12 Performance / 6 Super
topology; do not treat base-M5 support as validation for this machine. Scheduling,
frequency, idle and energy measurements follow working SMP rather than serving
as substitutes for it.

## GPU work can proceed in parallel

The desktop also needs acceleration: more CPU cores alone do not establish
responsive rendering at the internal panel's resolution. The public foundation
is worth building and auditing, but a bounded source search found no demonstrated
T6050/G17C accelerated desktop:

- [Gravity Mesa's Apple9 results](https://github.com/GravityLinux/mesa/blob/87ac51d411f0e58a9433567ec2666f457be89e1d/src/gallium/drivers/asahi/README.apple9-es3.md)
  report substantial native M4/T8132 coverage. That is evidence for a different
  GPU, not qualification of G17C.
- [Base-M5 research](https://github.com/sh1ftmaker/m5-linux-research/blob/d220c02ab2bc3cedb9a956061bce5106a1e44049/research/handoff-final/gpu.md)
  reports a completed bootstrap job while Mesa user submissions still fail.
  It is an implementation lead, not a working driver for this M5 Max.
- [The T6050 DCP proposal](https://github.com/aurora-silicon/linux/pull/254),
  reviewed at head `7e74883565ccfa234c8cf71064d523c600bb5985`, explicitly
  excludes AGX changes and awaits hardware qualification. Display control and
  3D acceleration are separate milestones.

The next offline GPU deliverable should pin and build the kernel/Mesa foundation
in the existing VM, compare exact G17C topology, firmware messages, UAT mappings
and initialization data against retained local research, and implement original
bounded serializers with invalid-input tests. Do not enable this GPU by merely
aliasing another GPU generation. The first eventual hardware milestone is a
verified compute result or pixel readback with bounded failure handling; only
then integrate the compositor and measure latency and energy.

## Storage, networking and the Linux agent

Keep the existing read-only storage and networking work as distinct tracks;
neither all-core execution nor GPU progress proves SSD or Wi-Fi compatibility.
Inventory their current artifacts before assigning new work. Reuse the stable
RAM-root and USB link for an eventual qualified Linux session. Host SSD write
access or access to personal macOS files requires a separate design and is not
part of this checkpoint.

The Linux-side agent becomes useful when its session remains responsive and has
reliable networking and persistent project storage. It will receive exact build
pins, bounded benchmark commands, expected results and rollback instructions.
Measure menu/input latency, renderer throughput, CPU/memory bandwidth, sustained
storage/network rates and energy on the same hardware. VM tests prove software
contracts and builds only; they do not emulate the missing Apple firmware or
qualify native interfaces.

## Immediate coordination

M1 independently runs the [offline handoff](../tools/m1n1-client/attempt31o-instructions.md)
and publishes its result. M5 owns the next firmware-prerequisite analysis and
the separate GPU build/audit track. No restart, native readiness grant, new image
installation or automatic rerun follows from an offline pass.
