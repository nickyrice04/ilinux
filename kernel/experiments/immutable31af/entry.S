/* SPDX-License-Identifier: MIT */
/* Original register-only, nonreturning resident-cold framebuffer probe.
 * No instruction uses SP. The only memory-store instruction writes a checked
 * pixel. x19..x26 hold geometry/table state; x27 phase, x28 status, x18 DAIF.
 * Leaf helpers preserve x9..x17; calling validators retain LR in x17.
 */
#include "layout.h"
.section .boot.entry,"ax",%progbits
.global native_entry
.type native_entry,%function
native_entry:
    b immutable_main
.size native_entry, .-native_entry
.section .boot.vectors,"ax",%progbits
.balign 2048
.global native_vectors
native_vectors:
.set slot, 0
.rept 16
    mov x17, #slot
    b native_fatal
    .space 120
    .set slot, slot+1
.endr
.section .boot.body,"ax",%progbits
.global immutable_main
.type immutable_main,%function
immutable_main:
    mov x27, #IF31_STAGE_ENTRY
    mov x28, #IF31_OK
    mov x25, #0
    mov x26, #0
    mrs x9, CurrentEL
    cmp x9, #8
    b.ne .Lel
    mrs x18, DAIF
    msr DAIFSet, #15
    adr x9, native_vectors
    msr VBAR_EL2, x9
    isb
    cbnz x0, .Lreason
    mov x20, x1
    mov x21, x2
    mrs x9, HCR_EL2
    ubfx x10, x9, #34, #1
    ubfx x11, x9, #27, #1
    cmp x10, x11
    b.ne .Lhcr
    mrs x11, SCTLR_EL2
    tbz x11, #0, .Lmmu
    tbnz x11, #25, .Lendian
    mrs x12, TCR_EL2
    cbz x10, .Lnonvhe
    mrs x13, ID_AA64MMFR3_EL1
    ubfx x14, x13, #32, #4
    cbz x14, .Lvhe_ips
    cmp x14, #1
    b.ne .Lformat
    and x14, x13, #15
    cmp x14, #1
    b.ne .Ltcrx
    mrs x14, S3_4_C2_C0_3
    tbnz x14, #5, .Lformat
.Lvhe_ips:
    ubfx x14, x12, #32, #3
    cmp x14, #6
    b.hi .Lformat
    b .Lprofile_ready
.Lnonvhe:
    ubfx x14, x12, #16, #3
    cmp x14, #6
    b.hi .Lformat
