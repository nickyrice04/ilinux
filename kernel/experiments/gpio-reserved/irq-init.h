/* SPDX-License-Identifier: GPL-2.0-only */
/* t6050: quiesce inherited inputs before gpiolib enables chained parents.
 * Register definitions and mode semantics come from the existing Linux driver.
 * Do not change outputs, mux, pull, group or pad configuration. */
static int apple_gpio_t6050_irq_init_hw(struct gpio_chip *gc)
{
	struct apple_gpio_pinctrl *pctl = gpiochip_get_data(gc);
	unsigned int pin, group, value, mode, changed = 0;
	int ret;

	ilinux_probe_path_mark(pctl->dev, 0x80);
	if (!gc->ngpio || gc->ngpio > 512 || !gc->irq.num_parents ||
	    gc->irq.num_parents > 7)
		return -EINVAL;

	/* A pending excluded source cannot be masked through its pad register.
	 * Refuse this controller before enabling parents; leave that source alone.
	 */
	ilinux_probe_path_mark(pctl->dev, 0x93);
	for (group = 0; group < gc->irq.num_parents; group++) {
		for (pin = 0; pin < gc->ngpio; pin += 32) {
			unsigned int count = gc->ngpio - pin;
			u32 declared = count >= 32 ? ~0U : BIT(count) - 1;
			u32 excluded = declared & ~apple_gpio_valid_word(pctl, pin);

			if (excluded && (readl_relaxed(pctl->base + REG_IRQ(group, pin)) & excluded))
				return dev_err_probe(pctl->dev, -EBUSY,
					"pending reserved GPIO IRQ in group %u word %u\n", group, pin / 32);
		}
	}

	for (pin = 0; pin < gc->ngpio; pin++) {
		if (!apple_gpio_pin_available(pctl, pin))
			continue;
		ilinux_probe_pin_mark(pctl->dev, pin);
		ilinux_probe_path_mark(pctl->dev, 0x81);
		ret = regmap_read(pctl->map, REG_GPIO(pin), &value);
		if (ret)
			return ret;
		mode = FIELD_GET(REG_GPIOx_MODE, value);
		if (mode < REG_GPIOx_IN_IRQ_HI || mode > REG_GPIOx_IN_IRQ_ANY)
			continue;
		/* Never attempt to override a firmware-locked pad. */
		if (value & REG_GPIOx_LOCK)
			return dev_err_probe(pctl->dev, -EPERM,
				"inherited IRQ on locked GPIO %u\n", pin);
		ilinux_probe_path_mark(pctl->dev, 0x82);
		ret = regmap_update_bits(pctl->map, REG_GPIO(pin), REG_GPIOx_MODE,
					FIELD_PREP(REG_GPIOx_MODE, REG_GPIOx_IN_IRQ_OFF));
		if (ret)
			return ret;
		/* The cache alone cannot prove that the hardware accepted a mask. */
		if (FIELD_GET(REG_GPIOx_MODE, readl(pctl->base + REG_GPIO(pin))) !=
		    REG_GPIOx_IN_IRQ_OFF)
			return dev_err_probe(pctl->dev, -EIO,
				"inherited IRQ mask readback failed at GPIO %u\n", pin);
		changed++;
	}
	/* W1C only valid pin bits, using the driver's existing ACK layout. */
	ilinux_probe_path_mark(pctl->dev, 0x83);
	for (group = 0; group < gc->irq.num_parents; group++) {
		for (pin = 0; pin < gc->ngpio; pin += 32) {
			u32 mask = apple_gpio_valid_word(pctl, pin);

			if (mask)
				writel(mask, pctl->base + REG_IRQ(group, pin));
		}
	}
	ilinux_probe_pin_mark(pctl->dev, 0xfff);
	ilinux_probe_path_mark(pctl->dev, 0x84);
	dev_info(pctl->dev, "t6050 IRQ handoff: pins=%u parents=%u masked=%u\n",
		 gc->ngpio, gc->irq.num_parents, changed);
	return 0;
}
