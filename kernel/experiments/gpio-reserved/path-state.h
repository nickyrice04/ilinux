/* SPDX-License-Identifier: GPL-2.0-only */
/* Included after the existing diagnostic globals; all device refs are bounded. */
static struct { const char *path; struct device_node *node; } ilinux_probe_nodes[] = {
#include "ilinux-device-identities.h"
};
static struct task_struct *ilinux_probe_owner;

static void ilinux_probe_identity_init(void)
{
	if (!of_machine_is_compatible("apple,j716c") ||
	    !of_machine_is_compatible("apple,t6050"))
		return;
	for (unsigned int i = 0; i < ARRAY_SIZE(ilinux_probe_nodes); i++)
		ilinux_probe_nodes[i].node = of_find_node_by_path(ilinux_probe_nodes[i].path);
}

static void ilinux_probe_identity_end(void)
{
	WRITE_ONCE(ilinux_probe_owner, NULL);
	for (unsigned int i = 0; i < ARRAY_SIZE(ilinux_probe_nodes); i++) {
		of_node_put(ilinux_probe_nodes[i].node);
		ilinux_probe_nodes[i].node = NULL;
	}
}

static unsigned int ilinux_probe_id(const struct device *dev)
{
	if (!dev || !dev->of_node)
		return 0;
	for (unsigned int i = 0; i < ARRAY_SIZE(ilinux_probe_nodes); i++)
		if (dev->of_node == ilinux_probe_nodes[i].node)
			return i + 1;
	return 0; /* A missing/dynamic/non-OF node is unknown, never guessed. */
}

static void ilinux_probe_path_start(struct device *dev)
{
	WRITE_ONCE(ilinux_probe_owner, current);
	ilinux_probe_fb_mark(4, ilinux_probe_id(dev));
	ilinux_probe_fb_mark(5, 0);
	ilinux_probe_fb_mark(7, 0xfff);
	ilinux_probe_fb_mark(6, ilinux_probe_id(dev));
}

void ilinux_probe_path_mark(struct device *dev, unsigned int phase);
void ilinux_probe_path_mark(struct device *dev, unsigned int phase)
{
	/* Attribute synchronous/nested operations to this retry's task only.
	 * Other async tasks cannot replace its last boundary. Never log pointers.
	 */
	if (!READ_ONCE(ilinux_probe_active) || READ_ONCE(ilinux_probe_owner) != current)
		return;
	ilinux_probe_fb_mark(6, ilinux_probe_id(dev));
	ilinux_probe_fb_mark(5, phase);
}

void ilinux_probe_pin_mark(struct device *dev, unsigned int pin);
void ilinux_probe_pin_mark(struct device *dev, unsigned int pin)
{
	if (!READ_ONCE(ilinux_probe_active) || READ_ONCE(ilinux_probe_owner) != current)
		return;
	ilinux_probe_fb_mark(6, ilinux_probe_id(dev));
	ilinux_probe_fb_mark(7, pin);
}
