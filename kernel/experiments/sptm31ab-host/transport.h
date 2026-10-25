/* SPDX-License-Identifier: MIT */
#ifndef ILINUX_SPTM31AB_TRANSPORT_H
#define ILINUX_SPTM31AB_TRANSPORT_H
#include <stdint.h>

/* Normal external AAPCS functions; no inline-assembly clobber promise and no
 * success result. These require a qualified resident-monitor call context,
 * owned aligned stack, executable placement, and the actual lifecycle/transport
 * preservation contract. They are uncalled inspection artifacts in31AB.
 * No live invocation is authorized or validated by compilation or emulation.
 * They do not acquire monitor state or authenticate an entry profile. */
void host_fixups_complete(void);
void host_register_cpu(uint64_t physical_affinity);
void host_register_exception_return(uint64_t handler_address);

#endif
