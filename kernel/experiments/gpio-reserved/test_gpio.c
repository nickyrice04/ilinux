/* SPDX-License-Identifier: GPL-2.0-only */
/* The installed helpers and extracted driver callbacks run against MMIO that
 * asserts on every forbidden access. This is not physical-hardware evidence. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t u32;
typedef uint8_t u8;
#define BIT(n) (1U << (n))
#define GENMASK(h,l) ((~0U >> (31-(h))) & (~0U << (l)))
#define FIELD_GET(m,v) (((v)&(m)) >> __builtin_ctz(m))
#define FIELD_PREP(m,v) (((v)<<__builtin_ctz(m))&(m))
#define REG_GPIO(x) (4*(x))
#define REG_GPIOx_DATA BIT(0)
#define REG_GPIOx_MODE GENMASK(3,1)
#define REG_GPIOx_PERIPH GENMASK(6,5)
#define REG_GPIOx_INPUT_ENABLE BIT(9)
#define REG_GPIOx_OUT 1
#define REG_GPIOx_IN_IRQ_HI 2
#define REG_GPIOx_IN_IRQ_ANY 6
#define REG_GPIOx_IN_IRQ_OFF 7
#define REG_GPIOx_LOCK BIT(21)
#define REG_IRQ(g,x) (0x800+0x40*(g)+4*((x)>>5))
#define REGCACHE_FLAT_S 9
#define GPIO_LINE_DIRECTION_IN 1
#define GPIO_LINE_DIRECTION_OUT 0
struct device { int unused; };
struct gpio_chip { unsigned int ngpio; struct {unsigned int num_parents;void *domain;} irq; };
struct apple_gpio_pinctrl {
 struct device *dev; void *base,*map; struct gpio_chip gpio_chip;
 unsigned int npins; bool filter_reserved; u32 valid_pins[16]; u8 irqgrps[7];
};
struct reg_default { unsigned int reg,def; };
struct regmap_config {
 struct reg_default *reg_defaults;
 unsigned int num_reg_defaults,num_reg_defaults_raw,cache_type;
 bool (*readable_reg)(struct device *,unsigned int);
 bool (*writeable_reg)(struct device *,unsigned int);
};
static struct apple_gpio_pinctrl ctl;
static u32 regs[0x1000/4],cache[512],before[512];
static bool forbidden[512];
static unsigned int reads,writes,acks,marks,index_value,deliveries;
static int fail_read,fail_write,drop_write;
static struct apple_gpio_pinctrl *gpiochip_get_data(struct gpio_chip *g) {assert(g==&ctl.gpio_chip);return &ctl;}
static struct apple_gpio_pinctrl *dev_get_drvdata(struct device *d) {(void)d;return &ctl;}
static void ilinux_probe_path_mark(struct device *d,unsigned int phase) {(void)d;assert((phase>=0x80&&phase<=0x84)||(phase>=0x90&&phase<=0x93));marks++;}
static void ilinux_probe_pin_mark(struct device *d,unsigned int pin) {(void)d;assert(pin<512||pin==0xfff);index_value=pin;}
#define dev_err_probe(d,e,...) (e)
static void dev_info(struct device *d,const char *format,...){(void)d;(void)format;}
#include "reserved-pins.h"
static int regmap_read(void *m,unsigned int off,unsigned int *v) {
 assert(m==cache && off%4==0 && off/4<ctl.npins && !forbidden[off/4]);
 if((int)(off/4)==fail_read)return -EIO;
 *v=cache[off/4];return 0;
}
static int regmap_update_bits(void *m,unsigned int off,unsigned int mask,unsigned int v) {
 assert(m==cache && off%4==0 && off/4<ctl.npins && !forbidden[off/4]);
 if((int)(off/4)==fail_write)return -EIO;
 cache[off/4]=(cache[off/4]&~mask)|(v&mask);writes++;
 if((int)(off/4)!=drop_write)regs[off/4]=cache[off/4];
 return 0;
}
static unsigned int readl_relaxed(void *p) {
 size_t off=(char*)p-(char*)regs;
 assert(off<sizeof(regs) && off%4==0);
 if(off<0x800){assert(off/4<ctl.npins && !forbidden[off/4]);reads++;}
 return regs[off/4];
}
#define readl readl_relaxed
static void writel(u32 mask,void *p) {
 size_t off=(char*)p-(char*)regs;
 assert(off>=0x800 && off<sizeof(regs) && off%4==0);
 unsigned int group=(off-0x800)/0x40,first=((off-0x800)%0x40)/4*32;
 assert(group<ctl.gpio_chip.irq.num_parents && first<ctl.npins);
 assert(mask==apple_gpio_valid_word(&ctl,first));
 for(unsigned int pin=0;pin<ctl.npins;pin++)if(!forbidden[pin]){
  unsigned int mode=FIELD_GET(REG_GPIOx_MODE,regs[pin]);assert(mode<2||mode>6);
 }
 regs[off/4]&=~mask;acks++;
}
struct irq_chip {int unused;};
struct irq_desc {struct irq_chip chip;u8 *data;};
#define container_of(ptr,type,member) ((type*)((char*)(ptr)-__builtin_offsetof(type,member)))
#define for_each_set_bit(bit,addr,size) for((bit)=0;(bit)<(size);(bit)++) if(*(addr)&(1UL<<(bit)))
static struct irq_chip *irq_desc_get_chip(struct irq_desc *d){return &d->chip;}
static u8 *irq_desc_get_handler_data(struct irq_desc *d){return d->data;}
static void chained_irq_enter(struct irq_chip *c,struct irq_desc *d){(void)c;(void)d;}
static void chained_irq_exit(struct irq_chip *c,struct irq_desc *d){(void)c;(void)d;}
static int generic_handle_domain_irq(void *domain,unsigned int pin){(void)domain;assert(pin<ctl.npins&&!forbidden[pin]);deliveries++;return 0;}
#include "cache-init.h"
#include "irq-init.h"
#include "tested-runtime.h"
static void reset(unsigned int n,unsigned int groups,bool filtered) {
 memset(&ctl,0,sizeof(ctl));memset(regs,0,sizeof(regs));memset(cache,0,sizeof(cache));memset(forbidden,0,sizeof(forbidden));
 ctl.base=regs;ctl.map=cache;ctl.npins=n;ctl.filter_reserved=filtered;
 ctl.gpio_chip.ngpio=n;ctl.gpio_chip.irq.num_parents=groups;
 reads=writes=acks=marks=index_value=deliveries=0;fail_read=fail_write=drop_write=-1;
 for(unsigned int pin=0;pin<n;pin++){
  ctl.valid_pins[pin/32]|=BIT(pin%32);
  before[pin]=cache[pin]=regs[pin]=0x508301U|((pin%8)<<1)|((pin%7)<<16);
 }
 for(unsigned int g=0;g<7;g++)for(unsigned int word=0;word<16;word++)regs[(0x800+g*0x40)/4+word]=~0U;
}
static void reserved(void){
 assert(!apple_gpio_reserve_range(&ctl,5,3));assert(!apple_gpio_reserve_range(&ctl,112,1));assert(!apple_gpio_reserve_range(&ctl,141,1));
 forbidden[5]=forbidden[6]=forbidden[7]=forbidden[112]=forbidden[141]=true;
}
int main(void){
 struct reg_default defs[512];struct regmap_config config={0};
 unsigned int counts[]={1,31,32,33,61,85,221,512};
 for(unsigned int k=0;k<sizeof(counts)/sizeof(counts[0]);k++){
  unsigned int n=counts[k];reset(n,7,true);
  assert(!apple_gpio_cache_defaults(&ctl,defs,&config));assert(reads==n&&config.num_reg_defaults==n&&index_value==0xfff);
  assert(!apple_gpio_t6050_irq_init_hw(&ctl.gpio_chip));assert(acks==7*((n+31)/32));
  for(unsigned int i=0;i<n;i++)assert((regs[i]&~REG_GPIOx_MODE)==(before[i]&~REG_GPIOx_MODE));
 }
 reset(221,7,true);reserved();
 assert(!apple_gpio_cache_defaults(&ctl,defs,&config));assert(reads==216&&config.num_reg_defaults==216);
 assert(!config.num_reg_defaults_raw&&config.cache_type==REGCACHE_FLAT_S);
 for(unsigned int i=0;i<config.num_reg_defaults;i++){assert(!forbidden[defs[i].reg/4]);assert(defs[i].def==before[defs[i].reg/4]);}
 for(unsigned int i=0;i<512;i++)assert(config.readable_reg(NULL,i*4)==(i<221&&!forbidden[i]));
 assert(!config.writeable_reg(NULL,1)&&!config.readable_reg(NULL,UINT32_MAX));
 assert(apple_gpio_t6050_irq_init_hw(&ctl.gpio_chip)==-EBUSY);assert(!writes&&!acks);
 for(unsigned int g=0;g<7;g++)for(unsigned int first=0;first<221;first+=32)
  regs[REG_IRQ(g,first)/4]=apple_gpio_valid_word(&ctl,first);
 assert(!apple_gpio_t6050_irq_init_hw(&ctl.gpio_chip));assert(acks==49);
 for(unsigned int i=0;i<221;i++)if(forbidden[i]){
  assert(regs[i]==before[i]);unsigned int r=reads,w=writes;
  assert(apple_gpio_get(&ctl.gpio_chip,i)==-EINVAL);assert(apple_gpio_set(&ctl.gpio_chip,i,1)==-EINVAL);
  assert(apple_gpio_direction_input(&ctl.gpio_chip,i)==-EINVAL);assert(apple_gpio_direction_output(&ctl.gpio_chip,i,1)==-EINVAL);
  assert(apple_gpio_get_direction(&ctl.gpio_chip,i)==-EINVAL);assert(reads==r&&writes==w);
 }
 struct irq_desc desc={.data=&ctl.irqgrps[0]};
 for(unsigned int first=0;first<221;first+=32)regs[REG_IRQ(0,first)/4]=~apple_gpio_valid_word(&ctl,first);
 apple_gpio_irq_handler(&desc);assert(!deliveries); /* reserved/tail bits cannot dispatch */
 for(unsigned int first=0;first<221;first+=32)regs[REG_IRQ(0,first)/4]=~0U;
 apple_gpio_irq_handler(&desc);assert(deliveries==216); /* excludes reserved + tail */
 assert(apple_gpio_get(&ctl.gpio_chip,221)==-EINVAL);
 assert(!apple_gpio_set(&ctl.gpio_chip,10,1));assert(!apple_gpio_direction_input(&ctl.gpio_chip,10));
 assert(!apple_gpio_direction_output(&ctl.gpio_chip,10,1));assert(apple_gpio_get_direction(&ctl.gpio_chip,10)==GPIO_LINE_DIRECTION_OUT);assert(apple_gpio_get(&ctl.gpio_chip,10)==1);
 reset(221,7,true);u32 saved[16];memcpy(saved,ctl.valid_pins,sizeof(saved));
 assert(apple_gpio_reserve_range(&ctl,0,0)==-EINVAL);assert(apple_gpio_reserve_range(&ctl,221,1)==-EINVAL);
 assert(apple_gpio_reserve_range(&ctl,220,2)==-EINVAL);assert(apple_gpio_reserve_range(&ctl,UINT32_MAX,2)==-EINVAL);
 assert(apple_gpio_reserve_range(&ctl,1,UINT32_MAX)==-EINVAL);assert(!memcmp(saved,ctl.valid_pins,sizeof(saved)));
 reserved();memcpy(saved,ctl.valid_pins,sizeof(saved));assert(apple_gpio_reserve_range(&ctl,4,3)==-EINVAL);assert(!memcmp(saved,ctl.valid_pins,sizeof(saved)));
 for(int failure=0;failure<4;failure++){
  reset(61,7,true);if(failure==0)fail_read=2;if(failure==1)fail_write=2;if(failure==2)drop_write=2;if(failure==3)cache[2]|=REG_GPIOx_LOCK;
  assert(apple_gpio_t6050_irq_init_hw(&ctl.gpio_chip)==(failure==3?-EPERM:-EIO));assert(!acks);
 }
 reset(1,7,true);assert(!apple_gpio_reserve_range(&ctl,0,1));forbidden[0]=true;
 assert(apple_gpio_cache_defaults(&ctl,defs,&config)==-EINVAL&&reads==0);
 reset(221,7,false);memset(ctl.valid_pins,0,sizeof(ctl.valid_pins));assert(apple_gpio_pin_available(&ctl,5));
 assert(!apple_gpio_pin_available(&ctl,221));
 puts("PASS: exact helpers/callbacks; 216 permitted reads, zero forbidden MMIO; IRQ masks/dispatch; eight geometries; malformed ranges; error propagation; legacy gate");
}
