// VM-only (job 041) test of init.c's status line against fixture trees laid out like the
// boot036 kernel's sysfs and dwc3 debugfs: the regdump uses every register name of the
// tree's dwc3_regs[] (from check_kernel_facts.py) in fs/debugfs/file.c's format, and the
// other files use the formats of drivers/usb/dwc3/debugfs.c and kernel/irq/irqdesc.c.
// boot040 adds the sysfs iommu link (<dwc3>/iommu -> <dart>/iommu/apple-dart.<dart>.iommu,
// drivers/iommu/iommu-sysfs.c), the DART's of_node, the short [usbN] lines, the bus-error
// address and the DART snapshot text. The dummy_hcd boot cannot reach this code: the VM
// has no dwc3, and the fixture root has no /dev/mem, so no device memory is read here.
// usage: status_fixture NEW_DIR REGDUMP_NAMES (it works inside NEW_DIR, as the root ".")
#define INIT_NO_MAIN
#define SYSROOT "."
#include "../init.c"

static int failures;

static void mkdirs(char *path)
{
    for (char *s = path + 1; *s; s++)
        if (*s == '/') { *s = 0; mkdir(path, 0755); *s = '/'; }
}

static void put_file(const char *rel, const void *data, size_t len)
{
    char path[512];
    snprintf(path, sizeof path, "./%s", rel);
    mkdirs(path);
    int f = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (f < 0 || write(f, data, len) != (ssize_t)len) { perror(path); exit(2); }
    close(f);
}

static void put_text(const char *rel, const char *text) { put_file(rel, text, strlen(text)); }

static void put_link(const char *rel, const char *target)
{
    char path[512];
    snprintf(path, sizeof path, "./%s", rel);
    mkdirs(path);
    if (symlink(target, path)) { perror(path); exit(2); }
}

// A regdump with every name of the tree's list; the named values, 0 for the others.
struct value { const char *name; unsigned v; };
static char names[16384];   // the tree's regdump names, read before entering the fixture root

static void put_regdump(const char *udc, const struct value *values)
{
    static char text[65536];
    struct buf b = { text, sizeof text, 0 };
    for (char *s = names, *nl; *s && (nl = strchr(s, '\n')); s = nl + 1) {
        *nl = 0;
        unsigned v = 0;
        for (const struct value *x = values; x->name; x++)
            if (!strcmp(x->name, s)) v = x->v;
        add(&b, "%s = 0x%08x\n", s, v);
        *nl = '\n';
    }
    char rel[256];
    snprintf(rel, sizeof rel, "sys/kernel/debug/usb/%s/regdump", udc);
    put_text(rel, text);
}

// A trb_ring: the header, then 256 TRBs, the first `hwo` (from `first`) owned by hardware.
static void put_ring(const char *udc, const char *ep, int first, int hwo, int enq, int deq)
{
    static char text[65536];
    struct buf b = { text, sizeof text, 0 };
    add(&b, "buffer_addr,size,type,ioc,isp_imi,csp,chn,lst,hwo\n");
    for (int i = 0; i < 256; i++) {
        int owned = i >= first && i < first + hwo;
        add(&b, "%08x%08x,%d,%s,%d,%d,%d,%d,%d,%d       %c%c\n", 0x10, 0x4000 + i * 512, owned ? 512 : 0,
            i == 255 ? "link" : "normal", owned, 0, owned, 0, owned, owned, enq == i ? 'E' : ' ',
            deq == i ? 'D' : ' ');
    }
    char rel[256];
    snprintf(rel, sizeof rel, "sys/kernel/debug/usb/%s/%s/trb_ring", udc, ep);
    put_text(rel, text);
}

static void put_ep(const char *udc, const char *ep, const char *type)
{
    char rel[256], text[32];
    snprintf(rel, sizeof rel, "sys/kernel/debug/usb/%s/%s/transfer_type", udc, ep);
    snprintf(text, sizeof text, "%s\n", type);
    put_text(rel, text);
}

