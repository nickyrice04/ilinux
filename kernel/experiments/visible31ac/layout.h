/* SPDX-License-Identifier: MIT */
#ifndef VISIBLE31AC_LAYOUT_H
#define VISIBLE31AC_LAYOUT_H
#define V31_PAYLOAD_BYTES 0x24000
#define V31_RECORD_BYTES 0x200
#define V31_MAGIC 0x4341313347495356
#define V31_VERSION 1
#define V31_R_MAGIC 0
#define V31_R_VERSION 8
#define V31_R_STAGE 16
#define V31_R_STATUS 24
#define V31_R_REASON 32
#define V31_R_BOOT 40
#define V31_R_MONITOR 48
#define V31_R_EL 56
#define V31_R_DAIF 64
#define V31_R_INCOMING_SP 72
#define V31_R_OWNED_SP 80
#define V31_R_VBAR 88
#define V31_R_HCR 96
#define V31_R_SCTLR 104
#define V31_R_TCR 112
#define V31_R_MMFR3 120
#define V31_R_LAST_VA 128
#define V31_R_LAST_PAR 136
#define V31_R_PROBES 144
#define V31_R_READ_BYTES 152
#define V31_R_COUNT 160
#define V31_R_HELPER_VERSION 168
#define V31_R_FB_PA 176
#define V31_R_FB_VA 184
#define V31_R_PAINT_ATTEMPT 192
#define V31_R_PAINTED_PIXELS 200
#define V31_R_FAULT_SLOT 208
#define V31_R_ESR 216
#define V31_R_ELR 224
#define V31_R_FAR 232
#define V31_R_SPSR 240
#define V31_R_FAULT_SP 248
#define V31_R_IMAGE_PAGES 256
#define V31_R_PROTECTED_PAGES 264
#define V31_R_EXPECTED_PA 272
#define V31_R_DETAIL 280
#define V31_R_TCR2 288
#define V31_R_TCR2_READ 296
#define V31_R_CTR 304
#define V31_R_LINE_BYTES 312
#define V31_R_CLEAN_COUNT 320
#define V31_R_CLEAN_PLANNED 328
#define V31_STAGE_CAPTURED 1
#define V31_STAGE_VECTORS 2
#define V31_STAGE_PROFILE 3
#define V31_STAGE_SNAPSHOTS 4
#define V31_STAGE_PLANNED 5
#define V31_STAGE_VALIDATED 6
#define V31_STAGE_PAINTED 7
#define V31_STAGE_REFUSED 0x80
#define V31_STAGE_FAULT 0xdead
#define V31_OK 0
#define V31_REASON 1
#define V31_EL 2
#define V31_HCR 3
#define V31_DAIF 4
#define V31_MMU 5
#define V31_FORMAT 6
#define V31_IMAGE_READ 7
#define V31_BOOT_READ 8
#define V31_MONITOR_READ 9
#define V31_HELPER_VERSION 10
#define V31_COUNT_READ 11
#define V31_COUNT_RANGE 12
#define V31_TABLE_READ 13
#define V31_TABLE_FORMAT 14
#define V31_VIDEO_FORMAT 15
#define V31_PLAN 16
#define V31_FB_TRANSLATION 17
#define V31_FB_PA 18
#define V31_FB_ATTR 19
#define V31_FB_ALIAS 20
#define V31_INPUT_CHANGED 21
#define V31_EXCEPTION 22
#define V31_LITTLE_ENDIAN 23
#define V31_TCRX 24
#define V31_CACHE_LINE 25
#define V31_CACHE_EXTENT 26
#ifndef __ASSEMBLER__
#include <stdint.h>
#include <stddef.h>
struct v31_record { volatile uint64_t words[V31_RECORD_BYTES / 8]; };
struct v31_page { uint64_t physical; };
extern struct v31_record native_record;
extern unsigned char native_image_base[], native_image_end[];
void visible31ac_bridge(struct v31_record *record);
uint64_t visible31ac_read_at(uint64_t va);
uint64_t visible31ac_write_at(uint64_t va);
uint64_t visible31ac_read_tcr2(void);
uint64_t visible31ac_read_ctr(void);
void visible31ac_clean(uint64_t va);
void visible31ac_barrier(void);
#endif
#endif
