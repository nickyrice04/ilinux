/* SPDX-License-Identifier: GPL-2.0-only */
/* Test harness for extracted Linux callbacks, not a hardware emulator. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <errno.h>
typedef uint64_t u64;
typedef uint32_t u32;
#define BIT(x) (1ULL << (x))
#define APPLE_DVFS_CMD 0x20
#define APPLE_DVFS_STATUS 0x50
#define APPLE_DVFS_CMD_BUSY BIT(31)
#define APPLE_DVFS_CMD_SET BIT(25)
#define APPLE_DVFS_CMD_PS1 31ULL
#define APPLE_DVFS_CMD_PS2 (15ULL << 12)
#define APPLE_DVFS_CMD_APSC_DIS_T6050 BIT(23)
#define APPLE_DVFS_CMD_APSC_BUSY_T6050 BIT(7)
#define APPLE_DVFS_TRANSITION_TIMEOUT 400
#define FIELD_GET(mask, x) (((x) & (mask)) >> __builtin_ctzll(mask))
#define FIELD_PREP(mask, x) (((u64)(x) << __builtin_ctzll(mask)) & (mask))
#define CPUFREQ_TABLE_END (~0U)
#define unlikely(x) (x)
#define dev_err(...) ((void)0)
struct cpufreq_frequency_table { unsigned int frequency, driver_data; };
struct apple_soc_cpufreq_info {
    bool has_ps2, ilinux_guarded;
    u64 max_pstate, cur_pstate_mask, cur_pstate_shift, ps1_mask, ps1_shift;
};
struct apple_cpu_priv { void *cpu_dev; unsigned char *reg_base; const struct apple_soc_cpufreq_info *info; };
struct cpufreq_policy { struct apple_cpu_priv *driver_data; struct cpufreq_frequency_table *freq_table; unsigned int cpu; };
static struct cpufreq_frequency_table freq[] = {{1344000, 2}, {1500000, 3}, {2000000, 4}, {CPUFREQ_TABLE_END, 0}};
static struct apple_soc_cpufreq_info info = {false, true, 31, 0, 0, 31, 0};
static unsigned char fake_mmio[256];
static struct apple_cpu_priv priv = {NULL, fake_mmio, &info};
static struct cpufreq_policy policy = {&priv, freq, 0};
static bool ilinux_enable_writes;
static unsigned int ilinux_max_pstate, online = 1, reads, writes, polls, fail_poll;
static bool bad_readback;
static u64 command, written;
static struct cpufreq_policy *cpufreq_cpu_get_raw(unsigned int cpu) { return cpu == 0 ? &policy : NULL; }
static unsigned int num_online_cpus(void) { return online; }
#define cpufreq_for_each_valid_entry(p, t) for ((p)=(t); (p)->frequency != CPUFREQ_TABLE_END; (p)++)
static u64 readq_relaxed(const void *address) {
    assert(address == fake_mmio + APPLE_DVFS_CMD);
    ++reads;
    return command;
}
static u32 readl_relaxed(const void *address) {
    /* Any STATUS access in the guarded tests is a failure. */
    assert(!info.ilinux_guarded && address == fake_mmio + APPLE_DVFS_STATUS);
    ++reads;
    return 2 << 5;
}
static void writeq_relaxed(u64 val, void *address) {
    assert(address == fake_mmio + APPLE_DVFS_CMD);
    ++writes;
    written = val;
    command = bad_readback ? ((val & ~31ULL) | 2) : val;
}
#define readq_poll_timeout_atomic(addr, val, condition, delay, timeout) \
    ({ ++polls; (val) = readq_relaxed(addr); (polls == fail_poll || !(condition)) ? -ETIMEDOUT : 0; })
/* ACTUAL_DRIVER_CALLBACKS */
static void reset(void) {
    ilinux_enable_writes = true; ilinux_max_pstate = 4;
    online = 1; policy.cpu = 0; freq[1].driver_data = 3;
    reads = writes = polls = fail_poll = 0; bad_readback = false;
    command = BIT(40) | (5ULL << 12) | 2; written = 0;
}
int main(void) {
    reset(); ilinux_enable_writes = false;
    assert(apple_soc_cpufreq_set_target(&policy, 1) == -EPERM && reads == 0 && writes == 0);
    reset(); online = 2;
    assert(apple_soc_cpufreq_set_target(&policy, 1) == -EPERM && writes == 0);
    reset(); policy.cpu = 1;
    assert(apple_soc_cpufreq_set_target(&policy, 1) == -EPERM && writes == 0);
    reset(); ilinux_max_pstate = 0;
    assert(apple_soc_cpufreq_set_target(&policy, 1) == -EINVAL && writes == 0);
    reset(); ilinux_max_pstate = 2;
    assert(apple_soc_cpufreq_set_target(&policy, 1) == -EINVAL && writes == 0);
    reset(); freq[1].driver_data = 1;
    assert(apple_soc_cpufreq_set_target(&policy, 1) == -EINVAL && writes == 0);
    reset(); freq[1].driver_data = 32;
    assert(apple_soc_cpufreq_set_target(&policy, 1) == -EINVAL && writes == 0);
    reset(); fail_poll = 1;
    assert(apple_soc_cpufreq_set_target(&policy, 1) == -EIO && writes == 0);
    reset(); command |= APPLE_DVFS_CMD_APSC_DIS_T6050;
    assert(apple_soc_cpufreq_set_target(&policy, 1) == -EBUSY && writes == 0);
    reset(); command |= APPLE_DVFS_CMD_APSC_BUSY_T6050;
    assert(apple_soc_cpufreq_set_target(&policy, 1) == -EBUSY && writes == 0);
    reset(); u64 before = command;
    assert(apple_soc_cpufreq_set_target(&policy, 1) == 0 && writes == 1 && polls == 2);
    assert(written == ((before & ~31ULL) | 3 | APPLE_DVFS_CMD_SET));
    reset(); fail_poll = 2;
    assert(apple_soc_cpufreq_set_target(&policy, 1) == -ETIMEDOUT && writes == 1);
    reset(); bad_readback = true;
    assert(apple_soc_cpufreq_set_target(&policy, 1) == -EIO && writes == 1);
    reset(); assert(apple_soc_cpufreq_get_rate(0) == 1344000 && reads == 1);
    reset(); command = 1;
    assert(apple_soc_cpufreq_get_rate(0) == 0 && reads == 1);
    reset(); assert(apple_soc_cpufreq_get_rate(1) == 0 && reads == 0);
    puts("PASS 16 extracted-callback cases: no default writes, cap/CPU/APSC gates, timeouts, exact RMW, command-only readback, no fabricated frequency");
    return 0;
}