.Lprofile_ready:
    mov x27, #IF31_STAGE_PROFILE
    adr x0, native_image_base
    mov x1, #IF31_PAYLOAD_BYTES
    mov x28, #IF31_IMAGE_READ
    bl immutable_readable
    mov x0, x20
    mov x1, #88
    mov x28, #IF31_BOOT_READ
    bl immutable_readable
    tst x20, #7
    b.ne .Lvideo
    ldrh w9, [x20]
    cmp w9, #2
    b.ne .Lvideo
    ldrh w9, [x20, #2]
    cmp w9, #2
    b.ne .Lvideo
    ldr x19, [x20, #40]
    and x19, x19, #0xfffffffffffffffc
    cbz x19, .Lvideo
    ldr x22, [x20, #56]
    ldr x9, [x20, #64]
    ldr x10, [x20, #72]
    ldr x24, [x20, #80]
    and x24, x24, #255
    cmp x24, #30
    b.eq .Ldepth_ready
    cmp x24, #32
    b.ne .Lvideo
.Ldepth_ready:
    cbz x22, .Lvideo
    tst x22, #3
    b.ne .Lvideo
    cmp x9, #IF31_MARKER_WIDTH
    b.lo .Lsmall
    cmp x10, #IF31_MARKER_HEIGHT
    b.lo .Lsmall
    lsr x11, x9, #62
    cbnz x11, .Lvideo
    lsl x11, x9, #2
    cmp x22, x11
    b.lo .Lvideo
    umulh x11, x22, x10
    cbnz x11, .Lvideo
    mul x23, x22, x10
    adds x23, x19, x23
    b.cs .Lvideo
    sub x9, x9, #IF31_MARKER_WIDTH
    lsr x9, x9, #1
    lsl x9, x9, #2
    sub x10, x10, #IF31_MARKER_HEIGHT
    lsr x10, x10, #1
    madd x15, x10, x22, x19
    add x15, x15, x9
    mov x0, x20
    mov x1, #88
    mov x28, #IF31_FB_ALIAS
    bl immutable_protect
    adr x0, native_image_base
    mov x1, #IF31_PAYLOAD_BYTES
    bl immutable_protect
    mov x20, x15
    cbz x21, .Lmonitor
    tst x21, #7
    b.ne .Lmonitor
    adds x21, x21, #416
    b.cs .Lmonitor
    mov x0, x21
    mov x1, #24
    mov x28, #IF31_MONITOR_READ
    bl immutable_readable
    ldr w9, [x21]
    cmp w9, #10
    b.ne .Lversion
    ldr x15, [x21, #8]
    ldr x25, [x21, #16]
    mov x0, x21
    mov x1, #24
    mov x28, #IF31_FB_ALIAS
    bl immutable_protect
    mov x0, x15
    mov x1, #4
    mov x28, #IF31_COUNT_READ
    bl immutable_readable
    tst x15, #3
    b.ne .Lcount_read
    ldr w26, [x15]
    cbz x26, .Lcount_range
    cmp x26, #64
    b.hi .Lcount_range
    mov x0, x15
    mov x1, #4
    mov x28, #IF31_FB_ALIAS
    bl immutable_protect
    tst x25, #7
    b.ne .Ltable_format
    mov x0, x25
    mov x1, #24
    mul x1, x26, x1
    mov x28, #IF31_TABLE_READ
    bl immutable_readable
    mov x28, #IF31_FB_ALIAS
    bl immutable_protect
    mov x28, #IF31_TABLE_FORMAT
    bl immutable_table_valid
    mov x27, #IF31_STAGE_INPUTS
    mov x0, x20
    mov x1, #IF31_MARKER_HEIGHT-1
    mul x1, x22, x1
    add x1, x1, #IF31_MARKER_WIDTH*4
    mov x28, #IF31_PLAN
    bl immutable_translate
    mov x21, x0
    mov x27, #IF31_STAGE_PLANNED
    bl immutable_validate_fb
    mov x27, #IF31_STAGE_VALIDATED
    mov x25, #0
    mov x26, #0
    mov x9, #0
    mov x10, x21
    mov w12, #0x00ffffff
    and x0, x24, #255
    cmp x0, #30
    b.ne .Lpaint_row
    mov w12, #0x3fffffff
.Lpaint_row:
    mov x11, #0
.Lpaint_column:
    cmp x9, #4
    b.lo .Lforeground
    cmp x9, #IF31_MARKER_HEIGHT-4
    b.hs .Lforeground
    cmp x11, #4
    b.lo .Lforeground
    cmp x11, #IF31_MARKER_WIDTH-4
    b.hs .Lforeground
    eor x0, x9, x11
    tbnz x0, #3, .Lforeground
    mov w0, #0
    b .Lpixel
.Lforeground:
    mov w0, w12
.global immutable_pixel_store
immutable_pixel_store:
.Lpixel:
    str w0, [x10, x11, lsl #2]
    add x26, x26, #1
    add x11, x11, #1
    cmp x11, #IF31_MARKER_WIDTH
    b.lo .Lpaint_column
    add x9, x9, #1
    cmp x9, #IF31_MARKER_HEIGHT
    b.hs .Lpaint_done
    add x10, x10, x22
    b .Lpaint_row
.Lpaint_done:
    dsb sy
    tbz x24, #8, .Lcomplete
    mov x9, #0
    mov x10, x21
    ubfx x12, x24, #16, #16
.Lclean_row:
    neg x0, x12
    and x13, x10, x0
    add x14, x10, #IF31_MARKER_WIDTH*4
.Lclean_line:
    dc cvac, x13
    add x25, x25, #1
    add x13, x13, x12
    cmp x13, x14
    b.lo .Lclean_line
    add x9, x9, #1
    cmp x9, #IF31_MARKER_HEIGHT
    b.hs .Lcomplete
    add x10, x10, x22
    b .Lclean_row
.Lcomplete:
    dsb sy
    mov x28, #IF31_OK
    mov x27, #IF31_STAGE_PAINTED
    b native_park
.Lreason: mov x28, #IF31_REASON; b immutable_refuse
.Lel: mov x28, #IF31_EL; b immutable_refuse
.Lhcr: mov x28, #IF31_HCR; b immutable_refuse
.Lmmu: mov x28, #IF31_MMU; b immutable_refuse
.Lendian: mov x28, #IF31_LITTLE_ENDIAN; b immutable_refuse
.Lformat: mov x28, #IF31_FORMAT; b immutable_refuse
.Ltcrx: mov x28, #IF31_TCRX; b immutable_refuse
.Lvideo: mov x28, #IF31_VIDEO_FORMAT; b immutable_refuse
.Lsmall: mov x28, #IF31_PLAN; b immutable_refuse
.Lmonitor: mov x28, #IF31_MONITOR_READ; b immutable_refuse
.Lversion: mov x28, #IF31_HELPER_VERSION; b immutable_refuse
.Lcount_read: mov x28, #IF31_COUNT_READ; b immutable_refuse
.Lcount_range: mov x28, #IF31_COUNT_RANGE; b immutable_refuse
.Ltable_format: mov x28, #IF31_TABLE_FORMAT; b immutable_refuse
.size immutable_main, .-immutable_main

/* x0VA,x1bytes preserved; other clobbers x2..x8 only. */
.type immutable_readable,%function
immutable_readable:
    cbz x0, immutable_refuse
    cbz x1, immutable_refuse
    adds x3, x0, x1
    b.cs immutable_refuse
    mov x2, x0
.Lread_page:
    mrs x4, PAR_EL1
    at s1e2r, x2
    isb
    mrs x5, PAR_EL1
    msr PAR_EL1, x4
    isb
    tbnz x5, #0, immutable_refuse
    lsr x6, x5, #56
    cmp x6, #0x44
    b.eq .Lread_next
    cmp x6, #0xff
    b.ne immutable_refuse
.Lread_next:
    orr x2, x2, #4095
    adds x2, x2, #1
    b.cs immutable_refuse
    cmp x2, x3
    b.lo .Lread_page
    ret
.size immutable_readable, .-immutable_readable

/* Protect source4KiB pages against the complete declared framebuffer extent.
 * Preserves x15/x16, geometry globals. x9..x14/x17 scratch. */
.type immutable_protect,%function
immutable_protect:
    mov x17, x30
    cbz x0, immutable_refuse
    cbz x1, immutable_refuse
    adds x10, x0, x1
    b.cs immutable_refuse
    mov x9, x0
.Lprotect_page:
    mov x0, x9
    bl immutable_read_at
    tbnz x0, #0, immutable_refuse
    lsr x11, x0, #56
    cmp x11, #0x44
    b.eq .Lprotect_attr
    cmp x11, #0xff
    b.ne immutable_refuse
.Lprotect_attr:
    and x12, x0, #0x000ffffffffff000
    add x13, x12, #4096
    cmp x12, x23
    b.hs .Lprotect_next
    cmp x19, x13
    b.lo immutable_refuse
.Lprotect_next:
    orr x9, x9, #4095
    adds x9, x9, #1
    b.cs immutable_refuse
    cmp x9, x10
    b.lo .Lprotect_page
    mov x30, x17
    ret
.size immutable_protect, .-immutable_protect

/* Already-readable table; endpoints exclusive, overflow checked, no overlap.
 * No calls; scratch x0..x17. */
.type immutable_table_valid,%function
immutable_table_valid:
    mov x9, x25
    mov x10, x26
.Ltable_a:
    ldr x13, [x9]
    ldr x15, [x9, #8]
    ldr w2, [x9, #16]
    cbz x2, immutable_refuse
    orr x0, x13, x15
    tst x0, #0x3fff
    b.ne immutable_refuse
    lsl x2, x2, #14
    adds x14, x13, x2
    b.cs immutable_refuse
    adds x16, x15, x2
    b.cs immutable_refuse
    mov x11, x25
    sub x12, x26, x10
    cbz x12, .Ltable_next
.Ltable_b:
    ldr x0, [x11]
    ldr x1, [x11, #8]
    ldr w2, [x11, #16]
    lsl x2, x2, #14
    add x3, x0, x2
    add x4, x1, x2
    cmp x13, x3
    b.hs .Ltable_virtual
    cmp x0, x14
    b.lo immutable_refuse
.Ltable_virtual:
    cmp x15, x4
    b.hs .Ltable_b_next
    cmp x1, x16
    b.lo immutable_refuse
.Ltable_b_next:
    add x11, x11, #24
    subs x12, x12, #1
    b.ne .Ltable_b
.Ltable_next:
    add x9, x9, #24
    subs x10, x10, #1
    b.ne .Ltable_a
    ret
.size immutable_table_valid, .-immutable_table_valid

/* x0PA,x1bytes ->x0VA. ContiguousVA across records. Preserves x9..x17. */
.type immutable_translate,%function
immutable_translate:
    cbz x1, immutable_refuse
    adds x2, x0, x1
    b.cs immutable_refuse
    mov x3, #0
    mov x4, #0
.Ltranslate_cursor:
    mov x5, x25
    mov x6, x26
.Ltranslate_find:
    ldr x7, [x5]
    ldr w8, [x5, #16]
    lsl x8, x8, #14
    add x8, x8, x7
    cmp x0, x7
    b.lo .Ltranslate_next
    cmp x0, x8
    b.hs .Ltranslate_next
    ldr x1, [x5, #8]
    sub x7, x0, x7
    add x1, x1, x7
    cbz x1, immutable_refuse
    cbnz x3, .Ltranslate_contiguous
    mov x3, x1
    b .Ltranslate_advance
.Ltranslate_contiguous:
    cmp x1, x4
    b.ne immutable_refuse
.Ltranslate_advance:
    cmp x8, x2
    csel x8, x8, x2, lo
    sub x7, x8, x0
    add x4, x1, x7
    mov x0, x8
    cmp x0, x2
    b.lo .Ltranslate_cursor
    mov x0, x3
    ret
.Ltranslate_next:
    add x5, x5, #24
    subs x6, x6, #1
    b.ne .Ltranslate_find
    b immutable_refuse
.size immutable_translate, .-immutable_translate

/* All pixel pages and rounded cache intervals precede every pixel store.
 * Calling validators use x17 for LR; their leaf callees preserve it. */
.type immutable_validate_fb,%function
immutable_validate_fb:
    mov x17, x30
    mov x9, #0
    mov x10, x21
    mov x11, x20
.Lvalidate_row:
    add x12, x10, #IF31_MARKER_WIDTH*4
    mov x13, x10
.Lvalidate_page:
    mov x28, #IF31_FB_TRANSLATION
    mov x0, x13
    bl immutable_write_at
    tbnz x0, #0, immutable_refuse
    and x2, x0, #0x000ffffffffff000
    and x15, x13, #4095
    orr x2, x2, x15
    sub x15, x13, x10
    add x15, x11, x15
    mov x28, #IF31_FB_PA
    cmp x2, x15
    b.ne immutable_refuse
    lsr x14, x0, #56
    cmp x14, #0x44
    b.eq .Lvalidate_next
    mov x28, #IF31_FB_ATTR
    cmp x14, #0xff
    b.ne immutable_refuse
    orr x24, x24, #256
.Lvalidate_next:
    orr x13, x13, #4095
    adds x13, x13, #1
    b.cs immutable_refuse
    cmp x13, x12
    b.lo .Lvalidate_page
    add x9, x9, #1
    cmp x9, #IF31_MARKER_HEIGHT
    b.hs .Lvalidate_rows_done
    add x10, x10, x22
    add x11, x11, x22
    b .Lvalidate_row
.Lvalidate_rows_done:
    tbz x24, #8, .Lvalidate_return
    mrs x0, CTR_EL0
    ubfx x0, x0, #16, #4
    mov x12, #4
    lsl x12, x12, x0
    mov x28, #IF31_CACHE_LINE
    cmp x12, #16
    b.lo immutable_refuse
    cmp x12, #2048
    b.hi immutable_refuse
    orr x24, x24, x12, lsl #16
    mov x9, #0
    mov x10, x21
    mov x11, x20
.Lvalidate_clean_row:
    neg x0, x12
    and x13, x10, x0
    add x14, x10, #IF31_MARKER_WIDTH*4
    sub x15, x10, x13
    sub x15, x11, x15
.Lvalidate_clean_line:
    mov x28, #IF31_CACHE_EXTENT
    cmp x15, x19
    b.lo immutable_refuse
    adds x16, x15, x12
    b.cs immutable_refuse
    cmp x16, x23
    b.hi immutable_refuse
    mov x0, x15
    mov x1, x12
    bl immutable_translate
    cmp x0, x13
    b.ne immutable_refuse
    mov x0, x13
    bl immutable_write_at
    tbnz x0, #0, immutable_refuse
    and x2, x0, #0x000ffffffffff000
    and x16, x13, #4095
    orr x2, x2, x16
    cmp x2, x15
    b.ne immutable_refuse
    lsr x0, x0, #56
    cmp x0, #0x44
    b.eq .Lvalidate_clean_next
    cmp x0, #0xff
    b.ne immutable_refuse
.Lvalidate_clean_next:
    add x13, x13, x12
    add x15, x15, x12
    cmp x13, x14
    b.lo .Lvalidate_clean_line
    add x9, x9, #1
    cmp x9, #IF31_MARKER_HEIGHT
    b.hs .Lvalidate_return
    add x10, x10, x22
    add x11, x11, x22
    b .Lvalidate_clean_row
.Lvalidate_return:
    mov x30, x17
    ret
.size immutable_validate_fb, .-immutable_validate_fb
.type immutable_read_at,%function
immutable_read_at:
    mrs x2, PAR_EL1
    at s1e2r, x0
    isb
    mrs x0, PAR_EL1
    msr PAR_EL1, x2
    isb
    ret
.size immutable_read_at, .-immutable_read_at
.type immutable_write_at,%function
immutable_write_at:
    mrs x2, PAR_EL1
    at s1e2w, x0
    isb
    mrs x0, PAR_EL1
    msr PAR_EL1, x2
    isb
    ret
.size immutable_write_at, .-immutable_write_at
.global immutable_refuse
.type immutable_refuse,%function
immutable_refuse:
    mov x27, #IF31_STAGE_REFUSED
    b native_park
.size immutable_refuse, .-immutable_refuse
.global native_park
.type native_park,%function
native_park:
    b native_park
.size native_park, .-native_park
.global native_fatal
.type native_fatal,%function
native_fatal:
    msr DAIFSet, #15
    mrs x28, ESR_EL2
    mrs x29, ELR_EL2
    mrs x16, FAR_EL2
    mov x27, #IF31_STAGE_FAULT
.global native_fault_park
native_fault_park:
    b native_fault_park
.size native_fatal, .-native_fatal
.section .late,"ax",%progbits
.global native_late_park
.type native_late_park,%function
native_late_park:
    b native_late_park
.size native_late_park, .-native_late_park
.section .reserved,"a",%progbits
.balign 16384
.global reserved_sptm_begin
reserved_sptm_begin:
    .space IF31_RESERVED_BYTES
.global reserved_sptm_end
reserved_sptm_end:
.section .note.GNU-stack,"",%progbits
