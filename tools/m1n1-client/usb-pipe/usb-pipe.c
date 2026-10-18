/* usb-pipe: ssh's ProxyCommand for the M5's USB byte pipe.
 *
 * The M5's RAM root presents, per USB-C port, one gadget (1d6b:0104, bcdDevice 0x0039) with
 * two bulk-only vendor-class interfaces: 0 carries the journal, 1 is a raw byte pipe on which
 * sshd runs in inetd mode. No macOS driver binds either. This tool opens interface 1 from user
 * space (IOUSBHost, the macOS SDK only), relays ssh's stdin to the bulk-OUT endpoint and the
 * bulk-IN endpoint to ssh's stdout, and exits when ssh closes or the device goes away. Before
 * relaying it waits for the M5 sshd's "SSH-" banner line and drops anything stale in front of
 * it (bulk endpoints keep what an earlier session left), so ssh sees exactly one banner.
 *
 *   ssh -F tools/m1n1-client/m5-ssh-config m5        (from the repository root on the M1)
 *
 * Only the matched interface is opened: never the device, never interface 0 (the bulk-log
 * reader's), never with the capture or seize options. No control request, alternate setting,
 * stall clearing, reset or power change: the source and tools/m1n1-client/test_usb_pipe.py's
 * static check keep it that way. The relay and the banner logic (relay.c) also run on Linux,
 * where the VM self-test drives them against the real gadget function through /dev/ttyUSB1
 * (--tty); --fd is for the offline tests. Build on macOS: tools/m1n1-client/usb-pipe/build.sh. */
#include "relay.h"
#include "usb-pipe.h"

#include <errno.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void usage(FILE *f)
{
    fputs("usage: usb-pipe [--port N] [--wait S] [--banner-wait S] [--quiet-ms MS]\n"
          "                [--write-timeout S] [--log FILE] [--dry-run]\n"
          "       usb-pipe --tty PATH | --fd N [relay options]      (test backends)\n"
          "  --port N           the M5 USB-C port named in the product string (1-3); default: the only match\n"
          "  --wait S           wait up to S seconds for the device (default 60)\n"
          "  --banner-wait S    wait up to S seconds for the M5 sshd's banner (default 20; 0 relays at once)\n"
          "  --quiet-ms MS      drop stale bytes before the banner after MS of silence (default 400)\n"
          "  --write-timeout S  a write the M5 does not take within S seconds ends the session (default 10)\n"
          "  --log FILE         append the event lines to FILE instead of stderr\n"
          "  --dry-run          find and check the device, print it, open nothing\n"
          "  --tty PATH         relay to a serial device opened raw instead of USB (Linux stand-in)\n"
          "  --fd N             relay to an inherited descriptor instead of USB (offline tests)\n"
          "exit: 0 session ended; 1 ssh side failed; 2 no device; 3 open refused; 4 wrong or ambiguous\n"
          "      device; 5 device failed or no banner; 6 bad usage\n", f);
}

static int number(const char *s, long min, long max, long *out)
{
    char *end;
    errno = 0;
    long v = strtol(s, &end, 10);
    if (errno || end == s || *end || v < min || v > max) return -1;
    *out = v;
    return 0;
}

int main(int argc, char **argv)
{
    struct usb_pipe_options o = { 0, 60, 20000, 400, 10, 0 };
    const char *log_path = NULL, *tty = NULL;
    long fd = -1, v;
    for (int i = 1; i < argc; i++) {
        const char *a = argv[i];
        const char *arg = i + 1 < argc ? argv[i + 1] : NULL;
        if (!strcmp(a, "--help") || !strcmp(a, "-h")) {
            usage(stdout);
            return 0;
        } else if (!strcmp(a, "--version")) {
            printf("usb-pipe %s\n", USB_PIPE_VERSION);
            return 0;
        } else if (!strcmp(a, "--dry-run")) {
            o.dry_run = 1;
        } else if (!arg) {
            fprintf(stderr, "usb-pipe: %s needs a value\n", a);
            return USB_PIPE_EXIT_USAGE;
        } else if (!strcmp(a, "--port") && !number(arg, 1, 3, &v)) {
            o.port = (int)v;
            i++;
        } else if (!strcmp(a, "--wait") && !number(arg, 0, 3600, &v)) {
            o.wait_s = (int)v;
            i++;
        } else if (!strcmp(a, "--banner-wait") && !number(arg, 0, 600, &v)) {
            o.banner_wait_ms = (int)v * 1000;
            i++;
        } else if (!strcmp(a, "--quiet-ms") && !number(arg, 1, 10000, &v)) {
            o.quiet_ms = (int)v;
            i++;
        } else if (!strcmp(a, "--write-timeout") && !number(arg, 1, 600, &v)) {
            o.write_timeout_s = (int)v;
            i++;
        } else if (!strcmp(a, "--log")) {
            log_path = arg;
            i++;
        } else if (!strcmp(a, "--tty")) {
            tty = arg;
            i++;
        } else if (!strcmp(a, "--fd") && !number(arg, 0, INT_MAX, &fd)) {
            i++;
        } else {
            fprintf(stderr, "usb-pipe: bad option or value: %s %s\n", a, arg);
            usage(stderr);
            return USB_PIPE_EXIT_USAGE;
        }
    }
    if (tty && fd >= 0) {
        fprintf(stderr, "usb-pipe: --tty and --fd exclude each other\n");
        return USB_PIPE_EXIT_USAGE;
    }
    FILE *log = stderr;
    if (log_path) {   /* ssh shows stderr to the user, so a log that cannot be opened is not fatal */
        log = fopen(log_path, "a");
        if (!log) {
            fprintf(stderr, "usb-pipe: cannot open the log %s (%s); logging to stderr\n", log_path, strerror(errno));
            log = stderr;
        }
    }
    if (tty || fd >= 0) {
        struct fd_pipe *p = tty ? fd_pipe_open_tty(tty) : fd_pipe_open_fd((int)fd);
        if (!p) {
            fprintf(log, "usb-pipe: cannot open %s: %s\n", tty ? tty : "the descriptor", strerror(errno));
            return USB_PIPE_EXIT_USAGE;
        }
        fprintf(log, "usb-pipe: test backend %s%s\n", tty ? "tty " : "fd ", tty ? tty : argv[argc - 1]);
        struct relay_options ro = { o.banner_wait_ms, o.quiet_ms, log };
        struct relay_stats st;
        int rc = relay_run(fd_pipe_ops(p), STDIN_FILENO, STDOUT_FILENO, &ro, &st);
        fd_pipe_close(p);
        return rc;
    }
    return usb_pipe_backend_main(&o, log);
}

#ifndef __APPLE__
int usb_pipe_backend_main(const struct usb_pipe_options *o, FILE *log)
{
    (void)o;
    fprintf(log, "usb-pipe: the USB backend (IOUSBHost) exists on macOS only; use --tty or --fd here\n");
    return USB_PIPE_EXIT_USAGE;
}
#endif
