/* SPDX-License-Identifier: MIT */
#ifndef OBSERVER31AB_H
#define OBSERVER31AB_H

#include <stddef.h>
#include <stdint.h>

#define OBS31_RANGE_MAX 64u
#define OBS31_RANGE_BYTES 24u
#define OBS31_VIDEO_PREFIX_BYTES 88u
#define OBS31_MARKER_WIDTH_MAX 32u
#define OBS31_MARKER_HEIGHT_MAX 16u

enum obs31_status {
    OBS31_OK = 0, OBS31_ARGUMENT, OBS31_SIZE, OBS31_FORMAT,
    OBS31_RANGE, OBS31_OVERLAP, OBS31_UNMAPPED, OBS31_NONCONTIGUOUS,
    OBS31_BOUNDS
};

struct obs31_range { uint64_t physical, virtual_address, bytes; };
struct obs31_table {
    uint32_t count;
    struct obs31_range ranges[OBS31_RANGE_MAX];
};
struct obs31_video {
    uint64_t physical_base, display, row_bytes, width, height, depth_word;
};
struct obs31_row { uint64_t physical, virtual_address, bytes; };
struct obs31_marker {
    uint32_t width, height, depth;
    struct obs31_row rows[OBS31_MARKER_HEIGHT_MAX];
};

/* All inputs are caller-owned snapshots/objects, never captured hardware
 * pointers. All outputs are unchanged on failure. Input/output storage must
 * not overlap. These functions authenticate neither the snapshot producer nor
 * mapping permissions, cache attributes, lifetime, or display visibility. */
enum obs31_status obs31_table_decode(const uint8_t *snapshot, size_t bytes,
    uint32_t count, struct obs31_table *output);
/* A positive-sized interval may cross records only with contiguous VA output.
 * Physical address and translated PAPT/virtual address remain distinct. */
enum obs31_status obs31_translate(const struct obs31_table *table,
    uint64_t physical, uint64_t bytes, uint64_t *virtual_address);
/* Exactly the selected 88-byte boot-record prefix, not a full ABI decoder.
 * Revision/version 2, depth low byte 30/32; only video base low2 bits stripped.
 * Display/rotation/scale metadata is preserved, not interpreted. */
enum obs31_status obs31_video_decode(const uint8_t *prefix, size_t bytes,
    struct obs31_video *output);
/* Coordinates address raw framebuffer rows; no rotation or scale transform.
 * Max32x16, four bytes/pixel. Validates the complete described framebuffer's
 * arithmetic, then requires PAPT coverage only for the requested rows. */
enum obs31_status obs31_marker_plan(const struct obs31_video *video,
    const struct obs31_table *table, uint64_t x, uint64_t y,
    uint32_t width, uint32_t height, struct obs31_marker *output);
/* RAM-only test/future integration component. ram_virtual_base is a numeric
 * model label for the caller-owned byte array, not a pointer conversion. All
 * rows are checked before any write. This must not be used for MMIO: it uses
 * ordinary byte stores, supplies no ordering/cache/permission operation, and
 * says nothing about scanout. Colors are raw little-endian four-byte words;
 * depth30 refuses bits30/31. Draws a border and alternating interior pixels. */
enum obs31_status obs31_paint_ram(const struct obs31_marker *marker,
    uint64_t ram_virtual_base, uint8_t *ram, size_t ram_bytes,
    uint32_t foreground, uint32_t background);

#endif
