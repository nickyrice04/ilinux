/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,v) ((x)=(v))
static bool ilinux_probe_active;
static unsigned int ilinux_sched_phase,ilinux_sched_switches,renders;
static int ilinux_sched_prev,ilinux_sched_next;
static bool ilinux_probe_fb_mark(unsigned int lane,unsigned int value){assert(lane==1&&value<256);renders++;return true;}
#include "old-hook.h"
#include "new-hook.h"
int main(void){
 ilinux_probe_sched_mark(5,1,2);assert(!renders&&!ilinux_sched_switches);
 ilinux_probe_active=true;
 for(unsigned int i=0;i<10000;i++)old_sched_mark(5,1,2);
 assert(renders==10000&&ilinux_sched_switches==10000);
 renders=ilinux_sched_switches=0;
 for(unsigned int i=0;i<10000;i++){ilinux_probe_sched_mark(5,3,4);ilinux_probe_sched_mark(6,0,0);ilinux_probe_sched_mark(0x31,0,0);}
 assert(!renders&&ilinux_sched_switches==10000&&ilinux_sched_phase==0x31&&ilinux_sched_prev==3&&ilinux_sched_next==4);
 ilinux_probe_active=false;ilinux_probe_sched_mark(5,5,6);assert(ilinux_sched_prev==3&&ilinux_sched_switches==10000);
 puts("PASS: actual old hook 10000 render calls; new hook 30000 checkpoints/zero render calls; PID/count/phase and inactive gating preserved");
}
