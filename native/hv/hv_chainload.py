"""Chainload planning, layout gates and breadcrumb helpers (private iLinux tooling).

Pure functions: no m1n1 import, no serial port. Everything here is checked by
test_hv_chainload.py without a target. Never for upstream.

Four jobs:

* The breadcrumb strip. The M5 has no reachable UART, so a silent early hang
  is only visible on the screen. White square blocks are painted into the boot
  framebuffer by the host, by the copy stub and by the new m1n1; what is lit
  names the last completed step. Geometry and slot numbers are a shared
  contract (see SLOT_* below and paint_rows()):

  - slots 0-2: the host. Slot 0: the layout gate passed, nothing written to
    the target yet. Slot 1: image, SEPFW, boot_args copy and copy stub staged,
    read back and cache-cleaned. Slot 2: everything staged and verified; it is
    painted immediately BEFORE the live ADT is patched and the handoff is
    issued, so that no target write follows the ADT patch except cache
    maintenance. boot021's own fb_update()/fb_shutdown copy their shadow
    framebuffer over the hardware framebuffer after the host painted, so
    these may be ERASED before the stub runs. They only show host progress if
    the host stalls before the handoff.
  - slot 3: the entry mark of the painting stub, its FIRST act: one 24x24
    block painted before the copy loop. 'Slot 3 lit, no bar' therefore means
    the stub was ENTERED and its copy loop, clear pass or bar pass did not
    finish. The bar below covers it, so the success state is unchanged.
  - slots 0-4: the copy stub's bar. After its copy loop it first CLEARS the
    whole strip rectangle (slots 0-20, so stale blocks from an earlier
    chainload in the same power cycle cannot be misread, the entry mark
    included) and then paints ONE solid bar over slots 0-4. Reaching the bar
    proves that host steps 0-2 completed and the copy loop finished.
  - slots 5-20: the new m1n1, steps c0..c15. It paints only when its own
    guard accepts the geometry (m1n1_will_paint(): what the stub needs plus a
    stride of at most 0x10000 and a height of at most 0x4000), and c9..c15
    only from a 16K aligned framebuffer base (m1n1_painted_steps(): 16, 9 or
    0 steps).
  Success on screen is: the bar (slots 0-4) plus every slot the new m1n1 can
  paint lit (5-20 normally). For the stock control build, which paints no
  c-blocks, it is the bar only. Where the stub cannot paint, the new m1n1
  will not either, and the screen cannot show success at all.
  Reading the screen after the handoff:

      nothing lit        the host never reached the handoff, boot021 hung in
                         its own shutdown, or the stub faulted before its
                         first store
      slot 3 only        the stub was entered; copy loop / clear / bar did not
                         finish
      bar (slots 0-4)    the stub finished; the new m1n1 died before c0
      bar + k blocks     the new m1n1 completed c0..c(k-1)
* The copy stub, the in-tree m1n1 chainload loop plus an optional entry mark,
  clear and paint passes. All literals sit in an 8-byte aligned pool: the stub
  runs with the MMU off, where every data access is Device memory and an
  unaligned 8-byte load faults. (hv002's stub had its literal at offset 36.)
  The copy loop ends only when its byte count reaches exactly 0, so the copy
  length must be a positive multiple of 16 (Plan enforces it).
* The layout: where the new image, SEPFW and boot_args land (identical to
  src/chainload.c in the pinned m1n1 with no variables) and the read-only
  gates that refuse a plan that would overwrite the ADT or the framebuffer,
  that stages over live data, or that repeats a chainload in the same power
  cycle.
  The live boot_args may lie inside the destination: the new m1n1 uses the
  staged copy, so overwriting iBoot's original of a FIRST chainload is
  harmless (a NOTE). It is a problem only when the live boot_args sit exactly
  at the planned boot_args address, which is what an earlier chainload in
  this power cycle leaves behind.
  The destination may overlap the START of the staging block (the copy
  source, with the stub at staging + image_size) in exactly one arrangement:
  destination start below staging start. The stub's loop is ascending, so a
  write at destination + 16*i only reaches source bytes that were read in an
  iteration <= i, and the stub sits above the destination end. That is what
  src/chainload.c does when _base + image_size lies above top_of_kernel_data,
  where its malloc'd buffer begins. It is a NOTE there; it is a problem when
  the destination starts at or above the staging start or would reach the
  stub.
  Independent of the destination, the host WRITES the staging block before
  the handoff, so it must not sit on live data: a staging block that starts
  below the current top_of_kernel_data (inside live kernel data) is a
  problem, and so is one that overlaps the original source range of any blob
  the flow relocates (the SEPFW copy would read bytes the staging already
  overwrote). Overlapping any other valid memory-map blob is only a NOTE
  (some 16-byte ADT values are not ranges). The launcher's staging block is
  utils.malloc() from the ProxyUtils heap, which starts 128 MiB above m1n1's
  own heap pointer, so it is normally clear of all of this.
* top_of_kernel_data. The new instance is handed
  align_up(max(current top_of_kernel_data, destination end), 16K). The in-tree
  flow and upstream chainload.py use the destination end alone, which can
  LOWER the value below live iBoot structures (the ADT and the memory-map
  blobs that are not moved sit between the m1n1 image and the old top). The
  new m1n1 starts its non-freeing heap AT top_of_kernel_data (heapblock_init)
  and fb_init() takes a framebuffer-sized shadow (about 30 MB) from it, so a
  lowered top would grow the heap over those structures. With the maximum the
  new heap starts where the old one did, and every blob that is not moved
  stays below it.
"""
import dataclasses
import struct
from types import SimpleNamespace

