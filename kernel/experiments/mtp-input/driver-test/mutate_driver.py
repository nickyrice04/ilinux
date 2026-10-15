#!/usr/bin/env python3
"""Mutation check for the ring-transport changes in dockchannel-hid.c.

usage: python3 -I mutate_driver.py DRIVER_C DCHID_RING_H [CC]

Applies one textual mistake at a time to a copy of the patched driver, builds
test_driver.c against it and requires the harness to fail (non-zero exit,
sanitizer report or hang). A mutant that still passes means the harness is too
weak for that behaviour. Stdlib only; compiled binaries run only in a temp dir.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import driver_build  # noqa: E402

HERE = Path(__file__).resolve().parent
DRIVER = Path(sys.argv[1])
HEADER = Path(sys.argv[2])
CC = sys.argv[3] if len(sys.argv) > 3 else "clang"

MUTANTS = [
    ("handshake without the 100 ms delay",
     "msecs_to_jiffies(RING_HANDSHAKE_DELAY_MS));\n\n\tif (hdr.hdr_len", "0);\n\n\tif (hdr.hdr_len"),
    ("awake report says asleep",
     "dchid_enc_awake(cmd, true);", "dchid_enc_awake(cmd, false);"),
    ("ring registered with the data size instead of the total size",
     "dchid_enc_register_fifo(cmd, dchid->ring_iova, dchid->ring.size);",
     "dchid_enc_register_fifo(cmd, dchid->ring_iova, dchid->ring.cap);"),
    ("ring registered at IOVA 0",
     "dchid_enc_register_fifo(cmd, dchid->ring_iova, dchid->ring.size);",
     "dchid_enc_register_fifo(cmd, 0, dchid->ring.size);"),
    ("no ring drain after a DockChannel read",
     "\tif (dchid->ring_mode)\n\t\tdchid_ring_drain(dchid);\n\n\tdockchannel_await(",
     "\tdockchannel_await("),
    ("handshake re-armed on every packet",
     "!atomic_xchg(&dchid->handshake_started, 1)", "1"),
    ("ready STM does not cancel the fallback",
     "\t\tcancel_delayed_work(&dchid->stm_work);\n", ""),
    ("inactive ready status is treated as ready",
     "if (dchid->ring_mode && length >= 4 && get_unaligned_le16(pkt + 2)) {",
     "if (0) {"),
    ("ring mode rejects a bare ack like FIFO mode",
     "\t\tif (!iface->dchid->ring_mode) {\n\t\t\tdev_err(iface->dchid->dev, \"Received length 0 output report ack\\n\");",
     "\t\tif (1) {\n\t\t\tdev_err(iface->dchid->dev, \"Received length 0 output report ack\\n\");"),
    ("ack header status byte ignored",
     "if (iface->dchid->ring_mode && (hdr->pad >> 8))", "if (0)"),
    ("empty descriptor block replaces a good descriptor",
     "\t\t\tif (blk->length)\n\t\t\t\tdchid_handle_descriptor(iface, data, blk->length);",
     "\t\t\tdchid_handle_descriptor(iface, data, blk->length);"),
    ("registration failure still marks the ring registered",
     "dchid->ring_registered = ret >= 0;", "dchid->ring_registered = true;"),
    ("type-0 frame with a body is dispatched",
     "\tif (hdr.channel == 0)\t\t/* valid, carries nothing (doorbell candidate) */\n\t\treturn;\n",
     ""),
    ("empty type-0 frame ignored in FIFO mode too",
     "\tif (dchid->ring_mode && hdr.channel == 0 && !hdr.length)\n\t\tgoto done;",
     "\tif (hdr.channel == 0 && !hdr.length)\n\t\tgoto done;"),
    ("ring DockChannel doorbell frame is an error",
     "\tif (dchid->ring_mode && hdr.channel == 0 && !hdr.length)\n\t\tgoto done;",
     "\tif (0)\n\t\tgoto done;"),
    ("ring smaller than the size announced",
     "mem = dmam_alloc_coherent(dev, size, &dchid->ring_iova, GFP_KERNEL);",
     "mem = dmam_alloc_coherent(dev, size / 2, &dchid->ring_iova, GFP_KERNEL);"),
    ("assembler buffer too small for a trackpad report",
     "dchid->ring_asm.cap = MAX_PKT_SIZE + sizeof(struct dchid_hdr);",
     "dchid->ring_asm.cap = 1024;"),
    ("ring mutex never released",
     "\t\tdchid_asm_reset(a);\n\t}\n\tmutex_unlock(&dchid->ring_lock);\n}",
     "\t\tdchid_asm_reset(a);\n\t}\n}"),
    ("ready-status block parsed with the wrong sense",
     "iface->inactive = get_unaligned_le16(data) == 1;", "iface->inactive = get_unaligned_le16(data) == 0;"),
    ("descriptor-less interface is created anyway",
     "\tif (dchid->ring_mode && !iface->hid_desc) {", "\tif (0) {"),
    ("poll tick does not drain",
     "\t/* Debug aid: finds out whether data reaches the ring when no doorbell is recognised. */\n\tdchid_ring_drain(dchid);\n",
     "\t/* Debug aid: finds out whether data reaches the ring when no doorbell is recognised. */\n"),
    ("checksum error drops everything queued behind it",
     "\t\t\tif (st != DCHID_ASM_E_CHECKSUM)\n\t\t\t\tdchid_ring_discard(dchid);",
     "\t\t\tdchid_ring_discard(dchid);"),
    ("framing error does not resynchronise",
     "\t\t\tif (st != DCHID_ASM_E_CHECKSUM)\n\t\t\t\tdchid_ring_discard(dchid);",
     ""),
    ("ring index error not recovered",
     "\t\t\tdchid_ring_reset(&dchid->ring);\n\t\t\tdchid_asm_reset(a);\n\t\t\tbreak;",
     "\t\t\tdchid_asm_reset(a);\n\t\t\tbreak;"),
    ("enable command sent although disabled by parameter",
     "\tif (mtp_enable_cmd) {\n\t\tret = dchid_enable_interface(iface);",
     "\tif (1) {\n\t\tret = dchid_enable_interface(iface);"),
    ("ring mode ignores the module parameter",
     "\tif (mtp_ring < 0)\n\t\tdchid->ring_mode = cfg && cfg->ring;\n\telse\n\t\tdchid->ring_mode = mtp_ring > 0;",
     "\tdchid->ring_mode = cfg && cfg->ring;"),
    ("ack flags are checked strictly in ring mode",
     "\t\t/* macOS matches an ack by its transfer id (seq) alone, so ring mode does too. */\n\t\tif (!iface->dchid->ring_mode) {",
     "\t\t/* macOS matches an ack by its transfer id (seq) alone, so ring mode does too. */\n\t\tif (1) {"),
    ("FIFO mode no longer stops at the transport block",
     "if (blk->type == INIT_TERMINATOR && !dchid->ring_mode)\n\t\t\tbreak;",
     "if (0)\n\t\t\tbreak;\n\t\tif (blk->type == INIT_TERMINATOR)\n\t\t\tdata += 0;"),
]


def build_and_run(work, source):
    tree, inc = driver_build.prepare_tree(work, source, HEADER)
    exe = Path(work) / "t"
    code, _, err = driver_build.run(
        driver_build.compile_cmd(CC, tree, inc, HERE / "test_driver.c", exe) + ["-w"], 300)
    if code:
        return "compile-error", err.strip().splitlines()[:3]
    code, out, err = driver_build.run([str(exe)], 180)
    if code == 124:
        return "fail", ["timeout"]
    lines = (err + out).strip().splitlines()
    fails = [line for line in lines if line.startswith("FAIL")]
    return ("pass" if code == 0 else "fail"), fails[:1] or lines[-1:]


def main():
    original = DRIVER.read_text()
    bad = 0
    with tempfile.TemporaryDirectory() as d:
        work = Path(d)
        status, _ = build_and_run(work, original)
        print("baseline:", status)
        if status != "pass":
            return 2
        for name, old, new in MUTANTS:
            if original.count(old) != 1:
                print("MUTATION SITE NOT FOUND:", name)
                bad += 1
                continue
            status, detail = build_and_run(work, original.replace(old, new))
            ok = status == "fail"
            print("%-62s %s" % (name, "caught" if ok else "SURVIVED (%s %s)" % (status, detail)))
            if not ok:
                bad += 1
    print("mutants: %d, survived/invalid: %d" % (len(MUTANTS), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
