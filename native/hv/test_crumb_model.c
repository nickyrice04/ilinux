/*
 * Offline model test for the hv003 early-boot framebuffer breadcrumbs
 * (private iLinux).
 *
 * test_crumb.py extracts the exact block between ILINUX-CRUMB-BEGIN and
 * ILINUX-CRUMB-END that 0002-ilinux-hv-t6050-hv003-crumbs.patch adds to
 * src/startup.c into crumb_block.inc and compiles this harness around it with
 * ASan/UBSan. Every fake framebuffer is allocated with exactly stride * height
 * bytes, so any store past the end of the framebuffer is an ASan error, and
 * the whole buffer is compared word by word against the contract:
 *
 *   BLOCK = 24 pixels square, PITCH = 28, ORIGIN_X = 8, ORIGIN_Y = 4,
 *   SLOTS = 21, COLOR = 0xFFFFFFFF, 4 bytes per pixel, depth & 0xff in {30, 32}.
 *   pixel address = base + (4 + row) * stride + (8 + slot * 28 + col) * 4
 *
 * The MMU is a switch (mmu_active), mmu_add_mapping is a recorder that also
 * rejects what the real mmu_map() would reject, and sysop() records the dsb
 * together with how much of the block was already stored when it ran.
 */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef uint8_t u8;
typedef uint32_t u32;
typedef uint64_t u64;

#define BIT(n)  (1ULL << (n))
#define PTE_PXN BIT(53)
#define PTE_UXN BIT(54)
/* Unparenthesised, exactly as in src/memory.h. */
#define PERM_RW            PTE_PXN | PTE_UXN
#define MAIR_IDX_NORMAL_NC 1
#define ALIGN_UP(x, a)     (((x) + ((a) - 1)) & ~((a) - 1))

struct boot_video {
    u64 base;
    u64 display;
    u64 stride;
    u64 width;
    u64 height;
    u64 depth;
};

struct boot_args {
    struct boot_video video;
};

static struct boot_args cur_boot_args;

