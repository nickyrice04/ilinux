/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Original prefixes. Link .text at zero with normal_helper supplied as an
 * absolute symbol. The four MOV instructions materialize a full 64-bit address
 * without an ADRP range assumption. No stack, MMIO, cache or system writes.
 * A failed first Normal store can prevent the subsequent Device recorder.
 */
.text
.macro prefix name, location, record_delta, destination
    .org \location
    .global \name
\name:
    movz x8, #:abs_g0_nc:(normal_helper + \record_delta)
    movk x8, #:abs_g1_nc:(normal_helper + \record_delta)
    movk x8, #:abs_g2_nc:(normal_helper + \record_delta)
    movk x8, #:abs_g3:(normal_helper + \record_delta)
    mov x9, #1
    str x9, [x8]
    dsb sy
    mrs x9, MPIDR_EL1
    ubfx x9, x9, #0, #24
    str x9, [x8, #8]
    dsb sy
    mov x9, #2
    str x9, [x8]
    dsb sy
    b \destination
.endm
prefix normal_vector_prefix, 0xc00, 0x1000, existing_vector_recorder
prefix normal_cold_prefix, 0xd00, 0x1080, existing_cold_recorder
