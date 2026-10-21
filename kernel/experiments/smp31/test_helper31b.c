/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Execute actual linked RAM-only helper entries in the ARM64 Linux VM.
 * Privileged register reads are instruction-audited, not executed at EL0. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
extern char helper31b[];
int main(void) {
    uint64_t (*read_word)(const uint64_t *) = (void *)(helper31b + 96);
    uint64_t (*or_words)(const uint64_t *, uint64_t) = (void *)(helper31b + 112);
    uint64_t (*publish)(uint64_t *, uint64_t) = (void *)(helper31b + 160);
    uint64_t words[256] = {0}, slot = 0;
    words[0]=1; words[239]=0x8000; words[255]=0x800000;
    assert(read_word(&words[239]) == 0x8000);
    assert(or_words(words, 240) == 0x8001);
    assert(or_words(words, 256) == 0x808001);
    assert(or_words(NULL, 0) == 0);
    assert(or_words(NULL, 257) == UINT64_MAX);
    assert(or_words(NULL, UINT64_MAX) == UINT64_MAX);
    assert(publish(&slot, 0x314159) == 0x31b && slot == 0x314159);
    puts("ACTUAL-ARM64-HELPER-PASS: aligned read, bounded scan, RAM publication/event");
    return 0;
}
