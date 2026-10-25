/* SPDX-License-Identifier: MIT */
/* AT helpers are called only after the finite profile checks. The new host
 * owns its PAR state and never returns to the producer. Restore low64 only. */
.section .text.probe,"ax",%progbits
.global visible31ac_read_at
.type visible31ac_read_at,%function
visible31ac_read_at:
    mrs x2, PAR_EL1
    at s1e2r, x0
    isb
    mrs x0, PAR_EL1
    msr PAR_EL1, x2
    isb
    ret
.size visible31ac_read_at, .-visible31ac_read_at
.global visible31ac_write_at
.type visible31ac_write_at,%function
visible31ac_write_at:
    mrs x2, PAR_EL1
    at s1e2w, x0
    isb
    mrs x0, PAR_EL1
    msr PAR_EL1, x2
    isb
    ret
.size visible31ac_write_at, .-visible31ac_write_at
.global visible31ac_read_tcr2
.type visible31ac_read_tcr2,%function
visible31ac_read_tcr2:
    mrs x0, S3_4_C2_C0_3
    ret
.size visible31ac_read_tcr2, .-visible31ac_read_tcr2
.global visible31ac_read_ctr
.type visible31ac_read_ctr,%function
visible31ac_read_ctr:
    mrs x0, CTR_EL0
    ret
.size visible31ac_read_ctr, .-visible31ac_read_ctr
.global visible31ac_clean
.type visible31ac_clean,%function
visible31ac_clean:
    dc cvac, x0
    ret
.size visible31ac_clean, .-visible31ac_clean
.global visible31ac_barrier
.type visible31ac_barrier,%function
visible31ac_barrier:
    dsb sy
    ret
.size visible31ac_barrier, .-visible31ac_barrier
.section .note.GNU-stack,"",%progbits
