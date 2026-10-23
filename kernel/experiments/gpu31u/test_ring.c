/* SPDX-License-Identifier: MIT */
#include "ring.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

struct fixture {
    struct gpu31u_ring *ring;
    uint32_t type, published, copy_status, publish_status;
    uint64_t offset;
    unsigned copies, publishes, ordered;
    bool copy_ok, publish_ok, reenter;
};
static struct gpu31u_effect copy_record(void *context, uint64_t offset,
                                       uint8_t record[GPU31U_RECORD_BYTES])
{
    struct fixture *f = context;
    ++f->copies;
    f->offset = offset;
    assert(f->ordered == 0);
    f->ordered = 1;
    if (f->reenter) assert(gpu31u_next(f->ring) == GPU31U_STATE);
    memset(record, 0xa5, GPU31U_RECORD_BYTES);
    for (unsigned i = 0; i < 4; ++i) record[i] = (uint8_t)(f->type >> (8 * i));
    return (struct gpu31u_effect){ f->copy_ok, f->copy_status };
}
static struct gpu31u_effect publish(void *context, uint32_t consumer)
{
    struct fixture *f = context;
    ++f->publishes;
    assert(f->ordered == 1);
    assert(f->ring->record_valid && f->ring->publication_attempted);
    assert(f->ring->record[71] == 0xa5);
    assert(f->ring->phase == GPU31U_BUSY);
    f->ordered = 2;
    f->published = consumer;
    if (f->reenter) assert(gpu31u_next(f->ring) == GPU31U_STATE);
    return (struct gpu31u_effect){ f->publish_ok, f->publish_status };
}
static struct gpu31u_ops operations(struct fixture *f)
{ return (struct gpu31u_ops){ copy_record, publish, f }; }
static struct fixture fixture(struct gpu31u_ring *ring)
{ return (struct fixture){ .ring = ring, .copy_ok = true, .publish_ok = true }; }

