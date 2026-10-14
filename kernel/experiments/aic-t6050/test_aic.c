/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Execute actual driver bodies against a rejecting fake register bank. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
typedef uint32_t u32;
typedef uint64_t u64;
typedef unsigned long irq_hw_number_t;
typedef unsigned long cpumask_t;
#define __initconst
#define __iomem
#define __exception_irq_entry
#define BIT(n) (1UL << (n))
#define GENMASK(h,l) ((~0UL >> (63-(h))) & (~0UL << (l)))
#define FIELD_GET(m,v) (((v) & (m)) >> __builtin_ctzl(m))
#define FIELD_PREP(m,v) (((unsigned long)(v) << __builtin_ctzl(m)) & (m))
#define sys_reg(o,p,n,m,r) (((o)<<14)|((p)<<11)|((n)<<7)|((m)<<3)|(r))
#define cntp_ctl_el0 sys_reg(3,3,14,2,1)
#define cntv_ctl_el0 sys_reg(3,3,14,3,1)
#define SYS_CNTP_CTL_EL02 sys_reg(3,5,14,2,1)
#define SYS_CNTV_CTL_EL02 sys_reg(3,5,14,3,1)
#define SYS_ICH_HCR_EL2 sys_reg(3,4,12,11,0)
#define SYS_ICH_MISR_EL2 sys_reg(3,4,12,11,2)
#define ICH_HCR_EL2_En BIT(0)
#define SYS_IMP_APL_PMCR0_EL1 sys_reg(3,1,15,0,0)
#define PMCR0_IMODE GENMASK(10,8)
#define PMCR0_IACT BIT(11)
#define PMCR0_IMODE_OFF 0
#define PMCR0_IMODE_FIQ 4
#define ARCH_TIMER_CTRL_ENABLE BIT(0)
#define ARCH_TIMER_CTRL_IT_MASK BIT(1)
#define ARCH_TIMER_CTRL_IT_STAT BIT(2)
#define AIC_IRQ 0
#define AIC_FIQ 1
#define AIC_TMR_HV_PHYS 0
#define AIC_TMR_HV_VIRT 1
#define AIC_TMR_GUEST_PHYS 2
#define AIC_TMR_GUEST_VIRT 3
#define AIC_CPU_PMU_E 4
#define AIC_CPU_PMU_P 5
#define IRQ_TYPE_SENSE_MASK 15
#define IRQ_TYPE_LEVEL_HIGH 4
#define DEFINE_STATIC_KEY_TRUE(n) bool n = true
#define DEFINE_PER_CPU(t,n) t n
#define static_branch_likely(p) (*(p))
#define __this_cpu_read(n) (n)
#define __this_cpu_write(n,v) ((n)=(v))
#define __this_cpu_or(n,v) ((n)|=(v))
#define __this_cpu_and(n,v) ((n)&=(v))
#define unlikely(n) (n)
#define WARN_ON(n) (assert(!(n)),0)
#define pr_err_ratelimited(...) do {} while (0)
struct irq_data { unsigned long hw; bool masked; };
struct pt_regs { int unused; };
struct irq_domain { void *host_data; };
struct irq_fwspec { int param_count; void *fwnode; u32 param[4]; };
#define irqd_to_hwirq(d) ((d)->hw)
#define irqd_irq_masked(d) ((d)->masked)
#define is_of_node(n) ((n)!=NULL)
static bool hyp;
static bool allowed[65536];
static u64 bank[65536];
static unsigned reads[65536], writes[65536], irqs[16], ipis, barriers, mmio;
#define is_kernel_in_hyp_mode() (hyp)
static u64 reg_read(unsigned r) { assert(r<65536 && allowed[r]); reads[r]++; return bank[r]; }
static void reg_write(unsigned r,u64 v) { assert(r<65536 && allowed[r]); writes[r]++; bank[r]=v; }
static void reg_update(unsigned r,u64 clear,u64 set) {
    u64 old=reg_read(r), val=(old & ~clear)|set;
    if (val!=old) reg_write(r,val);
}
#define read_sysreg(r) reg_read(r)
#define read_sysreg_s(r) reg_read(r)
#define write_sysreg_s(v,r) reg_write(r,v)
#define sysreg_clear_set(r,c,s) reg_update(r,c,s)
#define sysreg_clear_set_s(r,c,s) reg_update(r,c,s)
#define isb() (barriers++)
#define smp_processor_id() 0
static void aic_handle_ipi(struct pt_regs *r) { (void)r; ipis++; }
static void generic_handle_domain_irq(void *d,unsigned long h) { (void)d; assert(h<16); irqs[h]++; }
static u32 readl(void *p) { (void)p; return 0; }
#define aic_ic_read(ic,r) ((void)(ic),(void)(r),0U)
#define aic_ic_write(ic,r,v) ((void)(ic),(void)(r),(void)(v),mmio++)
#include "tested-aic.c"

