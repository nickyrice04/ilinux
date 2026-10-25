/* SPDX-License-Identifier: MIT */
.section .text.probe,"ax",%progbits
.balign 4
.global translation31ab_s1e2w
.type translation31ab_s1e2w,%function
translation31ab_s1e2w:
    mov x2, x0
    mov x1, xzr
    mrs x3, CurrentEL
    cmp x3, #8
    b.ne .Lwrong_el
    mrs x3, HCR_EL2
    tbnz x3, #34, .Lhcr
    tbnz x3, #27, .Lhcr
    mrs x3, DAIF
    and x3, x3, #0x3c0
    cmp x3, #0x3c0
    b.ne .Ldaif
    mrs x3, SCTLR_EL2
    tbz x3, #0, .Lmmu
    mrs x3, PAR_EL1
    at s1e2w, x2
    isb
    mrs x1, PAR_EL1
    msr PAR_EL1, x3
    isb
    mov x0, xzr
    ret
.Lwrong_el:
    mov x0, #1
    ret
.Lhcr:
    mov x0, #2
    ret
.Ldaif:
    mov x0, #3
    ret
.Lmmu:
    mov x0, #4
    ret
.size translation31ab_s1e2w, .-translation31ab_s1e2w
.section .note.GNU-stack,"",%progbits
