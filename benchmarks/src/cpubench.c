// cpubench.c - portable CPU / OS-overhead microbenchmarks for macOS-vs-Linux
// comparison on the same Apple Silicon machine.
//
// All hot loops are self-contained (no libc calls) so results compare the
// hardware + kernel, not libc implementations.  Builds unchanged on macOS and
// Linux (aarch64):
//   cc -O3 -mcpu=native -pthread cpubench.c -o cpubench   (clang or gcc)
//
// Usage: cpubench <kernel> [-t threads] [-r reps] [-s seconds]
//                 [-q ui|ui2|default|utility|bg]   (macOS QoS placement)
//                 [-c cpu,cpu,...]                 (Linux affinity)
// kernels: freq fma intmix sort sgemm sme_f32 sme_bf16 sme_i8 pingpong syscall all
//
// Output: one JSON object per measurement on stdout.

#define _GNU_SOURCE
#include <arm_neon.h>
#include <errno.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#ifdef __APPLE__
#include <pthread/qos.h>
#include <sys/sysctl.h>
#else
#include <sched.h>
#include <sys/auxv.h>
#include <asm/hwcap.h>
#endif

static double now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

static int cur_cpu(void) {
#ifdef __APPLE__
    size_t n = 0;
    if (pthread_cpu_number_np(&n) != 0) return -1;
    return (int)n;
#else
    return sched_getcpu();
#endif
}

// ---------------------------------------------------------------- kernels --
// Each kernel performs `iters` units of work and returns a checksum that is
// folded into a global sink to defeat dead-code elimination.

static volatile double g_sink;

// Peak FP32 NEON FMA: 24 independent 4-wide accumulator chains.
// FLOPs per iter = 24 * 4 * 2 = 192.
static double k_fma(uint64_t iters) {
    float32x4_t b = vdupq_n_f32(1.0000001f), c = vdupq_n_f32(0.9999999f);
#define A(i) float32x4_t a##i = vdupq_n_f32((float)(i + 1));
    A(0) A(1) A(2) A(3) A(4) A(5) A(6) A(7) A(8) A(9) A(10) A(11)
    A(12) A(13) A(14) A(15) A(16) A(17) A(18) A(19) A(20) A(21) A(22) A(23)
#undef A
    for (uint64_t i = 0; i < iters; i++) {
#define F(i) a##i = vfmaq_f32(a##i, b, c);
        F(0) F(1) F(2) F(3) F(4) F(5) F(6) F(7) F(8) F(9) F(10) F(11)
        F(12) F(13) F(14) F(15) F(16) F(17) F(18) F(19) F(20) F(21) F(22) F(23)
#undef F
        __asm__ volatile("" ::: "memory");
    }
    float32x4_t s = vaddq_f32(a0, a1);
#define S(i) s = vaddq_f32(s, a##i);
    S(2) S(3) S(4) S(5) S(6) S(7) S(8) S(9) S(10) S(11) S(12) S(13) S(14)
    S(15) S(16) S(17) S(18) S(19) S(20) S(21) S(22) S(23)
#undef S
    return vaddvq_f32(s);
}

// Clock estimate: a chain of 32 *dependent* single-cycle adds per iteration,
// so work units == core cycles and the rate reads as GHz (estimate: assumes
// 1-cycle ADD latency and that loop overhead overlaps with the chain).
static double k_freq(uint64_t iters) {
    uint64_t x = 0;
    for (uint64_t i = 0; i < iters; i++) {
#define A4 "add %0, %0, #1\n\tadd %0, %0, #1\n\tadd %0, %0, #1\n\tadd %0, %0, #1\n\t"
        __asm__ volatile(A4 A4 A4 A4 A4 A4 A4 A4 : "+r"(x));
#undef A4
    }
    return (double)(x & 0xff);
}

// Integer ALU mix: 8 independent multiply/xorshift/rotate chains.
// ops per iter counted as 8 chains * 6 ops = 48 integer ops.
static double k_intmix(uint64_t iters) {
    uint64_t x[8];
    for (int i = 0; i < 8; i++) x[i] = 0x9E3779B97F4A7C15ull * (i + 1);
    for (uint64_t i = 0; i < iters; i++) {
        for (int j = 0; j < 8; j++) {
            uint64_t v = x[j];
            v ^= v >> 31;
            v *= 0xBF58476D1CE4E5B9ull;
            v = (v << 17) | (v >> 47);
            v += i;
            x[j] = v;
        }
    }
    uint64_t s = 0;
    for (int i = 0; i < 8; i++) s ^= x[i];
    return (double)(s & 0xffff);
}

