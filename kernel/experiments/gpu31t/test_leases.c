/* SPDX-License-Identifier: MIT */
#include "leases.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

struct event { char kind; uint64_t resource, lease; };
struct fixture {
    struct gpu31t_batch batch;
    struct gpu31t_prepared replies[GPU31T_MAX_LEASES];
    struct gpu31t_completed completions[GPU31T_MAX_LEASES];
    uint64_t ids[GPU31T_MAX_LEASES];
    struct event events[GPU31T_MAX_LEASES * 2];
    size_t prepares, completes, events_count;
    bool reenter;
};
static struct gpu31t_ops operations(struct fixture *f);
static void check_reentry(struct fixture *f)
{
    if (!f->reenter) return;
    struct gpu31t_ops ops = operations(f);
    assert(gpu31t_prepare(&f->batch, &ops, f->ids, 1) == GPU31T_STATE);
    assert(gpu31t_finish(&f->batch) == GPU31T_STATE);
}
static struct gpu31t_prepared prepare(void *context, uint64_t resource)
{
    struct fixture *f = context;
    assert(f->batch.phase == GPU31T_PREPARING);
    assert(f->prepares < GPU31T_MAX_LEASES);
    size_t i = f->prepares++;
    assert(resource == f->ids[i]);
    f->events[f->events_count++] = (struct event){'P', resource, 0};
    check_reentry(f);
    return f->replies[i];
}
static struct gpu31t_completed complete(void *context, uint64_t resource, uint64_t lease)
{
    struct fixture *f = context;
    assert(f->batch.phase == GPU31T_CLEANING);
    size_t i;
    for (i = 0; i < f->prepares; ++i)
        if (f->replies[i].lease == lease && f->ids[i] == resource) break;
    assert(i < f->prepares && f->replies[i].cleanup_required);
    assert(f->batch.entries[i].cleanup_attempted);
    ++f->completes;
    f->events[f->events_count++] = (struct event){'C', resource, lease};
    check_reentry(f);
    return f->completions[i];
}
static struct gpu31t_ops operations(struct fixture *f)
{
    return (struct gpu31t_ops){prepare, complete, f};
}
static void init(struct fixture *f)
{
    memset(f, 0, sizeof(*f));
    for (size_t i = 0; i < GPU31T_MAX_LEASES; ++i) {
        f->ids[i] = 10 + i;
        f->replies[i] = (struct gpu31t_prepared){true, true, 0, 1000 + i};
        f->completions[i] = (struct gpu31t_completed){true, 0};
    }
}
static enum gpu31t_result acquire(struct fixture *f, size_t n)
{
    struct gpu31t_ops ops = operations(f);
    return gpu31t_prepare(&f->batch, &ops, f->ids, n);
}
static void arguments(void)
{
    struct fixture f; init(&f);
    struct gpu31t_ops ops = operations(&f), bad = ops;
    unsigned char before[sizeof(f.batch)]; memcpy(before, &f.batch, sizeof before);
    assert(gpu31t_prepare(NULL, &ops, f.ids, 1) == GPU31T_ARGUMENT);
    assert(gpu31t_prepare(&f.batch, NULL, f.ids, 1) == GPU31T_ARGUMENT);
    assert(gpu31t_prepare(&f.batch, &ops, NULL, 1) == GPU31T_ARGUMENT);
    assert(acquire(&f, 0) == GPU31T_ARGUMENT);
    assert(acquire(&f, GPU31T_MAX_LEASES + 1) == GPU31T_ARGUMENT);
    assert(acquire(&f, SIZE_MAX) == GPU31T_ARGUMENT);
    bad.prepare = NULL;
    assert(gpu31t_prepare(&f.batch, &bad, f.ids, 1) == GPU31T_ARGUMENT);
    bad = ops; bad.complete = NULL;
    assert(gpu31t_prepare(&f.batch, &bad, f.ids, 1) == GPU31T_ARGUMENT);
    assert(gpu31t_finish(NULL) == GPU31T_ARGUMENT);
    assert(gpu31t_finish(&f.batch) == GPU31T_STATE);
    assert(memcmp(before, &f.batch, sizeof before) == 0 && f.events_count == 0);
}
static void success(void)
{
    struct fixture f; init(&f);
    assert(acquire(&f, 3) == GPU31T_OK && f.batch.phase == GPU31T_PREPARED);
    assert(f.prepares == 3 && f.completes == 0);
    assert(gpu31t_finish(&f.batch) == GPU31T_OK && f.batch.phase == GPU31T_RELEASED);
    assert(f.events_count == 6);
    for (size_t i = 0; i < 3; ++i) {
        assert(f.events[i].kind == 'P' && f.events[i].resource == 10 + i);
        assert(f.events[3 + i].kind == 'C' && f.events[3 + i].resource == 12 - i);
    }
}
static void first_failure(void)
{
    struct fixture f; init(&f); f.replies[0].accepted = false;
    assert(acquire(&f, 3) == GPU31T_PREPARE_FAILED);
    assert(f.prepares == 1 && f.completes == 1 && f.batch.phase == GPU31T_FAILED);
    assert(!f.batch.entries[0].preparation.accepted && f.batch.entries[0].cleanup_attempted);
}
static void owned_failure(void)
{
    struct fixture f; init(&f); f.replies[2].accepted = false;
    assert(acquire(&f, 5) == GPU31T_PREPARE_FAILED);
    assert(f.prepares == 3 && f.completes == 3);
    assert(f.events[3].resource == 12 && f.events[4].resource == 11 && f.events[5].resource == 10);
}
static void unowned_failure(void)
{
    struct fixture f; init(&f); f.replies[2].accepted = false; f.replies[2].cleanup_required = false;
    assert(acquire(&f, 4) == GPU31T_PREPARE_FAILED);
    assert(f.prepares == 3 && f.completes == 2 && !f.batch.entries[2].cleanup_attempted);
}
static void borrowed(void)
{
    struct fixture f; init(&f);
    for (size_t i = 0; i < 4; ++i) f.replies[i].cleanup_required = false;
    assert(acquire(&f, 4) == GPU31T_OK && gpu31t_finish(&f.batch) == GPU31T_OK);
    assert(f.completes == 0);
}
static void pending_success(void)
{
    struct fixture f; init(&f); f.completions[1] = (struct gpu31t_completed){false, 7};
    assert(acquire(&f, 3) == GPU31T_OK && gpu31t_finish(&f.batch) == GPU31T_CLEANUP_PENDING);
    assert(f.batch.phase == GPU31T_UNRESOLVED && f.completes == 3);
    assert(!f.batch.entries[1].completion.released && f.batch.entries[1].completion.status == 7);
    assert(f.batch.entries[1].preparation.lease == 1001);
}
static void pending_failure(void)
{
    struct fixture f; init(&f); f.replies[1].accepted = false; f.completions[1].released = false;
    assert(acquire(&f, 4) == GPU31T_PREPARE_FAILED && f.batch.phase == GPU31T_UNRESOLVED);
    assert(f.prepares == 2 && f.completes == 2 && !f.batch.entries[1].completion.released);
    init(&f);
    f.replies[1].cleanup_required = false;
    f.replies[3].accepted = false;
    f.completions[0] = (struct gpu31t_completed){false, 11};
    f.completions[3] = (struct gpu31t_completed){false, 19};
    assert(acquire(&f, 5) == GPU31T_PREPARE_FAILED && f.batch.phase == GPU31T_UNRESOLVED);
    assert(f.prepares == 4 && f.completes == 3);
    assert(f.events[4].resource == 13 && f.events[5].resource == 12 && f.events[6].resource == 10);
    assert(!f.batch.entries[1].cleanup_attempted && f.batch.entries[2].completion.released);
    assert(!f.batch.entries[0].completion.released && f.batch.entries[0].completion.status == 11);
    assert(!f.batch.entries[3].completion.released && f.batch.entries[3].completion.status == 19);
    assert(f.batch.entries[0].preparation.lease == 1000 && f.batch.entries[3].preparation.lease == 1003);
    assert(gpu31t_finish(&f.batch) == GPU31T_STATE && f.completes == 3);
}
static void opaque_status(void)
{
    struct fixture f; init(&f);
    f.replies[0].status = UINT32_MAX; f.replies[0].lease = 0; f.ids[0] = 0;
    f.completions[0].status = UINT32_MAX;
    assert(acquire(&f, 1) == GPU31T_OK && gpu31t_finish(&f.batch) == GPU31T_OK);
    assert(f.batch.entries[0].preparation.status == UINT32_MAX);
    assert(f.batch.entries[0].completion.status == UINT32_MAX && f.events[1].lease == 0);
}
static void one_shot(void)
{
    for (unsigned mode = 0; mode < 3; ++mode) {
        struct fixture f; init(&f);
        if (mode == 1) f.replies[0].accepted = false;
        if (mode == 2) f.completions[0].released = false;
        (void)acquire(&f, 1);
        if (mode != 1) (void)gpu31t_finish(&f.batch);
        size_t calls = f.events_count;
        unsigned char before[sizeof(f.batch)]; memcpy(before, &f.batch, sizeof before);
        assert(acquire(&f, 1) == GPU31T_STATE && gpu31t_finish(&f.batch) == GPU31T_STATE);
        assert(f.events_count == calls && memcmp(before, &f.batch, sizeof before) == 0);
    }
}
static void reentrancy(void)
{
    struct fixture f; init(&f); f.reenter = true;
    assert(acquire(&f, 3) == GPU31T_OK && gpu31t_finish(&f.batch) == GPU31T_OK);
    init(&f); f.reenter = true; f.replies[1].accepted = false;
    assert(acquire(&f, 3) == GPU31T_PREPARE_FAILED && f.events_count == 4);
}
static void maximum(void)
{
    struct fixture f; init(&f);
    assert(acquire(&f, GPU31T_MAX_LEASES) == GPU31T_OK);
    assert(gpu31t_finish(&f.batch) == GPU31T_OK && f.events_count == 2 * GPU31T_MAX_LEASES);
}
static void shared_resource(void)
{
    struct fixture f; init(&f); f.ids[1] = f.ids[0];
    assert(acquire(&f, 2) == GPU31T_OK && gpu31t_finish(&f.batch) == GPU31T_OK);
    assert(f.events[2].lease == 1001 && f.events[3].lease == 1000);
}
static void failure_matrix(void)
{
    for (size_t n = 1; n <= GPU31T_MAX_LEASES; ++n)
        for (size_t stop = 0; stop <= n; ++stop)
            for (unsigned mask = 0; mask < 16; ++mask) {
                struct fixture f; init(&f);
                for (size_t i = 0; i < n; ++i) {
                    f.replies[i].accepted = i != stop;
                    f.replies[i].cleanup_required = ((mask >> (i % 4)) & 1u) != 0;
                }
                enum gpu31t_result result = acquire(&f, n);
                assert(result == (stop < n ? GPU31T_PREPARE_FAILED : GPU31T_OK));
                if (stop == n) assert(gpu31t_finish(&f.batch) == GPU31T_OK);
                size_t attempted = stop < n ? stop + 1 : n, cleaned = 0;
                assert(f.prepares == attempted);
                for (size_t i = attempted; i != 0; --i)
                    if (((mask >> ((i - 1) % 4)) & 1u) != 0) {
                        const struct event *e = &f.events[attempted + cleaned++];
                        assert(e->kind == 'C' && e->resource == 9 + i);
                    }
                assert(f.completes == cleaned && f.events_count == attempted + cleaned);
            }
}
int main(void)
{
    arguments(); success(); first_failure(); owned_failure(); unowned_failure();
    borrowed(); pending_success(); pending_failure(); opaque_status(); one_shot();
    reentrancy(); maximum(); shared_resource(); failure_matrix();
    puts("GPU31T_LEASES_PASS");
    return 0;
}
