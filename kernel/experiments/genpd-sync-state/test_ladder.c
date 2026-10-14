/*
 * Offline model test for the boot034 genpd release ladder (private iLinux).
 *
 * test_genpd.py extracts the exact block between ILINUX-LADDER-BEGIN/END from
 * apply.py into ladder_block.inc and compiles this harness around it with
 * stubbed kernel types. The model of genpd_power_off() follows the checks in
 * drivers/pmdomain/core.c: no power-off while off, always-on, stay_on, with a
 * powered subdomain, or with an active consumer device.
 */
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define __init

struct list_head { struct list_head *next, *prev; };
#define LIST_HEAD_INIT(n) { &(n), &(n) }
#define LIST_HEAD(n) struct list_head n = LIST_HEAD_INIT(n)
static void list_add_tail(struct list_head *n, struct list_head *h)
{
	n->prev = h->prev; n->next = h; h->prev->next = n; h->prev = n;
}
#define container_of(p, t, m) ((t *)((char *)(p) - offsetof(t, m)))
#define list_for_each_entry(pos, head, member)                                   \
	for (pos = container_of((head)->next, __typeof__(*pos), member);          \
	     &pos->member != (head);                                              \
	     pos = container_of(pos->member.next, __typeof__(*pos), member))

enum { GENPD_STATE_ON, GENPD_STATE_OFF };
#define GENPD_FLAG_ALWAYS_ON 1u

struct generic_pm_domain {
	const char *name;
	bool stay_on;
	int status;
	unsigned int flags;
	int sd_count;		/* powered subdomains */
	bool consumer_active;	/* a consumer device is not runtime-suspended */
	struct list_head gpd_list_node;
};

static LIST_HEAD(gpd_list);
static bool pd_ignore_unused;
#define genpd_status_on(g)	((g)->status == GENPD_STATE_ON)
#define genpd_is_always_on(g)	(((g)->flags & GENPD_FLAG_ALWAYS_ON) != 0)
#define genpd_lock(g)		do { locked++; } while (0)
#define genpd_unlock(g)		do { locked--; } while (0)
static int locked, list_locked;
#define mutex_lock(m)		do { list_locked++; } while (0)
#define mutex_unlock(m)		do { list_locked--; } while (0)
#define gpd_list_lock		0

static char log_buf[8192];
#define pr_info(...)		do { size_t l = strlen(log_buf); snprintf(log_buf + l, sizeof log_buf - l, __VA_ARGS__); } while (0)

struct work_struct { int dummy; };
struct delayed_work { struct work_struct work; };
#define DECLARE_DELAYED_WORK(n, f) struct delayed_work n = {{0}}
static int scheduled, last_delay_ms;
static void schedule_delayed_work(struct delayed_work *w, unsigned long delay)
{
	(void)w; scheduled = 1; last_delay_ms = (int)delay;
}
#define msecs_to_jiffies(x)	(x)
#define late_initcall(fn)	static int (*late_initcall_ptr)(void) = fn

static char off_order[256];
static void genpd_power_off(struct generic_pm_domain *g, bool one_dev_on, bool one_dev_probing,
			    unsigned int depth)
{
	(void)one_dev_on; (void)one_dev_probing; (void)depth;
	if (!genpd_status_on(g) || genpd_is_always_on(g) || g->stay_on || g->sd_count > 0 ||
	    g->consumer_active)
		return;
	g->status = GENPD_STATE_OFF;
	strcat(off_order, g->name);
	strcat(off_order, ",");
}

#include "ladder_block.inc"

static int failures;
#define CHECK(c)                                                                 \
	do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); failures++; } } while (0)

static struct generic_pm_domain doms[9];
static void add(int i, const char *name, int status, bool stay_on, unsigned flags, int sd, bool act)
{
	doms[i] = (struct generic_pm_domain){name, stay_on, status, flags, sd, act, {0, 0}};
	list_add_tail(&doms[i].gpd_list_node, &gpd_list);
}

static void reset_log(void)
{
	log_buf[0] = 0; off_order[0] = 0; scheduled = 0;
}

int main(void)
{
	/* init: only armed when pd_ignore_unused is set */
	pd_ignore_unused = false;
	CHECK(late_initcall_ptr() == 0 && !scheduled);
	pd_ignore_unused = true;
	CHECK(late_initcall_ptr() == 0 && scheduled && last_delay_ms == ILINUX_LADDER_START_MS);
	CHECK(strstr(log_buf, "ladder armed") != NULL);

	/* empty list: completes at once, no reschedule */
	reset_log();
	ilinux_genpd_ladder_fn(NULL);
	CHECK(!scheduled && strstr(log_buf, "ladder complete: 0 domains released"));
	CHECK(locked == 0 && list_locked == 0);

	/* A on, B off, C always-on, D on with an active consumer, E on, F on without stay_on,
	 * G on with a powered subdomain, H on, I off but still flagged stay_on */
	ilinux_ladder_visited = 0; ilinux_ladder_released = 0;
	add(0, "A", GENPD_STATE_ON, true, 0, 0, false);
	add(1, "B", GENPD_STATE_OFF, false, 0, 0, false);
	add(2, "C", GENPD_STATE_ON, true, GENPD_FLAG_ALWAYS_ON, 0, false);
	add(3, "D", GENPD_STATE_ON, true, 0, 0, true);
	add(4, "E", GENPD_STATE_ON, true, 0, 0, false);
	add(5, "F", GENPD_STATE_ON, false, 0, 0, false);
	add(6, "G", GENPD_STATE_ON, true, 0, 1, false);
	add(7, "H", GENPD_STATE_ON, true, 0, 0, false);
	add(8, "I", GENPD_STATE_OFF, true, 0, 0, false);	/* inconsistent: off yet stay_on */

	reset_log();
	int steps = 0;
	do {
		scheduled = 0;
		ilinux_genpd_ladder_fn(NULL);
		CHECK(locked == 0 && list_locked == 0);
		if (scheduled)
			CHECK(last_delay_ms == ILINUX_LADDER_STEP_MS);
		CHECK(++steps < 20);
	} while (scheduled);

	CHECK(ilinux_ladder_released == 5);		/* A D E G H */
	CHECK(strcmp(off_order, "A,E,H,") == 0);	/* D has a consumer, G a subdomain */
	CHECK(doms[3].status == GENPD_STATE_ON && !doms[3].stay_on);
	CHECK(doms[2].stay_on && doms[2].status == GENPD_STATE_ON);	/* always-on untouched */
	CHECK(doms[5].status == GENPD_STATE_ON);	/* F was not held by stay_on: left alone */
	CHECK(steps == 6);				/* 5 releases + the completion call */
	CHECK(strstr(log_buf, "ladder 1: release A") && strstr(log_buf, "ladder 5: release H"));
	CHECK(strstr(log_buf, "ladder complete: 5 domains released"));
	CHECK(strstr(log_buf, "release B") == NULL && strstr(log_buf, "release C") == NULL);
	CHECK(strstr(log_buf, "release I") == NULL);	/* never "release" an off domain */

	/* a second pass finds nothing new */
	reset_log();
	ilinux_genpd_ladder_fn(NULL);
	CHECK(!scheduled && strstr(log_buf, "ladder complete: 5 domains released"));

	if (failures) {
		printf("ladder model: %d failure(s)\n", failures);
		return 1;
	}
	printf("ladder model PASS\n");
	return 0;
}
