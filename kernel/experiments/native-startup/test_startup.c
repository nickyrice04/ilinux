/* SPDX-License-Identifier: GPL-2.0-or-later
 * Original regression harness around the actual public m1n1 startup function.
 * No register access or CPU activation occurs. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>

typedef uint64_t u64;
typedef uint8_t u8;
#define MAX_CPUS 32
#define MAX_EL3_CPUS 16
#define SECONDARY_STACK_SIZE 256
#define DUMMY_STACK_SIZE 256
#define PMGR_DIE_OFFSET UINT64_C(0x2100000000)
#define RVBAR_ADDR UINT64_C(0x0000fffffffff000)
struct cpu_info { bool valid; u8 die, cluster, core; u64 impl_reg; };
struct spin_table { u64 mpidr, flag, target, args[4], retval; };
static struct spin_table spin_table[MAX_CPUS];
static struct { bool apple_sysregs_unlocked; } features, *cpu_features = &features;
static u8 secondary_stacks[MAX_CPUS][SECONDARY_STACK_SIZE];
static u8 secondary_stacks_el3[MAX_EL3_CPUS][SECONDARY_STACK_SIZE];
static u8 dummy_stack[DUMMY_STACK_SIZE], dummy_stack_el1[DUMMY_STACK_SIZE];
static _Alignas(4096) u8 _vectors_start[1];
static void *_reset_stack, *_reset_stack_el1;
static int target_cpu;
static u64 cpu_start_base = 0x500088000;
static bool el3, acknowledge = true;
static unsigned reads, writes32, writes64, delays, barriers;
static u64 reset_vector, addresses[2], values[2];
static char messages[1024];

static bool has_el3(void) { return el3; }
static u64 read64(u64 address)
{
    assert(address == 0x500000000);
    reads++;
    return reset_vector;
}
static void write64(u64 address, u64 value)
{
    assert(address == 0x500000000);
    assert(value == (u64)_vectors_start);
    writes64++;
}
static void write32(u64 address, uint32_t value)
{
    assert(writes32 < 2);
    addresses[writes32] = address;
    values[writes32++] = value;
    if (writes32 == 2 && acknowledge)
        spin_table[target_cpu].flag = 1;
}
static void udelay(unsigned usec) { assert(usec == 1000); delays++; }
#define sysop(op) ((void)(op), barriers++)
static int capture_printf(const char *fmt, ...)
{
    size_t used = strlen(messages);
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(messages + used, sizeof(messages) - used, fmt, ap);
    va_end(ap);
    return n;
}
#define printf capture_printf
#include "startup.inc"
#undef printf

int main(int argc, char **argv)
{
    assert(argc == 2);
    struct cpu_info cpu = {true, 1, 2, 3, 0x500000000};
    reset_vector = (u64)_vectors_start | 1;
    target_cpu = 31;
    _reset_stack = dummy_stack;
    _reset_stack_el1 = dummy_stack_el1;
    if (!strcmp(argv[1], "mismatch")) {
        reset_vector += 4096;
        spin_table[7].target = 0x1234;
        smp_start_cpu(7, &cpu);
        if (writes32 || writes64 || delays || barriers || reads != 1 || target_cpu != 31 ||
            spin_table[7].target != 0x1234 || _reset_stack != dummy_stack ||
            _reset_stack_el1 != dummy_stack_el1 || !strstr(messages, "Skipping CPU 7")) {
            fprintf(stderr, "FAIL mismatch: reads=%u writes32=%u writes64=%u waits=%u\n",
                    reads, writes32, writes64, delays);
            return 1;
        }
    } else if (!strcmp(argv[1], "already-started")) {
        spin_table[7].flag = 1;
        smp_start_cpu(7, &cpu);
        assert(!reads && !writes32 && !writes64 && !barriers);
    } else if (!strcmp(argv[1], "out-of-range")) {
        smp_start_cpu(MAX_CPUS, &cpu);
        assert(!reads && !writes32 && !writes64 && !barriers);
    } else if (!strcmp(argv[1], "el3-out-of-range")) {
        el3 = true;
        smp_start_cpu(MAX_EL3_CPUS, &cpu);
        assert(!reads && !writes32 && !writes64 && !barriers);
    } else {
        if (!strcmp(argv[1], "unlocked")) {
            features.apple_sysregs_unlocked = true;
            reset_vector += 4096;
        } else if (!strcmp(argv[1], "timeout")) {
            acknowledge = false;
        } else if (!strcmp(argv[1], "el3-match")) {
            el3 = true;
        } else {
            assert(!strcmp(argv[1], "match"));
        }
        smp_start_cpu(7, &cpu);
        assert(reads == (features.apple_sysregs_unlocked ? 0u : 1u));
        assert(writes64 == (features.apple_sysregs_unlocked ? 1u : 0u));
        assert(writes32 == 2);
        assert(addresses[0] == cpu_start_base + PMGR_DIE_OFFSET + 4);
        assert(addresses[1] == cpu_start_base + PMGR_DIE_OFFSET + 8 + 4 * cpu.cluster);
        assert(values[0] == (1u << (4 * cpu.cluster + cpu.core)));
        assert(values[1] == (1u << cpu.core));
        assert(delays == (acknowledge ? 0u : 100u));
        assert(strstr(messages, acknowledge ? "Started." : "Failed!"));
        assert(_reset_stack == dummy_stack + DUMMY_STACK_SIZE);
        assert(_reset_stack_el1 == dummy_stack_el1 + DUMMY_STACK_SIZE);
    }
    printf("PASS %s\n", argv[1]);
    return 0;
}
