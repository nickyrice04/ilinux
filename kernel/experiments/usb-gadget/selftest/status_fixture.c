// VM-only (job 041) test of init.c's status line against fixture trees laid out like the
// boot036 kernel's sysfs and dwc3 debugfs: the regdump uses every register name of the
// tree's dwc3_regs[] (from check_kernel_facts.py) in fs/debugfs/file.c's format, and the
// other files use the formats of drivers/usb/dwc3/debugfs.c and kernel/irq/irqdesc.c.
// The dummy_hcd boot cannot reach this code: the VM has no dwc3.
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

static void run(const char *what, const char *want_line, const char *want_pre)
{
    char line[1000], pre[1024];
    struct buf b = { line, sizeof line - 1, 0 }, p = { pre, sizeof pre, 0 };
    line[0] = pre[0] = 0;
    build_status(&b, &p, 1);
    line[b.len++] = '\n';
    line[b.len] = 0;
    expect(what, line, want_line);
    char label[128];
    snprintf(label, sizeof label, "%s: one-time controller lines", what);
    expect(label, pre[0] ? pre : "(none)\n", want_pre);
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
    put_text("sys/kernel/irq/36/actions", "apple-dart fault handler\n");
    put_text("sys/kernel/irq/36/hwirq", "66954\n");
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
    run("port 1 streaming",
        "[ctl] port1 configured log 1796L 151234B q0 dwc3 On f4660 ev0 irq412 ep0 o:start i:start "
        "1out bulk h16 d0 1in bulk h0 d37\n",
        "[ctl] port1 dwc3: core 0x5533330a, 8 endpoints (4 IN), MDWIDTH 64; TX FIFO words 0:66 1:388 "
        "2:388 3:0; RX FIFO words 773\n");
    run("port 1, second heartbeat (controller line printed once)",
        "[ctl] port1 configured log 1796L 151234B q0 dwc3 On f4660 ev0 irq412 ep0 o:start i:start "
        "1out bulk h16 d0 1in bulk h0 d37\n", "(none)\n");

    // A wedge as attempt 18 might look: run/stop cleared, halted, a bus error, 8 event bytes
    // never handled, EP0 IN's Start Transfer still active with status 1, and an interrupt
    // endpoint enabled whose ring cannot be read.
    const struct value v2[] = {
        { "GSTS", 0x7e800010 }, { "DCTL", 0x0cf00000 }, { "DSTS", 0x00400000 | 836 << 3 },
        { "GEVNTCOUNT(0)", 0x00000008 }, { "DALEPENA", 0x0000002f },
        { "DEPCMD(0)", 0x00000006 }, { "DEPCMD(1)", 0x00011406 }, { "DEPCMD(5)", 0x00000408 }, { 0, 0 } };
    put_regdump(u1, v2);
    put_text("sys/kernel/debug/usb/2a2280000.usb/link_state", "Reset\n");
    put_ep(u1, "ep2in", "interrupt");
    put_text("sys/class/udc/2a2280000.usb/state", "configured\n");
    stats[0] = (struct stream_stats){ .records = 140, .bytes = 16384, .queued = 8192, .info_done = 1 };
    run("port 1 wedged",
        "[ctl] port1 configured log 140L 16384B q8192 dwc3 Reset f836 ev8 STOPPED HALTED BUSERR irq412 "
        "ep0 o:start i:start*!1 1out bulk h16 d0 1in bulk h0 d37 2in INTERRUPT h? c:end*\n", "(none)\n");

    // The VM's dummy_udc (no dwc3, no debugfs directory), a UDC whose gadget did not bind,
    // and a port whose tty never appeared.
    put_text("sys/class/udc/dummy_udc.0/state", "configured\n");
    put_text("sys/class/udc/x.usb/state", "not attached\n");
    nports = 3;
    ports[0] = (struct port){ .udc = "dummy_udc.0", .tty = "/dev/ttyGS0", .index = 4, .bound = 1, .st = &stats[0] };
    ports[1] = (struct port){ .udc = "x.usb", .index = 5, .bound = 0, .st = &stats[1] };
    ports[2] = (struct port){ .udc = "missing.usb", .index = 6, .bound = 1, .st = &stats[2] };
    stats[0] = (struct stream_stats){ .records = 12, .bytes = 900, .queued = 3 };
    run("VM-style ports",
        "[ctl] port4 configured log 12L 900B q3 dwc3 n/a | port5 not attached unbound dwc3 n/a | "
        "port6 ? no-tty dwc3 n/a\n", "(none)\n");

    // No UDC at all (the shipped Image in the generic VM).
    nports = 0;
    run("no UDC", "[ctl] no UDC\n", "(none)\n");

    // A long line stays bounded and newline-terminated.
    nports = MAX_UDC;
    for (int i = 0; i < MAX_UDC; i++)
        ports[i] = (struct port){ .udc = "2a2280000.usb", .tty = "/dev/ttyGS0", .index = 1, .bound = 1, .st = &stats[0] };
    char line[1000], pre[1024];
    struct buf b = { line, sizeof line - 1, 0 }, p = { pre, sizeof pre, 0 };
    build_status(&b, &p, 1);
    if (b.len >= sizeof line - 1 || line[b.len] != 0) { printf("FAIL bounded line (len %zu)\n", b.len); failures++; }
    else printf("ok   bounded line: %zu of %zu bytes\n", b.len, sizeof line - 1);

    printf(failures ? "status fixture FAIL (%d)\n" : "status fixture PASS\n", failures);
    return failures != 0;
}