// Branchy integer: in-place introsort-free quicksort of 256K uint32 values
// (1 MiB, L2-resident).  One iter = one full sort of a freshly shuffled array.
#define SORT_N (256 * 1024)
static void qs(uint32_t *a, long lo, long hi) {
    while (lo < hi) {
        uint32_t p = a[lo + ((hi - lo) >> 1)];
        long i = lo, j = hi;
        while (i <= j) {
            while (a[i] < p) i++;
            while (a[j] > p) j--;
            if (i <= j) { uint32_t t = a[i]; a[i] = a[j]; a[j] = t; i++; j--; }
        }
        if (j - lo < hi - i) { qs(a, lo, j); lo = i; }
        else { qs(a, i, hi); hi = j; }
    }
}
static double k_sort(uint64_t iters) {
    uint32_t *a = malloc(SORT_N * sizeof *a);
    uint64_t seed = 0x1234567ull, chk = 0;
    for (uint64_t it = 0; it < iters; it++) {
        for (long i = 0; i < SORT_N; i++) {
            seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17;
            a[i] = (uint32_t)seed;
        }
        qs(a, 0, SORT_N - 1);
        chk += a[SORT_N / 2];
    }
    free(a);
    return (double)(chk & 0xffff);
}

// Cache-blocked SGEMM, 256x256x256 per iter (auto-vectorised by compiler).
// FLOPs per iter = 2 * 256^3.
#define GN 256
static double k_sgemm(uint64_t iters) {
    float *A = aligned_alloc(128, GN * GN * 4), *B = aligned_alloc(128, GN * GN * 4),
          *C = aligned_alloc(128, GN * GN * 4);
    for (int i = 0; i < GN * GN; i++) { A[i] = (i % 7) * 0.1f; B[i] = (i % 5) * 0.2f; }
    for (uint64_t it = 0; it < iters; it++) {
        memset(C, 0, GN * GN * 4);
        for (int ii = 0; ii < GN; ii += 64)
            for (int kk = 0; kk < GN; kk += 64)
                for (int i = ii; i < ii + 64; i++)
                    for (int k = kk; k < kk + 64; k++) {
                        float a = A[i * GN + k];
                        float *c = &C[i * GN], *b = &B[k * GN];
                        for (int j = 0; j < GN; j++) c[j] += a * b[j];
                    }
        __asm__ volatile("" ::: "memory");
    }
    double s = C[GN * GN / 2];
    free(A); free(B); free(C);
    return s;
}


// ------------------------------------------------------------ SME kernels --
// Apple M4/M5 expose the matrix coprocessor as standard Arm SME/SME2 (the
// pre-M4 AMX was undocumented).  FMOPA outer products into the 4 ZA tiles.
// One SME unit is shared per CPU cluster, so scaling is per cluster.
#if defined(__ARM_FEATURE_SME)
#include <arm_sme.h>
#define SME_LOOP(OP)                                                   \
    for (uint64_t i = 0; i < iters; i++) {                             \
        OP(0); OP(1); OP(2); OP(3);                                    \
    }
