/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Linux ARM64 VM userspace only. Executes ONE ordinary STP from boot021.
 * No privileged instructions, reset code, sysregs, MMIO or kernel operations.
 * x0=aligned synthetic stack top, x1=FP value, x2=LR value, x3=SP output.
 */
.text
.balign 16
.global smp31e_store_frame
.type smp31e_store_frame, %function
smp31e_store_frame:
    mov x9, sp
    mov x10, x29
    mov x11, x30
    mov x29, x1
    mov x30, x2
    mov sp, x0
.global smp31e_frame_word
smp31e_frame_word:
    .inst 0xa9be7bfd /* pinned _cpu_reset_c first STP X29,X30,[SP,#-32]! */
    mov x4, sp
    mov sp, x9
    mov x29, x10
    mov x30, x11
    str x4, [x3]
    ret
.size smp31e_store_frame, . - smp31e_store_frame
.section .note.GNU-stack,"",%progbits
