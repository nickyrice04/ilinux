/* SPDX-License-Identifier: MIT */
/* VM-only PID1: the shipping module must refuse this non-J716c machine. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <sys/reboot.h>
#include <sys/syscall.h>
#include <unistd.h>
int main(void) {
    alarm(20);
    int fd=open("/ilinux_mem29.ko",O_RDONLY), rc=-1, error=0;
    if(fd>=0) {rc=syscall(SYS_finit_module,fd,"",0); error=errno;close(fd);}
    printf("MEMORY29-VM-REFUSAL %s rc=%d errno=%d\n",
           rc==-1 && error==ENODEV ? "PASS" : "FAIL",rc,error);
    /* Separate VM-only control build bypasses identity, never shipped. This
     * exercises the exact architectural snapshot/page-walk code in a guest. */
    fd=open("/control.ko",O_RDONLY);
    rc=fd>=0 ? syscall(SYS_finit_module,fd,"",0) : -1;
    if(fd>=0)close(fd);
    printf("MEMORY29-VM-CONTROL %s rc=%d\n",rc==0 ? "PASS" : "FAIL",rc);
    fflush(stdout);sync();reboot(RB_POWER_OFF);for(;;) pause();
}