// FP32 non-widening: 4 instr/iter, each SVLs*SVLs*2 FLOPs.
__arm_locally_streaming __arm_new("za") static double k_sme_f32(uint64_t iters) {
    svbool_t pg = svptrue_b32();
    svfloat32_t a = svdup_f32(1.0f), b = svdup_f32(0.5f);
    svzero_za();
#define OPF(t) svmopa_za32_f32_m(t, pg, pg, a, b)
    SME_LOOP(OPF)
#undef OPF
    svfloat32_t r = svread_hor_za32_f32_m(svdup_f32(0), pg, 0, 0);
    return svaddv_f32(pg, r);
}
// BF16 -> FP32 widening (2-way): SVLs*SVLs*2*2 FLOPs per instr.
__arm_locally_streaming __arm_new("za") static double k_sme_bf16(uint64_t iters) {
    svbool_t pg = svptrue_b16();
    svbfloat16_t a = svreinterpret_bf16_u16(svdup_u16(0x3f80));
    svbfloat16_t b = svreinterpret_bf16_u16(svdup_u16(0x3f00));
    svzero_za();
#define OPB(t) svmopa_za32_bf16_m(t, pg, pg, a, b)
    SME_LOOP(OPB)
#undef OPB
    svfloat32_t r = svread_hor_za32_f32_m(svdup_f32(0), svptrue_b32(), 0, 0);
    return svaddv_f32(svptrue_b32(), r);
}
// INT8 -> INT32 widening (4-way): SVLs*SVLs*4*2 ops per instr.
__arm_locally_streaming __arm_new("za") static double k_sme_i8(uint64_t iters) {
    svbool_t pg = svptrue_b8();
    svint8_t a = svdup_s8(1), b = svdup_s8(2);
    svzero_za();
#define OPI(t) svmopa_za32_s8_m(t, pg, pg, a, b)
    SME_LOOP(OPI)
#undef OPI
    svint32_t r = svread_hor_za32_s32_m(svdup_s32(0), svptrue_b32(), 0, 0);
    return (double)svaddv_s32(svptrue_b32(), r);
}
__arm_locally_streaming static uint64_t sme_svl_words(void) { return svcntw(); }
#endif

static int have_sme(void) {
#if defined(__ARM_FEATURE_SME)
#ifdef __APPLE__
    int v = 0; size_t n = sizeof v;
    if (sysctlbyname("hw.optional.arm.FEAT_SME", &v, &n, NULL, 0) != 0) return 0;
    return v;
#else
    return (getauxval(AT_HWCAP2) & HWCAP2_SME) != 0;
#endif
#else
    return 0;
#endif
}

struct kernel {
    const char *name;
    double (*fn)(uint64_t);
    double work_per_iter;  // units below
    const char *unit;      // what work_per_iter counts
    uint64_t calib_iters;  // starting iteration count for calibration
};

static struct kernel KERNELS[] = {
    {"freq", k_freq, 32.0, "GHz(est)", 1u << 20},
    {"fma", k_fma, 192.0, "GFLOP/s", 1u << 20},
    {"intmix", k_intmix, 48.0, "Gop/s", 1u << 20},
    {"sort", k_sort, SORT_N, "Melem/s", 4},
    {"sgemm", k_sgemm, 2.0 * GN * GN * GN, "GFLOP/s", 4},
#if defined(__ARM_FEATURE_SME)
    // work_per_iter filled in at startup from the streaming vector length
    {"sme_f32", k_sme_f32, 0, "GFLOP/s", 1u << 16},
    {"sme_bf16", k_sme_bf16, 0, "GFLOP/s", 1u << 16},
    {"sme_i8", k_sme_i8, 0, "Gop/s", 1u << 16},
#endif
};

// ------------------------------------------------------------- threading --
struct targ {
    const struct kernel *k;
    uint64_t iters;
    const char *qos;
    int pin_cpu;
    atomic_int *ready;
    atomic_int *go;
    double t0, t1;
    int cpu_before, cpu_after;
};

static void apply_placement(const char *qos, int pin_cpu) {
#ifdef __APPLE__
    (void)pin_cpu;
    if (!qos) return;
    qos_class_t q = QOS_CLASS_DEFAULT;
    if (!strcmp(qos, "ui")) q = QOS_CLASS_USER_INTERACTIVE;
    else if (!strcmp(qos, "ui2")) q = QOS_CLASS_USER_INITIATED;
    else if (!strcmp(qos, "utility")) q = QOS_CLASS_UTILITY;
    else if (!strcmp(qos, "bg")) q = QOS_CLASS_BACKGROUND;
    pthread_set_qos_class_self_np(q, 0);
#else
    (void)qos;
    if (pin_cpu >= 0) {
        cpu_set_t s;
        CPU_ZERO(&s);
        CPU_SET(pin_cpu, &s);
        pthread_setaffinity_np(pthread_self(), sizeof s, &s);
    }
#endif
}

static void *worker(void *p) {
    struct targ *a = p;
    apply_placement(a->qos, a->pin_cpu);
    atomic_fetch_add(a->ready, 1);
    while (!atomic_load(a->go)) { }
    a->cpu_before = cur_cpu();
    a->t0 = now();
    g_sink += a->k->fn(a->iters);
    a->t1 = now();
    a->cpu_after = cur_cpu();
    return NULL;
}

