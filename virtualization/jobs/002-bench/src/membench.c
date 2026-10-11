// membench.c - portable memory-subsystem benchmarks (macOS + Linux, aarch64).
//   cc -O3 -mcpu=native -pthread membench.c -o membench
//
// Usage:
//   membench stream  [-t threads] [-m MiB_per_array] [-r reps]
//   membench latency [-m max_MiB] [-d]      (random pointer chase, 128 B lines;
//                                            -d sets DIT, disabling Apple's DMP)
//   membench fault   [-m MiB] [-r reps]     (anonymous mmap + first-touch rate)
//
// STREAM kernels are explicit loops (no memcpy) so libc does not differ
// between OSes.  Bandwidth uses STREAM byte-counting conventions.

#define _GNU_SOURCE
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
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

// ----------------------------------------------------------------- STREAM --
static double *A, *B, *C;
static size_t N;
static int T;
#ifdef __APPLE__
// macOS lacks pthread barriers; tiny spin barrier.
typedef struct { atomic_int count, gen; int n; } sbar_t;
static sbar_t sb;
static void sbar_wait(void) {
    int g = atomic_load(&sb.gen);
    if (atomic_fetch_add(&sb.count, 1) == sb.n - 1) {
        atomic_store(&sb.count, 0);
        atomic_fetch_add(&sb.gen, 1);
    } else {
        while (atomic_load(&sb.gen) == g) { }
    }
}
#define BARRIER() sbar_wait()
#else
static pthread_barrier_t pb;
#define BARRIER() pthread_barrier_wait(&pb)
#endif

enum { K_COPY, K_SCALE, K_ADD, K_TRIAD, NK };
static const char *KN[NK] = {"copy", "scale", "add", "triad"};
static const double KB[NK] = {16, 16, 24, 24};  // bytes moved per element
static int REPS = 10;
static double times[NK][64];

static void *stream_worker(void *arg) {
    long id = (long)arg;
    size_t lo = N * id / T, hi = N * (id + 1) / T;
    const double s = 3.0;
    for (size_t i = lo; i < hi; i++) { A[i] = 1.0; B[i] = 2.0; C[i] = 0.0; }  // first touch
    for (int r = 0; r < REPS; r++) {
        for (int k = 0; k < NK; k++) {
            BARRIER();
            double t0 = now();
            switch (k) {
            case K_COPY:  for (size_t i = lo; i < hi; i++) C[i] = A[i]; break;
            case K_SCALE: for (size_t i = lo; i < hi; i++) B[i] = s * C[i]; break;
            case K_ADD:   for (size_t i = lo; i < hi; i++) C[i] = A[i] + B[i]; break;
            case K_TRIAD: for (size_t i = lo; i < hi; i++) A[i] = B[i] + s * C[i]; break;
            }
            BARRIER();
            if (id == 0) times[k][r] = now() - t0;
        }
    }
    return NULL;
}

static void run_stream(int threads, size_t mib, int reps) {
    T = threads;
    REPS = reps > 64 ? 64 : reps;
    N = mib * 1024 * 1024 / sizeof(double);
    A = aligned_alloc(16384, N * sizeof(double));
    B = aligned_alloc(16384, N * sizeof(double));
    C = aligned_alloc(16384, N * sizeof(double));
#ifdef __APPLE__
    sb.n = T;
#else
    pthread_barrier_init(&pb, NULL, T);
#endif
    pthread_t th[512];
    for (long i = 0; i < T; i++) pthread_create(&th[i], NULL, stream_worker, (void *)i);
    for (int i = 0; i < T; i++) pthread_join(th[i], NULL);
    for (int k = 0; k < NK; k++) {
        double v[64];
        // skip first rep (warm-up), STREAM reports best
        int n = REPS - 1;
        for (int r = 1; r < REPS; r++) v[r - 1] = KB[k] * N / times[k][r] / 1e9;
        qsort(v, n, sizeof *v, cmpd);
        printf("{\"bench\":\"mem\",\"test\":\"stream_%s\",\"threads\":%d,\"array_MiB\":%zu,"
               "\"reps\":%d,\"unit\":\"GB/s\",\"best\":%.2f,\"median\":%.2f,\"worst\":%.2f}\n",
               KN[k], T, mib, n, v[n - 1], v[n / 2], v[0]);
    }
    double chk = A[N / 3] + B[N / 5] + C[N / 7];
    if (chk == 12345.678) puts("");
    free(A); free(B); free(C);
}

