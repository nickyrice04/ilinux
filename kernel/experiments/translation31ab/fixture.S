/* SPDX-License-Identifier: MIT
 * ORIGINAL STANDARD-QEMU FIXTURE ONLY. Owns and configures its synthetic MMU.
 * Never link this setup into the resident-SPTM host image.
 */
.section .text.entry,"ax",%progbits
.global fixture_entry
.type fixture_entry,%function
.macro CASE number, va, expected_pa, attr
    ldr x22, =\va
    ldr x23, =\expected_pa
    mov x24, #\attr
    add x20, x19, #(128 + 64 * \number)
    ldr x4, =0x44000000402aa800
    msr PAR_EL1, x4
    isb
    mrs x21, PAR_EL1
    mov x0, x22
    bl translation31ab_s1e2w
    mrs x5, PAR_EL1
    mov x6, #\number
    stp x6, x0, [x20]
    stp x1, x21, [x20, #16]
    stp x5, x22, [x20, #32]
    stp x23, x24, [x20, #48]
.endm
fixture_entry:
    msr DAIFSet, #15
    mrs x0, CurrentEL
    cmp x0, #8
    b.ne fixture_park
    ldr x19, =fixture_capture
    mov x0, x19
    mov x1, #128
.Lclear_capture:
    stp xzr, xzr, [x0], #16
    subs x1, x1, #1
    b.ne .Lclear_capture
    ldr x0, =0x3142413133525458
    str x0, [x19]
    mov x0, #1
    str x0, [x19, #8]
    mrs x0, CurrentEL
    str x0, [x19, #16]
    ldr x0, =fixture_vectors
    msr VBAR_EL2, x0
    isb
    mov x0, #0x80000000
    msr HCR_EL2, x0
    mrs x0, SCTLR_EL2
    bic x0, x0, #1
    msr SCTLR_EL2, x0
    isb
    CASE 0, 0x80000000, 0, 0
    msr DAIFClr, #2
    CASE 1, 0x80000000, 0, 0
    msr DAIFSet, #15
    mov x0, #0x88000000
    msr HCR_EL2, x0
    isb
    CASE 2, 0x80000000, 0, 0
    mov x0, #0x80000000
    msr HCR_EL2, x0
    isb

    /* 39-bit VA, 4KiB granule: L1[1] identity block for fixture RAM;
     * L1[2] -> L2[0] -> six individual candidate pages at VA 0x80000000.
     */
    ldr x0, =fixture_l1
    mov x1, #768
.Lclear_tables:
    stp xzr, xzr, [x0], #16
    subs x1, x1, #1
    b.ne .Lclear_tables
    ldr x0, =fixture_l1
    ldr x1, =0x40000701
    str x1, [x0, #8]
    ldr x1, =fixture_l2
    orr x2, x1, #3
    str x2, [x0, #16]
    ldr x2, =fixture_l3
    orr x3, x2, #3
    str x3, [x1]
    ldr x3, =0x40200703
    str x3, [x2]
    ldr x3, =0x40201783
    str x3, [x2, #8]
    /* L3[2] invalid. L3[3] Normal WB; L3[4] a distinct actual PA. */
    ldr x3, =0x40203707
    str x3, [x2, #24]
    ldr x3, =0x40204703
    str x3, [x2, #32]
    /* AF clear, hardware AF management disabled in this baseline fixture. */
    ldr x3, =0x40205303
    str x3, [x2, #40]
    mov x1, #0xff44
    msr MAIR_EL2, x1
    ldr x1, =0x80823519
    msr TCR_EL2, x1
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
    mrs x0, HCR_EL2
    str x0, [x19, #24]
    mrs x0, TCR_EL2
    str x0, [x19, #32]
    mrs x0, SCTLR_EL2
    str x0, [x19, #40]
    mrs x0, MAIR_EL2
    str x0, [x19, #48]
    CASE 3, 0x80000000, 0x40200000, 0x44
    CASE 4, 0x80001000, 0, 0
    CASE 5, 0x80002000, 0, 0
    CASE 6, 0x80003000, 0x40203000, 0xff
    CASE 7, 0x80004000, 0x40304000, 0x44
    CASE 8, 0x80000fff, 0x40200fff, 0x44
    CASE 9, 0x80005000, 0, 0
    mov x0, #10
    str x0, [x19, #56]
    dsb sy
    mov x0, #2
    str x0, [x19, #8]
fixture_park:
    b fixture_park
.size fixture_entry, .-fixture_entry
.ltorg

.section .text.vectors,"ax",%progbits
.balign 2048
.global fixture_vectors
fixture_vectors:
.rept 16
    b fixture_fault
    .space 124
.endr
fixture_fault:
    ldr x19, =fixture_capture
    mrs x0, ESR_EL2
    str x0, [x19, #64]
    mrs x0, ELR_EL2
    str x0, [x19, #72]
    mrs x0, FAR_EL2
    str x0, [x19, #80]
    mrs x0, SPSR_EL2
    str x0, [x19, #88]
    dsb sy
    mov x0, #0xdead
    str x0, [x19, #8]
    b fixture_park
.ltorg

.section .capture,"aw",%progbits
.global fixture_capture
fixture_capture:
    .space 4096, 0xa5
.section .note.GNU-stack,"",%progbits
