/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Original diagnostic, linked at 0xa00. No SP/LR, security or MMIO writes.
 * Vector+0 MOV X9,#48 is replayed before resuming at vector+4. x0/x8/NZCV
 * are redefined by the unchanged reset prefix before use. X9 temporarily
 * carries CurrentEL but its original assignment is restored exactly.
 * This slot is also a synchronous exception vector: identity is not inferred.
 */
.text
.p2align 2
.global smp31f_recorder
.type smp31f_recorder, %function
.extern smp31f_record /* --defsym=smp31f_record=0x90a40 */
.extern smp31f_resume /* --defsym=smp31f_resume=0x4 */
smp31f_recorder:
    adrp x0, smp31f_record
    add x0, x0, #0xa40
    movz x8, #1
    str x8, [x0]
    dsb sy
    mrs x8, MPIDR_EL1
    ubfx x8, x8, #0, #24
    str x8, [x0, #16]
    dsb sy
    movz x8, #2
    str x8, [x0]
    dsb sy
    mrs x9, CurrentEL
    str x9, [x0, #8]
    dsb sy
    movz x8, #3
    str x8, [x0]
    dsb sy
    cmp x9, #4
    b.eq .Lel1
    cmp x9, #8
    b.eq .Lel2
    cmp x9, #12
    b.eq .Lel3
    dsb sy
    movz x8, #255
    str x8, [x0]
    dsb sy
    b .Lreplay
.Lel1:
    mrs x8, SCTLR_EL1
    b .Lsctlr_done
.Lel2:
    mrs x8, SCTLR_EL2
    b .Lsctlr_done
.Lel3:
    mrs x8, SCTLR_EL3
    b .Lsctlr_done
.Lsctlr_done:
    str x8, [x0, #24]
    dsb sy
    movz x8, #4
    str x8, [x0]
    dsb sy
.Lreplay:
    movz x9, #48
    b smp31f_resume
.size smp31f_recorder, . - smp31f_recorder
