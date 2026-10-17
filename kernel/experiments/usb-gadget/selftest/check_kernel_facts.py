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
  * the gadget's gser function has one vendor-class interface with two bulk endpoints.
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
