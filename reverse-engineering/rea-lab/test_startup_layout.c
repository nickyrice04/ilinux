#include "startup_layout.h"
#include <assert.h>
#include <stdio.h>
#include <limits.h>

static void rejects(const struct ilinux_cluster_bits *layout, size_t n,
                    unsigned cluster, unsigned core)
{
    struct ilinux_startup_masks value = {123, 456};
    assert(ilinux_startup_masks(layout, n, cluster, core, &value) == -1);
    assert(value.global == 123 && value.local == 456);
}

int main(void)
{
    const struct ilinux_cluster_bits t6050[] = {{6, 0}, {6, 6}, {6, 12}};
    const struct ilinux_cluster_bits legacy[] = {{6, 0}, {6, 4}, {6, 8}};
    struct ilinux_startup_masks value;
    uint32_t seen = 0;
    for (unsigned cluster = 0; cluster < 3; ++cluster) {
        for (unsigned core = 0; core < 6; ++core) {
            assert(!ilinux_startup_masks(t6050, 3, cluster, core, &value));
            assert(value.global == (UINT32_C(1) << (cluster * 6 + core)));
            assert(value.local == (UINT32_C(1) << core));
            assert(!(seen & value.global));
            seen |= value.global;
        }
    }
    assert(seen == UINT32_C(0x3ffff));
    rejects(legacy, 3, 0, 0);
    rejects(t6050, 3, 3, 0);
    rejects(t6050, 3, 0, 6);
    rejects(t6050, 3, UINT_MAX, UINT_MAX);
    rejects(t6050, 0, 0, 0);
    rejects(NULL, 3, 0, 0);
    assert(ilinux_startup_masks(t6050, 3, 0, 0, NULL) == -1);
    for (unsigned first = 0; first < 32; ++first) {
        for (unsigned n = 1; n <= 32 - first; ++n) {
            struct ilinux_cluster_bits one[] = {{n, first}};
            for (unsigned core = 0; core < n; ++core) {
                assert(!ilinux_startup_masks(one, 1, 0, core, &value));
                assert(value.global == (UINT32_C(1) << (first + core)));
                assert(value.local == (UINT32_C(1) << core));
            }
            rejects(one, 1, 0, n);
        }
    }
    const struct ilinux_cluster_bits bad[][1] = {{{0, 0}}, {{33, 0}}, {{1, 32}}, {{2, 31}}, {{UINT_MAX, 1}}};
    for (size_t i = 0; i < sizeof bad / sizeof bad[0]; ++i)
        rejects(bad[i], 1, 0, 0);
    puts("PASS: 18-core uniqueness, legacy collision rejection, all 5984 valid single-cluster masks, bounds and no output on errors");
    return 0;
}
