/* SPDX-License-Identifier: MIT */
/* Same dependent-load loop and full-cycle check across OSes. Layout and
 * per-allocation page advice are independent variables, never global knobs. */
#define _GNU_SOURCE
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <time.h>
#include <unistd.h>
#ifdef __APPLE__
#include <pthread.h>
#else
#include <sched.h>
#endif

static int cpu_number(void) {
#ifdef __APPLE__
    size_t n=0;
    return pthread_cpu_number_np(&n) ? -1 : (int)n;
#else
    return sched_getcpu();
#endif
}

static uint32_t rng;
static uint32_t next(void) { rng ^= rng << 13; rng ^= rng >> 17; rng ^= rng << 5; return rng; }
static void shuffle(size_t *a, size_t n) {
    for (size_t i = n - 1; i; --i) {
        size_t j = next() % (i + 1), x = a[i]; a[i] = a[j]; a[j] = x;
    }
}
static double now(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) exit(2);
    return t.tv_sec + 1e-9 * t.tv_nsec;
}
static long huge_kb(void *base) {
#ifdef __linux__
    FILE *f = fopen("/proc/self/smaps", "r");
    if (!f) return -1;
    char line[256]; unsigned long lo, hi; long kb = -1; int in = 0;
    while (fgets(line, sizeof(line), f)) {
        if (sscanf(line, "%lx-%lx", &lo, &hi) == 2)
            in = lo <= (uintptr_t)base && (uintptr_t)base < hi;
        else if (in && sscanf(line, "AnonHugePages: %ld kB", &kb) == 1) break;
    }
    fclose(f); return kb;
#else
    (void)base; return -1;
#endif
}
__attribute__((noinline)) static void **chase(void **p, size_t steps) {
    for (size_t i = 0; i < steps; ++i) p = (void **)*p;
    /* Keep the result observable even with LTO or alternate compilers. */
    __asm__ volatile("" : "+r"(p) : : "memory");
    return p;
}
static int run(size_t bytes, int local, int huge) {
    const size_t align = 32u << 20, stride = 128, page = (size_t)sysconf(_SC_PAGESIZE);
    size_t n = bytes / stride, per = page / stride;
    if (page < stride || bytes % page) return 2;
    void *raw = mmap(NULL, bytes + align, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0);
    if (raw == MAP_FAILED) return 2;
    uintptr_t aligned = ((uintptr_t)raw + align - 1) & ~(uintptr_t)(align - 1);
    size_t prefix = aligned - (uintptr_t)raw;
    if (prefix) munmap(raw, prefix);
    munmap((void *)(aligned + bytes), align - prefix);
    unsigned char *buf = (unsigned char *)aligned;
    int advice = -1, error = 0;
#ifdef __linux__
    advice = madvise(buf, bytes, huge ? MADV_HUGEPAGE : MADV_NOHUGEPAGE);
    error = advice ? errno : 0;
#else
    (void)huge;
#endif
    size_t *order = malloc(n * sizeof(*order));
    size_t *pages = malloc(n / per * sizeof(*pages));
    if (!order || !pages) return 2;
    rng = 0x605029u;
    for (size_t i = 0; i < n; ++i) order[i] = i;
    if (!local) shuffle(order, n);
    else {
        for (size_t i = 0; i < n / per; ++i) pages[i] = i;
        shuffle(pages, n / per);
        for (size_t i = 0; i < n / per; ++i) {
            for (size_t j = 0; j < per; ++j) order[i * per + j] = pages[i] * per + j;
            shuffle(order + i * per, per);
        }
    }
    for (size_t i = 0; i < n; ++i)
        *(void **)(buf + stride * order[i]) = buf + stride * order[(i + 1) % n];
    /* Exact graph validation: every allocated slot once, no early cycle. */
    void **p = (void **)buf;
    for (size_t i = 1; i <= n; ++i) {
        p = (void **)*p;
        if ((i < n && p == (void **)buf) || (i == n && p != (void **)buf)) return 3;
    }
    free(order); free(pages);
    size_t steps = n < 262144 ? 262144 : n;
    long hp = huge_kb(buf);
    for (unsigned r = 0; r < 3; ++r) {
        struct rusage before, after;
        getrusage(RUSAGE_SELF, &before);
        int cpu_before=cpu_number();
        double start = now(); p = chase(p, steps); double elapsed = now() - start;
        int cpu_after=cpu_number();
        getrusage(RUSAGE_SELF, &after);
        printf("{\"bench\":\"memory29\",\"bytes\":%zu,\"layout\":\"%s\","
               "\"advice\":\"%s\",\"advice_rc\":%d,\"advice_errno\":%d,"
               "\"page_bytes\":%zu,\"anon_huge_kb_before\":%ld,\"anon_huge_kb_after\":%ld,"
               "\"sample\":%u,\"steps\":%zu,\"ns_per_load\":%.3f,\"cpu_before\":%d,\"cpu_after\":%d,"
               "\"minor_faults\":%ld,\"major_faults\":%ld,\"voluntary_switches\":%ld,"
               "\"involuntary_switches\":%ld,\"sink\":%u}\n",
               bytes, local ? "page-local" : "global-random", huge ? "huge" : "base",
               advice, error, page, hp, huge_kb(buf), r, steps, elapsed * 1e9 / steps,cpu_before,cpu_after,
               after.ru_minflt - before.ru_minflt, after.ru_majflt - before.ru_majflt,
               after.ru_nvcsw - before.ru_nvcsw, after.ru_nivcsw - before.ru_nivcsw,
               (unsigned)((uintptr_t)p & 127));
        fflush(stdout);
    }
    munmap(buf, bytes); return 0;
}
int main(int argc, char **argv) {
    const char *qos = argc == 2 ? argv[1] : "default";
    if (argc > 2 || (strcmp(qos,"default") && strcmp(qos,"background"))) return 2;
#ifdef __APPLE__
    if (!strcmp(qos,"background") && pthread_set_qos_class_self_np(QOS_CLASS_BACKGROUND,0)) return 2;
#else
    if (strcmp(qos,"default")) return 2;
#endif
    alarm(80);
    printf("{\"event\":\"method\",\"qos\":\"%s\",\"core_placement\":\"sample-boundaries-only\",\"seed\":6311977}\n",qos);
    const size_t sizes[] = {16u<<10, 4u<<20, 32u<<20, 128u<<20};
    for (int huge=0; huge<2; ++huge) {
#ifdef __APPLE__
        if (huge) break; /* Linux advice unavailable, no fabricated A/B. */
#endif
        for (int local=0; local<2; ++local)
            for (size_t i=0; i<sizeof(sizes)/sizeof(*sizes); ++i) {
                int rc=run(sizes[i],local,huge); if (rc) return rc;
            }
    }
    return 0;
}
