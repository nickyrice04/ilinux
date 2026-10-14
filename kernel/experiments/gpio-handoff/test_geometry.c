/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include <errno.h>
#include <stdio.h>
#define REG_GPIO(x) (4*(x))
#define REG_IRQ(g,x) (0x800+0x40*(g)+4*((x)>>5))
#define IORESOURCE_MEM 1
#define dev_err_probe(d,e,...) (e)
struct resource { unsigned long size; };
struct platform_device {int dev; struct resource *r;};
struct regmap_config {unsigned int max_register,num_reg_defaults_raw;};
static struct resource *platform_get_resource(struct platform_device *p,int t,int i) {assert(t==1&&i==0);return p->r;}
static unsigned long resource_size(struct resource *r) {return r->size;}
#include "tested-geometry.h"
int main(void) {
 struct resource r={0x4000};struct platform_device p={0,&r};struct regmap_config c;
 unsigned int counts[]={61,85,221,512};
 for(unsigned int i=0;i<4;i++){
  unsigned int n=counts[i];assert(!geometry(true,n,7,&p,&c));
  assert(c.num_reg_defaults_raw==n && c.max_register==(n-1)*4);
  /* Emulate actual regcache raw-default reads: no undeclared register. */
  for(unsigned int off=0;off<c.num_reg_defaults_raw*4;off+=4)assert(off<n*4);
 }
 assert(!geometry(false,221,7,&p,&c));assert(c.num_reg_defaults_raw==512 && c.max_register==2048);
 assert(c.num_reg_defaults_raw>221); /* baseline overreads this modeled bank */
 assert(geometry(true,0,7,&p,&c)==-EINVAL);assert(geometry(true,513,7,&p,&c)==-EINVAL);
 assert(geometry(true,221,8,&p,&c)==-EINVAL);
 p.r=NULL;assert(geometry(true,221,7,&p,&c)==-EINVAL);p.r=&r;
 r.size=883;assert(geometry(true,221,0,&p,&c)==-EINVAL);
 r.size=REG_IRQ(6,220)+3;assert(geometry(true,221,7,&p,&c)==-EINVAL);
 r.size++;assert(!geometry(true,221,7,&p,&c));
 r.size=4;assert(!geometry(true,1,0,&p,&c));
 puts("PASS: actual geometry/config: declared banks, old overread reproduced, legacy unchanged, malformed resources rejected");
}
