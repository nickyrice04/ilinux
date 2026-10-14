/* SPDX-License-Identifier: GPL-2.0-only */
/* Explicit defaults avoid regcache_hw_init's contiguous hardware scan. */
static int apple_gpio_cache_defaults(struct apple_gpio_pinctrl *pctl,
				     struct reg_default *defaults,
				     struct regmap_config *config)
{
	unsigned int pin, count = 0;

	for (pin = 0; pin < pctl->npins; pin++) {
		if (!apple_gpio_pin_available(pctl, pin))
			continue;
		ilinux_probe_pin_mark(pctl->dev, pin);
		ilinux_probe_path_mark(pctl->dev, 0x91);
		defaults[count].reg = REG_GPIO(pin);
		defaults[count++].def = readl_relaxed(pctl->base + REG_GPIO(pin));
	}
	if (!count)
		return -EINVAL;
	config->reg_defaults = defaults;
	config->num_reg_defaults = count;
	config->num_reg_defaults_raw = 0;
	config->cache_type = REGCACHE_FLAT_S;
	config->readable_reg = apple_gpio_reg_accessible;
	config->writeable_reg = apple_gpio_reg_accessible;
	ilinux_probe_pin_mark(pctl->dev, 0xfff);
	ilinux_probe_path_mark(pctl->dev, 0x92);
	dev_info(pctl->dev, "GPIO cache: pins=%u readable=%u reserved=%u\n",
		 pctl->npins, count, pctl->npins - count);
	return 0;
}
