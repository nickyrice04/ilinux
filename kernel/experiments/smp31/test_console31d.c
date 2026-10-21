/* SPDX-License-Identifier: GPL-2.0-or-later
 * Compile only in the VM. Actual pinned m1n1 functions, simulated MMIO.
 * Bounded longjmp detects continued polling; no real UART is touched.
 */
#include <assert.h>
#include <setjmp.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stddef.h>
typedef uint8_t u8;
typedef uint64_t u64;
typedef int iodev_id_t;
#define UTRSTAT 0x10
#define UTRSTAT_TXBE 2
#define UTXH 0x20
#define DATA_TX_FREE 0x4014
#define DATA_TX8 0x4004
#define USAGE_CONSOLE 1
static u64 serial_base, dock_base;
static unsigned reads, writes;
static bool ready;
static jmp_buf escape;
static uint32_t read32(u64 address) {
    assert(address==0x505200010ULL || address==0x288e2c014ULL);
    if (++reads==32) longjmp(escape,1);
    return ready ? 2 : 0;
}
static void write32(u64 address,uint32_t value) {
    (void)value;
    assert(address==0x505200020ULL || address==0x288e2c004ULL);
    ++writes;
}
#include "uart31d.inc"
#include "dock31d.inc"
struct ops {void (*write)(void *,const void *,size_t);};
struct device {struct ops *ops; unsigned usage; void *opaque;};
static void serial_write(void *unused,const void *buffer,size_t size) {
    (void)unused; uart_write(buffer,size);
}
static void dock_write(void *unused,const void *buffer,size_t size) {
    (void)unused; dockchannel_uart_write(buffer,size);
}
static struct ops serial_ops={serial_write}, dock_ops={dock_write};
static struct device serial_device={&serial_ops,USAGE_CONSOLE,NULL};
static struct device dock_device={&dock_ops,USAGE_CONSOLE,NULL};
static struct device *iodevs[]={&serial_device,&dock_device};
#include "console31d.inc"
static void invoke(unsigned route) {
    if (!route) uart_putbyte('x');
    else _iodev_console_write_helper(route-1,'*',"x",1);
}
int main(void) {
    for (volatile unsigned route=0;route<3;route++) {
        serial_base=0x505200000ULL;dock_base=0x288e28000ULL;
        reads=writes=0;ready=false;
        if (!setjmp(escape)) {invoke(route);assert(!"full transmitter returned unexpectedly");}
        assert(reads==32 && writes==0);
        serial_base=dock_base=0;reads=writes=0;
        invoke(route);assert(reads==0 && writes==0);
        serial_base=0x505200000ULL;dock_base=0x288e28000ULL;
        reads=writes=0;ready=true;
        invoke(route);assert(reads>0 && writes>0);
    }
    puts("ACTUAL-SOURCE-CONSOLE-PASS: 9 cases; blocked polling, zero-base bypass, ready output");
}
