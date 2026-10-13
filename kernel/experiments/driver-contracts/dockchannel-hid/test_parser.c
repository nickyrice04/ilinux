/* SPDX-License-Identifier: MIT
 * Original synthetic harness. The tested parser functions and packet structs
 * are extracted verbatim from the pinned Linux source (GPL-2.0 OR MIT).
 * Run only in an isolated Linux guest. No devices or captured HID data used.
 */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <time.h>

typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;
struct completion { unsigned completed; };
struct mutex { int dummy; };
struct work_struct { void (*fn)(struct work_struct *); };
struct firmware { size_t size; const u8 *data; };
#define __packed __attribute__((packed))
#define GENMASK(h, l) (((~0U) << (l)) & (~0U >> (31 - (h))))
#define FIELD_GET(mask, value) (((value) & (mask)) >> __builtin_ctz(mask))
#define GFP_KERNEL 0
#define HID_INPUT_REPORT 0
#define WARN_ON_ONCE(x) ((void)(x))
#define container_of(ptr, type, member) ((type *)((char *)(ptr) - offsetof(type, member)))
#define min(a, b) ((a) < (b) ? (a) : (b))
#define INIT_WORK(work, callback) ((work)->fn = (callback))

#include "driver_types.inc"

static unsigned errors, warnings, infos, interface_gets, creates, descriptors;
static unsigned event_callbacks, reports, awaits, queued, releases, freed;
static unsigned allocations, completion_calls;
static unsigned checksum_words;
static bool fail_allocation;
static char last_log[512];
static struct dockchannel_hid device;
static struct dchid_iface iface;
static const struct firmware *next_firmware;
static const u8 *transport;
static size_t transport_size, transport_pos;

static void log_record(unsigned *counter, const char *format, ...)
{
    /* Consume arguments, including bounded strings, as real dev_* does. */
    char output[512];
    va_list args;
    va_start(args, format);
    vsnprintf(output, sizeof(output), format, args);
    va_end(args);
    ++*counter;
    memcpy(last_log, output, sizeof(last_log));
}
#define dev_err(dev, ...) log_record(&errors, __VA_ARGS__)
#define dev_warn(dev, ...) log_record(&warnings, __VA_ARGS__)
#define dev_info(dev, ...) log_record(&infos, __VA_ARGS__)

static u32 get_unaligned_le32(const void *p)
{
    ++checksum_words;
    const u8 *b = p;
    return (u32)b[0] | (u32)b[1] << 8 | (u32)b[2] << 16 | (u32)b[3] << 24;
}
static void *kzalloc(size_t size, int flags)
{
    if (fail_allocation) return NULL;
    void *p = calloc(1, size);
    assert(p);
    ++allocations;
    return p;
}
static void kfree(void *p) { if (p) ++freed; free(p); }
static void *devm_kmemdup(void *dev, const void *p, size_t n, int flags)
{
    void *result = malloc(n ? n : 1);
    if (result) memcpy(result, p, n);
    return result;
}
static int of_property_read_string(const void *node, const char *key, const char **name)
{ *name = "synthetic.bin"; return 0; }
static int request_firmware(const struct firmware **fw, const char *name, void *dev)
{ *fw = next_firmware; return 0; }
static void release_firmware(const struct firmware *fw) { ++releases; }
static void complete(struct completion *c) { ++c->completed; ++completion_calls; }
static void strscpy(char *dst, const char *src, size_t n)
{
    size_t length = strnlen(src, n - 1);
    memcpy(dst, src, length);
    dst[length] = 0;
}
static struct dchid_iface *dchid_get_interface(struct dockchannel_hid *dchid,
                                               int index, const char *name)
{
    ++interface_gets;
    /* The actual function also consumes name as a C string. */
    assert(strlen(name) < 16);
    return index < MAX_INTERFACES ? &iface : NULL;
}
static void dchid_handle_descriptor(struct dchid_iface *i, void *p, size_t n)
{ ++descriptors; }
static int dchid_create_interface(struct dchid_iface *i) { ++creates; return 0; }
static void dchid_handle_ready(struct dockchannel_hid *d, void *p, size_t n)
{ ++event_callbacks; }
static void dchid_handle_gpio(struct dockchannel_hid *d, void *p, size_t n)
{ ++event_callbacks; }
static void dchid_handle_report(struct dchid_iface *i, void *p, size_t n)
{ ++reports; }
static int dockchannel_recv(struct dockchannel *dc, void *out, size_t n)
{
    if (n > transport_size - transport_pos) return -EIO;
    memcpy(out, transport + transport_pos, n);
    transport_pos += n;
    return (int)n;
}
static int dockchannel_await(struct dockchannel *dc,
                            void (*callback)(void *, size_t), void *cookie, size_t n)
{ ++awaits; return (int)n; }
static int queue_work(void *queue, struct work_struct *work)
{ ++queued; work->fn(work); return 1; }