static void expect(const char *what, const char *got, const char *want)
{
    if (!strcmp(got, want)) { printf("ok   %s\n     %s", what, got); return; }
    printf("FAIL %s\n  got:  %s  want: %s", what, got, want);
    failures++;
}

// Every short line must fit the film: about 100 columns (the limit is per case: a wedge
// with three endpoints, two halt flags and a bus error is allowed a few more).
static void expect_short(const char *what, const char *text, size_t limit)
{
    for (const char *s = text; *s; ) {
        const char *nl = strchr(s, '\n');
        size_t len = nl ? (size_t)(nl - s) : strlen(s);
        if (len > limit) { printf("FAIL %s: %zu columns: %.*s\n", what, len, (int)len, s); failures++; }
        if (!nl) break;
        s = nl + 1;
    }
}

static size_t brief_limit = 100;

static void run(const char *what, const char *want_line, const char *want_pre, const char *want_brief)
{
    char line[1000], pre[1024], brief[1024];
    struct buf b = { line, sizeof line - 1, 0 }, p = { pre, sizeof pre, 0 }, q = { brief, sizeof brief, 0 };
    line[0] = pre[0] = brief[0] = 0;
    build_status(&b, &p, &q, 1);
    line[b.len++] = '\n';
    line[b.len] = 0;
    expect(what, line, want_line);
    char label[128];
    snprintf(label, sizeof label, "%s: one-time controller lines", what);
    expect(label, pre[0] ? pre : "(none)\n", want_pre);
    snprintf(label, sizeof label, "%s: short lines", what);
    expect(label, brief, want_brief);
    expect_short(label, brief, brief_limit);
}

