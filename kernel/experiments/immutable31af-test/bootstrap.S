/* SPDX-License-Identifier: MIT
 * Original standard-QEMU fixture. This is NEVER in the native payload.
 * The payload's complete identity mapping is read-only, including DATA_SPTM.
 */
#ifndef TEST_DAIF_CLEAR
#define TEST_DAIF_CLEAR 0
#endif
#ifndef TEST_MMU
#define TEST_MMU 1
#endif
.text
.global test_bootstrap
.type test_bootstrap,%function
test_bootstrap:
    msr DAIFSet, #15
    ldr x0, =TEST_HCR
    msr HCR_EL2, x0
    isb
    ldr x0, =0x04ff44
    msr MAIR_EL2, x0
    ldr x0, =TEST_TCR
    msr TCR_EL2, x0
    ldr x0, =0x43000000
    msr TTBR0_EL2, x0
    adr x0, fixture_vectors
    msr VBAR_EL2, x0
    dsb sy
    isb
    tlbi alle2
    dsb sy
    isb
    mrs x0, SCTLR_EL2
#if TEST_MMU
    orr x0, x0, #1
#else
    bic x0, x0, #1
#endif
    msr SCTLR_EL2, x0
    isb
    /* This deliberately unusable SP makes accidental stack use fail. */
    mov x0, #0
    mov sp, x0
    ldr x0, =0x0000000000400000
    msr PAR_EL1, x0
    isb
    ldr x0, =TEST_REASON
    ldr x1, =TEST_BOOT
    ldr x2, =TEST_MONITOR
    msr DAIFClr, #TEST_DAIF_CLEAR
    ldr x3, =TEST_ENTRY
    br x3
.ltorg
.size test_bootstrap, .-test_bootstrap
.balign 2048
.global fixture_vectors
fixture_vectors:
.set fixture_slot, 0
.rept 16
    mov x17, #fixture_slot
    b fixture_fatal
    .space 120
    .set fixture_slot, fixture_slot+1
.endr
.global fixture_fatal
.type fixture_fatal,%function
fixture_fatal:
    msr DAIFSet, #15
    ldr x16, =0x46000000
    ldr x0, =0x31464133464c5446
    str x0, [x16]
    mrs x0, ESR_EL2
    str x0, [x16, #8]
    mrs x0, ELR_EL2
    str x0, [x16, #16]
    mrs x0, FAR_EL2
    str x0, [x16, #24]
    mrs x0, SPSR_EL2
    str x0, [x16, #32]
    mov x0, sp
    str x0, [x16, #40]
    str x17, [x16, #48]
    mov x0, #0xdead
    str x0, [x16, #56]
    dsb sy
    mov x28, #22
    mov x27, #0xdead
.global fixture_fault_park
fixture_fault_park:
    b fixture_fault_park
.ltorg
.size fixture_fatal, .-fixture_fatal
.section .note.GNU-stack,"",%progbits
