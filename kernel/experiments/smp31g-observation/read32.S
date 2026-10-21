/* SPDX-License-Identifier: GPL-2.0-or-later
 * Original fixed-width MMIO read. Caller binds only two reviewed PS addresses.
 * No exception guard changes; only used after guarded baseline reads succeed.
 */
.text
.balign 16
.global smp31g_read32
smp31g_read32:
    dsb sy
    ldr w0, [x0]
    dsb sy
    ret
