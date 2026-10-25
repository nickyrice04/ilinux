/* SPDX-License-Identifier: MIT */
#include "layout.h"
.section .boot.entry,"ax",%progbits
.global native_entry
.type native_entry,%function
native_entry:
    mrs x3, CurrentEL
    mrs x4, DAIF
    mov x5, sp
    msr DAIFSet, #15
    adr x6, native_record
    mov x7, x6
    mov x8, #32
1:  stp xzr, xzr, [x7], #16
    subs x8, x8, #1
    b.ne 1b
    movz x7, #0x5356
    movk x7, #0x4749, lsl #16
    movk x7, #0x3133, lsl #32
    movk x7, #0x4341, lsl #48
    str x7, [x6, #V31_R_MAGIC]
    mov x7, #V31_VERSION
    str x7, [x6, #V31_R_VERSION]
    stp x0, x1, [x6, #V31_R_REASON]
    stp x2, x3, [x6, #V31_R_MONITOR]
    stp x4, x5, [x6, #V31_R_DAIF]
    dsb sy
    mov x7, #V31_STAGE_CAPTURED
    str x7, [x6, #V31_R_STAGE]
    cmp x3, #8
    b.ne .Lwrong_el
    msr SPSel, #1
    adr x7, native_stack_top
    mov sp, x7
    adr x8, native_vectors
    stp x7, x8, [x6, #V31_R_OWNED_SP]
    msr VBAR_EL2, x8
    isb
    mrs x7, HCR_EL2
    mrs x8, SCTLR_EL2
    stp x7, x8, [x6, #V31_R_HCR]
    mrs x7, TCR_EL2
    mrs x8, ID_AA64MMFR3_EL1
    stp x7, x8, [x6, #V31_R_TCR]
    dsb sy
    mov x7, #V31_STAGE_VECTORS
    str x7, [x6, #V31_R_STAGE]
    mov x0, x6
    bl visible31ac_bridge
.global native_park
native_park:
    b native_park
.Lwrong_el:
    mov x7, #V31_EL
    str x7, [x6, #V31_R_STATUS]
    dsb sy
    mov x7, #V31_STAGE_REFUSED
    str x7, [x6, #V31_R_STAGE]
    b native_park
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
.global native_fatal
.type native_fatal,%function
native_fatal:
    msr DAIFSet, #15
    adr x16, native_record
    str x17, [x16, #V31_R_FAULT_SLOT]
    mrs x0, ESR_EL2
    mrs x1, ELR_EL2
    stp x0, x1, [x16, #V31_R_ESR]
    mrs x0, FAR_EL2
    mrs x1, SPSR_EL2
    stp x0, x1, [x16, #V31_R_FAR]
    mov x0, sp
    str x0, [x16, #V31_R_FAULT_SP]
    mov x0, #V31_EXCEPTION
    str x0, [x16, #V31_R_STATUS]
    dsb sy
    mov x0, #V31_STAGE_FAULT
    str x0, [x16, #V31_R_STAGE]
    dsb sy
.global native_fault_park
native_fault_park:
    b native_fault_park
.size native_fatal, .-native_fatal

.section .late,"ax",%progbits
.global native_late_park
native_late_park:
    b native_late_park

.section .owned,"aw",%progbits
.balign 16
.global native_record
.type native_record,%object
native_record:
    .space 0x4000
.global native_stack_bottom
native_stack_bottom:
    .space 0x8000
.global native_stack_top
native_stack_top:
.section .note.GNU-stack,"",%progbits