static struct aic_irq_chip chip;
static void reset(const struct aic_info *info, bool el2) {
    memset(bank,0,sizeof(bank)); memset(reads,0,sizeof(reads)); memset(writes,0,sizeof(writes));
    memset(allowed,0,sizeof(allowed)); memset(irqs,0,sizeof(irqs));
    chip=(struct aic_irq_chip){.info=*info,.nr_die=1,.nr_irq=1024};
    aic_irqc=&chip; hyp=el2; use_fast_ipi=info->fast_ipi;
    use_local_fast_ipi=info->local_fast_ipi; ipis=barriers=mmio=0;
    aic_fiq_unmasked=~0U;
    allowed[cntp_ctl_el0]=allowed[cntv_ctl_el0]=true;
    allowed[SYS_IMP_APL_PMCR0_EL1]=true;
    allowed[SYS_IMP_APL_IPI_SR_EL1]=info->fast_ipi;
    allowed[SYS_CNTP_CTL_EL02]=allowed[SYS_CNTV_CTL_EL02]=el2;
    allowed[SYS_IMP_APL_VM_TMR_FIQ_ENA_EL2]=el2 && info->guest_timer_fiq;
    allowed[SYS_ICH_HCR_EL2]=allowed[SYS_ICH_MISR_EL2]=el2 && info->guest_timer_fiq;
    allowed[SYS_IMP_APL_UPMCR0_EL1]=allowed[SYS_IMP_APL_UPMSR_EL1]=info->uncore_pmu;
}
static int translate(unsigned idx, unsigned long *hw) {
    struct irq_domain d={.host_data=&chip}; unsigned type=0;
    struct irq_fwspec f={.param_count=3,.fwnode=&chip,.param={AIC_FIQ,idx,IRQ_TYPE_LEVEL_HIGH}};
    int ret=aic_irq_domain_translate(&d,&f,hw,&type);
    if (!ret) assert(type==IRQ_TYPE_LEVEL_HIGH);
    return ret;
}
int main(void) {
    const struct aic_info *profiles[]={&aic1_info,&aic1_fipi_info,&aic1_local_fipi_info,&aic2_info,&aic3_info,&aic3_t6050_info};
    unsigned scenarios=0;
    for (unsigned p=0;p<6;p++) for (unsigned el2=0;el2<2;el2++) {
        const struct aic_info *i=profiles[p]; reset(i,el2);
        bank[cntp_ctl_el0]=bank[cntv_ctl_el0]=5;
        bank[SYS_CNTP_CTL_EL02]=bank[SYS_CNTV_CTL_EL02]=5;
        bank[SYS_IMP_APL_VM_TMR_FIQ_ENA_EL2]=0x83;
        bank[SYS_IMP_APL_PMCR0_EL1]=0xf55;
        bank[SYS_IMP_APL_UPMCR0_EL1]=0x70055;
        bank[SYS_ICH_HCR_EL2]=3;
        assert(aic_init_cpu(0)==0 && !aic_fiq_unmasked && barriers==1);
        assert(bank[cntp_ctl_el0]==7 && bank[cntv_ctl_el0]==7);
        assert(bank[SYS_IMP_APL_PMCR0_EL1]==0x55);
        assert(writes[SYS_IMP_APL_IPI_SR_EL1]==i->fast_ipi);
        assert(bank[SYS_IMP_APL_UPMCR0_EL1]==(i->uncore_pmu?0x55:0x70055));
        if (el2 && i->guest_timer_fiq) assert(bank[SYS_IMP_APL_VM_TMR_FIQ_ENA_EL2]==0x80 && bank[SYS_ICH_HCR_EL2]==2);
        if (el2 && !i->guest_timer_fiq) assert(bank[SYS_CNTP_CTL_EL02]==7 && bank[SYS_CNTV_CTL_EL02]==7);
        if (!el2) assert(!reads[SYS_CNTP_CTL_EL02] && !reads[SYS_CNTV_CTL_EL02]);
        scenarios++;
        reset(i,el2);
        bank[cntp_ctl_el0]=bank[cntv_ctl_el0]=5;
        bank[SYS_IMP_APL_IPI_SR_EL1]=1;
        bank[SYS_IMP_APL_VM_TMR_FIQ_ENA_EL2]=3;
        bank[SYS_CNTP_CTL_EL02]=bank[SYS_CNTV_CTL_EL02]=5;
        bank[SYS_IMP_APL_UPMCR0_EL1]=0x40055;
        bank[SYS_IMP_APL_UPMSR_EL1]=1;
        struct pt_regs r={0}; aic_handle_fiq(&r); aic_handle_irq(&r);
        assert(irqs[0]==1 && irqs[1]==1 && ipis==i->fast_ipi);
        assert(irqs[2]==(el2 && i->guest_timer_fiq) && irqs[3]==(el2 && i->guest_timer_fiq));
        if (i->uncore_pmu) assert(bank[SYS_IMP_APL_UPMCR0_EL1]==0x55);
        scenarios++;
        unsigned long hw;
        for (unsigned idx=0;idx<AIC_NR_FIQ;idx++) {
            int ret=translate(idx,&hw);
            bool missing=(!el2 && idx<2) || (!i->guest_timer_fiq && (idx==AIC_VGIC_MI || (el2 && (idx==2 || idx==3))));
            assert(ret==(missing?-ENOENT:0));
            if (!ret && !el2 && (idx==2 || idx==3)) assert(hw==idx-2);
        }
        assert(translate(AIC_NR_FIQ,&hw)==-EINVAL);
        scenarios++;
    }
    for (unsigned t=2;t<=3;t++) {
        reset(&aic3_info,true); unsigned bit=t==2?2:1;
        struct irq_data d={.hw=t}; bank[SYS_IMP_APL_VM_TMR_FIQ_ENA_EL2]=0x83;
        aic_fiq_mask(&d); assert(bank[SYS_IMP_APL_VM_TMR_FIQ_ENA_EL2]==(0x83U&~bit));
        aic_fiq_unmask(&d); assert(bank[SYS_IMP_APL_VM_TMR_FIQ_ENA_EL2]==0x83);
        aic_fiq_set_mask(&d); aic_fiq_eoi(&d); assert(bank[SYS_IMP_APL_VM_TMR_FIQ_ENA_EL2]==0x83);
        reset(&aic3_t6050_info,true);
        aic_fiq_mask(&d); aic_fiq_unmask(&d); aic_fiq_set_mask(&d); aic_fiq_eoi(&d);
        /* Any forbidden register access above asserts immediately. */
        scenarios++;
    }
    printf("PASS: %u actual-driver scenarios; six profiles, EL1/EL2, timers, IRQs, masks and denied mappings\n",scenarios);
    return 0;
}
