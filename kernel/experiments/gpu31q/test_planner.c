/* SPDX-License-Identifier: MIT */
#include "planner.h"
#include <stdio.h>
#include <string.h>

#define CHECK(x) do { if (!(x)) { fprintf(stderr, "check at line %d\n", __LINE__); return 1; } } while (0)
#define PAGE UINT64_C(0x4000)

static const struct gpu31q_space normal = {
    PAGE, PAGE, UINT64_C(0x1000000000),
    UINT64_C(0x800000), UINT64_C(0x900000), UINT64_C(0x100000)
};
static const struct gpu31q_object object = {1, UINT64_C(0x1000000)};
static const struct gpu31q_op operation = {GPU31Q_READ, 1, 0, PAGE * 2, UINT64_C(0x100000000)};

/* Every rejection verifies the full output buffer and count remain unchanged. */
static int refused(const struct gpu31q_space *s,
                   const struct gpu31q_object *objects, size_t nobjects,
                   const struct gpu31q_op *ops, size_t nops,
                   size_t capacity, enum gpu31q_status expected)
{
    struct gpu31q_planned output[GPU31Q_MAX_OPS], before[GPU31Q_MAX_OPS];
    size_t count = 99;
    memset(output, 0xa5, sizeof(output));
    memcpy(before, output, sizeof(output));
    return gpu31q_plan(s, objects, nobjects, ops, nops, output, capacity, &count) == expected &&
           count == 99 && memcmp(output, before, sizeof(output)) == 0;
}

static int test_ordinary(void)
{
    struct gpu31q_op ops[3] = {operation, operation, operation};
    struct gpu31q_planned out[3];
    size_t n = 99;
    ops[1].flags = GPU31Q_WRITE;
    ops[2].flags = GPU31Q_READ | GPU31Q_WRITE;
    CHECK(gpu31q_plan(&normal, &object, 1, ops, 3, out, 3, &n) == GPU31Q_OK);
    CHECK(n == 3 && out[0].op.addr == UINT64_C(0x100000000));
    CHECK(out[1].op.flags == GPU31Q_WRITE && out[2].op.flags == 6);
    CHECK(out[0].object_bytes_accessed == 2 * PAGE);
    return 0;
}

static int test_reservation_edges(void)
{
    struct gpu31q_op op = operation;
    struct gpu31q_planned out;
    size_t n;
    op.addr = normal.kernel_start - op.size;
    CHECK(gpu31q_plan(&normal, &object, 1, &op, 1, &out, 1, &n) == GPU31Q_OK);
    op.addr += PAGE;
    CHECK(refused(&normal, &object, 1, &op, 1, 1, GPU31Q_RESERVATION));
    op.addr = normal.kernel_end;
    CHECK(gpu31q_plan(&normal, &object, 1, &op, 1, &out, 1, &n) == GPU31Q_OK);
    op.addr -= PAGE;
    CHECK(refused(&normal, &object, 1, &op, 1, 1, GPU31Q_RESERVATION));
    op.addr = normal.kernel_start - PAGE;
    op.size = normal.kernel_end - op.addr + PAGE;
    CHECK(refused(&normal, &object, 1, &op, 1, 1, GPU31Q_RESERVATION));
    return 0;
}

static int test_window_edges(void)
{
    struct gpu31q_op op = operation;
    struct gpu31q_planned out;
    size_t n;
    op.addr = normal.vm_start;
    CHECK(gpu31q_plan(&normal, &object, 1, &op, 1, &out, 1, &n) == GPU31Q_OK);
    op.addr = normal.vm_end - op.size;
    CHECK(gpu31q_plan(&normal, &object, 1, &op, 1, &out, 1, &n) == GPU31Q_OK);
    op.addr += PAGE;
    CHECK(refused(&normal, &object, 1, &op, 1, 1, GPU31Q_RANGE));
    op.addr = 0;
    CHECK(refused(&normal, &object, 1, &op, 1, 1, GPU31Q_RANGE));
    return 0;
}

static int test_single_page(void)
{
    struct gpu31q_op op = operation;
    struct gpu31q_object obj = {1, PAGE};
    struct gpu31q_planned out;
    size_t n;
    op.flags |= GPU31Q_SINGLE_PAGE;
    CHECK(gpu31q_plan(&normal, &obj, 1, &op, 1, &out, 1, &n) == GPU31Q_OK);
    CHECK(out.object_bytes_accessed == PAGE && out.op.size == PAGE * 2);
    obj.size = PAGE - 1;
    CHECK(refused(&normal, &obj, 1, &op, 1, 1, GPU31Q_OBJECT));
    obj.size = PAGE * 2;
    op.offset = PAGE;
    CHECK(gpu31q_plan(&normal, &obj, 1, &op, 1, &out, 1, &n) == GPU31Q_OK);
    op.offset += PAGE;
    CHECK(refused(&normal, &obj, 1, &op, 1, 1, GPU31Q_OBJECT));
    return 0;
}

