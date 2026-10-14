// SPDX-License-Identifier: GPL-2.0-only
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
extern uint64_t ilinux_fb_descriptor[2];
extern uint64_t probe0(uint64_t, uint64_t, uint64_t, uint64_t);
extern uint64_t probe1(uint64_t, uint64_t, uint64_t, uint64_t);
extern uint64_t probe2(uint64_t, uint64_t, uint64_t, uint64_t);
static uint32_t pixels[128][512];
int main(void)
{
	uint64_t (*probes[])(uint64_t, uint64_t, uint64_t, uint64_t) = {probe0, probe1, probe2};
	for (int i = 0; i < 3; i++) {
		// Zero descriptor is safe on generic VM boot and preserves boot arguments.
		assert(probes[i](0x12345678, 0x98765432, 0x5555, 0xaaa) ==
		       (0x12345678 ^ 0x98765432 ^ 0x5555 ^ 0xaaa));
	}
	ilinux_fb_descriptor[0] = (uintptr_t)pixels;
	ilinux_fb_descriptor[1] = sizeof(pixels[0]);
	for (int i = 0; i < 3; i++) {
		memset(pixels, 0x55, sizeof(pixels));
		assert(probes[i](1, 2, 4, 8) == 15);
		for (int y = 0; y < 128; y++)
			for (int x = 0; x < 512; x++) {
				int in = y >= 16 && y < 48 && x >= 16 + i * 80 && x < 80 + i * 80;
				assert(pixels[y][x] == (in ? UINT32_MAX : 0x55555555));
			}
	}
	puts("PASS: actual AArch64 macros, zero-descriptor no-op, x0-x3 preservation, exact three rectangles");
}
