/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Actual patched functions, synthetic MMIO. Run only in the VM. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "layout31.h"
typedef uint64_t u64;
typedef uint32_t u32;
typedef uint8_t u8;
#define T6050 0x6050
#define MAX_CPUS 32
#define MAX_EL3_CPUS 16
#define SECONDARY_STACK_SIZE 256
#define DUMMY_STACK_SIZE 256
#define PMGR_DIE_OFFSET 0x2100000000ULL
#define RVBAR_ADDR UINT64_C(0x0000fffffffff000)
#define RVBAR_LOCK 1
struct cpu_info { bool valid; u8 die, cluster, core; u64 impl_reg; };
struct spin_table { u64 mpidr, flag, target, args[4], retval; };
static struct cpu_info cpu_info[32];
static struct spin_table spin_table[32];
static struct { bool apple_sysregs_unlocked; } features, *cpu_features = &features;
static u8 secondary_stacks[32][256], secondary_stacks_el3[16][256];
static u8 dummy_stack[256], dummy_stack_el1[256];
static _Alignas(4096) u8 _vectors_start[1];
static void *_reset_stack, *_reset_stack_el1;
static int target_cpu, chip_id = T6050, boot_cpu_idx;
static u64 boot_cpu_mpidr = 0x40000, cpu_start_base = 0x280688000ULL;
static unsigned short smp31_desc[] = {6, 0, 6, 6, 6, 12};
static bool smp31_attempted, smp_initialized = true, ack = true, wfe;
static u64 primary_rvbar, secondary_rvbar, writes[2][2];
static unsigned nwrite, nread, delays;
static bool has_el3(void) { return false; }
static u64 read64(u64 address) {
    nread++;
    assert(address == 0x210050000ULL || address == 0x210150000ULL);
    return address == 0x210050000ULL ? primary_rvbar : secondary_rvbar;
}
static void write64(u64 a, u64 b) { (void)a; (void)b; assert(0); }
static void write32(u64 a, u32 b) {
    assert(wfe && nwrite < 2);
    writes[nwrite][0] = a; writes[nwrite++][1] = b;
    if (nwrite == 2 && ack) {
        spin_table[target_cpu].flag = 1;
        spin_table[target_cpu].mpidr = 0x40001;
    }
}
static void udelay(unsigned us) { assert(us == 1000); delays++; }
static void smp_set_wfe_mode(bool enable) { assert(enable); wfe = enable; }
#define sysop(op) ((void)(op))
/* Extracted from the actual candidate, not a Python reimplementation. */
#include "startup.inc"
int main(int argc, char **argv) {
    assert(argc == 2);
    cpu_info[0] = (struct cpu_info){true, 0, 0, 0, 0x210050000ULL};
    cpu_info[1] = (struct cpu_info){true, 0, 0, 1, 0x210150000ULL};
    primary_rvbar = secondary_rvbar = (u64)_vectors_start | 1;
    const char *test = argv[1];
    if (!strcmp(test, "bad-chip")) chip_id = 0x6051;
    else if (!strcmp(test, "bad-layout")) smp31_desc[3] = 4;
    else if (!strcmp(test, "bad-core")) cpu_info[1].core = 2;
    else if (!strcmp(test, "bad-impl")) cpu_info[1].impl_reg += 8;
    else if (!strcmp(test, "bad-primary-impl")) cpu_info[0].impl_reg += 8;
    else if (!strcmp(test, "bad-start-base")) cpu_start_base += 4;
    else if (!strcmp(test, "unlocked")) features.apple_sysregs_unlocked = true;
    else if (!strcmp(test, "primary-mismatch")) primary_rvbar += 4096;
    else if (!strcmp(test, "secondary-mismatch")) secondary_rvbar += 4096;
    else if (!strcmp(test, "lock-clear")) secondary_rvbar &= ~1ULL;
    else if (!strcmp(test, "already-alive")) spin_table[2].flag = 1;
    else if (!strcmp(test, "retry")) smp31_attempted = true;
    else if (!strcmp(test, "timeout")) ack = false;
    else assert(!strcmp(test, "match"));
    int rc = smp31_start_one();
    if (!strcmp(test, "match") || !strcmp(test, "timeout")) {
        assert(nread == 2 && nwrite == 2);
        assert(writes[0][0] == 0x280688004ULL && writes[0][1] == 2);
        assert(writes[1][0] == 0x280688008ULL && writes[1][1] == 2);
        assert(delays == (ack ? 0 : 100));
        assert(rc == (ack ? 0 : -5));
        if (!ack) assert(_reset_stack == secondary_stacks[1] + 256);
        assert(smp31_start_one() == -1 && nwrite == 2);
    } else {
        assert(rc < 0 && nwrite == 0 && delays == 0);
        assert(!_reset_stack && !spin_table[1].flag);
    }
    // Actual layout helper across every core, with malformed-input refusal.
    unsigned short good[] = {6,0,6,6,6,12};
    unsigned masks = 0;
    for (unsigned c = 0; c < 3; c++) for (unsigned k = 0; k < 6; k++) {
        unsigned bit = smp31_mask(good, sizeof(good), c, k);
        assert(bit && !(masks & bit)); masks |= bit;
    }
    assert(masks == 0x3ffff && !smp31_mask(good, 10, 0, 0));
    assert(!smp31_mask(good, 12, 3, 0) && !smp31_mask(good, 12, 0, 6));
    good[3] = 4; assert(!smp31_mask(good, 12, 0, 0));
    printf("PASS %s\n", test);
}
