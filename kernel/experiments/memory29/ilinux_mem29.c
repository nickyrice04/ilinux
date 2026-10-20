// SPDX-License-Identifier: GPL-2.0-only
/* Architectural memory attributes only. No MMIO, MSR, page-table changes,
 * physical addresses, or user-memory contents are exposed. */
#include <linux/module.h>
#include <linux/mm.h>
#include <linux/of.h>
#include <linux/cpu.h>
#include <linux/sched.h>
#include <asm/sysreg.h>
#include <asm/pgtable.h>

static int __init mem29_init(void)
{
	unsigned long address;
	struct mm_struct *mm = current->mm;
	pgd_t *pgd;
	p4d_t *p4d;
	pud_t *pud;
	pmd_t *pmd;
	pte_t *pte;
	spinlock_t *ptl;
	u64 descriptor = 0, midr, mpidr, sctlr, tcr, mair, ctr, clidr;
	int level = 0, cpu;

	if (!of_machine_is_compatible("apple,j716c") ||
	    !of_machine_is_compatible("apple,t6050") ||
	    num_online_cpus() != 1)
		return -ENODEV;
	cpu = get_cpu();
	midr = read_sysreg(midr_el1);
	mpidr = read_sysreg(mpidr_el1);
	if (cpu != 0 || ((midr >> 4) & 0xfff) != 0x68 ||
	    (midr >> 24) != 0x61 ||
	    (mpidr & 0xff00ffffffULL) != 0x40000) {
		put_cpu();
		return -ENODEV;
	}
	sctlr = read_sysreg(sctlr_el1);
	tcr = read_sysreg(tcr_el1);
	mair = read_sysreg(mair_el1);
	ctr = read_sysreg(ctr_el0);
	clidr = read_sysreg(clidr_el1);
	put_cpu();

	/* Inspect only attributes of this insmod process's initial stack page.
	 * Never dereference user data or emit its address/PFN. Holding mmap's
	 * write lock pins the page-table topology; the PTE lock protects its entry.
	 * No mapping is added or changed. */
	if (!mm)
		return -EINVAL;
	mmap_write_lock(mm);
	address = mm->start_stack;
	pgd = pgd_offset(mm, address);
	if (pgd_none(*pgd) || pgd_bad(*pgd))
		goto out;
	p4d = p4d_offset(pgd, address);
	if (p4d_none(*p4d) || p4d_bad(*p4d))
		goto out;
	pud = pud_offset(p4d, address);
	if (pud_leaf(*pud)) {
		descriptor = pud_val(*pud);
		level = 1;
		goto out;
	}
	if (pud_none(*pud) || pud_bad(*pud))
		goto out;
	pmd = pmd_offset(pud, address);
	if (pmd_leaf(*pmd)) {
		descriptor = pmd_val(*pmd);
		level = 2;
		goto out;
	}
	if (pmd_none(*pmd) || pmd_bad(*pmd))
		goto out;
	ptl = pte_lockptr(mm, pmd);
	spin_lock(ptl);
	pte = pte_offset_kernel(pmd, address);
	descriptor = pte_val(READ_ONCE(*pte));
	level = 3;
	spin_unlock(ptl);
out:
	mmap_write_unlock(mm);
	pr_info("ilinux_mem29 sctlr=%016llx tcr=%016llx mair=%016llx ctr=%016llx clidr=%016llx page_shift=%u level=%d attrs=%04llx normal_index=%u\n",
		sctlr, tcr, mair, ctr, clidr, PAGE_SHIFT, level,
		descriptor & (PTE_ATTRINDX_MASK | PTE_SHARED | PTE_AF | PTE_VALID),
		MT_NORMAL);
	/* Absent mapping is reported as level=0; the other registers remain useful. */
	return 0;
}
module_init(mem29_init);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("t6050 attempt29 one-shot architectural memory attributes");
