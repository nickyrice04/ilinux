/* SPDX-License-Identifier: MIT */
/* Original test environment. Real payload/parser/decompressor code is added
 * from authenticated public sources only inside the isolated Linux VM. */
#include <assert.h>
#include <ctype.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include "libfdt.h"
#include "tinf/tinf.h"
#include "stage1_proxy.h"
typedef uint8_t u8;
typedef uint32_t u32;
typedef uint64_t u64;
#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))
#define BUILD_TAG "direct31ai-mock-only"
#define T8140 0x8140
#define MAX_CPUS 64
#define SMP_TIMEOUT -2
#define BIT(x) (1UL << (x))
struct kernel_header {
    u32 code[2];
    u64 text_offset, image_size, flags, res2, res3, res4;
    u32 magic, res5;
};
enum { V26_6_2 = 1 };
static struct { int version; } os_firmware;
#include "payload_profile.h"
static int XzDecode(void *in, uint32_t *in_len, void *out, uint32_t *out_len)
{ (void)in; (void)in_len; (void)out; (void)out_len; return 0; }

#define HEAP_BYTES (96U << 20)
static u8 heap_storage[HEAP_BYTES + (2U << 20)];
static u8 *heap;
static size_t heap_used;
static void *heapblock_alloc_aligned(size_t size, size_t alignment)
{
    assert(alignment && !(alignment & (alignment - 1)));
    size_t offset = (heap_used + alignment - 1) & ~(alignment - 1);
    assert(offset <= HEAP_BYTES && size <= HEAP_BYTES - offset);
    heap_used = offset + size;
    return heap + offset;
}
static bool in_heap(const void *pointer, size_t bytes)
{
    uintptr_t start = (uintptr_t)pointer, base = (uintptr_t)heap;
    return start >= base && start <= base + HEAP_BYTES && bytes <= base + HEAP_BYTES - start;
}

static u8 *input, *expected_image, *expected_dtb, *expected_initrd;
static size_t input_size, image_bytes, dtb_bytes, initrd_bytes;
static int failure, boot_calls, prepare_calls, chosen_calls, invalid_initrd;
static bool initrd_set;
static unsigned events[32], event_count;
static void event(unsigned value) { assert(event_count < ARRAY_SIZE(events)); events[event_count++] = value; }
static void *adt;
static int chip_id = 0x6050, boot_cpu_idx;
static bool nvme_keep_running_for_linux;
static struct { void *entry; } next_stage;
static const void *adt_getprop(void *tree, int node, const char *name, u32 *length)
{
    (void)tree; (void)node; (void)length;
    assert(!strcmp(name, "target-type")); return "J716c";
}
static void *payload_start(void) { return input; }
static void cpufreq_payload_boost(bool enabled) { event(enabled ? 1 : 3); }
static void cpufreq_init(void) { event(5); }
static int smp_start_secondaries(void) { event(6); return 0; }
static int mitigations_perform(void) { event(7); return failure == 3 ? SMP_TIMEOUT : 0; }
static bool smp_is_alive(int cpu) { return cpu >= 0 && cpu < 18; }
static int smp_call_sync0(int cpu, void (*function)(void)) { (void)cpu; (void)function; abort(); }
static void do_enable_tso(void) { abort(); }
static bool nvme_shutdown(void) { event(4); return true; }
static bool nvme_set_sart_var(const char *value) { (void)value; abort(); }
static int display_configure(const char *value) { (void)value; abort(); }
static int display_configure_second(const char *value) { (void)value; abort(); }
static void mitigations_configure(const char *value) { (void)value; abort(); }
static int boot_storage_load(const char *spec, struct kernel_header **kernel, void **tree)
{ (void)spec; (void)kernel; (void)tree; abort(); }
static const char *stage1_config_target(void) { return NULL; }
static const char *stage1_config_esp_uuid(void) { abort(); }
static int chainload_load(const char *spec, char **vars, size_t *count, size_t capacity)
{ (void)spec; (void)vars; (void)count; (void)capacity; abort(); }
static void kboot_delete_chosen(const char *name) { (void)name; abort(); }
static void kboot_set_config_lost(void) { abort(); }
static int kboot_set_chosen(const char *name, const char *value)
{
    assert(!strcmp(name, "bootargs"));
    assert(!strcmp(value, "console=tty0 earlycon keep_bootcon rdinit=/init ro loglevel=7 panic=0"));
    chosen_calls++; event(8); return 0;
}
static void kboot_set_initrd(void *start, size_t size)
{
    assert(size == initrd_bytes && !memcmp(start, expected_initrd, size));
    invalid_initrd = !in_heap(start, size);
    initrd_set = true; event(2);
}
static int kboot_prepare_dt(void *tree)
{
    assert(fdt_totalsize(tree) == dtb_bytes && !memcmp(tree, expected_dtb, dtb_bytes));
    prepare_calls++; event(9);
    return failure == 1 || !initrd_set || invalid_initrd ? -1 : 0;
}
static int kboot_boot(void *kernel)
{
    assert(in_heap(kernel, image_bytes) && !((uintptr_t)kernel & ((2U << 20) - 1)));
    assert(!memcmp(kernel, expected_image, image_bytes));
    boot_calls++; event(10);
    if (failure == 2) return -1;
    next_stage.entry = kernel;
    return 0;
}
static int mock_log(const char *format, ...)
{
    va_list arguments;
    va_start(arguments, format);
    int result = vfprintf(stderr, format, arguments);
    va_end(arguments);
    return result;
}
#define printf mock_log