static int test_unbind(void)
{
    struct gpu31q_op op = {GPU31Q_UNBIND, 0, 0, PAGE, PAGE};
    struct gpu31q_planned out;
    size_t n;
    CHECK(gpu31q_plan(&normal, NULL, 0, &op, 1, &out, 1, &n) == GPU31Q_OK);
    CHECK(out.object_bytes_accessed == 0);
    op.flags |= GPU31Q_READ;
    CHECK(refused(&normal, NULL, 0, &op, 1, 1, GPU31Q_FLAGS));
    op.flags = GPU31Q_UNBIND;
    op.handle = 1;
    CHECK(refused(&normal, NULL, 0, &op, 1, 1, GPU31Q_FLAGS));
    op.handle = 0;
    op.offset = PAGE;
    CHECK(refused(&normal, NULL, 0, &op, 1, 1, GPU31Q_FLAGS));
    op.offset = 0;
    op.addr = normal.kernel_start;
    CHECK(refused(&normal, NULL, 0, &op, 1, 1, GPU31Q_RESERVATION));
    return 0;
}

static int test_ordered_replacement(void)
{
    struct gpu31q_op ops[3] = {operation, {GPU31Q_UNBIND, 0, 0, PAGE * 2, UINT64_C(0x100000000)}, operation};
    struct gpu31q_planned out[3];
    size_t n;
    ops[2].flags = GPU31Q_WRITE;
    CHECK(gpu31q_plan(&normal, &object, 1, ops, 3, out, 3, &n) == GPU31Q_OK);
    CHECK(n == 3 && out[0].op.flags == GPU31Q_READ && out[1].object_bytes_accessed == 0 && out[2].op.flags == GPU31Q_WRITE);
    return 0;
}

static int test_alignment(void)
{
    struct gpu31q_op op = operation;
    op.addr++;
    CHECK(refused(&normal, &object, 1, &op, 1, 1, GPU31Q_ALIGNMENT));
    op = operation;
    op.offset++;
    CHECK(refused(&normal, &object, 1, &op, 1, 1, GPU31Q_ALIGNMENT));
    op = operation;
    op.size--;
    CHECK(refused(&normal, &object, 1, &op, 1, 1, GPU31Q_ALIGNMENT));
    return 0;
}

static int test_flags(void)
{
    struct gpu31q_op op = operation;
    op.flags = 0;
    CHECK(refused(&normal, &object, 1, &op, 1, 1, GPU31Q_FLAGS));
    op.flags = GPU31Q_SINGLE_PAGE;
    CHECK(refused(&normal, &object, 1, &op, 1, 1, GPU31Q_FLAGS));
    op.flags = GPU31Q_READ | UINT32_C(0x80000000);
    CHECK(refused(&normal, &object, 1, &op, 1, 1, GPU31Q_FLAGS));
    return 0;
}

static int test_u64_overflow(void)
{
    struct gpu31q_space s = {1, 0, UINT64_MAX, 0x100, 0x200, 1};
    struct gpu31q_op op = {GPU31Q_READ, 1, 0, 1, UINT64_MAX};
    struct gpu31q_planned out;
    size_t n;
    CHECK(refused(&s, &object, 1, &op, 1, 1, GPU31Q_RANGE));
    op.addr--;
    CHECK(gpu31q_plan(&s, &object, 1, &op, 1, &out, 1, &n) == GPU31Q_OK);
    op.size = 2;
    CHECK(refused(&s, &object, 1, &op, 1, 1, GPU31Q_RANGE));
    s.page_size = PAGE;
    s.vm_end = UINT64_MAX & ~(PAGE - 1);
    s.kernel_start = PAGE;
    s.kernel_end = 2 * PAGE;
    s.kernel_min_size = PAGE;
    op.addr = s.vm_end - PAGE;
    op.size = PAGE;
    CHECK(gpu31q_plan(&s, &object, 1, &op, 1, &out, 1, &n) == GPU31Q_OK);
    op.addr = s.vm_end; /* Aligned span would end at exactly 2^64. */
    CHECK(refused(&s, &object, 1, &op, 1, 1, GPU31Q_RANGE));
    return 0;
}

static int test_object_overflow(void)
{
    struct gpu31q_space s = {1, 0, UINT64_MAX, 0x100, 0x200, 1};
    struct gpu31q_object obj = {1, UINT64_MAX};
    struct gpu31q_op op = {GPU31Q_READ, 1, UINT64_MAX - 1, 2, 0};
    CHECK(refused(&s, &obj, 1, &op, 1, 1, GPU31Q_OBJECT));
    op.offset = UINT64_MAX;
    op.size = 1;
    CHECK(refused(&s, &obj, 1, &op, 1, 1, GPU31Q_OBJECT));
    return 0;
}

