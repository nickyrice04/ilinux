# 31AC integrated visible-entry diagnostic

This original, nonreturning AArch64 payload integrates entry capture, an owned
stack and fatal vectors, bounded argument snapshots, the frozen 31AB framebuffer
planner, actual address-translation checks, and a 32 by 16 pixel marker. It makes
no monitor call, starts no CPU, installs no translation table, and does not change
translation controls or memory attributes. Native acceptance and display
visibility remain untested; the RAM record is not an independently available
native observer.

`run.py` compiles five objects, links at zero and `0x40400000`, audits the ELF
geometry and selected instruction classes, and requires identical payload bytes.
It verifies both frozen observer source hashes before compiling and rehashes all
inputs at completion. Original `memcpy`/`memset` leaf routines satisfy the C
runtime dependencies. The linked image has no unresolved symbols or retained
relocations. The audit is not a proof of every generated C instruction's effect.

```sh
python3 kernel/experiments/visible31ac/run.py --output build/visible31ac-new --cc cc --ld ld
```

The output directory must be fresh. GNU AArch64 tools are used in the isolated
Linux build. A host compile-only check can instead specify
`--cc clang --target aarch64-none-elf --compile-only`; it neither links nor runs
the payload. The runner itself never executes it. Emulator and Mach-O packaging
tests are separate, parent-owned work.

The exact `payload.bin` is `0x24000` bytes. Header canvas `0..0x4000` is zero;
owned data occupies `0x4000..0x10000`, including the 512-byte record at `0x4000`
and 32 KiB stack at `0x8000..0x10000`. Entry is at `0x10000`, vectors at `0x10800`,
and all executing code is in the initial boot region `0x10000..0x20000`. The
late region `0x20000..0x24000` contains only an unused self-branch. `layout.json`
exports linked symbol offsets and every numeric `V31_*` constant from `layout.h`.
The packager owns its additional metadata and link-edit regions.

Entry first captures full x0/x1/x2, CurrentEL, incoming DAIF and SP without using
the incoming stack or dereferencing argument pointers. It initializes its own
record and masks DAIF. At EL2 it selects its owned SP and VBAR_EL2 and captures
HCR_EL2, SCTLR_EL2, TCR_EL2 and MMFR3. Writes to the owned record/stack and fetching
initial code already require the loader's image mappings; this cannot be checked
before the first instruction. EL0 can trap before recording anything. Fatal
vectors record the current EL2 exception and park; they do not handle a trap
routed to another EL or guarded mode, or resume a monitor exception.

The C bridge accepts cold reason zero, incoming fully masked DAIF, EL2, MMU on,
little-endian data accesses, and HCR E2H/TGE either both zero or both one. Mixed
profiles refuse. Non-VHE EL2 uses the 64-bit translation format. In VHE, D128
capability zero needs no TCR2 read; capability one requires TCRX one and inactive
TCR2_EL2.D128. Other D128 encodings refuse. PS/IPS values zero through six are
accepted in the applicable TCR layout; seven refuses. DS is retained, not used
as a format refusal. Explicit AT S1E2R/W applies to both accepted regimes, and
the 64-bit PAR decoder retains PA bits 51:12. This new host owns PAR state and
restores only the sampled low 64 bits; it never returns to its producer. Existing
HA/HD remain unchanged. AT may have normal architectural access-flag effects,
so these checks are not described as universally read-only.

Before each external snapshot, AT checks the first byte and every intersecting
4 KiB boundary across the complete range. Sources must translate with Normal NC
`0x44` or Normal WB `0xff` attributes. Only then does a volatile byte copy read
them into owned storage. The selected inputs are the 88-byte boot prefix at x1;
24 bytes at x2+416 containing helper version 10 and count/table pointers; a u32
count from the count pointer; and exactly 24 times count bytes from the table
pointer, with count in 1..64. These are selected qualified fields, not a complete
monitor ABI. Unavailable pre-service15 data refuses without initializing it.
Re-reading helper/count detects an observed change but supplies no atomicity,
producer authentication, lock or lifetime guarantee.

The frozen observer validates revision/version 2, the six video words at offset
40, physical base with only its low two bits removed, depth low byte 30 or 32,
range arithmetic, 16 KiB range alignment, and unambiguous physical/virtual table
intervals. It plans the top-left raw 32 by 16 pixel rectangle without rotation or
scale interpretation. Every touched framebuffer page then passes write AT with
the complete expected PA and NC/WB attribute. The image and all snapshot-source
physical 4 KiB pages are protected against framebuffer aliases. This bounded
48-page list refuses excess rather than omitting protection.

All rows are validated before the first framebuffer store. NC rows need only
volatile 32-bit stores and DSB SY. For WB rows, CTR_EL0 DminLine supplies the line
size; this prototype accepts 16..2048 bytes. Every rounded clean-line interval
must remain inside the declared framebuffer, translate through the same PAPT
table to the same VA, and lie on the already validated and unprotected physical
page. At most 160 unique lines are retained. After painting, DC CVAC cleans those
lines to PoC and DSB SY completes the sequence; no invalidation occurs. Cleaning
can cover bytes outside the rectangle but not outside those checked intervals.
PoC completion does not prove scanout visibility or guarded-mode permission.
Mappings and source ownership must remain stable between checks and use.

Stage 7 means the payload completed its stores and ordering; it does not mean
monitor readiness or firmware acceptance. Stage `0x80` records a bounded refusal,
and `0xdead` records a fatal exception. `status`, last VA/PAR, expected PA,
paint-attempt flag, painted-pixel count, planned/completed clean counts and line
size distinguish those outcomes. Refusals during validation perform no pixel
store. A later actual store/clean exception can leave a partial marker, and the
record is best-effort when its own mapping faults. The marker is intentionally
small on a Retina display and needs close visual observation in any separately
authorized native test.

Behavioral provenance: the selected fields and current host regime are recorded
in the 31AB/31AC research notes; public architectural qualifications come from
the collaborating 31AC primary-source review. No Apple binary instructions,
decompiler text or SDK headers are included. Frozen 31AB implementation and
source manifests remain unchanged.
