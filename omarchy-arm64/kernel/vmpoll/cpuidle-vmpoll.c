// SPDX-License-Identifier: GPL-2.0
/*
 * cpuidle-vmpoll: poll briefly before WFI in an arm64 VM guest.
 *
 * Under Apple's Hypervisor.framework with its in-kernel GIC, a guest WFI is
 * handled inside hv_vcpu_run(): the framework parks the vCPU thread on a
 * condition variable until an interrupt is pending.  Waking a vCPU parked
 * that way costs about 19 us, while an IPI to a vCPU that is still running
 * guest code arrives in about 1.6 us.  Measured with a cross-vCPU pipe
 * ping-pong: 20.6 us with the target vCPU idle, 1.65 us with it kept busy.
 *
 * This driver gives the cpuidle governor a polling state ahead of WFI, so
 * idle periods predicted to be short are spent spinning with interrupts
 * enabled instead of halting.  Idle periods predicted to be long still
 * halt, and a single poll gives up after poll_limit_us, so an idle desktop
 * does not keep host cores busy.
 *
 * Why a separate driver: arm64 7.1.6 does not select ARCH_HAS_CPU_RELAX, so
 * the generic polling state (drivers/cpuidle/poll_state.c) is not built,
 * and the in-tree cpuidle-haltpoll driver is x86 + KVM only.  This is meant
 * for the iLinux VM kernel only; it says nothing about native hardware.
 */
#include <linux/cpuidle.h>
#include <linux/module.h>
#include <linux/sched.h>
#include <linux/sched/clock.h>
#include <linux/sched/idle.h>
#include <asm/barrier.h>

static unsigned int poll_limit_us = 50;
module_param(poll_limit_us, uint, 0644);
MODULE_PARM_DESC(poll_limit_us, "longest a single idle entry polls before giving up, in us (default 50)");

static unsigned int wfi_exit_latency_us = 20;
module_param(wfi_exit_latency_us, uint, 0444);
MODULE_PARM_DESC(wfi_exit_latency_us, "exit latency reported for WFI, in us (default 20, measured ~19)");

static unsigned int wfi_residency_us = 100;
module_param(wfi_residency_us, uint, 0444);
MODULE_PARM_DESC(wfi_residency_us, "shortest predicted idle for which the governor halts, in us (default 100)");

/* Checking the clock costs more than a spin iteration: only look every so often. */
#define VMPOLL_SPINS_PER_CLOCK_CHECK 200

static int vmpoll_poll(struct cpuidle_device *dev, struct cpuidle_driver *drv, int index)
{
	const u64 limit_ns = (u64)READ_ONCE(poll_limit_us) * NSEC_PER_USEC;
	const u64 start = local_clock();
	unsigned int spins = 0;

	dev->poll_time_limit = false;
	/*
	 * Entered with interrupts off.  Poll with them on: on arm64 a waker
	 * always sends a reschedule IPI (there is no polling flag), and it is
	 * that IPI reaching a still-running vCPU that makes the wakeup cheap.
	 */
	raw_local_irq_enable();
	if (!current_set_polling_and_test()) {
		while (!need_resched()) {
			cpu_relax();
			if (++spins < VMPOLL_SPINS_PER_CLOCK_CHECK)
				continue;
			spins = 0;
			if (local_clock() - start > limit_ns) {
				dev->poll_time_limit = true;
				break;
			}
		}
	}
	raw_local_irq_disable();
	current_clr_polling();
	return index;
}

static int vmpoll_wfi(struct cpuidle_device *dev, struct cpuidle_driver *drv, int index)
{
	/*
	 * cpu_do_idle() is not exported to modules.  Without pseudo-NMI (not
	 * enabled in this kernel) it only adds no-op IRQ context save/restore
	 * around exactly this sequence.
	 */
	dsb(sy);
	wfi();
	return index;
}

/*
 * No .owner: the cpuidle core takes a module reference for every registered
 * CPU device, which would make the module impossible to unload.  Unloading
 * is safe without it, because cpuidle_unregister() waits for every CPU to
 * leave the idle handler before the states go away.
 */
static struct cpuidle_driver vmpoll_driver = {
	.name = "vmpoll",
	.state_count = 2,
};

static int __init vmpoll_init(void)
{
	struct cpuidle_state *poll = &vmpoll_driver.states[0];
	struct cpuidle_state *halt = &vmpoll_driver.states[1];

	snprintf(poll->name, CPUIDLE_NAME_LEN, "POLL");
	snprintf(poll->desc, CPUIDLE_DESC_LEN, "bounded poll before WFI");
	poll->exit_latency = 0;
	poll->target_residency = 0;
	poll->power_usage = -1;
	poll->flags = CPUIDLE_FLAG_POLLING;
	poll->enter = vmpoll_poll;

	snprintf(halt->name, CPUIDLE_NAME_LEN, "WFI");
	snprintf(halt->desc, CPUIDLE_DESC_LEN, "WFI, vCPU parked by the hypervisor");
	halt->exit_latency = wfi_exit_latency_us;
	halt->target_residency = wfi_residency_us;
	halt->enter = vmpoll_wfi;

	return cpuidle_register(&vmpoll_driver, NULL);
}

static void __exit vmpoll_exit(void)
{
	cpuidle_unregister(&vmpoll_driver);
}

module_init(vmpoll_init);
module_exit(vmpoll_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Bounded polling idle state ahead of WFI for arm64 VM guests");
