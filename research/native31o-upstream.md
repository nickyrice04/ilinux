# 31O: the T6050 startup problem extends beyond this controller

Date: 2026-10-22. Read-only public-source investigation after the consumed
31N result. No downloaded code ran, no target operation occurred and no
installed boot object, firmware or setting changed.

## Decision

**31N closes the host-gap experiment, not the CPU-start investigation.** The
local pair completed and CPU1 changed power/state, but no entry channel
committed identity. Repeating the pair with another equivalent recorder is
unlikely to distinguish the remaining explanations.

New primary evidence makes firmware initialization a substantially stronger
research direction. Gravity Linux publicly identifies a secondary-core
startup problem on M5 Pro/Max and says it has reported the misconfiguration to
Apple. A separate T6050 investigation reports the same failure on a newer
firmware generation and unsuccessful attempts to register alternate image
packaging. These reports do **not** prove that no original software solution
exists, identify this machine's failed instruction, or qualify a firmware
update as a fix.

The practical next step is to correlate the existing boot layout and matching
firmware's preparation path offline. A further physical attempt needs an
observation or operation that distinguishes a specific remaining hypothesis.
There is no demonstrated upstream patch to transplant into this experiment.

## Newly located primary evidence

### Gravity's acknowledged platform limitation

The [Gravity Linux FAQ](https://gravitylinux.org/about/) says that, as of
macOS 27.0 Beta 5, M5 Pro/Max platform misconfiguration prevents its developers
from starting secondary cores; they report having notified Apple. The statement
is also present in pinned [website source](https://github.com/GravityLinux/website/blob/cfc74e6b3fcdb2f794fbf725464f27b506ad8d21/content/about.md).
It is the project's own report, not an Apple confirmation or published erratum.
The scope must remain Pro/Max: successful base-M5 results do not contradict it.

The FAQ names an older firmware version. It must not be described as proof that
every newer firmware has the same defect. The additional report below supplies
a separate, attributed observation on a later version.

Gravity's [bootloader](https://github.com/GravityLinux/bootloader/blob/f02d4a52017915febb222539636b5b025a70407a/src/smp.c)
was checked at `f02d4a52017915febb222539636b5b025a70407a`. The current secondary
path still has the familiar two 32-bit start writes and no demonstrated T6050
release correction. Its older four-core global mask must not replace this
project's already corrected eighteen-core topology mapping.

### Another T6050 machine, newer firmware, same unresolved result

The [J716s report](https://github.com/rolotrealanis98/m5pro-linux/blob/bb0c75e69d06247faf595641c5a12b0fadc415d2/docs/smp-t6050-raw-path.md)
at `bb0c75e69d06247faf595641c5a12b0fadc415d2` describes October 20 tests on an
18-core M5 Pro, macOS 27.2 boot objects and `mBoot-20457.41.2`. The author
reports power/state changes without entry evidence. Their raw boot layout has
an empty `BootKC-rx` region, the image in `BootKC-rw`, and a separate dummy WFI
region. They tried ordinary m1n1 Mach-O packaging and a BootKC-shaped variant;
`kmutil` rejected both before iBoot, and the raw object was restored.

This is useful evidence against a quick packaging fix. It is not a successful
alternate boot path. The report's stronger conclusion that the problem is
unfixable by a bootloader is the author's inference; neither its negative
markers nor ours establish that proposition. No registration command, firmware
replacement, protected-region modification or repeated release variant is
adopted from that report.

### Direct-installed raw loaders have already been tried elsewhere

Sowyu's more detailed [historical checkpoint](https://github.com/Sowyu/m5-azahi/blob/82c90a5fd0b841d3acec4f558f9424b2cefec8bf/research-archive/probe/CPU-CHECKPOINT.md)
goes beyond the shorter audit used for 31N: it records direct installed V5
boots, eliminating the RAM chainload, with CPU1 still failing its earliest
stage. It also reports negative RAM-independent event-loop observations.
Consequently, reinstalling an otherwise equivalent raw loader solely to remove
chainloading is a low-priority experiment, though this external result cannot
prove this machine's incoming state is identical.

That checkpoint also records an access hazard: the first
CPU0 CoreSight identity read caused an SError and transport timeout. Its
[identity probe](https://github.com/Sowyu/m5-azahi/blob/82c90a5fd0b841d3acec4f558f9424b2cefec8bf/research-archive/probe/cpu-debug-identify.py)
is explicitly disabled. This is concrete same-SoC evidence against treating an
ADT debug aperture as proof that a standard debug-ID or PC read is usable.
No debug unlock, authentication change, halt or blind register scan is proposed.

## What is still potentially discriminating

### 1. Image layout and pre-handoff initialization

The external raw-image observation suggests a concrete offline question:
**which initialization choices differ when the firmware accepts a raw custom
image, compared with its macOS kernel-collection path?** Use this project's
existing sanitized ADT and package metadata first; retain only allowed layout
relationships, not personal identifiers or raw memory-map dumps in public Git.

Trace the matching generic firmware's image-layout selection, reset-address
setup and CPU initialization ordering. Distinguish configuration code that runs
before any secondary can fetch from code that runs only during sleep/cluster
restoration. The previous matching-iBootData work establishes conditional
programs, not their active invocation. Establishing their caller and condition
is more useful now than translating another isolated operation.

The [existing platform study](native31l-platform-prepare.md) already identifies
ACC restoration and the `0xe440f8` selector. An actual write in macOS cluster
restore is not by itself evidence that CPU1, sharing CPU0's running cluster,
needs that write before first entry. Keep that distinction when comparing a
complete raw boot with a macOS boot. Do not replay a whole restoration program.

### 2. A bounded startup-state trajectory, if it answers a specific question

The [same-board qspqww findings](https://github.com/qspqww/m1n1/blob/90f3be1d34a5af87e04fffead4f3cdb44d8fd046/findings.md)
describe a local trace with a CPU1 implementation-state transition immediately
after the cluster start and another approximately five microseconds later.
CPU0 and an unstarted peer were unchanged. Their earliest entry marker stayed
negative. This supplies a comparison trace, not known meanings for the bits.

Our current observer reads 32 bits at the already bound implementation-state
location and publishes the low byte in three host-separated phases. It cannot
reconstruct that early trajectory. If firmware analysis identifies a useful
state discriminator, one fixed on-target, bounded post-pair trace could capture
it without host communication between samples. It would require independently
qualified access width, complete owned output storage, timestamps, a strict
sample limit and fault/partial-result handling. Existing 32-bit permission is
not automatically permission for a 64-bit access. Do not add a third CPU merely
because the external experiment used one.

Another state trace without a question that changes the next decision would
not justify another reboot. Full implementation words and CPU0's architectural
reset vector are not CPU1's PC; a changed opaque bit is not execution evidence.

### 3. Prepare later Linux work while first entry remains unresolved

The [T6050 cpufreq proposal](https://github.com/aurora-silicon/linux/pull/249),
head `a289553f195ed51f2e44dcb9dfaab307d70ec13b`, adds command-state DVFS handling
but explicitly requires qualified firmware thermal ownership and hardware
validation. It is a separate later integration lead, not a startup fix or
evidence of macOS-level speed. Independent storage, networking and renderer
work can continue offline without pretending that it removes the CPU blocker.

## Search scope and provenance

Fresh GitHub API reads checked public T6050 repositories/issues, Gravity's
bootloader history and FAQ source, the qspqww bring-up branch, Sowyu's detailed
checkpoint, and Aurora's CPU proposal. qspqww remains pinned at `90f3be1d` and
Sowyu at `82c90a5f`; neither exposes a newer demonstrated all-core correction.
This is a bounded public search, not a claim about all unpublished work.

Downloaded public notes/source stay under ignored `build/research31o-upstream/`
and were read as data only. Useful SHA-256 values for reproduction:

| Snapshot | SHA-256 |
|---|---|
| Gravity pinned FAQ source | `1f74c86910c1721852156cc1038e1100ee7a80620f4b5085438c92c1dfd72584` |
| Gravity pinned `src/smp.c` | `7ba57060e8118841b17b1624c8b02a4a8535a977bc6f8275d0066ab75c7f22ce` |
| J716s raw-path report | `90bfb6d68ff09ce4a75af72720611bcc69af1687de8d2ec9186d3474c235788b` |
| Sowyu detailed checkpoint | `4a04f9e2051ff83e34a9667d0862cdc9daa1fdd3e2349e9580575f2d65833d56` |
| qspqww findings | `2754434b5432504e85ca51431c3738332299bc37c0894c7f9bfa6519bbc40e20` |

The result changes research priority, not the machine. All eighteen cores,
their Performance/Super cooperation, native SMP and performance/energy parity
remain unverified. No fresh restart is justified by this source review alone.