U64_MAX = (1 << 64) - 1
SENTINEL = U64_MAX  # iBoot's "no such blob" value for both address and size

# --- breadcrumb strip contract ------------------------------------------------
BLOCK = 24      # pixels, square
PITCH = 28      # pixels between block origins
ORIGIN_X = 8
ORIGIN_Y = 4
SLOTS = 21
COLOR = 0xFFFFFFFF  # white in x8r8g8b8 and x2r10g10b10
BYTES_PER_PIXEL = 4

SLOT_HOST_GATE = 0      # layout gate passed, nothing written to the target yet
SLOT_HOST_STAGED = 1    # image, SEPFW, boot_args copy and copy stub staged, read back, cleaned
# Everything staged and verified; painted immediately BEFORE the live ADT write
# and the handoff (nothing but cache maintenance follows the ADT patch).
SLOT_HOST_HANDOFF = 2
# The painting stub's entry mark, painted before its copy loop; the final bar
# (slots 0..SLOT_STUB) covers it again.
SLOT_STUB_ENTERED = 3
SLOT_STUB = 4           # last slot of the stub bar (bar = slots 0..SLOT_STUB)
SLOT_M1N1_FIRST = 5     # new m1n1 steps c0..c15 occupy slots 5..20
M1N1_STEPS = 16
STUB_BAR_SLOTS = SLOT_STUB + 1


def m1n1_slot(step):
    if not 0 <= step < M1N1_STEPS:
        raise ValueError("m1n1 breadcrumb step out of range")
    return SLOT_M1N1_FIRST + step


STRIP_WIDTH = ORIGIN_X + SLOTS * PITCH  # pixels the strip needs, margin included
# Pixel extents the stub stores (rows are BLOCK high): the cleared strip rectangle
# runs from slot 0 to the right edge of slot 20, the bar from slot 0 to the right
# edge of slot 4. Both are movz immediates in the stub.
STRIP_PIXELS = (SLOTS - 1) * PITCH + BLOCK
BAR_PIXELS = (STUB_BAR_SLOTS - 1) * PITCH + BLOCK
# Byte offset of slot SLOT_STUB_ENTERED from the strip origin (an add immediate).
STUB_MARK_OFFSET = SLOT_STUB_ENTERED * PITCH * BYTES_PER_PIXEL
assert 0 < BLOCK < 0x10000 and 0 < BAR_PIXELS < STRIP_PIXELS < 0x10000
assert 0 < STUB_MARK_OFFSET < 0x1000 and SLOT_STUB_ENTERED <= SLOT_STUB


def _video_fields(video):
    try:
        return tuple(int(getattr(video, name)) for name in
                     ("base", "stride", "width", "height", "depth"))
    except (AttributeError, TypeError, ValueError):
        return None


def video_ok(video):
    """True when the strip may be painted into this boot framebuffer."""
    fields = _video_fields(video)
    if fields is None:
        return False
    base, stride, width, height, depth = fields
    return (base != 0 and base % 4 == 0 and (depth & 0xFF) in (30, 32) and
            width >= STRIP_WIDTH and height >= ORIGIN_Y + BLOCK and
            stride >= STRIP_WIDTH * BYTES_PER_PIXEL)


def slot_address(video, slot):
    """Address of the top-left pixel of a slot (no eligibility check)."""
    base, stride = int(video.base), int(video.stride)
    return base + ORIGIN_Y * stride + (ORIGIN_X + slot * PITCH) * BYTES_PER_PIXEL


def paint_rows(video, slot):
    """[(address, 24 white pixels)] for one slot; empty when painting is skipped."""
    if not video_ok(video) or not 0 <= slot < SLOTS:
        return []
    stride = int(video.stride)
    first = slot_address(video, slot)
    row = struct.pack("<I", COLOR) * BLOCK
    return [(first + r * stride, row) for r in range(BLOCK)]


