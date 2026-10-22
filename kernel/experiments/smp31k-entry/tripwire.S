/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Original observation-only candidate, linked at image+0xb00.
 * Only natural late entry through image+0x800 is intercepted. No RVBAR change.
 * No return to the primary stack/relocations/BSS. Human return bounds the spin.
 * MPIDR/CurrentEL may trap; phase zero does not distinguish fetch/store failure.
 */
.text
.global cold_tripwire
cold_tripwire:
    adrp x0, cold_record
    add x0, x0, :lo12:cold_record
    mov x8, #1
    str x8, [x0]
    dsb sy
    mrs x8, MPIDR_EL1
    ubfx x8, x8, #0, #24
    str x8, [x0, #16]
    dsb sy
    mov x8, #2
    str x8, [x0]
    dsb sy
    mrs x9, CurrentEL
    str x9, [x0, #8]
    dsb sy
    mov x8, #3
    str x8, [x0]
    dsb sy
1:  b 1b
