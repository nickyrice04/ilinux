// diag-init.c (boot038) - PID 1 for the t6050 RAM initramfs, with a USB control channel.
// Source: kernel/experiments/usb-gadget/init.c; packaged as diag-init.c.
// Keeps everything boot021-035's diag-init did: mounts proc/sys/dev, prints the
// bring-up observables to the console (framebuffer) and /dev/kmsg, heartbeats
// the online-CPU count. New in boot036, revised in boot038:
//  * one configfs gadget per UDC with two functions in one configuration:
//    CDC-ACM (a serial port that carries the kernel log, read-only from the
//    host side: this init only writes to it) and CDC-ECM (network). boot036
//    used CDC-EEM, which macOS 26.0.1 on the controller cannot bind. VID:PID
//    1d6b:0104, fixed locally administered MACs 02:69:6c:69:6e:0N, so the
//    Linux end of port N is fe80::69:6cff:fe69:6e0N (N = 1..3 for usb-drd0..2);
//  * the interface brought up: IPv6 link-local only, no IPv4, no routes;
//  * dropbear on port 22: root, key only (/root/.ssh/authorized_keys), no
//    password logins, no forwarding, host keys generated in RAM on first use,
//    restarted if it exits;
//  * one status line per heartbeat: UDC state, link, packet counters, address;
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
#include <sys/mount.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/wait.h>
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
#define MAX_UDC 8
// usb-drd0..2 (ports 1..3) by their dwc3 node; any other UDC (VM tests) gets 4+.
static const char *const known_udc[] = { "2a2280000.usb", "2aa280000.usb", "382280000.usb" };

struct port {
    char udc[64];
    char ifname[IFNAMSIZ];
    char tty[32];   // the ACM serial port on this side, /dev/ttyGSn
    int index;      // 1..9: MAC suffix and link-local address
    int bound;
    pid_t streamer; // child that copies /dev/kmsg to the serial port
    int streamer_starts;
};
static struct port ports[MAX_UDC];
static int nports;
static pid_t dropbear_pid = -1, selftest_pid = -1;
static int dropbear_starts, selftest_done;

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

// Copy the kernel log to the ACM serial port, record by record, as "[sec.usec] text".
// Runs in a child. A full 8 KiB u_serial FIFO (host not reading yet) makes write()
// return 0 or EAGAIN; the child then waits and retries the same record, so nothing
// is dropped while the kernel's log buffer still holds it.
static void stream_kmsg(const char *tty)
{
    int in = open("/dev/kmsg", O_RDONLY | O_CLOEXEC);
    int out = open(tty, O_WRONLY | O_NOCTTY | O_NONBLOCK | O_CLOEXEC);
    if (in < 0 || out < 0) _exit(1);
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
        for (int off = 0; off < len;) {
            ssize_t w = write(out, line + off, len - off);
            if (w > 0) { off += w; continue; }
            if (w < 0 && errno != EAGAIN && errno != EINTR) _exit(3);
            usleep(100000);
        }
    }
}

static pid_t spawn_stream(const char *tty)
{
    pid_t pid = fork();
    if (pid == 0) {
        setsid();
        stream_kmsg(tty);
        _exit(0);
    }
    return pid;
}

static void start_streamer(struct port *p)
{
    if (!p->tty[0] || p->streamer_starts >= 20) return;
    p->streamer_starts++;
    p->streamer = spawn_stream(p->tty);
}

