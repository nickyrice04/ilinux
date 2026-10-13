// diag-init.c - PID 1 for the t6050 RAM diagnostic initramfs.
// Non-interactive: mounts proc/sys/dev, prints the bring-up observables to the
// console (framebuffer) and /dev/kmsg, then heartbeats the online-CPU count so
// the screen keeps showing state. It writes nothing to any disk and never
// mounts storage. Build: gcc -static -O2 -o init diag-init.c
#include <fcntl.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <unistd.h>

static int con = 1;

static void outs(const char *s) { write(con, s, strlen(s)); }

static void kmsg(const char *s)
{
    int f = open("/dev/kmsg", O_WRONLY | O_CLOEXEC);
    if (f >= 0) { write(f, s, strlen(s)); close(f); }
}

static void say(const char *s) { outs(s); kmsg(s); }

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
        sleep(5);
        if (i == 11) say("\n[diag] 60s elapsed; still alive. Observe the M5 framebuffer; no native USB console is assumed.\n");
    }
    return 0;
}
