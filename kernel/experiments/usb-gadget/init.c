// diag-init.c (boot041) - PID 1 for the t6050 RAM initramfs, with a USB log channel.
// Source: kernel/experiments/usb-gadget/init.c; packaged as diag-init.c.
// Keeps everything boot021-035's diag-init did: mounts proc/sys/dev, prints the
// bring-up observables to the console (framebuffer) and /dev/kmsg, heartbeats
// the online-CPU count. New in boot036, revised in boot038 and boot039:
//  * one configfs gadget per UDC with ONE function: the generic serial function
//    (gser: vendor class 0xff, one bulk-IN and one bulk-OUT endpoint, no interrupt
//    endpoint, no class requests). A child of /init copies the kernel log to it and
//    never reads from it. boot036 used CDC-EEM (macOS 26.0.1 on the controller has
//    no driver); boot038 used CDC-ACM + CDC-ECM, and the device stopped answering
//    control transfers right after macOS set the configuration (attempt 18); both
//    of those functions have an interrupt-IN notification endpoint, gser has none.
//    VID:PID 1d6b:0104, bcdDevice 0x0139 (configfs takes BCD only, so not 0x003a; boot036
//    0x0036, boot038 0x0038, RAM root 0x0039), the port table and strings of boot036.
//    No network function in boot039; dropbear still runs (root, key only, no
//    forwarding, host keys made in RAM, restarted if it exits), on lo only;
//  * debugfs mounted; each heartbeat's status line gives every port's UDC state,
//    the log stream's counters and, per dwc3 controller, the link state, SOF frame
//    number, pending event bytes, interrupt count, the last EP0 OUT/IN endpoint
//    command and every other enabled endpoint's type and TRB ring state. Only
//    debugfs files whose read writes no controller register are read, in a child
//    process, so a stuck read or a parser fault never stops the heartbeat;
//  * once per controller: its endpoint count and TX FIFO sizes;
//  * /etc/ilinux/selftest, if present (VM tests only; the packager refuses a
//    shipped initramfs that contains it), runs once after the first setup.
// New in boot040 (after attempt 21: bulk IN flowed, then the dwc3 flagged a bus error,
// its interrupts stopped and an apple-dart fault interrupt stormed until Linux disabled
// it, with no fault ever reported):
//  * a short line per port each heartbeat, about 100 columns, with the fields that
//    matter on film: UDC state, link, SOF frame, dwc3 and DART fault interrupt counts,
//    log counters, the ring state of every enabled endpoint and, when the controller
//    flags a bus error, the address it failed on (GBUSERRADDR0/1);
//  * at bind, which DART instance, stream and fault interrupt serve each dwc3 core
//    (from the kernel's own sysfs links) and a read-only register snapshot of both
//    DART instances of that port, the one in the DT and its sibling, through /dev/mem;
//  * at the first bus error on a port: that port's log streamer is stopped for good
//    and the DART snapshot is taken again, so the fault state is on the screen.
// New in boot041 (after attempt 23: at the first bus error the fault sat on DART instance 0,
// which the boot036-040 DT leaves out, so Linux never set it up and had no handler for it;
// boot041's DT gives each dwc3 core both instances, <dart0 0>, <dart1 1>, as Asahi does):
//  * the DART instances of a core are read from the DT the kernel booted (the core's iommus
//    cells, each DART node found by its phandle) and checked against the ADT's pair, so the
//    identity line names both instances, their streams and how many apple-dart fault
//    handlers share the port's fault interrupt;
//  * at bind, after the register snapshot, one line per port says whether the kernel set
//    up each instance (bound to apple-dart, its stream translating on a valid table) and
//    both on one table;
//  * the short line carries both instances' pending-fault words (instance 0/instance 1).
// It writes nothing to any disk, never mounts storage and writes no device register.
// Build: gcc -static -O2 -o init diag-init.c
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <net/if.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/mount.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <termios.h>
#include <unistd.h>

static int con = 1;

static void outs(const char *s) { write(con, s, strlen(s)); }

static void kmsg(const char *s)
{
    int f = open("/dev/kmsg", O_WRONLY | O_CLOEXEC);
    if (f >= 0) { write(f, s, strlen(s)); close(f); }
}

static void say(const char *s) { outs(s); kmsg(s); }

static void sayf(const char *fmt, ...)
{
    char buf[512];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof buf, fmt, ap);
    va_end(ap);
    say(buf);
}

// Dump a /proc or /sys file to the console with a label; truncate long ones.
static void dump(const char *label, const char *path, long max)
{
    char buf[8192];
    outs("\n--- "); outs(label); outs(" ("); outs(path); outs(") ---\n");
    int f = open(path, O_RDONLY);
    if (f < 0) { outs("  (open failed)\n"); return; }
    long total = 0;
    for (;;) {
        ssize_t n = read(f, buf, sizeof buf);
        if (n <= 0) break;
        if (max > 0 && total + n > max) n = max - total;
        write(con, buf, n);
        total += n;
        if (max > 0 && total >= max) { outs("\n  [truncated]\n"); break; }
    }
    close(f);
}

// Count lines beginning with "processor" in /proc/cpuinfo = online CPUs.
static int online_cpus(void)
{
    char buf[16384];
    int f = open("/proc/cpuinfo", O_RDONLY), n, i, c = 0;
    if (f < 0) return -1;
    n = read(f, buf, sizeof buf - 1);
    close(f);
    if (n <= 0) return -1;
    buf[n] = 0;
    for (i = 0; i < n; i++)
        if ((i == 0 || buf[i - 1] == '\n') && !strncmp(buf + i, "processor", 9))
            c++;
    return c;
}

// ---- control channel ------------------------------------------------------

#define GADGETS "/sys/kernel/config/usb_gadget"
#define FUNCTION "gser.GS0"     // generic serial: vendor class, two bulk endpoints
#define BCD_DEVICE "0x0139"     // boot039; must be BCD (configfs is_valid_bcd)
#define MAX_UDC 8
// usb-drd0..2 (ports 1..3) by their dwc3 node; any other UDC (VM tests) gets 4+. The DART
// bases are the ADT's dart-usbN reg[0] (instance 0) and reg[1] (instance 1) translated
// through /arm-io ranges; the boot036-040 Stage-B DT gives each core instance 1, stream 1,
// boot041's both instances, streams 0 and 1.
static const struct { const char *udc; unsigned long long dart0, dart1; } known_udc[] = {
    { "2a2280000.usb", 0x2a2f00000ull, 0x2a2f80000ull },
    { "2aa280000.usb", 0x2aaf00000ull, 0x2aaf80000ull },
    { "382280000.usb", 0x382f00000ull, 0x382f80000ull },
};

// Log stream counters, in memory shared with the streamer child (it writes, /init reads).
struct stream_stats {
    unsigned long records, bytes;  // records copied, bytes accepted by the tty
    int queued;                    // bytes still in the M5's 8 KiB serial FIFO (TIOCOUTQ)
    int info_done;                 // the one-time dwc3 line for this port was printed
    int buserr;                    // the status reader saw GSTS.BUS_ERR_ADDR_VLD on this port
    unsigned buserr_lo, buserr_hi; // GBUSERRADDR0/1 at that time (the failing DMA address)
};

// One t8110-class DART instance's registers as dart_peek reads them (see there).
struct dart_regs {
    unsigned params[4], tlb, err, mask, addr_lo, addr_hi, streams, prot, enable, tcr[2], ttbr[2];
    unsigned version, g22_pending, g22_mask, ctrl, prot_status;   // v2.2 layout, else 0
    struct { unsigned summary, addr_lo, addr_hi; } s[2];
};

#define MAX_DARTS 3   // MAX_DARTS_PER_DEVICE in drivers/iommu/apple-dart.c