def stub_paint(video):
    """(slot 0 address, stride in bytes) for the stub, or None when it must not paint.

    Besides video_ok(), the stub stores 4-byte words with the MMU off, so the
    strip origin and every row address must be 4-byte aligned. This is THE
    predicate for the stub bar: the launcher's banner and handoff text use it,
    never video_ok() alone.
    """
    if not video_ok(video):
        return None
    stride = int(video.stride)
    if stride % 4:
        return None
    return slot_address(video, 0), stride


# The hv003 patch's own painter guard (ilinux_crumb_geometry_ok in src/startup.c) is the host's
# video_ok() plus a 4-byte aligned stride (so exactly stub_paint()) and these two ceilings.
M1N1_MAX_STRIDE = 0x10000
M1N1_MAX_HEIGHT = 0x4000


def m1n1_will_paint(video):
    """True when the new m1n1's painter guard accepts this framebuffer.

    That guard rejects exactly what stub_paint() rejects (not eligible, stride
    not a multiple of 4) and, beyond it, a stride above M1N1_MAX_STRIDE, a
    height above M1N1_MAX_HEIGHT and a stride * height that wraps the address
    space. So whenever the stub cannot paint, the new m1n1 will not either.
    """
    if stub_paint(video) is None:
        return False
    _, stride, _, height, _ = _video_fields(video)
    return (stride <= M1N1_MAX_STRIDE and height <= M1N1_MAX_HEIGHT and
            int(video.base) + stride * height <= U64_MAX)


# c0..c8 are painted before mmu_init() (MMU off, any 4-byte aligned base works); from c9 on
# the MMU is on and the painter must map the framebuffer first, which needs a 16K aligned base
# (it returns without painting otherwise, and so does every later step).
M1N1_MMU_OFF_STEPS = 9


def m1n1_painted_steps(video):
    """How many of the new m1n1's steps c0, c1, ... can paint here: 0, 9 or 16."""
    if not m1n1_will_paint(video):
        return 0
    return M1N1_STEPS if int(video.base) % 0x4000 == 0 else M1N1_MMU_OFF_STEPS


def strip_mode(video):
    """'bar' when the stub will paint, 'host' when only the host can paint (the stub and the
    new m1n1 both reject the geometry), else 'none' (not even the host paints)."""
    if stub_paint(video) is not None:
        return "bar"
    return "host" if video_ok(video) else "none"


# --- copy stub ------------------------------------------------------------------
# Source text (clang -c -target arm64-apple-macos, one instruction per word).
# Registers on entry, as handed over by proxy.reload() and src/chainload_asm.S:
# x0 = boot_args (kept for m1n1's _start), x1 = source, x2 = destination,
# x3 = length. The copy loop is the in-tree one; the pool is 8-byte aligned.
_COPY_SOURCE = """\
1:      ldp x5, x6, [x1], #16
        stp x5, x6, [x2]
        dc cvau, x2
        ic ivau, x2
        add x2, x2, #16
        sub x3, x3, #16
        cbnz x3, 1b
        dsb ish
        isb
"""
STUB_SOURCE = _COPY_SOURCE + """\
        ldr x4, 2f
        br x4
        .p2align 3
2:      .quad {entry}
"""
# Painting variant, part 1: the ENTRY MARK, before the copy loop. Loads the pool
# values and paints one BLOCK x BLOCK white block at slot SLOT_STUB_ENTERED
# (strip origin + STUB_MARK_OFFSET bytes) using only x7-x12, so x0-x3 (boot_args,
# copy arguments) and x5/x6 (copy loop) are untouched. x7 walks the rows, x8 is
# the stride, x9 the colour, x10 the row counter, x11 the pixels of the row.
_MARK_SOURCE = """\
        ldr x7, 2f
        ldr x8, 3f
        ldr x9, 4f
        add x7, x7, #{mark_off}
        mov w10, #{block}
10:     mov x11, x7
        mov w12, #{block}
11:     str w9, [x11], #4
        subs w12, w12, #1
        b.ne 11b
        add x7, x7, x8
        subs w10, w10, #1
        b.ne 10b
        dsb sy
"""
# Part 3: after the copy loop and barriers (boot021's own redraw has already
# finished by now): pass 1 stores 0 over the whole strip rectangle (BLOCK rows
# of STRIP_PIXELS pixels from slot 0), pass 2 stores white over slots
# 0..SLOT_STUB (BLOCK rows of BAR_PIXELS pixels). x11/x5 walk the row starts,
# x9 the pixels; x0 is never touched. The pool is read again (the entry mark
# used other registers).
_PAINT_TAIL_SOURCE = """\
        ldr x5, 2f
        ldr x6, 3f
        ldr x7, 4f
        mov x11, x5
        mov w8, #{rows}
6:      mov x9, x11
        mov w10, #{strip_px}
7:      str wzr, [x9], #4
        subs w10, w10, #1
        b.ne 7b
        add x11, x11, x6
        subs w8, w8, #1
        b.ne 6b
        mov w8, #{rows}
8:      mov x9, x5
        mov w10, #{bar_px}
9:      str w7, [x9], #4
        subs w10, w10, #1
        b.ne 9b
        add x5, x5, x6
        subs w8, w8, #1
        b.ne 8b
        dsb sy
        ldr x4, 5f
        br x4
        .p2align 3
2:      .quad {origin}
3:      .quad {stride}
4:      .quad {color}
5:      .quad {entry}
"""
# Entry mark, then the in-tree copy loop and barriers, then the clear and bar
# passes. Fill in with stub_paint_source().
STUB_PAINT_SOURCE = _MARK_SOURCE + _COPY_SOURCE + _PAINT_TAIL_SOURCE


