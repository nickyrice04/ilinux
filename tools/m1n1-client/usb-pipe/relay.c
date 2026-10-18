/* relay.c: the usb-pipe relay and its POSIX backends. See relay.h. */
#include "relay.h"

#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <pthread.h>
#include <signal.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

static long long now_ms(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec * 1000LL + t.tv_nsec / 1000000;
}

static void say(FILE *log, const char *fmt, ...)
{
    if (!log) return;
    va_list ap;
    va_start(ap, fmt);
    fputs("usb-pipe: ", log);
    vfprintf(log, fmt, ap);
    fputc('\n', log);
    fflush(log);
    va_end(ap);
}

const char *relay_end_name(enum relay_end end)
{
    switch (end) {
    case RELAY_END_STDIN_EOF: return "ssh closed the session";
    case RELAY_END_DEVICE_EOF: return "the device ended";
    case RELAY_END_DEVICE_ERROR: return "device error";
    case RELAY_END_STDOUT_ERROR: return "writing to ssh failed";
    case RELAY_END_NO_BANNER: return "no SSH banner from the device";
    }
    return "?";
}

ssize_t relay_find_banner(const unsigned char *buf, size_t len)
{
    ssize_t found = -1;
    for (size_t i = 0; i + 4 <= len; i++)
        if ((i == 0 || buf[i - 1] == '\n') && memcmp(buf + i, "SSH-", 4) == 0)
            found = (ssize_t)i;
    return found;
}

static int write_all(int fd, const unsigned char *buf, size_t len)
{
    while (len) {
        ssize_t n = write(fd, buf, len);
        if (n < 0) {
            if (errno == EINTR) continue;
            return -1;
        }
        buf += n;
        len -= (size_t)n;
    }
    return 0;
}

/* Before relaying: collect what the device sends until it has been quiet for quiet_ms after
 * a complete "SSH-" line, or until banner_wait_ms is up. Everything before the last such
 * line is stale (the end of an earlier session, banners of sshd instances that timed out
 * while no one was connected) and is dropped; the line and what follows go to ssh. ssh's own
 * banner waits in stdin meanwhile, so the M5's sshd sees it only once it is the live one. */
static int banner_sync(const struct pipe_ops *ops, int out_fd, const struct relay_options *opt,
                       struct relay_stats *st)
{
    enum { KEEP = 65536 };
    unsigned char *acc = malloc(KEEP), chunk[RELAY_CHUNK];
    size_t len = 0;
    long long start = now_ms(), deadline = start + opt->banner_wait_ms;
    if (!acc) {
        st->end = RELAY_END_STDOUT_ERROR;
        return -1;
    }
    for (;;) {
        long long left = deadline - now_ms();
        if (left <= 0) break;
        int wait = opt->quiet_ms > 0 && opt->quiet_ms < left ? opt->quiet_ms : (int)left;
        ssize_t n = ops->read(ops->ctx, chunk, sizeof chunk, wait < 1 ? 1 : wait);
        if (n > 0) {
            if (len + (size_t)n > KEEP) {   /* keep the newest KEEP bytes only (n <= RELAY_CHUNK < KEEP) */
                size_t drop = len + (size_t)n - KEEP;
                st->discarded += drop;
                memmove(acc, acc + drop, len - drop);
                len -= drop;
                memcpy(acc + len, chunk, (size_t)n);
                len += (size_t)n;
            } else {
                memcpy(acc + len, chunk, (size_t)n);
                len += (size_t)n;
            }
            continue;
        }
        if (n == RELAY_READ_TIMEOUT) {
            ssize_t at = relay_find_banner(acc, len);
            if (at >= 0 && memchr(acc + at, '\n', len - (size_t)at)) break;   /* quiet after a whole line */
            continue;
        }
        st->discarded += len;
        st->end = n == 0 || n == RELAY_READ_ABORTED ? RELAY_END_DEVICE_EOF : RELAY_END_DEVICE_ERROR;
        say(opt->log, "%s while waiting for the banner (%s); %zu stale bytes dropped",
            relay_end_name(st->end), n == RELAY_READ_ERROR ? ops->error(ops->ctx) : "end of data", len);
        free(acc);
        return -1;
    }
    ssize_t at = relay_find_banner(acc, len);
    if (at < 0) {
        st->discarded += len;
        st->end = RELAY_END_NO_BANNER;
        say(opt->log, "no SSH banner from the device in %d ms (%zu bytes received, dropped): is "
            "ilinux-sshd-tty running on the M5, or is an earlier session still closing (up to 45 s)?",
            opt->banner_wait_ms, len);
        free(acc);
        return -1;
    }
    st->discarded += (size_t)at;
    st->banner_ms = now_ms() - start;
    size_t line = (size_t)(len - at);
    const unsigned char *nl = memchr(acc + at, '\n', line);
    if (nl) line = (size_t)(nl - (acc + at));
    while (line && (acc[at + line - 1] == '\r')) line--;
    say(opt->log, "banner after %lld ms: %.*s (%llu stale bytes dropped first)", st->banner_ms,
        (int)(line > 80 ? 80 : line), (const char *)acc + at, st->discarded);
    if (write_all(out_fd, acc + at, len - (size_t)at)) {
        st->end = RELAY_END_STDOUT_ERROR;
        free(acc);
        return -1;
    }
    st->from_device += len - (size_t)at;
    free(acc);
    return 0;
}

