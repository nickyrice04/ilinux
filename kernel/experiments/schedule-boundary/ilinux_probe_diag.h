/* SPDX-License-Identifier: GPL-2.0-only */
/* Opt-in, single-CPU RAM-boot diagnostics. No device or routing changes. */
#include <linux/jiffies.h>
#include <linux/of.h>
#include <linux/preempt.h>
#include <linux/timer.h>
#include <linux/sched.h>
#include <linux/printk.h>
#include <clocksource/arm_arch_timer.h>
#include <asm/virt.h>
#include <asm/sysreg.h>
#include <asm/ptrace.h>

bool ilinux_probe_diag;
static bool ilinux_probe_active;
static unsigned int ilinux_probe_phase;
static unsigned int ilinux_probe_device;
static unsigned int ilinux_probe_worker;
static unsigned int ilinux_probe_heartbeats;
static unsigned long ilinux_probe_started;
static struct timer_list ilinux_probe_watch;
static unsigned int ilinux_sched_phase, ilinux_sched_switches;
static int ilinux_sched_prev, ilinux_sched_next;

/* Fixed framebuffer status cells: no printk, allocation or scheduler locks. */
extern bool ilinux_probe_fb_mark(unsigned int lane, unsigned int value);
void ilinux_probe_sched_mark(unsigned int phase, int prev, int next);

void ilinux_probe_sched_mark(unsigned int phase, int prev, int next)
{
	if (!READ_ONCE(ilinux_probe_active))
		return;
	WRITE_ONCE(ilinux_sched_phase, phase);
	if (phase == 5) {
		WRITE_ONCE(ilinux_sched_prev, prev);
		WRITE_ONCE(ilinux_sched_next, next);
		WRITE_ONCE(ilinux_sched_switches, ilinux_sched_switches + 1);
	}
	ilinux_probe_fb_mark(1, phase);
}

static int __init ilinux_probe_setup(char *value)
{
	if (strcmp(value, "1"))
		return 0;
	ilinux_probe_diag = true;
	return 1;
}
__setup("ilinux_probe_diag=", ilinux_probe_setup);

static void ilinux_probe_mark(unsigned int phase)
{
	if (!ilinux_probe_diag)
		return;
	WRITE_ONCE(ilinux_probe_phase, phase);
	ilinux_probe_fb_mark(0, phase);
	pr_info("ilinux-probe: phase=%u device=%u\n", phase,
		READ_ONCE(ilinux_probe_device));
}

/* Timer softirq, independent of the worker that deferred probing may block. */
static void ilinux_probe_watchdog(struct timer_list *timer)
{
	pr_info("ilinux-probe: heartbeat=%u phase=%u worker=%u device=%u ticks=%lu\n",
		++ilinux_probe_heartbeats, READ_ONCE(ilinux_probe_phase),
		READ_ONCE(ilinux_probe_worker), READ_ONCE(ilinux_probe_device), jiffies - ilinux_probe_started);
	ilinux_probe_fb_mark(3, ilinux_probe_heartbeats);
	pr_info("ilinux-probe: sched=%u selections=%u prev=%d next=%d current=%d/%.16s\n",
		READ_ONCE(ilinux_sched_phase), READ_ONCE(ilinux_sched_switches),
		READ_ONCE(ilinux_sched_prev), READ_ONCE(ilinux_sched_next),
		current->pid, current->comm);
	/* One interrupted-task stack, only if normal completion has not occurred. */
	if (ilinux_probe_heartbeats == 1)
		dump_stack();
	/* Finite logging even if a probe never completes. No forced reboot. */
	if (ilinux_probe_heartbeats < 6)
		mod_timer(timer, jiffies + 5 * HZ);
}

