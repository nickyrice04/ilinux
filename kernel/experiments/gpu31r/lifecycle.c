/* SPDX-License-Identifier: MIT */
#include "lifecycle.h"
#include <stddef.h>

static int valid(const struct gpu31r_state *s)
{
    unsigned i;
    if (!s || s->active > 1 || s->preload_known > 1 || s->preloaded > 1 ||
        s->subscriptions > 1 || s->payload_kind > GPU31R_PAYLOAD_DATA_SUCCESS ||
        (!s->preload_known && s->preloaded) ||
        (s->payload_kind < GPU31R_PAYLOAD_NULL_SUCCESS && s->payload_length) ||
        (s->payload_kind == GPU31R_PAYLOAD_DATA_SUCCESS && !s->payload_length))
        return 0;
    if (!s->epoch && (s->sequence || s->active)) return 0;
    for (i = 0; i < 2; i++)
        if (s->endpoints[i].accepted > 1 ||
            (!s->endpoints[i].instance && s->endpoints[i].accepted)) return 0;
    if (!s->active && (s->preload_known || s->preloaded || s->subscriptions ||
        s->payload_kind || s->payload_length || s->endpoints[0].instance ||
        s->endpoints[1].instance)) return 0;
    return 1;
}

int gpu31r_begin(struct gpu31r_state *s, uint64_t epoch)
{
    struct gpu31r_state fresh = {0};
    if (!valid(s) || !epoch) return GPU31R_INVALID;
    if (epoch <= s->epoch) return GPU31R_STALE;
    fresh.epoch = epoch;
    fresh.active = 1;
    *s = fresh;
    return GPU31R_APPLIED;
}

int gpu31r_apply(struct gpu31r_state *s, const struct gpu31r_event *e)
{
    struct gpu31r_state next;
    struct gpu31r_endpoint *endpoint;
    int result = GPU31R_APPLIED;
    if (!valid(s) || !e || !s->active || !e->sequence ||
        e->kind < GPU31R_PRELOAD || e->kind > GPU31R_REJECT)
        return GPU31R_INVALID;
    if (e->epoch != s->epoch || e->sequence <= s->sequence) return GPU31R_STALE;
    next = *s;
    switch (e->kind) {
    case GPU31R_PRELOAD:
        if (e->slot || e->instance || e->length || e->value > 1 ||
            (s->preload_known && s->preloaded != e->value)) return GPU31R_INVALID;
        next.preload_known = 1;
        next.preloaded = e->value;
        break;
    case GPU31R_PAYLOAD:
        if (e->slot || e->instance || e->value < GPU31R_PAYLOAD_FAILED ||
            e->value > GPU31R_PAYLOAD_DATA_SUCCESS ||
            (e->value == GPU31R_PAYLOAD_FAILED && e->length) ||
            (e->value == GPU31R_PAYLOAD_DATA_SUCCESS && !e->length))
            return GPU31R_INVALID;
        next.payload_kind = e->value;
        next.payload_length = e->length;
        break;
    case GPU31R_SUBSCRIPTIONS:
        if (e->slot || e->instance || e->length || e->value) return GPU31R_INVALID;
        next.subscriptions = 1;
        break;
    case GPU31R_MATCH:
    case GPU31R_ACCEPT:
    case GPU31R_TERMINATE:
    case GPU31R_REJECT:
        if (e->slot > 1 || !e->instance || e->length || e->value) return GPU31R_INVALID;
        endpoint = &next.endpoints[e->slot];
        if (e->kind == GPU31R_MATCH) {
            if (endpoint->instance != e->instance) {
                endpoint->instance = e->instance;
                endpoint->accepted = 0;
            }
        } else if (endpoint->instance != e->instance) {
            result = GPU31R_IGNORED_INSTANCE;
        } else if (e->kind == GPU31R_ACCEPT) {
            endpoint->accepted = 1;
        } else {
            endpoint->instance = 0;
            endpoint->accepted = 0;
        }
        break;
    case GPU31R_PROVIDER_END: {
        struct gpu31r_state ended = {0};
        if (e->slot || e->instance || e->length || e->value) return GPU31R_INVALID;
        ended.epoch = s->epoch;
        next = ended;
        break;
    }
    default: return GPU31R_INVALID;
    }
    next.sequence = e->sequence;
    *s = next;
    return result;
}

int gpu31r_inspect(const struct gpu31r_state *s, struct gpu31r_view *v)
{
    struct gpu31r_view out = {0};
    unsigned i;
    if (!valid(s) || !v) return GPU31R_INVALID;
    out.active = s->active;
    out.preload_known = s->preload_known;
    out.preloaded = s->preloaded;
    out.subscriptions = s->subscriptions;
    out.payload_kind = s->payload_kind;
    out.payload_length = s->payload_length;
    for (i = 0; i < 2; i++) {
        if (s->endpoints[i].instance) out.matched++;
        out.accepted += s->endpoints[i].accepted;
    }
    *v = out;
    return GPU31R_APPLIED;
}