def stub_paint_source(origin, stride, color, entry):
    """STUB_PAINT_SOURCE with the contract geometry and the four pool values."""
    return STUB_PAINT_SOURCE.format(mark_off=STUB_MARK_OFFSET, block=BLOCK, rows=BLOCK,
                                    strip_px=STRIP_PIXELS, bar_px=BAR_PIXELS,
                                    origin=origin, stride=stride, color=color, entry=entry)


# Words as printed by `otool -t` for the sources above (little-endian
# instruction values); test_hv_chainload.py re-assembles and compares.
_STUB_WORDS = (
    0xa8c11825, 0xa9001845, 0xd50b7b22, 0xd50b7522, 0x91004042, 0xd1004063,
    0xb5ffff43, 0xd5033b9f, 0xd5033fdf, 0x58000064, 0xd61f0080, 0xd503201f)
_STUB_PAINT_WORDS = (
    0x58000607, 0x58000628, 0x58000649, 0x910540e7, 0x5280030a, 0xaa0703eb,
    0x5280030c, 0xb8004569, 0x7100058c, 0x54ffffc1, 0x8b0800e7, 0x7100054a,
    0x54ffff21, 0xd5033f9f, 0xa8c11825, 0xa9001845, 0xd50b7b22, 0xd50b7522,
    0x91004042, 0xd1004063, 0xb5ffff43, 0xd5033b9f, 0xd5033fdf, 0x58000325,
    0x58000346, 0x58000367, 0xaa0503eb, 0x52800308, 0xaa0b03e9, 0x5280490a,
    0xb800453f, 0x7100054a, 0x54ffffc1, 0x8b06016b, 0x71000508, 0x54ffff21,
    0x52800308, 0xaa0503e9, 0x5280110a, 0xb8004527, 0x7100054a, 0x54ffffc1,
    0x8b0600a5, 0x71000508, 0x54ffff21, 0xd5033f9f, 0x58000104, 0xd61f0080)
STUB_CODE = struct.pack("<%dI" % len(_STUB_WORDS), *_STUB_WORDS)
STUB_PAINT_CODE = struct.pack("<%dI" % len(_STUB_PAINT_WORDS), *_STUB_PAINT_WORDS)
STUB_MAX = 0x100  # room reserved after the image in the staging block
POOL_QWORDS = 4   # origin, stride, colour, entry (painting variant)
assert len(STUB_PAINT_CODE) % 8 == 0 and len(STUB_CODE) % 8 == 0
assert len(STUB_PAINT_CODE) + 8 * POOL_QWORDS <= STUB_MAX


def stub(entry, paint=None):
    """Copy stub bytes; paint=(slot_0_addr, stride_bytes) adds the entry mark, clear and bar."""
    if not 0 <= entry <= U64_MAX or entry % 4:
        raise ValueError("stub entry must be a 4-byte aligned 64-bit address")
    if paint is None:
        return STUB_CODE + struct.pack("<Q", entry)
    origin, stride = paint
    if not 0 <= origin <= U64_MAX or origin % 4:
        raise ValueError("breadcrumb strip address must be 4-byte aligned")
    if not 0 < stride <= U64_MAX or stride % 4:
        raise ValueError("breadcrumb stride must be a positive multiple of 4")
    if origin + (BLOCK - 1) * stride + STRIP_PIXELS * BYTES_PER_PIXEL > U64_MAX:
        raise ValueError("breadcrumb strip rectangle wraps the address space")
    return STUB_PAINT_CODE + struct.pack("<QQQQ", origin, stride, COLOR, entry)


def check_stub_size(code):
    """Raise unless the stub fits the room reserved behind the image (call BEFORE writing it)."""
    if len(code) > STUB_MAX:
        raise ValueError("copy stub is %d bytes, more than the %d bytes reserved after the image"
                         % (len(code), STUB_MAX))
    return code


COPY_GRANULE = 16   # bytes per iteration of the copy loop


