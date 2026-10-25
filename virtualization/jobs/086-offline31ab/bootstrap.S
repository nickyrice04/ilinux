/* SPDX-License-Identifier: MIT */
/* Original QEMU-only fixture. Never packaged as the native entry image. */
#ifndef TEST_IMAGE_BASE
#define TEST_IMAGE_BASE 0x40000000
#endif
.section .text,"ax",@progbits
.global test_bootstrap
test_bootstrap:
    msr DAIFSet, #15
    mrs x9, CurrentEL
    cmp x9, #8
    b.ne 1f
    /* QEMU-only EL2 fixture, with explicit non-VHE/VHE HCR state. */
    ldr x9, test_hcr
    msr HCR_EL2, x9
    isb
1:
    ldr x0, reason
    ldr x1, fake_argument1
    ldr x2, fake_argument2
    ldr x9, initial_sp
    mov sp, x9
    ldr x9, test_entry
    br x9
.balign 8
reason: .quad 0x100000000
fake_argument1: .quad 0xaaaa111122223333
fake_argument2: .quad 0xbbbb444455556666
initial_sp: .quad 0x40301000
test_entry: .quad TEST_IMAGE_BASE + 0xc000
#ifdef TEST_VHE
test_hcr: .quad 0x488000000
#else
test_hcr: .quad 0x80000000
#endif
.section .note.GNU-stack,"",@progbits