// The DARTs behind one dwc3 core, as the kernel's sysfs and the DT it booted describe them:
// instance 0 and instance 1 of the port's dart-usbN pair, in the DT or not.
struct dartinfo {
    int known;                 // the iommu link resolved
    char name[64];             // its target, e.g. apple-dart.2a2f00000.iommu
    unsigned long long base;   // instance 1 register base
    unsigned long long base0;  // instance 0 base, only once the bases are confirmed (dart_identify), else 0
    unsigned sid, sid0, hwirq; // instance 1's and instance 0's streams (iommus), fault IRQ (DT interrupts[1])
    int linux_irq;             // Linux IRQ number of the "apple-dart fault handler", -1 if none
    int handlers;              // apple-dart fault handlers on that IRQ: one per DART instance with a driver
    int ndt;                   // DART instances the DT gives the core (its iommus entries)
    struct { unsigned long long base; unsigned sid; int inst, bound; } dt[MAX_DARTS];
    int in_dt0;                // instance 0 is one of them (boot041's DT)
    int bound[2];              // instance 0 / instance 1 bound to the apple-dart driver
    struct dart_regs regs[2];  // the last register snapshot (instance 0, instance 1)
    int regs_ok[2];
};

struct port {
    char udc[64];
    char tty[32];   // the gser serial port on this side, /dev/ttyGSn
    int index;      // 1..9: port number in the strings
    int bound;
    int stopped;    // the streamer was stopped at a bus error and is not restarted
    pid_t streamer; // child that copies /dev/kmsg to the serial port
    int streamer_starts;
    struct stream_stats *st;
    struct dartinfo dart;
};
static struct port ports[MAX_UDC];
static struct stream_stats *stats;   // MAX_UDC entries, MAP_SHARED
static int nports;
static pid_t dropbear_pid = -1, selftest_pid = -1, status_pid = -1;
static int dropbear_starts, selftest_done, status_stuck_since = -1;
#ifndef SYSROOT
#define SYSROOT ""                   // prefix for the status readers' paths ("." in fixture tests)
#endif

// Write a value to a sysfs/configfs attribute; 0 or -errno.
static int put(const char *path, const char *value)
{
    int f = open(path, O_WRONLY | O_CLOEXEC);
    if (f < 0) return -errno;
    ssize_t n = write(f, value, strlen(value));
    int err = n < 0 ? -errno : 0;
    close(f);
    return err;
}

// Read one line (newline stripped); empty string on failure.
static const char *get(const char *path, char *buf, size_t size)
{
    buf[0] = 0;
    int f = open(path, O_RDONLY | O_CLOEXEC);
    if (f < 0) return buf;
    ssize_t n = read(f, buf, size - 1);
    close(f);
    if (n < 0) n = 0;
    buf[n] = 0;
    char *nl = strchr(buf, '\n');
    if (nl) *nl = 0;
    return buf;
}

// Read a whole small file; its length, or -1.
static long slurp(const char *path, char *buf, size_t size)
{
    int f = open(path, O_RDONLY | O_CLOEXEC);
    if (f < 0) return -1;
    size_t total = 0;
    for (;;) {
        ssize_t n = read(f, buf + total, size - 1 - total);
        if (n <= 0) break;
        total += n;
        if (total >= size - 1) break;
    }
    close(f);
    buf[total] = 0;
    return total;
}

static int gadget_put(const char *gadget, const char *attr, const char *value)
{
    char path[256];
    snprintf(path, sizeof path, GADGETS "/%s/%s", gadget, attr);
    int err = put(path, value);
    if (err) sayf("[ctl] write %s failed: %s\n", path, strerror(-err));
    return err;
}

static int gadget_mkdir(const char *gadget, const char *dir)
{
    char path[256];
    snprintf(path, sizeof path, GADGETS "/%s%s%s", gadget, *dir ? "/" : "", dir);
    if (mkdir(path, 0755) && errno != EEXIST) {
        sayf("[ctl] mkdir %s failed: %s\n", path, strerror(errno));
        return -1;
    }
    return 0;
}

static int set_up(const char *ifname)
{
    struct ifreq ifr;
    int s = socket(AF_INET6, SOCK_DGRAM | SOCK_CLOEXEC, 0);
    if (s < 0) return -errno;
    memset(&ifr, 0, sizeof ifr);
    snprintf(ifr.ifr_name, sizeof ifr.ifr_name, "%s", ifname);
    int err = 0;
    if (ioctl(s, SIOCGIFFLAGS, &ifr) < 0) err = -errno;
    else if (!(ifr.ifr_flags & IFF_UP)) {
        ifr.ifr_flags |= IFF_UP;
        if (ioctl(s, SIOCSIFFLAGS, &ifr) < 0) err = -errno;
    }
    close(s);
    return err;
}

// Copy the kernel log to the serial port, record by record, as "[sec.usec] text".
// Runs in a child. A full 8 KiB u_serial FIFO (host not reading yet) makes write()
// return 0 or EAGAIN; the child then waits and retries the same record, so nothing
// is dropped while the kernel's log buffer still holds it. The port is raw: nothing
// a host might send is echoed back, and lines end in exactly "\r\n".
static void stream_kmsg(const char *tty, struct stream_stats *st)
{
    int in = open("/dev/kmsg", O_RDONLY | O_CLOEXEC);
    int out = open(tty, O_WRONLY | O_NOCTTY | O_NONBLOCK | O_CLOEXEC);
    if (in < 0 || out < 0) _exit(1);
    struct termios t;
    if (!tcgetattr(out, &t)) {
        cfmakeraw(&t);
        tcsetattr(out, TCSANOW, &t);
    }
    char rec[8192], line[8192 + 32];
    for (;;) {
        ssize_t n = read(in, rec, sizeof rec - 1);
        if (n < 0) {
            if (errno == EPIPE || errno == EINTR) continue;   // overrun: continue with the newest
            _exit(2);
        }
        if (n == 0) continue;
        rec[n] = 0;
        char *nl = strchr(rec, '\n');
        if (nl) *nl = 0;
        char *sep = strchr(rec, ';');
        unsigned long seq = 0, usec = 0;
        if (sep) sscanf(rec, "%*u,%lu,%lu", &seq, &usec);
        int len = snprintf(line, sizeof line, "[%5lu.%06lu] %s\r\n", usec / 1000000, usec % 1000000,
                           sep ? sep + 1 : rec);
        int q;
        for (int off = 0; off < len;) {
            ssize_t w = write(out, line + off, len - off);
            if (w > 0) { off += w; st->bytes += w; continue; }
            if (w < 0 && errno != EAGAIN && errno != EINTR) _exit(3);
            if (!ioctl(out, TIOCOUTQ, &q)) st->queued = q;
            usleep(100000);
        }
        st->records++;
        if (!ioctl(out, TIOCOUTQ, &q)) st->queued = q;
    }
}

static void port_dart_report(struct port *p);   // defined with the DART helpers below

static pid_t spawn_stream(const char *tty, struct stream_stats *st)
{
    pid_t pid = fork();
    if (pid == 0) {
        setsid();
        stream_kmsg(tty, st);
        _exit(0);
    }
    return pid;
}

static void start_streamer(struct port *p)
{
    if (!p->tty[0] || p->streamer_starts >= 20) return;
    p->streamer_starts++;
    p->streamer = spawn_stream(p->tty, p->st);
}

