/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Original fixed-width startup write helper, placed at helper offset 352.
 * x0 = one of the controller's two fixed PMGR CPU1 start addresses.
 * w1 = 2, validated by the controller before this call.
 * Returns the fixed marker 0x31e after the store and full-system barrier.
 * No exception-guard change, register readback, retry, SEV, stack or LR edit.
 * The controller journals intent before P_CALL. A missing reply leaves
 * completion unknown, including when the store executed before a fault.
 * This source alone never authorizes a target invocation.
 */
.text
.p2align 2
.global smp31e_start_write
.type smp31e_start_write, %function
smp31e_start_write:
    str w1, [x0]
    dsb sy
    movz x0, #0x31e
    ret
.size smp31e_start_write, . - smp31e_start_write