int main(int argc, char **argv)
{
    if (argc != 3) { fprintf(stderr, "usage: status_fixture NEW_DIR REGDUMP_NAMES\n"); return 2; }
    if (slurp(argv[2], names, sizeof names) <= 0) { perror(argv[2]); return 2; }
    if (mkdir(argv[1], 0755) || chdir(argv[1])) { perror(argv[1]); return 2; }
    static struct stream_stats local[MAX_UDC];
    stats = local;

    // Port 1, configured, streaming: SOF frame 4660 (DSTS bits 16:3; bit 17 RXFIFOEMPTY set), link On,
    // RUN_STOP set, EP0 OUT/IN last command Start Transfer, ep1out/ep1in enabled (DALEPENA
    // bits 0-3), 16 OUT TRBs armed, IN ring idle with dequeue at 37.
    const char *u1 = "2a2280000.usb";
    put_text("sys/class/udc/2a2280000.usb/state", "configured\n");
    static const unsigned char irq1[12] = { 0, 0, 0, 0, 0, 0, 0x05, 0x8b, 0, 0, 0, 4 };
    put_file("sys/class/udc/2a2280000.usb/device/of_node/interrupts", irq1, sizeof irq1);
    static const unsigned char iommus1[8] = { 0, 0, 0, 0x2b, 0, 0, 0, 1 };   // <&dart_usb0_1 1>
    put_file("sys/class/udc/2a2280000.usb/device/of_node/iommus", iommus1, sizeof iommus1);
    // The DART behind it: its platform device, of_node and the kernel's iommu class link.
    static const unsigned char dart_irq1[12] = { 0, 0, 0, 0, 0, 0, 0x05, 0x8f, 0, 0, 0, 4 };
    put_file("sys/devices/platform/soc/2a2f80000.iommu/of_node/interrupts", dart_irq1, sizeof dart_irq1);
    put_text("sys/devices/platform/soc/2a2f80000.iommu/iommu/apple-dart.2a2f80000.iommu/uevent", "");
    put_link("sys/class/udc/2a2280000.usb/device/iommu",
             "../../../../devices/platform/soc/2a2f80000.iommu/iommu/apple-dart.2a2f80000.iommu");
    put_text("sys/kernel/irq/36/actions", "apple-dart fault handler\n");
    put_text("sys/kernel/irq/36/hwirq", "66959\n");   // AIC_IRQ_HWIRQ(die 0, IRQ 0x58f) = 0x1058f
    put_text("sys/kernel/irq/36/per_cpu_count", "7\n");
    put_text("sys/kernel/irq/37/actions", "dwc3\n");
    put_text("sys/kernel/irq/37/hwirq", "66955\n");   // AIC_IRQ_HWIRQ(die 0, IRQ 0x58b) = 0x1058b
    put_text("sys/kernel/irq/37/per_cpu_count", "400,12,0,0\n");
    put_text("sys/kernel/irq/38/actions", "dwc3\n");
    put_text("sys/kernel/irq/38/hwirq", "66987\n");   // port 2's, IRQ 0x5ab
    put_text("sys/kernel/irq/38/per_cpu_count", "3,0,0,0\n");
    put_text("sys/kernel/debug/usb/2a2280000.usb/link_state", "On\n");
    const struct value v1[] = {
        { "GSNPSID", 0x5533330a }, { "GHWPARAMS0", 0x4020400a }, { "GHWPARAMS3", 0x00108085 },
        { "GTXFIFOSIZ(0)", 0x00000042 }, { "GTXFIFOSIZ(1)", 0x00420184 }, { "GTXFIFOSIZ(2)", 0x01c60184 },
        { "GTXFIFOSIZ(3)", 0x034a0000 }, { "GRXFIFOSIZ(0)", 0x00000305 },
        { "GSTS", 0x7e800000 }, { "DCTL", 0x8cf00000 }, { "DSTS", 0x00020000 | 4660 << 3 },
        { "GEVNTCOUNT(0)", 0 }, { "DALEPENA", 0x0000000f },
        { "DEPCMD(0)", 0x00000006 }, { "DEPCMD(1)", 0x00010006 }, { "DEPCMD(2)", 0x00020006 },
        { "DEPCMD(3)", 0x00030006 }, { 0, 0 } };
    put_regdump(u1, v1);
    put_ep(u1, "ep1out", "bulk");
    put_ring(u1, "ep1out", 0, 16, 16, 0);
    put_ep(u1, "ep1in", "bulk");
    put_ring(u1, "ep1in", 0, 0, 37, 37);
    put_ep(u1, "ep2in", "--");                                       // present, not enabled

    nports = 1;
    ports[0] = (struct port){ .udc = "2a2280000.usb", .tty = "/dev/ttyGS0", .index = 1, .bound = 1, .st = &stats[0] };
    stats[0] = (struct stream_stats){ .records = 1796, .bytes = 151234, .queued = 0 };

    // The DART identity from the sysfs links: instance 1 at 2a2f80000, stream 1, fault IRQ
    // 0x58f = Linux 36; instance 0 from the table.
    dart_identify(&ports[0]);
    char text[1024];
    struct buf t = { text, sizeof text, 0 };
    text[0] = 0;
    dart_identity_text(&ports[0], &t);
    expect("DART identity line", text,
           "[usb1] 2a2280000.usb irq 58b(37) dart1 2a2f80000 sid 1 fault irq 58f(36); dart0 2a2f00000 not in DT\n");
    expect_short("DART identity line", text, 100);
    if (!ports[0].dart.known || ports[0].dart.base != 0x2a2f80000ull || ports[0].dart.base0 != 0x2a2f00000ull
        || ports[0].dart.hwirq != 0x58f || ports[0].dart.sid != 1 || ports[0].dart.linux_irq != 36) {
        printf("FAIL dartinfo: known %d base %llx base0 %llx hwirq %x sid %u irq %d\n", ports[0].dart.known,
               ports[0].dart.base, ports[0].dart.base0, ports[0].dart.hwirq, ports[0].dart.sid, ports[0].dart.linux_irq);
        failures++;
    } else printf("ok   dartinfo resolved from the sysfs links\n");

    run("port 1 streaming",
        "[ctl] port1 configured log 1796L 151234B q0 dwc3 On f4660 ev0 irq412 ep0 o:start i:start "
        "1out bulk h16 d0 1in bulk h0 d37\n",
        "[ctl] port1 dwc3: core 0x5533330a, 8 endpoints (4 IN), MDWIDTH 64; TX FIFO words 0:66 1:388 "
        "2:388 3:0; RX FIFO words 773\n",
        "[usb1] configured On f4660 irq412 dart7 151234B q0 1o h16 d0 1i h0 d37\n");
    run("port 1, second heartbeat (controller line printed once)",
        "[ctl] port1 configured log 1796L 151234B q0 dwc3 On f4660 ev0 irq412 ep0 o:start i:start "
        "1out bulk h16 d0 1in bulk h0 d37\n", "(none)\n",
        "[usb1] configured On f4660 irq412 dart7 151234B q0 1o h16 d0 1i h0 d37\n");
    if (stats[0].buserr) { printf("FAIL bus error recorded without BUSERR\n"); failures++; }

    // Attempt 21's picture: link On, SOFs counting, a bus error on the first IN DMA address
    // (GBUSERRADDR1:0 = 0x3ff_ffffc000), 17 IN TRBs owned by hardware with the dequeue index
    // frozen at 105, the dwc3 interrupt count frozen; the DART fault interrupt stormed.
    put_text("sys/kernel/irq/36/per_cpu_count", "99900\n");
    put_text("sys/kernel/irq/37/per_cpu_count", "146\n");
    const struct value v3[] = {
        { "GSTS", 0x7e800010 }, { "DCTL", 0x8cf00000 }, { "DSTS", 0x00020000 | 14975 << 3 },
        { "GEVNTCOUNT(0)", 0 }, { "DALEPENA", 0x0000000f },
        { "GBUSERRADDR0", 0xffffc000 }, { "GBUSERRADDR1", 0x000003ff },
        { "DEPCMD(0)", 0x00000006 }, { "DEPCMD(1)", 0x00010006 }, { "DEPCMD(2)", 0x00020006 },
        { "DEPCMD(3)", 0x00030006 }, { 0, 0 } };
    put_regdump(u1, v3);
    put_ring(u1, "ep1out", 0, 17, 17, 0);
    put_ring(u1, "ep1in", 105, 17, 122, 105);
    stats[0] = (struct stream_stats){ .records = 605, .bytes = 46250, .queued = 8192, .info_done = 1 };
    run("port 1 as in attempt 21 (bus error)",
        "[ctl] port1 configured log 605L 46250B q8192 dwc3 On f14975 ev0 BUSERR@3ffffffc000 irq146 "
        "ep0 o:start i:start 1out bulk h17 d0 1in bulk h17 d105\n", "(none)\n",
        "[usb1] configured On f14975 irq146 dart99900 46250B q8192 1o h17 d0 1i h17 d105 BUSERR@3ffffffc000\n");
    if (stats[0].buserr != 1 || stats[0].buserr_lo != 0xffffc000 || stats[0].buserr_hi != 0x3ff) {
        printf("FAIL bus error not recorded in the shared stats (%d %x %x)\n", stats[0].buserr,
               stats[0].buserr_hi, stats[0].buserr_lo);
        failures++;
    } else printf("ok   bus error and its address recorded in the shared stats\n");
    // What /init prints when it sees the recorded bus error (no streamer here; no /dev/mem in
    // the fixture root, so both snapshot reads report n/a instead of touching memory).
    t.len = 0; text[0] = 0;
    bus_error_text(&ports[0], &t);
    expect("bus error line", text,
           "[ctl] port 1: dwc3 bus error at DMA address 0x3ffffffc000: log streamer not running; kernel messages "
           "stay on the console\n");
    t.len = 0; text[0] = 0;
    dart_snapshot_text(&ports[0], &t, 0);
    expect("DART snapshot without /dev/mem", text,
           "[usb1] dart0 @2a2f00000 regs n/a (No such file or directory)\n"
           "[usb1] dart1 @2a2f80000 regs n/a (No such file or directory)\n");
    ports[0].stopped = 1;
    run("port 1 after the streamer was stopped",
        "[ctl] port1 configured log 605L 46250B q8192 dwc3 On f14975 ev0 BUSERR@3ffffffc000 irq146 "
        "ep0 o:start i:start 1out bulk h17 d0 1in bulk h17 d105\n", "(none)\n",
        "[usb1] configured On f14975 irq146 dart99900 nostream 1o h17 d0 1i h17 d105 BUSERR@3ffffffc000\n");
    ports[0].stopped = 0;

    // The register snapshot's text, with made-up values: a fault flagged on stream 1 (a DART of
    // version 2.1: PARAMS3 bits 15:0 = 0x0201, no third line).
    struct dart_regs r = { .params = { 0x0e000001, 0x00000001, 0x2a2a0201, 0x00040010 }, .tlb = 0,
                           .err = 0x80100020, .mask = 0, .addr_lo = 0xffffc000, .addr_hi = 0x3ff, .streams = 2,
                           .prot = 0, .enable = 0xffff, .tcr = { 0, 1 }, .ttbr = { 0, 0x8c000001 }, .version = 0x0201 };
    t.len = 0; text[0] = 0;
    dart_regs_text(&t, 1, 1, 0x2a2f80000ull, &r, 1);
    expect("DART register lines", text,
           "[usb1] dart1 @2a2f80000 p1 0e000001 p2 00000001 p3 2a2a0201 p4 00040010 prot 0 en ffff\n"
           "[usb1] dart1 err 80100020 FAULT strm 2 addr 3ffffffc000 tcr 0/1 ttbr 0/8c000001 tlb 0 mask 0\n");
    expect_short("DART register lines", text, 100);
    // A DART of version 2.2: the third line with the pending bitmap, mask, control, protection
    // status and the first two streams' error blocks (stream 1: a table-walk fault at the PTE
    // level, code 0, level 3, at 0x3ff_ffffc000).
    struct dart_regs g = { .params = { 0x0e000001, 0x00000011, 0x2a2a0202, 0x00040010 }, .err = 0, .version = 0x0202,
                           .tcr = { 0, 1 }, .ttbr = { 0, 0x8c000001 }, .enable = 0xffff, .g22_pending = 2, .g22_mask = 0,
                           .ctrl = 2, .prot_status = 0, .s = { { 0, 0, 0 }, { 0x00003000, 0xffffc000, 0x3ff } } };
    t.len = 0; text[0] = 0;
    dart_regs_text(&t, 1, 1, 0x2a2f80000ull, &g, 0);
    expect("DART register lines, v2.2 layout", text,
           "[usb1] dart1 err 00000000 strm 0 addr 000000000 tcr 0/1 ttbr 0/8c000001 tlb 0 mask 0\n"
           "[usb1] dart1 v2.2 pend 2 mask 0 ctl 2 prot 0 s0 00000000@0 s1 00003000@3ffffffc000\n");
    expect_short("DART register lines, v2.2 layout", text, 100);

    // A wedge as attempt 18 might look: run/stop cleared, halted, a bus error, 8 event bytes
    // never handled, EP0 IN's Start Transfer still active with status 1, and an interrupt
    // endpoint enabled whose ring cannot be read.
    put_text("sys/kernel/irq/36/per_cpu_count", "7\n");
    put_text("sys/kernel/irq/37/per_cpu_count", "400,12,0,0\n");
    const struct value v2[] = {
        { "GSTS", 0x7e800010 }, { "DCTL", 0x0cf00000 }, { "DSTS", 0x00400000 | 836 << 3 },
        { "GEVNTCOUNT(0)", 0x00000008 }, { "DALEPENA", 0x0000002f },
        { "DEPCMD(0)", 0x00000006 }, { "DEPCMD(1)", 0x00011406 }, { "DEPCMD(5)", 0x00000408 }, { 0, 0 } };
    put_regdump(u1, v2);
    put_ring(u1, "ep1out", 0, 16, 16, 0);
    put_ring(u1, "ep1in", 0, 0, 37, 37);
    put_text("sys/kernel/debug/usb/2a2280000.usb/link_state", "Reset\n");
    put_ep(u1, "ep2in", "interrupt");
    put_text("sys/class/udc/2a2280000.usb/state", "configured\n");
    stats[0] = (struct stream_stats){ .records = 140, .bytes = 16384, .queued = 8192, .info_done = 1 };
    brief_limit = 105;   // three endpoints, two halt flags and a bus error at once
    run("port 1 wedged",
        "[ctl] port1 configured log 140L 16384B q8192 dwc3 Reset f836 ev8 STOPPED HALTED BUSERR@0 irq412 "
        "ep0 o:start i:start*!1 1out bulk h16 d0 1in bulk h0 d37 2in INTERRUPT h? c:end*\n", "(none)\n",
        "[usb1] configured Reset f836 irq412 dart7 16384B q8192 1o h16 d0 1i h0 d37 2i h? STOPPED HALTED "
        "BUSERR@0\n");
    brief_limit = 100;

    // The VM's dummy_udc (no dwc3, no debugfs directory, no iommu link), a UDC whose gadget
    // did not bind, and a port whose tty never appeared.
    put_text("sys/class/udc/dummy_udc.0/state", "configured\n");
    put_text("sys/class/udc/x.usb/state", "not attached\n");
    nports = 3;
    ports[0] = (struct port){ .udc = "dummy_udc.0", .tty = "/dev/ttyGS0", .index = 4, .bound = 1, .st = &stats[0] };
    ports[1] = (struct port){ .udc = "x.usb", .index = 5, .bound = 0, .st = &stats[1] };
    ports[2] = (struct port){ .udc = "missing.usb", .index = 6, .bound = 1, .st = &stats[2] };
    stats[0] = (struct stream_stats){ .records = 12, .bytes = 900, .queued = 3 };
    dart_identify(&ports[0]);
    t.len = 0; text[0] = 0;
    dart_identity_text(&ports[0], &t);
    expect("identity line without an iommu link", text, "[usb4] dummy_udc.0 irq 0(-1) no iommu link in sysfs\n");
    t.len = 0; text[0] = 0;
    dart_snapshot_text(&ports[0], &t, 1);
    expect("no snapshot for an unknown UDC", text, "[usb4] dart regs not read (no confirmed DART bases for dummy_udc.0)\n");
    run("VM-style ports",
        "[ctl] port4 configured log 12L 900B q3 dwc3 n/a | port5 not attached unbound dwc3 n/a | "
        "port6 ? no-tty dwc3 n/a\n", "(none)\n",
        "[usb4] configured 900B q3 dwc3 n/a\n[usb5] not attached unbound dwc3 n/a\n[usb6] ? no-tty dwc3 n/a\n");

    // No UDC at all (the shipped Image in the generic VM).
    nports = 0;
    run("no UDC", "[ctl] no UDC\n", "(none)\n", "");

    // A long line stays bounded and newline-terminated.
    nports = MAX_UDC;
    for (int i = 0; i < MAX_UDC; i++)
        ports[i] = (struct port){ .udc = "2a2280000.usb", .tty = "/dev/ttyGS0", .index = 1, .bound = 1, .st = &stats[0] };
    char line[1000], pre[1024], brief[1024];
    struct buf b = { line, sizeof line - 1, 0 }, p = { pre, sizeof pre, 0 }, q = { brief, sizeof brief, 0 };
    build_status(&b, &p, &q, 1);
    if (b.len >= sizeof line - 1 || line[b.len] != 0) { printf("FAIL bounded line (len %zu)\n", b.len); failures++; }
    else printf("ok   bounded line: %zu of %zu bytes\n", b.len, sizeof line - 1);
    if (q.len >= sizeof brief || brief[q.len] != 0) { printf("FAIL bounded short lines (len %zu)\n", q.len); failures++; }
    else printf("ok   bounded short lines: %zu of %zu bytes\n", q.len, sizeof brief);

    printf(failures ? "status fixture FAIL (%d)\n" : "status fixture PASS\n", failures);
    return failures != 0;
}
