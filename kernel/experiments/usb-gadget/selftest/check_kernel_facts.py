#!/usr/bin/env python3
"""Check init.c's status readers against the exact kernel tree (job 041, in the VM).

usage: check_kernel_facts.py TREE INIT_C REGNAMES_OUT

Every file name, register name and text format the boot039 status line relies on
must be what this tree's code creates and prints:
  * drivers/usb/dwc3/debugfs.c creates link_state, regdump and the per-endpoint
    transfer_type and trb_ring files under usb_debug_root/<dev_name>;
  * every register init.c looks up is in dwc3_regs[], and fs/debugfs/file.c
    prints each as "NAME = 0x%08x";
  * the per-endpoint files init.c reads write no register, and the ones it avoids do;
  * trb_ring lines have nine comma-separated fields and end in the E/D markers;
  * /sys/kernel/irq/<n>/{actions,hwirq,per_cpu_count} exist, the Apple AIC puts the
    IRQ number in the low 16 bits of hwirq, and dwc3 names its action "dwc3";
  * the gadget's gser function has one vendor-class interface with two bulk endpoints;
  * boot040: the regdump has GBUSERRADDR0/1 (the first failing DMA address), the DART
    driver registers its shared fault interrupt as "apple-dart fault handler", the IOMMU
    core links a master to its IOMMU as <device>/iommu (iommu-sysfs.c), and the t8110
    register offsets init.c reads through /dev/mem are the driver's DART_T8110_* values.
Writes the regdump names (one per line) for the fixture test and prints the facts.
"""
import re
import sys
from pathlib import Path


def fail(message):
    raise SystemExit("kernel facts FAIL: " + message)


def function_body(text, name):
    """The definition of function name (signature through its closing brace)."""
    start = re.search(r"^[^\n;]*\b%s\([^;{]*\)\s*\{" % re.escape(name), text, re.M)
    if not start:
        fail("no function " + name)
    end = text.index("\n}\n", start.start())
    return text[start.start():end]