def check_copy_length(length):
    """The copy loop ends only when its count reaches exactly 0 (sub x3, x3, #16)."""
    if not isinstance(length, int) or length <= 0 or length % COPY_GRANULE:
        raise ValueError("copy length must be a positive multiple of %d bytes (the stub's copy "
                         "loop ends only when the count reaches exactly 0)" % COPY_GRANULE)
    return length


# --- layout -----------------------------------------------------------------------
ALIGN = 0x4000
BOOTARGS_SIZE = 0x4000   # space reserved for boot_args inside the image
BOOT_ARGS_LEN = 0x480    # sizeof(struct boot_args) in the pinned m1n1
TOP_OF_KERNEL_DATA_OFFSET = 0x20
ENTRY_OFFSET = 0x800


def align_up(value, alignment=ALIGN):
    return (value + alignment - 1) & ~(alignment - 1)


@dataclasses.dataclass(frozen=True)
class Plan:
    """Where the chainloaded image sits; offsets are from new_base."""
    image_len: int      # bytes of m1n1 image, before the 4 zero pad bytes
    new_base: int
    sepfw: object       # (address, size) as in the ADT, or None when absent
    sepfw_off: int
    bootargs_off: int
    image_size: int     # total region copied to new_base
    overflow: bool      # arithmetic left 64 bits

    def __post_init__(self):
        # image_size is the stub's x3: a value that is not a positive multiple
        # of 16 would never reach 0 and the loop would copy until it faults.
        check_copy_length(self.image_size)

    @property
    def region(self):
        return (self.new_base, self.image_size)

    @property
    def entry(self):
        return self.new_base + ENTRY_OFFSET

    @property
    def bootargs_address(self):
        """Where the staged boot_args copy ends up (the new instance's P_GET_BOOTARGS answer)."""
        return self.new_base + self.bootargs_off

    @property
    def sepfw_address(self):
        """Where the relocated SEPFW ends up."""
        return self.new_base + self.sepfw_off


def plan_layout(image_len, new_base, sepfw):
    """src/chainload.c with no variables: image + 4, 16K align, SEPFW, 16K, boot_args."""
    sepfw_size = int(sepfw[1]) if sepfw else 0
    sepfw_off = align_up(image_len + 4)
    bootargs_off = align_up(sepfw_off + sepfw_size)
    image_size = bootargs_off + BOOTARGS_SIZE
    overflow = (image_size > U64_MAX or new_base + image_size > U64_MAX or
                (bool(sepfw) and sepfw[0] + sepfw[1] > U64_MAX))
    return Plan(image_len, new_base, tuple(sepfw) if sepfw else None, sepfw_off,
                bootargs_off, image_size, overflow)


def plan_with_blobs(image_len, new_base, sepfw, sepfw_off, bootargs_off, image_size):
    """Plan for the Python flow, where m1n1.bootmem decides the offsets."""
    overflow = (image_size > U64_MAX or new_base + image_size > U64_MAX or
                (bool(sepfw) and sepfw[0] + sepfw[1] > U64_MAX))
    return Plan(image_len, new_base, tuple(sepfw) if sepfw else None, sepfw_off,
                bootargs_off, image_size, overflow)


@dataclasses.dataclass(frozen=True)
class Facts:
    """What the live target looks like; every range is (start, size) or None."""
    adt: object
    boot_args: object
    framebuffer: object   # None when boot_args.video.base == 0
    staging: object       # None when it could not be allocated
    ram: object
    memory_map: dict      # name -> (address, size)
    top: object = None    # current top_of_kernel_data (None when unknown)


def overlaps(a, b):
    """True when two (start, size) ranges share at least one byte."""
    if not a or not b or a[1] <= 0 or b[1] <= 0:
        return False
    return a[0] < b[0] + b[1] and b[0] < a[0] + a[1]


def _inside(inner, outer):
    return outer[0] <= inner[0] and inner[0] + inner[1] <= outer[0] + outer[1]


def _safe(name):
    text = "".join(c if c.isalnum() or c in "_.+-" else "?" for c in str(name))
    return text[:32] or "?"


def sepfw_at_planned_address(plan):
    """True when the ADT's SEPFW already points where this plan would relocate it."""
    return (plan.sepfw is not None and SENTINEL not in plan.sepfw and plan.sepfw[1] != 0 and
            plan.sepfw[0] == plan.sepfw_address)


def boot_args_at_planned_address(plan, facts):
    """True when the live boot_args sit exactly where this plan stages its copy.

    That is what an earlier chainload in the same power cycle leaves behind.
    """
    return facts.boot_args is not None and facts.boot_args[0] == plan.bootargs_address


STAGING_NONE, STAGING_SAFE, STAGING_UNSAFE = "none", "safe", "unsafe"


