/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Original, position-independent leaf helpers. CPU0 only; no MMIO or MSR.
 * Register entries are 16 bytes. Never executes on CPU1, whose timer callback
 * is the immutable installed timeout_calculate(0). No stack or literal pool.
 * Later entries read known RAM or publish one known RAM slot, never MMIO.
 */
.section .text,"ax"
.balign 16
.global helper31b
helper31b:
    dsb sy
    sev
    mov x0, #0x31b
    ret
.balign 16
    mrs x0, CurrentEL
    ret
.balign 16
    mrs x0, ID_AA64PFR0_EL1
    ret
.balign 16
    mrs x0, MPIDR_EL1
    ret
.balign 16
    mrs x0, MIDR_EL1
    ret
.balign 16
    mrs x0, SCTLR_EL1
    ret
.balign 16
    /* +96: aligned read, without the proxy's global exception-guard changes. */
    ldr x0, [x0]
    ret
.balign 16
    /* +112: OR at most 256 aligned words, for untouched-core checks. */
    mov x2, xzr
    cmp x1, #256
    b.hi 3f
    cbz x1, 2f
1:  ldr x3, [x0], #8
    orr x2, x2, x3
    subs x1, x1, #1
    b.ne 1b
2:  mov x0, x2
    ret
3:  mov x0, #-1
    ret
.balign 16
    /* +160: publish target, order before event; no target-side wait. */
    str x1, [x0]
    dsb sy
    sev
    mov x0, #0x31b
    ret
.balign 16
.global helper31b_end
helper31b_end:
