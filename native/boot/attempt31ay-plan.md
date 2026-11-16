# 31AY: reproduce the community J716c source stack offline

Scope: accept M1's 31AX review `ee4f70c`, reproduce the matching open-source
kernel/Aura/Mesa stack, test it in isolation and publish an M1 review handoff.
No firmware, volume, boot object, Startup Disk, security, installation or live
controller action is authorized by this task. Original remains protected at
Full Security; prior return confirmations stand without another manual query.

## Foundation

Use Cameron Cooper's publication `5e11068a`, preserving its complete pins:
kernel `a59e709c`, full 16K config, same-build modules/DT, Aura `9da61857`,
Mesa `10161a78`, and OS firmware 27.2.1/26B131 with the source's OS mBoot and
loaded-image checks. The 14-inch Pro ready image is not this board's image.
Use public implementations directly; another old-stack CPU-start experiment
does not advance this matched baseline.

Jobs 096 and 097 execute public build code only in the retained ARM64 Linux
VM, with no network or package installation, fresh case-sensitive tmpfs and
both workspace locks. Source provenance, signed compiler inputs, build options,
artifacts and native runtime results remain separate evidence categories.
Recorded tool metadata differences must never mask a hardware/config change.

The stack manifest, validator, initial ALPM guard and pure watchdog lease
component are in `native/stack/j716c-community/`. They are offline tooling,
not a new deployed boot stack. Raw source DT data containing foreign per-unit
DROM remains private/nondeployable. Local firmware and runtime ADT fields must
be provisioned independently and must not enter public Git.

## Before the next owner boot proposal

1. Complete the source builds and inspect Image, same-release AArch64 modules,
   CPU topology, separate Stage1/Stage2 layouts and CPU-only Mesa tests. Keep
   source-build identities distinct from the publisher's measured binaries and
   package assets. A generic Stage1 from public source can become our candidate;
   the publisher's private installed Stage1 is not required.
   Our generic Stage1 is factory-blank proxy mode, with no ESP configuration.
   Qualify the matching Aura RAM-chainload or direct-composite route if keeping
   the existing partition layout; Lab APFS Data is not an ESP.
2. Qualify a supported refresh of the existing Lab to the exact Apple firmware
   baseline, including paired Recovery, runtime firmware, signing/installer
   trust, space, preservation and shared-system-firmware effects. Apple's public
   metadata advertises J716cAP/26B131, but no installer has been downloaded or
   verified. The inspected community startup updater is unfinished and its
   policy excludes this exact board/build; do not run it or substitute Pro pins.
3. Assemble a new Omarchy RAM root with the rebuilt modules, accelerated Mesa
   and appropriate reviewed Mac packages. Remove obsolete software-renderer
   forcing only in that new native profile. Validate the desktop/root in a VM;
   virtual rendering is not physical G17C validation.
4. Bind a concrete new kit/profile to our new Stage1/Stage2/root artifacts and
   post-transition baseline. Keep the reviewed AX state machine, preservation
   checks and independent rescue; never rebase old anchors or replay spent
   transactions. Requalify boot021 operation on the new firmware before treating
   it as functional fallback, and retain a separate manual Original route.
5. Complete watchdog integration: pre-Linux arming/retention, finite pre-open
   feeding, sole Linux owner, authenticated lease transport and real expiry
   behavior. The pure lease model is not a physical guardian; an M1 child
   timeout does not reset M5, and a hardware reset does not select Original.
6. Test the actual ALPM hooks in a disposable root and review the deployment
   closure. Then present the owner with one concrete firmware/boot proposal.
   No restart cue, page server or staging follows automatically from builds.

## First native acceptance window

After explicit approval and all deployment prerequisites, prefer one informative
RAM-root window over multiple narrow old-stack restarts. Record actual firmware
and artifact identities, all eighteen online CPUs, the three M/M/P clusters
(twelve Performance and six Super cores), cache/affinity/capacity topology,
temperature-qualified clock ceilings, native Asahi renderer/Vulkan identity,
panel readback, keyboard latency and N1/SSH connectivity. Preserve the reference's
conservative fan/clock/idle/RTC/ATC2 limits. Keep camera observation available,
with authentication and personal information excluded.

Use identical portable CPU/RAM and interactive workloads for the subsequent
macOS comparison. Eighteen online cores and a GPU device node do not prove
correct scheduling, sustained clocks, graphics correctness or efficiency.
Only once the native desktop and network are usable should the Linux-side
agent take over routine integration and measurement. Storage throughput,
persistence, APFS access, video/AI/audio/camera/suspend remain feature-specific
tasks; no Original write mount or partition change is implied.

Current evidence and actual limitations are recorded in the 31AY reproduction
receipts and source findings. Native Linux/SMP/GPU/performance, firmware update,
new enrollment and physical watchdog expiry remain **NOT RUN** in this task.
M1 follows `tools/m1n1-client/attempt31ay-instructions.md`, offline only.
