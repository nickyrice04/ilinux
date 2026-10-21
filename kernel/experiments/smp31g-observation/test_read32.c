/* SPDX-License-Identifier: MIT */
#define _GNU_SOURCE
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <unistd.h>
extern uint64_t smp31g_read32(const volatile uint32_t *);
int main(void) {
    long page = sysconf(_SC_PAGESIZE);
    if (page < 4096) return 1;
    char *p = mmap(NULL, (size_t)page * 2, PROT_READ|PROT_WRITE,
                   MAP_PRIVATE|MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) return 2;
    if (mprotect(p+page, (size_t)page, PROT_NONE)) return 3;
    volatile uint32_t *v = (volatile uint32_t *)(p+page-4);
    const uint32_t cases[] = {0, 0xff, 0xffffffffU, 0x80000000U, 0x10000c0fU};
    for (size_t i=0; i<sizeof(cases)/sizeof(cases[0]); ++i) {
        *v=cases[i];
        if (smp31g_read32(v) != (uint64_t)cases[i]) return 4;
    }
    if (munmap(p,(size_t)page*2)) return 5;
    puts("READ32-WIDTH-AND-GUARD-PAGE-PASS");
    return 0;
}
