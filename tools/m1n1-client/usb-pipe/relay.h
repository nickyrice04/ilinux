/* relay.h: the byte-pipe relay that usb-pipe runs between ssh (stdin/stdout) and the M5's
 * SSH interface. The device behind it is one of three backends with the same contract:
 * IOUSBHost on macOS (iousbhost.m: the bulk-IN and bulk-OUT pipes of interface 1 of the
 * M5's gadget), a serial device opened raw (the Linux stand-in in the VM self-test reads
 * /dev/ttyUSB1, the generic usb-serial driver's view of the same interface), or an inherited
 * descriptor (the offline tests: a socket or a pseudo-terminal). The relay, the banner sync
 * and the exit rules are the same code on every platform, so what the VM proves against the
 * real gadget function and what the offline tests prove on the Mac is what runs on the M1. */
#ifndef USB_PIPE_RELAY_H
#define USB_PIPE_RELAY_H
#include <stddef.h>
#include <stdio.h>
#include <sys/types.h>

#define RELAY_CHUNK 16384   /* one bulk transfer at most: a multiple of the 512-byte packet */

enum { RELAY_READ_EOF = 0, RELAY_READ_ERROR = -1, RELAY_READ_TIMEOUT = -2, RELAY_READ_ABORTED = -3 };

struct pipe_ops {
    void *ctx;
    /* Read at most len bytes. Blocks until at least one byte arrived (returns the count), the
     * device ended (0), an error (-1), with timeout_ms > 0 the timeout (-2), or abort_read
     * was called (-3). A timeout loses nothing: bytes that arrived before it are returned as
     * a count instead. */
    ssize_t (*read)(void *ctx, void *buf, size_t len, int timeout_ms);
    /* Write all len bytes; returns len, or -1. */
    ssize_t (*write)(void *ctx, const void *buf, size_t len);
    /* Make a read blocked in another thread return promptly, with -3. */
    void (*abort_read)(void *ctx);
    /* A short description of the last read or write error, for the log. */
    const char *(*error)(void *ctx);
};

struct relay_options {
    int banner_wait_ms;   /* > 0: wait this long for the M5 sshd's "SSH-" line before relaying */
    int quiet_ms;         /* stale bytes before that line are dropped once the device has been
                             quiet this long; the line itself and everything after it go to ssh */
    FILE *log;            /* one line per event, or NULL */
};

enum relay_end {
    RELAY_END_STDIN_EOF,      /* ssh closed its side: the normal end of a session */
    RELAY_END_DEVICE_EOF,     /* the device ended: unplugged, terminated, or the test end closed */
    RELAY_END_DEVICE_ERROR,   /* a read or write on the device failed */
    RELAY_END_STDOUT_ERROR,   /* writing to ssh failed */
    RELAY_END_NO_BANNER,      /* no "SSH-" line from the device within banner_wait_ms */
};

struct relay_stats {
    unsigned long long to_device, from_device, discarded;
    long long banner_ms;      /* when the banner was seen, ms after the start; -1 if never */
    enum relay_end end;
};

/* Offset of the last line in buf that starts with "SSH-" (at offset 0 or after '\n'), or -1. */
ssize_t relay_find_banner(const unsigned char *buf, size_t len);

/* Relay between in_fd/out_fd (ssh) and the device until one side ends. Returns the process
 * exit status: 0 for a normal end (ssh closed, or the device ended), 5 for a device failure or
 * a missing banner, 1 when writing to ssh failed. */
int relay_run(const struct pipe_ops *ops, int in_fd, int out_fd, const struct relay_options *opt,
              struct relay_stats *stats);

const char *relay_end_name(enum relay_end end);

/* POSIX backends for the tests and the Linux stand-in: an inherited bidirectional descriptor
 * (socket, pseudo-terminal master) or a serial device opened raw (O_RDWR | O_NOCTTY). */
struct fd_pipe;
struct fd_pipe *fd_pipe_open_fd(int fd);               /* takes ownership of fd */
struct fd_pipe *fd_pipe_open_tty(const char *path);
const struct pipe_ops *fd_pipe_ops(struct fd_pipe *p);
void fd_pipe_close(struct fd_pipe *p);

#endif
