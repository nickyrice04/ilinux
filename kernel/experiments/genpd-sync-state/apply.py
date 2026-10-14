#!/usr/bin/env python3
"""boot034: make genpd sync_state honor pd_ignore_unused; log real power-offs;
release unclaimed boot-on domains one at a time after a long stable window.

Apply to a Linux tree: apply.py <tree>. Digest-gated on drivers/pmdomain/core.c.
Private iLinux experiment; not an upstream submission.
"""
import hashlib
from pathlib import Path
import sys

CORE_SHA256 = 'b310e39444ff5c24c7102818a5f3c52eddc3836175e48e893a7c4a4dabe9c7fd'

LADDER = r'''
/* ILINUX-LADDER-BEGIN */
/*
 * iLinux boot034 experiment. With pd_ignore_unused the sync_state paths above
 * keep every boot-on domain powered. After a long stable window, release the
 * remaining boot-on, unclaimed domains one at a time and log each name before
 * it is powered off, so that a firmware-initiated reset is attributable to the
 * domain whose power-off preceded it. Bounded by the number of domains.
 */
#define ILINUX_LADDER_START_MS	17000
#define ILINUX_LADDER_STEP_MS	500

static void ilinux_genpd_ladder_fn(struct work_struct *work);
static DECLARE_DELAYED_WORK(ilinux_genpd_ladder_work, ilinux_genpd_ladder_fn);
static unsigned int ilinux_ladder_visited;	/* gpd_list entries already examined */
static unsigned int ilinux_ladder_released;	/* domains released so far */

static void ilinux_genpd_ladder_fn(struct work_struct *work)
{
	struct generic_pm_domain *genpd, *pick = NULL;
	unsigned int n = 0;

	mutex_lock(&gpd_list_lock);
	list_for_each_entry(genpd, &gpd_list, gpd_list_node) {
		if (n++ < ilinux_ladder_visited)
			continue;
		ilinux_ladder_visited = n;
		if (genpd_status_on(genpd) && genpd->stay_on &&
		    !genpd_is_always_on(genpd)) {
			pick = genpd;
			break;
		}
	}

	if (!pick) {
		mutex_unlock(&gpd_list_lock);
		pr_info("ilinux-genpd: ladder complete: %u domains released\n",
			ilinux_ladder_released);
		return;
	}

	genpd_lock(pick);
	ilinux_ladder_released++;
	pr_info("ilinux-genpd: ladder %u: release %s\n",
		ilinux_ladder_released, pick->name);
	pick->stay_on = false;
	genpd_power_off(pick, false, false, 0);
	genpd_unlock(pick);
	mutex_unlock(&gpd_list_lock);

	schedule_delayed_work(&ilinux_genpd_ladder_work,
			      msecs_to_jiffies(ILINUX_LADDER_STEP_MS));
}

static int __init ilinux_genpd_ladder_init(void)
{
	/* Without pd_ignore_unused, sync_state already released everything. */
	if (!pd_ignore_unused)
		return 0;

	pr_info("ilinux-genpd: ladder armed: first release in %u ms, then one domain per %u ms\n",
		ILINUX_LADDER_START_MS, ILINUX_LADDER_STEP_MS);
	schedule_delayed_work(&ilinux_genpd_ladder_work,
			      msecs_to_jiffies(ILINUX_LADDER_START_MS));
	return 0;
}
late_initcall(ilinux_genpd_ladder_init);
/* ILINUX-LADDER-END */

'''


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise SystemExit('anchor count %d != 1: %r' % (text.count(old), old[:60]))
    return text.replace(old, new)


def main():
    root = Path(sys.argv[1])
    path = root / 'drivers/pmdomain/core.c'
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != CORE_SHA256:
        raise SystemExit('drivers/pmdomain/core.c differs from the reviewed digest')
    s = data.decode()

    # 1. sync_state must honor pd_ignore_unused (both provider paths).
    s = replace_once(s, '''	if (!np)
		return;

	mutex_lock(&gpd_list_lock);
	list_for_each_entry(genpd, &gpd_list, gpd_list_node) {
		if (genpd->provider == of_fwnode_handle(np)) {''', '''	if (!np)
		return;

	/* iLinux: pd_ignore_unused must also cover sync_state, as for the late sweep. */
	if (pd_ignore_unused) {
		pr_info_once("ilinux-genpd: sync_state keeps unused power domains on (pd_ignore_unused)\\n");
		return;
	}

	mutex_lock(&gpd_list_lock);
	list_for_each_entry(genpd, &gpd_list, gpd_list_node) {
		if (genpd->provider == of_fwnode_handle(np)) {''')
    s = replace_once(s, '''	struct generic_pm_domain *genpd = container_of(dev, struct generic_pm_domain, dev);

	switch (genpd->sync_state) {''', '''	struct generic_pm_domain *genpd = container_of(dev, struct generic_pm_domain, dev);

	/* iLinux: see of_genpd_sync_state(). */
	if (pd_ignore_unused) {
		pr_info_once("ilinux-genpd: sync_state keeps unused power domains on (pd_ignore_unused)\\n");
		return;
	}

	switch (genpd->sync_state) {''')

    # 2. Trace every real power-off.
    s = replace_once(s, '''	if (!genpd->power_off)
		goto out;

	timed = timed && genpd->gd && !genpd->states[state_idx].fwnode;''', '''	if (!genpd->power_off)
		goto out;

	pr_info("ilinux-genpd: power off %s\\n", genpd->name);

	timed = timed && genpd->gd && !genpd->states[state_idx].fwnode;''')

    # 3. Staged release ladder, after the provider sync_state helpers.
    s = replace_once(s, '''EXPORT_SYMBOL_GPL(of_genpd_sync_state);
''', '''EXPORT_SYMBOL_GPL(of_genpd_sync_state);
''' + LADDER)

    path.write_text(s)
    print('PASS: genpd sync_state honors pd_ignore_unused; power-off trace and release ladder added')


if __name__ == '__main__':
    main()