static void ilinux_probe_begin(void)
{
	u64 begin, elapsed, budget;
	unsigned long before, ticks;
	unsigned int loops;
	u32 rate;

	if (!ilinux_probe_diag)
		return;
	pr_info("ilinux-probe: target=%s mode=%s cpus=%u\n",
		of_machine_is_compatible("apple,j716c") &&
		of_machine_is_compatible("apple,t6050") ? "j716c-t6050" : "generic-test",
		is_kernel_in_hyp_mode() ? "EL2" : "EL1", num_online_cpus());
	ilinux_probe_mark(1);
	if (num_online_cpus() != 1 || irqs_disabled())
		panic("ilinux-probe: requires one CPU and enabled interrupts");
	rate = arch_timer_get_rate();
	if (!rate)
		panic("ilinux-probe: missing architectural counter rate");
	budget = max_t(u64, rate / 10, 1); /* 100 ms; do not wait on jiffies. */
	/* Keep the one CPU executing, but leave timer interrupts enabled. */
	preempt_disable();
	before = jiffies;
	begin = arch_timer_read_counter();
	elapsed = 0;
	for (loops = 0; loops < 100000000 && elapsed < budget; loops++) {
		cpu_relax();
		elapsed = arch_timer_read_counter() - begin;
	}
	ticks = jiffies - before;
	/* Log before preempt_enable can schedule a potentially stuck worker. */
	pr_info("ilinux-probe: timer counter=%s ticks=%lu\n",
		elapsed >= budget ? "PASS" : "FAIL", ticks);
	/* Architectural status only; no Apple implementation-defined registers. */
	pr_info("ilinux-probe: timer phys=%u virt=%u irq_masked=%u fiq_masked=%u\n",
		(unsigned int)(read_sysreg(cntp_ctl_el0) & 7),
		(unsigned int)(read_sysreg(cntv_ctl_el0) & 7),
		!!(read_sysreg(daif) & PSR_I_BIT),
		!!(read_sysreg(daif) & PSR_F_BIT));
	if (elapsed < budget || !ticks)
		panic("ilinux-probe: timer progress failed; stop RAM test");
	/* Arm before re-enabling preemption: attempt 8 stopped in this gap. */
	ilinux_probe_mark(10);
	ilinux_probe_started = jiffies;
	ilinux_probe_heartbeats = 0;
	WRITE_ONCE(ilinux_probe_active, true);
	timer_setup(&ilinux_probe_watch, ilinux_probe_watchdog, 0);
	ilinux_probe_mark(11);
	mod_timer(&ilinux_probe_watch, jiffies + 5 * HZ);
	ilinux_probe_mark(12);
	pr_info("ilinux-probe: reschedule pending=%u strip=%u (P/S/W/H hex)\n",
		!!need_resched(), ilinux_probe_fb_mark(1, 0));
	preempt_enable();
	ilinux_probe_mark(13);
	ilinux_probe_mark(2);
}

static void ilinux_probe_worker_mark(unsigned int state)
{
	if (ilinux_probe_diag && READ_ONCE(ilinux_probe_active)) {
		WRITE_ONCE(ilinux_probe_worker, state);
		ilinux_probe_fb_mark(2, state);
	}
}

static void ilinux_probe_retry(struct device *dev, bool entering)
{
	const char *compatible = "no-of-compatible";
	if (!ilinux_probe_diag || !READ_ONCE(ilinux_probe_active))
		return;
	if (entering)
		WRITE_ONCE(ilinux_probe_device, ilinux_probe_device + 1);
	/* DT compatible identifies a device class; never log its name or address. */
	if (dev->of_node)
		of_property_read_string(dev->of_node, "compatible", &compatible);
	if (ilinux_probe_device <= 32)
		pr_info("ilinux-probe: retry=%u %s compatible=%.80s\n",
			ilinux_probe_device, entering ? "begin" : "end", compatible);
	else if (entering && ilinux_probe_device == 33)
		pr_info("ilinux-probe: retry detail capped at 32; counters continue\n");
}

static void ilinux_probe_end(void)
{
	if (!ilinux_probe_diag)
		return;
	WRITE_ONCE(ilinux_probe_active, false);
	timer_shutdown_sync(&ilinux_probe_watch);
	ilinux_probe_mark(9);
}
