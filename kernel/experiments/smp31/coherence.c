/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Original bounded Linux affinity, timer and shared-data wakeup smoke test.
 * No hotplug, MMIO, system-register access, frequency or renderer changes. */
#define _GNU_SOURCE
#include <errno.h>
#include <linux/futex.h>
#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

enum { ROUNDS = 2000 };
static _Atomic int phase, failed;
static uint64_t payload[8];
static int cores[2];
static uint64_t deadline;
static uint64_t now(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) abort();
    return (uint64_t)t.tv_sec * 1000000000 + t.tv_nsec;
}
static void wake(void) { syscall(SYS_futex, &phase, FUTEX_WAKE_PRIVATE, 1, NULL, NULL, 0); }
static int wait_for(int wanted) {
    struct timespec bound = {0, 100000000};
    while (atomic_load_explicit(&phase, memory_order_acquire) != wanted) {
        if (atomic_load(&failed) || now() >= deadline) return -1;
        int old = 1 - wanted;
        int r = syscall(SYS_futex, &phase, FUTEX_WAIT_PRIVATE, old, &bound, NULL, 0);
        if (r < 0 && errno != EAGAIN && errno != EINTR && errno != ETIMEDOUT) return -1;
    }
    return atomic_load(&failed) || now() >= deadline ? -1 : 0;
}
static int pin(int cpu) {
    cpu_set_t mask;
    CPU_ZERO(&mask); CPU_SET(cpu, &mask);
    return pthread_setaffinity_np(pthread_self(), sizeof(mask), &mask) || sched_getcpu() != cpu;
}
static void *worker(void *unused) {
    (void)unused;
    if (pin(cores[1])) goto fail;
    for (uint64_t n = 1; n <= ROUNDS; n++) {
        if (wait_for(1) || sched_getcpu() != cores[1]) goto fail;
        for (unsigned j = 0; j < 8; j++) if (payload[j] != (n ^ (0xabcdeULL << j))) goto fail;
        atomic_store_explicit(&phase, 0, memory_order_release); wake();
    }
    return NULL;
fail:
    atomic_store(&failed, 1); wake(); return NULL;
}
int main(void) {
    cpu_set_t mask;
    if (sched_getaffinity(0, sizeof(mask), &mask)) return 1;
    int found = 0;
    for (int i = 0; i < CPU_SETSIZE && found < 2; i++) if (CPU_ISSET(i, &mask)) cores[found++] = i;
    if (found != 2) { puts("{\"result\":\"NEEDS_TWO_ALLOWED_CPUS\"}"); return 77; }
    if (pin(cores[0])) return 1;
    uint64_t start = now(); deadline = start + 5000000000ULL;
    pthread_t thread;
    if (pthread_create(&thread, NULL, worker, NULL)) return 1;
    for (uint64_t n = 1; n <= ROUNDS; n++) {
        if (wait_for(0) || sched_getcpu() != cores[0]) { atomic_store(&failed, 1); break; }
        for (unsigned j = 0; j < 8; j++) payload[j] = n ^ (0xabcdeULL << j);
        atomic_store_explicit(&phase, 1, memory_order_release); wake();
    }
    if (wait_for(0)) atomic_store(&failed, 1);
    wake();
    if (pthread_join(thread, NULL)) return 1;
    uint64_t elapsed = now() - start;
    printf("{\"result\":\"%s\",\"cpus\":[%d,%d],\"rounds\":%d,\"elapsed_ns\":%llu}\n",
           atomic_load(&failed) ? "FAIL" : "PASS", cores[0], cores[1], ROUNDS,
           (unsigned long long)elapsed);
    return atomic_load(&failed) ? 1 : 0;
}
