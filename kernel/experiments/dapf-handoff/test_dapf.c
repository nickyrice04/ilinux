/* Synthetic-MMIO regression for actual pinned src/dapf.c. Never run on hardware. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint8_t u8;
typedef uint32_t u32;
typedef uint64_t u64;
#define PACKED __attribute__((packed))
static void *adt;
static uint32_t records[8 * 4];
static unsigned char config[56];
static unsigned instances_len, reg_len, config_len = 52, writes, bad_writes, getregs;
static bool metadata = true;
static int selected_reg = -1;
static int adt_path_offset_trace(void *a, const char *path, int *trace)
{ (void)a; (void)path; trace[0] = 0; return 0; }
static int adt_path_offset(void *a, const char *path)
{ (void)a; (void)path; return 0; }
static const void *adt_getprop(void *a, int node, const char *prop, u32 *len)
{
    (void)a; (void)node;
    if (!strcmp(prop, "instance") && metadata) { *len = instances_len; return records; }
    if (!strcmp(prop, "reg")) { *len = reg_len; return records; }
    if (!strcmp(prop, "dapf-instance-0")) { *len = config_len; return config; }
    return NULL;
}
static int pmgr_adt_power_enable(const char *path) { (void)path; assert(0); return -1; }
static void pmgr_adt_power_disable(const char *path) { (void)path; assert(0); }
static int adt_get_reg(void *a, int *trace, const char *prop, int index, u64 *base, u64 *size)
{
    (void)a; (void)trace; (void)prop; (void)size;
    getregs++;
    if (index < 0 || (unsigned)index >= reg_len / 16) return -1;
    selected_reg = index; *base = 0x10000000 + index * 0x10000; return 0;
}
static bool adt_is_compatible(void *a, int node, const char *compat)
{ (void)a; (void)node; return !strcmp(compat, "dart,t8110"); }
static void write32(u64 address, u32 value)
{
    (void)value;
    assert(selected_reg >= 0);
    assert(address >= 0x10000000 && address < 0x10080000);
    writes++;
    if (records[selected_reg * 4] != 0x44415046) bad_writes++;
}
static void write64(u64 address, u64 value) { write32(address, (u32)value); }
#include "tested-dapf.c"

static void reset(unsigned count)
{
    memset(records, 0, sizeof(records)); memset(config, 0, sizeof(config));
    for (unsigned i = 0; i < count; i++) records[4 * i] = 0x44415254;
    instances_len = reg_len = count * 16; metadata = true;
    writes = bad_writes = getregs = 0; config_len = 52; selected_reg = -1;
}
int main(int argc, char **argv)
{
    assert(argc == 2);
    reset(2); records[4] = 0x47415046;
    assert(dapf_init("/arm-io/dart-aop", 1) == 0);
    if (!strcmp(argv[1], "baseline")) {
        assert(writes == 5 && bad_writes == 5 && selected_reg == 1);
        puts("PASS: baseline attempts all five DAPF writes to GAPF in synthetic AOP layout");
        return 0;
    }
    assert(writes == 0 && getregs == 0);
    reset(3); records[4] = 0x44415046; records[8] = 0x47415046;
    assert(dapf_init("/arm-io/dart-mtp", 1) == 0);
    assert(writes == 5 && bad_writes == 0 && selected_reg == 1);
    reset(7); records[20] = 0x44415046; records[24] = 0x47415046;
    assert(dapf_init("/arm-io/dart-isp0", 5) == 0);
    assert(writes == 5 && bad_writes == 0 && selected_reg == 5);
    reset(3); records[8] = 0x44415046;
    assert(dapf_init("synthetic-moved", 1) == 0);
    assert(writes == 5 && bad_writes == 0 && selected_reg == 2);
    reset(2); records[4] = 0x44415046; metadata = false;
    assert(dapf_init("legacy-no-instance", 1) == 0);
    assert(writes == 5 && bad_writes == 0 && selected_reg == 1);
    reset(2); records[4] = 0x44415046; config_len = 56;
    assert(dapf_init("legacy-56-byte-config", 1) == 0);
    assert(writes == 5 && bad_writes == 0);
    reset(2); records[4] = 0x44415046; instances_len = 31;
    assert(dapf_init("malformed-instance", 1) == -1 && writes == 0 && getregs == 0);
    reset(2); records[4] = 0x44415046; reg_len = 48;
    assert(dapf_init("mismatched-count", 1) == -1 && writes == 0 && getregs == 0);
    reset(2); records[0] = records[4] = 0x44415046;
    assert(dapf_init("ambiguous-instance", 1) == -1 && writes == 0 && getregs == 0);
    reset(2); records[4] = 0x44415046; instances_len = 0;
    assert(dapf_init("empty-instance", 1) == -1 && writes == 0 && getregs == 0);
    reset(2); records[4] = 0x44415046; reg_len = 31;
    assert(dapf_init("malformed-reg", 1) == -1 && writes == 0 && getregs == 0);
    reset(2); records[4] = 0x44415046; records[5] = 1;
    assert(dapf_init("no-instance-zero", 1) == 0 && writes == 0 && getregs == 0);
    puts("PASS: 12 source-guard scenarios; GAPF untouched, valid/legacy DAPF preserved");
    return 0;
}