def classify_staging_overlap(plan, staging, stub_address=None):
    """(state, reason) of the destination against the staging block.

    state is STAGING_NONE (disjoint), STAGING_SAFE (the destination starts
    below the staging block and ends below the stub: the ascending copy only
    overwrites source bytes it has already read) or STAGING_UNSAFE with the
    reason. stub_address defaults to staging start + plan.image_size, where
    the launcher writes the stub. A staging block below top_of_kernel_data is
    a separate rule (staging_below_top): it holds with or without an overlap.
    """
    if staging is None or not overlaps(plan.region, staging):
        return STAGING_NONE, None
    start, end = plan.new_base, plan.new_base + plan.image_size
    if stub_address is None:
        stub_address = staging[0] + plan.image_size
    if start >= staging[0]:
        return STAGING_UNSAFE, ("the destination starts at or above the staging block, so the "
                                "ascending copy would overwrite source bytes before reading them")
    if end > stub_address:
        return STAGING_UNSAFE, "the destination would overwrite the copy stub"
    return STAGING_SAFE, None


STAGING_NOTE = ("destination overlaps the start of the staging block; safe: ascending copy, "
                "destination below staging, stub above destination end")
STAGING_BELOW_TOP = "staging block lies below top_of_kernel_data, inside live kernel data"


def staging_below_top(facts):
    """True when the staging block starts below the current top_of_kernel_data (unknown: False)."""
    return (facts.staging is not None and facts.top is not None and
            facts.staging[0] < int(facts.top))


def blob_range(plan, facts, name):
    """(address, size) of a memory-map blob when it is a valid, non-wrapping range, else None.

    SEPFW comes from the plan (what the ADT said when it was read), every other
    name from facts.memory_map. The unset sentinel, size 0 and a range that
    wraps the address space are not ranges.
    """
    rng = plan.sepfw if name == "SEPFW" else facts.memory_map.get(name)
    if rng is None:
        return None
    addr, size = rng
    if addr == SENTINEL or size in (0, SENTINEL) or addr + size > U64_MAX:
        return None
    return addr, size


def staging_source_overlaps(plan, facts, moved):
    """Names of relocated blobs whose ORIGINAL source range the staging block overlaps."""
    if facts.staging is None:
        return []
    out = []
    for name in moved:
        rng = blob_range(plan, facts, name)
        if rng is not None and overlaps(facts.staging, rng):
            out.append(name)
    return out


def check_layout(plan, facts, moved=("SEPFW",)):
    """(problems, notes). Problems are fatal; notes are information only.

    moved names the memory-map blobs the flow relocates; any other blob the
    destination covers is overwritten, as in the in-tree flow.
    """
    problems, notes = [], []
    if plan.sepfw is None:
        problems.append("SEPFW is missing from the memory map")
    elif SENTINEL in plan.sepfw:
        problems.append("SEPFW is the unset (all-ones) sentinel")
    elif plan.sepfw[1] == 0:
        problems.append("SEPFW has size 0")
    if plan.overflow:
        problems.append("layout arithmetic overflows 64 bits")
        return problems, notes  # the region numbers mean nothing from here on
    dest = plan.region
    if plan.new_base % 8:
        problems.append("destination base is not 8-byte aligned (stub runs with the MMU off)")
    if facts.ram is None or facts.ram[1] <= 0:
        problems.append("RAM range unknown")
    elif not _inside(dest, facts.ram):
        problems.append("destination lies outside RAM")
    for label, rng in (("ADT", facts.adt), ("framebuffer", facts.framebuffer)):
        if rng is not None and overlaps(dest, rng):
            problems.append("destination overlaps the " + label)
    below_top = staging_below_top(facts)
    state, reason = classify_staging_overlap(plan, facts.staging)
    if state == STAGING_UNSAFE:
        problems.append("destination overlaps the staging block (%s)" % reason)
    elif state == STAGING_SAFE and not below_top:     # a block below the top is refused below
        notes.append(STAGING_NOTE)
    if boot_args_at_planned_address(plan, facts):
        problems.append("destination overlaps the boot_args at the planned boot_args address")
    elif facts.boot_args is not None and overlaps(dest, facts.boot_args):
        notes.append("live boot_args lies inside the destination; it will be overwritten, "
                     "m1n1 already copied it")
    if facts.staging is None:
        problems.append("staging block could not be allocated")
    else:
        if facts.staging[0] % 8:
            problems.append("staging block is not 8-byte aligned (stub runs with the MMU off)")
        if facts.ram is not None and facts.ram[1] > 0 and not _inside(facts.staging, facts.ram):
            problems.append("staging block lies outside RAM")
        for label, rng in (("ADT", facts.adt), ("boot_args", facts.boot_args),
                           ("framebuffer", facts.framebuffer)):
            if rng is not None and overlaps(facts.staging, rng):
                problems.append("staging block overlaps the " + label)
        if below_top:
            problems.append(STAGING_BELOW_TOP)
        for name in staging_source_overlaps(plan, facts, moved):
            addr, size = blob_range(plan, facts, name)
            problems.append("staging block overlaps the %s source (0x%x bytes at 0x%x): the "
                            "staged copy would read bytes the staging already overwrote"
                            % (_safe(name), size, addr))
    if sepfw_at_planned_address(plan):
        notes.append("SEPFW already points at the planned relocation address; if this is not "
                     "the first run since power-on, a previous chainload patched this ADT: "
                     "power off completely")
    for name in sorted(facts.memory_map):
        if name in moved:
            continue
        rng = blob_range(plan, facts, name)       # unset, empty and non-range values are skipped
        if rng is None:
            continue
        addr, size = rng
        if overlaps(dest, rng):
            notes.append("memory-map blob %s (0x%x bytes at 0x%x) lies in the destination "
                         "and will be overwritten" % (_safe(name), size, addr))
        if facts.staging is not None and overlaps(facts.staging, rng):
            notes.append("staging block overlaps memory-map blob %s (0x%x bytes at 0x%x); the "
                         "host writes it before the handoff" % (_safe(name), size, addr))
    return problems, notes


