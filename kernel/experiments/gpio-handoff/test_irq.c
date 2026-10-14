/* SPDX-License-Identifier: GPL-2.0-only */
/* Execute the exact installed helper with a bounded MMIO/cache model. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t u32;
#define BIT(n) (1U << (n))
#define GENMASK(h,l) ((~0U >> (31-(h))) & (~0U << (l)))
#define FIELD_GET(m,v) (((v)&(m)) >> __builtin_ctz(m))
#define FIELD_PREP(m,v) (((v)<<__builtin_ctz(m))&(m))
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
#define REG_GPIO(x) (4*(x))
#define REG_GPIOx_MODE GENMASK(3,1)
#define REG_GPIOx_IN_IRQ_HI 2
#define REG_GPIOx_IN_IRQ_ANY 6
#define REG_GPIOx_IN_IRQ_OFF 7
#define REG_GPIOx_LOCK BIT(21)
#define REG_IRQ(g,x) (0x800+0x40*(g)+4*((x)>>5))
struct device { int unused; };
struct gpio_chip { unsigned int ngpio; struct {unsigned int num_parents; void *domain;} irq; };
struct apple_gpio_pinctrl { struct device *dev; void *base, *map; struct gpio_chip gpio_chip; unsigned char irqgrps[7]; };
static struct apple_gpio_pinctrl ctl;
static u32 regs[0x1000/4],cache[512],before[512];
static unsigned int reads,writes,acks,marks;
static int fail_read,fail_write,drop_write;
static struct apple_gpio_pinctrl *gpiochip_get_data(struct gpio_chip *g) { assert(g==&ctl.gpio_chip);return &ctl; }
static void ilinux_probe_path_mark(struct device *d,unsigned int phase) {(void)d;assert(phase>=0x80&&phase<=0x84);marks++;}
#define dev_err_probe(d,e,...) (e)
static void dev_info(struct device *d,const char *fmt,unsigned int n,unsigned int g,unsigned int changed) {(void)d;(void)fmt;assert(n==ctl.gpio_chip.ngpio && g==ctl.gpio_chip.irq.num_parents && changed==writes);}
static int regmap_read(void *m,unsigned int off,unsigned int *v) {
 assert(m==cache && off%4==0 && off/4<ctl.gpio_chip.ngpio);reads++;
 if((int)(off/4)==fail_read)return -EIO;
 *v=cache[off/4];return 0;
}
static int regmap_update_bits(void *m,unsigned int off,unsigned int mask,unsigned int v) {
 assert(m==cache && mask==REG_GPIOx_MODE && off/4<ctl.gpio_chip.ngpio);
 if((int)(off/4)==fail_write)return -EIO;
 cache[off/4]=(cache[off/4]&~mask)|(v&mask);writes++;
 if((int)(off/4)!=drop_write)regs[off/4]=cache[off/4];
 return 0;
}
static unsigned int readl(void *p) {size_t off=(char *)p-(char *)regs;assert(off<ctl.gpio_chip.ngpio*4);return regs[off/4];}
static void writel(u32 mask,void *p) {
 size_t off=(char *)p-(char *)regs;unsigned int group=(off-0x800)/0x40,word=(off-0x800)%0x40/4;
 assert(off>=0x800 && off<sizeof(regs) && !(off%4));
 assert(group<ctl.gpio_chip.irq.num_parents && word*32<ctl.gpio_chip.ngpio);
 unsigned int count=min_t(unsigned int,32,ctl.gpio_chip.ngpio-word*32);
 assert(mask==GENMASK(count-1,0));
 /* Every active source must be masked before the first W1C. */
 for(unsigned int i=0;i<ctl.gpio_chip.ngpio;i++){unsigned int mode=FIELD_GET(REG_GPIOx_MODE,regs[i]);assert(mode<2||mode>6);}
 regs[off/4]&=~mask;acks++;
}
struct irq_chip { int unused; };
struct irq_desc { struct irq_chip chip; unsigned char *data; };
typedef unsigned char u8;
#define container_of(ptr,type,member) ((type *)((char *)(ptr)-__builtin_offsetof(type,member)))
#define for_each_set_bit(bit,addr,size) for((bit)=0;(bit)<(size);(bit)++) if(*(addr)&(1UL<<(bit)))
static unsigned int deliveries,entered,exited;
static struct irq_chip *irq_desc_get_chip(struct irq_desc *d) {return &d->chip;}
static u8 *irq_desc_get_handler_data(struct irq_desc *d) {return d->data;}
static void chained_irq_enter(struct irq_chip *c,struct irq_desc *d) {(void)c;(void)d;entered++;}
static void chained_irq_exit(struct irq_chip *c,struct irq_desc *d) {(void)c;(void)d;exited++;}
static unsigned int readl_relaxed(void *p) {size_t off=(char *)p-(char *)regs;assert(off>=0x800&&off<sizeof(regs));return regs[off/4];}
static int generic_handle_domain_irq(void *domain,unsigned int pin) {(void)domain;assert(pin<ctl.gpio_chip.ngpio);deliveries++;return -EINVAL;}
#include "tested-old-handler.h"
#include "irq-init.h"
static void reset(unsigned int n,unsigned int groups) {
 memset(regs,0,sizeof(regs));memset(cache,0,sizeof(cache));
 ctl.base=regs;ctl.map=cache;ctl.gpio_chip.ngpio=n;ctl.gpio_chip.irq.num_parents=groups;
 reads=writes=acks=marks=0;fail_read=fail_write=drop_write=-1;
 for(unsigned int i=0;i<n&&i<512;i++){
  /* Every mode, mux/pull/group/output-data field represented; all preserved. */
  before[i]=0x508301U|((i%8)<<1)|((i%7)<<16);
  cache[i]=regs[i]=before[i];
 }
 for(unsigned int g=0;g<7;g++)for(unsigned int word=0;word<16;word++)regs[(0x800+g*0x40)/4+word]=~0U;
}
int main(void) {
 reset(32,7);struct irq_desc desc={.data=&ctl.irqgrps[0]};
 for(unsigned int i=0;i<3;i++)apple_gpio_irq_handler(&desc);
 assert(deliveries==96 && entered==3 && exited==3 && regs[REG_IRQ(0,0)/4]==~0U);
 assert(!apple_gpio_t6050_irq_init_hw(&ctl.gpio_chip));
 deliveries=0;apple_gpio_irq_handler(&desc);assert(!deliveries && !regs[REG_IRQ(0,0)/4]);
 unsigned int counts[]={1,31,32,33,61,85,221,512};
 for(unsigned int k=0;k<sizeof(counts)/sizeof(counts[0]);k++){
  unsigned int n=counts[k];reset(n,7);assert(apple_gpio_t6050_irq_init_hw(&ctl.gpio_chip)==0);
  assert(reads==n && acks==7*((n+31)/32));
  for(unsigned int i=0;i<n;i++){
   unsigned int mode=FIELD_GET(REG_GPIOx_MODE,before[i]);
   u32 expected=(mode>=2&&mode<=6)?(before[i]&~REG_GPIOx_MODE)|FIELD_PREP(REG_GPIOx_MODE,7):before[i];
   assert(regs[i]==expected && cache[i]==expected);
  }
  /* Fake chained parent: old pending state retriggers; repaired valid bits do not. */
  for(unsigned int g=0;g<7;g++)for(unsigned int pin=0;pin<n;pin+=32){
   unsigned int cnt=min_t(unsigned int,32,n-pin);assert(!(regs[REG_IRQ(g,pin)/4]&GENMASK(cnt-1,0)));
  }
 }
 reset(221,7);assert(regs[REG_IRQ(0,0)/4]); /* baseline would remain asserted */
 fail_read=2;assert(apple_gpio_t6050_irq_init_hw(&ctl.gpio_chip)==-EIO);assert(!acks);
 reset(221,7);fail_write=2;assert(apple_gpio_t6050_irq_init_hw(&ctl.gpio_chip)==-EIO);assert(!acks);
 reset(221,7);drop_write=2;assert(apple_gpio_t6050_irq_init_hw(&ctl.gpio_chip)==-EIO);assert(!acks);
 reset(221,7);cache[2]|=REG_GPIOx_LOCK;regs[2]=cache[2];assert(apple_gpio_t6050_irq_init_hw(&ctl.gpio_chip)==-EPERM);assert(!acks && !writes);
 unsigned int bad[][2]={{0,7},{513,7},{221,0},{221,8}};
 for(unsigned int i=0;i<4;i++){reset(bad[i][0],bad[i][1]);assert(apple_gpio_t6050_irq_init_hw(&ctl.gpio_chip)==-EINVAL);assert(!reads&&!writes&&!acks);}
 puts("PASS: actual IRQ helper: 8 geometries, pending-source regression, field preservation, 4 errors, 4 invalid geometries");
}
