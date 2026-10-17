// diag-init.c (boot039) - PID 1 for the t6050 RAM initramfs, with a USB log channel.
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
// It writes nothing to any disk and never mounts storage.
// Build: gcc -static -O2 -o init diag-init.c
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <net/if.h>
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
// usb-drd0..2 (ports 1..3) by their dwc3 node; any other UDC (VM tests) gets 4+.
static const char *const known_udc[] = { "2a2280000.usb", "2aa280000.usb", "382280000.usb" };

// Log stream counters, in memory shared with the streamer child (it writes, /init reads).
struct stream_stats {
    unsigned long records, bytes;  // records copied, bytes accepted by the tty
    int queued;                    // bytes still in the M5's 8 KiB serial FIFO (TIOCOUTQ)
    int info_done;                 // the one-time dwc3 line for this port was printed
};

struct port {
    char udc[64];
    char tty[32];   // the gser serial port on this side, /dev/ttyGSn
    int index;      // 1..9: port number in the strings
    int bound;
    pid_t streamer; // child that copies /dev/kmsg to the serial port
    int streamer_starts;
    struct stream_stats *st;
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
}

static int port_index(const char *udc)
{
    for (unsigned i = 0; i < sizeof known_udc / sizeof *known_udc; i++)
        if (!strcmp(udc, known_udc[i])) return i + 1;
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
                    sayf("[ctl] log streamer for port %d exited (status 0x%x); restarting\n",
                         ports[i].index, st);
                    ports[i].streamer = -1;
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

// Interrupt count of the "dwc3" action whose hwirq matches this UDC's DT interrupt.
static long irq_count(const char *udc)
{
    char path[320], text[256];
    unsigned char cells[12];
    snprintf(path, sizeof path, SYSROOT "/sys/class/udc/%.63s/device/of_node/interrupts", udc);
    int f = open(path, O_RDONLY | O_CLOEXEC);
    if (f < 0) return -1;
    ssize_t n = read(f, cells, sizeof cells);
    close(f);
    if (n != 12) return -1;
    unsigned long want = (unsigned long)cells[4] << 24 | cells[5] << 16 | cells[6] << 8 | cells[7];
    DIR *d = opendir(SYSROOT "/sys/kernel/irq");
    if (!d) return -1;
    long total = -1;
    struct dirent *e;
    while (total < 0 && (e = readdir(d))) {
        if (e->d_name[0] == '.') continue;
        snprintf(path, sizeof path, SYSROOT "/sys/kernel/irq/%s/actions", e->d_name);
        if (strcmp(get(path, text, sizeof text), "dwc3")) continue;
        snprintf(path, sizeof path, SYSROOT "/sys/kernel/irq/%s/hwirq", e->d_name);
        if ((strtoul(get(path, text, sizeof text), 0, 10) & 0xffff) != want) continue;
        snprintf(path, sizeof path, SYSROOT "/sys/kernel/irq/%s/per_cpu_count", e->d_name);
        get(path, text, sizeof text);
        total = 0;
        for (char *s = text; *s; s++) {
            total += strtol(s, &s, 10);
            if (*s != ',') break;
        }
    }
    closedir(d);
    return total;
}

// Compact state of one dwc3 controller for the status line. If info is given, it also
// gets the controller's endpoint count and FIFO sizes (static after the core's init).
static void dwc3_state(const char *udc, struct buf *b, struct buf *info)
{
    static char dump[32768];
    char dir[192], path[256], link[64], type[32];
    snprintf(dir, sizeof dir, SYSROOT DEBUG_USB "/%.63s", udc);
    snprintf(path, sizeof path, "%s/regdump", dir);
    if (slurp(path, dump, sizeof dump) <= 0) {
        add(b, " dwc3 n/a");
        return;
    }
    snprintf(path, sizeof path, "%s/link_state", dir);
    get(path, link, sizeof link);
    unsigned gsts = 0, dctl = 0, dsts = 0, evcount = 0, alepena = 0, cmd0 = 0, cmd1 = 0;
    reg(dump, "GSTS", &gsts);
    reg(dump, "DCTL", &dctl);
    reg(dump, "DSTS", &dsts);
    reg(dump, "GEVNTCOUNT(0)", &evcount);
    reg(dump, "DALEPENA", &alepena);
    reg(dump, "DEPCMD(0)", &cmd0);
    reg(dump, "DEPCMD(1)", &cmd1);
    add(b, " dwc3 %s f%u ev%u", link[0] ? link : "?", (dsts >> 3) & 0x3fff, evcount & 0xfffc);
    if (!(dctl & (1u << 31))) add(b, " STOPPED");          // DCTL.RUN_STOP clear
    if (dsts & (1u << 22)) add(b, " HALTED");              // DSTS.DEVCTRLHLT
    if (gsts & (1u << 4)) add(b, " BUSERR");               // GSTS.BUS_ERR_ADDR_VLD
    if (gsts & (1u << 5)) add(b, " CSR-TIMEOUT");          // GSTS.CSR_TIMEOUT
    if (evcount & (1u << 31)) add(b, " EVBUSY");           // GEVNTCOUNT.EVNT_HANDLER_BUSY
    long irqs = irq_count(udc);
    if (irqs >= 0) add(b, " irq%ld", irqs);
    else add(b, " irq?");
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

// The status line: per port, the UDC state, the log stream's counters (records,
// bytes accepted, bytes still queued in the M5's FIFO) and, with with_dwc3, the
// controller state; pre gets the one-time controller lines that come before it.
static void build_status(struct buf *line, struct buf *pre, int with_dwc3)
{
    char state[64], path[160], text[256];
    add(line, "[ctl] %s", nports ? "" : "no UDC");
    for (int i = 0; i < nports; i++) {
        struct port *p = &ports[i];
        snprintf(path, sizeof path, SYSROOT "/sys/class/udc/%.63s/state", p->udc);
        get(path, state, sizeof state);
        add(line, "%sport%d %s", i ? " | " : "", p->index, state[0] ? state : "?");
        if (!p->bound) add(line, " unbound");
        else if (!p->tty[0]) add(line, " no-tty");
        else add(line, " log %luL %luB q%d", p->st->records, p->st->bytes, p->st->queued);
        if (!with_dwc3) continue;
        struct buf info = { text, sizeof text, 0 };
        text[0] = 0;
        dwc3_state(p->udc, line, p->st->info_done ? NULL : &info);
        if (info.len) {
            add(pre, "[ctl] port%d dwc3: %s\n", p->index, text);
            p->st->info_done = 1;
        }
    }
}

static void status_line(int with_dwc3)
{
    char line[1000], pre[1024];
    struct buf b = { line, sizeof line - 1, 0 }, p = { pre, sizeof pre, 0 };   // room for '\n'
    line[0] = pre[0] = 0;
    build_status(&b, &p, with_dwc3);
    line[b.len++] = '\n';
    line[b.len] = 0;
    for (char *s = pre, *nl; *s && (nl = strchr(s, '\n')); s = nl + 1) {   // one kmsg record each
        char c = nl[1];
        nl[1] = 0;
        say(s);
        nl[1] = c;
    }
    say(line);
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
        "no network\n");
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