static uint64_t calibrate(const struct kernel *k, double seconds, const char *qos, int pin) {
    apply_placement(qos, pin);
    uint64_t it = k->calib_iters;
    for (;;) {
        double t0 = now();
        g_sink += k->fn(it);
        double dt = now() - t0;
        if (dt > 0.2) return (uint64_t)(it * (seconds / dt)) + 1;
        it *= 2;
    }
}

static int cmpd(const void *a, const void *b) {
    double x = *(const double *)a, y = *(const double *)b;
    return x < y ? -1 : x > y;
}

static void run_kernel(const struct kernel *k, int threads, int reps, double secs,
                       const char *qos, int *pins, int npins) {
    uint64_t iters = calibrate(k, secs, qos, npins ? pins[0] : -1);
    double *agg = calloc(reps, sizeof *agg), *per = calloc(reps, sizeof *per);
    char cpus[1024] = "";
    for (int r = 0; r < reps; r++) {
        pthread_t *th = calloc(threads, sizeof *th);
        struct targ *ta = calloc(threads, sizeof *ta);
        atomic_int ready = 0, go = 0;
        for (int i = 0; i < threads; i++) {
            ta[i] = (struct targ){.k = k, .iters = iters, .qos = qos,
                                  .pin_cpu = npins ? pins[i % npins] : -1,
                                  .ready = &ready, .go = &go};
            pthread_create(&th[i], NULL, worker, &ta[i]);
        }
        while (atomic_load(&ready) < threads) { }
        atomic_store(&go, 1);
        double tmin = 1e300, tmax = 0, sum_rate = 0;
        for (int i = 0; i < threads; i++) {
            pthread_join(th[i], NULL);
            if (ta[i].t0 < tmin) tmin = ta[i].t0;
            if (ta[i].t1 > tmax) tmax = ta[i].t1;
            sum_rate += iters * k->work_per_iter / (ta[i].t1 - ta[i].t0);
        }
        agg[r] = threads * (double)iters * k->work_per_iter / (tmax - tmin);
        per[r] = sum_rate / threads;
        if (r == reps - 1) {
            size_t off = 0;
            for (int i = 0; i < threads && off < sizeof cpus - 16; i++)
                off += snprintf(cpus + off, sizeof cpus - off, "%s%d>%d", i ? "," : "",
                                ta[i].cpu_before, ta[i].cpu_after);
        }
        free(th); free(ta);
    }
    double scale = (!strcmp(k->unit, "Melem/s")) ? 1e-6 : 1e-9;
    qsort(agg, reps, sizeof *agg, cmpd);
    qsort(per, reps, sizeof *per, cmpd);
    printf("{\"bench\":\"cpu\",\"kernel\":\"%s\",\"threads\":%d,\"qos\":\"%s\",\"reps\":%d,"
           "\"unit\":\"%s\",\"aggregate_median\":%.3f,\"aggregate_min\":%.3f,\"aggregate_max\":%.3f,"
           "\"per_thread_median\":%.3f,\"cpus_last_rep\":\"%s\"}\n",
           k->name, threads, qos ? qos : "none", reps, k->unit, agg[reps / 2] * scale,
           agg[0] * scale, agg[reps - 1] * scale, per[reps / 2] * scale, cpus);
    fflush(stdout);
    free(agg); free(per);
}

