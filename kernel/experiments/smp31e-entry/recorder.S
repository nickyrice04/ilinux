/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Original project diagnostic. OFFLINE ONLY; link .text at VMA 0xa00.
 * No stack, LR, security-register or MMIO writes. x0/x8/NZCV are dead at
 * the replaced cpu_reset MOV; replay it and resume its original BL.
 * This is not a target installer or permission to patch the live image.
 */
.text
.p2align 2
.global smp31e_recorder
.type smp31e_recorder, %function
.extern smp31e_record /* Linker: --defsym=smp31e_record=0x90a40 */
.extern smp31e_resume /* Linker: --defsym=smp31e_resume=0x900 */
smp31e_recorder:
    mrs x8, MPIDR_EL1
    ubfx x8, x8, #0, #24
    movz x0, #1
    movk x0, #4, lsl #16
    cmp x8, x0
    b.ne .Lreplay
    adrp x0, smp31e_record
    add x0, x0, #0xa40
    str x8, [x0, #16]
    dsb sy
    movz x8, #1
    str x8, [x0]
    dsb sy
    mrs x8, CurrentEL
    str x8, [x0, #8]
    cmp x8, #4
    b.eq .Lel1
    cmp x8, #8
    b.eq .Lel2
    cmp x8, #12
    b.eq .Lel3
    dsb sy
    movz x8, #255
    str x8, [x0]
    dsb sy
    b .Lreplay
.Lel1:
    dsb sy
    movz x8, #2
    str x8, [x0]
    dsb sy
    mrs x8, SCTLR_EL1
    b .Lsctlr_done
.Lel2:
    dsb sy
    movz x8, #2
    str x8, [x0]
    dsb sy
    mrs x8, SCTLR_EL2
    b .Lsctlr_done
.Lel3:
    dsb sy
    movz x8, #2
    str x8, [x0]
    dsb sy
    mrs x8, SCTLR_EL3
    b .Lsctlr_done
.Lsctlr_done:
    str x8, [x0, #24]
    dsb sy
    movz x8, #3
    str x8, [x0]
    dsb sy
.Lreplay:
    movz w0, #79
    b smp31e_resume
.size smp31e_recorder, . - smp31e_recorder