// One gser gadget on one UDC. Each step is reported, so the screen names a failure.
static void setup_port(struct port *p)
{
    char g[16], v[64];
    snprintf(g, sizeof g, "g%d", p->index);
    if (gadget_mkdir(g, "")) return;
    gadget_put(g, "idVendor", "0x1d6b");        // Linux Foundation
    gadget_put(g, "idProduct", "0x0104");       // Multifunction Composite Gadget
    gadget_put(g, "bcdDevice", BCD_DEVICE);
    gadget_put(g, "bcdUSB", "0x0200");
    if (gadget_mkdir(g, "strings/0x409")) return;
    gadget_put(g, "strings/0x409/manufacturer", "iLinux");
    snprintf(v, sizeof v, "iLinux J716c control channel, port %d", p->index);
    gadget_put(g, "strings/0x409/product", v);
    snprintf(v, sizeof v, "ilinux-port%d", p->index);   // not a hardware serial
    gadget_put(g, "strings/0x409/serialnumber", v);
    if (gadget_mkdir(g, "functions/" FUNCTION)) return;
    if (gadget_mkdir(g, "configs/c.1") || gadget_mkdir(g, "configs/c.1/strings/0x409")) return;
    gadget_put(g, "configs/c.1/strings/0x409/configuration", "Bulk-only kernel log port");
    char from[256], to[256];
    snprintf(from, sizeof from, GADGETS "/%s/functions/" FUNCTION, g);
    snprintf(to, sizeof to, GADGETS "/%s/configs/c.1/" FUNCTION, g);
    if (symlink(from, to) && errno != EEXIST) {
        sayf("[ctl] link %s failed: %s\n", to, strerror(errno));
        return;
    }
    if (gadget_put(g, "UDC", p->udc)) return;
    p->bound = 1;
    char num[16];
    snprintf(from, sizeof from, GADGETS "/%s/functions/" FUNCTION "/port_num", g);
    get(from, num, sizeof num);
    if (num[0]) snprintf(p->tty, sizeof p->tty, "/dev/ttyGS%s", num);
    start_streamer(p);
    sayf("[ctl] port %d: UDC %s bound, GSER bulk-only 1d6b:0104 bcdDevice " BCD_DEVICE
         ", no interrupt endpoint, log on %s\n", p->index, p->udc, p->tty[0] ? p->tty + 5 : "no tty");
    port_dart_report(p);
}

static int port_index(const char *udc)
{
    for (unsigned i = 0; i < sizeof known_udc / sizeof *known_udc; i++)
        if (!strcmp(udc, known_udc[i].udc)) return i + 1;
    int next = 4;
    for (int i = 0; i < nports; i++)
        if (ports[i].index >= next) next = ports[i].index + 1;
    return next <= 9 ? next : -1;
}

static int by_name(const void *a, const void *b)
{
    return strcmp(*(char *const *)a, *(char *const *)b);
}

// Set up any UDC not seen before (probes can finish after PID 1 starts).
static void scan_udcs(void)
{
    char *names[MAX_UDC];
    int n = 0;
    DIR *d = opendir("/sys/class/udc");
    if (!d) return;
    struct dirent *e;
    while ((e = readdir(d)) && n < MAX_UDC)
        if (e->d_name[0] != '.') names[n++] = strdup(e->d_name);
    closedir(d);
    qsort(names, n, sizeof *names, by_name);
    for (int i = 0; i < n; i++) {
        int seen = 0;
        for (int j = 0; j < nports; j++)
            if (!strcmp(ports[j].udc, names[i])) seen = 1;
        int index = seen ? -1 : port_index(names[i]);
        if (!seen && index > 0 && nports < MAX_UDC && strlen(names[i]) < sizeof ports[0].udc) {
            struct port *p = &ports[nports];
            memset(p, 0, sizeof *p);
            p->st = &stats[nports++];
            snprintf(p->udc, sizeof p->udc, "%s", names[i]);
            p->index = index;
            setup_port(p);
        }
        free(names[i]);
    }
}

static pid_t spawn(char *const argv[])
{
    pid_t pid = fork();
    if (pid == 0) {
        setsid();
        int null = open("/dev/null", O_RDONLY);
        if (null >= 0) dup2(null, 0);
        int c = open("/dev/console", O_WRONLY);
        if (c >= 0) { dup2(c, 1); dup2(c, 2); }
        execv(argv[0], argv);
        _exit(127);
    }
    return pid;
}

static void start_dropbear(void)
{
    // -F foreground, -E log to the console, -s no password logins, -R host keys
    // on first use (RAM only), -j/-k no port forwarding, -K 15 keepalive.
    static char *const argv[] = { "/usr/bin/dropbear", "-F", "-E", "-s", "-R", "-j", "-k",
                                  "-K", "15", "-p", "22", NULL };
    if (dropbear_starts >= 20) return;
    dropbear_starts++;
    dropbear_pid = spawn(argv);
    sayf("[ctl] dropbear start %d: pid %d, port 22, key-only root\n", dropbear_starts,
         (int)dropbear_pid);
}

static void reap(void)
{
    int st;
    pid_t pid;
    while ((pid = waitpid(-1, &st, WNOHANG)) > 0) {
        if (pid == dropbear_pid) {
            sayf("[ctl] dropbear exited (status 0x%x); restarting\n", st);
            dropbear_pid = -1;
        } else if (pid == selftest_pid) {
            sayf("[ctl] selftest exit=%d\n", WIFEXITED(st) ? WEXITSTATUS(st) : 128 + WTERMSIG(st));
            selftest_pid = -1;
        } else if (pid == status_pid) {   // a status reader that finished late
            sayf("[ctl] dwc3 status reader finished after being stuck since heartbeat %03d\n",
                 status_stuck_since);
            status_pid = -1;
            status_stuck_since = -1;
        } else {
            for (int i = 0; i < nports; i++)
                if (pid == ports[i].streamer) {
                    ports[i].streamer = -1;
                    if (ports[i].stopped) continue;   // stopped at a bus error: stays stopped
                    sayf("[ctl] log streamer for port %d exited (status 0x%x); restarting\n",
                         ports[i].index, st);
                    start_streamer(&ports[i]);
                }
        }
    }
    if (dropbear_pid < 0) start_dropbear();
}

// ---- dwc3 state (debugfs) -------------------------------------------------
// Files read, all under /sys/kernel/debug/usb/<UDC>/ (drivers/usb/dwc3/debugfs.c of the
// boot036 tree): link_state (reads GSTS and DSTS), regdump (register reads only) and
// ep<N>{in,out}/transfer_type and trb_ring (driver memory only). Never read: the FIFO
// and queue files, GDBGEPINFO and lsp_dump, whose reads write a debug select register.

#define DEBUG_USB "/sys/kernel/debug/usb"

struct buf { char *s; size_t size, len; };   // bounded appends, always NUL-terminated

static void add(struct buf *b, const char *fmt, ...)
{
    if (b->len + 1 >= b->size) return;
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(b->s + b->len, b->size - b->len, fmt, ap);
    va_end(ap);
    if (n > 0) b->len += n;
    if (b->len >= b->size) b->len = b->size - 1;
}

// Value of a "NAME = 0x%08x" line in a regdump text; 0 if found.
static int reg(const char *dump, const char *name, unsigned *value)
{
    size_t len = strlen(name);
    for (const char *s = dump; *s; ) {
        if (!strncmp(s, name, len) && !strncmp(s + len, " = 0x", 5))
            return sscanf(s + len + 5, "%x", value) == 1 ? 0 : -1;
        const char *nl = strchr(s, '\n');
        if (!nl) break;
        s = nl + 1;
    }
    return -1;
}

// " o:start" style: the last command written to an endpoint's DEPCMD register;
// '*' = still active (CMDACT), "!N" = nonzero command status.
static void depcmd(struct buf *b, const char *label, unsigned v)
{
    static const char *const names[16] = {
        "none", "cfg", "rsc", "getstate", "stall", "clrstall", "start", "update",
        "end", "startcfg", "c10", "c11", "c12", "c13", "c14", "c15" };
    add(b, " %s:%s%s", label, names[v & 0xf], (v & (1u << 10)) ? "*" : "");
    if ((v >> 12) & 0xf) add(b, "!%u", (v >> 12) & 0xf);
}

// Hardware-owned TRBs and the dequeue index in one endpoint's trb_ring; -1 if unknown.
static void trb_state(const char *path, int *hwo, int *deq)
{
    static char text[32768];
    *hwo = *deq = -1;
    if (slurp(path, text, sizeof text) <= 0) return;
    *hwo = 0;
    int i = -1;   // the header line comes first
    for (char *s = text; *s; i++) {
        char *nl = strchr(s, '\n');
        if (nl) *nl = 0;
        int commas = 0;
        char *c = s;
        while (*c && commas < 8)
            if (*c++ == ',') commas++;
        if (i >= 0 && commas == 8) {   // ...,lst,hwo  then the E and D markers
            if (*c == '1') (*hwo)++;
            if (strchr(c + 1, 'D')) *deq = i;
        }
        if (!nl) break;
        s = nl + 1;
    }
}