/* ssh ends a session by writing its last packets (the channel close, the disconnect) into the
 * ProxyCommand's socket and then sending the ProxyCommand SIGHUP (ssh_kill_proxy_command). A bulk pipe has
 * no hang-up of its own, so those packets are the only thing that tells the M5's sshd the client is gone:
 * lose them and the server waits for a client that has left, until its keepalives give up (a minute) or,
 * before authentication, its login grace time. So once relaying, SIGHUP means nothing to this tool, and
 * neither does SIGPIPE: it goes on forwarding what ssh already wrote until stdin ends. (Measured: with the
 * default SIGHUP, a busy single CPU lost the tail of nearly every session.) */
static void survive_ssh_exit(void)
{
    signal(SIGHUP, SIG_IGN);
    signal(SIGPIPE, SIG_IGN);
}

struct relay_state {
    const struct pipe_ops *ops;
    int in_fd;
    struct relay_stats *st;
    pthread_mutex_t lock;
    int stdin_done, device_write_failed;
};

static void *stdin_thread(void *arg)
{
    struct relay_state *s = arg;
    unsigned char buf[RELAY_CHUNK];
    for (;;) {
        ssize_t n = read(s->in_fd, buf, sizeof buf);
        if (n < 0 && errno == EINTR) continue;
        pthread_mutex_lock(&s->lock);
        if (n <= 0) {
            s->stdin_done = 1;
            pthread_mutex_unlock(&s->lock);
            break;
        }
        pthread_mutex_unlock(&s->lock);
        if (s->ops->write(s->ops->ctx, buf, (size_t)n) != n) {
            pthread_mutex_lock(&s->lock);
            s->device_write_failed = 1;
            pthread_mutex_unlock(&s->lock);
            break;
        }
        pthread_mutex_lock(&s->lock);
        s->st->to_device += (unsigned long long)n;
        pthread_mutex_unlock(&s->lock);
    }
    s->ops->abort_read(s->ops->ctx);   /* ends the device read the main thread is blocked in */
    return NULL;
}

