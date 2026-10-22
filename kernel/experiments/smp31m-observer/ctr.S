/* SPDX-License-Identifier: GPL-2.0-or-later */
/* CPU0-only pre-start metadata reader. No cache or system-register writes. */
.text
.global smp31m_read_ctr
smp31m_read_ctr:
    mrs x0, CTR_EL0
    ret