// The DT interrupt number (cell 1 of the first 3-cell AIC specifier) of a device node.
static long dt_irq(const char *of_node_dir)
{
    char path[320];
    unsigned char cells[12];
    snprintf(path, sizeof path, "%s/interrupts", of_node_dir);
    int f = open(path, O_RDONLY | O_CLOEXEC);
    if (f < 0) return -1;
    ssize_t n = read(f, cells, sizeof cells);
    close(f);
    if (n != 12) return -1;
    return (long)cells[4] << 24 | cells[5] << 16 | cells[6] << 8 | cells[7];
}

// Interrupt count of the /sys/kernel/irq entry whose actions name `action` and whose
// AIC hwirq (bits 15:0 = the DT interrupt) is `want`; -1 if none. *linux_irq gets its
// number and *matches how many of its actions are `action`. A shared line lists its actions
// comma-separated, so the match is by substring.
static long irq_count_of(const char *action, long want, int *linux_irq, int *matches)
{
    char path[320], text[256];
    if (linux_irq) *linux_irq = -1;
    if (matches) *matches = 0;
    if (want < 0) return -1;
    DIR *d = opendir(SYSROOT "/sys/kernel/irq");
    if (!d) return -1;
    long total = -1;
    struct dirent *e;
    while (total < 0 && (e = readdir(d))) {
        if (e->d_name[0] == '.') continue;
        snprintf(path, sizeof path, SYSROOT "/sys/kernel/irq/%s/actions", e->d_name);
        get(path, text, sizeof text);
        if (!strstr(text, action)) continue;
        snprintf(path, sizeof path, SYSROOT "/sys/kernel/irq/%s/hwirq", e->d_name);
        if ((long)(strtoul(get(path, text, sizeof text), 0, 10) & 0xffff) != want) continue;
        if (matches) {
            snprintf(path, sizeof path, SYSROOT "/sys/kernel/irq/%s/actions", e->d_name);
            get(path, text, sizeof text);
            for (const char *s = text; (s = strstr(s, action)); s += strlen(action)) (*matches)++;
        }
        snprintf(path, sizeof path, SYSROOT "/sys/kernel/irq/%s/per_cpu_count", e->d_name);
        get(path, text, sizeof text);
        if (linux_irq) *linux_irq = atoi(e->d_name);
        total = 0;
        for (char *s = text; *s; s++) {
            total += strtol(s, &s, 10);
            if (*s != ',') break;
        }
    }
    closedir(d);
    return total;
}

// Interrupt count of the "dwc3" action whose hwirq matches this UDC's DT interrupt.
static long irq_count(const char *udc)
{
    char dir[320];
    snprintf(dir, sizeof dir, SYSROOT "/sys/class/udc/%.63s/device/of_node", udc);
    return irq_count_of("dwc3", dt_irq(dir), NULL, NULL);
}

// ---- the DART behind each core ---------------------------------------------------------
// The kernel links a DMA master to its IOMMU: <dwc3 device>/iommu -> the DART's class
// device (…/<dart>.iommu/iommu/apple-dart.<dart>.iommu); apple-dart returns there the DART
// of the core's first iommus entry (apple_dart_probe_device: stream_maps[0]). The dwc3
// node's iommus cells name every DART the DT gives the core, with its stream; each phandle
// is found among the DART platform devices' of_node (phandle, reg, interrupts), whose
// driver link says whether apple-dart is bound. The ADT pairs instance 0 and instance 1 of
// one dart-usbN node on one interrupt (known_udc): the boot036-040 DT gives the core
// instance 1 only, boot041's both.

static unsigned be32(const unsigned char *c)
{
    return (unsigned)c[0] << 24 | (unsigned)c[1] << 16 | (unsigned)c[2] << 8 | c[3];
}

// The DART platform device whose DT node has this phandle: its base (DT reg), fault IRQ (DT
// interrupts) and whether the apple-dart driver is bound to it; 0 if found, -1 if not.
static int dart_by_phandle(unsigned phandle, unsigned long long *base, unsigned *hwirq, int *bound)
{
    char path[320], target[320];
    unsigned char cells[16];
    int found = -1;
    DIR *d = opendir(SYSROOT "/sys/bus/platform/devices");
    if (!d) return -1;
    struct dirent *e;
    while (found && (e = readdir(d))) {
        size_t n = strlen(e->d_name);
        if (n < 7 || strcmp(e->d_name + n - 6, ".iommu")) continue;
        snprintf(path, sizeof path, SYSROOT "/sys/bus/platform/devices/%.200s/of_node/phandle", e->d_name);
        int f = open(path, O_RDONLY | O_CLOEXEC);
        if (f < 0) continue;
        ssize_t got = read(f, cells, 4);
        close(f);
        if (got != 4 || be32(cells) != phandle) continue;
        snprintf(path, sizeof path, SYSROOT "/sys/bus/platform/devices/%.200s/of_node/reg", e->d_name);
        f = open(path, O_RDONLY | O_CLOEXEC);
        got = f < 0 ? -1 : read(f, cells, sizeof cells);
        if (f >= 0) close(f);
        if (got != 16) break;   // /soc has two address and two size cells
        *base = (unsigned long long)be32(cells) << 32 | be32(cells + 4);
        snprintf(path, sizeof path, SYSROOT "/sys/bus/platform/devices/%.200s/of_node", e->d_name);
        long irq = dt_irq(path);
        *hwirq = irq < 0 ? 0 : (unsigned)irq;
        snprintf(path, sizeof path, SYSROOT "/sys/bus/platform/devices/%.200s/driver", e->d_name);
        ssize_t len = readlink(path, target, sizeof target - 1);
        target[len > 0 ? len : 0] = 0;
        const char *driver = strrchr(target, '/');
        *bound = !strcmp(driver ? driver + 1 : target, "apple-dart");
        found = 0;
    }
    closedir(d);
    return found;
}

// The bases are confirmed, and both instances' registers may be read, only when the kernel
// attached the core to the DT's first DART, every DART the DT gives the core is instance 0
// or 1 of this port's ADT pair on the same fault interrupt, and instance 1 is one of them.
// Instance 0's base is then the pair's, also when the DT leaves it out (boot036-040).
static void dart_identify(struct port *p)
{
    struct dartinfo *d = &p->dart;
    char path[320], target[320], of_dir[384];
    unsigned char cells[8 * MAX_DARTS];
    memset(d, 0, sizeof *d);
    d->linux_irq = -1;
    snprintf(path, sizeof path, SYSROOT "/sys/class/udc/%.63s/device/iommu", p->udc);
    if (!realpath(path, target)) return;
    const char *name = strrchr(target, '/');
    if (!name) return;
    snprintf(d->name, sizeof d->name, "%s", name + 1);
    // …/<dart platform device>/iommu/apple-dart.<dart>.iommu: two levels up is the device.
    char *cut = strrchr(target, '/');
    if (cut) *cut = 0;
    cut = strrchr(target, '/');
    if (cut) *cut = 0;
    const char *devname = strrchr(target, '/');
    if (!devname) return;
    unsigned long long linked = strtoull(devname + 1, NULL, 16);
    d->base = linked;
    snprintf(of_dir, sizeof of_dir, "%s/of_node", target);
    long irq = dt_irq(of_dir);
    if (irq < 0) return;
    d->hwirq = (unsigned)irq;
    d->known = 1;
    int pair = -1;
    for (unsigned i = 0; i < sizeof known_udc / sizeof *known_udc; i++)
        if (!strcmp(p->udc, known_udc[i].udc)) pair = i;
    snprintf(path, sizeof path, SYSROOT "/sys/class/udc/%.63s/device/of_node/iommus", p->udc);
    int f = open(path, O_RDONLY | O_CLOEXEC);
    ssize_t got = f < 0 ? -1 : read(f, cells, sizeof cells);
    if (f >= 0) close(f);
    int confirmed = pair >= 0 && got >= 8 && got % 8 == 0, have1 = 0;
    for (int i = 0; got >= 8 && i < got / 8; i++) {
        unsigned hw = 0;
        d->dt[i].sid = be32(cells + 8 * i + 4);
        d->dt[i].inst = -1;
        if (dart_by_phandle(be32(cells + 8 * i), &d->dt[i].base, &hw, &d->dt[i].bound) == 0 && pair >= 0
                && hw == d->hwirq)
            d->dt[i].inst = d->dt[i].base == known_udc[pair].dart0 ? 0
                          : d->dt[i].base == known_udc[pair].dart1 ? 1 : -1;
        if (d->dt[i].inst < 0) confirmed = 0;
        if (d->dt[i].inst == 1 && !have1) {
            have1 = 1;
            d->sid = d->dt[i].sid;
            d->bound[1] = d->dt[i].bound;
        }
        if (d->dt[i].inst == 0 && !d->in_dt0) {
            d->in_dt0 = 1;
            d->sid0 = d->dt[i].sid;
            d->bound[0] = d->dt[i].bound;
        }
        d->ndt++;
    }
    if (confirmed && have1 && d->dt[0].base == linked) {
        d->base = known_udc[pair].dart1;
        d->base0 = known_udc[pair].dart0;
    }
}

