/* SPDX-License-Identifier: MIT */
/* Original external-AAPCS wrappers from the published bootstrap-call contract.
 * Compile/link inspection only. None is called by the diagnostic entry. */
.macro dispatch_body number
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    mov x16, #\number
    /* Published GENTER selector0 encoding, not copied implementation bytes. */
    .inst 0x00201420
    ldp x29, x30, [sp], #16
    ret
.endm

/* This call precedes making later text executable in the public lifecycle. */
.section .boot.transport,"ax",@progbits
.balign 4
.global host_fixups_complete
.type host_fixups_complete,%function
host_fixups_complete:
    dispatch_body 15
.size host_fixups_complete, .-host_fixups_complete

.section .text.transport,"ax",@progbits
.balign 4
.global host_register_cpu
.type host_register_cpu,%function
host_register_cpu:
    /* x0 is the one uint64 physical-affinity argument, not a memory pointer. */
    dispatch_body 14
.size host_register_cpu, .-host_register_cpu

.global host_register_exception_return
.type host_register_exception_return,%function
host_register_exception_return:
    /* x0 is the separately qualified exception-return handler address. */
    dispatch_body 18
.size host_register_exception_return, .-host_register_exception_return

.section .note.GNU-stack,"",@progbits
