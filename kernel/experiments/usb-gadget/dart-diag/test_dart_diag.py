#!/usr/bin/env python3
"""Contract check of the boot040 apple-dart patches (job 041, in the VM, and on the Mac
against a patched scratch copy).

usage: test_dart_diag.py PATCHED_APPLE_DART_C

Part 1: the t8110 handler must report the raw ERROR, ERROR_MASK, ERROR_STREAMS, ERROR_ADDR
and TLB_CMD when the error flag is clear, rate-limited by count; return IRQ_NONE when
nothing is pending (the kernel's spurious-interrupt protection stays); acknowledge only
through ERROR and ERROR_STREAMS; never write TCR, TTBR, PROTECT, ENABLE/DISABLE_STREAMS or
ERROR_MASK, so translation and protection are untouched; keep the recognised-fault path
(name, address, write-back); and the probe must name each t8110 instance.
Part 2: the v2.2-layout handler must be reached only through the version gate
(g22_layout, set from PARAMS3 bits 15:0 >= 0x202 and a large enough window); read the
pending words, the protection status and the control register; return IRQ_NONE when nothing
is pending; write only the pending words back, all ones to the protection status, and the
flush-unlock command; disable the line after 256 acknowledgements; and the reset path may
add only the same acknowledgement writes plus the v2.2 mask. The file's digest must be the
one apply.py produced for both patches.
"""
import hashlib
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from apply import AFTER  # noqa: E402


def fail(message):
    raise SystemExit("dart-diag FAIL: " + message)


def function_body(text, name):
    start = re.search(r"^[^\n;]*\b%s\([^;{]*\)\s*\{" % re.escape(name), text, re.M)
    if not start:
        fail("no function " + name)
    end = text.index("\n}\n", start.start())
    return text[start.start():end]