// Count of the DART fault interrupt behind this port (and its Linux number and how many
// apple-dart fault handlers share it); -1 if unknown.
static long dart_irq_count(struct port *p)
{
    if (!p->dart.known) return -1;
    return irq_count_of("apple-dart fault handler", p->dart.hwirq, &p->dart.linux_irq, &p->dart.handlers);
}

// One line: which dwc3 interrupt, DART instances, streams and fault interrupt serve the port.
static void dart_identity_text(struct port *p, struct buf *b)
{
    char dir[320];
    int dwc3_irq = -1;
    const struct dartinfo *d = &p->dart;
    snprintf(dir, sizeof dir, SYSROOT "/sys/class/udc/%.63s/device/of_node", p->udc);
    long hw = dt_irq(dir);
    irq_count_of("dwc3", hw, &dwc3_irq, NULL);
    add(b, "[usb%d] %s irq %lx(%d)", p->index, p->udc, hw < 0 ? 0 : hw, dwc3_irq);
    if (!d->known) {
        add(b, " no iommu link in sysfs\n");
        return;
    }
    dart_irq_count(p);
    if (!d->base0)   // what the kernel linked; nothing is read
        add(b, " iommu %s, %d DART%s in DT: bases not confirmed\n", d->name, d->ndt, d->ndt == 1 ? "" : "s");
    else if (d->in_dt0)   // boot041's DT: both instances, and the fault handlers on their shared line
        add(b, " dart0 %llx sid %u + dart1 %llx sid %u fault irq %x(%d) x%d\n", d->base0, d->sid0, d->base,
            d->sid, d->hwirq, d->linux_irq, d->handlers);
    else
        add(b, " dart1 %llx sid %u fault irq %x(%d); dart0 %llx not in DT\n", d->base, d->sid, d->hwirq,
            d->linux_irq, d->base0);
}

// Registers of one t8110-class DART instance, read through /dev/mem: 32-bit loads only,
// never a write. Offsets from drivers/iommu/apple-dart.c (DART_T8110_*): PARAMS1-4 0x00-0x0c,
// TLB_CMD 0x80, ERROR 0x100, ERROR_MASK 0x104, ERROR_ADDR_LO/HI 0x170/0x174, ERROR_STREAMS
// 0x1c0, PROTECT 0x200, ENABLE_STREAMS 0xc00, TCR 0x1000 + 4*sid, TTBR 0x1400 + 4*sid.
// A DART whose PARAMS3 bits 15:0 report version 2.2 or later keeps its fault state elsewhere
// (dart-diag/rea-dart-2026-10-18.md; the boot040 kernel patch part 2 uses the same offsets):
// pending bitmap 0x4000, mask 0x4060, control 0x210, protection status 0x704 (0x4204 from
// 2.4), and a 64-byte block per stream at 0x8000 + 0x40*sid (summary +0, address +8/+0xc).
// Those are read only when the version says so; the instance window is 0xc000 (ADT reg).
static int dart_peek(unsigned long long base, struct dart_regs *r)
{
    int f = open(SYSROOT "/dev/mem", O_RDONLY | O_SYNC | O_CLOEXEC);
    if (f < 0) return -errno;
    volatile unsigned *m = mmap(NULL, 0xc000, PROT_READ, MAP_SHARED, f, (off_t)base);
    int err = m == MAP_FAILED ? -errno : 0;
    close(f);
    if (err) return err;
    for (int i = 0; i < 4; i++) r->params[i] = m[i];
    r->tlb = m[0x80 / 4];
    r->err = m[0x100 / 4];
    r->mask = m[0x104 / 4];
    r->addr_lo = m[0x170 / 4];
    r->addr_hi = m[0x174 / 4];
    r->streams = m[0x1c0 / 4];
    r->prot = m[0x200 / 4];
    r->enable = m[0xc00 / 4];
    for (int sid = 0; sid < 2; sid++) {
        r->tcr[sid] = m[0x1000 / 4 + sid];
        r->ttbr[sid] = m[0x1400 / 4 + sid];
    }
    r->version = r->params[2] & 0xffff;
    if (r->version >= 0x0202) {
        r->g22_pending = m[0x4000 / 4];
        r->g22_mask = m[0x4060 / 4];
        r->ctrl = m[0x210 / 4];
        r->prot_status = m[(r->version >= 0x0204 ? 0x4204 : 0x704) / 4];
        for (int sid = 0; sid < 2; sid++) {
            r->s[sid].summary = m[(0x8000 + 0x40 * sid) / 4];
            r->s[sid].addr_lo = m[(0x8000 + 0x40 * sid + 0x08) / 4];
            r->s[sid].addr_hi = m[(0x8000 + 0x40 * sid + 0x0c) / 4];
        }
    }
    munmap((void *)m, 0xc000);
    return 0;
}

// One DART instance's pending-fault word for the short line, through /dev/mem as dart_peek
// (32-bit loads, never a write): PARAMS3 for the version, then the per-stream pending bitmap
// (0x4000, streams 0-31) on a version 2.2 or later DART, else ERROR_STREAMS (0x1c0), the
// older layout's per-stream error bitmap. The word, or -errno.
static long long dart_pending(unsigned long long base)
{
    int f = open(SYSROOT "/dev/mem", O_RDONLY | O_SYNC | O_CLOEXEC);
    if (f < 0) return -errno;
    volatile unsigned *m = mmap(NULL, 0xc000, PROT_READ, MAP_SHARED, f, (off_t)base);
    int err = m == MAP_FAILED ? -errno : 0;
    close(f);
    if (err) return err;
    unsigned word = (m[0x08 / 4] & 0xffff) >= 0x0202 ? m[0x4000 / 4] : m[0x1c0 / 4];
    munmap((void *)m, 0xc000);
    return word;
}

