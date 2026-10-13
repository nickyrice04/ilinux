#include "ring_math.h"

#include <assert.h>
#include <inttypes.h>
#include <stddef.h>
#include <stdio.h>

static bool equal_queue(struct acipc_software_queue a,
                        struct acipc_software_queue b)
{
    return a.slots == b.slots && a.head == b.head && a.tail == b.tail;
}

static uint64_t test_queue_model(void)
{
    uint64_t cases = 0;
    for (uint64_t slots = 1; slots <= 20; ++slots) {
        for (uint64_t head = 0; head < slots; ++head) {
            for (uint64_t tail = 0; tail < slots; ++tail) {
                struct acipc_software_queue initial = {slots, head, tail};
                uint64_t expected_used = 0, used;
                /* Independent small-state reference: walk occupied slots. */
                for (uint64_t at = tail; at != head; at = at + 1 == slots ? 0 : at + 1)
                    ++expected_used;
                assert(acipc_queue_occupancy(&initial, &used) && used == expected_used);
                for (uint64_t count = 0; count <= slots + 1; ++count) {
                    struct acipc_software_queue queue = initial;
                    bool accepted = count <= slots - 1 - expected_used;
                    assert(acipc_queue_push(&queue, count) == accepted);
                    if (accepted) {
                        assert(acipc_queue_occupancy(&queue, &used));
                        assert(used == expected_used + count && queue.tail == tail);
                        assert(acipc_queue_pop(&queue, count));
                    }
                    /* Push/pop undo occupancy, not necessarily physical indices. */
                    if (accepted) {
                        assert(acipc_queue_occupancy(&queue, &used) && used == expected_used);
                    } else {
                        assert(equal_queue(queue, initial));
                    }
                    queue = initial;
                    accepted = count <= expected_used;
                    assert(acipc_queue_pop(&queue, count) == accepted);
                    if (accepted) {
                        assert(acipc_queue_occupancy(&queue, &used));
                        assert(used == expected_used - count && queue.head == head);
                    } else {
                        assert(equal_queue(queue, initial));
                    }
                    ++cases;
                }
            }
        }
    }
    struct acipc_software_queue queue = {UINT64_MAX, UINT64_MAX - 1, UINT64_MAX - 1};
    uint64_t used;
    assert(acipc_queue_push(&queue, UINT64_MAX - 1));
    assert(queue.head == UINT64_MAX - 2);
    assert(acipc_queue_occupancy(&queue, &used) && used == UINT64_MAX - 1);
    struct acipc_software_queue saved = queue;
    assert(!acipc_queue_push(&queue, 1) && equal_queue(queue, saved));
    assert(!acipc_queue_pop(&queue, UINT64_MAX) && equal_queue(queue, saved));
    assert(acipc_queue_pop(&queue, UINT64_MAX - 1));
    assert(queue.tail == queue.head);
    saved = queue;
    assert(!acipc_queue_pop(&queue, 1) && equal_queue(queue, saved));
    queue = (struct acipc_software_queue){UINT64_MAX, 1, UINT64_MAX - 1};
    assert(acipc_queue_occupancy(&queue, &used) && used == 2);
    assert(acipc_queue_pop(&queue, 2) && queue.tail == 1);
    assert(!acipc_queue_init(&queue, 0) && queue.tail == 1);
    assert(acipc_queue_init(&queue, 1));
    assert(acipc_queue_push(&queue, 0) && acipc_queue_pop(&queue, 0));
    assert(!acipc_queue_push(&queue, 1));
    for (unsigned bad = 0; bad < 3; ++bad) {
        queue = (struct acipc_software_queue){5, 0, 0};
        if (bad == 0) queue.slots = 0;
        if (bad == 1) queue.head = 5;
        if (bad == 2) queue.tail = 5;
        saved = queue;
        used = 123;
        assert(!acipc_queue_occupancy(&queue, &used) && used == 123);
        assert(!acipc_queue_push(&queue, 0) && equal_queue(queue, saved));
        assert(!acipc_queue_pop(&queue, 0) && equal_queue(queue, saved));
    }
    assert(!acipc_queue_init(NULL, 5));
    assert(!acipc_queue_occupancy(NULL, &used));
    assert(!acipc_queue_occupancy(&queue, NULL));
    assert(!acipc_queue_push(NULL, 1) && !acipc_queue_pop(NULL, 1));
    return cases;
}

int main(void)
{
    uint64_t queue_cases = test_queue_model();
    /* Deliberately includes observed non-power-of-two plist values. */
    const uint64_t sizes[] = {1, 2, 4, 5, 9, 16, 17, 64, 96, 128, 192, 2048};
    uint64_t cases = 0, next, index, steps, expected;
    struct acipc_buffer_span span;

    for (size_t n = 0; n < sizeof(sizes) / sizeof(sizes[0]); ++n) {
        uint64_t slots = sizes[n];
        for (index = 0; index < slots; ++index) {
            expected = index;
            for (steps = 0; steps < 2 * slots + 1; ++steps) {
                assert(acipc_index_advance(slots, index, steps, &next));
                assert(next == expected);
                expected = expected + 1 == slots ? 0 : expected + 1;
                ++cases;
            }
            assert(acipc_slot_span(slots, 260, index, slots * 260, &span));
            assert(span.offset == index * 260 && span.length == 260);
        }
    }

    assert(acipc_index_advance(UINT64_MAX, UINT64_MAX - 1,
                              UINT64_MAX - 1, &next));
    assert(next == UINT64_MAX - 2);
    assert(acipc_index_advance(17, 16, UINT64_MAX, &next));
    assert(next == 16); /* UINT64_MAX is divisible by 17. */
    assert(acipc_index_advance(1, 0, UINT64_MAX, &next) && next == 0);
    /* A power-of-two mask would return zero instead of one here. */
    assert(acipc_index_advance(5, 0, 1, &next) && next == 1);

    next = 123;
    assert(!acipc_index_advance(0, 0, 1, &next) && next == 123);
    assert(!acipc_index_advance(5, 5, 1, &next) && next == 123);
    assert(!acipc_index_advance(5, 0, 1, NULL));
    span = (struct acipc_buffer_span){123, 456};
    assert(!acipc_slot_span(17, 260, 16, 17 * 260 - 1, &span));
    assert(span.offset == 123 && span.length == 456);
    assert(!acipc_slot_span(UINT64_MAX, 2, 0, UINT64_MAX, &span));
    assert(!acipc_slot_span(5, 260, 5, 5 * 260, &span));
    assert(!acipc_slot_span(0, 260, 0, 0, &span));
    assert(!acipc_slot_span(5, 0, 0, 0, &span));
    assert(!acipc_slot_span(5, 260, 0, 1300, NULL));
    assert(acipc_span_valid(10, (struct acipc_buffer_span){10, 0}));
    assert(!acipc_span_valid(10, (struct acipc_buffer_span){11, 0}));
    assert(!acipc_span_valid(10, (struct acipc_buffer_span){9, 2}));
    assert(!acipc_span_valid(UINT64_MAX,
                            (struct acipc_buffer_span){UINT64_MAX, 1}));
    printf("ACIPC software ring arithmetic: %" PRIu64 " wrap cases pass; "
           "bounds/overflow cases pass; no hardware access\n", cases);
    printf("ACIPC one-empty-slot software queue: %" PRIu64 " state/count cases pass\n", queue_cases);
    return 0;
}
