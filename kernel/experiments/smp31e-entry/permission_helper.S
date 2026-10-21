/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Original, fixed pre-start translation probes. Append after the 192-byte
 * 31B helper. AT updates only PAR; save/restore that diagnostic register.
 * No mappings, permissions, cache controls or HCR changes. Never run after
 * CPU1 start, and never call an EL2 AT routine from EL1.
 */
.text
.p2align 2
.global smp31e_permission_tail
.type smp31e_permission_tail, %function
smp31e_permission_tail:
    mrs x2, PAR_EL1
    at s1e1r, x0
    isb
    mrs x0, PAR_EL1
    msr PAR_EL1, x2
    isb
    ret
    nop
    mrs x2, PAR_EL1
    at s1e1w, x0
    isb
    mrs x0, PAR_EL1
    msr PAR_EL1, x2
    isb
    ret
    nop
    mrs x2, PAR_EL1
    at s1e2r, x0
    isb
    mrs x0, PAR_EL1
    msr PAR_EL1, x2
    isb
    ret
    nop
    mrs x2, PAR_EL1
    at s1e2w, x0
    isb
    mrs x0, PAR_EL1
    msr PAR_EL1, x2
    isb
    ret
    nop
    mrs x0, CurrentEL
    cmp x0, #8
    b.ne .Lnot_el2
    mrs x0, HCR_EL2
    ret
.Lnot_el2:
    mov x0, xzr
    ret
    nop
.size smp31e_permission_tail, . - smp31e_permission_tail
