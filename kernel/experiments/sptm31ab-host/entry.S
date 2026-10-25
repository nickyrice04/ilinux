/* SPDX-License-Identifier: MIT */
#include "layout.h"

.section .boot.entry,"ax",@progbits
.balign 4
.global host_entry
.type host_entry,%function
host_entry:
    /* No use of the incoming stack or dereference of incoming x0/x1/x2. */
    mrs x3, CurrentEL
    mrs x4, DAIF
    mov x5, sp
    msr DAIFSet, #15
    adr x6, host_capture
    /* Initialize every record byte without relying on loader zero-fill. */
    .set clear_offset, 0
    .rept 16
    stp xzr, xzr, [x6, #clear_offset]
    .set clear_offset, clear_offset + 16
    .endr
    movz x7, #(REC_MAGIC & 0xffff)
    movk x7, #((REC_MAGIC >> 16) & 0xffff), lsl #16
    movk x7, #((REC_MAGIC >> 32) & 0xffff), lsl #32
    movk x7, #((REC_MAGIC >> 48) & 0xffff), lsl #48
    str x7, [x6, #REC_MAGIC_OFFSET]
    mov x7, #REC_VERSION
    str x7, [x6, #REC_VERSION_OFFSET]
    str x3, [x6, #REC_CURRENT_EL]
    str x4, [x6, #REC_DAIF]
    str x5, [x6, #REC_INCOMING_SP]
    stp x0, x1, [x6, #REC_X0]
    str x2, [x6, #REC_X2]
    mov x7, #PHASE_CAPTURED
    dsb sy
    str x7, [x6, #REC_PHASE]
    dsb sy
    cmp x3, #4
    b.eq host_prepare_stack
    cmp x3, #8
    b.ne host_unsupported_el
    /* HCR is read only on EL2. No VHE alias is inferred from its value. */
    mrs x7, HCR_EL2
    str x7, [x6, #REC_HCR_EL2]
    mov x7, #1
    str x7, [x6, #REC_HCR_PRESENT]
host_prepare_stack:
    msr SPSel, #1
    adr x7, host_stack_top
    mov sp, x7
    str x7, [x6, #REC_OWNED_SP]
    adr x7, host_vectors
    str x7, [x6, #REC_VECTOR_BASE]
    cmp x3, #4
    b.eq host_set_el1_vectors
    msr VBAR_EL2, x7
    b host_vectors_installed
host_set_el1_vectors:
    msr VBAR_EL1, x7
host_vectors_installed:
    isb
    mov x7, #PHASE_VECTORS_PARKED
    dsb sy
    str x7, [x6, #REC_PHASE]
    dsb sy
    b host_park
host_unsupported_el:
    mov x7, #PHASE_UNSUPPORTED_EL
    dsb sy
    str x7, [x6, #REC_PHASE]
    dsb sy
.global host_park
host_park:
    /* Deliberately no WFI/WFE, callback, argument read, monitor call or return. */
    b host_park
.size host_entry, .-host_entry

.section .boot.vectors,"ax",@progbits
.balign 2048
.global host_vectors
.type host_vectors,%function
host_vectors:
    .set vector_slot, 0
    .rept 16
    mov x17, #vector_slot
    b host_fatal_vector
    .space 120, 0
    .set vector_slot, vector_slot + 1
    .endr
.size host_vectors, .-host_vectors

.section .boot.fault,"ax",@progbits
.balign 4
.global host_fatal_vector
.type host_fatal_vector,%function
host_fatal_vector:
    /* Stackless diagnostic termination, not monitored exception continuation. */
    msr DAIFSet, #15
    adr x16, host_capture
    str x17, [x16, #REC_FAULT_SLOT]
    mrs x17, CurrentEL
    str x17, [x16, #REC_FAULT_EL]
    cmp x17, #4
    b.eq host_fault_el1
    cmp x17, #8
    b.ne host_fault_recorded
    mrs x17, ESR_EL2
    str x17, [x16, #REC_FAULT_ESR]
    mrs x17, ELR_EL2
    str x17, [x16, #REC_FAULT_ELR]
    mrs x17, FAR_EL2
    str x17, [x16, #REC_FAULT_FAR]
    mrs x17, SPSR_EL2
    str x17, [x16, #REC_FAULT_SPSR]
    b host_fault_recorded
host_fault_el1:
    mrs x17, ESR_EL1
    str x17, [x16, #REC_FAULT_ESR]
    mrs x17, ELR_EL1
    str x17, [x16, #REC_FAULT_ELR]
    mrs x17, FAR_EL1
    str x17, [x16, #REC_FAULT_FAR]
    mrs x17, SPSR_EL1
    str x17, [x16, #REC_FAULT_SPSR]
host_fault_recorded:
    mov x17, sp
    str x17, [x16, #REC_FAULT_SP]
    mrs x17, DAIF
    str x17, [x16, #REC_FAULT_DAIF]
    mov x17, #PHASE_FATAL_EXCEPTION
    dsb sy
    str x17, [x16, #REC_PHASE]
    dsb sy
.global host_fault_park
host_fault_park:
    b host_fault_park
.size host_fatal_vector, .-host_fatal_vector

.section .data.owned,"aw",@progbits
.balign 16
.global host_capture
.type host_capture,%object
host_capture:
    .zero 0x4000
.size host_capture, HOST_CAPTURE_BYTES
.global host_stack_bottom
host_stack_bottom:
    .zero 0x4000
.global host_stack_top
host_stack_top:

.section .note.GNU-stack,"",@progbits
