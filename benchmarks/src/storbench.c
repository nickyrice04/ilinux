// storbench.c - portable storage benchmark (macOS F_NOCACHE / Linux O_DIRECT).
//   cc -O2 -pthread storbench.c -o storbench
//
// Usage:
//   storbench seqwrite  FILE -m MiB [-b KiB]           sequential write + full flush
//   storbench seqread   FILE [-b KiB] [-t threads]     sequential read, cache bypassed
//   storbench randread  FILE [-b KiB] [-t threads] [-s secs]
//   storbench randwrite FILE [-b KiB] [-t threads] [-s secs]   (overwrites FILE)
//   storbench syncwrite FILE [-b KiB] [-t threads] [-s secs]   (overwrites FILE)
//       random writes, each followed by fsync (fdatasync on Linux): the
//       durability cost apps such as package managers, git and browsers pay
//
// Each thread issues synchronous I/O, so -t approximates queue depth.
// The page/buffer cache is bypassed on both OSes; data written is random
// (incompressible).  Only FILE is touched.

#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

static double now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}
static int cmpd(const void *a, const void *b) {
    double x = *(const double *)a, y = *(const double *)b;
    return x < y ? -1 : x > y;
}

static int open_nocache(const char *path, int flags) {
#ifdef __APPLE__
    int fd = open(path, flags, 0644);
    if (fd >= 0) fcntl(fd, F_NOCACHE, 1);
#else
    int fd = open(path, flags | O_DIRECT, 0644);
#endif
    if (fd < 0) { perror(path); exit(1); }
    return fd;
}
static void full_flush(int fd) {
#ifdef __APPLE__
    if (fcntl(fd, F_FULLFSYNC) != 0) fsync(fd);
#else
    fsync(fd);
#endif
}
static void *xalloc(size_t n) {
    void *p = NULL;
    if (posix_memalign(&p, 16384, n)) { perror("posix_memalign"); exit(1); }
    return p;
}
static void fill_random(unsigned char *b, size_t n, uint64_t seed) {
    for (size_t i = 0; i + 8 <= n; i += 8) {
        seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17;
        memcpy(b + i, &seed, 8);
    }
}

struct job {
    const char *path;
    int write;          // 0 read, 1 write
    int random;
    int sync_each;      // fsync after every write (syncwrite)
    size_t bs;
    off_t lo, hi;       // region for sequential jobs; file size for random
    double secs;
    uint64_t seed;
    // results
    uint64_t ops, bytes;
    double *lat;        // per-op latency samples (random only)
    size_t nlat, caplat;
    double t0, t1;
};

static void *io_worker(void *p) {
    struct job *j = p;
    int fd = open_nocache(j->path, j->write ? O_RDWR : O_RDONLY);
    unsigned char *buf = xalloc(j->bs);
    fill_random(buf, j->bs, j->seed | 1);
    j->t0 = now();
    if (!j->random) {
        for (off_t off = j->lo; off < j->hi; off += j->bs) {
            ssize_t r = j->write ? pwrite(fd, buf, j->bs, off) : pread(fd, buf, j->bs, off);
            if (r <= 0) { perror("io"); break; }
            j->ops++; j->bytes += r;
        }
    } else {
        uint64_t s = j->seed | 1, nblk = (uint64_t)(j->hi / j->bs);
        double end = j->t0 + j->secs;
        for (;;) {
            s ^= s << 13; s ^= s >> 7; s ^= s << 17;
            off_t off = (off_t)(s % nblk) * j->bs;
            double a = now();
            if (a >= end) break;
            ssize_t r = j->write ? pwrite(fd, buf, j->bs, off) : pread(fd, buf, j->bs, off);
            if (r > 0 && j->sync_each) {
#ifdef __APPLE__
                fsync(fd);
#else
                fdatasync(fd);
#endif
            }
            double b = now();
            if (r <= 0) { perror("io"); break; }
            j->ops++; j->bytes += r;
            if (j->nlat == j->caplat) {
                j->caplat = j->caplat ? j->caplat * 2 : 65536;
                j->lat = realloc(j->lat, j->caplat * sizeof(double));
            }
            j->lat[j->nlat++] = (b - a) * 1e6;
        }
    }
    if (j->write) full_flush(fd);
    j->t1 = now();
    close(fd);
    free(buf);
    return NULL;
}

