/* SPDX-License-Identifier: MIT */
#ifndef ILINUX_DIRECT31AH_PROXY_POLICY_H
#define ILINUX_DIRECT31AH_PROXY_POLICY_H

/* A software-only decision: it does not access MMIO or change any carrier. */
static inline int ilinux_j716c_proxy_usb2(unsigned chip, unsigned board,
                                       int deferred_usb2, int window_already_offered)
{
    return chip == 0x6050 && board == 0x0e && deferred_usb2 && !window_already_offered;
}

#endif
