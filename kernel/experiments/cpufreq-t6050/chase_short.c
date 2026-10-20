/* SPDX-License-Identifier: MIT */
/* Bounded diagnostic random pointer chase. Portable; same build on both OSes.
 * Fixed seed, 128-byte links, one complete warm traversal, three timed samples.
 * No DIT/sysreg changes. This is distinct from membench's longer protocol. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

static uint32_t state = 0x605028u;
static uint32_t random32(void) {
    state ^= state << 13; state ^= state >> 17; state ^= state << 5;
    return state;
}
static double now(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) exit(2);
    return t.tv_sec + t.tv_nsec * 1e-9;
}
int main(void) {
    const size_t sizes[] = {16u << 10, 4u << 20, 32u << 20, 128u << 20};
    alarm(45);
    for (size_t s = 0; s < sizeof(sizes) / sizeof(*sizes); ++s) {
        size_t n = sizes[s] / 128, *order = malloc(n * sizeof(*order));
        unsigned char *buf = NULL;
        if (!order || posix_memalign((void **)&buf, 128, sizes[s])) return 2;
        for (size_t i = 0; i < n; ++i) order[i] = i;
        for (size_t i = n - 1; i; --i) {
            size_t j = random32() % (i + 1), x = order[i];
            order[i] = order[j]; order[j] = x;
        }
        for (size_t i = 0; i < n; ++i)
            *(void **)(buf + order[i] * 128) = buf + order[(i + 1) % n] * 128;
        free(order);
        void **p = (void **)buf;
        for (size_t i = 0; i < n; ++i) p = (void **)*p;
        if (p != (void **)buf) return 3;
        size_t steps = n < 262144 ? 262144 : n;
        for (unsigned r = 0; r < 3; ++r) {
            double start = now();
            for (size_t i = 0; i < steps; ++i) p = (void **)*p;
            double elapsed = now() - start;
            printf("{\"bench\":\"chase_short\",\"size_bytes\":%zu,\"steps\":%zu,"
                   "\"sample\":%u,\"ns_per_load\":%.3f,\"sink\":%u}\n",
                   sizes[s], steps, r, elapsed / steps * 1e9,
                   (unsigned)((uintptr_t)p & 127));
            fflush(stdout);
        }
        free(buf);
    }
    return 0;
}