// One ACM + ECM gadget on one UDC. Each step is reported, so the screen names a failure.
static void setup_port(struct port *p)
{
    char g[16], v[64];
    snprintf(g, sizeof g, "g%d", p->index);
    if (gadget_mkdir(g, "")) return;
    gadget_put(g, "idVendor", "0x1d6b");        // Linux Foundation
    gadget_put(g, "idProduct", "0x0104");       // Multifunction Composite Gadget
    gadget_put(g, "bcdDevice", "0x0038");
    gadget_put(g, "bcdUSB", "0x0200");
    if (gadget_mkdir(g, "strings/0x409")) return;
    gadget_put(g, "strings/0x409/manufacturer", "iLinux");
    snprintf(v, sizeof v, "iLinux J716c control channel, port %d", p->index);
    gadget_put(g, "strings/0x409/product", v);
    snprintf(v, sizeof v, "ilinux-port%d", p->index);   // not a hardware serial
    gadget_put(g, "strings/0x409/serialnumber", v);
    // ACM first (interfaces 0-1), then ECM (2-3): the link order sets the interface order.
    if (gadget_mkdir(g, "functions/acm.GS0") || gadget_mkdir(g, "functions/ecm.usb")) return;
    snprintf(v, sizeof v, "02:69:6c:69:6e:%02x", p->index);
    gadget_put(g, "functions/ecm.usb/dev_addr", v);
    snprintf(v, sizeof v, "02:69:6c:69:6f:%02x", p->index);
    gadget_put(g, "functions/ecm.usb/host_addr", v);
    if (gadget_mkdir(g, "configs/c.1") || gadget_mkdir(g, "configs/c.1/strings/0x409")) return;
    gadget_put(g, "configs/c.1/strings/0x409/configuration", "CDC ACM log port + CDC ECM network");
    char from[256], to[256];
    static const char *const functions[] = { "acm.GS0", "ecm.usb" };
    for (unsigned i = 0; i < 2; i++) {
        snprintf(from, sizeof from, GADGETS "/%s/functions/%s", g, functions[i]);
        snprintf(to, sizeof to, GADGETS "/%s/configs/c.1/%s", g, functions[i]);
        if (symlink(from, to) && errno != EEXIST) {
            sayf("[ctl] link %s failed: %s\n", to, strerror(errno));
            return;
        }
    }
    if (gadget_put(g, "UDC", p->udc)) return;
    p->bound = 1;
    snprintf(from, sizeof from, GADGETS "/%s/functions/ecm.usb/ifname", g);
    get(from, p->ifname, sizeof p->ifname);
    char num[16];
    snprintf(from, sizeof from, GADGETS "/%s/functions/acm.GS0/port_num", g);
    get(from, num, sizeof num);
    if (num[0]) snprintf(p->tty, sizeof p->tty, "/dev/ttyGS%s", num);
    int err = p->ifname[0] ? set_up(p->ifname) : -ENODEV;
    start_streamer(p);
    sayf("[ctl] port %d: UDC %s bound, ACM+ECM 1d6b:0104, interface %s %s, log on %s; "
         "Linux end fe80::69:6cff:fe69:6e%02x%%<if>\n", p->index, p->udc,
         p->ifname[0] ? p->ifname : "?", err ? strerror(-err) : "up",
         p->tty[0] ? p->tty + 5 : "no tty", p->index);
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
            struct port *p = &ports[nports++];
            memset(p, 0, sizeof *p);
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

// Link-local address of an interface from /proc/net/if_inet6 (IFA_F_TENTATIVE 0x40 =
// duplicate address detection running, IFA_F_DADFAILED 0x08 = address unusable).
static const char *ll_addr(const char *ifname, char *out, size_t size)
{
    char line[256], hex[33], name[IFNAMSIZ + 1];
    unsigned idx, plen, scope, flags;
    snprintf(out, size, "no-ll");
    FILE *f = fopen("/proc/net/if_inet6", "re");
    if (!f) return out;
    while (fgets(line, sizeof line, f))
        if (sscanf(line, "%32s %x %x %x %x %16s", hex, &idx, &plen, &scope, &flags, name) == 6 &&
            !strcmp(name, ifname) && !strncmp(hex, "fe80", 4)) {
            snprintf(out, size, "fe80::%.4s:%.4s:%.4s:%.4s%s", hex + 16, hex + 20, hex + 24,
                     hex + 28, flags & 0x08 ? "(dadfailed)" : flags & 0x40 ? "(tentative)" : "");
            break;
        }
    fclose(f);
    return out;
}

static void status_line(void)
{
    char line[1024], state[64], oper[32], rx[32], tx[32], ll[64], path[160];
    int len = snprintf(line, sizeof line, "[ctl] %s", nports ? "" : "no UDC");
    for (int i = 0; i < nports && len < (int)sizeof line - 1; i++) {
        struct port *p = &ports[i];
        snprintf(path, sizeof path, "/sys/class/udc/%s/state", p->udc);
        get(path, state, sizeof state);
        if (!p->bound || !p->ifname[0]) {
            len += snprintf(line + len, sizeof line - len, "%sport%d %s %s", i ? " | " : "",
                            p->index, state[0] ? state : "?", p->bound ? "no-if" : "unbound");
            continue;
        }
        snprintf(path, sizeof path, "/sys/class/net/%s/operstate", p->ifname);
        get(path, oper, sizeof oper);
        snprintf(path, sizeof path, "/sys/class/net/%s/statistics/rx_packets", p->ifname);
        get(path, rx, sizeof rx);
        snprintf(path, sizeof path, "/sys/class/net/%s/statistics/tx_packets", p->ifname);
        get(path, tx, sizeof tx);
        len += snprintf(line + len, sizeof line - len, "%sport%d %s %s %s rx=%s tx=%s %s",
                        i ? " | " : "", p->index, state[0] ? state : "?", p->ifname, oper,
                        rx, tx, ll_addr(p->ifname, ll, sizeof ll));
    }
    if (len > (int)sizeof line - 2) len = sizeof line - 2;
    line[len++] = '\n';
    line[len] = 0;
    say(line);
}

static void control_channel_init(void)
{
    mkdir("/dev/pts", 0755);
    if (mount("devpts", "/dev/pts", "devpts", MS_NOSUID | MS_NOEXEC, "mode=620,ptmxmode=666"))
        sayf("[ctl] devpts mount failed: %s\n", strerror(errno));
    if (mount("configfs", "/sys/kernel/config", "configfs", 0, 0))
        sayf("[ctl] configfs mount failed: %s\n", strerror(errno));
    sethostname("ilinux-j716c", 12);
    setenv("PATH", "/usr/bin:/usr/sbin:/bin:/sbin", 1);
    setenv("HOME", "/root", 1);
    setenv("TERM", "linux", 1);
    int err = set_up("lo");
    if (err) sayf("[ctl] lo up failed: %s\n", strerror(-err));
    say("\n[ctl] USB control channel: CDC-ACM log port + CDC-ECM per UDC, IPv6 link-local, SSH key only\n");
    for (int i = 0; i < 40 && !nports; i++) {   // up to 10 s for the first UDC
        scan_udcs();
        if (!nports) usleep(250000);
    }
    if (!nports) say("[ctl] no UDC yet (dwc3 not probed); rescanning every heartbeat\n");
    start_dropbear();
}

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
        status_line();
        if (!selftest_done && access("/etc/ilinux/selftest", X_OK) == 0) {
            static char *const argv[] = { "/etc/ilinux/selftest", NULL };
            selftest_done = 1;
            selftest_pid = spawn(argv);
            sayf("[ctl] selftest started: pid %d\n", (int)selftest_pid);
        }
        sleep(5);
        if (i == 11) say("\n[diag] 60s elapsed; still alive. Observe the M5 framebuffer and the M1's new USB network interface.\n");
    }
    return 0;
}
