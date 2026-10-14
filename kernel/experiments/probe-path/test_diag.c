/* Compile the actual diagnostic body with controlled clock/timer/print shims. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <setjmp.h>
typedef uint64_t u64;
typedef uint32_t u32;
#define __init
#define __setup(a, b)
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x, v) ((x) = (v))
#define max_t(t, a, b) ((t)(a) > (t)(b) ? (t)(a) : (t)(b))
#define HZ 250
#define PSR_I_BIT (1UL << 7)
#define PSR_F_BIT (1UL << 6)
#define read_sysreg(reg) (!strcmp(#reg, "daif") ? 0UL : 5UL)
static unsigned long jiffies;
static unsigned int cpus = 1, rate = 1000, preempted, arms, shutdowns, logs, stacks, marks;
static bool disabled, firing = true, advancing = true;
static u64 counter;
static jmp_buf panic_env;
struct timer_list { void (*callback)(struct timer_list *); };
struct device_node { int unused; };
struct device { struct device_node *of_node; };
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
static struct device_node *of_find_node_by_path(const char *s) { (void)s; return NULL; }
static void of_node_put(struct device_node *n) { (void)n; }
static struct task_struct { int pid; char comm[17]; } fake_task = { 1, "swapper-test" };
#define current (&fake_task)
static bool need_resched(void) { return true; }
static void dump_stack(void) { stacks++; }
bool ilinux_probe_fb_mark(unsigned int lane, unsigned int value) { assert(lane < 7 && value < 65536); marks++; return true; }
unsigned int ilinux_probe_fb_state(void) { return 6; }
static void pr_info(const char *fmt, ...) __attribute__((format(printf,1,2)));
static void pr_info(const char *fmt, ...) { va_list a; char b[256]; va_start(a,fmt); vsnprintf(b,sizeof(b),fmt,a); va_end(a); logs++; }
static void panic(const char *s) { (void)s; longjmp(panic_env, 1); }
static void preempt_disable(void) { preempted++; }
static void preempt_enable(void) { assert(preempted == 1 && arms == 1); preempted--; }
static unsigned int num_online_cpus(void) { return cpus; }
static bool irqs_disabled(void) { return disabled; }
static u32 arch_timer_get_rate(void) { return rate; }
static u64 arch_timer_read_counter(void) { if (advancing) counter += 10; if (firing) jiffies++; return counter; }
static void cpu_relax(void) {}
static bool of_machine_is_compatible(const char *s) { return !strcmp(s,"apple,j716c") || !strcmp(s,"apple,t6050"); }
static bool is_kernel_in_hyp_mode(void) { return true; }
static void of_property_read_string(void *n, const char *p, const char **v) { (void)n; (void)p; *v="apple,t6050-pmgr-pwrstate"; }
static void timer_setup(struct timer_list *t, void (*f)(struct timer_list *), int flags) { assert(!flags); t->callback=f; }
static void mod_timer(struct timer_list *t, unsigned long expires) { assert(t->callback); assert(expires > jiffies); arms++; }
static void timer_shutdown_sync(struct timer_list *t) { assert(t->callback); shutdowns++; }
#include "tested-diag.h"
int main(void)
{
    unsigned int before;
    struct device dev = { .of_node = (void *)1 };
    ilinux_probe_begin(); ilinux_probe_sched_mark(5, 1, 2); assert(!logs && !arms && !marks); /* default is inert */
    assert(!ilinux_probe_setup("0")); assert(!ilinux_probe_diag);
    assert(ilinux_probe_setup("1"));
    ilinux_probe_begin(); assert(!preempted && arms == 1 && ilinux_probe_phase == 2);
    ilinux_probe_sched_mark(5, 1, 7); assert(ilinux_sched_switches == 1 && ilinux_sched_prev == 1 && ilinux_sched_next == 7);
    ilinux_probe_sched_mark(7, 0, 0); assert(ilinux_sched_phase == 7 && ilinux_sched_next == 7);
    for (unsigned int state = 0x10; state <= 0x31; state++) { ilinux_probe_sched_mark(state, 0, 0); assert(ilinux_sched_phase == state); }
    before = logs;
    for (int i = 0; i < 40; i++) { ilinux_probe_retry(&dev, true); ilinux_probe_retry(&dev, false); }
    assert(logs - before == 65 && ilinux_probe_device == 40); /* bounded detailed logs */
    before = arms;
    for (int i = 0; i < 6; i++) ilinux_probe_watch.callback(&ilinux_probe_watch);
    assert(arms - before == 5 && ilinux_probe_heartbeats == 6 && stacks == 1);
    ilinux_probe_end(); assert(shutdowns == 1 && !ilinux_probe_active && ilinux_probe_phase == 9);
    before = logs; ilinux_probe_retry(&dev, true); assert(before == logs);
    before = marks; ilinux_probe_sched_mark(5, 2, 3); assert(before == marks);
    firing = false;
    if (!setjmp(panic_env)) { ilinux_probe_begin(); assert(!"missing tick was accepted"); }
    assert(preempted == 1); preempted = 0;
    firing = true; advancing = false;
    if (!setjmp(panic_env)) { ilinux_probe_begin(); assert(!"frozen counter was accepted"); }
    preempted = 0; advancing = true;
    rate = 0;
    if (!setjmp(panic_env)) { ilinux_probe_begin(); assert(!"zero rate accepted"); }
    rate = 1000; disabled = true;
    if (!setjmp(panic_env)) { ilinux_probe_begin(); assert(!"masked IRQs accepted"); }
    disabled = false; cpus = 2;
    if (!setjmp(panic_env)) { ilinux_probe_begin(); assert(!"multiple CPUs accepted"); }
    puts("PASS: diagnostic invariants, pre-armed watchdog, scheduler state and single stack; no hardware exercised");
    return 0;
}