int relay_run(const struct pipe_ops *ops, int in_fd, int out_fd, const struct relay_options *opt,
              struct relay_stats *st)
{
    memset(st, 0, sizeof *st);
    st->banner_ms = -1;
    long long start = now_ms();
    if (opt->banner_wait_ms > 0 && banner_sync(ops, out_fd, opt, st) < 0)
        return st->end == RELAY_END_STDOUT_ERROR ? 1 : 5;
    survive_ssh_exit();
    struct relay_state s = { ops, in_fd, st, PTHREAD_MUTEX_INITIALIZER, 0, 0 };
    pthread_t thread;
    if (pthread_create(&thread, NULL, stdin_thread, &s)) {
        say(opt->log, "cannot start the stdin thread");
        st->end = RELAY_END_STDOUT_ERROR;
        return 1;
    }
    unsigned char buf[RELAY_CHUNK];
    int status = 0;
    for (;;) {
        ssize_t n = ops->read(ops->ctx, buf, sizeof buf, 0);
        if (n > 0) {
            if (write_all(out_fd, buf, (size_t)n)) {
                /* ssh has closed its side. What it wrote before it did is still in our stdin: let the
                 * stdin thread forward it (it ends when the pipe is empty), for at most two seconds. */
                st->end = RELAY_END_STDOUT_ERROR;
                status = 1;
                for (int waited = 0; waited < 200; waited++) {
                    pthread_mutex_lock(&s.lock);
                    int done = s.stdin_done || s.device_write_failed;
                    pthread_mutex_unlock(&s.lock);
                    if (done) break;
                    struct timespec ts = { 0, 10 * 1000 * 1000 };
                    nanosleep(&ts, NULL);
                }
                pthread_mutex_lock(&s.lock);
                if (s.stdin_done && !s.device_write_failed) {
                    st->end = RELAY_END_STDIN_EOF;   /* an ordinary end: ssh left, everything it wrote was sent */
                    status = 0;
                }
                pthread_mutex_unlock(&s.lock);
                break;
            }
            pthread_mutex_lock(&s.lock);
            st->from_device += (unsigned long long)n;
            pthread_mutex_unlock(&s.lock);
            continue;
        }
        if (n == RELAY_READ_TIMEOUT) continue;
        pthread_mutex_lock(&s.lock);
        int stdin_done = s.stdin_done, write_failed = s.device_write_failed;
        pthread_mutex_unlock(&s.lock);
        if (n == RELAY_READ_ABORTED && write_failed) {
            st->end = RELAY_END_DEVICE_ERROR;
            status = 5;
            say(opt->log, "write to the device failed: %s", ops->error(ops->ctx));
        } else if (n == RELAY_READ_ABORTED || (n == 0 && stdin_done)) {
            st->end = RELAY_END_STDIN_EOF;
        } else if (n == 0) {
            st->end = RELAY_END_DEVICE_EOF;
        } else {
            st->end = RELAY_END_DEVICE_ERROR;
            status = 5;
            say(opt->log, "read from the device failed: %s", ops->error(ops->ctx));
        }
        break;
    }
    /* After ssh closed stdin, or after a failed device write, the thread has ended. After a
     * device-side end it may still sit in read(2) on stdin; the process exits with it. */
    if (st->end == RELAY_END_STDIN_EOF || s.device_write_failed) pthread_join(thread, NULL);
    else pthread_detach(thread);   /* a device-side end: nothing is left to deliver to */
    say(opt->log, "end: %s; %llu bytes to the device, %llu from it, %llu stale dropped, %lld ms",
        relay_end_name(st->end), st->to_device, st->from_device, st->discarded, now_ms() - start);
    return status;
}

/* ---- POSIX backends ---------------------------------------------------------------- */

struct fd_pipe {
    int fd;
    int abort_pipe[2];
    char err[160];
};

static void fdp_set_error(struct fd_pipe *p, const char *what)
{
    snprintf(p->err, sizeof p->err, "%s: %s", what, strerror(errno));
}

