/* Original provider fixture, unrelated to Apple code. */
#include <stdint.h>
#include <stdio.h>

__attribute__((noinline)) uint32_t saturating_add_u32(uint32_t a, uint32_t b)
{
    uint32_t sum = a + b;
    return sum < a ? UINT32_MAX : sum;
}

int main(void)
{
    const uint32_t cases[][3] = {
        {0, 0, 0}, {1, 2, 3}, {UINT32_MAX, 0, UINT32_MAX},
        {UINT32_MAX, 1, UINT32_MAX}, {0x80000000u, 0x80000000u, UINT32_MAX}
    };
    for (unsigned i = 0; i < sizeof cases / sizeof cases[0]; ++i)
        if (saturating_add_u32(cases[i][0], cases[i][1]) != cases[i][2])
            return 1;
    puts("PASS: 5 saturating addition cases");
    return 0;
}
