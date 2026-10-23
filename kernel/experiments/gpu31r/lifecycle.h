/* SPDX-License-Identifier: MIT */
#ifndef ILINUX_GPU31R_LIFECYCLE_H
#define ILINUX_GPU31R_LIFECYCLE_H
#include <stdint.h>

/* Original offline evidence model. No hardware protocol numbers or pointers. */
enum gpu31r_event_kind {
    GPU31R_PRELOAD = 1, GPU31R_PAYLOAD, GPU31R_SUBSCRIPTIONS,
    GPU31R_MATCH, GPU31R_ACCEPT, GPU31R_TERMINATE, GPU31R_PROVIDER_END,
    GPU31R_REJECT
};
enum gpu31r_payload_kind {
    GPU31R_PAYLOAD_UNKNOWN = 0, GPU31R_PAYLOAD_FAILED,
    GPU31R_PAYLOAD_NULL_SUCCESS, GPU31R_PAYLOAD_DATA_SUCCESS
};
enum gpu31r_result {
    GPU31R_APPLIED = 0, GPU31R_IGNORED_INSTANCE = 1,
    GPU31R_INVALID = -1, GPU31R_STALE = -2
};
struct gpu31r_endpoint {
    uint64_t instance; /* Caller-assigned identity, never a hardware address. */
    unsigned accepted;
};
struct gpu31r_state {
    uint64_t epoch, sequence, payload_length;
    unsigned active, preload_known, preloaded, subscriptions, payload_kind;
    struct gpu31r_endpoint endpoints[2];
};
struct gpu31r_event {
    uint64_t epoch, sequence, instance, length;
    unsigned kind, slot, value;
};
struct gpu31r_view {
    unsigned active, matched, accepted, subscriptions, preload_known, preloaded;
    unsigned payload_kind;
    uint64_t payload_length;
    unsigned native_ready; /* Always zero: this API cannot qualify hardware. */
};

/* Zero-initialize first. Serialize all calls externally (including callbacks).
 * Epochs increase across replacements; sequence increases within an epoch.
 * Invalid/stale inputs leave state untouched. Ignored old-instance events consume
 * their sequence but cannot change the currently attached endpoint.
 * Instance tokens must not be recycled within an epoch. The caller must reject
 * stale MATCH observations before assigning an ingestion sequence; this model
 * cannot authenticate callback identity or reconstruct physical event ordering.
 * Slots are local array positions, NOT ADT roles or firmware selectors. */
int gpu31r_begin(struct gpu31r_state *state, uint64_t epoch);
int gpu31r_apply(struct gpu31r_state *state, const struct gpu31r_event *event);
int gpu31r_inspect(const struct gpu31r_state *state, struct gpu31r_view *view);
#endif
