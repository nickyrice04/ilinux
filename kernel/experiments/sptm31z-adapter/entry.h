/* SPDX-License-Identifier: MIT */
#ifndef ILINUX_SPTM31Z_ENTRY_H
#define ILINUX_SPTM31Z_ENTRY_H

#include <stddef.h>
#include <stdint.h>

/* A version-bound observation, NOT an enabled native hardware profile.
 * The retained/current T6050 25G83 cold consumer copies 848 monitor bytes.
 * None of the measured SDK layouts matches. No field-layout interpolation,
 * length-based profile detection or opaque libsptm_state inspection is supplied.
 * The caller must independently bind the actual source to this observation. */
#define SPTM31Z_MONITOR_BYTES 848u
enum sptm31z_profile { SPTM31Z_NO_PROFILE = 0, SPTM31Z_T6050_25G83_OBSERVED = 1 };
enum sptm31z_kind {
    SPTM31Z_UNRECOGNIZED = 0, SPTM31Z_COLD, SPTM31Z_SECONDARY,
    SPTM31Z_WARM, SPTM31Z_HIBERNATION, SPTM31Z_PANIC
};
enum sptm31z_entry_status {
    SPTM31Z_ENTRY_OK = 0, SPTM31Z_ENTRY_ARGUMENT, SPTM31Z_ENTRY_PROFILE,
    SPTM31Z_ENTRY_UNKNOWN_REASON, SPTM31Z_ENTRY_ROLE,
    SPTM31Z_ENTRY_LENGTH
};
struct sptm31z_entry_words { uint64_t x0, x1, x2; };
struct sptm31z_entry_snapshot {
    enum sptm31z_profile profile;
    enum sptm31z_kind kind;
    struct sptm31z_entry_words raw;
};
struct sptm31z_boot_words { uint64_t iboot_arguments, monitor_arguments; };
struct sptm31z_panic_words { uint64_t message, core_dump_flag; };
/* A physical address value, never an automatically dereferenceable C pointer. */
struct sptm31z_physical_address { uint64_t value; };
struct sptm31z_monitor_snapshot {
    struct sptm31z_entry_snapshot entry;
    /* ONLY independently checked local field: little-endian u64 at byte24.
     * This decoded value still needs RAM, alignment and ownership validation. */
    struct sptm31z_physical_address first_available;
    /* Contains potentially sensitive seed/state bytes on a real system.
     * Keep private. This library has no logging or serialization routine. */
    uint8_t private_bytes[SPTM31Z_MONITOR_BYTES];
};

/* Classify the FULL 64-bit x0 word. The local entry confirms cold0/panic4;
 * secondary1/warm2/hibernation3 are labels from the SDK26.5 comparator,
 * not proof of those local producer paths. No truncation to a byte-wide enum.
 * UNKNOWN_REASON retains all three raw words but grants neither argument role.
 * Unsupported profile/invalid C argument leaves output unchanged.
 * Captured words are untrusted numeric observations; they are never dereferenced.
 */
enum sptm31z_entry_status sptm31z_capture_entry(enum sptm31z_profile profile,
    struct sptm31z_entry_words words, struct sptm31z_entry_snapshot *output);

/* Explicit role accessors. Only COLD yields typed boot-argument words in this
 * prototype. This is a conservative local-evidence restriction: the public XNU
 * entry comment assigns those roles to all nonpanic reasons, but noncold local
 * producers have not been qualified. Other raw words remain available.
 * Only PANIC yields panic words. Those x1/x2 role names come from the pinned
 * public XNU entry comment; the local check establishes the reason4 branch,
 * not the complete panic producer. The raw panic Boolean stays uint64_t:
 * no undocumented nonzero-success/coredump policy is invented. These functions
 * validate snapshot consistency, not the authenticity of the captured entry.
 * Invalid input leaves output unchanged. No captured address is dereferenced. */
enum sptm31z_entry_status sptm31z_get_boot_words(
    const struct sptm31z_entry_snapshot *entry, struct sptm31z_boot_words *output);
enum sptm31z_entry_status sptm31z_get_panic_words(
    const struct sptm31z_entry_snapshot *entry, struct sptm31z_panic_words *output);

/* Snapshot exactly 848 caller-readable monitor bytes for the explicitly
 * selected observation. This cold-only API refuses noncold allocation reuse.
 * It does not cast raw x1/x2 or read memory at those words. The caller must bind
 * bytes to the captured monitor argument pointer and establish readability,
 * stability and the actual source/version before the copy. The explicit enum
 * is a caller assertion, not authentication or proof of native compatibility.
 * Buffer alignment is unrestricted. Source/outputs must not overlap; all C
 * objects must be valid and the buffer must be readable for the accepted length.
 * Caller serializes access. No callbacks, allocator, native calls or assembly.
 *
 * Only the local-checked first-available physical address is decoded; the rest
 * remains opaque. PAPT/virtual bounds and other SDK fields are not inferred.
 * The separate memory planner requires independently qualified RAM bounds,
 * page size, iBoot high-water mark and live reservations before using that value.
 * Preserve this owned snapshot while any code uses it; no reuse/release API.
 * Native ABI qualification is incomplete: NOT_DEPLOYABLE in this checkpoint.
 */
enum sptm31z_entry_status sptm31z_snapshot_monitor(
    const struct sptm31z_entry_snapshot *entry, const uint8_t *bytes, size_t length,
    struct sptm31z_monitor_snapshot *output);

#endif
