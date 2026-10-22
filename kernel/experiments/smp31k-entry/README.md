# 31K natural cold-entry provenance tripwire

This is an original, RAM-only observation candidate for the exact public
boot021 image. It is **not a CPU-start fix**, reset-vector redirect, proof of
the effective CPU1 entry, or a Linux SMP implementation. Native execution is
**NOT RUN**. The parent 31K controller owns live authorization and all deadlines.

The public m1n1 primary entry is image offset `0x800`. Its normal path sets the
primary stack, applies relocations and calls `_start_c`, which clears shared
BSS. Allowing a late secondary to resume that primary path could damage the
already running proxy. The candidate therefore replaces just its first word
with a branch to an original 76-byte tripwire at `0xb00`. If execution naturally
reaches that entry after the primary proxy is ready, the tripwire records a
phase, low24 MPIDR and CurrentEL in distinct SMP RAM, then branches to itself.
It never replays the replaced instruction or resumes the cold path.

No RVBAR, MMIO, protection, system-register, stack or LR writes occur in this
tripwire. It changes x0/x8/x9 and the owned RAM record; it never preserves the
incoming boot-argument pointer. The terminal branch deliberately avoids WFE,
whose incoming trap/wake behavior is unknown. This is an **externally bounded
terminal spin**, not verified architectural parking. Interrupts or faults may
still leave the path. An unexpected CPU0 arrival would also spin and lose the
proxy. The human's independent return deadline remains essential.

| Region | Offset range | Ownership |
|---|---|---|
| Cold first word | `0x800..0x804` | New branch, original word `0xaa0003f3` |
| Existing vector recorder | `0xa00..0xaa8` | Frozen 31J, unchanged |
| Cold tripwire | `0xb00..0xb4c` | Original code, capacity ends `0xc00` |
| Existing vector record | `0x90a40..0x90a80` | Frozen 31J, unchanged |
| Cold record | `0x90a80..0x90ac0` | phase/EL/identity at offsets 0/8/16 |
| CPU0 positive-control scratch | `0x90b00..0x90b40` | Separate control owner |

`audit.py` binds the full image SHA and optional full symbol SHA, verifies zero
padding, and scans the bounded text/RELA sections for allocated symbols,
relative relocations, direct branches/literals/ADR and adjacent ADRP+ADD
references. No candidate references occur in the pinned image. The image-only
mode repeats byte/reference checks using the reviewed bound layout and explicitly
does not claim a new full-symbol check. These scans cannot exclude computed
references, broad-range accesses or hardware/firmware access. They do not prove
the primary can never re-enter its cold path.

The controller must prove live scratch is freshly zero without erasing unknown
contents; independently check both ends of code/record permissions; publish and
verify the body before the hook; and verify whole immutable text with only the
four approved vector/cold deltas. CPU0 positive control must pass first and
restore its distinct marker. No incoming CPU1 mapping or visibility follows
from successful CPU0 control or AT probes.

The first store precedes every system-register read. The phase meanings are:

1. A store before MPIDR/CurrentEL reads became visible.
2. Low24 MPIDR was published before the identity commit.
3. CurrentEL was published before the EL commit.

Phase3 does **not** prove the next barrier or terminal branch executed. Every
nonzero phase stops the campaign, including wrong identity, invalid phase and
partial acquisition; no CPU1 callback or continuation follows. Identity labels
use the project's reviewed 18-core map: 12 Performance (M) and 6 Super (P), with
CPU1 the sole startup target. Raw register values are not public output.

The cold tracker permits at most 2048 samples/8192 fixed reads, enough for the
existing bounded arrival loop and eight near-deadline callback loops without
an artificial 256-sample refusal. Existing controller wall deadlines remain
unchanged and take precedence; reaching this ceiling is a terminal refusal.

Both channels remaining at zero still cannot distinguish another entry, no
instruction fetch, an early fault or first-store visibility failure. A cold
positive with expected CPU1 identity identifies this instrumented code's
observation path, not the firmware's full reset provenance. The vector slot is
also an exception vector; vector positivity alone is not reset provenance.

## Offline verification

Run with a locally retained pinned image and, on the build host, its symbols:

```sh
python3 -I kernel/experiments/smp31k-entry/test_tripwire.py --image "$IMAGE" --symbols "$SYMBOLS"
python3 -I kernel/experiments/smp31k-entry/audit.py --image "$IMAGE" --symbols "$SYMBOLS"
python3 -I kernel/experiments/smp31k-entry/builder.py --image "$IMAGE" --symbols "$SYMBOLS"
```

Omit `--symbols` for the explicit image-only intake. Do not omit `--image` from
the test command: otherwise two image-bound tests are reported as skipped.
In the isolated build VM, GNU assembler/linker/objcopy reproduce `tripwire.S`
with `tripwire.ld`; compare its `.text` bytes with `builder.program()[0]`.

`model.py` is an original exact-instruction software oracle. Tests inject a
halt before each instruction, invisible stores, wrong identities, invalid EL,
partial reads and source mutations. They verify the publication sequence,
exclusive owned-store range, no BSS continuation, stack/LR preservation and
terminal-stop interpretation. This model is not Apple firmware emulation and
does not validate native fetch, coherency, secondary release or performance.