// ---------------------------------------------------------------- latency --
// With -d, PSTATE.DIT is set first.  On Apple M3 and later, DIT also disables
// the data memory-dependent prefetcher (DMP), which otherwise prefetches the
// pointers stored in this chase buffer and makes cache latencies look lower.
#define LINE 128
static int g_dit;
static void run_latency(size_t max_mib) {
    if (g_dit) __asm__ volatile("msr DIT, #1" ::: "memory");
    size_t sizes_kib[] = {16, 32, 64, 96, 128, 192, 256, 512, 1024, 2048, 4096, 8192,
                          12288, 16384, 24576, 32768, 49152, 65536, 98304, 131072,
                          262144, 524288, 1048576, 2097152};
    for (size_t si = 0; si < sizeof sizes_kib / sizeof *sizes_kib; si++) {
        size_t bytes = sizes_kib[si] * 1024;
        if (bytes > max_mib * 1024 * 1024) break;
        size_t n = bytes / LINE;
        char *buf = aligned_alloc(16384, bytes);
        size_t *perm = malloc(n * sizeof *perm);
        for (size_t i = 0; i < n; i++) perm[i] = i;
        uint64_t seed = 88172645463325252ull;
        for (size_t i = n - 1; i > 0; i--) {  // Fisher-Yates (Sattolo for one cycle)
            seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17;
            size_t j = seed % i;
            size_t t = perm[i]; perm[i] = perm[j]; perm[j] = t;
        }
        for (size_t i = 0; i < n; i++)
            *(void **)(buf + perm[i] * LINE) = buf + perm[(i + 1) % n] * LINE;
        free(perm);
        void **p = (void **)buf;
        size_t steps = 20 * 1000 * 1000;
        if (steps < 4 * n) steps = 4 * n;
        for (size_t i = 0; i < n; i++) p = (void **)*p;  // warm
        double best = 1e30;
        for (int r = 0; r < 3; r++) {
            double t0 = now();
            for (size_t i = 0; i < steps; i += 8) {
                p = (void **)*p; p = (void **)*p; p = (void **)*p; p = (void **)*p;
                p = (void **)*p; p = (void **)*p; p = (void **)*p; p = (void **)*p;
            }
            double ns = (now() - t0) / steps * 1e9;
            if (ns < best) best = ns;
        }
        printf("{\"bench\":\"mem\",\"test\":\"latency_random_chase\",\"dit\":%d,"
               "\"size_KiB\":%zu,\"unit\":\"ns\",\"best\":%.2f,\"sink\":%d}\n",
               g_dit, sizes_kib[si], best, (int)((uintptr_t)p & 1));
        fflush(stdout);
        free(buf);
    }
}

// ------------------------------------------------------------ page faults --
static void run_fault(size_t mib, int reps) {
    size_t bytes = mib * 1024 * 1024;
    long pg = sysconf(_SC_PAGESIZE);
    double *v = calloc(reps, sizeof *v), *u = calloc(reps, sizeof *u);
    for (int r = 0; r < reps; r++) {
        double t0 = now();
        char *m = mmap(NULL, bytes, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0);
        if (m == MAP_FAILED) { perror("mmap"); exit(1); }
        for (size_t i = 0; i < bytes; i += pg) m[i] = 1;
        double t1 = now();
        munmap(m, bytes);
        double t2 = now();
        v[r] = bytes / (t1 - t0) / 1e9;
        u[r] = (t2 - t1) * 1e3;
    }
    qsort(v, reps, sizeof *v, cmpd);
    qsort(u, reps, sizeof *u, cmpd);
    printf("{\"bench\":\"mem\",\"test\":\"anon_first_touch\",\"MiB\":%zu,\"page_size\":%ld,"
           "\"reps\":%d,\"unit\":\"GB/s\",\"median\":%.2f,\"best\":%.2f,"
           "\"faults_per_s_median\":%.0f,\"munmap_ms_median\":%.2f}\n",
           mib, pg, reps, v[reps / 2], v[reps - 1], v[reps / 2] * 1e9 / pg, u[reps / 2]);
    free(v); free(u);
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s stream|latency|fault [-t N] [-m MiB] [-r reps]\n", argv[0]);
        return 2;
    }
    int threads = 1, reps = 10;
    size_t mib = 0;
    for (int i = 2; i < argc; i++) {
        if (!strcmp(argv[i], "-t") && i + 1 < argc) threads = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-m") && i + 1 < argc) mib = strtoull(argv[++i], 0, 10);
        else if (!strcmp(argv[i], "-r") && i + 1 < argc) reps = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-d")) g_dit = 1;
    }
    if (!strcmp(argv[1], "stream")) run_stream(threads, mib ? mib : 1024, reps);
    else if (!strcmp(argv[1], "latency")) run_latency(mib ? mib : 2048);
    else if (!strcmp(argv[1], "fault")) run_fault(mib ? mib : 4096, reps < 3 ? 3 : reps);
    else { fprintf(stderr, "unknown test\n"); return 2; }
    return 0;
}