static off_t file_size(const char *path) {
    struct stat st;
    if (stat(path, &st)) { perror(path); exit(1); }
    return st.st_size;
}

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr, "usage: %s seqwrite|seqread|randread|randwrite|syncwrite FILE [-m MiB] [-b KiB] "
                        "[-t threads] [-s secs]\n", argv[0]);
        return 2;
    }
    const char *mode = argv[1], *path = argv[2];
    size_t mib = 1024, bs_kib = 0;
    int threads = 1;
    double secs = 10;
    for (int i = 3; i < argc; i++) {
        if (!strcmp(argv[i], "-m") && i + 1 < argc) mib = strtoull(argv[++i], 0, 10);
        else if (!strcmp(argv[i], "-b") && i + 1 < argc) bs_kib = strtoull(argv[++i], 0, 10);
        else if (!strcmp(argv[i], "-t") && i + 1 < argc) threads = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-s") && i + 1 < argc) secs = atof(argv[++i]);
    }
    int sync_each = !strcmp(mode, "syncwrite");
    int is_write = !strcmp(mode, "seqwrite") || !strcmp(mode, "randwrite") || sync_each;
    int is_rand = !strncmp(mode, "rand", 4) || sync_each;
    size_t bs = (bs_kib ? bs_kib : (is_rand ? 4 : 8192)) * 1024;

    if (!strcmp(mode, "seqwrite")) {
        int fd = open_nocache(path, O_CREAT | O_TRUNC | O_WRONLY);
        close(fd);
        threads = 1;
    }
    off_t fsz = !strcmp(mode, "seqwrite") ? (off_t)mib * 1024 * 1024 : file_size(path);
    pthread_t th[256];
    struct job *jobs = calloc(threads, sizeof *jobs);
    for (int i = 0; i < threads; i++) {
        jobs[i] = (struct job){.path = path, .write = is_write, .random = is_rand,
                               .sync_each = sync_each, .bs = bs,
                               .secs = secs, .seed = 0x9E3779B97F4A7C15ull * (i + 1)};
        if (is_rand) { jobs[i].lo = 0; jobs[i].hi = fsz; }
        else {
            off_t per = (fsz / threads) / bs * bs;
            jobs[i].lo = per * i;
            jobs[i].hi = per * (i + 1);
        }
    }
    double t0 = now();
    for (int i = 0; i < threads; i++) pthread_create(&th[i], NULL, io_worker, &jobs[i]);
    uint64_t ops = 0, bytes = 0;
    size_t nlat = 0;
    for (int i = 0; i < threads; i++) {
        pthread_join(th[i], NULL);
        ops += jobs[i].ops; bytes += jobs[i].bytes; nlat += jobs[i].nlat;
    }
    double dt = now() - t0;
    printf("{\"bench\":\"storage\",\"test\":\"%s\",\"threads\":%d,\"block_KiB\":%zu,"
           "\"file_MiB\":%lld,\"seconds\":%.3f,\"MB_per_s\":%.1f,\"IOPS\":%.0f",
           mode, threads, bs / 1024, (long long)(fsz >> 20), dt, bytes / dt / 1e6, ops / dt);
    if (nlat) {
        double *all = malloc(nlat * sizeof *all);
        size_t k = 0;
        for (int i = 0; i < threads; i++) {
            memcpy(all + k, jobs[i].lat, jobs[i].nlat * sizeof *all);
            k += jobs[i].nlat;
            free(jobs[i].lat);
        }
        qsort(all, nlat, sizeof *all, cmpd);
        printf(",\"lat_us_p50\":%.1f,\"lat_us_p99\":%.1f,\"lat_us_p999\":%.1f",
               all[nlat / 2], all[(size_t)(nlat * 0.99)], all[(size_t)(nlat * 0.999)]);
        free(all);
    }
    printf("}\n");
    free(jobs);
    return 0;
}
