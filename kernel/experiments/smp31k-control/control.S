/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Original returning CPU0 leaf. Caller binds x0 to the middle word of a
 * separately owned scratch block and x1 to a fixed marker or saved original.
 * One aligned 64-bit store to owned SMP-shared RAM; no SEV, stack, MSR or MMIO.
 * x0/x1 are caller-saved. x30 is unchanged; this is not a reset recorder.
 */
.text
.balign 16
.global smp31k_control_store
.type smp31k_control_store, %function
smp31k_control_store:
    str x1, [x0]
    dsb sy
    movz x0, #0x314b
    ret
.size smp31k_control_store, . - smp31k_control_store
