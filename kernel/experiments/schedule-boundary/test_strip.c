/* Actual renderer, guarded RAM and synthetic fonts; no display hardware. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint8_t u8;
typedef uint32_t u32;
typedef uint64_t u64;
#define U32_MAX UINT32_MAX
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,v) ((x)=(v))
#define DIV_ROUND_UP(a,b) (((a)+(b)-1)/(b))
struct font_desc { unsigned int width, height; const unsigned char *data; };
static const struct font_desc *fb_font;
static void *fb_mapping;
static bool mapping_failed;
static u32 fb_width, fb_height, fb_stride;
bool ilinux_probe_diag;
#include "status-strip.h"

static void run(unsigned int w, unsigned int h)
{
    unsigned char font[256 * 64 * 4];
    struct font_desc f = { w, h, font };
    const u32 sentinel = 0x12345678;
    fb_font = &f; fb_width = 640; fb_height = 200; fb_stride = 2592;
    size_t words = (size_t)fb_stride / 4 * fb_height;
    u32 *ram = malloc((words + 2) * sizeof(*ram)); assert(ram);
    fb_mapping = ram + 1;
    memset(font, 0xa5, sizeof(font));
    for (unsigned int lane = 0; lane < 4; lane++) {
        for (size_t i = 0; i < words + 2; i++) ram[i] = sentinel;
        assert(ilinux_probe_fb_mark(lane, 255));
        assert(ram[0] == sentinel && ram[words+1] == sentinel);
        for (u32 y = 0; y < fb_height; y++) for (u32 x = 0; x < fb_stride/4; x++) {
            bool written = y >= fb_height-h && x >= lane*5*w && x < lane*5*w+4*w;
            u32 v = ram[1 + (size_t)y*(fb_stride/4) + x];
            assert(written ? (v == 0 || v == U32_MAX) : v == sentinel);
        }
    }
    assert(!ilinux_probe_fb_mark(4, 1)); assert(!ilinux_probe_fb_mark(0, 256));
    fb_width = 20*w-1; assert(!ilinux_probe_fb_mark(0, 0)); fb_width = 640;
    fb_height = 2*h-1; assert(!ilinux_probe_fb_mark(0, 0)); fb_height = 200;
    mapping_failed = true; assert(!ilinux_probe_fb_mark(0, 0)); mapping_failed = false;
    ilinux_probe_diag = false; assert(!ilinux_probe_fb_mark(0, 0)); ilinux_probe_diag = true;
    fb_font = NULL; assert(!ilinux_probe_fb_mark(0, 0)); fb_font = &f;
    fb_mapping = NULL; assert(!ilinux_probe_fb_mark(0, 0));
    free(ram);
}
int main(void)
{
    ilinux_probe_diag = true;
    fb_text_height = 0; assert(!fb_text_height);
    run(8,16); run(32,64); run(1,1);
    puts("PASS: actual strip renderer, three font geometries, four lanes, guards and rejected inputs");
}
