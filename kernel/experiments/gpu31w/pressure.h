/* SPDX-License-Identifier: MIT */
#ifndef ILINUX_GPU31W_PRESSURE_H
#define ILINUX_GPU31W_PRESSURE_H
#include "../gpu31v/mapping.h"

#define GPU31W_NOTE UINT64_C(0x0085000000000000)
#define GPU31W_PROVIDER_ROLE 0u
#define GPU31W_ENDPOINT 0x21u
enum gpu31w_phase { GPU31W_FRESH=0, GPU31W_PREPARED, GPU31W_FULL,
    GPU31W_BUSY, GPU31W_DONE, GPU31W_STOPPED };
enum gpu31w_result { GPU31W_OK=0, GPU31W_QUEUE_FULL, GPU31W_ARGUMENT,
    GPU31W_STATE, GPU31W_NOTE_UNKNOWN, GPU31W_WRITE_UNKNOWN,
    GPU31W_PUBLISH_UNKNOWN };
struct gpu31w_transport {
    uint32_t provider_role, endpoint;
    struct gpu31v_effect (*note)(void *context, uint32_t endpoint,
        uint64_t word, bool flag);
    void *context;
};
struct gpu31w_submission {
    enum gpu31w_phase phase;
    /* Read-only receipt to callers; only the31W API may drive this object. */
    struct gpu31v_submission mapping;
    struct gpu31w_transport transport;
    bool note_required, note_attempted, note_accepted;
    uint64_t note_word;
    uint32_t note_status;
};

/* Original one-attempt composition of the selected host-side contract. Numeric
 * role0 is not an ADT GPU identity. Caller must independently qualify the role,
 * endpoint, provider's admitted direct-send path, firmware version and lifetime.
 * The endpoint must be non-null and its provider's direct-send guard must admit
 * the send. Values in this structure cannot prove that qualification. No native adapter
 * is supplied. The word is opaque: it is NOT labeled a wake/flush. Another
 * version's public implementation calls0x85 halt; do not deploy from this test.
 * The flag is the checked false argument, not an assigned priority convention.
 * All31V mapping preconditions remain; keep sole-producer ownership and acquired
 * snapshot/mapping validity across prepare, note and publish. Zero-initialize
 * untampered state, forbid aliasing, and serialize externally. */
enum gpu31w_result gpu31w_prepare(struct gpu31w_submission *submission,
    const struct gpu31v_mapping *mapping, uint32_t consumer, uint32_t producer,
    uint64_t mapped_bytes, const struct gpu31v_ops *ops,
    const struct gpu31w_transport *transport);

/* One free entry in the captured256-slot ring requires the note BEFORE writing
 * the record. Full refuses without note/wait; other positions need no note.
 * Adapter acceptance is separate from opaque status. A suppressed/uncertain
 * note must return accepted=false even if a private provider returned status0.
 * Refusal can have effects: retain the receipt and stop without retry/reuse.
 * Accepted note is not firmware consumption or completion. Do not issue a
 * follow-up action after unknown effects or construct a new object to retry.
 * Bounded synchronous callbacks cannot mutate state, drive the embedded31V
 * object through another API, or retain its pointers.
 * Reentry is refused. Actual DMA ordering remains the31V publish adapter's job. */
enum gpu31w_result gpu31w_submit(struct gpu31w_submission *submission);
#endif
