/* SPDX-License-Identifier: MIT */
#include "entry.h"

static enum sptm31z_kind classify(uint64_t reason)
{
    switch (reason) {
    case 0: return SPTM31Z_COLD;
    case 1: return SPTM31Z_SECONDARY;
    case 2: return SPTM31Z_WARM;
    case 3: return SPTM31Z_HIBERNATION;
    case 4: return SPTM31Z_PANIC;
    default: return SPTM31Z_UNRECOGNIZED;
    }
}

static enum sptm31z_entry_status check(const struct sptm31z_entry_snapshot *entry)
{
    if (!entry)
        return SPTM31Z_ENTRY_ARGUMENT;
    if (entry->profile != SPTM31Z_T6050_25G83_OBSERVED)
        return SPTM31Z_ENTRY_PROFILE;
    if (entry->kind != classify(entry->raw.x0))
        return SPTM31Z_ENTRY_ROLE;
    return SPTM31Z_ENTRY_OK;
}

enum sptm31z_entry_status sptm31z_capture_entry(enum sptm31z_profile profile,
    struct sptm31z_entry_words words, struct sptm31z_entry_snapshot *output)
{
    struct sptm31z_entry_snapshot snapshot;
    if (!output)
        return SPTM31Z_ENTRY_ARGUMENT;
    if (profile != SPTM31Z_T6050_25G83_OBSERVED)
        return SPTM31Z_ENTRY_PROFILE;
    snapshot.profile = profile;
    snapshot.kind = classify(words.x0);
    snapshot.raw = words;
    *output = snapshot;
    return snapshot.kind == SPTM31Z_UNRECOGNIZED ? SPTM31Z_ENTRY_UNKNOWN_REASON : SPTM31Z_ENTRY_OK;
}

enum sptm31z_entry_status sptm31z_get_boot_words(
    const struct sptm31z_entry_snapshot *entry, struct sptm31z_boot_words *output)
{
    struct sptm31z_boot_words words;
    enum sptm31z_entry_status status = check(entry);
    if (status != SPTM31Z_ENTRY_OK)
        return status;
    if (!output)
        return SPTM31Z_ENTRY_ARGUMENT;
    if (entry->kind != SPTM31Z_COLD)
        return SPTM31Z_ENTRY_ROLE;
    words.iboot_arguments = entry->raw.x1;
    words.monitor_arguments = entry->raw.x2;
    *output = words;
    return SPTM31Z_ENTRY_OK;
}

enum sptm31z_entry_status sptm31z_get_panic_words(
    const struct sptm31z_entry_snapshot *entry, struct sptm31z_panic_words *output)
{
    struct sptm31z_panic_words words;
    enum sptm31z_entry_status status = check(entry);
    if (status != SPTM31Z_ENTRY_OK)
        return status;
    if (!output)
        return SPTM31Z_ENTRY_ARGUMENT;
    if (entry->kind != SPTM31Z_PANIC)
        return SPTM31Z_ENTRY_ROLE;
    words.message = entry->raw.x1;
    words.core_dump_flag = entry->raw.x2;
    *output = words;
    return SPTM31Z_ENTRY_OK;
}

static uint64_t read_le64(const uint8_t *bytes)
{
    uint64_t value = 0;
    unsigned i;
    for (i = 0; i < 8; i++)
        value |= (uint64_t)bytes[i] << (8 * i);
    return value;
}

enum sptm31z_entry_status sptm31z_snapshot_monitor(
    const struct sptm31z_entry_snapshot *entry, const uint8_t *bytes, size_t length,
    struct sptm31z_monitor_snapshot *output)
{
    struct sptm31z_monitor_snapshot snapshot;
    enum sptm31z_entry_status status = check(entry);
    size_t i;
    if (status != SPTM31Z_ENTRY_OK)
        return status;
    if (!bytes || !output)
        return SPTM31Z_ENTRY_ARGUMENT;
    if (entry->kind != SPTM31Z_COLD)
        return SPTM31Z_ENTRY_ROLE;
    if (length != SPTM31Z_MONITOR_BYTES)
        return SPTM31Z_ENTRY_LENGTH;
    snapshot.entry = *entry;
    for (i = 0; i < SPTM31Z_MONITOR_BYTES; i++)
        snapshot.private_bytes[i] = bytes[i];
    snapshot.first_available.value = read_le64(snapshot.private_bytes + 24);
    *output = snapshot;
    return SPTM31Z_ENTRY_OK;
}
