/* SPDX-License-Identifier: MIT
 * Synthetic standard-ARM fixture only. Never linked into a native payload.
 * Enter frozen31AF at EL1h with translation disabled and SP=0 so its first
 * CurrentEL branch can be observed independently of any framebuffer mapping.
 */
.text
.global test_bootstrap
.type test_bootstrap,%function
test_bootstrap:
    msr DAIFSet, #15
    mov x0, #0x80000000
    msr HCR_EL2, x0
    isb
    adr x0, fixture_vectors
    msr VBAR_EL1, x0
    msr VBAR_EL2, x0
    mrs x0, SCTLR_EL1
    bic x0, x0, #1
    msr SCTLR_EL1, x0
    mov x0, #0
    msr SP_EL1, x0
    mov x0, #0x3c5
    msr SPSR_EL2, x0
    ldr x0, =TEST_ENTRY
    msr ELR_EL2, x0
    ldr x0, =TEST_REASON
    ldr x1, =TEST_BOOT
    ldr x2, =TEST_MONITOR
    isb
    eret
.ltorg
.size test_bootstrap, .-test_bootstrap
.balign 2048
fixture_vectors:
.set slot, 0
.rept 16
    mov x17, #slot
    b fixture_fatal
    .space 120
    .set slot, slot+1
.endr
fixture_fatal:
    msr DAIFSet, #15
    ldr x16, =0x46000000
    ldr x0, =0x31464133464c5446
    str x0, [x16]
    mrs x9, CurrentEL
    cmp x9, #4
    b.ne .Lel2
    mrs x0, ESR_EL1
    mrs x1, ELR_EL1
    mrs x2, FAR_EL1
    mrs x3, SPSR_EL1
    b .Lcapture
.Lel2:
    mrs x0, ESR_EL2
    mrs x1, ELR_EL2
    mrs x2, FAR_EL2
    mrs x3, SPSR_EL2
.Lcapture:
    str x0, [x16, #8]
    str x1, [x16, #16]
    str x2, [x16, #24]
    str x3, [x16, #32]
    mov x0, sp
    str x0, [x16, #40]
    str x17, [x16, #48]
    mov x0, #0xdead
    str x0, [x16, #56]
    dsb sy
    mov x28, #22
    mov x27, #0xdead
.Lpark:
    b .Lpark
.ltorg
.section .note.GNU-stack,"",%progbits