// ---------------------------------------------------------- OS overheads --
// Pipe ping-pong between two threads: measures wakeup + context switch cost.
static int pp_a[2], pp_b[2];
static long pp_rounds;
static const char *pp_qos;
static void *pp_peer(void *x) {
    (void)x;
    apply_placement(pp_qos, -1);
    char c;
    for (long i = 0; i < pp_rounds; i++) {
        if (read(pp_a[0], &c, 1) != 1) break;
        if (write(pp_b[1], &c, 1) != 1) break;
    }
    return NULL;
}
static void run_pingpong(int reps, const char *qos) {
    pp_rounds = 200000;
    pp_qos = qos;
    double *v = calloc(reps, sizeof *v);
    for (int r = 0; r < reps; r++) {
        if (pipe(pp_a) || pipe(pp_b)) { perror("pipe"); exit(1); }
        pthread_t t;
        pthread_create(&t, NULL, pp_peer, NULL);
        apply_placement(qos, -1);
        char c = 'x';
        double t0 = now();
        for (long i = 0; i < pp_rounds; i++) {
            if (write(pp_a[1], &c, 1) != 1) break;
            if (read(pp_b[0], &c, 1) != 1) break;
        }
        double dt = now() - t0;
        pthread_join(t, NULL);
        close(pp_a[0]); close(pp_a[1]); close(pp_b[0]); close(pp_b[1]);
        v[r] = dt / pp_rounds * 1e6;  // us per round trip
    }
    qsort(v, reps, sizeof *v, cmpd);
    printf("{\"bench\":\"cpu\",\"kernel\":\"pipe_pingpong_roundtrip\",\"qos\":\"%s\",\"reps\":%d,"
           "\"unit\":\"us\",\"median\":%.3f,\"min\":%.3f,\"max\":%.3f}\n",
           qos ? qos : "none", reps, v[reps / 2], v[0], v[reps - 1]);
    free(v);
}

static void run_syscall(int reps) {
    double *v = calloc(reps, sizeof *v);
    long n = 2000000;
    for (int r = 0; r < reps; r++) {
        double t0 = now();
        long s = 0;
        for (long i = 0; i < n; i++) s += getppid();
        double dt = now() - t0;
        g_sink += s;
        v[r] = dt / n * 1e9;
    }
    qsort(v, reps, sizeof *v, cmpd);
    printf("{\"bench\":\"cpu\",\"kernel\":\"syscall_getppid\",\"reps\":%d,\"unit\":\"ns\","
           "\"median\":%.2f,\"min\":%.2f,\"max\":%.2f}\n", reps, v[reps / 2], v[0], v[reps - 1]);
    free(v);
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s fma|intmix|sort|sgemm|pingpong|syscall [-t N] [-r reps] "
                        "[-s secs] [-q qos] [-c cpu,cpu]\n", argv[0]);
        return 2;
    }
    const char *which = argv[1], *qos = NULL;
    int threads = 1, reps = 5, pins[512], npins = 0;
    double secs = 1.0;
    for (int i = 2; i < argc; i++) {
        if (!strcmp(argv[i], "-t") && i + 1 < argc) threads = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-r") && i + 1 < argc) reps = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-s") && i + 1 < argc) secs = atof(argv[++i]);
        else if (!strcmp(argv[i], "-q") && i + 1 < argc) qos = argv[++i];
        else if (!strcmp(argv[i], "-c") && i + 1 < argc) {
            char *s = argv[++i], *tok;
            while ((tok = strsep(&s, ",")) && npins < 512) pins[npins++] = atoi(tok);
        }
    }
    if (!strcmp(which, "pingpong")) { run_pingpong(reps, qos); return 0; }
    if (!strcmp(which, "syscall")) { run_syscall(reps); return 0; }
    int ran = 0, sme = have_sme();
#if defined(__ARM_FEATURE_SME)
    if (sme) {
        double svls = (double)sme_svl_words();  // FP32 lanes per vector
        for (size_t i = 0; i < sizeof KERNELS / sizeof *KERNELS; i++) {
            if (!strcmp(KERNELS[i].name, "sme_f32")) KERNELS[i].work_per_iter = 4 * svls * svls * 2;
            if (!strcmp(KERNELS[i].name, "sme_bf16")) KERNELS[i].work_per_iter = 4 * svls * svls * 2 * 2;
            if (!strcmp(KERNELS[i].name, "sme_i8")) KERNELS[i].work_per_iter = 4 * svls * svls * 4 * 2;
        }
    }
#endif
    for (size_t i = 0; i < sizeof KERNELS / sizeof *KERNELS; i++)
        if (!strcmp(which, "all") || !strcmp(which, KERNELS[i].name)) {
            if (!strncmp(KERNELS[i].name, "sme", 3) && !sme) {
                printf("{\"bench\":\"cpu\",\"kernel\":\"%s\",\"status\":\"unsupported\"}\n",
                       KERNELS[i].name);
                ran = 1;
                continue;
            }
            run_kernel(&KERNELS[i], threads, reps, secs, qos, pins, npins);
            ran = 1;
        }
    if (!ran) { fprintf(stderr, "unknown kernel %s\n", which); return 2; }
    return 0;
}
