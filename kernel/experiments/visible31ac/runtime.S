/* SPDX-License-Identifier: MIT */
/* Original bounded-call freestanding byte helpers, no external runtime. */
.section .text.runtime,"ax",%progbits
.global memcpy
.type memcpy,%function
memcpy:
    mov x3, x0
    cbz x2, 2f
1:  ldrb w4, [x1], #1
    strb w4, [x3], #1
    subs x2, x2, #1
    b.ne 1b
2:  ret
.size memcpy, .-memcpy
.global memset
.type memset,%function
memset:
    mov x3, x0
    cbz x2, 2f
1:  strb w1, [x3], #1
    subs x2, x2, #1
    b.ne 1b
2:  ret
.size memset, .-memset
.section .note.GNU-stack,"",%progbits
