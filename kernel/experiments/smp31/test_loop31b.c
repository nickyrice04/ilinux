/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Actual pinned smp_secondary_entry and timeout_calculate, extracted in VM.
 * Atomic shared fields model uncached/ordered target RAM; host sleep models
 * WFE. This is protocol validation, NOT a hardware/architecture emulator. */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
typedef uint64_t u64;
typedef uint32_t u32;
#define MAX_CPUS 32
#define SECONDARY_STACK_SIZE 0x10000
#define MPIDR_EL1 1
#define CNTPCT_EL0 2
#define CNTFRQ_EL0 3
#define TPIDR_EL2 4
#define TPIDR_EL1 5
#define SYS_IMP_APL_IPI_SR_EL1 6
#define AIC_IPI_MASK_SET 0
#define AIC_IPI_SELF 0
#define AIC_IPI_ACK 0
#define AIC_IPI_OTHER 0
#define AIC_IPI_MASK_CLR 0
static unsigned char secondary_stacks[MAX_CPUS][SECONDARY_STACK_SIZE];
static struct { _Atomic u64 mpidr, stack; } smp_reset_stacks[MAX_CPUS];
static struct spin_table {
    _Atomic u64 mpidr, flag, target, args[4], retval;
} spin_table[MAX_CPUS];
static const struct { bool fast_ipi; } features = {true};
static const typeof(features) *cpu_features = &features;
static int target_cpu = 1;
static _Atomic bool wfe_mode = true, done;
static _Atomic int park_visits, tpidr;
static u64 now_ns(void) {
    struct timespec ts; assert(!clock_gettime(CLOCK_MONOTONIC, &ts));
    return (u64)ts.tv_sec * 1000000000ULL + (u64)ts.tv_nsec;
}
static u64 readreg(int reg) {
    if (reg == MPIDR_EL1) return 0x40001;
    if (reg == CNTPCT_EL0) return now_ns();
    assert(reg == CNTFRQ_EL0); return 1000000000;
}
#define mrs(reg) readreg(reg)
#define msr(reg, value) do { assert((reg) == TPIDR_EL2); atomic_store(&tpidr, (value)); } while (0)
static bool in_el2(void) { return true; }
static void aic_write(int a, int b) { (void)a; (void)b; abort(); }
static void aic_ack(void) { abort(); }
static void deep_wfi(void) { abort(); }
static void operation(const char *op) {
    atomic_thread_fence(memory_order_seq_cst);
    if (!strcmp(op, "wfe")) {
        atomic_fetch_add(&park_visits, 1);
        if (atomic_load(&done)) pthread_exit(NULL);
        struct timespec ts = {.tv_nsec=1000000}; nanosleep(&ts, NULL);
    }
}
#define sysop(op) operation(op)
#define printf(...) ((void)0)
#include "loop31b.inc"
#undef printf
static void *secondary(void *unused) { (void)unused; smp_secondary_entry(); return NULL; }
static void wait_value(_Atomic u64 *field, u64 expected) {
    u64 end = now_ns() + 2000000000ULL;
    while (atomic_load(field) != expected) {
        assert(now_ns() < end);
        struct timespec ts = {.tv_nsec=1000000}; nanosleep(&ts, NULL);
    }
}
int main(void) {
    for (int i=0; i<MAX_CPUS; ++i) smp_reset_stacks[i].mpidr = UINT64_MAX;
    pthread_t thread; assert(!pthread_create(&thread, NULL, secondary, NULL));
    wait_value(&spin_table[1].flag, 1);
    assert(spin_table[1].mpidr == 0x40001 && tpidr == 1);
    assert(smp_reset_stacks[1].mpidr == 0x40001);
    assert(smp_reset_stacks[1].stack == (u64)secondary_stacks[1] + SECONDARY_STACK_SIZE);
    u64 previous = 0;
    for (int n=0; n<2; ++n) {
        assert(spin_table[1].target == 0);
        atomic_store_explicit(&spin_table[1].target, (u64)timeout_calculate, memory_order_release);
        wait_value(&spin_table[1].flag, 2+n);
        wait_value(&spin_table[1].target, 0);
        assert(spin_table[1].retval > previous);
        previous = spin_table[1].retval;
        struct timespec ts = {.tv_nsec=10000000}; nanosleep(&ts, NULL);
    }
    atomic_store(&done, true);
    assert(!pthread_join(thread, NULL));
    assert(park_visits > 0 && spin_table[1].flag == 3);
    for (int i=0; i<MAX_CPUS; ++i) if (i != 1) assert(spin_table[i].flag == 0);
    puts("ACTUAL-SECONDARY-LOOP-PASS: CPU1 entry, two requests, idle loop; synthetic registers/WFE");
    return 0;
}
