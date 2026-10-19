#!/usr/bin/env python3
"""check_facts.py TREE: the kernel facts boot042's attempt-26 checklist relies on, from the exact tree.

Each fact is read from the source that builds the Image and the modules (the job VM's boot042 tree),
not from memory: what touches the MTP at boot (the DART probe only) and what each module load then does.
Prints one line per fact; exits 1 if any is not found as stated. Standard library only.
"""
import re
import sys
from pathlib import Path


def body(text, signature):
    """The text of the C function whose definition line starts with SIGNATURE, up to its closing brace."""
    start = text.find(signature)
    if start < 0:
        return None
    end = text.find("\n}\n", start)
    return text[start:end + 3] if end >= 0 else None


def main(argv):
    if len(argv) != 2:
        raise SystemExit(__doc__.splitlines()[0])
    tree = Path(argv[1])
    src = lambda p: (tree / p).read_text(errors="replace")  # noqa: E731
    facts = []

    def fact(label, ok, detail=""):
        facts.append((label, bool(ok), detail))

    dart = src("drivers/iommu/apple-dart.c")
    probe = body(dart, "static int apple_dart_probe(") or ""
    i_params = probe.find("DART_PARAMS1")
    i_reset = probe.find("apple_dart_hw_reset(dart)")
    i_irq = probe.find("request_irq(dart->irq")
    fact("apple-dart probe: reads PARAMS1/2 (and PARAMS3/4 on t8110) and validates them before any write",
         0 <= i_params < i_reset and "MMIO region too small" in probe[:i_reset])
    fact("apple-dart probe: resets the DART unless it is locked, before its fault interrupt is requested",
         re.search(r"if \(!dart->locked\) \{\s*ret = apple_dart_hw_reset\(dart\);", probe) and 0 < i_reset < i_irq)
    fact("apple-dart probe: the fault interrupt is requested shared and enabled (no IRQF_NO_AUTOEN)",
         re.search(r"request_irq\(dart->irq, apple_dart_irq, IRQF_SHARED,", probe) and "NO_AUTOEN" not in probe)
    reset = body(dart, "static int apple_dart_hw_reset(") or ""
    fact("apple-dart reset: every stream's DMA is disabled (TCR and TTBR cleared), which also clears a t8110 remap",
         "bitmap_set(stream_map.sidmap, 0, dart->num_streams)" in reset and "apple_dart_hw_disable_dma(&stream_map)" in reset
         and "DART_T8110_TCR_REMAP_EN" in dart)
    xlate = body(dart, "static int apple_dart_of_xlate(") or ""
    fact("apple-dart of_xlate: several iommus entries on one DART merge into one stream map (one domain for all)",
         "set_bit(sid, cfg->stream_maps[i].sidmap)" in xlate)
    fact("apple-dart: apple,dma-range is read as the IOVA window",
         "apple,dma-range" in dart)

    dd = src("drivers/base/dd.c")
    plat = src("drivers/base/platform.c")
    ofdev = src("drivers/of/device.c")
    fact("driver core: a device's DMA (and IOMMU) set-up runs when a driver probes it (really_probe -> bus dma_configure)",
         re.search(r"dev->bus->dma_configure\(dev\)", dd) and "of_dma_configure" in plat
         and "of_iommu_configure(" in ofdev)

    mbox = src("drivers/soc/apple/mailbox.c")
    mprobe = body(mbox, "static int apple_mbox_probe(") or ""
    fact("apple-mailbox probe: no register access; both interrupts requested with IRQF_NO_AUTOEN",
         mprobe and not re.search(r"\b(readl|writel)(_relaxed)?\(", mprobe) and mprobe.count("IRQF_NO_AUTOEN") == 2)

    helper = src("drivers/soc/apple/rtkit-helper.c")
    hprobe = body(helper, "static int apple_rtkit_helper_probe(") or ""
    fact("rtkit-helper probe: sets the ASC CPU's RUN bit, then wakes (or boots) the coprocessor through RTKit",
         0 <= hprobe.find("APPLE_ASC_CPU_CONTROL_RUN") < hprobe.find("apple_rtkit_wake(helper->rtk)"))
    hremove = body(helper, "static void apple_rtkit_helper_remove(") or ""
    fact("rtkit-helper remove: quiesces RTKit and clears the CPU control register (unloading stops the MTP CPU)",
         "apple_rtkit_quiesce" in hremove and "writel_relaxed(0, helper->asc_base + APPLE_ASC_CPU_CONTROL)" in hremove)
    fact("rtkit-helper matches apple,rtk-helper-asc4", '"apple,rtk-helper-asc4"' in helper and "MODULE_DEVICE_TABLE(of" in helper)

    dock = src("drivers/soc/apple/dockchannel.c")
    dprobe = body(dock, "static int dockchannel_probe(") or ""
    fact("apple-dockchannel probe: masks and acknowledges the FIFO's interrupts, then creates its child (input@8000)",
         "writel_relaxed(0, dcc->irq_base + IRQ_MASK)" in dprobe and "writel_relaxed(~0, dcc->irq_base + IRQ_FLAG)" in dprobe
         and "devm_of_platform_populate(dev)" in dprobe)
    fact("apple-dockchannel matches apple,dockchannel", '"apple,dockchannel"' in dock and "MODULE_DEVICE_TABLE(of" in dock)

    hid = src("drivers/hid/dockchannel-hid/dockchannel-hid.c")
    fact("dockchannel-hid (patched) matches apple,t6050-dockchannel-hid and apple,dockchannel-hid",
         '"apple,t6050-dockchannel-hid"' in hid and '"apple,dockchannel-hid"' in hid and "MODULE_DEVICE_TABLE(of" in hid)
    fact("dockchannel-hid (patched) logs the ring registration and has the mtp_poll_ms/mtp_ring parameters",
         "Ring registered" in hid and "mtp_poll_ms" in hid and "mtp_ring" in hid)
    fact("dockchannel-hid finds the helper CPU through apple,helper-cpu", "apple,helper-cpu" in hid)

    core = src("drivers/nvme/host/core.c")
    setup = body(core, "blk_status_t nvme_setup_cmd(") or ""
    ro_set = body(core, "static int ilinux_read_only_set(") or ""
    fact("nvme-core (storage set): ilinux_read_only starts on and is 0444 (no runtime writes)",
         "static bool ilinux_read_only = true;" in core and
         "module_param_cb(ilinux_read_only, &ilinux_read_only_ops, &ilinux_read_only, 0444);" in core)
    fact("nvme-core (storage set): a load asking for ilinux_read_only=0 fails with EPERM unless built with ILINUX_RO_CONTROL",
         re.search(r"#ifndef ILINUX_RO_CONTROL\s+if \(!on\) \{[^}]*return -EPERM;\s+\}\s+#endif", ro_set) is not None
         and "ilinux_read_only = on;" in ro_set)
    fact("nvme-core (storage set): nvme_setup_cmd refuses before its switch, so nothing refused is mapped or submitted",
         0 <= setup.find("nvme_ilinux_ro_allowed(ns, req, cmd)") < setup.find("switch (req_op(req))"))
    fact("nvme-core (storage set): every namespace is read-only in this mode",
         re.search(r"return ilinux_read_only \|\| info->is_readonly", core))

    happle = src("drivers/hid/hid-apple.c")
    host_rows = [l.strip() for l in happle.splitlines() if "BUS_HOST" in l or "HOST_VENDOR_ID_APPLE" in l
                 or "DOCKCHANNEL" in l.upper()]
    fact("hid-apple: device-table rows for host-bus (DockChannel/SPI) Apple keyboards (informational)", True,
         "; ".join(host_rows[:4]) or "none: hid-generic (built in) would serve the keyboard")

    bad = 0
    for label, ok, detail in facts:
        print("%s %s%s" % ("PASS" if ok else "FAIL", label, (" [" + detail + "]") if detail else ""))
        bad += not ok
    if bad:
        raise SystemExit("%d of %d facts not found as stated" % (bad, len(facts)))
    print("kernel facts PASS: %d" % len(facts))


if __name__ == "__main__":
    main(sys.argv)
