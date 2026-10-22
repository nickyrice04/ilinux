/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Original fixed CPU0 leaf. No arguments, stack or memory reads.
 * Same two previously used CPU1 stores, with no host request between them.
 * It is not atomic and does not alter the caller's interrupt state.
 */
.text
.balign 4
.global ilinux_31n_start_pair
.type ilinux_31n_start_pair, %function
ilinux_31n_start_pair:
    movz x8, #0x8000
    movk x8, #0x8068, lsl #16
    movk x8, #2, lsl #32
    mov w9, #2
    dsb sy
    str w9, [x8, #4]
    dsb sy
    str w9, [x8, #8]
    dsb sy
    mov x0, #0x314e
    ret
.size ilinux_31n_start_pair, .-ilinux_31n_start_pair