static int test_unknown_and_duplicate_object(void)
{
    struct gpu31q_object objs[2] = {object, object};
    struct gpu31q_op op = operation;
    CHECK(refused(&normal, objs, 2, &op, 1, 1, GPU31Q_OBJECT));
    op.handle = 2;
    CHECK(refused(&normal, &object, 1, &op, 1, 1, GPU31Q_OBJECT));
    op.handle = 0;
    CHECK(refused(&normal, NULL, 0, &op, 1, 1, GPU31Q_OBJECT));
    return 0;
}

static int test_object_extent(void)
{
    struct gpu31q_object obj = {1, PAGE * 2};
    struct gpu31q_op op = operation;
    struct gpu31q_planned out;
    size_t n;
    CHECK(gpu31q_plan(&normal, &obj, 1, &op, 1, &out, 1, &n) == GPU31Q_OK);
    op.offset = PAGE;
    CHECK(refused(&normal, &obj, 1, &op, 1, 1, GPU31Q_OBJECT));
    obj.size--;
    op.offset = 0;
    CHECK(refused(&normal, &obj, 1, &op, 1, 1, GPU31Q_OBJECT));
    return 0;
}

static int test_space_shape(void)
{
    struct gpu31q_space s = normal;
    s.page_size = 0;
    CHECK(gpu31q_validate_space(&s) == GPU31Q_ALIGNMENT);
    s.page_size = 3;
    CHECK(gpu31q_validate_space(&s) == GPU31Q_ALIGNMENT);
    s = normal; s.vm_end = s.vm_start;
    CHECK(gpu31q_validate_space(&s) == GPU31Q_WINDOW);
    s = normal; s.vm_end = 0;
    CHECK(gpu31q_validate_space(&s) == GPU31Q_WINDOW);
    s = normal; s.vm_end--;
    CHECK(gpu31q_validate_space(&s) == GPU31Q_ALIGNMENT);
    return 0;
}

static int test_space_reservation(void)
{
    struct gpu31q_space s = normal;
    s.kernel_end = s.kernel_start;
    CHECK(gpu31q_validate_space(&s) == GPU31Q_RESERVATION);
    s = normal; s.kernel_min_size++;
    CHECK(gpu31q_validate_space(&s) == GPU31Q_RESERVATION);
    s = normal; s.kernel_start = 0;
    CHECK(gpu31q_validate_space(&s) == GPU31Q_RESERVATION);
    s = normal; s.kernel_end = s.vm_end + PAGE;
    CHECK(gpu31q_validate_space(&s) == GPU31Q_RESERVATION);
    s = normal; s.kernel_min_size = 0;
    CHECK(gpu31q_validate_space(&s) == GPU31Q_RESERVATION);
    s = normal; s.kernel_end++;
    CHECK(gpu31q_validate_space(&s) == GPU31Q_ALIGNMENT);
    return 0;
}

static int test_late_failure_atomicity(void)
{
    struct gpu31q_op ops[3] = {operation, operation, operation};
    ops[2].addr = normal.kernel_start;
    CHECK(refused(&normal, &object, 1, ops, 3, 3, GPU31Q_RESERVATION));
    ops[2] = operation; ops[2].handle = 8;
    CHECK(refused(&normal, &object, 1, ops, 3, 3, GPU31Q_OBJECT));
    CHECK(refused(&normal, &object, 1, ops, 3, 2, GPU31Q_CAPACITY));
    return 0;
}

static int test_empty_and_null(void)
{
    size_t n = 99;
    struct gpu31q_planned out;
    CHECK(gpu31q_plan(&normal, NULL, 0, NULL, 0, NULL, 0, &n) == GPU31Q_OK && n == 0);
    CHECK(gpu31q_validate_space(NULL) == GPU31Q_ARGUMENT);
    CHECK(gpu31q_plan(&normal, NULL, 0, NULL, 0, NULL, 0, NULL) == GPU31Q_ARGUMENT);
    CHECK(refused(NULL, &object, 1, &operation, 1, 1, GPU31Q_ARGUMENT));
    CHECK(refused(&normal, NULL, 1, &operation, 1, 1, GPU31Q_ARGUMENT));
    CHECK(refused(&normal, &object, 1, NULL, 1, 1, GPU31Q_ARGUMENT));
    CHECK(gpu31q_plan(&normal, &object, 1, &operation, 1, NULL, 1, &n) == GPU31Q_ARGUMENT);
    CHECK(gpu31q_plan(&normal, &object, 1, &operation, 1, &out, 1, NULL) == GPU31Q_ARGUMENT);
    return 0;
}

