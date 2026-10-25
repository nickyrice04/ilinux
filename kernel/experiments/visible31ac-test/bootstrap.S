/* SPDX-License-Identifier: MIT
 * Original standard-QEMU setup. NEVER part of the native image. */
.text
.global test_bootstrap
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
    dsb sy
    isb
    tlbi alle2
    dsb sy
    isb
    mrs x0, SCTLR_EL2
    orr x0, x0, #1
    msr SCTLR_EL2, x0
    isb
    ldr x0, =0x40301000
    mov sp, x0
    ldr x0, =TEST_REASON
    ldr x1, =TEST_BOOT
    ldr x2, =TEST_MONITOR
    ldr x3, =0x40410000
    br x3
.ltorg