def main(tree, init_c, names_out):
    tree = Path(tree)
    debugfs = (tree / "drivers/usb/dwc3/debugfs.c").read_text()
    init = Path(init_c).read_text()
    facts = []

    # Files.
    for name in ("regdump", "link_state"):
        if not re.search(r'debugfs_create_(file|regset32)\("%s"' % name, debugfs):
            fail("debugfs.c creates no %s file" % name)
    for name in ("transfer_type", "trb_ring"):
        if not re.search(r'\{ "%s", &' % name, debugfs):
            fail("debugfs.c's endpoint file map has no " + name)
    if 'debugfs_create_dir(dev_name(dwc->dev), usb_debug_root)' not in debugfs:
        fail("dwc3's debugfs root is not usb_debug_root/<dev_name>")
    common = (tree / "drivers/usb/common/common.c").read_text()
    if 'usb_debug_root = debugfs_create_dir("usb", NULL)' not in common:
        fail("usb_debug_root is not <debugfs>/usb")
    for used in ('"/sys/kernel/debug/usb"', '"%s/regdump"', '"%s/link_state"',
                 '"%s/%s/transfer_type"', '"%s/%s/trb_ring"'):
        if used not in init:
            fail("init.c does not read " + used)
    facts.append("dwc3 debugfs: <debugfs>/usb/<UDC>/{regdump,link_state,ep*/transfer_type,ep*/trb_ring}")

    # Which reads touch registers.
    for show in ("dwc3_transfer_type_show", "dwc3_trb_ring_show"):
        body = function_body(debugfs, show)
        if "dwc3_readl" in body or "dwc3_writel" in body or "fifo_space" in body:
            fail(show + " accesses a register")
    body = function_body(debugfs, "dwc3_link_state_show")
    if "dwc3_writel" in body or body.count("dwc3_readl") != 2:
        fail("link_state is not two register reads")
    core = (tree / "drivers/usb/dwc3/core.c").read_text()
    if "dwc3_writel(dwc, DWC3_GDBGFIFOSPACE" not in function_body(core, "dwc3_core_fifo_space"):
        fail("expected dwc3_core_fifo_space to write GDBGFIFOSPACE (the avoided files)")
    if "dwc3_writel(dwc, DWC3_GDBGLSPMUX" not in function_body(debugfs, "dwc3_ep_info_register_show"):
        fail("expected GDBGEPINFO's read to write GDBGLSPMUX")
    writing = ("tx_fifo_size", "rx_fifo_size", "tx_request_queue", "rx_request_queue", "rx_info_queue",
               "descriptor_fetch_queue", "event_queue", "GDBGEPINFO", "lsp_dump")
    for name in writing + ("testmode", "mode"):
        if re.search(r'/%s"' % name, init):
            fail("init.c reads the avoided file " + name)
    facts.append("read-only: link_state (GSTS+DSTS reads), regdump (reads), transfer_type and trb_ring "
                 "(driver memory); never read, since reading writes GDBGFIFOSPACE or GDBGLSPMUX: "
                 + ", ".join(writing) + "; not needed: mode, testmode")

    # Register names and the regdump format.
    regs = debugfs[debugfs.index("static const struct debugfs_reg32 dwc3_regs[]"):]
    regs = regs[:regs.index("};")]
    names = []
    for kind, arg in re.findall(r"(dump_register|dump_ep_register_set)\(([^()]*(?:\([^()]*\))?)\)", regs):
        if kind == "dump_register":
            names.append(arg)
        else:
            names += ["DEPCMDPAR2(%s)" % arg, "DEPCMDPAR1(%s)" % arg, "DEPCMDPAR0(%s)" % arg, "DEPCMD(%s)" % arg]
    used = set(re.findall(r'reg\(dump, "([A-Z0-9_()]+)"', init))
    used |= {"DEPCMD(%d)" % n for n in range(32)} | {"GTXFIFOSIZ(%d)" % n for n in range(32)}
    missing = sorted(used - set(names))
    if missing:
        fail("registers init.c reads are not in dwc3_regs[]: " + " ".join(missing))
    file_c = (tree / "fs/debugfs/file.c").read_text()
    if 'seq_printf(s, "%s = 0x%08x\\n", regs->name,' not in file_c:
        fail('fs/debugfs/file.c does not print "%s = 0x%08x\\n"')
    Path(names_out).write_text("\n".join(names) + "\n")
    facts.append("regdump: %d registers printed as 'NAME = 0x%%08x'; init.c reads %d of them"
                 % (len(names), len(used)))

    # trb_ring line format.
    trb = function_body(debugfs, "dwc3_trb_ring_show")
    if 'seq_printf(s, "%08x%08x,%d,%s,%d,%d,%d,%d,%d,%d       %c%c\\n",' not in trb \
            or "!!(trb->ctrl & DWC3_TRB_CTRL_HWO)," not in trb or "dep->trb_dequeue == i ? 'D'" not in trb:
        fail("trb_ring format changed")
    if 'seq_puts(s, "buffer_addr,size,type,ioc,isp_imi,csp,chn,lst,hwo\\n");' not in trb:
        fail("trb_ring header changed")
    facts.append("trb_ring: header, then '<addr>,<size>,<type>,ioc,isp_imi,csp,chn,lst,hwo       ED' per TRB")
    hs = function_body((tree / "drivers/usb/dwc3/debug.h").read_text(), "dwc3_gadget_hs_link_string")
    facts.append("high-speed link strings: " + ", ".join(re.findall(r'return "([^"]+)"', hs)))
    for line in ("bulk", "interrupt", "control", "isochronous", "--"):
        if 'seq_puts(s, "%s\\n");' % line not in function_body(debugfs, "dwc3_transfer_type_show"):
            fail("transfer_type does not print " + line)

    # Interrupt counts.
    irqdesc = (tree / "kernel/irq/irqdesc.c").read_text()
    for attr in ("per_cpu_count", "hwirq", "actions"):
        if not re.search(r"IRQ_ATTR_RO\(%s\)" % attr, irqdesc):
            fail("no /sys/kernel/irq/<n>/" + attr)
    aic = (tree / "drivers/irqchip/irq-apple-aic.c").read_text()
    if not re.search(r"#define AIC_EVENT_NUM\s+GENMASK\(15, 0\)", aic) \
            or not re.search(r"#define AIC_IRQ_HWIRQ\(die, irq\)[^\n]*\\\n[^\n]*\\\n\s*FIELD_PREP\(AIC_EVENT_NUM, irq\)\)", aic) \
            or "*hwirq = AIC_IRQ_HWIRQ(die, args[0]);" not in aic:
        fail("the AIC hwirq does not carry the IRQ number in bits 15:0")
    gadget = (tree / "drivers/usb/dwc3/gadget.c").read_text()
    if not re.search(r'IRQF_SHARED, "dwc3", dwc->ev_buf\)', gadget):
        fail('dwc3 does not name its gadget interrupt "dwc3"')
    udc = (tree / "drivers/usb/gadget/udc/core.c").read_text()
    if "udc->dev.parent = gadget->dev.parent;" not in udc:
        fail("the UDC's parent is not the gadget's parent (the dwc3 device)")
    facts.append("irq: /sys/kernel/irq/<n>/{actions,hwirq,per_cpu_count}; AIC hwirq bits 15:0 = DT IRQ; "
                 'action "dwc3"; /sys/class/udc/<UDC>/device = the dwc3 device')

    # The function.
    gser = (tree / "drivers/usb/gadget/function/f_serial.c").read_text()
    desc = gser[gser.index("gser_interface_desc = {"):]
    desc = desc[:desc.index("};")]
    if ".bNumEndpoints =\t2," not in desc or ".bInterfaceClass =\tUSB_CLASS_VENDOR_SPEC," not in desc:
        fail("gser's interface is not vendor class with two endpoints")
    if "USB_ENDPOINT_XFER_INT" in gser or ".setup" in gser:
        fail("gser has an interrupt endpoint or a setup handler")
    if '"gser"' not in gser or "DECLARE_USB_FUNCTION_INIT(gser," not in gser:
        fail("no configfs function named gser")
    facts.append("gser: one interface, class 0xff, two bulk endpoints, no interrupt endpoint, "
                 "no setup (class request) handler")

    # boot040: the bus-error address registers, the DART fault IRQ, the iommu link and the
    # register offsets of the read-only DART snapshot.
    for name in ("GBUSERRADDR0", "GBUSERRADDR1"):
        if name not in names or 'reg(dump, "%s"' % name not in init:
            fail("regdump or init.c lacks " + name)
    core_h = (tree / "drivers/usb/dwc3/core.h").read_text()
    if "#define DWC3_GSTS_BUS_ERR_ADDR_VLD\tBIT(4)" not in core_h:
        fail("GSTS.BUS_ERR_ADDR_VLD is not bit 4")
    dart = (tree / "drivers/iommu/apple-dart.c").read_text()
    if 'request_irq(dart->irq, apple_dart_irq, IRQF_SHARED,\n\t\t\t  "apple-dart fault handler", dart)' not in dart:
        fail('the DART fault interrupt is not requested shared as "apple-dart fault handler"')
    if '"apple-dart fault handler"' not in init:
        fail("init.c does not look for the apple-dart fault handler action")
    offsets = {"DART_T8110_TLB_CMD": "0x80", "DART_T8110_ERROR": "0x100", "DART_T8110_ERROR_MASK": "0x104",
               "DART_T8110_ERROR_ADDR_LO": "0x170", "DART_T8110_ERROR_ADDR_HI": "0x174",
               "DART_T8110_ERROR_STREAMS": "0x1c0", "DART_T8110_PROTECT": "0x200",
               "DART_T8110_ENABLE_STREAMS": "0xc00", "DART_T8110_TCR": "0x1000", "DART_T8110_TTBR": "0x1400"}
    for name, value in offsets.items():
        if not re.search(r"#define %s\s+%s\b" % (name, value), dart):
            fail("%s is not %s in apple-dart.c" % (name, value))
    peek = function_body(init, "dart_peek")
    for value in ("0x80", "0x100", "0x104", "0x170", "0x174", "0x1c0", "0x200", "0xc00", "0x1000", "0x1400"):
        if "m[%s / 4" % value not in peek:
            fail("init.c's dart_peek does not read offset " + value)
    # boot040 part 2: the v2.2 fault layout, in the patched driver and in init.c, gated on PARAMS3 bits 15:0.
    g22 = {"DART_T8110_PARAMS3_VERSION": "GENMASK(15, 0)", "DART_T8110_VERSION_2_2": "0x0202",
           "DART_T8110_VERSION_2_4": "0x0204", "DART_T8110_CTRL": "0x210", "DART_T8110_G22_PROT_STATUS": "0x704",
           "DART_T8110_G24_PROT_STATUS": "0x4204", "DART_T8110_G22_PENDING": "0x4000",
           "DART_T8110_G22_ERROR_MASK": "0x4060", "DART_T8110_G22_ADDR_LO": "0x08", "DART_T8110_G22_ADDR_HI": "0x0c"}
    for name, value in g22.items():
        if not re.search(r"#define %s\s+%s" % (name, re.escape(value)), dart):
            fail("%s is not %s in the patched apple-dart.c" % (name, value))
    if "#define DART_T8110_G22_STREAM_BLOCK(sid) (0x8000 + 0x40 * (sid))" not in dart:
        fail("the v2.2 stream block is not at 0x8000 + 0x40*sid in the patched apple-dart.c")
    for value in ("m[0x4000 / 4]", "m[0x4060 / 4]", "m[0x210 / 4]", "? 0x4204 : 0x704) / 4]",
                  "m[(0x8000 + 0x40 * sid) / 4]", "m[(0x8000 + 0x40 * sid + 0x08) / 4]",
                  "m[(0x8000 + 0x40 * sid + 0x0c) / 4]"):
        if value not in peek:
            fail("init.c's dart_peek does not read the v2.2 register " + value)
    if "if (r->version >= 0x0202)" not in peek or "r->version = r->params[2] & 0xffff;" not in peek:
        fail("init.c's v2.2 reads are not gated on PARAMS3 bits 15:0 >= 0x0202")
    if "mmap(NULL, 0xc000" not in peek:
        fail("init.c's dart_peek does not map the 0xc000 instance window")
    if "writel" in peek or "m[" in peek.split("munmap")[-1] or peek.count("= m[") + peek.count("] = m[") < 10 \
            or re.search(r"m\[[^\]]*\]\s*=", peek):
        fail("init.c's dart_peek must only read device memory")
    if "#define DART_T8110_ERROR_FLAG BIT(31)" not in dart or "#define DART_T8110_ERROR_STREAM GENMASK(27, 20)" not in dart:
        fail("the t8110 error flag or stream field moved")
    if "readl(dart->regs + DART_T8110_PARAMS3)" not in dart or "DART_T8110_PARAMS3 0x08" not in dart:
        fail("PARAMS3 is not at 0x08")
    sysfs = (tree / "drivers/iommu/iommu-sysfs.c").read_text()
    if 'sysfs_create_link_nowarn(&link->kobj, &iommu->dev->kobj, "iommu")' not in sysfs \
            or 'iommu->dev->parent = parent;' not in sysfs or 'iommu->dev->class = &iommu_class;' not in sysfs:
        fail("the IOMMU core no longer links <device>/iommu to a class device under the IOMMU's parent")
    if '"/sys/class/udc/%.63s/device/iommu"' not in init:
        fail("init.c does not follow <dwc3>/iommu")
    facts.append("boot040: GBUSERRADDR0/1 in the regdump; GSTS bit 4 = BUS_ERR_ADDR_VLD; DART fault IRQ shared as "
                 '"apple-dart fault handler"; <device>/iommu links to the DART class device under its platform '
                 "device; dart_peek offsets = DART_T8110_{TLB_CMD,ERROR,ERROR_MASK,ERROR_ADDR_LO/HI,ERROR_STREAMS,"
                 "PROTECT,ENABLE_STREAMS,TCR,TTBR}, reads only; v2.2 layout (patched driver and init.c, gated on "
                 "PARAMS3 bits 15:0): PENDING 0x4000, MASK 0x4060, CTRL 0x210, PROT_STATUS 0x704/0x4204, blocks "
                 "0x8000 + 0x40*sid (addr +0x08/+0x0c)")
    configfs = (tree / "drivers/usb/gadget/configfs.c").read_text()
    store = function_body(configfs, "gadget_dev_desc_bcdDevice_store")
    if "is_valid_bcd(bcdDevice)" not in store or "if ((bcd_val & 0xf) > 9)" not in function_body(configfs, "is_valid_bcd"):
        fail("configfs no longer requires a BCD bcdDevice (recheck the rule below)")
    bcd = re.search(r'#define BCD_DEVICE "0x([0-9a-fA-F]{4})"', init)
    if not bcd or any(int(digit, 16) > 9 for digit in bcd.group(1)):
        fail("init.c's BCD_DEVICE is not valid BCD; configfs would refuse it and keep its default")
    facts.append("bcdDevice 0x%s: valid BCD, which configfs's bcdDevice store requires (is_valid_bcd)" % bcd.group(1))
    print("\n".join(facts))
    print("kernel facts PASS")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