#include "driver_functions.inc"

static void reset(void)
{
    errors = warnings = infos = interface_gets = creates = descriptors = 0;
    event_callbacks = reports = awaits = queued = releases = freed = 0;
    allocations = completion_calls = 0;
    checksum_words = 0;
    fail_allocation = false;
    last_log[0] = 0;
    memset(&device, 0, sizeof(device));
    memset(&iface, 0, sizeof(iface));
    device.id_ready = true;
    iface.dchid = &device;
    iface.name = "keyboard";
    device.ifaces[0] = device.ifaces[1] = &iface;
    iface.out_report = -1;
    transport = NULL;
    transport_size = transport_pos = 0;
}

static void put16(void *p, u16 v)
{ u8 *b = p; b[0] = v; b[1] = v >> 8; }
static void put32(void *p, u32 v)
{ u8 *b = p; for (unsigned i = 0; i < 4; ++i) b[i] = v >> (8 * i); }

static u8 *init_packet(size_t extra, size_t *length)
{
    *length = sizeof(struct dchid_init_hdr) + extra;
    u8 *p = calloc(1, *length);
    assert(p);
    p[0] = EVENT_INIT;
    p[3] = 1;
    memcpy(p + 4, "keyboard", 9);
    return p;
}

/* Build the transport envelope independently from the Linux checksum function. */
static void receive(unsigned index, unsigned body_length, unsigned sub_length)
{
    size_t size = 8 + body_length + 4;
    u8 *p = calloc(1, size);
    assert(p && body_length <= 65535);
    p[0] = 8;
    p[1] = DCHID_CHANNEL_REPORT;
    put16(p + 2, body_length);
    p[5] = index;
    if (body_length >= 8) put16(p + 10, sub_length);
    u32 sum = 0;
    for (size_t i = 0; i + 4 <= size - 4; i += 4)
        sum += (u32)p[i] | (u32)p[i + 1] << 8 | (u32)p[i + 2] << 16 | (u32)p[i + 3] << 24;
    put32(p + size - 4, UINT32_MAX - sum);
    transport = p;
    transport_size = size;
    transport_pos = 0;
    dchid_handle_packet(&device, size);
    assert(awaits == 1);
    assert(transport_pos == size);
    free(p);
}

static void test_case(const char *name)
{
    reset();
    if (!strcmp(name, "short_firmware")) {
        for (size_t n = 0; n < sizeof(struct fw_header); ++n) {
            u8 *p = malloc(n ? n : 1);
            assert(p);
            memset(p, 0, n);
            struct firmware fw = { n, p };
            void *data = NULL;
            size_t size = 0;
            next_firmware = &fw;
            assert(dchid_get_firmware(&iface, &data, &size) == -EINVAL);
            assert(!data);
            free(p);
        }
        assert(releases == sizeof(struct fw_header));
    } else if (!strcmp(name, "unterminated_name")) {
        size_t n;
        u8 *p = init_packet(0, &n);
        memset(p + 4, 'x', 16);
        dchid_handle_init(&device, p, n);
        assert(interface_gets == 0 && creates == 0);
        free(p);
    } else if (!strcmp(name, "short_gpio")) {
        size_t n;
        u8 *p = init_packet(4 + 36, &n);
        u8 *block = p + sizeof(struct dchid_init_hdr);
        put16(block, INIT_GPIO_REQUEST);
        put16(block + 2, 4); /* Adjacent data cannot fill this short block. */
        put16(block + 6, 7);
        put16(block + 8, INIT_TERMINATOR);
        put16(block + 10, 28);
        dchid_handle_init(&device, p, n);
        assert(iface.gpio_id == 0);
        free(p);
    } else if (!strcmp(name, "empty_product")) {
        size_t n;
        u8 *p = init_packet(4, &n);
        put16(p + sizeof(struct dchid_init_hdr), INIT_PRODUCT_NAME);
        dchid_handle_init(&device, p, n);
        assert(warnings == 1 && infos == 0);
        free(p);
    } else if (!strcmp(name, "empty_event")) {
        dchid_handle_event(&device, NULL, 0);
        assert(event_callbacks == 0);
    } else if (!strcmp(name, "short_body")) {
        receive(1, 0, 0);
        assert(queued == 0 && allocations == 0);
    } else if (!strcmp(name, "unaligned_body")) {
        receive(1, 9, 0);
        assert(queued == 0 && errors == 1);
        assert(checksum_words == 0);
    } else if (!strcmp(name, "bad_iface")) {
        receive(255, 8, 0);
        assert(queued == 0 && errors == 1);
    } else if (!strcmp(name, "bad_subheader")) {
        receive(1, 8, 1);
        assert(queued == 1 && allocations == 1 && freed == 1);
    } else if (!strcmp(name, "allocation_rearm")) {
        fail_allocation = true;
        receive(1, 12, 3);
        assert(queued == 0 && allocations == 0 && awaits == 1);
    } else if (!strcmp(name, "valid_input")) {
        receive(1, 12, 3);
        assert(queued == 1 && reports == 1 && freed == 1 && errors == 0);
    } else if (!strcmp(name, "valid_init")) {
        size_t n;
        u8 *p = init_packet(4 + 36 + 4, &n);
        u8 *block = p + sizeof(struct dchid_init_hdr);
        put16(block, INIT_GPIO_REQUEST);
        put16(block + 2, 36);
        put16(block + 6, 7);
        memcpy(block + 8, "reset", 6);
        put16(block + 40, INIT_TERMINATOR);
        dchid_handle_init(&device, p, n);
        assert(iface.gpio_id == 7 && !strcmp(iface.gpio_name, "reset"));
        assert(creates == 1 && errors == 0);
        free(p);
    } else if (!strcmp(name, "valid_firmware")) {
        u8 p[24] = {0};
        put32(p, FW_MAGIC);
        put32(p + 4, FW_VER);
        put32(p + 8, 20);
        put32(p + 12, 4);
        put32(p + 16, 1);
        p[20] = 0xaa;
        struct firmware fw = {sizeof(p), p};
        void *data = NULL;
        size_t size = 0;
        next_firmware = &fw;
        iface.index = 3;
        assert(dchid_get_firmware(&iface, &data, &size) == 0);
        assert(size == 4 && ((u8 *)data)[0] == 0xaa && ((u8 *)data)[1] == 3);
        assert(releases == 1);
        free(data);
    } else {
        fprintf(stderr, "Unknown case: %s\n", name);
        exit(2);
    }
    printf("PASS %s\n", name);
}