def layout_table(plan, facts, moved=("SEPFW",)):
    """Plain table of hex addresses and sizes; nothing else from the target."""
    dest = plan.region
    below_top = staging_below_top(facts)
    source_hits = staging_source_overlaps(plan, facts, moved)

    def row(label, rng, mark=""):
        if rng is None:
            return "%-26s %-18s %-18s %-10s %s" % (label, "-", "-", "-", mark)
        start, size = rng
        return "%-26s 0x%016x 0x%016x 0x%-8x %s" % (label, start, start + size, size, mark)

    def flag(rng):
        return "OVERLAPS DESTINATION" if rng is not None and overlaps(dest, rng) else ""

    staging_state, _ = classify_staging_overlap(plan, facts.staging)
    staging_marks = []
    if staging_state == STAGING_UNSAFE:
        staging_marks.append("OVERLAPS DESTINATION")
    elif staging_state == STAGING_SAFE:
        staging_marks.append("OVERLAPS DESTINATION START" if below_top else
                             "OVERLAPS DESTINATION START (note: ascending copy, safe)")
    if below_top:
        staging_marks.append("BELOW top_of_kernel_data (live kernel data)")
    staging_marks += ["OVERLAPS %s SOURCE" % _safe(name) for name in source_hits]
    staging_mark = "; ".join(staging_marks)
    if boot_args_at_planned_address(plan, facts):
        ba_mark = "AT THE PLANNED boot_args ADDRESS (earlier chainload)"
    elif facts.boot_args is not None and overlaps(dest, facts.boot_args):
        ba_mark = "OVERLAPS DESTINATION (note: overwritten, already copied)"
    else:
        ba_mark = ""
    sepfw_marks = []
    if sepfw_at_planned_address(plan):
        sepfw_marks.append("AT THE PLANNED RELOCATION ADDRESS")
    if "SEPFW" in source_hits:
        sepfw_marks.append("OVERLAPPED BY STAGING")
    sepfw_mark = "; ".join(sepfw_marks)
    lines = ["%-26s %-18s %-18s %-10s" % ("REGION", "START", "END", "SIZE"),
             row("destination", dest),
             row("  m1n1 image (+4 pad)", (plan.new_base, plan.image_len + 4)),
             row("  SEPFW (relocated)", (plan.sepfw_address,
                                         plan.sepfw[1] if plan.sepfw else 0)),
             row("  boot_args", (plan.bootargs_address, BOOTARGS_SIZE)),
             row("RAM", facts.ram, "" if facts.ram and _inside(dest, facts.ram)
                 else "DESTINATION OUTSIDE"),
             row("ADT", facts.adt, flag(facts.adt)),
             row("boot_args (live)", facts.boot_args, ba_mark),
             row("framebuffer", facts.framebuffer, flag(facts.framebuffer)),
             row("staging block", facts.staging, staging_mark),
             row("SEPFW (current)", plan.sepfw, sepfw_mark)]
    for name in sorted(facts.memory_map):
        if name in moved:
            continue
        rng = blob_range(plan, facts, name)
        if rng is None:
            continue
        marks = []
        if overlaps(dest, rng):
            marks.append("OVERLAPS DESTINATION")
        if facts.staging is not None and overlaps(facts.staging, rng):
            marks.append("OVERLAPPED BY STAGING (note)")
        if marks:
            lines.append(row("blob " + _safe(name), rng, "; ".join(marks)))
    return "\n".join(lines)


