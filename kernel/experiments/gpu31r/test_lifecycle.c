/* SPDX-License-Identifier: MIT */
#include "lifecycle.h"
#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>

static unsigned groups;
static struct gpu31r_state start(uint64_t epoch)
{
    struct gpu31r_state s = {0};
    assert(gpu31r_begin(&s, epoch) == GPU31R_APPLIED);
    return s;
}
static int event(struct gpu31r_state *s, unsigned kind, unsigned slot,
                 uint64_t instance, unsigned value, uint64_t length)
{
    struct gpu31r_event e = {s->epoch, s->sequence + 1, instance, length, kind, slot, value};
    return gpu31r_apply(s, &e);
}
static void inspect(const struct gpu31r_state *s, unsigned matched, unsigned accepted)
{
    struct gpu31r_view v;
    assert(gpu31r_inspect(s, &v) == GPU31R_APPLIED);
    assert(v.matched == matched && v.accepted == accepted && !v.native_ready);
}
static void refused(struct gpu31r_state *s, struct gpu31r_event e, int expected)
{
    unsigned char before[sizeof *s];
    memcpy(before, s, sizeof *s);
    assert(gpu31r_apply(s, &e) == expected);
    assert(memcmp(before, s, sizeof *s) == 0);
}
static void basics(void)
{
    struct gpu31r_state s = {0};
    struct gpu31r_view v = {0};
    struct gpu31r_event e = {0};
    inspect(&s, 0, 0);
    assert(gpu31r_begin(NULL, 1) == GPU31R_INVALID);
    assert(gpu31r_apply(NULL, &e) == GPU31R_INVALID);
    assert(gpu31r_inspect(NULL, &v) == GPU31R_INVALID);
    assert(gpu31r_inspect(&s, NULL) == GPU31R_INVALID);
    assert(gpu31r_begin(&s, 0) == GPU31R_INVALID);
    refused(&s, e, GPU31R_INVALID); groups++;

    assert(gpu31r_begin(&s, 9) == GPU31R_APPLIED);
    assert(s.epoch == 9 && s.active && !s.sequence);
    assert(gpu31r_begin(&s, 9) == GPU31R_STALE);
    assert(gpu31r_begin(&s, 8) == GPU31R_STALE); groups++;

    e.epoch = 8; e.sequence = 1; e.kind = GPU31R_SUBSCRIPTIONS;
    refused(&s, e, GPU31R_STALE);
    e.epoch = 10; refused(&s, e, GPU31R_STALE);
    e.epoch = 9; assert(gpu31r_apply(&s, &e) == GPU31R_APPLIED);
    refused(&s, e, GPU31R_STALE);
    e.sequence = 0; refused(&s, e, GPU31R_INVALID); groups++;

    e.sequence = 2; e.kind = 0; refused(&s, e, GPU31R_INVALID);
    e.kind = UINT_MAX; refused(&s, e, GPU31R_INVALID);
    assert(gpu31r_apply(&s, NULL) == GPU31R_INVALID); groups++;
}
static void evidence(void)
{
    struct gpu31r_state s = start(1);
    struct gpu31r_view v;
    assert(event(&s, GPU31R_PAYLOAD, 0, 0, GPU31R_PAYLOAD_NULL_SUCCESS, 8) == 0);
    gpu31r_inspect(&s, &v);
    assert(v.payload_length == 8 && !v.preload_known && !v.subscriptions);
    inspect(&s, 0, 0); groups++;

    assert(event(&s, GPU31R_PRELOAD, 0, 0, 1, 0) == 0);
    assert(event(&s, GPU31R_PRELOAD, 0, 0, 1, 0) == 0);
    gpu31r_inspect(&s, &v);
    assert(v.preload_known && v.preloaded && !v.matched);
    { struct gpu31r_event e = {1, s.sequence+1, 0, 0, GPU31R_PRELOAD, 0, 0};
      refused(&s, e, GPU31R_INVALID); }
    groups++;

    assert(event(&s, GPU31R_PAYLOAD, 0, 0, GPU31R_PAYLOAD_FAILED, 0) == 0);
    assert(s.preloaded && !s.payload_length && s.payload_kind == GPU31R_PAYLOAD_FAILED);
    assert(event(&s, GPU31R_PAYLOAD, 0, 0, GPU31R_PAYLOAD_DATA_SUCCESS, UINT64_MAX) == 0);
    assert(s.payload_length == UINT64_MAX); groups++;

    assert(event(&s, GPU31R_SUBSCRIPTIONS, 0, 0, 0, 0) == 0);
    assert(event(&s, GPU31R_SUBSCRIPTIONS, 0, 0, 0, 0) == 0);
    inspect(&s, 0, 0); groups++;
}
static void callbacks(void)
{
    struct gpu31r_state s = start(3);
    /* Reentrant callbacks may arrive before registration returns. */
    assert(event(&s, GPU31R_MATCH, 0, 77, 0, 0) == 0);
    inspect(&s, 1, 0);
    assert(event(&s, GPU31R_ACCEPT, 0, 77, 0, 0) == 0);
    inspect(&s, 1, 1);
    assert(!s.subscriptions);
    assert(event(&s, GPU31R_SUBSCRIPTIONS, 0, 0, 0, 0) == 0); groups++;

    assert(event(&s, GPU31R_ACCEPT, 1, 55, 0, 0) == GPU31R_IGNORED_INSTANCE);
    inspect(&s, 1, 1); groups++;

    assert(event(&s, GPU31R_MATCH, 0, 78, 0, 0) == 0);
    inspect(&s, 1, 0);
    assert(event(&s, GPU31R_ACCEPT, 0, 77, 0, 0) == GPU31R_IGNORED_INSTANCE);
    assert(event(&s, GPU31R_TERMINATE, 0, 77, 0, 0) == GPU31R_IGNORED_INSTANCE);
    inspect(&s, 1, 0);
    assert(s.endpoints[0].instance == 78); groups++;

    assert(event(&s, GPU31R_ACCEPT, 0, 78, 0, 0) == 0);
    assert(event(&s, GPU31R_MATCH, 0, 78, 0, 0) == 0);
    inspect(&s, 1, 1); groups++;

    assert(event(&s, GPU31R_MATCH, 1, 99, 0, 0) == 0);
    assert(event(&s, GPU31R_ACCEPT, 1, 99, 0, 0) == 0);
    inspect(&s, 2, 2);
    assert(event(&s, GPU31R_TERMINATE, 0, 78, 0, 0) == 0);
    inspect(&s, 1, 1);
    assert(s.endpoints[1].instance == 99); groups++;

    assert(event(&s, GPU31R_REJECT, 1, 98, 0, 0) == GPU31R_IGNORED_INSTANCE);
    inspect(&s, 1, 1);
    assert(event(&s, GPU31R_REJECT, 1, 99, 0, 0) == 0);
    inspect(&s, 0, 0); groups++;

    assert(gpu31r_begin(&s, 4) == 0);
    inspect(&s, 0, 0);
    assert(!s.preload_known && !s.payload_kind && !s.subscriptions);
    { struct gpu31r_event e = {3, UINT64_MAX, 99, 0, GPU31R_ACCEPT, 1, 0};
      refused(&s, e, GPU31R_STALE); }
    groups++;

    assert(event(&s, GPU31R_MATCH, 1, 99, 0, 0) == 0);
    assert(event(&s, GPU31R_PROVIDER_END, 0, 0, 0, 0) == 0);
    inspect(&s, 0, 0);
    assert(!s.active && s.epoch == 4);
    assert(event(&s, GPU31R_MATCH, 1, 99, 0, 0) == GPU31R_INVALID);
    assert(gpu31r_begin(&s, 4) == GPU31R_STALE);
    assert(gpu31r_begin(&s, 5) == 0); groups++;
}
static void validation(void)
{
    struct gpu31r_state s = start(1);
    struct gpu31r_event e = {1, 1, 0, 0, GPU31R_SUBSCRIPTIONS, 0, 0};
    unsigned kind;
    for (kind = GPU31R_PRELOAD; kind <= GPU31R_REJECT; kind++) {
        e.kind = kind; e.slot = UINT_MAX;
        refused(&s, e, GPU31R_INVALID);
    }
    e.kind = GPU31R_MATCH; e.slot = 0;
    refused(&s, e, GPU31R_INVALID);
    e.instance = 1; e.length = 1; refused(&s, e, GPU31R_INVALID);
    e.length = 0; e.value = 1; refused(&s, e, GPU31R_INVALID);
    e.kind = GPU31R_SUBSCRIPTIONS; e.value = 0; refused(&s, e, GPU31R_INVALID);
    e.instance = 0; e.value = 1; refused(&s, e, GPU31R_INVALID); groups++;

    e.kind = GPU31R_PAYLOAD; e.value = GPU31R_PAYLOAD_UNKNOWN;
    refused(&s, e, GPU31R_INVALID);
    e.value = GPU31R_PAYLOAD_FAILED; e.length = 1; refused(&s, e, GPU31R_INVALID);
    e.value = GPU31R_PAYLOAD_DATA_SUCCESS; e.length = 0; refused(&s, e, GPU31R_INVALID);
    e.value = UINT_MAX; refused(&s, e, GPU31R_INVALID); groups++;

    { struct gpu31r_view v, before;
      memset(&v, 0xa5, sizeof v); memcpy(&before, &v, sizeof v);
      s.endpoints[1].accepted = 1;
      assert(gpu31r_inspect(&s, &v) == GPU31R_INVALID);
      assert(memcmp(&v, &before, sizeof v) == 0);
      assert(gpu31r_begin(&s, 2) == GPU31R_INVALID);
      refused(&s, e, GPU31R_INVALID); }
    groups++;

    s = start(1);
    s.payload_kind = GPU31R_PAYLOAD_DATA_SUCCESS;
    assert(gpu31r_begin(&s, 2) == GPU31R_INVALID);

    s = start(UINT64_MAX);
    e = (struct gpu31r_event){UINT64_MAX, UINT64_MAX, UINT64_MAX, 0, GPU31R_MATCH, 1, 0};
    assert(gpu31r_apply(&s, &e) == 0);
    inspect(&s, 1, 0);
    refused(&s, e, GPU31R_STALE);
    e.sequence = 0; refused(&s, e, GPU31R_INVALID);
    assert(gpu31r_begin(&s, 1) == GPU31R_STALE); groups++;
}
static void explore(struct gpu31r_state s, unsigned depth)
{
    unsigned choice;
    if (!depth) return;
    for (choice = 0; choice < 8; choice++) {
        struct gpu31r_state next = s;
        unsigned slot = choice & 1;
        unsigned kind = choice < 2 ? GPU31R_MATCH : choice < 4 ? GPU31R_ACCEPT :
                        choice < 6 ? GPU31R_TERMINATE : GPU31R_SUBSCRIPTIONS;
        uint64_t token = kind == GPU31R_SUBSCRIPTIONS ? 0 : (depth & 1) + 1;
        struct gpu31r_view v;
        int r = event(&next, kind, kind == GPU31R_SUBSCRIPTIONS ? 0 : slot, token, 0, 0);
        assert(r == GPU31R_APPLIED || r == GPU31R_IGNORED_INSTANCE);
        assert(gpu31r_inspect(&next, &v) == 0);
        assert(!v.native_ready && v.accepted <= v.matched && v.matched <= 2);
        /* Acceptance can only be introduced by an explicit accept event. */
        if (kind != GPU31R_ACCEPT)
            assert(next.endpoints[slot].accepted <= s.endpoints[slot].accepted);
        explore(next, depth - 1);
    }
}
int main(void)
{
    basics(); evidence(); callbacks(); validation();
    explore(start(1), 5); groups++;
    assert(groups == 21);
    puts("GPU31R_LIFECYCLE_PASS");
    return 0;
}