static void arguments(void)
{
    struct gpu31u_ring ring = {0};
    unsigned char before[sizeof(ring)];
    memcpy(before, &ring, sizeof(ring));
    struct fixture f = fixture(&ring);
    struct gpu31u_ops ops = operations(&f), bad = ops;
    assert(gpu31u_begin(NULL, 3, 0, 1, 216, 1, &ops) == GPU31U_ARGUMENT);
    assert(gpu31u_next(NULL) == GPU31U_ARGUMENT);
    assert(gpu31u_next(&ring) == GPU31U_STATE);
    assert(gpu31u_begin(&ring, 0, 0, 0, 216, 1, &ops) == GPU31U_ARGUMENT);
    assert(gpu31u_begin(&ring, 3, 3, 1, 216, 1, &ops) == GPU31U_ARGUMENT);
    assert(gpu31u_begin(&ring, 3, 0, 3, 216, 1, &ops) == GPU31U_ARGUMENT);
    assert(gpu31u_begin(&ring, 3, 0, 1, 215, 1, &ops) == GPU31U_ARGUMENT);
    assert(gpu31u_begin(&ring, 3, 0, 1, 216, 1, NULL) == GPU31U_ARGUMENT);
    bad.copy = NULL;
    assert(gpu31u_begin(&ring, 3, 0, 1, 216, 1, &bad) == GPU31U_ARGUMENT);
    bad = ops; bad.publish = NULL;
    assert(gpu31u_begin(&ring, 3, 0, 1, 216, 1, &bad) == GPU31U_ARGUMENT);
    assert(memcmp(&ring, before, sizeof(ring)) == 0);
    assert(!f.copies && !f.publishes);
}
static void bounded_drain(void)
{
    /* Every start/end pair for non-power-of-two and power-of-two capacities. */
    for (uint32_t n = 1; n <= 17; ++n) {
        for (uint32_t consumer = 0; consumer < n; ++consumer) {
            for (uint32_t producer = 0; producer < n; ++producer) {
                struct gpu31u_ring ring = {0};
                struct fixture f = fixture(&ring);
                struct gpu31u_ops ops = operations(&f);
                uint32_t expected = consumer;
                unsigned count = (producer + n - consumer) % n;
                assert(gpu31u_begin(&ring, n, consumer, producer,
                    (uint64_t)n * 72, 1, &ops) == (count ? GPU31U_OK : GPU31U_EMPTY));
                for (unsigned i = 0; i < count; ++i) {
                    f.ordered = 0;
                    assert(gpu31u_next(&ring) == GPU31U_OK);
                    assert(f.offset == (uint64_t)expected * 72);
                    expected = (expected + 1) % n;
                    assert(f.published == expected && ring.consumer == expected);
                    assert(ring.record_valid && ring.record_type == 0);
                    for (unsigned j = 4; j < 72; ++j) assert(ring.record[j] == 0xa5);
                }
                assert(gpu31u_next(&ring) == GPU31U_EMPTY);
                assert(f.copies == count && f.publishes == count);
                assert(ring.phase == GPU31U_DONE && ring.consumer == producer);
                assert(gpu31u_begin(&ring, n, 0, 0, (uint64_t)n * 72, 1, &ops) == GPU31U_STATE);
            }
        }
    }
}
static void types(void)
{
    const uint32_t values[] = {0, 1, 31, 32, 63, 64, 65, 127, UINT32_MAX};
    for (unsigned j = 0; j < sizeof(values) / sizeof(values[0]); ++j) {
        for (unsigned allow = 0; allow < 2; ++allow) {
            struct gpu31u_ring ring = {0};
            struct fixture f = fixture(&ring);
            struct gpu31u_ops ops = operations(&f);
            f.type = values[j];
            assert(gpu31u_begin(&ring, 3, 2, 0, 216,
                allow ? UINT64_MAX : 0, &ops) == GPU31U_OK);
            bool accepted = allow && f.type < 64;
            assert(gpu31u_next(&ring) == (accepted ? GPU31U_OK : GPU31U_TYPE_REFUSED));
            assert(ring.record_type == f.type && ring.record_valid);
            assert(f.publishes == (unsigned)accepted);
            assert(ring.consumer == (accepted ? 0u : 2u));
            if (!accepted) assert(gpu31u_next(&ring) == GPU31U_STATE);
        }
    }
    /* A single allow bit must not alias another in-range type. */
    struct gpu31u_ring ring = {0};
    struct fixture f = fixture(&ring);
    struct gpu31u_ops ops = operations(&f);
    f.type = 2;
    assert(gpu31u_begin(&ring, 2, 0, 1, 144, UINT64_C(1) << 1, &ops) == GPU31U_OK);
    assert(gpu31u_next(&ring) == GPU31U_TYPE_REFUSED && !f.publishes);
}
static void failures(void)
{
    for (unsigned which = 0; which < 2; ++which) {
        struct gpu31u_ring ring = {0};
        struct fixture f = fixture(&ring);
        struct gpu31u_ops ops = operations(&f);
        f.copy_ok = which != 0; f.publish_ok = false;
        f.copy_status = UINT32_C(0xfedcba98); f.publish_status = 0;
        assert(gpu31u_begin(&ring, 3, 2, 0, 216, 1, &ops) == GPU31U_OK);
        assert(gpu31u_next(&ring) == (which ? GPU31U_PUBLISH_UNKNOWN : GPU31U_COPY_FAILED));
        assert(ring.consumer == 2 && ring.copy_status == f.copy_status);
        assert(ring.record_valid == (which != 0));
        assert(ring.publication_attempted == (which != 0));
        assert(gpu31u_next(&ring) == GPU31U_STATE);
        assert(f.copies == 1 && f.publishes == which);
        if (which) assert(ring.proposed_consumer == 0 && ring.publish_status == 0);
    }
}
static void status_and_reentrancy(void)
{
    struct gpu31u_ring ring = {0};
    struct fixture f = fixture(&ring);
    struct gpu31u_ops ops = operations(&f);
    f.reenter = true; f.copy_status = 17; f.publish_status = 29;
    assert(gpu31u_begin(&ring, 2, 0, 1, 144, 1, &ops) == GPU31U_OK);
    assert(gpu31u_next(&ring) == GPU31U_OK);
    assert(ring.copy_status == 17 && ring.publish_status == 29);
    assert(ring.phase == GPU31U_DONE && f.copies == 1 && f.publishes == 1);
}
static void wide_offsets(void)
{
    struct gpu31u_ring ring = {0};
    struct fixture f = fixture(&ring);
    struct gpu31u_ops ops = operations(&f);
    assert(gpu31u_begin(&ring, UINT32_MAX, UINT32_MAX - 1, 0,
        (uint64_t)UINT32_MAX * 72, 1, &ops) == GPU31U_OK);
    assert(gpu31u_next(&ring) == GPU31U_OK);
    assert(f.offset == (uint64_t)(UINT32_MAX - 1) * 72 && f.published == 0);
}
static void later_failure_receipt(void)
{
    struct gpu31u_ring ring = {0};
    struct fixture f = fixture(&ring);
    struct gpu31u_ops ops = operations(&f);
    assert(gpu31u_begin(&ring, 3, 0, 2, 216, 1, &ops) == GPU31U_OK);
    assert(gpu31u_next(&ring) == GPU31U_OK);
    f.copy_ok = false; f.ordered = 0;
    assert(gpu31u_next(&ring) == GPU31U_COPY_FAILED);
    assert(!ring.record_valid && !ring.publication_attempted && ring.consumer == 1);
    assert(f.copies == 2 && f.publishes == 1);
}
int main(void)
{
    arguments(); bounded_drain(); types(); failures(); status_and_reentrancy();
    wide_offsets(); later_failure_receipt();
    puts("GPU31U_RING_PASS");
    return 0;
}