def main(path):
    text = Path(path).read_text()
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != AFTER:
        fail("the file is not the patched apple-dart.c apply.py produces")
    irq = function_body(text, "apple_dart_t8110_irq")
    if irq.count("return IRQ_NONE;") != 1 or "if (!error && !any_stream)\n\t\t\treturn IRQ_NONE;" not in irq:
        fail("the handler must return IRQ_NONE exactly when nothing is pending")
    if "if (!(error & DART_T8110_ERROR_FLAG)) {" not in irq:
        fail("the flag check is gone")
    if "without the error flag" not in irq or "n <= 4 || n % 25000 == 0" not in irq:
        fail("the unrecognised-interrupt report or its count rate limit is missing")
    for reg in ("ERROR_MASK", "TLB_CMD", "ERROR_ADDR_LO", "ERROR_ADDR_HI", "ERROR_STREAMS"):
        if "DART_T8110_" + reg not in irq:
            fail("the handler does not read " + reg)
    writes = re.findall(r"writel\(([^;]*)\);", irq)
    allowed = ("writel(error, dart->regs + DART_T8110_ERROR)",
               "writel(U32_MAX, dart->regs + DART_T8110_ERROR_STREAMS + 4 * i)")
    for w in writes:
        if "writel(%s)" % w not in allowed:
            fail("unexpected register write in the handler: writel(%s)" % w)
    if len(writes) != 4:
        fail("expected two acknowledgement writes per path, found %d" % len(writes))
    for forbidden in ("DART_TCR(", "DART_TTBR(", "DART_T8110_TCR", "DART_T8110_TTBR", "DART_T8110_PROTECT",
                      "DART_T8110_UNPROTECT", "ENABLE_STREAMS", "DISABLE_STREAMS", "apple_dart_hw_",
                      "invalidate_tlb", "TLB_CMD)"):   # TLB_CMD is read only, never written
        if forbidden in irq.replace("readl(dart->regs + DART_T8110_TLB_CMD)", ""):
            fail("the handler touches " + forbidden)
    if '"translation fault: status:0x%x stream:%d code:0x%x (%s) at 0x%llx (fault #%u' not in irq:
        fail("the recognised-fault report changed shape")
    if "dart->faults_reported++;" not in irq:
        fail("recognised faults are not counted")
    streams = function_body(text, "apple_dart_t8110_error_streams")
    if "writel" in streams or "readl(dart->regs + DART_T8110_ERROR_STREAMS + 4 * i)" not in streams:
        fail("the stream bitmap helper must only read ERROR_STREAMS")
    probe = function_body(text, "apple_dart_probe")
    if '"t8110-class DART v%lu.%lu: PARAMS 0x%08x 0x%08x 0x%08x 0x%08x, %lu clients, fault IRQ %d, ERROR 0x%08x\\n"' not in probe:
        fail("the probe does not name the t8110 instance")
    if probe.count("writel") != 0:
        fail("the probe gained a register write")
    reset = function_body(text, "apple_dart_hw_reset")
    if reset.count("writel") != 3 or "writel(0,  dart->regs + DART_T8110_ERROR_MASK);" not in reset:
        fail("apple_dart_hw_reset changed beyond the v2.2 clear call")
    for name in ("apple_dart_hw_enable_translation", "apple_dart_hw_disable_dma", "apple_dart_hw_enable_bypass",
                 "apple_dart_hw_set_ttbr", "apple_dart_setup_translation", "apple_dart_t8110_hw_tlb_command"):
        function_body(text, name)   # still present
    if "u32 faults_reported;" not in text or "u32 irqs_without_flag;" not in text:
        fail("the counters are missing from struct apple_dart")

    # Part 2: the v2.2 layout.
    if "if (dart->g22_layout)\n\t\treturn apple_dart_t8110_g22_irq(irq, dart);" not in irq:
        fail("the v2.2 handler is not reached through the g22_layout gate at the top of the t8110 handler")
    if irq.index("return apple_dart_t8110_g22_irq") > irq.index("readl("):
        fail("the pre-2.2 registers are read before the version gate")
    g22 = function_body(text, "apple_dart_t8110_g22_irq")
    if g22.count("return IRQ_NONE;") != 1 or "if (!any) {" not in g22:
        fail("the v2.2 handler must return IRQ_NONE exactly when nothing is pending")
    g22_writes = re.findall(r"writel\(([^;]*)\);", g22)
    g22_allowed = ("writel(U32_MAX, dart->regs + prot_off)",
                   "writel(pending[i], dart->regs + DART_T8110_G22_PENDING + 4 * i)")
    for w in g22_writes:
        if "writel(%s)" % w not in g22_allowed:
            fail("unexpected register write in the v2.2 handler: writel(%s)" % w)
    if len(g22_writes) != 2:
        fail("expected exactly two acknowledgement writes in the v2.2 handler, found %d" % len(g22_writes))
    for forbidden in ("DART_TCR(", "DART_TTBR(", "DART_T8110_TCR", "DART_T8110_TTBR", "DART_T8110_PROTECT",
                      "DART_T8110_UNPROTECT", "ENABLE_STREAMS", "DISABLE_STREAMS", "apple_dart_hw_",
                      "invalidate_tlb", "G22_ERROR_MASK)"):   # the mask is read for the report, never written here
        if forbidden in g22.replace("readl(dart->regs + DART_T8110_G22_ERROR_MASK)", ""):
            fail("the v2.2 handler touches " + forbidden)
    for needed in ("DART_T8110_G22_PENDING", "DART_T8110_G22_STREAM_BLOCK(32 * i + sid)", "DART_T8110_G22_ADDR_LO",
                   "DART_T8110_G22_ADDR_HI", "DART_T8110_G22_SUMMARY_CODE", "DART_T8110_CTRL_FLUSH_UNLOCK_NEEDED",
                   "apple_dart_t8110_flush_unlock(dart)", "disable_irq_nosync(irq)", "== 256", "dart->faults_reported++;",
                   '"translation fault (v2.2 layout): stream %d code %u (%s) level %s at 0x%llx%s AXI id 0x%08x summary 0x%08x (fault #%u, IRQ %d)\\n"',
                   "n <= 4 || n % 25000 == 0"):
        if needed not in g22:
            fail("the v2.2 handler lacks " + needed)
    unlock = function_body(text, "apple_dart_t8110_flush_unlock")
    if unlock.count("writel") != 1 or "writel(val, dart->regs + DART_T8110_TLB_CMD);" not in unlock \
            or "FIELD_PREP(DART_T8110_TLB_CMD_OP, DART_T8110_TLB_CMD_OP_FLUSH_UNLOCK)" not in unlock \
            or "DART_T8110_TLB_CMD_G22_FLAG" not in unlock or "readl_poll_timeout_atomic" not in unlock \
            or "spin_lock_irqsave(&dart->lock, flags);" not in unlock:
        fail("flush-unlock must be one TLB_CMD write (op 4, bit 15) under the lock with a bounded busy wait")
    clear = function_body(text, "apple_dart_t8110_g22_clear")
    clear_writes = re.findall(r"writel\(([^;]*)\);", clear)
    if sorted(clear_writes) != sorted(["pending, dart->regs + DART_T8110_G22_PENDING + 4 * i",
                                       "U32_MAX, dart->regs + apple_dart_t8110_g22_prot_status_offset(dart)",
                                       "0, dart->regs + DART_T8110_G22_ERROR_MASK"]):
        fail("the v2.2 reset clear writes something other than the pending words, the protection status and the mask")
    if "if (dart->g22_layout)\n\t\t\tapple_dart_t8110_g22_clear(dart);" not in reset:
        fail("apple_dart_hw_reset does not clear the v2.2 state behind the gate")
    gate = ("dart->version = FIELD_GET(DART_T8110_PARAMS3_VERSION, dart_params[2]);",
            "if (dart->version >= DART_T8110_VERSION_2_2) {",
            "if (resource_size(res) < DART_T8110_G22_STREAM_BLOCK(dart->num_streams))",
            "dart->g22_layout = 1;")
    for needed in gate:
        if needed not in probe:
            fail("the probe's version gate lacks " + needed)
    for name, value in (("DART_T8110_VERSION_2_2", "0x0202"), ("DART_T8110_G22_PENDING", "0x4000"),
                        ("DART_T8110_G22_ERROR_MASK", "0x4060"), ("DART_T8110_CTRL", "0x210"),
                        ("DART_T8110_G22_PROT_STATUS", "0x704"), ("DART_T8110_G24_PROT_STATUS", "0x4204"),
                        ("DART_T8110_TLB_CMD_OP_FLUSH_UNLOCK", "4"), ("DART_T8110_TLB_CMD_G22_FLAG", "BIT(15)")):
        if not re.search(r"#define %s\s+%s(?=\s)" % (name, re.escape(value)), text):
            fail("%s is not %s" % (name, value))
    if "#define DART_T8110_G22_STREAM_BLOCK(sid) (0x8000 + 0x40 * (sid))" not in text:
        fail("the stream block is not at 0x8000 + 0x40*sid")
    print("dart-diag PASS: part 1 reports unrecognised fault IRQs (raw ERROR/MASK/STREAMS/ADDR/TLB_CMD, "
          "count-limited), IRQ_NONE when nothing is pending, acknowledges only ERROR and ERROR_STREAMS, names each "
          "t8110 instance at probe; part 2 (gated on PARAMS3 version >= 2.2) reports and acknowledges in the v2.2 "
          "layout (pending words, protection status, flush-unlock), IRQ_NONE when nothing is pending, disables the "
          "line after 256 acknowledgements; translation, protection and TLB-flush paths unchanged")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
