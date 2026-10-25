/* SPDX-License-Identifier: MIT */
#ifndef ILINUX_TRANSLATION31AB_PROBE_H
#define ILINUX_TRANSLATION31AB_PROBE_H
#include <stdint.h>

enum translation31ab_status {
    TRANSLATION31AB_EXECUTED = 0,
    TRANSLATION31AB_WRONG_EL = 1,
    TRANSLATION31AB_HCR_PROFILE = 2,
    TRANSLATION31AB_DAIF_OPEN = 3,
    TRANSLATION31AB_MMU_OFF = 4
};

struct translation31ab_result {
    uint64_t status;
    uint64_t par;
};

/* AAPCS64 returns this pair in x0/x1. No memory operand is dereferenced.
 * Caller must qualify ordinary AArch64 EL2, a 64-bit PAR format, legal access
 * to these system registers/instructions, and stable translation tables. All
 * DAIF masks must already be set, with no reentrant PAR user. The function
 * refuses EL1/EL3, E2H/TGE, open DAIF masks, or SCTLR_EL2.M == 0. EL0 is
 * excluded: its CurrentEL read can trap before a refusal. These checks
 * are not authentication of an Apple native execution profile.
 *
 * EXECUTED means AT completed and returned raw PAR, including any PAR.F fault.
 * Refusal returns par == 0 without touching PAR. On normal return the original
 * 64-bit PAR is restored. A trap/nonreturn cannot promise restoration.
 * No target load/store, monitor call, or translation-control write occurs.
 * AT may affect translation caches/access flags under an enabled hardware
 * access-flag regime; this is not a universal side-effect-free memory read.
 */
struct translation31ab_result translation31ab_s1e2w(uint64_t virtual_address);
#endif