def video_report(video):
    """Lines describing the boot framebuffer and the strip decisions (hex and words only)."""
    fields = _video_fields(video)
    if fields is None:
        return ["framebuffer fields unavailable: breadcrumb strip disabled"]
    base, stride, width, height, depth = fields
    paint = stub_paint(video)

    def yn(value):
        return "yes" if value else "no"

    return [
        "framebuffer base 0x%x stride 0x%x width 0x%x height 0x%x" % (base, stride, width, height),
        "framebuffer depth field 0x%x, bpp 0x%x, RETINA flag (0x10000) %s"
        % (depth, depth & 0xFF, "set" if depth & 0x10000 else "clear"),
        "framebuffer base 16K aligned: %s" % yn(base % 0x4000 == 0),
        "breadcrumb strip eligible for the host (video_ok): %s" % yn(video_ok(video)),
        "stub bar will paint (stub_paint): %s%s"
        % (yn(paint is not None),
           " (strip origin 0x%x, row stride 0x%x)" % paint if paint is not None else ""),
        "new m1n1 will paint (its guard: stub_paint, stride <= 0x%x, height <= 0x%x): %s"
        % (M1N1_MAX_STRIDE, M1N1_MAX_HEIGHT, yn(m1n1_will_paint(video))),
    ] + (["new m1n1 paints only c0-c8 (slots 5-13): the base is not 16K aligned, so it cannot map "
          "the framebuffer once the MMU is on (c9-c15, slots 14-20, will not paint)"]
         if m1n1_painted_steps(video) == M1N1_MMU_OFF_STEPS else [])


def new_top_of_kernel_data(plan, current_top):
    """The top_of_kernel_data the new instance is handed (see the module docstring).

    align_up(max(current top, destination end), 16K): never lower than iBoot's
    own value, so the new m1n1's heap starts where the old one did and stays
    above every blob that is not moved.
    """
    return align_up(max(int(current_top), plan.new_base + plan.image_size), ALIGN)


def top_report(plan, top_of_kernel_data, facts=None):
    """(lines, notes): current top_of_kernel_data, destination end and the chosen new top.

    Notes are information only. facts is accepted for call compatibility.
    """
    end = plan.new_base + plan.image_size
    top = int(top_of_kernel_data)
    new_top = new_top_of_kernel_data(plan, top)
    if end > top:
        relation = "ABOVE the current top by 0x%x" % (end - top)
    elif end < top:
        relation = "BELOW the current top by 0x%x" % (top - end)
    else:
        relation = "EQUAL to the current top"
    if new_top == top:
        choice = "= the current top (the new heap starts where the old one did)"
    else:
        choice = "= the destination end, 16K aligned (above the current top)"
    lines = ["top_of_kernel_data (current)    0x%016x" % top,
             "destination end                 0x%016x %s" % (end, relation),
             "top_of_kernel_data (new)        0x%016x %s" % (new_top, choice)]
    notes = []
    if end > top:
        notes.append("the destination ends above the current top_of_kernel_data by 0x%x; the new "
                     "top follows the destination end, so the new m1n1's heap starts above the "
                     "destination" % (end - top))
    return lines, notes


# --- raw boot_args ------------------------------------------------------------------
@dataclasses.dataclass(frozen=True)
class BootArgsView:
    revision: int
    version: int
    virt_base: int
    phys_base: int
    mem_size: int
    top_of_kernel_data: int
    video: object          # SimpleNamespace: base display stride width height depth
    devtree: int
    devtree_size: int

    @property
    def adt_address(self):
        """Physical address of the ADT, as ProxyUtils.get_adt() computes it."""
        return (self.devtree - self.virt_base + self.phys_base) & U64_MAX


def parse_boot_args(raw):
    """Fields common to revisions 1-3 (struct boot_args in src/xnuboot.h)."""
    if len(raw) < 0x6C:
        raise ValueError("boot_args too short")
    revision, version = struct.unpack_from("<HH", raw, 0)
    virt_base, phys_base, mem_size, top = struct.unpack_from("<4Q", raw, 8)
    base, display, stride, width, height, depth = struct.unpack_from("<6Q", raw, 0x28)
    devtree, devtree_size = struct.unpack_from("<QI", raw, 0x60)
    video = SimpleNamespace(base=base, display=display, stride=stride, width=width,
                            height=height, depth=depth)
    return BootArgsView(revision, version, virt_base, phys_base, mem_size, top, video,
                        devtree, devtree_size)


def with_top_of_kernel_data(raw, value):
    """The raw boot_args bytes with only the u64 at offset 0x20 replaced."""
    if len(raw) != BOOT_ARGS_LEN:
        raise ValueError("boot_args must be exactly 0x%x bytes" % BOOT_ARGS_LEN)
    if not 0 <= value <= U64_MAX:
        raise ValueError("top_of_kernel_data out of range")
    out = bytearray(raw)
    struct.pack_into("<Q", out, TOP_OF_KERNEL_DATA_OFFSET, value)
    return bytes(out)
