/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include "proxy_policy.h"

int main(void)
{
    assert(ilinux_j716c_proxy_usb2(0x6050, 0x0e, 1, 0));
    assert(!ilinux_j716c_proxy_usb2(0x6051, 0x0e, 1, 0));
    assert(!ilinux_j716c_proxy_usb2(0x6050, 0x0f, 1, 0));
    assert(!ilinux_j716c_proxy_usb2(0x8142, 0x24, 1, 0));
    assert(!ilinux_j716c_proxy_usb2(0x6050, 0x0e, 0, 0));
    assert(!ilinux_j716c_proxy_usb2(0x6050, 0x0e, 1, 1));
    return 0;
}