#ifndef TEST_VARIANT
#define TEST_VARIANT "unspecified"
#endif

static void benchmark(unsigned iterations)
{
    /* Fixed valid envelope, no per-iteration setup allocation or log output.
     * Allocation/free performed by the extracted driver remain in the timing.
     * No hardware interrupt scheduling or actual HID consumer is measured.
     */
    u8 p[24] = {8, DCHID_CHANNEL_REPORT, 12, 0, 0, 1, 0, 0,
                0, 0, 3, 0};
    u32 sum = 0;
    struct timespec start, end;
    reset();
    for (size_t i = 0; i < sizeof(p) - 4; i += 4)
        sum += (u32)p[i] | (u32)p[i + 1] << 8 | (u32)p[i + 2] << 16 | (u32)p[i + 3] << 24;
    put32(p + sizeof(p) - 4, UINT32_MAX - sum);
    transport = p;
    transport_size = sizeof(p);
    assert(clock_gettime(CLOCK_MONOTONIC, &start) == 0);
    for (unsigned i = 0; i < iterations; ++i) {
        transport_pos = 0;
        dchid_handle_packet(&device, sizeof(p));
    }
    assert(clock_gettime(CLOCK_MONOTONIC, &end) == 0);
    assert(queued == iterations && reports == iterations && freed == iterations);
    assert(awaits == iterations && allocations == iterations && errors == 0);
    double elapsed = (double)(end.tv_sec - start.tv_sec) +
                     (double)(end.tv_nsec - start.tv_nsec) * 1e-9;
    printf("{\"scope\":\"synthetic_vm_parser\",\"variant\":\"%s\","
           "\"iterations\":%u,\"elapsed_s\":%.9f,\"ns_per_packet\":%.3f,"
           "\"compiler\":\"%s\",\"pointer_bits\":%zu}\n",
           TEST_VARIANT, iterations, elapsed, elapsed * 1e9 / iterations,
           __VERSION__, sizeof(void *) * 8);
}

int main(int argc, char **argv)
{
    static const char *cases[] = {
        "short_firmware", "unterminated_name", "short_gpio", "empty_product",
        "empty_event", "short_body", "unaligned_body", "bad_iface",
        "bad_subheader", "allocation_rearm", "valid_input", "valid_init", "valid_firmware"
    };
    if (argc == 3 && !strcmp(argv[1], "bench")) {
        char *end;
        unsigned long iterations = strtoul(argv[2], &end, 10);
        assert(*end == 0 && iterations > 0 && iterations <= 10000000);
        benchmark((unsigned)iterations);
        return 0;
    }
    assert(argc == 2);
    if (!strcmp(argv[1], "all")) {
        for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i)
            test_case(cases[i]);
    } else test_case(argv[1]);
    return 0;
}