// The snapshot's text: the static parameters once (with_params), then the fault and
// translation state. ERROR bit 31 is the driver's fault flag ("FAULT"); its code bits
// 5..0 mean read fault, write fault, no PTE, no PMD, no PGD, no TTBR; stream in 27:20.
static void dart_regs_text(struct buf *b, int port, int inst, unsigned long long base,
                           const struct dart_regs *r, int with_params)
{
    if (with_params)
        add(b, "[usb%d] dart%d @%llx p1 %08x p2 %08x p3 %08x p4 %08x prot %x en %x\n", port, inst, base,
            r->params[0], r->params[1], r->params[2], r->params[3], r->prot, r->enable);
    add(b, "[usb%d] dart%d err %08x%s strm %x addr %x%08x tcr %x/%x ttbr %x/%x tlb %x mask %x\n",
        port, inst, r->err, (r->err >> 31) ? " FAULT" : "", r->streams, r->addr_hi, r->addr_lo,
        r->tcr[0], r->tcr[1], r->ttbr[0], r->ttbr[1], r->tlb, r->mask);
    if (r->version >= 0x0202)   // the v2.2 fault layout: pending streams, mask, control, protection, blocks 0-1
        add(b, "[usb%d] dart%d v%u.%u pend %x mask %x ctl %x prot %x s0 %08x@%llx s1 %08x@%llx\n", port, inst,
            r->version >> 8, r->version & 0xff, r->g22_pending, r->g22_mask, r->ctrl, r->prot_status,
            r->s[0].summary, (unsigned long long)r->s[0].addr_hi << 32 | r->s[0].addr_lo,
            r->s[1].summary, (unsigned long long)r->s[1].addr_hi << 32 | r->s[1].addr_lo);
}

// Both DART instances of the port: instance 0 and instance 1 of its dart-usbN pair, the
// DT's and, on the boot036-040 DT, the sibling it leaves out. Nothing is read unless
// dart_identify confirmed the bases, so an unknown UDC (the VM's dummy_udc) reads no device
// memory. The values read stay in the port's dartinfo for the setup line.
static void dart_snapshot_text(struct port *p, struct buf *b, int with_params)
{
    struct dartinfo *d = &p->dart;
    d->regs_ok[0] = d->regs_ok[1] = 0;
    if (!d->known || !d->base0) {
        add(b, "[usb%d] dart regs not read (no confirmed DART bases for %s)\n", p->index, p->udc);
        return;
    }
    unsigned long long bases[2] = { d->base0, d->base };
    for (int inst = 0; inst < 2; inst++) {
        struct dart_regs *r = &d->regs[inst];
        memset(r, 0, sizeof *r);
        int err = dart_peek(bases[inst], r);
        if (err) add(b, "[usb%d] dart%d @%llx regs n/a (%s)\n", p->index, inst, bases[inst], strerror(-err));
        else {
            d->regs_ok[inst] = 1;
            dart_regs_text(b, p->index, inst, bases[inst], r, with_params);
        }
    }
}

// Whether a DART instance translates a stream the way the kernel sets it up for a DMA
// domain (apple_dart_setup_translation): the stream enabled, TCR translate (bit 0) without
// bypass (bits 2:1), TTBR valid (bit 0). The snapshot holds streams 0 and 1.
static int stream_set_up(const struct dart_regs *r, unsigned sid)
{
    return sid < 2 && (r->enable >> sid & 1) && (r->tcr[sid] & 7) == 1 && (r->ttbr[sid] & 1);
}

// After the bind snapshot, one line: per DART instance the DT gives the core, its stream,
// whether apple-dart is bound to it, and that stream's TCR and TTBR; then the verdict. Both
// set up = both bound and translating, on one table (the core's one DMA domain).
static void dart_setup_text(struct port *p, struct buf *b)
{
    const struct dartinfo *d = &p->dart;
    if (!d->known || !d->base0) return;
    int insts[2], n = 0, good = 0, unread = 0, same = 1;
    unsigned table = 0;
    if (d->in_dt0) insts[n++] = 0;
    insts[n++] = 1;
    add(b, "[usb%d]", p->index);
    for (int i = 0; i < n; i++) {
        int inst = insts[i];
        unsigned sid = inst ? d->sid : d->sid0;
        const struct dart_regs *r = &d->regs[inst];
        add(b, "%s dart%d sid %u %s", i ? " +" : "", inst, sid, d->bound[inst] ? "bound" : "unbound");
        if (!d->regs_ok[inst] || sid > 1) {
            add(b, " regs n/a");
            unread = 1;
            continue;
        }
        add(b, " tcr %x ttbr %x", r->tcr[sid], r->ttbr[sid]);
        if (d->bound[inst] && stream_set_up(r, sid)) good |= 1 << inst;
        if (i && r->ttbr[sid] != table) same = 0;
        table = r->ttbr[sid];
    }
    const char *verdict;
    if (unread) verdict = "not checked";
    else if (n == 1) verdict = good ? "set up; dart0 not in DT" : "NOT set up; dart0 not in DT";
    else if (good == 3) verdict = same ? "both set up" : "both translating, NOT one table";
    else verdict = good == 2 ? "dart0 NOT set up" : good == 1 ? "dart1 NOT set up" : "neither set up";
    add(b, ": %s\n", verdict);
}

static void say_lines(const char *text)   // one kmsg record per line
{
    char copy[2048];
    snprintf(copy, sizeof copy, "%s", text);
    for (char *s = copy, *nl; *s && (nl = strchr(s, '\n')); s = nl + 1) {
        char c = nl[1];
        nl[1] = 0;
        say(s);
        nl[1] = c;
    }
}

static void dart_snapshot(struct port *p, int with_params)
{
    char text[1024];
    struct buf b = { text, sizeof text, 0 };
    text[0] = 0;
    if (p->dart.known && p->dart.base0)
        sayf("[ctl] port %d: reading DART registers at 0x%llx and 0x%llx through /dev/mem\n", p->index,
             p->dart.base0, p->dart.base);
    dart_snapshot_text(p, &b, with_params);
    say_lines(text);
}

// At bind: the DART identity line, the first register snapshot (with the parameters) and
// whether the kernel set up the DT's instances.
static void port_dart_report(struct port *p)
{
    char text[512];
    struct buf b = { text, sizeof text, 0 };
    text[0] = 0;
    dart_identify(p);
    dart_identity_text(p, &b);
    say(text);
    dart_snapshot(p, 1);
    b.len = 0;
    text[0] = 0;
    dart_setup_text(p, &b);
    if (text[0]) say(text);
}

// The fields of one controller that the short per-port line shows.
struct keyf {
    int ok;                              // the regdump was read
    char link[64];
    unsigned frame;
    long irqs, dart_irqs;                // dwc3 and DART fault interrupt counts, -1 unknown
    int pend_read;                       // both DART instances' pending words: 1 read, -1 failed, 0 not read
    unsigned pend[2];                    // instance 0, instance 1
    int stopped, halted, buserr, csr_timeout, evbusy;
    unsigned buserr_lo, buserr_hi;       // GBUSERRADDR0/1 when buserr
    int neps;
    struct { int num, in, hwo, deq; } ep[6];
};