static int test_resource_limits(void)
{
    struct gpu31q_op ops[GPU31Q_MAX_OPS + 1u];
    struct gpu31q_planned out[GPU31Q_MAX_OPS];
    struct gpu31q_object objs[GPU31Q_MAX_OBJECTS + 1u];
    size_t i, n = 99;
    for (i = 0; i <= GPU31Q_MAX_OPS; ++i) ops[i] = operation;
    for (i = 0; i <= GPU31Q_MAX_OBJECTS; ++i) { objs[i] = object; objs[i].handle = (uint32_t)(i + 1); }
    CHECK(gpu31q_plan(&normal, objs, GPU31Q_MAX_OBJECTS, ops, GPU31Q_MAX_OPS, out, GPU31Q_MAX_OPS, &n) == GPU31Q_OK && n == GPU31Q_MAX_OPS);
    CHECK(refused(&normal, &object, 1, ops, GPU31Q_MAX_OPS + 1u, GPU31Q_MAX_OPS, GPU31Q_LIMIT));
    CHECK(refused(&normal, objs, GPU31Q_MAX_OBJECTS + 1u, &operation, 1, 1, GPU31Q_LIMIT));
    return 0;
}

static int test_zero_extent(void)
{
    struct gpu31q_op op = operation;
    struct gpu31q_object obj = object;
    op.size = 0;
    CHECK(refused(&normal, &object, 1, &op, 1, 1, GPU31Q_RANGE));
    obj.size = 0;
    CHECK(refused(&normal, &obj, 1, &operation, 1, 1, GPU31Q_OBJECT));
    obj = object; obj.handle = 0;
    CHECK(refused(&normal, &obj, 1, &operation, 1, 1, GPU31Q_OBJECT));
    return 0;
}

static int test_variable_page_sizes(void)
{
    uint64_t page;
    for (page = 1; page <= UINT64_C(0x10000); page <<= 1) {
        struct gpu31q_space s = {page, page, page * 32, page * 16, page * 20, page * 4};
        struct gpu31q_object obj = {1, page};
        struct gpu31q_op op = {GPU31Q_READ | GPU31Q_SINGLE_PAGE, 1, 0, page * 4, page * 2};
        struct gpu31q_planned out;
        size_t n;
        CHECK(gpu31q_plan(&s, &obj, 1, &op, 1, &out, 1, &n) == GPU31Q_OK);
        CHECK(out.object_bytes_accessed == page);
    }
    return 0;
}

/* Independent small integer/page-grid oracle: no checked-add/interval helper
 * from the implementation is reused. 139392 acceptance decisions. */
static int test_grid_oracle(void)
{
    struct gpu31q_space s = {PAGE, PAGE, 33 * PAGE, 16 * PAGE, 20 * PAGE, 4 * PAGE};
    struct gpu31q_object obj = {1, 8 * PAGE};
    unsigned a, len, off, flags;
    for (a = 0; a < 36; ++a) for (len = 0; len < 11; ++len)
    for (off = 0; off < 11; ++off) for (flags = 0; flags < 32; ++flags) {
        struct gpu31q_op op = {flags, (flags & 1u) ? 0u : 1u, off * PAGE, len * PAGE, a * PAGE};
        struct gpu31q_planned out;
        size_t n;
        int span = len > 0 && a >= 1 && a + len <= 33 && (a + len <= 16 || a >= 20);
        int form = (flags & 1u) ? (flags == 1 && off == 0) :
            ((flags & ~14u) == 0 && (flags & 6u) != 0 && off + ((flags & 8u) ? 1u : len) <= 8);
        CHECK((gpu31q_plan(&s, &obj, 1, &op, 1, &out, 1, &n) == GPU31Q_OK) == (span && form));
    }
    return 0;
}

int main(void)
{
    CHECK(test_ordinary() == 0);
    CHECK(test_reservation_edges() == 0);
    CHECK(test_window_edges() == 0);
    CHECK(test_single_page() == 0);
    CHECK(test_unbind() == 0);
    CHECK(test_ordered_replacement() == 0);
    CHECK(test_alignment() == 0);
    CHECK(test_flags() == 0);
    CHECK(test_u64_overflow() == 0);
    CHECK(test_object_overflow() == 0);
    CHECK(test_unknown_and_duplicate_object() == 0);
    CHECK(test_object_extent() == 0);
    CHECK(test_space_shape() == 0);
    CHECK(test_space_reservation() == 0);
    CHECK(test_late_failure_atomicity() == 0);
    CHECK(test_empty_and_null() == 0);
    CHECK(test_resource_limits() == 0);
    CHECK(test_zero_extent() == 0);
    CHECK(test_variable_page_sizes() == 0);
    CHECK(test_grid_oracle() == 0);
    puts("GPU31Q_PLANNER_PASS");
    return 0;
}