static int failures;
#define CHECK(c)                                                                                   \
    do {                                                                                           \
        if (!(c)) {                                                                                \
            printf("FAIL line %d: %s\n", __LINE__, #c);                                            \
            failures++;                                                                            \
        }                                                                                          \
    } while (0)

/* ---- fake hardware ------------------------------------------------------ */

static bool mmu_on;
static u32 *watch_buf;
static size_t watch_words;

static size_t lit_words(void)
{
    size_t n = 0;
    for (size_t i = 0; watch_buf && i < watch_words; i++)
        n += watch_buf[i] == 0xffffffffu;
    return n;
}

static bool mmu_active(void)
{
    return mmu_on;
}

struct map_call {
    u64 from, to;
    size_t size;
    u8 attr;
    u64 perms;
    bool mmu;
    size_t lit; /* framebuffer words already lit when the call came */
    int dsbs;
};

#define MAX_MAPS 16
static struct map_call maps[MAX_MAPS];
static int nmaps;

static void mmu_add_mapping(u64 from, u64 to, size_t size, u8 attr, u64 perms)
{
    /* The real mmu_map() returns -1 (and mmu_add_mapping panics) for these. */
    if ((from & 0x3fff) || (size & 0x3fff)) {
        printf("FAIL: mmu_add_mapping(0x%llx, size 0x%zx) would panic\n", (unsigned long long)from,
               size);
        failures++;
    }
    if (nmaps < MAX_MAPS)
        maps[nmaps] = (struct map_call){from, to, size, attr, perms, mmu_on, lit_words(), 0};
    nmaps++;
}

static int ndsb;
static size_t lit_at_last_dsb;

static void model_sysop(const char *op)
{
    if (strcmp(op, "dsb sy") != 0) {
        printf("FAIL: unexpected sysop \"%s\"\n", op);
        failures++;
        return;
    }
    ndsb++;
    lit_at_last_dsb = lit_words();
}
#define sysop(op) model_sysop(op)

#include "crumb_block.inc"

/* ---- framebuffer under test --------------------------------------------- */

#define BLOCK_WORDS (24 * 24)
#define SLOTS       21

struct fb {
    void *raw;
    u32 *words;
    size_t nwords;
    struct boot_video v;
};

static u32 pattern(size_t i)
{
    return 0x01000000u + (u32)i; /* never 0xffffffff, unique per word */
}

static struct fb fb_new(u64 width, u64 height, u64 stride, u64 depth)
{
    struct fb f;
    size_t size = (size_t)(stride * height);
    void *p = NULL;

    if (posix_memalign(&p, 0x4000, size)) {
        printf("allocation failed\n");
        exit(2);
    }
    f.raw = p;
    f.words = p;
    f.nwords = size / 4;
    for (size_t i = 0; i < f.nwords; i++)
        f.words[i] = pattern(i);
    f.v = (struct boot_video){.base = (u64)(uintptr_t)p,
                              .display = 0,
                              .stride = stride,
                              .width = width,
                              .height = height,
                              .depth = depth};
    return f;
}

static void fb_free(struct fb *f)
{
    free(f->raw);
    f->raw = NULL;
}

static void watch(struct fb *f)
{
    watch_buf = f->words;
    watch_words = f->nwords;
}

static void reset_model(u32 initial_state)
{
    mmu_on = false;
    nmaps = 0;
    ndsb = 0;
    lit_at_last_dsb = 0;
    ilinux_crumb_state = initial_state;
    watch_buf = NULL;
    watch_words = 0;
}

static bool expected_lit(u64 y, u64 x, u32 mask)
{
    if (y < 4 || y >= 4 + 24 || x < 8)
        return false;
    u64 slot = (x - 8) / 28;
    return slot < SLOTS && (x - 8) % 28 < 24 && ((mask >> slot) & 1);
}

/*
 * Whole-buffer comparison: lit exactly in the blocks of `mask`, untouched
 * elsewhere. `stride` is the one the painter was given (bytes).
 */
static int verify_at(const struct fb *f, size_t off, u64 stride, u32 mask, const char *what)
{
    int bad = 0;
    u64 words_per_row = stride / 4;

    for (size_t i = 0; i < f->nwords; i++) {
        bool lit = false;
        if (words_per_row && i >= off)
            lit = expected_lit((i - off) / words_per_row, (i - off) % words_per_row, mask);
        u32 want = lit ? 0xffffffffu : pattern(i);
        if (f->words[i] != want) {
            if (bad < 4)
                printf("FAIL %s: word %zu = 0x%08x, want 0x%08x\n", what, i, f->words[i], want);
            bad++;
        }
    }
    if (bad) {
        printf("FAIL %s: %d wrong words\n", what, bad);
        failures++;
    }
    return bad;
}

static int verify_stride(const struct fb *f, u64 stride, u32 mask, const char *what)
{
    return verify_at(f, 0, stride, mask, what);
}

static int verify(const struct fb *f, u32 mask, const char *what)
{
    return verify_at(f, 0, f->v.stride, mask, what);
}

/* ---- tests -------------------------------------------------------------- */

static u32 g_initial_state;

/* Minimal geometry: the last block row is the last framebuffer row. */
#define MIN_W      596
#define MIN_H      28
#define MIN_STRIDE 2384

static void test_placement(void)
{
    static const struct {
        u64 w, h, stride, depth;
    } geoms[] = {
        {MIN_W, MIN_H, MIN_STRIDE, 32},
        {MIN_W, MIN_H, MIN_STRIDE, 30},
        {600, 40, 2560, 32},               /* stride != width * 4 */
        {640, 1136, 2560, 30},             /* the dummy framebuffer m1n1 knows */
        {3456, 2234, 13824, 30 | 0x10000}, /* 16" panel, retina flag in depth */
        {3456, 2234, 13824 + 64, 32},
    };
    static const unsigned slots[] = {0, 1, 2, 4, 5, 9, 10, 19, 20};
    static const unsigned few[] = {0, 5, 20}; /* large framebuffers: keep the run short */

    for (size_t g = 0; g < sizeof(geoms) / sizeof(geoms[0]); g++) {
        bool big = geoms[g].h > 1000;
        size_t n = big ? sizeof(few) / sizeof(few[0]) : sizeof(slots) / sizeof(slots[0]);

        for (size_t s = 0; s < n; s++) {
            struct fb f = fb_new(geoms[g].w, geoms[g].h, geoms[g].stride, geoms[g].depth);
            unsigned slot = big ? few[s] : slots[s];
            char what[96];

            reset_model(g_initial_state);
            watch(&f);
            ilinux_crumb(&f.v, slot);
            snprintf(what, sizeof(what), "placement geom %zu slot %u", g, slot);
            verify(&f, 1u << slot, what);
            CHECK(ndsb == 1);
            CHECK(lit_at_last_dsb == BLOCK_WORDS); /* dsb after the last store */
            CHECK(nmaps == 0);                     /* MMU off: never map */
            fb_free(&f);
        }
    }
}

static void test_all_slots(void)
{
    struct fb f = fb_new(MIN_W, MIN_H, MIN_STRIDE, 32);

    reset_model(g_initial_state);
    watch(&f);
    for (unsigned s = 0; s < SLOTS; s++)
        ilinux_crumb(&f.v, s);
    verify(&f, (1u << SLOTS) - 1, "all 21 slots");
    CHECK(lit_words() == (size_t)SLOTS * BLOCK_WORDS);
    CHECK(ndsb == SLOTS && nmaps == 0);

    /* Painting again changes nothing. */
    for (unsigned s = 0; s < SLOTS; s++)
        ilinux_crumb(&f.v, s);
    verify(&f, (1u << SLOTS) - 1, "all 21 slots repainted");
    fb_free(&f);
}

/* One guard case: nothing may be stored, mapped or synchronised. */
static void expect_skipped(struct fb *f, struct boot_video v, unsigned slot, bool mmu,
                           const char *what)
{
    reset_model(g_initial_state);
    watch(f);
    mmu_on = mmu;
    ilinux_crumb(&v, slot);
    verify_stride(f, v.stride, 0, what);
    CHECK(ndsb == 0);
    CHECK(nmaps == 0);
}

static void expect_painted(struct fb *f, struct boot_video v, unsigned slot, const char *what)
{
    reset_model(g_initial_state);
    watch(f);
    ilinux_crumb(&v, slot);
    verify_stride(f, v.stride, 1u << slot, what);
    CHECK(ndsb == 1);
}

static void restore(struct fb *f)
{
    for (size_t i = 0; i < f->nwords; i++)
        f->words[i] = pattern(i);
}

static void test_guards(void)
{
    struct fb f = fb_new(MIN_W + 4, MIN_H + 2, MIN_STRIDE + 16, 32);
    struct boot_video ok = f.v;
    struct boot_video v;

    expect_painted(&f, ok, 7, "baseline geometry");
    restore(&f);

    v = ok;
    v.base = 0;
    expect_skipped(&f, v, 7, false, "base 0");
    for (u64 off = 1; off < 4; off++) {
        v = ok;
        v.base += off;
        expect_skipped(&f, v, 7, false, "misaligned base");
    }
    /* A base that is merely 4-aligned is painted (the contract only needs 4). */
    v = ok;
    v.base += 4;
    v.stride = MIN_STRIDE + 8;
    v.height = MIN_H;
    reset_model(g_initial_state);
    watch(&f);
    ilinux_crumb(&v, 7);
    verify_at(&f, 1, v.stride, 1u << 7, "base only 4-aligned");
    CHECK(ndsb == 1);
    restore(&f);

    static const u64 bad_depths[] = {0, 8, 16, 24, 31, 33, 64, 0x10000, 0x10000 | 24, 0x1ffff00};
    for (size_t i = 0; i < sizeof(bad_depths) / sizeof(bad_depths[0]); i++) {
        v = ok;
        v.depth = bad_depths[i];
        expect_skipped(&f, v, 7, false, "bad depth");
    }
    static const u64 good_depths[] = {30, 32, 0x10000 | 30, 0x10000 | 32, 0xffffff00 | 30};
    for (size_t i = 0; i < sizeof(good_depths) / sizeof(good_depths[0]); i++) {
        v = ok;
        v.depth = good_depths[i];
        expect_painted(&f, v, 7, "good depth");
        restore(&f);
    }

    v = ok;
    v.width = MIN_W - 1;
    expect_skipped(&f, v, 7, false, "narrow width");
    v.width = 0;
    expect_skipped(&f, v, 7, false, "zero width");
    v = ok;
    v.width = MIN_W;
    expect_painted(&f, v, 7, "width exactly 596");
    restore(&f);

    v = ok;
    v.height = MIN_H - 1;
    expect_skipped(&f, v, 7, false, "short height");
    v.height = 4;
    expect_skipped(&f, v, 7, false, "tiny height");
    v.height = 0;
    expect_skipped(&f, v, 7, false, "zero height");
    v = ok;
    v.height = MIN_H;
    expect_painted(&f, v, 7, "height exactly 28");
    restore(&f);

    v = ok;
    v.stride = MIN_STRIDE - 4;
    expect_skipped(&f, v, 7, false, "small stride");
    v.stride = 0;
    expect_skipped(&f, v, 7, false, "zero stride");
    v = ok;
    v.stride = MIN_STRIDE;
    expect_painted(&f, v, 7, "stride exactly 2384");
    restore(&f);

    /* c0..c8 store 4-byte words with the MMU off: a stride that is not a multiple of 4
     * would give unaligned Device stores (alignment fault). Refuse it. */
    for (u64 add = 1; add < 4; add++) {
        v = ok;
        v.stride = MIN_STRIDE + add;
        expect_skipped(&f, v, 7, false, "stride not a multiple of 4");
    }
    v = ok;
    v.stride = MIN_STRIDE + 4;
    expect_painted(&f, v, 7, "stride 4 mod 8 is fine for 4-byte stores");
    restore(&f);

    static const unsigned bad_slots[] = {21, 22, 31, 255, 0xffffffffu};
    for (size_t i = 0; i < sizeof(bad_slots) / sizeof(bad_slots[0]); i++)
        expect_skipped(&f, ok, bad_slots[i], false, "slot >= SLOTS");
    expect_painted(&f, ok, 20, "slot 20");
    restore(&f);
    expect_painted(&f, ok, 0, "slot 0");
    restore(&f);

    /* Realistic upper bounds: stride 0x10000 and height 0x4000 are accepted, beyond refused. */
    {
        struct fb big = fb_new(MIN_W, MIN_H, 0x10000, 30);
        struct boot_video bv = big.v;
        expect_painted(&big, bv, 7, "stride exactly 0x10000");
        fb_free(&big);
        struct fb tall = fb_new(MIN_W, 0x4000, MIN_STRIDE, 30);
        bv = tall.v;
        expect_painted(&tall, bv, 7, "height exactly 0x4000");
        fb_free(&tall);
        v = ok;
        v.stride = 0x10004;
        expect_skipped(&f, v, 7, false, "stride above 0x10000");
        v = ok;
        v.height = 0x4001;
        expect_skipped(&f, v, 7, false, "height above 0x4000");
    }

    /* Garbage boot_args: nothing may wrap into a wild store. */
    static const struct boot_video wild[] = {
        {~0ULL - 0xfff, 0, 0x10000000, 3456, 2234, 30},
        {0x10000000000ULL, 0, 0x4000000000000000ULL, 3456, 2234, 30},
        {0x10000000000ULL, 0, 13824, 3456, 0x4000000000000000ULL, 30},
        {0x10000000000ULL, 0, 0xffffffffffffff00ULL, ~0ULL, ~0ULL, 30},
        {~0ULL - 3, 0, 13824, 3456, 2234, 32},
        {~0ULL - 0xffffff, 0, 13824, 3456, 2234, 32},
    };
    for (size_t i = 0; i < sizeof(wild) / sizeof(wild[0]); i++)
        for (int m = 0; m < 2; m++) {
            reset_model(g_initial_state);
            mmu_on = m;
            ilinux_crumb(&wild[i], 20);
            ilinux_crumb(&wild[i], 0);
            CHECK(ndsb == 0 && nmaps == 0);
        }

    /* The skip rules apply with the MMU on and a mapped framebuffer too. */
    v = ok;
    v.depth = 24;
    expect_skipped(&f, v, 7, true, "depth 24 with MMU on");
    fb_free(&f);
}

static void test_mapping_sequence(void)
{
    /* 596x28 at stride 2384: 66752 bytes, not a multiple of 16K. */
    struct fb f = fb_new(MIN_W, MIN_H, MIN_STRIDE, 30);
    struct boot_args raw = {f.v};

    reset_model(g_initial_state);
    watch(&f);
    cur_boot_args = raw;

    /* c0 runs on the raw boot_args pointer, before the copy. */
    ilinux_crumb(&raw.video, 5);
    for (unsigned step = 1; step <= 8; step++)
        ilinux_crumb_step(step);
    CHECK(nmaps == 0);
    CHECK(lit_words() == 9 * BLOCK_WORDS);

    mmu_on = true; /* mmu_init() ran */
    ilinux_crumb_step(9);
    CHECK(nmaps == 1);
    CHECK(maps[0].mmu);
    CHECK(maps[0].from == f.v.base && maps[0].to == f.v.base);
    CHECK(maps[0].size == ALIGN_UP((size_t)MIN_STRIDE * MIN_H, 0x4000) && maps[0].size == 0x14000);
    CHECK(maps[0].attr == MAIR_IDX_NORMAL_NC);
    CHECK(maps[0].perms == (PTE_PXN | PTE_UXN));
    CHECK(maps[0].lit == 9 * BLOCK_WORDS); /* mapped before the first MMU-on store */
    CHECK(lit_words() == 10 * BLOCK_WORDS);
    CHECK(ndsb == 10);

    for (unsigned step = 10; step <= 15; step++)
        ilinux_crumb_step(step);
    CHECK(nmaps == 1); /* once, not per call */
    verify(&f, 0x1fffe0, "steps c0..c15 are slots 5..20");

    /* Warm re-entry of m1n1_main(): the MMU goes off, then on with fresh tables. */
    mmu_on = false;
    ilinux_crumb_step(6);
    CHECK(nmaps == 1);
    mmu_on = true;
    ilinux_crumb_step(9);
    ilinux_crumb_step(10);
    CHECK(nmaps == 2);
    CHECK(maps[1].from == f.v.base && maps[1].mmu);
    fb_free(&f);
}

static void test_foreign_and_garbage_state(void)
{
    struct fb f = fb_new(MIN_W, MIN_H, MIN_STRIDE, 32);

    /* MMU already on at the first call: the page tables are not ours. */
    reset_model(g_initial_state);
    watch(&f);
    mmu_on = true;
    for (unsigned s = 5; s < 21; s++)
        ilinux_crumb(&f.v, s);
    verify(&f, 0, "foreign MMU: no stores");
    CHECK(nmaps == 0 && ndsb == 0);
    /* Seeing it off arms the mapping, exactly one call maps. */
    mmu_on = false;
    ilinux_crumb(&f.v, 5);
    mmu_on = true;
    ilinux_crumb(&f.v, 14);
    ilinux_crumb(&f.v, 15);
    CHECK(nmaps == 1);
    verify(&f, (1u << 5) | (1u << 14) | (1u << 15), "after arming");
    restore(&f);

    /* Not-yet-initialised memory (.bss before the clear): only ARMED can map. */
    static const u32 junk[] = {0, 1, 0xffffffffu, 0xdeadbeefu, 0x43524d00u, 0x43524d33u};
    for (size_t i = 0; i < sizeof(junk) / sizeof(junk[0]); i++) {
        reset_model(junk[i]);
        watch(&f);
        mmu_on = true;
        ilinux_crumb(&f.v, 14);
        verify(&f, 0, "junk state, MMU on");
        CHECK(nmaps == 0 && ndsb == 0);
        /* With the MMU off the same junk is harmless: c0 paints. */
        reset_model(junk[i]);
        watch(&f);
        ilinux_crumb(&f.v, 5);
        verify(&f, 1u << 5, "junk state, MMU off");
        CHECK(nmaps == 0 && ndsb == 1);
        restore(&f);
    }

    /* The state is nonzero in the image: .data, so the bss clear cannot move it. */
    CHECK(g_initial_state != 0);
    fb_free(&f);
}

static void test_arming_does_not_need_a_valid_geometry(void)
{
    /*
     * display_init() may change cur_boot_args.video after the MMU is on. Calls
     * made earlier with a geometry that is refused must still count as having
     * seen the MMU off, or the framebuffer would never be mapped.
     */
    struct fb f = fb_new(MIN_W, MIN_H, MIN_STRIDE, 32);
    struct boot_video v = f.v;

    v.depth = 24;
    reset_model(g_initial_state);
    watch(&f);
    for (unsigned s = 5; s <= 13; s++)
        ilinux_crumb(&v, s);
    CHECK(lit_words() == 0 && ndsb == 0);
    mmu_on = true;
    v.depth = 30;
    ilinux_crumb(&v, 14);
    CHECK(nmaps == 1);
    verify(&f, 1u << 14, "mapped and painted once the geometry is valid");
    fb_free(&f);
}

static void test_unmappable_base(void)
{
    /* MMU on, armed, framebuffer not 16K aligned: no mapping call, no store. */
    struct fb f = fb_new(MIN_W, MIN_H + 4, MIN_STRIDE, 32);
    struct boot_video v = f.v;

    v.base += 0x1000;
    v.height = MIN_H;
    reset_model(g_initial_state);
    watch(&f);
    ilinux_crumb(&v, 5); /* MMU off: arms */
    mmu_on = true;
    ilinux_crumb(&v, 14);
    CHECK(nmaps == 0 && ndsb == 1);
    CHECK(lit_words() == BLOCK_WORDS); /* only the MMU-off c0 block */
    fb_free(&f);
}

static void test_steps_and_shadow(void)
{
    struct fb f = fb_new(MIN_W, MIN_H, MIN_STRIDE, 32);
    struct fb sh = fb_new(MIN_W, MIN_H, MIN_STRIDE, 32);

    reset_model(g_initial_state);
    watch(&f);
    cur_boot_args.video = f.v;

    ilinux_crumb_step(0);
    verify(&f, 1u << 5, "step 0 is slot 5");
    restore(&f);
    ilinux_crumb_step(15);
    verify(&f, 1u << 20, "step 15 is slot 20");
    restore(&f);
    ilinux_crumb_step(16);
    ilinux_crumb_step(0xffffffffu);
    verify(&f, 0, "steps >= 16 ignored");

    /* The shadow copy: same geometry, no MMU, no mapping, no dsb. */
    ndsb = 0;
    nmaps = 0;
    mmu_on = true;
    ilinux_crumb_shadow_step(15, sh.words);
    verify(&sh, 1u << 20, "shadow step 15");
    verify(&f, 0, "shadow does not touch the hardware buffer");
    CHECK(ndsb == 0 && nmaps == 0);
    restore(&sh);
    ilinux_crumb_shadow(&f.v, sh.words, 0);
    verify(&sh, 1u, "shadow slot 0");
    restore(&sh);
    ilinux_crumb_shadow_step(16, sh.words);
    ilinux_crumb_shadow(&f.v, NULL, 3);
    struct boot_video bad = f.v;
    bad.depth = 24;
    ilinux_crumb_shadow(&bad, sh.words, 3);
    bad = f.v;
    bad.width = MIN_W - 1;
    ilinux_crumb_shadow(&bad, sh.words, 3);
    ilinux_crumb_shadow(&f.v, sh.words, 21);
    verify(&sh, 0, "shadow guards");

    /* Shadow stride follows the video stride, not the width. */
    struct fb wide = fb_new(600, 30, 2560, 30);
    struct fb wide_sh = fb_new(600, 30, 2560, 30);
    cur_boot_args.video = wide.v;
    watch(&wide);
    mmu_on = false;
    ilinux_crumb_step(15);
    ilinux_crumb_shadow_step(15, wide_sh.words);
    verify(&wide, 1u << 20, "wide hw");
    verify(&wide_sh, 1u << 20, "wide shadow");
    fb_free(&wide);
    fb_free(&wide_sh);

    fb_free(&f);
    fb_free(&sh);
}

/*
 * fb_init() copies the hardware framebuffer into the console's shadow copy and
 * every later fb_update() copies it back. c15 comes after fb_init(), so it
 * only survives if it was also stored in the shadow.
 */
static void test_c15_survives_console_update(void)
{
    for (int with_shadow = 0; with_shadow < 2; with_shadow++) {
        struct fb hw = fb_new(MIN_W, MIN_H, MIN_STRIDE, 30);
        struct fb sh = fb_new(MIN_W, MIN_H, MIN_STRIDE, 30);

        reset_model(g_initial_state);
        watch(&hw);
        cur_boot_args.video = hw.v;
        for (unsigned step = 0; step <= 8; step++)
            ilinux_crumb_step(step);
        mmu_on = true;
        for (unsigned step = 9; step <= 14; step++)
            ilinux_crumb_step(step);
        memcpy(sh.words, hw.words, hw.nwords * 4); /* fb_init(): memcpy(fb.ptr, hwptr) */
        ilinux_crumb_step(15);
        if (with_shadow)
            ilinux_crumb_shadow_step(15, sh.words);
        memcpy(hw.words, sh.words, hw.nwords * 4); /* fb_update() on the next console write */
        CHECK(with_shadow ? lit_words() == 16 * BLOCK_WORDS : lit_words() == 15 * BLOCK_WORDS);
        verify(&hw, with_shadow ? 0x1fffe0 : 0x0fffe0, "after fb_update");
        fb_free(&hw);
        fb_free(&sh);
    }
}

static void test_realistic_boot(void)
{
    struct fb f = fb_new(3456, 2234, 13824, 30 | 0x10000);
    struct fb sh = fb_new(3456, 2234, 13824, 30 | 0x10000);
    struct boot_args raw = {f.v};

    reset_model(g_initial_state);
    watch(&f);
    cur_boot_args = raw;
    ilinux_crumb(&raw.video, 5);
    for (unsigned step = 1; step <= 8; step++)
        ilinux_crumb_step(step);
    mmu_on = true;
    for (unsigned step = 9; step <= 15; step++)
        ilinux_crumb_step(step);
    ilinux_crumb_shadow_step(15, sh.words);
    CHECK(nmaps == 1);
    CHECK(maps[0].size == ALIGN_UP((size_t)13824 * 2234, 0x4000));
    verify(&f, 0x1fffe0, "realistic boot strip");
    verify(&sh, 1u << 20, "realistic shadow");
    fb_free(&f);
    fb_free(&sh);
}

int main(void)
{
    g_initial_state = ilinux_crumb_state;

    test_placement();
    test_all_slots();
    test_guards();
    test_mapping_sequence();
    test_foreign_and_garbage_state();
    test_arming_does_not_need_a_valid_geometry();
    test_unmappable_base();
    test_steps_and_shadow();
    test_c15_survives_console_update();
    test_realistic_boot();

    if (failures) {
        printf("crumb model FAIL (%d)\n", failures);
        return 1;
    }
    printf("crumb model PASS\n");
    return 0;
}