// Compact state of one dwc3 controller for the status line. If info is given, it also
// gets the controller's endpoint count and FIFO sizes (static after the core's init).
// k gets the key fields; a bus error is also recorded in the port's shared stats.
static void dwc3_state(struct port *p, struct buf *b, struct buf *info, struct keyf *k)
{
    static char dump[32768];
    const char *udc = p->udc;
    char dir[192], path[256], link[64], type[32];
    memset(k, 0, sizeof *k);
    k->irqs = k->dart_irqs = -1;
    snprintf(dir, sizeof dir, SYSROOT DEBUG_USB "/%.63s", udc);
    snprintf(path, sizeof path, "%s/regdump", dir);
    if (slurp(path, dump, sizeof dump) <= 0) {
        add(b, " dwc3 n/a");
        return;
    }
    k->ok = 1;
    snprintf(path, sizeof path, "%s/link_state", dir);
    get(path, link, sizeof link);
    snprintf(k->link, sizeof k->link, "%s", link[0] ? link : "?");
    unsigned gsts = 0, dctl = 0, dsts = 0, evcount = 0, alepena = 0, cmd0 = 0, cmd1 = 0;
    reg(dump, "GSTS", &gsts);
    reg(dump, "DCTL", &dctl);
    reg(dump, "DSTS", &dsts);
    reg(dump, "GEVNTCOUNT(0)", &evcount);
    reg(dump, "DALEPENA", &alepena);
    reg(dump, "DEPCMD(0)", &cmd0);
    reg(dump, "DEPCMD(1)", &cmd1);
    k->frame = (dsts >> 3) & 0x3fff;
    k->stopped = !(dctl & (1u << 31));                     // DCTL.RUN_STOP clear
    k->halted = !!(dsts & (1u << 22));                     // DSTS.DEVCTRLHLT
    k->buserr = !!(gsts & (1u << 4));                      // GSTS.BUS_ERR_ADDR_VLD
    k->csr_timeout = !!(gsts & (1u << 5));                 // GSTS.CSR_TIMEOUT
    k->evbusy = !!(evcount & (1u << 31));                  // GEVNTCOUNT.EVNT_HANDLER_BUSY
    if (k->buserr) {                                       // the first DMA address that failed
        reg(dump, "GBUSERRADDR0", &k->buserr_lo);
        reg(dump, "GBUSERRADDR1", &k->buserr_hi);
        p->st->buserr_lo = k->buserr_lo;
        p->st->buserr_hi = k->buserr_hi;
        p->st->buserr = 1;
    }
    add(b, " dwc3 %s f%u ev%u", k->link, k->frame, evcount & 0xfffc);
    if (k->stopped) add(b, " STOPPED");
    if (k->halted) add(b, " HALTED");
    if (k->buserr) add(b, " BUSERR@%llx", (unsigned long long)k->buserr_hi << 32 | k->buserr_lo);
    if (k->csr_timeout) add(b, " CSR-TIMEOUT");
    if (k->evbusy) add(b, " EVBUSY");
    k->irqs = irq_count(udc);
    if (k->irqs >= 0) add(b, " irq%ld", k->irqs);
    else add(b, " irq?");
    k->dart_irqs = dart_irq_count(p);
    if (p->dart.known && p->dart.base0) {   // both instances' pending faults, in the confirmed bases only
        long long w0 = dart_pending(p->dart.base0), w1 = dart_pending(p->dart.base);
        k->pend_read = w0 >= 0 && w1 >= 0 ? 1 : -1;
        k->pend[0] = w0 >= 0 ? (unsigned)w0 : 0;
        k->pend[1] = w1 >= 0 ? (unsigned)w1 : 0;
    }
    add(b, " ep0");
    depcmd(b, "o", cmd0);
    depcmd(b, "i", cmd1);
    for (int n = 2; n < 32; n++) {                         // DALEPENA: enabled endpoints
        if (!(alepena & (1u << n))) continue;
        char name[16], regname[16];
        unsigned cmd = 0;
        int hwo, deq;
        snprintf(name, sizeof name, "ep%d%s", n >> 1, (n & 1) ? "in" : "out");
        snprintf(path, sizeof path, "%s/%s/transfer_type", dir, name);
        get(path, type, sizeof type);
        snprintf(path, sizeof path, "%s/%s/trb_ring", dir, name);
        trb_state(path, &hwo, &deq);
        snprintf(regname, sizeof regname, "DEPCMD(%d)", n);
        reg(dump, regname, &cmd);
        add(b, " %s %s", name + 2, !strcmp(type, "interrupt") ? "INTERRUPT" : type[0] ? type : "?");
        if (hwo >= 0) add(b, " h%d d%d", hwo, deq);
        else add(b, " h?");
        if ((cmd & (1u << 10)) || ((cmd >> 12) & 0xf)) depcmd(b, "c", cmd);
        if (k->neps < (int)(sizeof k->ep / sizeof *k->ep)) {
            k->ep[k->neps].num = n >> 1;
            k->ep[k->neps].in = n & 1;
            k->ep[k->neps].hwo = hwo;
            k->ep[k->neps].deq = deq;
            k->neps++;
        }
    }
    if (!info) return;
    unsigned id = 0, hw0 = 0, hw3 = 0, fifo = 0;
    reg(dump, "GSNPSID", &id);
    reg(dump, "GHWPARAMS0", &hw0);
    reg(dump, "GHWPARAMS3", &hw3);
    unsigned in_eps = (hw3 >> 18) & 0x1f;
    add(info, "core 0x%08x, %u endpoints (%u IN), MDWIDTH %u; TX FIFO words", id, (hw3 >> 12) & 0x3f,
        in_eps, (hw0 >> 8) & 0xff);
    for (unsigned n = 0; n < in_eps && n < 32; n++) {
        char regname[24];
        snprintf(regname, sizeof regname, "GTXFIFOSIZ(%u)", n);
        if (reg(dump, regname, &fifo)) break;
        add(info, " %u:%u", n, fifo & 0xffff);
    }
    if (!reg(dump, "GRXFIFOSIZ(0)", &fifo)) add(info, "; RX FIFO words %u", fifo & 0xffff);
}

// The short line of one port, about 100 columns, for the film: UDC state, link, SOF frame,
// the dwc3 and DART fault interrupt counts, both DART instances' pending-fault words
// (boot041: "pend <instance 0>/<instance 1>"), the bytes accepted and queued (or "nostream"
// once the streamer was stopped), every enabled endpoint's hardware-owned TRBs and dequeue
// index, the flags, a bus error with its address last. The record count and the EP0
// commands stay in the long line. Three endpoints, two halt flags, a bus error and the
// pending words at once can reach about 115 columns.
static void brief_line(struct buf *b, struct port *p, const char *state, const struct keyf *k, int with_dwc3)
{
    add(b, "[usb%d] %s", p->index, state[0] ? state : "?");
    if (!p->bound) add(b, " unbound");
    else if (!p->tty[0]) add(b, " no-tty");
    if (with_dwc3 && k->ok) {
        add(b, " %s f%u", k->link, k->frame);
        if (k->irqs >= 0) add(b, " irq%ld", k->irqs);
        else add(b, " irq?");
        if (k->dart_irqs >= 0) add(b, " dart%ld", k->dart_irqs);
        else add(b, " dart?");
        if (k->pend_read > 0) add(b, " pend %x/%x", k->pend[0], k->pend[1]);
        else if (k->pend_read < 0) add(b, " pend ?");
    }
    if (p->stopped) add(b, " nostream");                  // stopped at a bus error; counters frozen
    else if (p->bound && p->tty[0]) add(b, " %luB q%d", p->st->bytes, p->st->queued);
    if (!with_dwc3) return;
    if (!k->ok) {
        add(b, " dwc3 n/a");
        return;
    }
    for (int i = 0; i < k->neps; i++) {
        add(b, " %d%c", k->ep[i].num, k->ep[i].in ? 'i' : 'o');
        if (k->ep[i].hwo >= 0) add(b, " h%d d%d", k->ep[i].hwo, k->ep[i].deq);
        else add(b, " h?");
    }
    if (k->stopped) add(b, " STOPPED");
    if (k->halted) add(b, " HALTED");
    if (k->csr_timeout) add(b, " CSR-TIMEOUT");
    if (k->evbusy) add(b, " EVBUSY");
    if (k->buserr) add(b, " BUSERR@%llx", (unsigned long long)k->buserr_hi << 32 | k->buserr_lo);
}

// The status line: per port, the UDC state, the log stream's counters (records,
// bytes accepted, bytes still queued in the M5's FIFO) and, with with_dwc3, the
// controller state; pre gets the one-time controller lines that come before it, and
// brief one short line per port (printed between the heartbeat and the long line).
static void build_status(struct buf *line, struct buf *pre, struct buf *brief, int with_dwc3)
{
    char state[64], path[160], text[256];
    struct keyf k;
    add(line, "[ctl] %s", nports ? "" : "no UDC");
    for (int i = 0; i < nports; i++) {
        struct port *p = &ports[i];
        snprintf(path, sizeof path, SYSROOT "/sys/class/udc/%.63s/state", p->udc);
        get(path, state, sizeof state);
        add(line, "%sport%d %s", i ? " | " : "", p->index, state[0] ? state : "?");
        if (!p->bound) add(line, " unbound");
        else if (!p->tty[0]) add(line, " no-tty");
        else add(line, " log %luL %luB q%d", p->st->records, p->st->bytes, p->st->queued);
        memset(&k, 0, sizeof k);
        k.irqs = k.dart_irqs = -1;
        if (with_dwc3) {
            struct buf info = { text, sizeof text, 0 };
            text[0] = 0;
            dwc3_state(p, line, p->st->info_done ? NULL : &info, &k);
            if (info.len) {
                add(pre, "[ctl] port%d dwc3: %s\n", p->index, text);
                p->st->info_done = 1;
            }
        }
        brief_line(brief, p, state, &k, with_dwc3);
        add(brief, "\n");
    }
}