static ssize_t fdp_read(void *ctx, void *buf, size_t len, int timeout_ms)
{
    struct fd_pipe *p = ctx;
    struct pollfd pfd[2] = { { p->fd, POLLIN, 0 }, { p->abort_pipe[0], POLLIN, 0 } };
    for (;;) {
        int r = poll(pfd, 2, timeout_ms > 0 ? timeout_ms : -1);
        if (r < 0) {
            if (errno == EINTR) continue;
            fdp_set_error(p, "poll");
            return RELAY_READ_ERROR;
        }
        if (r == 0) return RELAY_READ_TIMEOUT;
        if (pfd[1].revents) return RELAY_READ_ABORTED;   /* abort_read from the other thread */
        ssize_t n = read(p->fd, buf, len);
        if (n < 0) {
            if (errno == EINTR || errno == EAGAIN) continue;
            if (errno == EIO) return RELAY_READ_EOF;   /* a hung-up terminal */
            fdp_set_error(p, "read");
            return RELAY_READ_ERROR;
        }
        return n;
    }
}

static ssize_t fdp_write(void *ctx, const void *buf, size_t len)
{
    struct fd_pipe *p = ctx;
    const unsigned char *b = buf;
    size_t done = 0;
    while (done < len) {
        ssize_t n = write(p->fd, b + done, len - done);
        if (n < 0) {
            if (errno == EINTR) continue;
            if (errno == EAGAIN) {
                struct pollfd pfd = { p->fd, POLLOUT, 0 };
                poll(&pfd, 1, 10000);
                continue;
            }
            fdp_set_error(p, "write");
            return -1;
        }
        done += (size_t)n;
    }
    return (ssize_t)len;
}

static void fdp_abort(void *ctx)
{
    struct fd_pipe *p = ctx;
    ssize_t n = write(p->abort_pipe[1], "x", 1);
    (void)n;
}

static const char *fdp_error(void *ctx)
{
    return ((struct fd_pipe *)ctx)->err;
}

static const struct pipe_ops fdp_template = { NULL, fdp_read, fdp_write, fdp_abort, fdp_error };

struct fd_pipe_with_ops {
    struct fd_pipe p;
    struct pipe_ops ops;
};

struct fd_pipe *fd_pipe_open_fd(int fd)
{
    struct fd_pipe_with_ops *w = calloc(1, sizeof *w);
    if (!w) return NULL;
    w->p.fd = fd;
    if (pipe(w->p.abort_pipe)) {
        free(w);
        return NULL;
    }
    fcntl(w->p.abort_pipe[0], F_SETFD, FD_CLOEXEC);
    fcntl(w->p.abort_pipe[1], F_SETFD, FD_CLOEXEC);
    w->ops = fdp_template;
    w->ops.ctx = &w->p;
    return &w->p;
}

struct fd_pipe *fd_pipe_open_tty(const char *path)
{
    int fd = open(path, O_RDWR | O_NOCTTY | O_CLOEXEC);
    if (fd < 0) return NULL;
    struct termios t;
    if (tcgetattr(fd, &t) == 0) {   /* a serial device: raw, 8N1, no flow control, no echo */
        cfmakeraw(&t);
        t.c_cflag |= CLOCAL | CREAD;
        t.c_cflag &= ~(tcflag_t)CRTSCTS;
        t.c_cc[VMIN] = 1;
        t.c_cc[VTIME] = 0;
        cfsetispeed(&t, B115200);   /* meaningless on a USB port; set for completeness */
        cfsetospeed(&t, B115200);
        if (tcsetattr(fd, TCSANOW, &t)) {
            close(fd);
            return NULL;
        }
    }
    struct fd_pipe *p = fd_pipe_open_fd(fd);
    if (!p) close(fd);
    return p;
}

const struct pipe_ops *fd_pipe_ops(struct fd_pipe *p)
{
    return &((struct fd_pipe_with_ops *)p)->ops;
}

void fd_pipe_close(struct fd_pipe *p)
{
    tcdrain(p->fd);   /* a serial port discards what it has not sent when it is closed; ENOTTY on a socket is fine */
    close(p->fd);
    close(p->abort_pipe[0]);
    close(p->abort_pipe[1]);
    free(p);
}