static void status_line(int with_dwc3)
{
    char line[1000], pre[1024], brief[1024];
    struct buf b = { line, sizeof line - 1, 0 }, p = { pre, sizeof pre, 0 }, q = { brief, sizeof brief, 0 };
    line[0] = pre[0] = brief[0] = 0;                                        // room for '\n'
    build_status(&b, &p, &q, with_dwc3);
    line[b.len++] = '\n';
    line[b.len] = 0;
    say_lines(pre);     // one kmsg record each
    say_lines(brief);
    say(line);
}

// The first bus error on a port: its log streamer is stopped for good (a stalled bulk
// path no longer gets the kernel log copied into it, and the later kernel messages are
// read on the console), and both DART instances' registers are shown while the fault is
// fresh. The streamer's death is reaped without a restart (stopped).
static void bus_error_text(struct port *p, struct buf *b)
{
    add(b, "[ctl] port %d: dwc3 bus error at DMA address 0x%llx: log streamer %s; kernel messages "
        "stay on the console\n", p->index, (unsigned long long)p->st->buserr_hi << 32 | p->st->buserr_lo,
        p->streamer > 0 ? "stopped" : "not running");
}

static void on_bus_error(struct port *p)
{
    char text[256];
    struct buf b = { text, sizeof text, 0 };
    text[0] = 0;
    p->stopped = 1;
    bus_error_text(p, &b);
    if (p->streamer > 0) kill(p->streamer, SIGKILL);
    say(text);
    dart_snapshot(p, 0);
}

// The status line is built in a child that also reads the dwc3 state, so a debugfs read
// that blocks, or a fault in the parsing, costs one status line and never the heartbeat.
// A child still running after 2 s is left alone and reported; until it exits, /init
// prints the line without the dwc3 state.
static void status(int beat)
{
    if (status_pid > 0) {
        sayf("[ctl] dwc3 status reader pid %d stuck since heartbeat %03d\n", (int)status_pid,
             status_stuck_since);
        status_line(0);
        return;
    }
    pid_t pid = fork();
    if (pid < 0) {
        status_line(0);
        return;
    }
    if (pid == 0) {
        status_line(1);
        _exit(0);
    }
    for (int i = 0; i < 200; i++) {
        int st;
        if (waitpid(pid, &st, WNOHANG) == pid) {
            if (!WIFEXITED(st) || WEXITSTATUS(st)) {
                sayf("[ctl] dwc3 status reader failed (status 0x%x)\n", st);
                status_line(0);
            }
            for (int j = 0; j < nports; j++)   // the child records a bus error in shared memory
                if (ports[j].st->buserr && !ports[j].stopped) on_bus_error(&ports[j]);
            return;
        }
        usleep(10000);
    }
    status_pid = pid;
    status_stuck_since = beat;
    sayf("[ctl] dwc3 status reader pid %d did not finish in 2 s\n", (int)pid);
    status_line(0);
}

static void control_channel_init(void)
{
    mkdir("/dev/pts", 0755);
    if (mount("devpts", "/dev/pts", "devpts", MS_NOSUID | MS_NOEXEC, "mode=620,ptmxmode=666"))
        sayf("[ctl] devpts mount failed: %s\n", strerror(errno));
    if (mount("configfs", "/sys/kernel/config", "configfs", 0, 0))
        sayf("[ctl] configfs mount failed: %s\n", strerror(errno));
    if (mount("debugfs", "/sys/kernel/debug", "debugfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, 0))
        sayf("[ctl] debugfs mount failed: %s\n", strerror(errno));
    else
        say("[ctl] debugfs on /sys/kernel/debug: dwc3 state in every status line\n");
    stats = mmap(NULL, MAX_UDC * sizeof *stats, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS, -1, 0);
    if (stats == MAP_FAILED) {
        static struct stream_stats local[MAX_UDC];
        sayf("[ctl] shared log counters unavailable (%s); they will read 0\n", strerror(errno));
        stats = local;
    }
    sethostname("ilinux-j716c", 12);
    setenv("PATH", "/usr/bin:/usr/sbin:/bin:/sbin", 1);
    setenv("HOME", "/root", 1);
    setenv("TERM", "linux", 1);
    int err = set_up("lo");
    if (err) sayf("[ctl] lo up failed: %s\n", strerror(-err));
    say("\n[ctl] USB control channel: GSER bulk-only kernel log port per UDC, no interrupt endpoint, "
        "no network; boot041: both DART instances per port in the DT, their setup at bind, both "
        "pending-fault words in the short [usbN] lines; boot040's DART lines kept\n");
    for (int i = 0; i < 40 && !nports; i++) {   // up to 10 s for the first UDC
        scan_udcs();
        if (!nports) usleep(250000);
    }
    if (!nports) say("[ctl] no UDC yet (dwc3 not probed); rescanning every heartbeat\n");
    start_dropbear();
}

#ifndef INIT_NO_MAIN
int main(void)
{
    mount("proc", "/proc", "proc", 0, 0);
    mount("sysfs", "/sys", "sysfs", 0, 0);
    mount("devtmpfs", "/dev", "devtmpfs", 0, 0);
    int c = open("/dev/console", O_WRONLY);
    if (c >= 0) con = c;

    say("\n======== iLinux t6050 RAM diagnostic initramfs ========\n");
    say("PID 1 reached: the kernel booted and ran userspace.\n");

    dump("kernel", "/proc/version", 0);
    dump("cmdline", "/proc/cmdline", 0);
    dump("DT model", "/proc/device-tree/model", 128);
    dump("DT compatible", "/proc/device-tree/compatible", 256);
    dump("memory", "/proc/meminfo", 256);
    dump("CPU online mask", "/sys/devices/system/cpu/online", 64);
    dump("cpuinfo", "/proc/cpuinfo", 4096);
    dump("interrupts", "/proc/interrupts", 2048);

    control_channel_init();

    // Heartbeat: shows the online-CPU count over time (SMP may arrive late,
    // or a late fault may change state). Framebuffer console shows the latest.
    char line[96];
    for (int i = 0;; i++) {
        int n = online_cpus();
        int len = 0;
        const char *p = "\n[diag] heartbeat ";
        memcpy(line, p, strlen(p)); len = strlen(p);
        line[len++] = '0' + (i / 100) % 10;
        line[len++] = '0' + (i / 10) % 10;
        line[len++] = '0' + i % 10;
        const char *q = "  online_cpus=";
        memcpy(line + len, q, strlen(q)); len += strlen(q);
        if (n < 0) { line[len++] = '?'; }
        else { if (n >= 10) line[len++] = '0' + n / 10; line[len++] = '0' + n % 10; }
        line[len++] = '\n'; line[len] = 0;
        say(line);
        reap();
        scan_udcs();
        status(i);
        if (!selftest_done && access("/etc/ilinux/selftest", X_OK) == 0) {
            static char *const argv[] = { "/etc/ilinux/selftest", NULL };
            selftest_done = 1;
            selftest_pid = spawn(argv);
            sayf("[ctl] selftest started: pid %d\n", (int)selftest_pid);
        }
        sleep(5);
        if (i == 11) say("\n[diag] 60s elapsed; still alive. Observe the M5 framebuffer and the M1's bulk log reader.\n");
    }
    return 0;
}
#endif
